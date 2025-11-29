"""Home Assistant camera adapter."""
import os
from typing import Optional

import aiohttp

from app.core.models import Camera


class HACamera:
    """Home Assistant camera adapter."""
    
    def __init__(self):
        self.supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "")
        self.ha_base_url = os.environ.get("HA_BASE_URL", "http://supervisor/core")
    
    async def get_cameras(self) -> list[Camera]:
        """Get list of camera entities from Home Assistant."""
        if not self.supervisor_token:
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.supervisor_token}"}
                url = f"{self.ha_base_url}/api/states"
                
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return []
                    
                    states = await response.json()
            
            cameras = []
            for state in states:
                entity_id = state.get("entity_id", "")
                if entity_id.startswith("camera."):
                    cameras.append(Camera(
                        entity_id=entity_id,
                        name=state.get("attributes", {}).get("friendly_name", entity_id),
                        state=state.get("state", "unknown")
                    ))
            
            return cameras
            
        except Exception as e:
            print(f"Error fetching cameras: {e}")
            return []
    
    async def get_snapshot(self, entity_id: str) -> Optional[bytes]:
        """Get a snapshot from a camera."""
        if not self.supervisor_token:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.supervisor_token}"}
                url = f"{self.ha_base_url}/api/camera_proxy/{entity_id}"
                
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status != 200:
                        print(f"Failed to get snapshot: {response.status}")
                        return None
                    
                    return await response.read()
                    
        except Exception as e:
            print(f"Error getting snapshot: {e}")
            return None
    
    async def test_camera(self, entity_id: str) -> bool:
        """Test if a camera is accessible."""
        snapshot = await self.get_snapshot(entity_id)
        return snapshot is not None and len(snapshot) > 0
