import logging

import psycopg
import requests

logger = logging.getLogger(__name__)


def init_db(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                display_name TEXT NOT NULL,
                picture_url TEXT NOT NULL,
                event_count INTEGER NOT NULL DEFAULT 0,
                is_premium BOOLEAN DEFAULT FALSE,
                premium_until TIMESTAMPTZ
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                name TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                last_done_at TIMESTAMPTZ NOT NULL,
                has_reminder BOOLEAN NOT NULL,
                cycle_time INTEGER,
                cycle_unit TEXT,
                cycle_ends_at TIMESTAMPTZ,
                share_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                record_id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
                event_name TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                done_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                chat_id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                chat_type TEXT NOT NULL,
                current_state INTEGER NOT NULL,
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
                event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
                event_name TEXT NOT NULL,
                owner_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                recipient_id TEXT NOT NULL
            )
            """
        )


def add_user(user_id: str, display_name: str, picture_url: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (user_id, display_name, picture_url, event_count, is_premium, premium_until)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, display_name, picture_url, 0, False, None),
        )
    logger.info(f"User inserted: {user_id}")


def delete_user(user_id: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE user_id = %s;", (user_id,))
        if cur.rowcount > 0:
            logger.info(f"User deleted: {user_id}")
        else:
            logger.info(f"No user found on deletion: {user_id}")
