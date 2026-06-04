import time
import webbrowser
import pyautogui

def capture_dashboard_screenshot():
    print("Launching browser to capture dashboard screenshot...")
    # Open localhost dashboard
    webbrowser.open("http://localhost:8000/dashboard")
    
    # Wait for the page to load and render completely
    time.sleep(5)
    
    # Press F11 to make it full screen for a clean preview image
    print("Toggling full screen...")
    pyautogui.press("f11")
    time.sleep(2)
    
    # Capture the screen
    print("Taking screenshot...")
    screenshot = pyautogui.screenshot()
    
    # Save the screenshot
    output_path = "dashboard_preview.png"
    screenshot.save(output_path)
    print(f"Screenshot saved successfully to {output_path}")
    
    # Exit full screen
    print("Exiting full screen...")
    pyautogui.press("f11")

if __name__ == "__main__":
    capture_dashboard_screenshot()
