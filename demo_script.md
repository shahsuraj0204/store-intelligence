# Apex Retail - Technical Demo Script

This script is structured for a **1.5 to 2-minute live technical demo** where you showcase the command-line pipeline, backend APIs, and the test suite.

---

### Part 1: Automated Test Suite (Validation)
* **Duration**: ~20-30 seconds
* **Visual Action**: Open your terminal (PowerShell or Command Prompt) and run the pytest suite:
  ```powershell
  pytest tests/ -v
  ```
* **What to Say**:
  > "To guarantee correctness and prevent regression, I built a comprehensive test suite. 
  > Here, I am running `pytest` against my test suite. 
  > You can see that all tests—covering multi-camera pipeline outputs, metric aggregations, and my rule-based anomaly engine—pass successfully. 
  > This confirms the backend calculations are production-ready."

---

### Part 2: Interactive API Documentation (FastAPI Swagger)
* **Duration**: ~20-30 seconds
* **Visual Action**: Switch to browser and open `http://localhost:8000/docs` (Swagger UI). Scroll through the endpoints (`/events/ingest`, `/stores/{id}/metrics`, `/stores/{id}/anomalies`, `/stores/{id}/placement-optimization`).
* **What to Say**:
  > "Next, let's look at the API layer. The FastAPI backend automatically generates interactive Swagger documentation. 
  > Operators can test and integrate all critical routes here—including real-time metrics, funnel drop-off sequences, anomalies, and layout placements. 
  > The WebSocket feed is also exposed at `/events/stream` for continuous event pushes."

---

### Part 3: Running the Edge Computer Vision Ingestion Pipeline
* **Duration**: ~40-50 seconds
* **Visual Action**: 
  1. Open terminal and start the YOLOv8 pipeline against the CCTV footage:
     ```powershell
     python pipeline/detect.py --video_dir "CCTV Footage" --store_id "ST1008" --output "events_output.jsonl"
     ```
  2. Explain that the detector tracks individuals and maps them to zones. 
  3. Once generated, run the event emitter:
     ```powershell
     python pipeline/emit.py --input "events_output.jsonl" --host "http://127.0.0.1:8000"
     ```
* **What to Say**:
  > "Now, let's run the actual computer vision tracking pipeline. 
  > I am running `detect.py` against the raw CCTV videos. The script loads my YOLOv8 model, processes frames, applies ByteTrack for identity tracking, and projects centroid coordinates into store layouts to generate state-change events.
  > 
  > Once processed, I use `emit.py` to stream this data. Watch the terminal as it reads the generated JSONL file and posts batches of events directly to my running FastAPI backend. 
  > These events immediately update the database and broadcast to my live dashboard over WebSockets."

---

### Part 4: Technical Summary & Outro
* **Duration**: ~15 seconds
* **Visual Action**: Switch back to the dashboard to show the fresh events listed in the "Real-time Pipeline Feed".
* **What to Say**:
  > "As you can see, the live monitor instantly captures the pipeline ingestion. 
  > I have a fully validated, end-to-end telemetry system running seamlessly on standard hardware. 
  > Thanks for watching the technical demonstration."
