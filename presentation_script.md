# Apex Retail - Store Intelligence Desk
## Presentation & Screen Recording Script

This script is structured for a **2-minute live demo** where you record your screen and speak over it. 

---

### Phase 1: The Pitch Deck (Slide Presenter)
* **Duration**: ~20 seconds
* **Visual Action**: Open `http://localhost:8000/dashboard` in browser. Click on **Project Pitch Deck** on the sidebar to bring up the integrated slide presentation.
* **What to Say**:
  > "Hello everyone, my name is Shah, and today I'm demonstrating Apex Retail—my AI-powered Store Intelligence Desk built for the Purplle Tech Challenge 2026. 
  > 
  > Traditional retail stores operate in a blind spot. They don't know why customers abandon queues, where they spend their time, or how shelf layouts affect actual conversion. 
  > Apex Retail solves this by bridging the gap between Edge Computer Vision tracking and Point of Sale data."

---

### Phase 2: Slide Progression & Architecture
* **Duration**: ~20 seconds
* **Visual Action**: Click **Next** on the slide presenter twice to show the Technical Stack slide.
* **What to Say**:
  > "My system architecture features a custom, lightweight YOLOv8 and ByteTrack pipeline that runs human detection at the edge. 
  > I designed a spatial-temporal stitching window to connect visitor tracks across overlapping cameras without heavy GPU dependencies. 
  > The tracking data is ingested via FastAPI and SQLite, pushing real-time events to my frontend dashboard via WebSockets."

---

### Phase 3: Live KPI Desk & Simulation
* **Duration**: ~20 seconds
* **Visual Action**: Click **Next** to exit the deck, loading the **Live Monitor** desk. Click the **"Run Simulation"** button in the top right to start the live feed of mock shopper data.
* **What to Say**:
  > "Let's dive into the Live Monitor desk. I will launch my live simulation. 
  > Instantly, you see my KPI cards update. I track Unique Visitors, real-time Conversion Rates, Cashier Queue Depth, and Cart Abandonment rates. 
  > Notice the real-time event stream ticker scrolling on the right—every customer entry, zone visit, and checkout queue event is pushed instantly over WebSockets."

---

### Phase 4: Conversion Funnel & Zone Heatmap
* **Duration**: ~20 seconds
* **Visual Action**: Scroll down slightly to display the **Customer Conversion Funnel** chart and the **Product Zone Heatmap**.
* **What to Say**:
  > "Below, the conversion funnel tracks customer drop-offs at every critical milestone—from initial entry to browsing, queue joining, and final POS checkout.
  > Adjacent to it, my interactive store layout heatmap shows shopper density and average dwell times across Skincare, Makeup, Haircare, and Fragrance zones. 
  > This allows store operators to identify high-interest zones and cold zones at a single glance."

---

### Phase 5: Visitor Journey Re-ID & Layout Optimizer
* **Duration**: ~20 seconds
* **Visual Action**: Scroll down to the **Shopper Journey Re-ID Tracker** and click on one of the visitor IDs (e.g. `VIS_801`). Then scroll to the **Layout Placement Optimizer**.
* **What to Say**:
  > "Using my Spatial Re-ID tracker, I reconstruct the exact camera timeline of individual shoppers as they transition across zones, separating employees from customers automatically.
  > By combining these trajectories with POS transaction logs, my Layout Placement Optimizer evaluates aisle efficiency—measuring buy-together affinities against actual foot traffic flow to suggest product shifts."

---

### Phase 6: AI Copilot, Alerts & Wrap-up
* **Duration**: ~20 seconds
* **Visual Action**: Scroll back to the top to show the **AI Operations Copilot** recommendations and the **Security & Operations Alerts** desk. Toggle the **Voice Copilot** button on the sidebar to demonstrate voice features.
* **What to Say**:
  > "Lastly, my AI Copilot gives managers real-time recommendations, while the Security desk fires auditory and visual alerts for abnormal queues or unauthorized restricted-area entries.
  > With dynamic data correlation and real-time alerts, Apex Retail brings e-commerce style analytics to the physical retail world. Thank you."
