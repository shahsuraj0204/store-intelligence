import argparse
import json
import time
import requests

def emit_events(jsonl_path, host="http://localhost:8000", batch_size=100, simulate=False):
    url = f"{host}/events/ingest"
    print(f"Reading events from {jsonl_path}...")
    
    events = []
    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line.strip()))
    except Exception as e:
        print(f"Failed to read JSONL file: {e}")
        return
        
    total_events = len(events)
    print(f"Loaded {total_events} events. Emission mode: {'Simulated Real-Time' if simulate else 'Batch'}")
    
    if total_events == 0:
        print("No events to emit.")
        return

    if simulate:
        # Stream events in order of their timestamps
        # Determine time scale: check diff between first and last event
        from datetime import datetime
        try:
            first_time = datetime.fromisoformat(events[0]["timestamp"].replace("Z", ""))
            last_time = datetime.fromisoformat(events[-1]["timestamp"].replace("Z", ""))
            total_duration = (last_time - first_time).total_seconds()
            print(f"Events span {total_duration} seconds of video footage.")
        except Exception:
            pass
            
        print("Replaying events to backend in real-time mode...")
        current_batch = []
        for i, event in enumerate(events):
            current_batch.append(event)
            
            # Send batch if it's the last event or if we have a small group
            # (In simulation, we can send events individually or every 1-2 seconds)
            if len(current_batch) >= 5 or i == total_events - 1:
                try:
                    res = requests.post(url, json=current_batch)
                    if res.ok:
                        print(f"Sent simulation batch of {len(current_batch)} events. Response: {res.json()}")
                    else:
                        print(f"Failed to send batch: HTTP {res.status_code}")
                except Exception as e:
                    print(f"Network error in simulation emission: {e}")
                current_batch = []
                
            time.sleep(0.5) # Simulated latency
    else:
        # Standard batch emission
        for i in range(0, total_events, batch_size):
            batch = events[i:i+batch_size]
            print(f"Posting batch of {len(batch)} events to {url}...")
            try:
                res = requests.post(url, json=batch)
                if res.ok:
                    print(f"Successfully ingested batch: {res.json()}")
                else:
                    print(f"Failed to ingest batch: HTTP {res.status_code} - {res.text}")
            except Exception as e:
                print(f"Network error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Purplle Store Intelligence Event Emitter")
    parser.add_argument("--input", default="events_output.jsonl", help="Path to events JSONL file")
    parser.add_argument("--host", default="http://localhost:8000", help="FastAPI Server base URL")
    parser.add_argument("--batch_size", type=int, default=100, help="Ingest batch size")
    parser.add_argument("--simulate", action="store_true", help="Enable simulated real-time replay")
    args = parser.parse_args()
    
    emit_events(
        jsonl_path=args.input,
        host=args.host,
        batch_size=args.batch_size,
        simulate=args.simulate
    )

if __name__ == "__main__":
    main()
