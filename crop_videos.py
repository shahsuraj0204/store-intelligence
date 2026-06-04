import cv2
import os

def crop_video(input_path, output_path, max_frames=150, target_width=480, target_height=270):
    print(f"Reading {input_path}...")
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Error opening {input_path}")
        return False
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0
        
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Safe standard codec for web
    out = cv2.VideoWriter(output_path, fourcc, fps, (target_width, target_height))
    
    frame_count = 0
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        # Resize to make it small and fast to load over the web
        resized = cv2.resize(frame, (target_width, target_height))
        out.write(resized)
        frame_count += 1
        
    cap.release()
    out.release()
    print(f"Saved {output_path} with {frame_count} frames.")
    return True

if __name__ == "__main__":
    video_dir = "CCTV Footage"
    output_dir = "dashboard"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for i in range(1, 6):
        input_file = os.path.join(video_dir, f"CAM {i}.mp4")
        output_file = os.path.join(output_dir, f"cam{i}_loop.mp4")
        if os.path.exists(input_file):
            crop_video(input_file, output_file)
        else:
            print(f"Skipping CAM {i} as it is not found.")
