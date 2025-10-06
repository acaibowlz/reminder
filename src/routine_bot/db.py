import logging

import psycopg
from psycopg.types.json import Json

from routine_bot.constants import DATABASE_URL
from routine_bot.models import ChatData, EventData

logger = logging.getLogger(__name__)

conn = psycopg.connect(conninfo=DATABASE_URL)


def table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
    return cur.fetchone()[0] is not None


def create_users_table(cur: psycopg.Cursor) -> None:
    """
    Users Table
    -----------
    - user_id :
        Unique identifier for each user (corresponds to the LINE user ID).
    - created_at :
        Timestamp when the user record was created.
    - display_name :
        Display name of the user, retrieved from LINE's Get Profile API.
    - picture_url :
        URL of the user's profile picture, retrieved from LINE's Get Profile API.
    - profile_refreshed_at :
        Timestamp of the most recent update from LINE's Get Profile API.
    - event_count :
        Total number of events owned by the user.
    - is_premium :
        Indicates whether the user is subscribed to a premium plan.
    - premium_until :
        Expiration timestamp of the user's premium feature access.
        Users can unsubscribe at any time, but premium access remains active until this timestamp.
    - is_blocked :
        Indicates whether the user has blocked the bot
    """
    cur.execute(
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            display_name TEXT NOT NULL,
            picture_url TEXT NOT NULL,
            profile_refreshed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_count INTEGER NOT NULL DEFAULT 0,
            is_premium BOOLEAN NOT NULL DEFAULT FALSE,
            premium_until TIMESTAMPTZ,
            is_blocked BOOLEAN NOT NULL DEFAULT FALSE
        )
        """
    )


def create_chats_table(cur: psycopg.Cursor) -> None:
    """
    Chats Table
    ------------
    - chat_id :
        Unique identifier for each chat session.
    - created_at :
        Timestamp indicating when the chat record was created.
    - user_id :
        Identifier of the user associated with the chat session.
    - chat_type :
        Specifies the purpose of the chat, i.e., which event or action is being processed.
        Refer to `ChatType` in `constants.py`.
    - current_step :
        Indicates the current processing stage within the chat workflow.
        Refer to the corresponding `*Steps` constants in `constants.py`.
        Set to NULL when the chat session is completed.
    - payload :
        JSON object containing intermediate data collected during the chat flow.
    - is_completed :
        Indicates whether the chat session has been completed.
    """
    cur.execute(
        """
        CREATE TABLE chats (
            chat_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            user_id TEXT NOT NULL REFERENCES users(user_id),
            chat_type TEXT NOT NULL,
            current_step TEXT,
            payload JSON,
            is_completed BOOLEAN NOT NULL DEFAULT FALSE
        )
        """
    )


def create_events_table(cur: psycopg.Cursor) -> None:
    """
    Events Table
    ------------
    - event_id :
        Unique identifier for each event.
    - created_at :
        Timestamp indicating when the event record was created.
    - event_name :
        Name of the event.
    - user_id :
        Identifier of the user who owns the event.
    - last_done_at :
        Timestamp of the most recent time the user completed the event.
        Event completion timestamps are stored at day-level precision,
        with the time set to 00:00 (UTC+8).
    - reminder :
        Indicates whether reminders are enabled for the event.
    - reminder_cycle :
        Specifies the recurrence interval of the reminder (e.g., daily, weekly).
    - next_reminder :
        If the current time is later than this timestamp, the reminder is considered due,
        and the bot will send the reminder on its next scheduled run.
    - share_count :
        The number of users this event is shared with.
        All shared users will also receive reminder notifications.
    - is_active :
        If a user blocks the bot, the events they own are marked as inactive,
        and their associated reminders will no longer be triggered.
    """

    cur.execute(
        """
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_name TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(user_id),
            last_done_at TIMESTAMPTZ NOT NULL,
            reminder BOOLEAN NOT NULL,
            reminder_cycle TEXT,
            next_reminder TIMESTAMPTZ,
            share_count INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        )
        """
    )


def create_updates_table(cur: psycopg.Cursor) -> None:
    """
    Updates Table
    --------------
    - update_id :
        Unique identifier for each update entry.
        This table records every instance in which a user updates
        the completion time of an event.
    - created_at :
        Timestamp indicating when the update entry was created.
    - event_id :
        Identifier of the event associated with this update.
    - event_name :
        Name of the event associated with this update.
    - user_id :
        Identifier of the user who owns the event.
    - done_at :
        Timestamp representing the newly updated completion time of the event.
        Event completion times are stored with day-level precision,
        with the time component normalized to 00:00 (UTC+8).
    """
    cur.execute(
        """
        CREATE TABLE updates (
            update_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_id TEXT NOT NULL REFERENCES events(event_id),
            event_name TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(user_id),
            done_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def create_shares_table(cur: psycopg.Cursor) -> None:
    """
    Shares Table
    ------------
    - share_id :
        Unique identifier for each share record.
        The shared events will also send reminder notification to receipients.
    - created_at :
        Timestamp indicating when the share record was created.
    - event_id :
        Identifier of the event being shared.
    - event_name :
        Name of the event being shared.
    - owner_id :
        Identifier of the user who owns the event.
    - recipient_id :
        Identifier of the user with whom the event is shared.
    """
    cur.execute(
        """
        CREATE TABLE shares (
            share_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_id TEXT NOT NULL REFERENCES events(event_id),
            event_name TEXT NOT NULL,
            owner_id TEXT NOT NULL REFERENCES users(user_id),
            recipient_id TEXT NOT NULL
        )
        """
    )


def init_db(conn: psycopg.Connection):
    table_creators = {
        "users": create_users_table,
        "chats": create_chats_table,
        "events": create_events_table,
        "updates": create_updates_table,
        "shares": create_shares_table,
    }
    with conn.cursor() as cur:
        for table, creator_func in table_creators.items():
            if table_exists(cur, table):
                continue
            creator_func(cur)
            logger.info(f"Table created: {table}")
    conn.commit()
    logger.info("Database initialized")


# -------------------------------- User Table -------------------------------- #


def add_user(user_id: str, display_name: str, picture_url: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (user_id, display_name, picture_url, premium_until)
            VALUES (%s, %s, %s, %s)
            """,
            (
                user_id,
                display_name,
                picture_url,
                None,
            ),
        )
    conn.commit()
    logger.info(f"User inserted: {user_id}")


# -------------------------------- Chat Table -------------------------------- #


def add_chat(chat: ChatData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chats (chat_id, user_id, chat_type, current_step, payload)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                chat.chat_id,
                chat.user_id,
                chat.chat_type,
                chat.current_step,
                Json(chat.payload),
            ),
        )
    conn.commit()
    logger.info(f"Chat inserted: {chat.chat_id}")


def update_chat(chat: ChatData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chats
            SET current_step = %s,
                payload       = %s,
                is_completed  = %s
            WHERE chat_id     = %s
            """,
            (
                chat.current_step,
                Json(chat.payload),
                chat.is_completed,
                chat.chat_id,
            ),
        )
    conn.commit()
    logger.info(f"Chat updated: {chat.chat_id}")


def get_ongoing_chat(user_id: str, conn: psycopg.Connection) -> ChatData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chat_id, user_id, chat_type, current_step, payload, is_completed
            FROM chats
            WHERE user_id = %s AND is_completed = %s
            """,
            (user_id, False),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return ChatData(*result)


# -------------------------------- Event Table ------------------------------- #


def add_event(event_data: EventData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO events (event_id, event_name, user_id, last_done_at, reminder, reminder_cycle, next_reminder)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event_data.event_id,
                event_data.event_name,
                event_data.user_id,
                event_data.last_done_at,
                event_data.reminder,
                event_data.reminder_cycle,
                event_data.next_reminder,
            ),
        )
    conn.commit()
    logger.info(f"Event inserted: {event_data.event_id}")


def get_event_id(user_id: str, event_name: str, conn: psycopg.Connection) -> str | None:
    with conn.cursor() as cur:
        cur.execute("SELECT event_id FROM events WHERE user_id = %s AND event_name = %s", (user_id, event_name))
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]


def get_event_data(user_id: str, event_name: str, conn: psycopg.Connection) -> EventData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT event_id, event_name, user_id, last_done_at, reminder, reminder_cycle, next_reminder, share_count
            FROM events
            WHERE user_id = %s AND event_name = %s
            """,
            (user_id, event_name),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return EventData(*result)


def get_all_active_events_with_reminder(conn: psycopg.Connection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT event_id FROM events WHERE is_active = true AND reminder = true")
        result = cur.fetchall()
        return [row[0] for row in result]


def update_event():
    pass
