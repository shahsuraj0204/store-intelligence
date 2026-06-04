from app.db import get_db_connection
from datetime import datetime

def get_store_visitor_journeys(store_id: str) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all events for the store sorted by visitor and time
    cursor.execute("""
        SELECT event_id, camera_id, visitor_id, event_type, timestamp, zone_id, dwell_ms, is_staff, queue_depth, sku_zone
        FROM events
        WHERE store_id = ?
        ORDER BY visitor_id, timestamp ASC
    """, (store_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Reconstruct journeys in memory
    journeys_map = {}
    for row in rows:
        v_id = row["visitor_id"]
        if v_id not in journeys_map:
            journeys_map[v_id] = {
                "visitor_id": v_id,
                "is_staff": bool(row["is_staff"]),
                "start_time": row["timestamp"],
                "last_active": row["timestamp"],
                "path": []
            }
            
        event_type = row["event_type"]
        zone_id = row["zone_id"]
        
        # Build human-readable descriptions for timeline steps
        description = ""
        icon = "fa-circle"
        if event_type == "ENTRY":
            description = f"Entered store via Entrance camera ({row['camera_id']})"
            icon = "fa-right-to-bracket"
        elif event_type == "EXIT":
            description = "Exited store boundary"
            icon = "fa-right-from-bracket"
        elif event_type == "ZONE_ENTER":
            description = f"Entered {zone_id} Product Zone"
            icon = "fa-shoe-prints"
        elif event_type == "ZONE_DWELL":
            dwell_sec = round(row["dwell_ms"] / 1000.0, 1)
            sku_info = f" (browsing {row['sku_zone']})" if row["sku_zone"] else ""
            description = f"Browsed in {zone_id} for {dwell_sec}s{sku_info}"
            icon = "fa-clock"
        elif event_type == "BILLING_QUEUE_JOIN":
            q_depth = row["queue_depth"] or 1
            description = f"Joined Checkout Queue (Queue Depth: {q_depth})"
            icon = "fa-people-group"
        elif event_type == "ZONE_EXIT":
            dwell_sec = round(row["dwell_ms"] / 1000.0, 1)
            description = f"Left {zone_id} zone after {dwell_sec}s"
            icon = "fa-arrow-right-from-bracket"
            
        journeys_map[v_id]["path"].append({
            "event_type": event_type,
            "timestamp": row["timestamp"],
            "zone_id": zone_id,
            "dwell_ms": row["dwell_ms"],
            "description": description,
            "icon": icon,
            "camera_id": row["camera_id"]
        })
        journeys_map[v_id]["last_active"] = row["timestamp"]
        
    # Convert map to sorted list based on start time (newest journeys first)
    sorted_journeys = list(journeys_map.values())
    sorted_journeys.sort(key=lambda x: x["start_time"], reverse=True)
    return sorted_journeys
