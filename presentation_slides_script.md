# Apex Retail - Pitch Deck Slides Script

This script is for a **1-minute walkthrough** of the integrated slide deck (Project Pitch Deck).

---

### Slide 1: Welcome & Overview
* **Action**: Open the dashboard, click **Project Pitch Deck** on the sidebar. Keep Slide 1 active.
* **What to Say**:
  > "Welcome to Apex Retail. This is my store intelligence solution built for the Purplle Tech Challenge. 
  > I focus on real-time computer vision tracking and cross-camera Re-ID shopper journey analytics to optimize physical retail stores."

---

### Slide 2: The Retail Problem
* **Action**: Click **Next** to show Slide 2 (Retail Visibility Bottlenecks).
* **What to Say**:
  > "Physical store managers suffer from blind spots. They face unknown customer dwell times, sudden checkout queue abandonments, and static product layouts with no data to back up their design decisions."

---

### Slide 3: Technical Architecture
* **Action**: Click **Next** to show Slide 3 (Technical Stack).
* **What to Say**:
  > "My architecture solves this by processing live CCTV footage on standard CPU hardware using YOLOv8 and ByteTrack. 
  > This raw trajectory data is sent to a FastAPI backend backed by SQLite database storage, which updates my responsive live dashboard in real time using WebSockets."

---

### Slide 4: Core Innovation 1: Spatial Re-ID
* **Action**: Click **Next** to show Slide 4 (Spatial Re-ID Journey Timeline).
* **What to Say**:
  > "My first core innovation is multi-camera spatial Re-ID. 
  > I stitch trajectories across overlapping cameras, allowing me to map a customer's exact journey timeline from entry to browse, billing queue, and exit."

---

### Slide 5: Core Innovation 2: POS Correlation
* **Action**: Click **Next** to show Slide 5 (POS Basket Correlation A/B).
* **What to Say**:
  > "Second, I correlate POS transaction baskets directly with physical traffic. 
  > By mapping buy-together product affinities against customer shelf transitions, I calculate a Placement Efficiency Index to optimize shelf layouts."

---

### Slide 6: Core Innovation 3: Voice Copilot
* **Action**: Click **Next** to show Slide 6 (Voice & Sound Copilot).
* **What to Say**:
  > "Finally, I developed an eyes-free Voice Copilot. 
  > Using in-browser speech synthesis, the dashboard reads out automated operational warnings and triggers alarm tones for security breaches, keeping store managers alerted instantly."
