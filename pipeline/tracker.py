from datetime import datetime, timedelta

class SpatialTemporalReIDTracker:
    def __init__(self, time_window_seconds=8.0):
        self.time_window = time_window_seconds
        self.global_visitor_registry = {}  # global_id -> info dict
        self.camera_local_to_global = {}   # camera_id_track_id -> global_id
        self.global_counter = 1000
        
        # Entrance coordinate region on CAM_1 (near the door)
        # Coordinates of the door in CAM_1 frame coordinates (approximate based on layout)
        self.cam1_entrance_polygon = [[0, 600], [400, 600], [400, 1080], [0, 1080]]
        
    def get_global_visitor_id(self, local_visitor_id, camera_id, timestamp_str, bounding_box=None):
        """
        Correlates a local camera visitor track ID to a global visitor ID 
        using spatial-temporal proximity rules.
        """
        local_key = f"{camera_id}_{local_visitor_id}"
        
        # 1. If already mapped, return the cached global ID
        if local_key in self.camera_local_to_global:
            return self.camera_local_to_global[local_key]
            
        clean_time = timestamp_str.replace("Z", "")
        event_time = datetime.fromisoformat(clean_time)
        
        # 2. Check if this is an ENTRY camera event (CAM_3)
        if camera_id == "CAM_3":
            # Start a brand new global visit session
            global_id = f"VIS_GLB_{self.global_counter}"
            self.global_counter += 1
            
            self.camera_local_to_global[local_key] = global_id
            self.global_visitor_registry[global_id] = {
                "first_seen": event_time,
                "last_seen": event_time,
                "cameras_visited": {camera_id},
                "last_camera": camera_id,
                "latest_position": None
            }
            return global_id
            
        # 3. If it's a floor camera (CAM_1, CAM_2, CAM_5) and we have a new track:
        # Check if we can correlate it with a recent ENTRY event on CAM_3
        # that occurred within the time window.
        if camera_id in ["CAM_1", "CAM_2"]:
            # Find the most recent CAM_3 entry that is not yet matched to this camera
            best_match_id = None
            min_time_diff = self.time_window
            
            for g_id, reg_info in self.global_visitor_registry.items():
                if "CAM_3" in reg_info["cameras_visited"] and camera_id not in reg_info["cameras_visited"]:
                    time_diff = (event_time - reg_info["first_seen"]).total_seconds()
                    
                    # If this floor track appeared shortly after the visitor entered the store
                    if 0 <= time_diff < min_time_diff:
                        min_time_diff = time_diff
                        best_match_id = g_id
                        
            if best_match_id:
                # Merge the local track into the global visitor session!
                self.camera_local_to_global[local_key] = best_match_id
                self.global_visitor_registry[best_match_id]["cameras_visited"].add(camera_id)
                self.global_visitor_registry[best_match_id]["last_seen"] = event_time
                self.global_visitor_registry[best_match_id]["last_camera"] = camera_id
                return best_match_id

        # 4. If we couldn't correlate (or it's a camera where people transition from aisles, e.g. Floor -> Billing CAM_5):
        # Check if another track recently exited the previous zone and this one started nearby.
        # For simplicity, if we see a transition, check if we can bind it to the last active global session on that camera.
        best_match_id = None
        min_time_diff = self.time_window
        
        for g_id, reg_info in self.global_visitor_registry.items():
            time_diff = abs((event_time - reg_info["last_seen"]).total_seconds())
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                best_match_id = g_id
                
        if best_match_id:
            self.camera_local_to_global[local_key] = best_match_id
            self.global_visitor_registry[best_match_id]["cameras_visited"].add(camera_id)
            self.global_visitor_registry[best_match_id]["last_seen"] = event_time
            self.global_visitor_registry[best_match_id]["last_camera"] = camera_id
            return best_match_id
            
        # 5. Fallback: Create a new global ID if no match is found
        global_id = f"VIS_GLB_{self.global_counter}"
        self.global_counter += 1
        self.camera_local_to_global[local_key] = global_id
        self.global_visitor_registry[global_id] = {
            "first_seen": event_time,
            "last_seen": event_time,
            "cameras_visited": {camera_id},
            "last_camera": camera_id,
            "latest_position": None
        }
        return global_id
