import os
import json
import uuid
import cv2
import argparse
from datetime import datetime, timedelta
from ultralytics import YOLO
from tracker import SpatialTemporalReIDTracker

# Load Store Layout Config
def load_store_layout(layout_path="store_layout.json"):
    if not os.path.exists(layout_path):
        return None
    with open(layout_path, "r") as f:
        return json.load(f)

# Helper to check if point (x, y) is inside polygon
def is_point_in_polygon(x, y, polygon):
    # Simple bounding box check first, then ray casting or basic bounds
    # Since our polygons are rectangular in store_layout.json, a simple bounding check works perfectly:
    # polygon format: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys)

def determine_zone(x, y, camera_config):
    for zone in camera_config.get("coverage_zones", []):
        if is_point_in_polygon(x, y, zone.get("polygon", [])):
            return zone.get("zone_id")
    return None

def process_video_clip(video_path, camera_id, store_id, layout, model, reid_tracker, start_time_str="2026-04-10T12:15:00Z"):
    print(f"Processing clip {video_path} for camera {camera_id}...")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Failed to open video clip {video_path}")
        return []
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
        
    # Get camera zone config
    camera_config = None
    for store in layout.get("stores", []):
        if store.get("store_id") == store_id:
            for cam in store.get("cameras", []):
                if cam.get("camera_id") == camera_id:
                    camera_config = cam
                    break
                    
    if not camera_config:
        print(f"No configuration found for camera {camera_id} in store {store_id}")
        cap.release()
        return []

    # Map start time
    clean_start_time = start_time_str.replace("Z", "")
    start_dt = datetime.fromisoformat(clean_start_time)
    
    events = []
    
    # Tracking state
    visitor_active_zones = {}  # track_id -> current_zone
    visitor_zone_start_times = {}  # track_id -> datetime when entered current_zone
    visitor_first_seen = {}  # track_id -> datetime
    visitor_last_seen = {}  # track_id -> datetime
    visitor_frame_count = {}  # track_id -> count of frames seen
    visitor_sequences = {}  # track_id -> current ordinal sequence number
    
    # Run YOLOv8 Tracking in streaming mode (person detection class is 0)
    results = model.track(source=video_path, classes=[0], tracker="bytetrack.yaml", stream=True, conf=0.25, verbose=False)
    
    frame_idx = 0
    for result in results:
        frame_idx += 1
        # Simulated timestamp based on video frame offset
        frame_offset_seconds = frame_idx / fps
        frame_dt = start_dt + timedelta(seconds=frame_offset_seconds)
        timestamp_str = frame_dt.isoformat() + "Z"
        
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            continue
            
        for box in boxes:
            # Box coords: xyxy
            xyxy = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = xyxy
            # Foot point of person (middle-bottom of bounding box)
            px = int((x1 + x2) / 2)
            py = int(y2)
            
            # Confidence
            conf = float(box.conf[0].cpu().numpy())
            
            # Track ID
            if box.id is None:
                continue
            track_id = int(box.id[0].cpu().numpy())
            # Use spatial-temporal tracker for multi-camera Re-ID stitching
            visitor_token = reid_tracker.get_global_visitor_id(track_id, camera_id, timestamp_str)
            
            # Update seen frames
            visitor_frame_count[visitor_token] = visitor_frame_count.get(visitor_token, 0) + 1
            if visitor_token not in visitor_first_seen:
                visitor_first_seen[visitor_token] = frame_dt
                visitor_sequences[visitor_token] = 1
                
                # Emit ENTRY if it's the entrance camera (CAM_3)
                if camera_id == "CAM_3":
                    events.append({
                        "event_id": str(uuid.uuid4()),
                        "store_id": store_id,
                        "camera_id": camera_id,
                        "visitor_id": visitor_token,
                        "event_type": "ENTRY",
                        "timestamp": timestamp_str,
                        "zone_id": None,
                        "dwell_ms": 0,
                        "is_staff": False,
                        "confidence": round(conf, 2),
                        "metadata": {
                            "queue_depth": None,
                            "sku_zone": None,
                            "session_seq": visitor_sequences[visitor_token]
                        }
                    })
                    visitor_sequences[visitor_token] += 1
                    
            visitor_last_seen[visitor_token] = frame_dt
            
            # Determine Zone
            zone_id = determine_zone(px, py, camera_config)
            
            prev_zone = visitor_active_zones.get(visitor_token)
            
            if zone_id != prev_zone:
                # 1. Handle zone exit if leaving a zone
                if prev_zone:
                    enter_time = visitor_zone_start_times.get(visitor_token, frame_dt)
                    dwell_ms = int((frame_dt - enter_time).total_seconds() * 1000)
                    
                    events.append({
                        "event_id": str(uuid.uuid4()),
                        "store_id": store_id,
                        "camera_id": camera_id,
                        "visitor_id": visitor_token,
                        "event_type": "ZONE_EXIT",
                        "timestamp": timestamp_str,
                        "zone_id": prev_zone,
                        "dwell_ms": dwell_ms,
                        "is_staff": False,
                        "confidence": round(conf, 2),
                        "metadata": {
                            "queue_depth": None,
                            "sku_zone": None,
                            "session_seq": visitor_sequences[visitor_token]
                        }
                    })
                    visitor_sequences[visitor_token] += 1
                
                # 2. Handle zone enter
                visitor_active_zones[visitor_token] = zone_id
                visitor_zone_start_times[visitor_token] = frame_dt
                
                if zone_id:
                    events.append({
                        "event_id": str(uuid.uuid4()),
                        "store_id": store_id,
                        "camera_id": camera_id,
                        "visitor_id": visitor_token,
                        "event_type": "ZONE_ENTER",
                        "timestamp": timestamp_str,
                        "zone_id": zone_id,
                        "dwell_ms": 0,
                        "is_staff": False,
                        "confidence": round(conf, 2),
                        "metadata": {
                            "queue_depth": None,
                            "sku_zone": None,
                            "session_seq": visitor_sequences[visitor_token]
                        }
                    })
                    visitor_sequences[visitor_token] += 1
                    
                    # Special: Join queue if entering Billing queue
                    if zone_id == "BILLING":
                        # Compute active queue depth (simulated or count active IDs in zone)
                        active_billing_count = sum(1 for v, z in visitor_active_zones.items() if z == "BILLING")
                        events.append({
                            "event_id": str(uuid.uuid4()),
                            "store_id": store_id,
                            "camera_id": camera_id,
                            "visitor_id": visitor_token,
                            "event_type": "BILLING_QUEUE_JOIN",
                            "timestamp": timestamp_str,
                            "zone_id": "BILLING",
                            "dwell_ms": 0,
                            "is_staff": False,
                            "confidence": round(conf, 2),
                            "metadata": {
                                "queue_depth": active_billing_count,
                                "sku_zone": None,
                                "session_seq": visitor_sequences[visitor_token]
                            }
                        })
                        visitor_sequences[visitor_token] += 1
            
            else:
                # 3. Handle ZONE_DWELL: if they have been in the zone for 30s since last entry/dwell
                if zone_id:
                    last_dwell_dt = visitor_zone_start_times.get(visitor_token, frame_dt)
                    elapsed = (frame_dt - last_dwell_dt).total_seconds()
                    
                    # Emit every 30s of continued dwell
                    if elapsed >= 30.0:
                        visitor_zone_start_times[visitor_token] = frame_dt  # Reset dwell start
                        
                        sku_label = None
                        if zone_id == "SKINCARE": sku_label = "MOISTURISER"
                        elif zone_id == "MAKEUP": sku_label = "LIPSTICK"
                        elif zone_id == "HAIRCARE": sku_label = "SHAMPOO"
                        elif zone_id == "FRAGRANCE": sku_label = "PERFUME"
                        
                        events.append({
                            "event_id": str(uuid.uuid4()),
                            "store_id": store_id,
                            "camera_id": camera_id,
                            "visitor_id": visitor_token,
                            "event_type": "ZONE_DWELL",
                            "timestamp": timestamp_str,
                            "zone_id": zone_id,
                            "dwell_ms": int(elapsed * 1000),
                            "is_staff": False,
                            "confidence": round(conf, 2),
                            "metadata": {
                                "queue_depth": None,
                                "sku_zone": sku_label,
                                "session_seq": visitor_sequences[visitor_token]
                            }
                        })
                        visitor_sequences[visitor_token] += 1

    # End of video: emit EXIT for active sessions
    for visitor_token, current_zone in visitor_active_zones.items():
        visitor_last = visitor_last_seen.get(visitor_token, start_dt)
        timestamp_exit_str = visitor_last.isoformat() + "Z"
        
        # ZONE_EXIT
        if current_zone:
            enter_time = visitor_zone_start_times.get(visitor_token, start_dt)
            dwell_ms = int((visitor_last - enter_time).total_seconds() * 1000)
            events.append({
                "event_id": str(uuid.uuid4()),
                "store_id": store_id,
                "camera_id": camera_id,
                "visitor_id": visitor_token,
                "event_type": "ZONE_EXIT",
                "timestamp": timestamp_exit_str,
                "zone_id": current_zone,
                "dwell_ms": dwell_ms,
                "is_staff": False,
                "confidence": 1.0,
                "metadata": {
                    "queue_depth": None,
                    "sku_zone": None,
                    "session_seq": visitor_sequences[visitor_token]
                }
            })
            visitor_sequences[visitor_token] += 1
            
        # EXIT if entrance cam
        if camera_id == "CAM_3":
            events.append({
                "event_id": str(uuid.uuid4()),
                "store_id": store_id,
                "camera_id": camera_id,
                "visitor_id": visitor_token,
                "event_type": "EXIT",
                "timestamp": timestamp_exit_str,
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 1.0,
                "metadata": {
                    "queue_depth": None,
                    "sku_zone": None,
                    "session_seq": visitor_sequences[visitor_token]
                }
            })
            
    # Classify Staff: If an ID was present for a very high fraction of frames (e.g. they spend >90% of the entire video in the frames), 
    # flag their events as is_staff=True.
    total_frames = frame_idx if frame_idx > 0 else 1
    staff_visitors = set()
    for token, count in visitor_frame_count.items():
        # If seen in more than 60% of total video frames, they are staff members
        if (count / total_frames) >= 0.60:
            staff_visitors.add(token)
            
    # Modify events to set is_staff=True for staff
    for event in events:
        if event["visitor_id"] in staff_visitors:
            event["is_staff"] = True
            
    cap.release()
    print(f"Processed camera {camera_id}: generated {len(events)} events (Staff identified: {len(staff_visitors)}).")
    return events

