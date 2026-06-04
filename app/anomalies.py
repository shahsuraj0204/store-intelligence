from app.db import get_db_connection
from datetime import datetime, timedelta
import uuid

def detect_anomalies(store_id: str) -> list:
    anomalies = []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get latest event time to use as reference current time (simulates real-time)
    cursor.execute("SELECT MAX(timestamp) as max_time FROM events WHERE store_id = ?", (store_id,))
    max_time_row = cursor.fetchone()
    if not (max_time_row and max_time_row["max_time"]):
        conn.close()
        return []
        
    current_time_str = max_time_row["max_time"]
    clean_curr_time = current_time_str.replace("Z", "")
    try:
        current_dt = datetime.fromisoformat(clean_curr_time)
    except Exception:
        conn.close()
        return []
        
    # Rule 1: BILLING_QUEUE_SPIKE
    # Check latest queue depth
    cursor.execute("""
        SELECT queue_depth, timestamp
        FROM events
        WHERE store_id = ? AND event_type = 'BILLING_QUEUE_JOIN' AND queue_depth IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1
    """, (store_id,))
    queue_row = cursor.fetchone()
    if queue_row:
        depth = queue_row["queue_depth"]
        if depth >= 5:
            severity = "CRITICAL" if depth >= 7 else "WARN"
            anomalies.append({
                "anomaly_id": str(uuid.uuid4()),
                "anomaly_type": "BILLING_QUEUE_SPIKE",
                "severity": severity,
                "timestamp": queue_row["timestamp"],
                "zone_id": "BILLING",
                "description": f"Billing queue depth has spiked to {depth} people.",
                "suggested_action": "Deploy additional checkout staff and open auxiliary billing counter."
            })
            
    # Rule 2: UNAUTHORIZED_ENTRY
    # Check if any non-staff visitor has visited the BACK_OFFICE zone
    cursor.execute("""
        SELECT visitor_id, timestamp, zone_id
        FROM events
        WHERE store_id = ? AND is_staff = 0 AND zone_id = 'BACK_OFFICE'
        ORDER BY timestamp DESC LIMIT 10
    """, (store_id,))
    unauth_rows = cursor.fetchall()
    for row in unauth_rows:
        anomalies.append({
            "anomaly_id": str(uuid.uuid4()),
            "anomaly_type": "UNAUTHORIZED_ENTRY",
            "severity": "CRITICAL",
            "timestamp": row["timestamp"],
            "zone_id": "BACK_OFFICE",
            "description": f"Customer visitor {row['visitor_id']} detected inside restricted Back Office / Storage area.",
            "suggested_action": "Alert store security to perform a restricted zone sweep."
        })
        
    # Rule 3: DEAD_ZONE (no visits in last 30 minutes in a zone)
    # Get all active zones in this store
    cursor.execute("""
        SELECT DISTINCT zone_id 
        FROM events 
        WHERE store_id = ? AND zone_id IS NOT NULL AND zone_id NOT IN ('ENTRY', 'EXIT', 'BACK_OFFICE')
    """, (store_id,))
    zones = [row["zone_id"] for row in cursor.fetchall()]
    
    for zone in zones:
        # Check last visit time for this zone
        cursor.execute("""
            SELECT MAX(timestamp) as last_visit
            FROM events
            WHERE store_id = ? AND zone_id = ? AND is_staff = 0
        """, (store_id, zone))
        last_row = cursor.fetchone()
        if last_row and last_row["last_visit"]:
            clean_last = last_row["last_visit"].replace("Z", "")
            try:
                last_dt = datetime.fromisoformat(clean_last)
                # If last visit was more than 30 minutes ago
                if (current_dt - last_dt) > timedelta(minutes=30):
                    anomalies.append({
                        "anomaly_id": str(uuid.uuid4()),
                        "anomaly_type": "DEAD_ZONE",
                        "severity": "INFO",
                        "timestamp": last_row["last_visit"],
                        "zone_id": zone,
                        "description": f"No visitor traffic detected in the {zone} zone for over 30 minutes.",
                        "suggested_action": "Check product assortment and shelf lighting in this zone."
                    })
            except Exception:
                pass
                
    # Rule 4: CONVERSION_DROP
    # Let's compute the current conversion rate
    # Fetch historical data (simulated 7-day average conversion is 25%)
    # If today's conversion is under 12%, trigger drop warning
    from app.metrics import calculate_store_metrics
    metrics = calculate_store_metrics(store_id)
    conv_rate = metrics["conversion_rate"]
    unique_v = metrics["unique_visitors"]
    
    # Only flag if there is enough statistical significance (e.g. >10 visitors)
    if unique_v >= 10 and conv_rate < 12.0:
        anomalies.append({
            "anomaly_id": str(uuid.uuid4()),
            "anomaly_type": "CONVERSION_DROP",
            "severity": "WARN",
            "timestamp": current_time_str,
            "zone_id": None,
            "description": f"Store conversion rate is abnormally low at {conv_rate}% (historical average: 25.0%).",
            "suggested_action": "Verify if high-demand cosmetic lines are out-of-stock or if billing queues are causing abandonment."
        })
        
    conn.close()
    return anomalies
