"""Core models for TwinSync Spot."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SpotType(Enum):
    """Types of spots with templates."""
    WORK = "work"
    CHILL = "chill"
    SLEEP = "sleep"
    KITCHEN = "kitchen"
    ENTRYWAY = "entryway"
    STORAGE = "storage"
    CUSTOM = "custom"


class SpotStatus(Enum):
    """Status of a spot."""
    SORTED = "sorted"
    NEEDS_ATTENTION = "needs_attention"
    ERROR = "error"
    UNKNOWN = "unknown"
    SNOOZED = "snoozed"


# Templates for each spot type
SPOT_TEMPLATES = {
    "work": """This is my work area. I need a clear surface to focus.

Things that should be here:
- Laptop/monitor
- Keyboard and mouse
- Notepad/pen

Things that shouldn't be here:
- Coffee cups or dishes
- Random papers
- Clutter""",

    "chill": """This is where I relax. Should feel calm and uncluttered.

Things that are fine here:
- Remote controls
- Blankets/pillows
- Books I'm reading

Things that shouldn't pile up:
- Empty cups/plates
- Random items
- Clutter""",

    "sleep": """This is my sleep space. Should be calm and ready for rest.

Ready state:
- Bed made
- No clothes on floor
- Nightstand clear except essentials""",

    "kitchen": """This is my kitchen area. Should be clear and ready to use.

Ready state:
- Counters clear
- Dishes put away
- No food left out""",

    "entryway": """This is my entryway. First thing I see coming home.

Ready state:
- Shoes in rack/organised
- No bags on floor
- Keys in place""",

    "storage": """This is a storage area. Things should be organised.

What belongs here:
- Specific items for this space

Signs it needs sorting:
- Items out of place
- Things piling up""",

    "custom": """Describe this space in your own words.

What is it for?
What should it look like when ready?
What shouldn't be here?"""
}


@dataclass
class ToSortItem:
    """An item that needs sorting."""
    item: str
    location: Optional[str] = None
    recurring: bool = False
    recurrence_count: int = 0


@dataclass
class CheckResult:
    """Result of a spot check."""
    status: str
    to_sort: list = field(default_factory=list)
    looking_good: list = field(default_factory=list)
    notes: dict = field(default_factory=dict)
    error_message: Optional[str] = None
    api_response_time: Optional[float] = None


@dataclass
class SpotPatterns:
    """Patterns detected for a spot."""
    recurring_items: dict = field(default_factory=dict)  # {"coffee mug": 12}
    usually_sorted_by: Optional[str] = None  # "10:00 AM"
    worst_day: Optional[str] = None  # "Monday"
    best_day: Optional[str] = None  # "Friday"


@dataclass
class SpotMemory:
    """Memory/history for a spot."""
    spot_id: int
    patterns: SpotPatterns = field(default_factory=SpotPatterns)
    current_streak: int = 0
    longest_streak: int = 0
    total_checks: int = 0
    last_check_status: Optional[str] = None


@dataclass
class Spot:
    """A spot being tracked."""
    id: int
    name: str
    camera_entity: str
    definition: str
    spot_type: str = "custom"
    voice: str = "supportive"
    custom_voice_prompt: Optional[str] = None
    created_at: Optional[str] = None
    status: SpotStatus = SpotStatus.UNKNOWN
    last_check: Optional[str] = None
    current_streak: int = 0
    longest_streak: int = 0
    snoozed_until: Optional[str] = None
    total_resets: int = 0
    last_reset: Optional[str] = None


@dataclass
class Camera:
    """A camera entity."""
    entity_id: str
    name: str
    state: str = "unknown"
