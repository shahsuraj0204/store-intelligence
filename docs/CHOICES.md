# Store Intelligence System - Engineering Decisions (CHOICES.md)

This document describes the architectural trade-offs, alternatives considered, and justifications for the core engineering decisions made in building the store intelligence prototype.

---

## Decision 1: Object Detection and Tracking Model Selection

### Options Considered:
1.  **YOLOv8 Nano (yolov8n.pt)**: Extremely lightweight (3.2M parameters), fast inference speeds (3-5ms on GPU, 15-30ms on CPU).
2.  **YOLOv8 Medium (yolov8m.pt)**: Larger size, higher detection accuracy, but slow on CPU (100-200ms).
3.  **MediaPipe Pose**: Good for single-person tracking but struggles in crowded retail store environments.

### What the AI Suggested:
The AI suggested using YOLOv8 Medium with ByteTrack to maximize human detection scores, noting that retail environments are crowded and occlusion is frequent.

### What We Chose and Why:
We chose **YOLOv8 Nano (yolov8n.pt) combined with ByteTrack**.
*   **Rationale**: The evaluation environment runs on CPU-only containers without CUDA GPU support. YOLOv8 Medium drops to under 5 FPS on CPU, making batch video processing slow. YOLOv8 Nano runs significantly faster, uses less memory, and when paired with ByteTrack (which uses Kalman filtering and Hungarian association on box overlap), is robust against occlusion and cross-camera track interruptions.

---

## Decision 2: Event Schema Design Rationale

### Options Considered:
1.  **Raw Coordinate Streams**: Posting raw track IDs and $(x, y)$ coordinates to the API for the backend to process.
2.  **State-Change Ingestion (Selected)**: Defining a catalog of high-level behavior events (ENTRY, EXIT, ZONE_ENTER, ZONE_EXIT, ZONE_DWELL, BILLING_QUEUE_JOIN).

### What the AI Suggested:
The AI suggested sending raw coordinates every 10 frames and running a coordinate-to-zone processor on the server.

### What We Chose and Why:
We chose a **decoupled State-Change Event Schema** (complying with the required schema in Section 5 of the PDF).
*   **Rationale**: Sending raw coordinate streams causes heavy network overhead and increases API ingestion workloads. Moving the zone-mapping logic to the edge/pipeline layer allows the backend to be completely database-centric. The backend only records clean, high-level behavioral logs (`visitor_id`, `dwell_ms`, `event_type`), making API queries for metrics and funnels extremely fast and scalable.

---

## Decision 3: API Framework & Storage Choice

### Options Considered:
1.  **FastAPI + SQLite (Selected)**: Python-based async server with zero-config SQL storage.
2.  **Express.js + MongoDB**: Node.js server with document storage.
3.  **Django + PostgreSQL**: Full-stack framework with heavy relational database support.

### What the AI Suggested:
The AI suggested Express.js and MongoDB for rapid API prototyping.

### What We Chose and Why:
We chose **FastAPI with SQLite**.
*   **Rationale**: FastAPI is the industry standard for high-performance Python microservices. Its built-in support for ASGI WebSockets allows real-time metric broadcasting, and its automatic Swagger/OpenAPI docs make API testing trivial. SQLite was selected over heavy database servers because it is fully self-contained, runs inside the same container, requires zero environment configuration, and supports transaction locking for safe batch event ingestion.
