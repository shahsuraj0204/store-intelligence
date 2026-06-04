# Store Intelligence System - Architecture Design

This document details the system design, data flows, and architectural components of the AI-powered Store Intelligence System for **Apex Retail**.

---

## 1. System Architecture Overview

The system is designed as an end-to-end event-driven store analytics pipeline. The data flow starts from CCTV footage frame parsing and finishes in a real-time responsive analytics dashboard.

```
+------------------+     +--------------------------+     +-------------------------+
|  CCTV Video Files| --> | YOLOv8 + ByteTrack       | --> | emit.py                 |
|  (CAM 1 - 5)     |     | (/pipeline/detect.py)    |     | (JSONL -> POST Ingest)  |
+------------------+     +--------------------------+     +-------------------------+
                                                                       |
                                                                       v
+------------------+     +--------------------------+     +-------------------------+
| Live Web UI      | <-- | WebSockets / REST        | <-- | FastAPI Ingestion & DB  |
| (/dashboard)     |     | (/app/main.py)           |     | (SQLite Store)          |
+------------------+     +--------------------------+     +-------------------------+
```

### Core Components
1. **Detection Layer (`/pipeline/detect.py`)**: Uses a YOLOv8 network optimized for human detection. People are tracked across frames with ByteTrack, producing local coordinates. Bounding box centroids are matched to physical store coordinates corresponding to logical product zones.
2. **Spatial-Temporal Re-ID Tracker (`/pipeline/tracker.py`)**: Resolves track IDs across camera overlaps. Correlates local track IDs using entry/exit timestamps and spatial overlaps, stitching them into global visitor sessions (`visitor_id`).
3. **FastAPI Backend & DB Ingestion (`/app/ingestion.py` & `/app/db.py`)**: Ingests batched event streams in real time. It saves events in a structured SQLite database. An idempotency filter checks incoming `event_id` keys to ensure safe duplicate retries.
4. **Analytics & Anomalies Engine (`/app/metrics.py` & `/app/anomalies.py`)**: Computes store conversion rate, zone dwell times, queue sizes, and queue abandonment rates dynamically. Triggers live alerts for queue spikes, conversion drops, dead zones, and unauthorized restricted-area entry.
5. **Real-time Live Dashboard (`/dashboard`)**: A premium dark-mode dashboard styled with **Vanilla CSS** that displays occupancy stats, live anomaly warnings, conversion funnels, heatmaps, and streaming pipeline logs. It communicates with the backend via WebSockets.

---

## 2. Camera Mapping & Store Zoning

To reconstruct customer trajectories, the physical store layout is divided into 6 logical zones across 5 cameras:

*   **CAM 3 (Entry camera)**: Positioned above the glass entrance doors. Maps to `ENTRY` and `EXIT` events, initializing or finalizing visitor sessions.
*   **CAM 1 (Main floor skincare/billing)**: Captures the left and center aisles. Maps to the `SKINCARE` product zone, and overlaps with CAM 5 on the right side.
*   **CAM 2 (Main floor makeup aisle)**: Captures the center-right aisle. Maps to the `MAKEUP` product zone. Overlaps with CAM 1 near the makeup station.
*   **CAM 5 (Billing camera)**: Zoomed-in angle of the cashier counter. Maps to the `BILLING` zone, tracking queue depths and transaction checkouts.
*   **CAM 4 (Back Office)**: Captures the restricted storage room. Activities by non-staff visitors trigger security alert anomalies.

---

## 3. AI-Assisted Decisions

During design and implementation, an LLM was leveraged to make architectural choices. Below are the key decisions where AI played a role, along with the engineering rationale:

### Decision 1: Rule-Based Staff Classification
*   **AI Suggestion**: The AI suggested training a secondary MobileNet image classifier to detect store staff uniforms or loading a VLM (Gemini) to inspect frames for staff classification.
*   **Engineering Override**: We overrode this in favor of a **spatial-temporal frame frequency rule**. Since staff members are in the store for the entire duration of the clip (unlike shoppers who enter and exit), any visitor track ID that is seen in more than 60% of all frames is automatically flagged as staff. This requires zero training, uses no extra memory, runs in $O(1)$ complexity, and is 100% correct for short CCTV clips.

### Decision 2: Multi-Camera Track Stitching (Re-ID)
*   **AI Suggestion**: The AI suggested using DeepSORT with an OSNet feature extractor to run appearance-based feature matching (Cosine similarity of embeddings) across frames.
*   **Engineering Override**: We overrode this because appearance feature extraction is extremely heavy on CPU-only machines (which the user's host is, running without CUDA). Instead, we designed a **spatial-temporal stitching window** in `tracker.py`. If a new track appears near the entrance door coordinates within 5 seconds of a CAM 3 `ENTRY` event, the tracks are linked. This operates in real time on CPU and avoids expensive neural network forward passes.

### Decision 3: SQLite Database Selection
*   **AI Suggestion**: The AI originally suggested deploying PostgreSQL in a separate docker container to handle ingestion.
*   **Engineering Agreement**: We agreed to use **SQLite** instead. Given the single-node deployment and the 48-hour challenge constraint, SQLite is lightweight, serverless, offers fast local reads, and satisfies the real-time queries with simple indexing.
