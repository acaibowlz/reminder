import logging

import psycopg
from psycopg.types.json import Json

from routine_bot.const import DATABASE_URL
from routine_bot.models import ChatData, EventData

logger = logging.getLogger(__name__)

conn = psycopg.connect(conninfo=DATABASE_URL)


def init_db(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                display_name TEXT NOT NULL,
                picture_url TEXT NOT NULL,
                profile_refreshed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                event_count INTEGER NOT NULL DEFAULT 0,
                is_premium BOOLEAN DEFAULT FALSE,
                premium_until TIMESTAMPTZ,
                is_blocked BOOLEAN DEFAULT FALSE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                event_name TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                last_done_at TIMESTAMPTZ NOT NULL,
                has_reminder BOOLEAN NOT NULL,
                cycle_count INTEGER,
                cycle_unit TEXT,
                cycle_ends_at TIMESTAMPTZ,
                share_count INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                record_id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                event_id TEXT NOT NULL REFERENCES events(event_id),
                event_name TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                done_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                chat_id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                user_id TEXT NOT NULL REFERENCES users(user_id),
                chat_type TEXT NOT NULL,
                current_step TEXT NOT NULL,
                next_step TEXT NOT NULL,
                state_data JSON,
                is_completed BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS shares (
                share_id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                event_id TEXT NOT NULL REFERENCES events(event_id),
                event_name TEXT NOT NULL,
                owner_id TEXT NOT NULL REFERENCES users(user_id),
                recipient_id TEXT NOT NULL
            )
            """
        )
    conn.commit()
    logger.info("Database initialized")


### User Table ###
def add_user(user_id: str, display_name: str, picture_url: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (user_id, display_name, picture_url, event_count, is_premium, premium_until)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, display_name, picture_url, 0, False, None),
        )
    conn.commit()
    logger.info(f"User inserted: {user_id}")


### Event Table ###
def add_event(event_data: EventData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO events (event_id, event_name, user_id, last_done_at, has_reminder, cycle_time, cycle_unit, cycle_ends_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event_data.event_id,
                event_data.event_name,
                event_data.user_id,
                event_data.last_done_at,
                event_data.has_reminder,
                event_data.cycle_time,
                event_data.cycle_unit,
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


### Chat Table ###
def add_chat(chat_data: ChatData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chats (chat_id, user_id, chat_type, current_step, next_step, state_data)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                chat_data.chat_id,
                chat_data.user_id,
                chat_data.chat_type,
                chat_data.current_step,
                chat_data.next_step,
                Json(chat_data.state_data),
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
                next_step    = %s,
                state_data   = %s,
                is_completed = %s,
            WHERE chat_id    = %s
            """,
            (
                chat_data.current_step,
                chat_data.next_step,
                Json(chat_data.state_data),
                chat_data.is_completed,
                chat_data.chat_id,
            ),
        )
    conn.commit()
    logger.info(f"Chat updated: {chat_data.chat_id}")


def get_ongoing_chat_id(user_id: str, conn: psycopg.Connection) -> str | None:
    with conn.cursor() as cur:
        cur.execute("SELECT chat_id FROM chats WHERE user_id = %s AND is_completed = %s", (user_id, False))
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]


def get_ongoing_chat_data(user_id: str, conn: psycopg.Connection) -> ChatData | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT chat_id, user_id, chat_type, current_step, next_step, state_data, is_completed FROM chats WHERE user_id = %s AND is_completed = %s",
            (user_id, False),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return ChatData(*result)
