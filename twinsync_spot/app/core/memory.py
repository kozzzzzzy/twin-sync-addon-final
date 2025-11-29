"""Memory Engine for TwinSync Spot - THE KILLER FEATURE.

This module analyzes check history to detect patterns:
- Recurring items that keep appearing
- Best/worst days
- Usual times when sorted
- Streaks
"""
from collections import Counter
from datetime import datetime
from typing import Optional

from app.core.models import SpotMemory, SpotPatterns, Spot


# How many times an item must appear to be "recurring"
RECURRING_THRESHOLD = 3

# How many days of history to consider
MEMORY_RETENTION_DAYS = 30


class MemoryEngine:
    """Analyzes check history to detect patterns."""
    
    def calculate_memory(self, spot_id: int, checks: list[dict], spot: Optional[Spot] = None) -> SpotMemory:
        """Calculate memory/patterns from check history."""
        if not checks:
            return SpotMemory(
                spot_id=spot_id,
                current_streak=spot.current_streak if spot else 0,
                longest_streak=spot.longest_streak if spot else 0,
            )
        
        patterns = SpotPatterns(
            recurring_items=self._count_recurring_items(checks),
            worst_day=self._find_worst_day(checks),
            best_day=self._find_best_day(checks),
            usually_sorted_by=self._find_usual_sorted_time(checks),
        )
        
        last_check = checks[-1] if checks else None
        
        return SpotMemory(
            spot_id=spot_id,
            patterns=patterns,
            current_streak=spot.current_streak if spot else 0,
            longest_streak=spot.longest_streak if spot else 0,
            total_checks=len(checks),
            last_check_status=last_check["status"] if last_check else None,
        )
    
    def _count_recurring_items(self, checks: list[dict]) -> dict[str, int]:
        """Count how many times each item appears in to_sort."""
        counter = Counter()
        
        for check in checks:
            to_sort = check.get("to_sort", [])
            for item in to_sort:
                # Handle both dict and string formats
                if isinstance(item, dict):
                    item_name = item.get("item", "").lower().strip()
                else:
                    item_name = str(item).lower().strip()
                
                if item_name:
                    counter[item_name] += 1
        
        # Only return items that appear at least RECURRING_THRESHOLD times
        return {item: count for item, count in counter.items() 
                if count >= RECURRING_THRESHOLD}
    
    def _find_worst_day(self, checks: list[dict]) -> Optional[str]:
        """Find the day of week with most 'needs_attention' statuses."""
        day_counts = Counter()
        
        for check in checks:
            if check.get("status") == "needs_attention":
                try:
                    dt = datetime.fromisoformat(check["timestamp"])
                    day_counts[dt.strftime("%A")] += 1
                except (ValueError, KeyError):
                    pass
        
        if not day_counts:
            return None
        
        return day_counts.most_common(1)[0][0]
    
    def _find_best_day(self, checks: list[dict]) -> Optional[str]:
        """Find the day of week with most 'sorted' statuses."""
        day_counts = Counter()
        
        for check in checks:
            if check.get("status") == "sorted":
                try:
                    dt = datetime.fromisoformat(check["timestamp"])
                    day_counts[dt.strftime("%A")] += 1
                except (ValueError, KeyError):
                    pass
        
        if not day_counts:
            return None
        
        return day_counts.most_common(1)[0][0]
    
    def _find_usual_sorted_time(self, checks: list[dict]) -> Optional[str]:
        """Find the usual time when spot is sorted."""
        hour_counts = Counter()
        
        for check in checks:
            if check.get("status") == "sorted":
                try:
                    dt = datetime.fromisoformat(check["timestamp"])
                    hour_counts[dt.hour] += 1
                except (ValueError, KeyError):
                    pass
        
        if not hour_counts:
            return None
        
        most_common_hour = hour_counts.most_common(1)[0][0]
        
        # Format nicely
        if most_common_hour == 0:
            return "midnight"
        elif most_common_hour == 12:
            return "noon"
        elif most_common_hour < 12:
            return f"{most_common_hour}:00 AM"
        else:
            return f"{most_common_hour - 12}:00 PM"
    
    def build_memory_context(self, memory: SpotMemory) -> str:
        """Build context string for AI prompt."""
        lines = []
        
        if memory.total_checks == 0:
            return "First check - no history yet."
        
        lines.append(f"Total checks: {memory.total_checks}")
        
        if memory.last_check_status:
            lines.append(f"Last check: {memory.last_check_status}")
        
        if memory.current_streak > 0:
            lines.append(f"Current streak: {memory.current_streak} days")
        
        if memory.patterns.recurring_items:
            top_items = list(memory.patterns.recurring_items.items())[:3]
            items_str = ", ".join(f"{item} ({count}x)" for item, count in top_items)
            lines.append(f"Recurring items: {items_str}")
        
        if memory.patterns.worst_day:
            lines.append(f"Worst day: {memory.patterns.worst_day}")
        
        if memory.patterns.best_day:
            lines.append(f"Best day: {memory.patterns.best_day}")
        
        if memory.patterns.usually_sorted_by:
            lines.append(f"Usually sorted by: {memory.patterns.usually_sorted_by}")
        
        return "\n".join(lines) if lines else "No patterns detected yet."
    
    def enrich_items_with_recurring(self, items: list, recurring_items: dict[str, int]) -> list:
        """Add recurring flag and count to items based on memory."""
        enriched = []
        
        for item in items:
            if isinstance(item, dict):
                item_name = item.get("item", "").lower().strip()
                if item_name in recurring_items:
                    item["recurring"] = True
                    item["recurrence_count"] = recurring_items[item_name]
                else:
                    item["recurring"] = False
                enriched.append(item)
            else:
                item_name = str(item).lower().strip()
                if item_name in recurring_items:
                    enriched.append({
                        "item": str(item),
                        "recurring": True,
                        "recurrence_count": recurring_items[item_name]
                    })
                else:
                    enriched.append({
                        "item": str(item),
                        "recurring": False
                    })
        
        return enriched
