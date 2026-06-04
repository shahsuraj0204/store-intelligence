#!/bin/bash
# Purplle Tech Challenge 2026 - Detection Pipeline Runner
# Usage: ./pipeline/run.sh [video_dir] [store_id] [api_host]

VIDEO_DIR=${1:-"CCTV Footage"}
STORE_ID=${2:-"ST1008"}
API_HOST=${3:-"http://localhost:8000"}
OUTPUT_FILE="events_output.jsonl"

echo "=== Starting Store Intelligence Detection Pipeline ==="
echo "Video Directory: $VIDEO_DIR"
echo "Store ID: $STORE_ID"
echo "API Host: $API_HOST"

# 1. Run YOLOv8 Tracking & Zone Mapping
python pipeline/detect.py --video_dir "$VIDEO_DIR" --store_id "$STORE_ID" --output "$OUTPUT_FILE"

# 2. Emit events to FastAPI endpoint
python pipeline/emit.py --input "$OUTPUT_FILE" --host "$API_HOST"

echo "=== Pipeline Processing Complete ==="
