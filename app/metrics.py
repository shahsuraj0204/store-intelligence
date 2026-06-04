from app.db import get_db_connection
from datetime import datetime
from app.funnel import compute_store_funnel

def calculate_store_metrics(store_id: str) -> dict:
    # 1. Fetch funnel stages (which give us visitors, billing queue, and purchases)
    funnel_stages = compute_store_funnel(store_id)
    
    unique_visitors = funnel_stages[0]["count"]
    billing_queue = funnel_stages[2]["count"]
    purchases = funnel_stages[3]["count"]
    
    # 2. Conversion rate
    conversion_rate = 0.0
    if unique_visitors > 0:
        conversion_rate = round((purchases / unique_visitors) * 100, 2)
        
    # 3. Abandonment rate
    abandonment_rate = 0.0
    if billing_queue > 0:
        abandonment_rate = round(((billing_queue - purchases) / billing_queue) * 100, 2)
        
    # 4. Average dwell time per zone
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT zone_id, AVG(dwell_ms) as avg_dwell
        FROM events
        WHERE store_id = ? AND is_staff = 0 AND zone_id IS NOT NULL AND zone_id NOT IN ('ENTRY', 'EXIT')
        GROUP BY zone_id
    """, (store_id,))
    rows = cursor.fetchall()
    avg_dwell_times = {row["zone_id"]: round(row["avg_dwell"], 2) for row in rows}
    
    # 5. Current queue depth
    # Find the latest event of type BILLING_QUEUE_JOIN. If visitor has not left billing zone, count them.
    # Alternatively, look at the last recorded queue_depth metadata value in the events log.
    cursor.execute("""
        SELECT queue_depth 
        FROM events 
        WHERE store_id = ? AND event_type = 'BILLING_QUEUE_JOIN' AND queue_depth IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1
    """, (store_id,))
    row = cursor.fetchone()
    current_queue_depth = row["queue_depth"] if row else 0
    
    conn.close()
    
    return {
        "store_id": store_id,
        "timestamp": datetime.utcnow(),
        "unique_visitors": unique_visitors,
        "conversion_rate": conversion_rate,
        "avg_dwell_times": avg_dwell_times,
        "queue_depth": current_queue_depth,
        "abandonment_rate": abandonment_rate
    }

def get_store_heatmap(store_id: str) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get total visit count and average dwell per zone
    cursor.execute("""
        SELECT zone_id, COUNT(DISTINCT visitor_id) as visit_count, AVG(dwell_ms) as avg_dwell
        FROM events
        WHERE store_id = ? AND is_staff = 0 AND zone_id IS NOT NULL AND zone_id NOT IN ('ENTRY', 'EXIT')
        GROUP BY zone_id
    """, (store_id,))
    rows = cursor.fetchall()
    
    # Find total visitor sessions to see if we have enough data confidence (>20 sessions)
    cursor.execute("SELECT COUNT(DISTINCT visitor_id) as total_sessions FROM events WHERE store_id = ? AND is_staff = 0", (store_id,))
    sessions_row = cursor.fetchone()
    total_sessions = sessions_row["total_sessions"] if sessions_row else 0
    data_confidence = total_sessions >= 20
    
    heatmap = []
    max_visits = max([row["visit_count"] for row in rows]) if rows else 1
    
    for row in rows:
        zone_id = row["zone_id"]
        visit_count = row["visit_count"]
        avg_dwell = row["avg_dwell"]
        
        # Normalized score 0-100 based on visit frequency
        normalized_score = round((visit_count / max_visits) * 100, 2)
        
        heatmap.append({
            "zone_id": zone_id,
            "visit_frequency": visit_count,
            "avg_dwell_sec": round(avg_dwell / 1000.0, 2),
            "normalized_score": normalized_score
        })
        
    conn.close()
    
    return {
        "store_id": store_id,
        "timestamp": datetime.utcnow(),
        "data_confidence": data_confidence,
        "heatmap": heatmap
    }