def main():
    parser = argparse.ArgumentParser(description="Purplle Store Intelligence Video Detection Pipeline")
    parser.add_argument("--video_dir", default="CCTV Footage", help="Directory containing the camera clips")
    parser.add_argument("--store_id", default="ST1008", help="Active store ID")
    parser.add_argument("--output", default="events_output.jsonl", help="Output file path")
    args = parser.parse_args()
    
    layout = load_store_layout()
    if not layout:
        print("Failed to load store_layout.json layout configuration.")
        return
        
    print("Loading YOLOv8 tracking model...")
    model = YOLO("yolov8n.pt")
    
    # Initialize Re-ID spatial-temporal tracker
    reid_tracker = SpatialTemporalReIDTracker()
    
    all_events = []
    
    # Process cameras CAM 1 to 5
    for i in range(1, 6):
        video_file = os.path.join(args.video_dir, f"CAM {i}.mp4")
        if os.path.exists(video_file):
            cam_events = process_video_clip(
                video_path=video_file,
                camera_id=f"CAM_{i}",
                store_id=args.store_id,
                layout=layout,
                model=model,
                reid_tracker=reid_tracker
            )
            all_events.extend(cam_events)
        else:
            print(f"Video file {video_file} not found.")
            
    # Sort events by timestamp so they flow in order
    all_events.sort(key=lambda x: x["timestamp"])
    
    # Write to output file
    with open(args.output, "w") as f:
        for event in all_events:
            f.write(json.dumps(event) + "\n")
            
    print(f"Success! Generated {len(all_events)} events total, written to {args.output}.")

if __name__ == "__main__":
    main()
