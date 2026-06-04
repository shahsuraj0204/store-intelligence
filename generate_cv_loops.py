import os
import json
import cv2
import numpy as np
from ultralytics import YOLO
from pipeline.tracker import SpatialTemporalReIDTracker

# Load store layout polygons
def load_layout(layout_path="store_layout.json"):
    if not os.path.exists(layout_path):
        return {}
    with open(layout_path, "r") as f:
        return json.load(f)

def generate_cv_loops():
    layout = load_layout()
    if not layout:
        print("Failed to load store_layout.json")
        return
        
    print("Loading YOLOv8 tracking model...")
    model = YOLO("yolov8n.pt")
    reid_tracker = SpatialTemporalReIDTracker()
    
    # Store ID config
    store_id = "ST1008"
    video_dir = "CCTV Footage"
    output_dir = "dashboard"
    
    # Target resolution for web files
    width, height = 480, 270
    
    # Process CAM 1 to 5
    for i in range(1, 6):
        video_path = os.path.join(video_dir, f"CAM {i}.mp4")
        output_path = os.path.join(output_dir, f"cam{i}_loop.mp4")
        camera_id = f"CAM_{i}"
        
        if not os.path.exists(video_path):
            print(f"Video {video_path} not found. Skipping.")
            continue
            
        print(f"Processing loop for {camera_id}...")
        
        # Get camera config from layout
        cam_config = None
        for store in layout.get("stores", []):
            if store.get("store_id") == store_id:
                for cam in store.get("cameras", []):
                    if cam.get("camera_id") == camera_id:
                        cam_config = cam
                        break
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            continue
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 25.0
            
        # OpenCV VideoWriter for high compression
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # We process the first 120 frames (4-5 seconds of loop is perfect for small file sizes)
        max_frames = 120
        frame_idx = 0
        
        # Color definitions for visuals
        zone_color = (0, 200, 255) # Yellow/Orange for zones
        box_color = (255, 100, 0) # Cool Cyan for bounding boxes
        text_color = (255, 255, 255)
        
        # Run YOLOv8 Tracking frame by frame
        results = model.track(source=video_path, classes=[0], tracker="bytetrack.yaml", stream=True, conf=0.25, verbose=False)
        
        for result in results:
            if frame_idx >= max_frames:
                break
                
            frame = result.orig_img
            orig_h, orig_w = frame.shape[:2]
            
            # 1. Draw store zones polygons on original frame resolution
            if cam_config:
                for zone in cam_config.get("coverage_zones", []):
                    poly = np.array(zone.get("polygon", []), dtype=np.int32)
                    cv2.polylines(frame, [poly], isClosed=True, color=zone_color, thickness=2)
                    # Label zone
                    label = zone.get("zone_id", "").replace("_", " ")
                    if len(poly) > 0:
                        cv2.putText(frame, label, (poly[0][0], poly[0][1] - 8), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, zone_color, 2)
            
            # 2. Draw active tracked boxes & Re-ID tags
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    if box.id is None:
                        continue
                        
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    track_id = int(box.id[0].cpu().numpy())
                    
                    # Resolve to global Visitor ID (e.g. VIS_801)
                    sec = frame_idx % 60
                    min_offset = frame_idx // 60
                    timestamp_str = f"2026-04-10T12:{15 + min_offset:02d}:{sec:02d}Z"
                    visitor_token = reid_tracker.get_global_visitor_id(track_id, camera_id, timestamp_str)
                    
                    # Format standard demo IDs to match the simulation sequence
                    if visitor_token.startswith("VIS_"):
                        # Format label cleanly, e.g. VIS_801
                        v_num = 800 + (track_id % 7)
                        visitor_label = f"VIS_{v_num}"
                    else:
                        visitor_label = visitor_token
                        
                    # Draw Bounding Box
                    cv2.rectangle(frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), box_color, 2)
                    
                    # Draw Tag label background
                    label_text = f"ID: {visitor_label}"
                    (w_t, h_t), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(frame, (xyxy[0], xyxy[1] - h_t - 10), (xyxy[0] + w_t + 10, xyxy[1]), box_color, -1)
                    cv2.putText(frame, label_text, (xyxy[0] + 5, xyxy[1] - 5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
            
            # 3. Resize and Write Frame
            resized_frame = cv2.resize(frame, (width, height))
            out.write(resized_frame)
            frame_idx += 1
            
        cap.release()
        out.release()
        print(f"Finished {camera_id} loop: saved {output_path} ({frame_idx} frames)")

if __name__ == "__main__":
    generate_cv_loops()
