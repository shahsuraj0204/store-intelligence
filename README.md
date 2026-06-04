# Store Intelligence System (Apex Retail)

This repository contains the AI-powered Store Intelligence System built for the Purplle Tech Challenge 2026. It combines a computer vision tracking pipeline, real-time analytics REST & WebSocket API, and an interactive live dashboard.

---

## Quick Setup (5 Commands)

Process from cloning to running in exactly 5 steps:

```bash
# 1. Clone the repository and navigate inside
git clone <repo_url> && cd store-intelligence

# 2. Start the FastAPI backend and live dashboard containers
docker compose up -d --build

# 3. Initialize Python dependencies for local testing
pip install -r requirements.txt

# 4. Run the computer vision detection & tracking pipeline against the CCTV footage
./pipeline/run.sh

# 5. Run the automated test suite
pytest tests/ -v
```

---

## Services & Ports

*   **Live Dashboard Web Surface**: Available at [http://localhost:8000/dashboard](http://localhost:8000/dashboard) (or redirects from [http://localhost:8000](http://localhost:8000)).
*   **FastAPI REST endpoints**: Exposed at `http://localhost:8000/docs` (Swagger UI).
*   **Real-time WebSocket stream**: Available at `ws://localhost:8000/events/stream`.

---

## Ingesting & Simulating Data

### Running the Batch Pipeline
To process the video clips and automatically ingest the behavioral events to the REST API, execute:
```bash
./pipeline/run.sh
```

### Running Simulated Live Demo
If CUDA is unavailable on your machine, running YOLOv8 tracking on CPU may take several minutes. To view the dashboard's live streaming, charts, and anomaly alerts instantly:
1. Open the Live Dashboard at `http://localhost:8000`
2. Click the **"Run Simulation"** button in the top right corner.
3. This triggers a mock real-time replay event stream directly into the API, showing WebSockets and visual cards updating live!
