"""SQLite database for TwinSync Spot."""
import json
from datetime import datetime, timedelta
from typing import Optional
import aiosqlite

from app.core.models import Spot, SpotStatus, CheckResult, SpotMemory
from app.core.memory import MemoryEngine


class Database:
    """SQLite database handler."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
    
    async def init(self):
        """Initialize database and create tables."""
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS spots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                camera_entity TEXT NOT NULL,
                definition TEXT NOT NULL,
                spot_type TEXT NOT NULL DEFAULT 'custom',
                voice TEXT NOT NULL DEFAULT 'supportive',
                custom_voice_prompt TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unknown',
                last_check TEXT,
                current_streak INTEGER NOT NULL DEFAULT 0,
                longest_streak INTEGER NOT NULL DEFAULT 0,
                snoozed_until TEXT,
                total_resets INTEGER NOT NULL DEFAULT 0,
                last_reset TEXT
            );
            
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spot_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                to_sort_json TEXT,
                looking_good_json TEXT,
                notes_main TEXT,
                notes_pattern TEXT,
                notes_encouragement TEXT,
                error_message TEXT,
                api_response_time REAL,
                FOREIGN KEY (spot_id) REFERENCES spots(id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_checks_spot_id ON checks(spot_id);
            CREATE INDEX IF NOT EXISTS idx_checks_timestamp ON checks(timestamp);
        """)
        await self.conn.commit()
    
    async def close(self):
        """Close database connection."""
        if self.conn:
            await self.conn.close()
    
    # Spot operations
    async def create_spot(self, name: str, camera_entity: str, definition: str,
                          spot_type: str = "custom", voice: str = "supportive",
                          custom_voice_prompt: str = None) -> int:
        """Create a new spot."""
        now = datetime.utcnow().isoformat()
        cursor = await self.conn.execute(
            """INSERT INTO spots (name, camera_entity, definition, spot_type, voice, 
               custom_voice_prompt, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, camera_entity, definition, spot_type, voice, custom_voice_prompt, now, "unknown")
        )
        await self.conn.commit()
        return cursor.lastrowid
    
    async def get_spot(self, spot_id: int) -> Optional[Spot]:
        """Get a spot by ID."""
        cursor = await self.conn.execute(
            "SELECT * FROM spots WHERE id = ?", (spot_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_spot(row)
    
    async def get_all_spots(self) -> list[Spot]:
        """Get all spots."""
        cursor = await self.conn.execute("SELECT * FROM spots ORDER BY name")
        rows = await cursor.fetchall()
        return [self._row_to_spot(row) for row in rows]
    
    async def update_spot(self, spot_id: int, **kwargs) -> bool:
        """Update a spot."""
        if not kwargs:
            return False
        
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [spot_id]
        
        cursor = await self.conn.execute(
            f"UPDATE spots SET {set_clause} WHERE id = ?", values
        )
        await self.conn.commit()
        return cursor.rowcount > 0
    
    async def delete_spot(self, spot_id: int) -> bool:
        """Delete a spot."""
        cursor = await self.conn.execute(
            "DELETE FROM spots WHERE id = ?", (spot_id,)
        )
        await self.conn.commit()
        return cursor.rowcount > 0
    
    # Check operations
    async def save_check(self, spot_id: int, result: CheckResult) -> int:
        """Save a check result."""
        now = datetime.utcnow().isoformat()
        
        to_sort_json = json.dumps([item.__dict__ if hasattr(item, '__dict__') else item 
                                   for item in (result.to_sort or [])])
        looking_good_json = json.dumps(result.looking_good or [])
        
        cursor = await self.conn.execute(
            """INSERT INTO checks (spot_id, timestamp, status, to_sort_json, looking_good_json,
               notes_main, notes_pattern, notes_encouragement, error_message, api_response_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (spot_id, now, result.status, to_sort_json, looking_good_json,
             result.notes.get("main") if result.notes else None,
             result.notes.get("pattern") if result.notes else None,
             result.notes.get("encouragement") if result.notes else None,
             result.error_message, result.api_response_time)
        )
        await self.conn.commit()
        
        # Update spot status
        await self.update_spot(spot_id, status=result.status, last_check=now)
        
        return cursor.lastrowid
    
    async def get_recent_checks(self, spot_id: int, limit: int = 10) -> list[dict]:
        """Get recent checks for a spot."""
        cursor = await self.conn.execute(
            """SELECT * FROM checks WHERE spot_id = ? 
               ORDER BY timestamp DESC LIMIT ?""",
            (spot_id, limit)
        )
        rows = await cursor.fetchall()
        return [self._row_to_check(row) for row in rows]
    
    async def get_checks_since(self, spot_id: int, since: datetime) -> list[dict]:
        """Get checks since a certain date."""
        cursor = await self.conn.execute(
            """SELECT * FROM checks WHERE spot_id = ? AND timestamp >= ?
               ORDER BY timestamp ASC""",
            (spot_id, since.isoformat())
        )
        rows = await cursor.fetchall()
        return [self._row_to_check(row) for row in rows]
    
    async def get_spot_memory(self, spot_id: int) -> SpotMemory:
        """Get memory/patterns for a spot."""
        # Get checks from last 30 days
        since = datetime.utcnow() - timedelta(days=30)
        checks = await self.get_checks_since(spot_id, since)
        
        spot = await self.get_spot(spot_id)
        
        # Use MemoryEngine to calculate patterns
        engine = MemoryEngine()
        return engine.calculate_memory(spot_id, checks, spot)
    
    async def record_reset(self, spot_id: int):
        """Record a reset (user marked spot as fixed)."""
        spot = await self.get_spot(spot_id)
        if not spot:
            return
        
        now = datetime.utcnow().isoformat()
        new_streak = spot.current_streak + 1
        longest = max(spot.longest_streak, new_streak)
        
        await self.update_spot(
            spot_id,
            status="sorted",
            current_streak=new_streak,
            longest_streak=longest,
            total_resets=spot.total_resets + 1,
            last_reset=now
        )
    
    def _row_to_spot(self, row) -> Spot:
        """Convert database row to Spot object."""
        return Spot(
            id=row["id"],
            name=row["name"],
            camera_entity=row["camera_entity"],
            definition=row["definition"],
            spot_type=row["spot_type"],
            voice=row["voice"],
            custom_voice_prompt=row["custom_voice_prompt"],
            created_at=row["created_at"],
            status=SpotStatus(row["status"]) if row["status"] else SpotStatus.UNKNOWN,
            last_check=row["last_check"],
            current_streak=row["current_streak"],
            longest_streak=row["longest_streak"],
            snoozed_until=row["snoozed_until"],
            total_resets=row["total_resets"],
            last_reset=row["last_reset"],
        )
    
    def _row_to_check(self, row) -> dict:
        """Convert database row to check dict."""
        return {
            "id": row["id"],
            "spot_id": row["spot_id"],
            "timestamp": row["timestamp"],
            "status": row["status"],
            "to_sort": json.loads(row["to_sort_json"]) if row["to_sort_json"] else [],
            "looking_good": json.loads(row["looking_good_json"]) if row["looking_good_json"] else [],
            "notes": {
                "main": row["notes_main"],
                "pattern": row["notes_pattern"],
                "encouragement": row["notes_encouragement"],
            },
            "error_message": row["error_message"],
            "api_response_time": row["api_response_time"],
        }
