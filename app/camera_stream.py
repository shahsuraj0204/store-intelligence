import os
import cv2
import json
import time
import math
import numpy as np
from datetime import datetime
from ultralytics import YOLO

# Pre-load YOLOv8 model globally to avoid loading it on-demand for every request/tab switch
yolo_model = None
try:
    yolo_model = YOLO("yolov8n.pt")
except Exception:
    pass


# Load Store Layout Config for drawing boundaries
def get_store_camera_polygons(store_id, camera_id):
    layout_path = "store_layout.json"
    if not os.path.exists(layout_path):
        return []
        
    try:
        with open(layout_path, "r") as f:
            layout = json.load(f)
            
        for store in layout.get("stores", []):
            if store.get("store_id") == store_id:
                for cam in store.get("cameras", []):
                    if cam.get("camera_id") == camera_id:
                        return cam.get("coverage_zones", [])
    except Exception:
        pass
    return []

# Synthetic camera stream generator (Fallback when MP4 is missing or CPU runs slow)
def generate_synthetic_cctv_frame(store_id, camera_id, frame_idx):
    # 640x360 base frame
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    # Dark blue premium background
    frame[:] = (20, 15, 10)
    
    # Draw floor plan grids
    for i in range(0, 640, 40):
        cv2.line(frame, (i, 0), (i, 360), (30, 25, 15), 1)
    for i in range(0, 360, 40):
        cv2.line(frame, (0, i), (640, i), (30, 25, 15), 1)
        
    # Draw title
    cv2.putText(frame, f"CCTV [{camera_id}] - SIMULATED CORRELATION FEED", (15, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (167, 139, 250), 1, cv2.LINE_AA)
                
    # Draw timestamp
    time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    cv2.putText(frame, time_str, (430, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (156, 163, 175), 1, cv2.LINE_AA)
                
    # Draw zones boundaries (scaled down 1920x1080 -> 640x360 by dividing by 3)
    zones = get_store_camera_polygons(store_id, camera_id)
    for zone in zones:
        zone_id = zone.get("zone_id")
        polygon = zone.get("polygon", [])
        
        # Scale polygon coordinates
        pts = np.array([[int(p[0]/3), int(p[1]/3)] for p in polygon], np.int32)
        pts = pts.reshape((-1, 1, 2))
        
        # Determine color
        color = (130, 80, 50)
        if zone_id == "SKINCARE": color = (246, 130, 59) # Blue
        elif zone_id == "MAKEUP": color = (250, 139, 167) # Purple
        elif zone_id == "BILLING": color = (182, 114, 244) # Pink
        elif zone_id == "BACK_OFFICE": color = (68, 68, 239) # Red
        
        cv2.polylines(frame, [pts], True, color, 1)
        
        # Draw label
        if len(polygon) > 0:
            cx = int(sum(p[0]/3 for p in polygon) / len(polygon))
            cy = int(sum(p[1]/3 for p in polygon) / len(polygon))
            cv2.putText(frame, zone_id, (cx - 30, cy), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

    # Animate moving visitors (moving circles with bounding boxes)
    t = frame_idx * 0.05
    
    # Sim visitor 1 (skincare / Floor)
    if camera_id in ["CAM_1", "CAM_2"]:
        v1_x = int(320 + math.cos(t) * 120)
        v1_y = int(180 + math.sin(t) * 60)
        
        # Draw bounding box
        cv2.rectangle(frame, (v1_x - 20, v1_y - 45), (v1_x + 20, v1_y + 45), (250, 139, 167), 1)
        # Dot/Target
        cv2.circle(frame, (v1_x, v1_y), 4, (250, 139, 167), -1)
        # Label
        cv2.putText(frame, "VIS_GLB_1021", (v1_x - 20, v1_y - 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (250, 139, 167), 1, cv2.LINE_AA)
                    
    # Sim visitor 2 (billing)
    if camera_id in ["CAM_1", "CAM_5"]:
        v2_x = int(450 + math.sin(t * 0.3) * 30)
        v2_y = int(220 + math.cos(t * 0.3) * 15)
        
        # Draw bounding box
        cv2.rectangle(frame, (v2_x - 18, v2_y - 40), (v2_x + 18, v2_y + 40), (182, 114, 244), 1)
        cv2.circle(frame, (v2_x, v2_y), 4, (182, 114, 244), -1)
        cv2.putText(frame, "VIS_GLB_1025", (v2_x - 18, v2_y - 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (182, 114, 244), 1, cv2.LINE_AA)

    # Return JPEG bytes
    ret, jpeg = cv2.imencode('.jpg', frame)
    return jpeg.tobytes()

# Stream processor using OpenCV and YOLOv8
def get_camera_stream_generator(store_id, camera_id):
    # Determine video file path based on mapping
    # Camera mapping: CAM_1 -> CAM 1.mp4, etc.
    cam_num = camera_id.split("_")[1] if "_" in camera_id else "1"
    video_path = os.path.join("CCTV Footage", f"CAM {cam_num}.mp4")
    
    model = yolo_model

    # Check device type to dynamically adjust skip frame interval
    import torch
    is_gpu = torch.cuda.is_available()
    skip_interval = 1 if is_gpu else 12  # Run YOLO inference every 12 frames on CPU, every frame on GPU
    cached_boxes = []

    # Read layout polygons
    zones = get_store_camera_polygons(store_id, camera_id)
    
    cap = None
    if os.path.exists(video_path):
        cap = cv2.VideoCapture(video_path)
        
    frame_idx = 0
    
    try:
        while True:
            frame_idx += 1
            
            # If video is missing or uvicorn lacks OpenCV video reading, stream synthetic frame
            if not cap or not cap.isOpened() or not model:
                jpeg_bytes = generate_synthetic_cctv_frame(store_id, camera_id, frame_idx)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
                time.sleep(0.04) # Simulate 25 FPS
                continue
                
            ret, frame = cap.read()
            if not ret:
                # Video ended, loop back to start
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
                
            # Resize frame to 640x360 for high performance CPU tracking
            frame = cv2.resize(frame, (640, 360))
            
            # Draw store zone polygons
            for zone in zones:
                zone_id = zone.get("zone_id")
                polygon = zone.get("polygon", [])
                
                # Scale polygon coordinates from 1920x1080 -> 640x360
                pts = np.array([[int(p[0]/3), int(p[1]/3)] for p in polygon], np.int32)
                pts = pts.reshape((-1, 1, 2))
                
                # Choose color
                color = (255, 255, 255)
                if zone_id == "SKINCARE": color = (246, 130, 59) # Blue
                elif zone_id == "MAKEUP": color = (250, 139, 167) # Purple
                elif zone_id == "BILLING": color = (182, 114, 244) # Pink
                elif zone_id == "BACK_OFFICE": color = (68, 68, 239) # Red
                
                cv2.polylines(frame, [pts], True, color, 1)
                
            # Run YOLO tracker at interval, or draw cached boxes
            if frame_idx % skip_interval == 1 or not cached_boxes:
                results = model.track(frame, classes=[0], tracker="bytetrack.yaml", persist=True, verbose=False)
                new_boxes = []
                if len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes
                    for box in boxes:
                        if box.id is not None:
                            xyxy = box.xyxy[0].cpu().numpy()
                            track_id = int(box.id[0].cpu().numpy())
                            new_boxes.append((xyxy, track_id))
                cached_boxes = new_boxes
            
            # Draw bounding boxes (from cache or new inference)
            for xyxy, track_id in cached_boxes:
                x1, y1, x2, y2 = map(int, xyxy)
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (167, 139, 250), 1)
                # Draw Label
                label = f"VIS_{camera_id}_{track_id}"
                cv2.putText(frame, label, (x1, y1 - 8), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (167, 139, 250), 1, cv2.LINE_AA)
            
            # Encode frame to JPEG
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                       
            # Throttling to simulate realistic camera feed rate
            # If running on CPU, model inference takes time, so reduce sleep time
            sleep_time = 0.04 / skip_interval if is_gpu else 0.005
            time.sleep(sleep_time)
            
    except Exception as e:
        # Release capture resources
        if cap:
            cap.release()
        raise e
    finally:
        if cap:
            cap.release()
