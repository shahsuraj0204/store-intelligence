import sqlite3
from typing import List, Dict, Any
from app.db import get_db_connection
from app.models import EventSchema

def ingest_events_batch(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    processed_count = 0
    failed_count = 0
    errors = []
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    except Exception as e:
        # Database unavailable: should raise service unavailable (handled in main.py)
        raise RuntimeError("Database unavailable") from e

    try:
        for event_data in events:
            try:
                # 1. Validate against Pydantic schema
                event = EventSchema(**event_data)
                
                # 2. Insert event. Use INSERT OR IGNORE for idempotency
                cursor.execute("""
                    INSERT OR IGNORE INTO events (
                        event_id, store_id, camera_id, visitor_id, event_type, 
                        timestamp, zone_id, dwell_ms, is_staff, confidence, 
                        queue_depth, sku_zone, session_seq
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.store_id,
                    event.camera_id,
                    event.visitor_id,
                    event.event_type,
                    event.timestamp,
                    event.zone_id,
                    event.dwell_ms,
                    1 if event.is_staff else 0,
                    event.confidence,
                    event.metadata.queue_depth if event.metadata else None,
                    event.metadata.sku_zone if event.metadata else None,
                    event.metadata.session_seq if event.metadata else 1
                ))
                
                # Increment processed count (INSERT OR IGNORE handles duplicates successfully)
                processed_count += 1
                    
            except Exception as val_error:
                failed_count += 1
                errors.append({
                    "event_id": event_data.get("event_id", "unknown"),
                    "error": str(val_error)
                })
        
        conn.commit()
    except Exception as db_error:
        conn.rollback()
        raise db_error
    finally:
        if conn:
            conn.close()
            
    return {
        "status": "success" if failed_count == 0 else "partial_success",
        "processed_count": processed_count,
        "failed_count": failed_count,
        "errors": errors
    }
