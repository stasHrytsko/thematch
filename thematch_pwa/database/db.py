# database/db.py
# Postgres database layer for Vercel serverless deployment.
# Replaces the original SQLite implementation while keeping the same schema
# and public interface so API handlers need no changes.
import os
import logging
from datetime import datetime
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection() -> psycopg2.extensions.connection:
    """Open a new Postgres connection.

    Each serverless invocation should open its own connection and close it
    before returning (Vercel functions are stateless). psycopg2 is used
    directly here instead of a pool because the connection lifetime is
    bounded by the request.
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db() -> None:
    """Create tables if they do not already exist.

    Run this once during initial deployment or via a setup script.
    It is safe to call multiple times (uses CREATE TABLE IF NOT EXISTS).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id   BIGINT PRIMARY KEY,
                    username  TEXT,
                    free_checks  INTEGER DEFAULT 10,
                    paid_checks  INTEGER DEFAULT 0,
                    birth_date   DATE
                );

                CREATE TABLE IF NOT EXISTS checks_history (
                    id                  SERIAL PRIMARY KEY,
                    user_id             BIGINT,
                    date1               TEXT NOT NULL,
                    date2               TEXT NOT NULL,
                    compatibility_score REAL,
                    check_date          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id         SERIAL PRIMARY KEY,
                    user_id    BIGINT,
                    text       TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)
        conn.commit()
        logger.info("Database tables initialised")
    finally:
        conn.close()


class Database:
    """Postgres database wrapper.

    Designed for serverless usage: create one instance per request,
    call close() when done (or use as a context manager).
    """

    def __init__(self) -> None:
        self.conn = get_connection()

    # ------------------------------------------------------------------ #
    # Context manager support                                              #
    # ------------------------------------------------------------------ #

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self) -> None:
        """Close the underlying database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()

    # ------------------------------------------------------------------ #
    # Users                                                                #
    # ------------------------------------------------------------------ #

    def get_user(self, user_id: int) -> Optional[dict]:
        """Return the user row as a dict, or None if not found."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_user(self, user_id: int, username: str) -> bool:
        """Insert a new user row. Does nothing if the user already exists."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (user_id, username) VALUES (%s, %s)"
                    " ON CONFLICT (user_id) DO NOTHING",
                    (user_id, username),
                )
            self.conn.commit()
            return True
        except Exception as exc:
            logger.error("Error creating user %s: %s", user_id, exc)
            self.conn.rollback()
            return False

    def update_user_birth_date(self, user_id: int, birth_date: datetime) -> bool:
        """Persist the user's birth date (stored as YYYY-MM-DD string)."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET birth_date = %s WHERE user_id = %s",
                    (birth_date.strftime("%Y-%m-%d"), user_id),
                )
            self.conn.commit()
            return True
        except Exception as exc:
            logger.error("Error updating birth date for user %s: %s", user_id, exc)
            self.conn.rollback()
            return False

    def get_user_birth_date(self, user_id: int) -> Optional[datetime]:
        """Return the stored birth date as a datetime, or None."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT birth_date FROM users WHERE user_id = %s", (user_id,)
                )
                row = cur.fetchone()
                if row and row["birth_date"]:
                    return datetime.strptime(str(row["birth_date"]), "%Y-%m-%d")
            return None
        except Exception as exc:
            logger.error("Error fetching birth date for user %s: %s", user_id, exc)
            return None

    def update_checks_count(self, user_id: int, is_free: bool = True) -> bool:
        """Decrement the free or paid checks counter by 1 (floor 0)."""
        field = "free_checks" if is_free else "paid_checks"
        try:
            with self.conn.cursor() as cur:
                # field name comes from our own code, not user input — safe to interpolate.
                cur.execute(
                    f"UPDATE users SET {field} = {field} - 1"
                    f" WHERE user_id = %s AND {field} > 0",
                    (user_id,),
                )
            self.conn.commit()
            return True
        except Exception as exc:
            logger.error("Error updating checks count for user %s: %s", user_id, exc)
            self.conn.rollback()
            return False

    # ------------------------------------------------------------------ #
    # Check history                                                        #
    # ------------------------------------------------------------------ #

    def add_check_history(
        self,
        user_id: int,
        date1: str,
        date2: str,
        compatibility_score: float,
    ) -> bool:
        """Append a compatibility check result to the history table."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO checks_history (user_id, date1, date2, compatibility_score)"
                    " VALUES (%s, %s, %s, %s)",
                    (user_id, date1, date2, compatibility_score),
                )
            self.conn.commit()
            return True
        except Exception as exc:
            logger.error("Error saving check history: %s", exc)
            self.conn.rollback()
            return False

    def get_history(self, user_id: int, limit: int = 10) -> list:
        """Return the most recent *limit* checks for a user (newest first)."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM checks_history"
                " WHERE user_id = %s ORDER BY check_date DESC LIMIT %s",
                (user_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------ #
    # Feedback                                                             #
    # ------------------------------------------------------------------ #

    def save_feedback(self, user_id: Optional[int], text: str) -> bool:
        """Persist a feedback message. user_id may be None for anonymous submissions."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO feedback (user_id, text) VALUES (%s, %s)",
                    (user_id, text),
                )
            self.conn.commit()
            return True
        except Exception as exc:
            logger.error("Error saving feedback: %s", exc)
            self.conn.rollback()
            return False
