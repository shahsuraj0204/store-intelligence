import sqlite3
import os
import csv
from datetime import datetime

def get_db_connection():
    db_path = os.environ.get("DATABASE_PATH", "store_intelligence.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Events table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        store_id TEXT NOT NULL,
        camera_id TEXT NOT NULL,
        visitor_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        zone_id TEXT,
        dwell_ms INTEGER DEFAULT 0,
        is_staff INTEGER DEFAULT 0,
        confidence REAL DEFAULT 1.0,
        queue_depth INTEGER,
        sku_zone TEXT,
        session_seq INTEGER DEFAULT 1
    )
    """)
    
    # POS Transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pos_transactions (
        transaction_id TEXT PRIMARY KEY,
        store_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        basket_value_inr REAL NOT NULL
    )
    """)
    
    # Indexes for fast queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_store_time ON events (store_id, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_visitor ON events (visitor_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events (event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pos_store_time ON pos_transactions (store_id, timestamp)")
    
    # Insert mock POS transactions for STORE_BLR_002 to enable conversion correlation in simulation
    cursor.execute("""
        INSERT OR IGNORE INTO pos_transactions (transaction_id, store_id, timestamp, basket_value_inr)
        VALUES 
        ('TXN_BLR_002_01', 'STORE_BLR_002', '2026-04-10T12:20:00Z', 1200.00),
        ('TXN_BLR_002_02', 'STORE_BLR_002', '2026-04-10T12:22:00Z', 750.00),
        ('TXN_BLR_002_03', 'STORE_BLR_002', '2026-04-10T12:25:00Z', 2200.00)
    """)
    
    # Seed default events for STORE_BLR_002 to enable metrics immediately
    mock_events = [
        # VIS_BLR_001 Flow (converts with TXN_BLR_002_01)
        ('e_blr_001', 'STORE_BLR_002', 'CAM_3', 'VIS_BLR_001', 'ENTRY', '2026-04-10T12:15:02Z', None, 0, 0, 1.0, None, None, 1),
        ('e_blr_002', 'STORE_BLR_002', 'CAM_1', 'VIS_BLR_001', 'ZONE_ENTER', '2026-04-10T12:15:15Z', 'SKINCARE', 0, 0, 0.95, None, None, 2),
        ('e_blr_003', 'STORE_BLR_002', 'CAM_1', 'VIS_BLR_001', 'ZONE_DWELL', '2026-04-10T12:15:45Z', 'SKINCARE', 30000, 0, 0.95, None, 'MOISTURISER', 3),
        ('e_blr_004', 'STORE_BLR_002', 'CAM_5', 'VIS_BLR_001', 'ZONE_ENTER', '2026-04-10T12:16:10Z', 'BILLING', 0, 0, 0.90, None, None, 4),
        ('e_blr_005', 'STORE_BLR_002', 'CAM_5', 'VIS_BLR_001', 'BILLING_QUEUE_JOIN', '2026-04-10T12:16:15Z', 'BILLING', 0, 0, 0.90, 1, None, 5),
        ('e_blr_006', 'STORE_BLR_002', 'CAM_5', 'VIS_BLR_001', 'ZONE_DWELL', '2026-04-10T12:16:45Z', 'BILLING', 30000, 0, 0.90, None, None, 6),
        ('e_blr_007', 'STORE_BLR_002', 'CAM_3', 'VIS_BLR_001', 'EXIT', '2026-04-10T12:17:00Z', None, 0, 0, 1.0, None, None, 7),
        
        # VIS_BLR_002 Flow (visits BACK_OFFICE Restricted Area)
        ('e_blr_008', 'STORE_BLR_002', 'CAM_3', 'VIS_BLR_002', 'ENTRY', '2026-04-10T12:15:10Z', None, 0, 0, 1.0, None, None, 1),
        ('e_blr_009', 'STORE_BLR_002', 'CAM_2', 'VIS_BLR_002', 'ZONE_ENTER', '2026-04-10T12:15:25Z', 'MAKEUP', 0, 0, 0.95, None, None, 2),
        ('e_blr_010', 'STORE_BLR_002', 'CAM_2', 'VIS_BLR_002', 'ZONE_DWELL', '2026-04-10T12:15:55Z', 'MAKEUP', 30000, 0, 0.95, None, 'LIPSTICK', 3),
        ('e_blr_011', 'STORE_BLR_002', 'CAM_4', 'VIS_BLR_002', 'ZONE_ENTER', '2026-04-10T12:17:15Z', 'BACK_OFFICE', 0, 0, 0.98, None, None, 4),
        
        # Staff member VIS_BLR_STAFF
        ('e_blr_012', 'STORE_BLR_002', 'CAM_2', 'VIS_BLR_STAFF', 'ZONE_DWELL', '2026-04-10T12:15:30Z', 'MAKEUP', 30000, 1, 1.0, None, None, 1),
        
        # Queue buildup (Spike Anomaly)
        ('e_blr_013', 'STORE_BLR_002', 'CAM_3', 'VIS_BLR_003', 'ENTRY', '2026-04-10T12:17:20Z', None, 0, 0, 1.0, None, None, 1),
        ('e_blr_014', 'STORE_BLR_002', 'CAM_3', 'VIS_BLR_004', 'ENTRY', '2026-04-10T12:17:22Z', None, 0, 0, 1.0, None, None, 1),
        ('e_blr_015', 'STORE_BLR_002', 'CAM_3', 'VIS_BLR_005', 'ENTRY', '2026-04-10T12:17:25Z', None, 0, 0, 1.0, None, None, 1),
        ('e_blr_016', 'STORE_BLR_002', 'CAM_3', 'VIS_BLR_006', 'ENTRY', '2026-04-10T12:17:28Z', None, 0, 0, 1.0, None, None, 1),
        ('e_blr_017', 'STORE_BLR_002', 'CAM_3', 'VIS_BLR_007', 'ENTRY', '2026-04-10T12:17:30Z', None, 0, 0, 1.0, None, None, 1),
        
        # Queue joins
        ('e_blr_018', 'STORE_BLR_002', 'CAM_5', 'VIS_BLR_003', 'BILLING_QUEUE_JOIN', '2026-04-10T12:17:40Z', 'BILLING', 0, 0, 0.95, 2, None, 2),
        ('e_blr_019', 'STORE_BLR_002', 'CAM_5', 'VIS_BLR_004', 'BILLING_QUEUE_JOIN', '2026-04-10T12:17:42Z', 'BILLING', 0, 0, 0.95, 3, None, 2),
        ('e_blr_020', 'STORE_BLR_002', 'CAM_5', 'VIS_BLR_005', 'BILLING_QUEUE_JOIN', '2026-04-10T12:17:45Z', 'BILLING', 0, 0, 0.95, 4, None, 2),
        ('e_blr_021', 'STORE_BLR_002', 'CAM_5', 'VIS_BLR_006', 'BILLING_QUEUE_JOIN', '2026-04-10T12:17:48Z', 'BILLING', 0, 0, 0.95, 5, None, 2),
        ('e_blr_022', 'STORE_BLR_002', 'CAM_5', 'VIS_BLR_007', 'BILLING_QUEUE_JOIN', '2026-04-10T12:17:50Z', 'BILLING', 0, 0, 0.95, 6, None, 2),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO events (
            event_id, store_id, camera_id, visitor_id, event_type, 
            timestamp, zone_id, dwell_ms, is_staff, confidence, 
            queue_depth, sku_zone, session_seq
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, mock_events)

    # Seed default events for ST1008 just in case
    mock_events_st1008 = [
        # VIS_ST_001 Flow (converts with transaction loaded from CSV or TXN_ST_01)
        ('e_st_001', 'ST1008', 'CAM_3', 'VIS_ST_001', 'ENTRY', '2026-04-10T12:15:02Z', None, 0, 0, 1.0, None, None, 1),
        ('e_st_002', 'ST1008', 'CAM_1', 'VIS_ST_001', 'ZONE_ENTER', '2026-04-10T12:15:15Z', 'SKINCARE', 0, 0, 0.95, None, None, 2),
        ('e_st_003', 'ST1008', 'CAM_1', 'VIS_ST_001', 'ZONE_DWELL', '2026-04-10T12:15:45Z', 'SKINCARE', 30000, 0, 0.95, None, 'MOISTURISER', 3),
        ('e_st_004', 'ST1008', 'CAM_5', 'VIS_ST_001', 'ZONE_ENTER', '2026-04-10T12:16:10Z', 'BILLING', 0, 0, 0.90, None, None, 4),
        ('e_st_005', 'ST1008', 'CAM_5', 'VIS_ST_001', 'BILLING_QUEUE_JOIN', '2026-04-10T12:16:15Z', 'BILLING', 0, 0, 0.90, 1, None, 5),
        ('e_st_006', 'ST1008', 'CAM_5', 'VIS_ST_001', 'ZONE_DWELL', '2026-04-10T12:16:45Z', 'BILLING', 30000, 0, 0.90, None, None, 6),
        ('e_st_007', 'ST1008', 'CAM_3', 'VIS_ST_001', 'EXIT', '2026-04-10T12:17:00Z', None, 0, 0, 1.0, None, None, 7),
        
        # VIS_ST_002 Flow (visits BACK_OFFICE Restricted Area)
        ('e_st_008', 'ST1008', 'CAM_3', 'VIS_ST_002', 'ENTRY', '2026-04-10T12:15:10Z', None, 0, 0, 1.0, None, None, 1),
        ('e_st_009', 'ST1008', 'CAM_2', 'VIS_ST_002', 'ZONE_ENTER', '2026-04-10T12:15:25Z', 'MAKEUP', 0, 0, 0.95, None, None, 2),
        ('e_st_010', 'ST1008', 'CAM_2', 'VIS_ST_002', 'ZONE_DWELL', '2026-04-10T12:15:55Z', 'MAKEUP', 30000, 0, 0.95, None, 'LIPSTICK', 3),
        ('e_st_011', 'ST1008', 'CAM_4', 'VIS_ST_002', 'ZONE_ENTER', '2026-04-10T12:17:15Z', 'BACK_OFFICE', 0, 0, 0.98, None, None, 4),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO events (
            event_id, store_id, camera_id, visitor_id, event_type, 
            timestamp, zone_id, dwell_ms, is_staff, confidence, 
            queue_depth, sku_zone, session_seq
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, mock_events_st1008)

    conn.commit()
    conn.close()
    
    # Load transactions if CSV is present
    load_pos_from_csv()

def load_pos_from_csv():
    # Find any CSV file in the current directory containing POS data
    csv_file = None
    for f in os.listdir("."):
        if f.endswith(".csv") and "Brigade" in f:
            csv_file = f
            break
            
    if not csv_file:
        print("No POS transaction CSV file found in the workspace.")
        return
        
    print(f"Loading POS transactions from {csv_file}...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        with open(csv_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                try:
                    # Map CSV columns: order_id, store_id, order_date, order_time, total_amount
                    tx_id = row.get("order_id")
                    store_id = row.get("store_id")
                    order_date = row.get("order_date")
                    order_time = row.get("order_time")
                    total_amount = row.get("total_amount")
                    
                    if not (tx_id and store_id and order_date and order_time and total_amount):
                        continue
                        
                    # Parse timestamp from 10-04-2026 and 16:55:36 to ISO-8601 '2026-04-10T16:55:36Z'
                    # order_date can be in format DD-MM-YYYY
                    date_parts = order_date.split("-")
                    if len(date_parts) == 3:
                        day, month, year = date_parts
                        iso_timestamp = f"{year}-{month}-{day}T{order_time}Z"
                    else:
                        iso_timestamp = f"{order_date}T{order_time}Z"
                        
                    cursor.execute("""
                        INSERT OR IGNORE INTO pos_transactions (transaction_id, store_id, timestamp, basket_value_inr)
                        VALUES (?, ?, ?, ?)
                    """, (tx_id, store_id, iso_timestamp, float(total_amount)))
                    
                    if conn.changes() > 0:
                        count += 1
                except Exception as e:
                    # Ignore rows with errors
                    pass
            conn.commit()
            print(f"Successfully loaded {count} new POS transactions.")
    except Exception as e:
        print(f"Failed to load POS transactions from CSV: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()

