import logging
from datetime import datetime

import psycopg
from psycopg.types.json import Json

from routine_bot.constants import TZ_TAIPEI
from routine_bot.enums import ChatStatus
from routine_bot.models import ChatData, EventData, ShareData, UpdateData, UserData

logger = logging.getLogger(__name__)


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
    - notification_time :
        Daily time-of-day (without date) when the user prefers to receive notifications.
    - event_count :
        Total number of events owned by the user.
        Users on free plan can have up to 5 events.
    - is_premium :
        Indicates whether the user is subscribed to a premium plan.
    - premium_until :
        Expiration timestamp of the user's premium feature access.
        Users can unsubscribe at any time, but premium access remains active until this timestamp.
        Post-expiration behavior for users with > 5 events:
        - Can view, update, edit, and delete all existing events
        - Cannot create new events until event_count <= 5 or premium is renewed
        - Will NOT receive notifications/reminders for any events while over the 5-event limit
        (notifications resume once event_count <= 5 or premium is renewed)
    - is_active :
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
            notification_time TIME NOT NULL DEFAULT '00:00',
            event_count INTEGER NOT NULL DEFAULT 0,
            is_premium BOOLEAN NOT NULL DEFAULT FALSE,
            premium_until TIMESTAMPTZ,
            is_active BOOLEAN NOT NULL DEFAULT FALSE
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
    - status :
        The current status of the chat session.
        Refer to `ChatStatus` in `constants.py`.
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
            status TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chats_user_status ON chats (user_id, status)")


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
    - last_notification_sent_at:
        Timestamp indicating when the last reminder notification is sent.
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
            last_notification_sent_at TIMESTAMPTZ,
            share_count INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            -- Prevent duplicate event names per user
            UNIQUE (user_id, event_name)
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
            VALUES (%s, %s, %s, NULL)
            """,
            (user_id, display_name, picture_url),
        )
    conn.commit()
    logger.info(f"User inserted: {user_id}")


def get_user(user_id: str, conn: psycopg.Connection) -> UserData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT user_id, display_name, picture_url, profile_refreshed_at, notification_time, event_count, is_premium, premium_until, is_active
            FROM users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return UserData(*result)


def is_user_exists(user_id: str, conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM users
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        return cur.fetchone() is not None


def set_user_profile(user_id: str, display_name: str, picture_url: str, conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET display_name = %s,
                picture_url = %s,
                profile_refreshed_at = %s
            WHERE user_id = %s
            """,
            (display_name, picture_url, datetime.now(tz=TZ_TAIPEI), user_id),
        )
    conn.commit()
    logger.info(f"User profile updated: {user_id}")


def increment_user_event_count(user_id: str, by: int, conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET event_count = event_count + %s
            WHERE user_id = %s
            """,
            (by, user_id),
        )
    conn.commit()
    logger.info(f"User event count updated by {by}")


def set_user_activeness(user_id: str, to: bool, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET is_active = %s
            WHERE user_id = %s
            """,
            (to, user_id),
        )
    conn.commit()
    logger.info(f"User activeness updated: {user_id}")


# -------------------------------- Chat Table -------------------------------- #


def add_chat(chat: ChatData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chats (chat_id, user_id, chat_type, current_step, payload, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                chat.chat_id,
                chat.user_id,
                chat.chat_type,
                chat.current_step,
                Json(chat.payload),
                ChatStatus.ONGOING.value,
            ),
        )
    conn.commit()
    logger.info(f"Chat inserted: {chat.chat_id}")


def get_chat(chat_id: str, conn: psycopg.Connection) -> ChatData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chat_id, user_id, chat_type, current_step, payload, status
            FROM chats
            WHERE chat_id = %s
            """,
            (chat_id,),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return ChatData(*result)


def get_ongoing_chat_id(user_id: str, conn: psycopg.Connection) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chat_id
            FROM chats
            WHERE user_id = %s AND status = %s
            """,
            (user_id, ChatStatus.ONGOING.value),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]


def set_chat_current_step(chat_id: str, current_step: str | None, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chats
            SET current_step = %s
            WHERE chat_id = %s
            """,
            (current_step, chat_id),
        )
    conn.commit()
    logger.info(f"Chat current_step updated: {chat_id}")


def set_chat_payload(chat_id: str, payload: dict, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chats
            SET payload = %s
            WHERE chat_id = %s
            """,
            (Json(payload), chat_id),
        )
    conn.commit()
    logger.info(f"Chat payload updated: {chat_id}")


def set_chat_status(chat_id: str, status: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chats
            SET status = %s
            WHERE chat_id = %s
            """,
            (status, chat_id),
        )
    conn.commit()
    logger.info(f"Chat status updated: {chat_id}")


# -------------------------------- Event Table ------------------------------- #


def add_event(event: EventData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO events (event_id, event_name, user_id, last_done_at, reminder, reminder_cycle, next_reminder)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event.event_id,
                event.event_name,
                event.user_id,
                event.last_done_at,
                event.reminder,
                event.reminder_cycle,
                event.next_reminder,
            ),
        )
    conn.commit()
    logger.info(f"Event inserted: {event.event_id}")


def get_event(event_id: str, conn: psycopg.Connection) -> EventData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT event_id, event_name, user_id, last_done_at, reminder, reminder_cycle, next_reminder, last_notification_sent_at, share_count
            FROM events
            WHERE event_id = %s
            """,
            (event_id,),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return EventData(*result)


def get_event_id(user_id: str, event_name: str, conn: psycopg.Connection) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT event_id
            FROM events
            WHERE user_id = %s AND event_name = %s
            """,
            (user_id, event_name),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]


# def get_all_events_by_user(user_id: str, conn: psycopg.Connection) -> list[str]:
#     with conn.cursor() as cur:
#         cur.execute(
#             """
#             SELECT event_id
#             FROM events
#             WHERE user_id = %s
#             """,
#             (user_id,),
#         )
#         result = cur.fetchall()
#         return [row[0] for row in result]


# def get_events_with_due_reminders(conn: psycopg.Connection) -> list[str]:
#     with conn.cursor() as cur:
#         cur.execute(
#             """
#             SELECT event_id
#             FROM events
#             WHERE is_active = TRUE
#               AND reminder = TRUE
#               AND next_reminder <= NOW()
#             """,
#         )
#         result = cur.fetchall()
#         return [EventData(*row) for row in result]


def set_event_activeness(event_id: str, to: bool, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET is_active = %s
            WHERE event_id = %s
            """,
            (to, event_id),
        )
    conn.commit()
    logger.info(f"Event activeness updated: {event_id}")


# ------------------------------- Update Table ------------------------------- #


def add_update(update: UpdateData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO updates (update_id, event_id, event_name, user_id, done_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                update.update_id,
                update.event_id,
                update.event_name,
                update.user_id,
                update.done_at,
            ),
        )
    conn.commit()
    logger.info(f"Update inserted: {update.update_id}")


def get_event_recent_update_times(event_id: str, conn: psycopg.Connection, limit: int = 10) -> list[datetime]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT done_at
            FROM updates
            WHERE event_id = %s
            ORDER BY done_at DESC
            LIMIT %s
            """,
            (event_id, limit),
        )
        result = cur.fetchall()
        return [row[0] for row in result]


# ------------------------------- Share Table -------------------------------- #


def add_share(share: ShareData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO shares (share_id, event_id, event_name, owner_id, recipient_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                share.share_id,
                share.event_id,
                share.event_name,
                share.owner_id,
                share.recipient_id,
            ),
        )
    conn.commit()
    logger.info(f"Share inserted: {share.share_id}")
