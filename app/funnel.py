from app.db import get_db_connection
from datetime import datetime

def compute_store_funnel(store_id: str) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch all visitors for the store (excluding staff)
    cursor.execute("""
        SELECT DISTINCT visitor_id 
        FROM events 
        WHERE store_id = ? AND is_staff = 0
    """, (store_id,))
    visitors = [row["visitor_id"] for row in cursor.fetchall()]
    
    entry_count = len(visitors)
    zone_visit_count = 0
    billing_queue_count = 0
    purchase_count = 0
    
    if entry_count > 0:
        # 2. Count visitors who visited a product shelf zone (e.g. SKINCARE, MAKEUP, HAIRCARE, FRAGRANCE, etc.)
        # A named zone is a non-null zone that is not 'BILLING' or 'ENTRY' or 'EXIT'.
        cursor.execute("""
            SELECT DISTINCT visitor_id
            FROM events
            WHERE store_id = ? AND is_staff = 0
              AND zone_id IS NOT NULL 
              AND zone_id NOT IN ('BILLING', 'ENTRY', 'EXIT')
        """, (store_id,))
        zone_visitors = {row["visitor_id"] for row in cursor.fetchall()}
        zone_visit_count = len(zone_visitors)
        
        # 3. Count visitors who joined the billing queue / entered billing zone
        cursor.execute("""
            SELECT DISTINCT visitor_id
            FROM events
            WHERE store_id = ? AND is_staff = 0
              AND (zone_id = 'BILLING' OR event_type = 'BILLING_QUEUE_JOIN')
        """, (store_id,))
        billing_visitors = {row["visitor_id"] for row in cursor.fetchall()}
        billing_queue_count = len(billing_visitors)
        
        # 4. Count purchases.
        # Find billing zone exits or dwell times, and look for POS transactions for this store 
        # in the 5-minute window after.
        # Let's get the max timestamp when each visitor was in the billing zone
        cursor.execute("""
            SELECT visitor_id, timestamp
            FROM events
            WHERE store_id = ? AND is_staff = 0
              AND (zone_id = 'BILLING' OR event_type = 'BILLING_QUEUE_JOIN')
        """, (store_id,))
        billing_events = cursor.fetchall()
        
        converted_visitors = set()
        
        # Load POS transactions for this store to correlate in memory
        cursor.execute("""
            SELECT timestamp 
            FROM pos_transactions 
            WHERE store_id = ?
        """, (store_id,))
        pos_timestamps = [row["timestamp"] for row in cursor.fetchall()]
        
        # Correlate:
        # A visitor who was in the billing zone in the 5-minute window before a transaction timestamp counts as a converted visitor.
        # That means: transaction_time - 300 seconds <= billing_time <= transaction_time
        # Or: billing_time <= transaction_time <= billing_time + 300 seconds (5 minutes)
        for row in billing_events:
            v_id = row["visitor_id"]
            if v_id in converted_visitors:
                continue
                
            b_time_str = row["timestamp"]
            # Standardize timestamp formats (remove Z suffix if present)
            clean_b_time = b_time_str.replace("Z", "")
            try:
                b_dt = datetime.fromisoformat(clean_b_time)
                for tx_time_str in pos_timestamps:
                    clean_tx_time = tx_time_str.replace("Z", "")
                    tx_dt = datetime.fromisoformat(clean_tx_time)
                    
                    diff = (tx_dt - b_dt).total_seconds()
                    if 0 <= diff <= 300:  # 0 to 5 minutes
                        converted_visitors.add(v_id)
                        break
            except Exception as e:
                # Handle unexpected date parsing formats
                pass
                
        purchase_count = len(converted_visitors)
        
    conn.close()
    
    # Compute drop-offs
    stages = [
        {"stage_name": "Entry", "count": entry_count, "drop_off_pct": 0.0},
        {"stage_name": "Zone Visit", "count": zone_visit_count, "drop_off_pct": 0.0},
        {"stage_name": "Billing Queue", "count": billing_queue_count, "drop_off_pct": 0.0},
        {"stage_name": "Purchase", "count": purchase_count, "drop_off_pct": 0.0}
    ]
    
    # Calculate drop-off pct compared to previous stage
    if entry_count > 0:
        stages[1]["drop_off_pct"] = round(((entry_count - zone_visit_count) / entry_count) * 100, 2)
    if zone_visit_count > 0:
        stages[2]["drop_off_pct"] = round(((zone_visit_count - billing_queue_count) / zone_visit_count) * 100, 2)
    if billing_queue_count > 0:
        stages[3]["drop_off_pct"] = round(((billing_queue_count - purchase_count) / billing_queue_count) * 100, 2)
        
    return stages
