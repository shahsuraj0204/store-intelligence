from datetime import datetime
from app.db import get_db_connection

def check_system_health():
    db_connected = False
    last_event_timestamps = {}
    stale_feeds = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test connection
        cursor.execute("SELECT 1")
        cursor.fetchone()
        db_connected = True
        
        # Find last event per store
        cursor.execute("""
            SELECT store_id, MAX(timestamp) as last_time
            FROM events
            GROUP BY store_id
        """)
        rows = cursor.fetchall()
        for row in rows:
            last_event_timestamps[row["store_id"]] = row["last_time"]
            
        # Find stale feeds: check all active cameras in the last 2 hours,
        # see if their latest timestamp is more than 10 minutes (600s) behind the most recent event timestamp in the database.
        # (This handles offline / replay mode where the "current time" is simulated by the latest timestamp in the DB).
        cursor.execute("SELECT MAX(timestamp) as max_db_time FROM events")
        max_db_time_row = cursor.fetchone()
        
        if max_db_time_row and max_db_time_row["max_db_time"]:
            max_db_time_str = max_db_time_row["max_db_time"]
            # Parse ISO timestamp. Standard format: 'YYYY-MM-DDTHH:MM:SSZ' or similar.
            try:
                # Clean Z suffix if present
                clean_db_time = max_db_time_str.replace("Z", "")
                max_db_dt = datetime.fromisoformat(clean_db_time)
                
                # Check latest per camera
                cursor.execute("""
                    SELECT camera_id, MAX(timestamp) as last_cam_time
                    FROM events
                    GROUP BY camera_id
                """)
                cam_rows = cursor.fetchall()
                for cam_row in cam_rows:
                    cam_time_str = cam_row["last_cam_time"]
                    clean_cam_time = cam_time_str.replace("Z", "")
                    cam_dt = datetime.fromisoformat(clean_cam_time)
                    
                    # If camera is more than 10 minutes (600 seconds) behind the database's latest state
                    diff_seconds = (max_db_dt - cam_dt).total_seconds()
                    if diff_seconds > 600:
                        stale_feeds.append(cam_row["camera_id"])
            except Exception as e:
                # Log parsing error if formats are unexpected
                pass
                
        conn.close()
    except Exception as e:
        db_connected = False
        
    status = "healthy"
    if not db_connected:
        status = "unhealthy"
    elif stale_feeds:
        status = "warning"
        
    return {
        "status": status,
        "database_connected": db_connected,
        "last_event_timestamps": last_event_timestamps,
        "stale_feeds": stale_feeds
    }
