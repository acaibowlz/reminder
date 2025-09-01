from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserData:
    user_id: str
    display_name: str
    picturl_url: str
    profile_refreshed_at: datetime
    event_count: int
    is_premium: bool
    premium_until: Optional[datetime]
    is_blocked: bool


@dataclass
class EventData:
    event_id: str
    event_name: str
    user_id: str
    last_done_at: datetime
    has_reminder: bool
    cycle_count: Optional[int] = None
    cycle_unit: Optional[str] = None
    cycle_ends_at: Optional[datetime] = None
    share_count: int = 0
    is_active: bool = False


@dataclass
class ChatData:
    chat_id: str
    user_id: str
    chat_type: str
    current_state: int
    state_data: dict
    is_completed: bool
