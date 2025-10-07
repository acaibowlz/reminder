from dataclasses import dataclass, field
from datetime import datetime

from src.routine_bot.enums import ChatStatus


@dataclass
class UserData:
    user_id: str
    display_name: str
    picturl_url: str
    profile_refreshed_at: datetime
    event_count: int
    is_premium: bool
    premium_until: datetime | None
    is_blocked: bool


@dataclass
class EventData:
    event_id: str
    event_name: str
    user_id: str
    last_done_at: datetime
    reminder: bool
    reminder_cycle: str | None = None
    next_reminder: datetime | None = None
    share_count: int = 0


@dataclass
class ChatData:
    chat_id: str
    user_id: str
    chat_type: str
    current_step: str | None
    payload: dict = field(default_factory=dict)
    status: str = ChatStatus.ONGOING
