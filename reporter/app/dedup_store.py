import asyncio
import json
import os
import sqlite3
import time
from pathlib import Path


class DedupStore:
    """Tracks, per (ip, category), when it was last reported to Avatoris and
    how many attempts have been suppressed since - so we stay within the
    API's one-report-per-target-per-30-minutes rule without dropping data."""

    def __init__(self, db_path: str):
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                ip TEXT NOT NULL,
                category TEXT NOT NULL,
                last_reported_at REAL,
                pending_count INTEGER NOT NULL DEFAULT 0,
                usernames TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY (ip, category)
            )
            """
        )
        self._conn.commit()
        self._lock = asyncio.Lock()

    async def register_attempt(self, ip: str, category: str, username, window_seconds: int):
        """Returns (should_report_now, usernames_for_comment)."""
        async with self._lock:
            return await asyncio.to_thread(
                self._register_attempt_sync, ip, category, username, window_seconds
            )

    def _register_attempt_sync(self, ip, category, username, window_seconds):
        now = time.time()
        row = self._conn.execute(
            "SELECT last_reported_at, usernames FROM reports WHERE ip=? AND category=?",
            (ip, category),
        ).fetchone()

        if row is None or row[0] is None or (now - row[0]) > window_seconds:
            self._conn.execute(
                """
                INSERT INTO reports (ip, category, last_reported_at, pending_count, usernames)
                VALUES (?, ?, ?, 0, '[]')
                ON CONFLICT(ip, category) DO UPDATE SET
                    last_reported_at = excluded.last_reported_at,
                    pending_count = 0,
                    usernames = '[]'
                """,
                (ip, category, now),
            )
            self._conn.commit()
            return True, ([username] if username else [])

        usernames = json.loads(row[1])
        if username and username not in usernames:
            usernames.append(username)
        self._conn.execute(
            "UPDATE reports SET pending_count = pending_count + 1, usernames=? WHERE ip=? AND category=?",
            (json.dumps(usernames[:20]), ip, category),
        )
        self._conn.commit()
        return False, usernames

    async def flush_candidates(self, window_seconds: int):
        async with self._lock:
            return await asyncio.to_thread(self._flush_candidates_sync, window_seconds)

    def _flush_candidates_sync(self, window_seconds):
        now = time.time()
        return self._conn.execute(
            """
            SELECT ip, category, pending_count, usernames FROM reports
            WHERE pending_count > 0 AND (? - last_reported_at) > ?
            """,
            (now, window_seconds),
        ).fetchall()

    async def mark_flushed(self, ip: str, category: str):
        async with self._lock:
            await asyncio.to_thread(self._mark_flushed_sync, ip, category)

    def _mark_flushed_sync(self, ip, category):
        self._conn.execute(
            "UPDATE reports SET last_reported_at=?, pending_count=0, usernames='[]' WHERE ip=? AND category=?",
            (time.time(), ip, category),
        )
        self._conn.commit()
