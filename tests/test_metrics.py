# PROMPT: Write FastAPI unit tests using TestClient to verify the /metrics and /funnel endpoints against SQLite mock databases.
# CHANGES MADE: Added SQLite database setup/teardown fixtures and loaded sample POS transactions.

import os
# Use test database environment
os.environ["DATABASE_PATH"] = "test_store_intelligence.db"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, get_db_connection

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    # Setup test schema
    init_db()
    
    # Clean tables to ensure isolation
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events")
    cursor.execute("DELETE FROM pos_transactions")
    
    # Load some mock POS transactions directly for correlation testing
    cursor.execute("""
        INSERT INTO pos_transactions (transaction_id, store_id, timestamp, basket_value_inr)
        VALUES 
        ('TXN_TEST_01', 'ST1008', '2026-04-10T12:20:00Z', 1500.00),
        ('TXN_TEST_02', 'ST1008', '2026-04-10T12:22:00Z', 850.00)
    """)
    conn.commit()
    conn.close()
    
    yield

def test_events_ingest_and_idempotency():
    event_data = {
        "event_id": "evt-uuid-001",
        "store_id": "ST1008",
        "camera_id": "CAM_3",
        "visitor_id": "VIS_TEST_01",
        "event_type": "ENTRY",
        "timestamp": "2026-04-10T12:15:00Z",
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.95,
        "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
    }
    
    # 1. Post event for the first time
    response1 = client.post("/events/ingest", json=[event_data])
    assert response1.status_code == 200
    assert response1.json()["processed_count"] == 1
    
    # 2. Post the SAME event again (idempotency check)
    response2 = client.post("/events/ingest", json=[event_data])
    assert response2.status_code == 200
    assert response2.json()["processed_count"] == 1  # Should be processed successfully (skipped duplicate but counts as success)

def test_metrics_computation():
    # Ingest a sequence of events for a customer who visits Skincare, Billing, and then converts
    events = [
        # Visitor enters
        {"event_id": "evt-001", "store_id": "ST1008", "camera_id": "CAM_3", "visitor_id": "VIS_C01", "event_type": "ENTRY", "timestamp": "2026-04-10T12:15:00Z", "zone_id": None, "dwell_ms": 0, "is_staff": False},
        # Visitor visits Skincare
        {"event_id": "evt-002", "store_id": "ST1008", "camera_id": "CAM_1", "visitor_id": "VIS_C01", "event_type": "ZONE_ENTER", "timestamp": "2026-04-10T12:15:10Z", "zone_id": "SKINCARE", "dwell_ms": 0, "is_staff": False},
        # Visitor dwells in Skincare
        {"event_id": "evt-003", "store_id": "ST1008", "camera_id": "CAM_1", "visitor_id": "VIS_C01", "event_type": "ZONE_DWELL", "timestamp": "2026-04-10T12:15:40Z", "zone_id": "SKINCARE", "dwell_ms": 30000, "is_staff": False},
        # Visitor goes to Billing
        {"event_id": "evt-004", "store_id": "ST1008", "camera_id": "CAM_5", "visitor_id": "VIS_C01", "event_type": "ZONE_ENTER", "timestamp": "2026-04-10T12:16:00Z", "zone_id": "BILLING", "dwell_ms": 0, "is_staff": False},
        {"event_id": "evt-005", "store_id": "ST1008", "camera_id": "CAM_5", "visitor_id": "VIS_C01", "event_type": "BILLING_QUEUE_JOIN", "timestamp": "2026-04-10T12:16:05Z", "zone_id": "BILLING", "dwell_ms": 0, "is_staff": False, "metadata": {"queue_depth": 1, "sku_zone": None, "session_seq": 5}},
        # Visitor exits
        {"event_id": "evt-006", "store_id": "ST1008", "camera_id": "CAM_3", "visitor_id": "VIS_C01", "event_type": "EXIT", "timestamp": "2026-04-10T12:17:00Z", "zone_id": None, "dwell_ms": 0, "is_staff": False}
    ]
    
    ingest_res = client.post("/events/ingest", json=events)
    assert ingest_res.status_code == 200
    
    # Query metrics
    metrics_res = client.get("/stores/ST1008/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    
    assert metrics["unique_visitors"] == 1
    # Visitor was at Billing at 12:16, POS transaction occurred at 12:20 (4 mins later - within 5 min window)
    # So conversion rate should be 100%
    assert metrics["conversion_rate"] == 100.0
    assert metrics["abandonment_rate"] == 0.0
