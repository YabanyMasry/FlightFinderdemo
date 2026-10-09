"""Tiny SQLite response cache.

Keyed by (method+url+sorted params). Stores the raw JSON body plus a timestamp.
Repeated scans within the TTL reuse the stored body instead of hitting the API.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from typing import Optional


class Cache:
    def __init__(self, path: str, ttl_hours: float):
        self.ttl_seconds = ttl_hours * 3600
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS responses ("
            "  key TEXT PRIMARY KEY,"
            "  body TEXT NOT NULL,"
            "  created_at REAL NOT NULL"
            ")"
        )
        self.conn.commit()

    @staticmethod
    def make_key(method: str, url: str, params: dict) -> str:
        blob = json.dumps(
            {"m": method.upper(), "u": url, "p": params or {}}, sort_keys=True
        )
        return hashlib.sha256(blob.encode()).hexdigest()

    def get(self, key: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT body, created_at FROM responses WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            return None
        body, created_at = row
        if time.time() - created_at > self.ttl_seconds:
            return None
        return json.loads(body)

    def set(self, key: str, body: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO responses (key, body, created_at) VALUES (?, ?, ?)",
            (key, json.dumps(body), time.time()),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
