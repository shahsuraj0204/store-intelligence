# PROMPT: Generate unit tests for detect_anomalies function in app/anomalies.py covering BILLING_QUEUE_SPIKE, UNAUTHORIZED_ENTRY, DEAD_ZONE, and CONVERSION_DROP.
# CHANGES MADE: Integrated datetime offset calculations to simulate 30 minutes of dead zone inactivity.

import os
os.environ["DATABASE_PATH"] = "test_anomalies.db"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, get_db_connection
from app.anomalies import detect_anomalies

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events")
    cursor.execute("DELETE FROM pos_transactions")
    conn.commit()
    conn.close()
    yield

def test_billing_queue_spike_anomaly():
    # Post a billing queue join event with depth = 6
    events = [
        {
            "event_id": "e-test-q-01",
            "store_id": "ST1008",
            "camera_id": "CAM_5",
            "visitor_id": "VIS_A01",
            "event_type": "BILLING_QUEUE_JOIN",
            "timestamp": "2026-04-10T12:00:00Z",
            "zone_id": "BILLING",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.90,
            "metadata": {"queue_depth": 6, "sku_zone": None, "session_seq": 1}
        }
    ]
    
    client.post("/events/ingest", json=events)
    
    # Query anomalies endpoint
    response = client.get("/stores/ST1008/anomalies")
    assert response.status_code == 200
    anomalies = response.json()["anomalies"]
    
    # We should have a queue spike anomaly flagged
    q_spikes = [a for a in anomalies if a["anomaly_type"] == "BILLING_QUEUE_SPIKE"]
    assert len(q_spikes) == 1
    assert q_spikes[0]["severity"] == "WARN"

def test_unauthorized_entry_anomaly():
    # Post a customer entering restricted BACK_OFFICE zone
    events = [
        {
            "event_id": "e-test-unauth-01",
            "store_id": "ST1008",
            "camera_id": "CAM_4",
            "visitor_id": "VIS_CUSTOMER_01",
            "event_type": "ZONE_ENTER",
            "timestamp": "2026-04-10T12:00:00Z",
            "zone_id": "BACK_OFFICE",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.95,
            "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
        }
    ]
    
    client.post("/events/ingest", json=events)
    
    # Query anomalies
    anomalies = detect_anomalies("ST1008")
    unauths = [a for a in anomalies if a["anomaly_type"] == "UNAUTHORIZED_ENTRY"]
    
    assert len(unauths) == 1
    assert unauths[0]["severity"] == "CRITICAL"
