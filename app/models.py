from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class EventMetadata(BaseModel):
    queue_depth: Optional[int] = Field(default=None, description="Queue depth for BILLING_QUEUE_JOIN")
    sku_zone: Optional[str] = Field(default=None, description="Zone label from store_layout.json")
    session_seq: Optional[int] = Field(default=1, description="Ordinal position of this event in visitor session")

class EventSchema(BaseModel):
    event_id: str = Field(description="UUID-v4 globally unique identifier")
    store_id: str = Field(description="Identifier of the store")
    camera_id: str = Field(description="Identifier of the camera producing the event")
    visitor_id: str = Field(description="Re-ID token unique per visit session")
    event_type: str = Field(description="Event type from the event catalogue (ENTRY, EXIT, ZONE_ENTER, ZONE_EXIT, ZONE_DWELL, BILLING_QUEUE_JOIN, BILLING_QUEUE_ABANDON, REENTRY)")
    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    zone_id: Optional[str] = Field(default=None, description="Null for ENTRY/EXIT events, otherwise name of zone")
    dwell_ms: int = Field(default=0, description="Dwell time in milliseconds; 0 for instantaneous events")
    is_staff: bool = Field(default=False, description="Flag indicating if the person is classified as store staff")
    confidence: float = Field(default=1.0, description="Detection confidence score (0.0 to 1.0)")
    metadata: Optional[EventMetadata] = Field(default_factory=EventMetadata)

class IngestResponse(BaseModel):
    status: str
    processed_count: int
    failed_count: int
    errors: List[Dict[str, Any]]

class StoreMetricsResponse(BaseModel):
    store_id: str
    timestamp: datetime
    unique_visitors: int
    conversion_rate: float
    avg_dwell_times: Dict[str, float]
    queue_depth: int
    abandonment_rate: float

class FunnelStage(BaseModel):
    stage_name: str
    count: int
    drop_off_pct: float

class StoreFunnelResponse(BaseModel):
    store_id: str
    timestamp: datetime
    funnel: List[FunnelStage]

class HeatmapGridCell(BaseModel):
    zone_id: str
    visit_frequency: int
    avg_dwell_sec: float
    normalized_score: float  # 0-100

class StoreHeatmapResponse(BaseModel):
    store_id: str
    timestamp: datetime
    data_confidence: bool
    heatmap: List[HeatmapGridCell]

class AnomalyItem(BaseModel):
    anomaly_id: str
    anomaly_type: str  # e.g., QUEUE_SPIKE, CONVERSION_DROP, DEAD_ZONE, UNAUTHORIZED_ENTRY
    severity: str  # INFO, WARN, CRITICAL
    timestamp: str
    zone_id: Optional[str] = None
    description: str
    suggested_action: str

class StoreAnomaliesResponse(BaseModel):
    store_id: str
    timestamp: datetime
    anomalies: List[AnomalyItem]

class HealthResponse(BaseModel):
    status: str
    database_connected: bool
    last_event_timestamps: Dict[str, str]  # store_id -> last event timestamp
    stale_feeds: List[str]  # list of stale camera IDs (no event for >10 mins)
