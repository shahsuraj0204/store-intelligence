import time
import uuid
import json
import logging
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any

from app.db import init_db
from app.models import EventSchema, IngestResponse, StoreMetricsResponse, StoreFunnelResponse, StoreHeatmapResponse, StoreAnomaliesResponse, HealthResponse
from app.ingestion import ingest_events_batch
from app.metrics import calculate_store_metrics, get_store_heatmap
from app.funnel import compute_store_funnel
from app.anomalies import detect_anomalies
from app.health import check_system_health
from app.insights import generate_store_insights
from app.journeys import get_store_visitor_journeys
from app.placement_optimizer import analyze_layout_placement

# Initialize database
init_db()

# Setup Logger
logger = logging.getLogger("store_intelligence")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(ch)

app = FastAPI(
    title="Store Intelligence API",
    description="Production-grade Store Intelligence API with live metrics, real-time analytics, and anomaly detection.",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Connections Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                # Handle disconnected clients gracefully
                pass

manager = ConnectionManager()

# Structured Logging & Graceful Degradation Middleware
@app.middleware("http")
async def store_intelligence_middleware(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Extract store_id if present in path params
    store_id = "unknown"
    path_parts = request.url.path.split("/")
    if "stores" in path_parts:
        try:
            store_idx = path_parts.index("stores")
            if store_idx + 1 < len(path_parts):
                store_id = path_parts[store_idx + 1]
        except ValueError:
            pass
            
    # Extract event_count for ingest endpoint
    event_count = 0
    if request.url.path == "/events/ingest" and request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, list):
                event_count = len(body)
            elif isinstance(body, dict):
                event_count = 1
        except Exception:
            pass
            
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        # Graceful degradation for database outages or runtime panics
        latency = int((time.time() - start_time) * 1000)
        status_code = 503 if "Database unavailable" in str(e) or "sqlite" in str(e).lower() else 500
        
        log_payload = {
            "trace_id": trace_id,
            "store_id": store_id,
            "endpoint": request.url.path,
            "latency_ms": latency,
            "event_count": event_count,
            "status_code": status_code,
            "error": str(e)
        }
        logger.error(json.dumps(log_payload))
        
        error_detail = "Database service unavailable. Please check container health." if status_code == 503 else "Internal Server Error."
        return JSONResponse(
            status_code=status_code,
            content={
                "error": error_detail,
                "trace_id": trace_id,
                "status_code": status_code
            }
        )

    latency = int((time.time() - start_time) * 1000)
    
    # Log request details
    log_payload = {
        "trace_id": trace_id,
        "store_id": store_id,
        "endpoint": request.url.path,
        "latency_ms": latency,
        "event_count": event_count,
        "status_code": status_code
    }
    logger.info(json.dumps(log_payload))
    
    # Add trace ID to headers
    response.headers["X-Trace-ID"] = trace_id
    return response

# WebSocket real-time feed
@websocket_route := app.websocket("/events/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; clients read broadcasts, but don't need to post
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# 1. POST /events/ingest
@app.post("/events/ingest", response_model=IngestResponse)
async def ingest_events(events: List[Dict[str, Any]]):
    if len(events) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size exceeds maximum limit of 500 events."
        )
        
    result = ingest_events_batch(events)
    
    # Broadcast successfully ingested events over WebSockets
    if result["processed_count"] > 0:
        await manager.broadcast({
            "type": "event_ingested_batch",
            "count": result["processed_count"],
            "events": [e for e in events if e.get("event_id") not in [err["event_id"] for err in result["errors"]]]
        })
        
    return result

# 1a. POST /events/clear
@app.post("/events/clear")
async def clear_events():
    try:
        from app.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events")
        conn.commit()
        conn.close()
        # Broadcast a clear message so connected websockets can update
        await manager.broadcast({
            "type": "events_cleared"
        })
        return {"status": "success", "message": "Database cleared successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear database: {str(e)}"
        )

# 2. GET /stores/{id}/metrics
@app.get("/stores/{id}/metrics", response_model=StoreMetricsResponse)
async def get_store_metrics(id: str):
    try:
        metrics = calculate_store_metrics(id)
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate metrics: {str(e)}"
        )

# 3. GET /stores/{id}/funnel
@app.get("/stores/{id}/funnel", response_model=StoreFunnelResponse)
async def get_store_funnel(id: str):
    try:
        stages = compute_store_funnel(id)
        return {
            "store_id": id,
            "timestamp": datetime.utcnow(),
            "funnel": stages
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversion funnel: {str(e)}"
        )

# 4. GET /stores/{id}/heatmap
@app.get("/stores/{id}/heatmap", response_model=StoreHeatmapResponse)
async def get_store_heatmap_endpoint(id: str):
    try:
        heatmap_data = get_store_heatmap(id)
        return heatmap_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve heatmap: {str(e)}"
        )

# 5. GET /stores/{id}/anomalies
@app.get("/stores/{id}/anomalies", response_model=StoreAnomaliesResponse)
async def get_store_anomalies(id: str):
    try:
        anomalies = detect_anomalies(id)
        return {
            "store_id": id,
            "timestamp": datetime.utcnow(),
            "anomalies": anomalies
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect anomalies: {str(e)}"
        )

# 6. GET /health
@app.get("/health", response_model=HealthResponse)
async def get_health():
    health = check_system_health()
    if health["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=health)
    return health

# 5a. GET /stores/{id}/insights
@app.get("/stores/{id}/insights")
async def get_store_insights_endpoint(id: str):
    try:
        insights = generate_store_insights(id)
        return insights
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate insights: {str(e)}"
        )

# 5b. GET /stores/{id}/journeys
@app.get("/stores/{id}/journeys")
async def get_store_journeys_endpoint(id: str):
    try:
        journeys = get_store_visitor_journeys(id)
        return journeys
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve visitor journeys: {str(e)}"
        )
# 5c. GET /stores/{id}/placement-optimization
@app.get("/stores/{id}/placement-optimization")
async def get_store_placement_optimization(id: str):
    try:
        optimization = analyze_layout_placement(id)
        return optimization
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze layout placement: {str(e)}"
        )

from fastapi.responses import StreamingResponse
from app.camera_stream import get_camera_stream_generator

# 7. GET /stores/{id}/cameras/{camera_id}/stream
@app.get("/stores/{id}/cameras/{camera_id}/stream")
def get_camera_stream(id: str, camera_id: str):
    return StreamingResponse(
        get_camera_stream_generator(id, camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# Mount Dashboard folder as static files
# Make sure dashboard files are placed in `/dashboard`
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")

# Add a default redirect to the dashboard
from fastapi.responses import RedirectResponse
@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/dashboard")

from datetime import datetime
