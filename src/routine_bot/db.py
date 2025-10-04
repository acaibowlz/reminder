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
    cur.execute(
        """
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_name TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(user_id),
            last_done_at TIMESTAMPTZ NOT NULL,
            reminder BOOLEAN NOT NULL,
            cycle_period TEXT,
            cycle_ends_at TIMESTAMPTZ,
            share_count INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        )
        """
    )


def create_records_table(cur: psycopg.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE records (
            record_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_id TEXT NOT NULL REFERENCES events(event_id),
            event_name TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(user_id),
            done_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def create_shares_table(cur: psycopg.Cursor) -> None:
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
        "records": create_records_table,
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


def add_chat(chat_data: ChatData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chats (chat_id, user_id, chat_type, current_step, payload)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                chat_data.chat_id,
                chat_data.user_id,
                chat_data.chat_type,
                chat_data.current_step,
                Json(chat_data.payload),
            ),
        )
    conn.commit()
    logger.info(f"Chat inserted: {chat_data.chat_id}")


def update_chat(chat_data: ChatData, conn: psycopg.Connection) -> None:
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
                chat_data.current_step,
                Json(chat_data.payload),
                chat_data.is_completed,
                chat_data.chat_id,
            ),
        )
    conn.commit()
    logger.info(f"Chat updated: {chat_data.chat_id}")


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
            INSERT INTO events (event_id, event_name, user_id, last_done_at, reminder, cycle_period, cycle_ends_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event_data.event_id,
                event_data.event_name,
                event_data.user_id,
                event_data.last_done_at,
                event_data.reminder,
                event_data.cycle_period,
                event_data.cycle_ends_at,
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


def update_event():
    pass
