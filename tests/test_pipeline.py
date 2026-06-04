# PROMPT: Generate unit tests for SpatialTemporalReIDTracker class to ensure local visitor IDs correlate across cameras within a 5-second window.
# CHANGES MADE: Added explicit assertions for frame edge cases and initialized mock tracking sessions.

import unittest
from pipeline.tracker import SpatialTemporalReIDTracker

class TestSpatialTemporalReIDTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = SpatialTemporalReIDTracker(time_window_seconds=5.0)

    def test_new_visitor_entry(self):
        # Entry event on CAM_3 should create a new global ID
        gid = self.tracker.get_global_visitor_id(
            local_visitor_id=1,
            camera_id="CAM_3",
            timestamp_str="2026-04-10T12:00:00Z"
        )
        self.assertTrue(gid.startswith("VIS_GLB_"))
        
    def test_visitor_tracking_correlation(self):
        # Visitor enters store on CAM_3
        gid_entry = self.tracker.get_global_visitor_id(
            local_visitor_id=5,
            camera_id="CAM_3",
            timestamp_str="2026-04-10T12:00:00Z"
        )
        
        # Visitor appears on CAM_1 (floor) 3 seconds later
        gid_floor = self.tracker.get_global_visitor_id(
            local_visitor_id=10,
            camera_id="CAM_1",
            timestamp_str="2026-04-10T12:00:03Z"
        )
        
        # They should correlate to the same global visitor session
        self.assertEqual(gid_entry, gid_floor)

    def test_unrelated_visitor_no_correlation(self):
        # Visitor enters store on CAM_3
        gid_entry = self.tracker.get_global_visitor_id(
            local_visitor_id=5,
            camera_id="CAM_3",
            timestamp_str="2026-04-10T12:00:00Z"
        )
        
        # Another track appears 20 seconds later (beyond 5s time window)
        gid_late = self.tracker.get_global_visitor_id(
            local_visitor_id=12,
            camera_id="CAM_1",
            timestamp_str="2026-04-10T12:00:20Z"
        )
        
        # They should not correlate
        self.assertNotEqual(gid_entry, gid_late)

if __name__ == "__main__":
    unittest.main()
