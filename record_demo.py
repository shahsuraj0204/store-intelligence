import os
import time
import sqlite3
import webbrowser
import subprocess
import numpy as np
import cv2
import mss
import pyautogui
import asyncio
import edge_tts

# Database clear
def clear_db():
    print("Clearing database events & anomalies to start simulation from scratch...")
    db_path = "store_intelligence.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM anomalies")
            conn.commit()
            print("Database cleared successfully.")
        except Exception as e:
            print(f"Error clearing database: {e}")
        finally:
            conn.close()

# Synthesize all speech segment audio clips using Microsoft Edge Neural TTS
async def generate_speech_tracks_async():
    print("Synthesizing voiceover narration tracks using Edge Neural TTS...")
    temp_dir = "temp_speech"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    VOICE_SEGMENTS = [
        # Slides Deck (0s - 15s)
        ("seg_0.mp3", "Welcome to Apex Retail. This is Shah's Team presenting our store intelligence solution for the Purplle Tech Challenge."),
        ("seg_1.mp3", "Brick-and-mortar retail stores suffer from blind spots in shopper pathways, checkout queue abandonment, and static product layouts."),
        ("seg_2.mp3", "Apex Retail bridges these gaps by combining real-time computer vision streams with point-of-sale transactions into a single intelligence desk."),
        
        # Live Monitor (15s - 25s)
        ("seg_3.mp3", "We are now loading the Live Monitor Desk, which tracks real-time traffic statistics. The KPI deck displays unique visitors, conversion rate, checkout queue depths, and cart abandonment rates instantly, helping managers detect checkout delays immediately."),
        
        # Funnel Analysis (25s - 35s)
        ("seg_4.mp3", "Scrolling down, the customer conversion funnel visualizes step-by-step shopper drop-offs from store entrance, browsing zones, queue joins, to checkout completion. This pinpoints customer dropoff friction zones."),
        
        # Heatmap (35s - 45s)
        ("seg_5.mp3", "Next, the product zone heatmap maps spatial dwell times and visit frequencies across Skincare, Makeup, Haircare, and Fragrance aisles, helping managers optimize shelf layout designs based on actual shopper interest."),
        
        # Shopper Journeys (45s - 65s)
        ("seg_6.mp3", "Here, the Shopper Journey Re-ID Tracker groups multi-camera sequences into continuous visitor timelines. We select a visitor to map their exact physical timeline path from entrance, browsing shelves, checking out, to exit."),
        
        # Layout Optimization (65s - 80s)
        ("seg_7.mp3", "The Layout Placement Optimizer mines POS transaction baskets and correlates buy-together strengths with physical aisle traffic, automatically calculating placement efficiency and recommending layout improvements."),
        
        # Copilot & Alerts (80s - 95s)
        ("seg_8.mp3", "At the top right, our AI Operations Copilot processes real-time telemetry to generate automated staffing alerts, while the Security Anomalies Desk flags restricted office breaches or queue spills visually and audibly."),
        
        # Wrap up (95s - 105s)
        ("seg_9.mp3", "Apex Retail optimizes brick-and-mortar store operations dynamically. Thank you for your time.")
    ]
    
    # en-US-AndrewNeural is an extremely realistic, clear human-like male voice
    voice = "en-US-AndrewNeural"
    
    for filename, text in VOICE_SEGMENTS:
        filepath = os.path.join(temp_dir, filename)
        print(f"Generating neural voice: {filepath}")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filepath)
        
    print("All narration clips synthesized.")

def generate_speech_tracks():
    asyncio.run(generate_speech_tracks_async())

# Recording screens to silent MP4 video
def record_screen(output_video_path, duration_seconds=60, fps=10):
    with mss.mss() as sct:
        # Get primary monitor size
        monitor = sct.monitors[1]
        width = monitor['width']
        height = monitor['height']
        
        # Configure OpenCV VideoWriter (MP4V Codec)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        
        print(f"Recording primary screen at {width}x{height}, {fps} FPS...")
        start_time = time.time()
        frame_interval = 1.0 / fps
        frames_recorded = 0
        
        # Press F11 for Full Screen view
        print("Toggling full screen browser layout...")
        time.sleep(1)
        pyautogui.press('f11')
        time.sleep(2)  # Wait for transition
        
        try:
            while time.time() - start_time < duration_seconds:
                loop_start = time.time()
                
                # Capture frame
                img = np.array(sct.grab(monitor))
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                out.write(frame)
                frames_recorded += 1
                
                # Regulate frame rate delay
                elapsed = time.time() - loop_start
                wait_time = frame_interval - elapsed
                if wait_time > 0:
                    time.sleep(wait_time)
        finally:
            out.release()
            print("Exiting full screen view...")
            pyautogui.press('f11')
            print(f"Captured {frames_recorded} frames in {time.time() - start_time:.2f} seconds.")

# Stitch silent video and delayed voice clips using FFmpeg
def stitch_video_audio(silent_video, output_video):
    print("Stitching silent video and neural voice segments using FFmpeg...")
    
    # FFmpeg command structure
    cmd = [
        "ffmpeg", "-y",
        "-i", silent_video,
        "-i", "temp_speech/seg_0.mp3",
        "-i", "temp_speech/seg_1.mp3",
        "-i", "temp_speech/seg_2.mp3",
        "-i", "temp_speech/seg_3.mp3",
        "-i", "temp_speech/seg_4.mp3",
        "-i", "temp_speech/seg_5.mp3",
        "-i", "temp_speech/seg_6.mp3",
        "-i", "temp_speech/seg_7.mp3",
        "-i", "temp_speech/seg_8.mp3",
        "-i", "temp_speech/seg_9.mp3",
        "-filter_complex", 
        "[1:a]adelay=0|0[a0];"
        "[2:a]adelay=5000|5000[a1];"
        "[3:a]adelay=10000|10000[a2];"
        "[4:a]adelay=15000|15000[a3];"
        "[5:a]adelay=25000|25000[a4];"
        "[6:a]adelay=35000|35000[a5];"
        "[7:a]adelay=45000|45000[a6];"
        "[8:a]adelay=65000|65000[a7];"
        "[9:a]adelay=80000|80000[a8];"
        "[10:a]adelay=95000|95000[a9];"
        "[a0][a1][a2][a3][a4][a5][a6][a7][a8][a9]amix=inputs=10[outa]",
        "-map", "0:v",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_video
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Video production complete: {output_video}")
    except subprocess.CalledProcessError as e:
        print(f"Error compiling video with FFmpeg: {e}")

# Clean up temp speech folder
def cleanup():
    print("Cleaning up temporary audio assets...")
    temp_dir = "temp_speech"
    if os.path.exists(temp_dir):
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)
    if os.path.exists("silent_temp.mp4"):
        os.remove("silent_temp.mp4")
    print("Cleanup complete.")

if __name__ == "__main__":
    clear_db()
    generate_speech_tracks()
    
    # Open dashboard with ?autodemo=true
    print("Launching browser with autodemo link...")
    webbrowser.open("http://localhost:8000/dashboard/?autodemo=true")
    
    # Wait for page to initialize and browser window to focus
    time.sleep(3)
    
    # Record screen (105 seconds captures slides + comprehensive dashboard tour + alerts)
    record_screen("silent_temp.mp4", duration_seconds=105, fps=10)
    
    # Stitch video and audio
    stitch_video_audio("silent_temp.mp4", "purplle_tech_challenge_demo.mp4")
    
    # Cleanup temp folders
    cleanup()
    print("Process complete! Open purplle_tech_challenge_demo.mp4 to review your pitch video.")
