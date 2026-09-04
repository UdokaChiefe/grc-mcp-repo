"""
SQLite-backed StateStore.

save(record) returns an opaque id; get(id) returns the record back.
The id is the only handle callers get to a stored record — full evidence
payloads are never round-tripped through the conversation, only the id is.
"""

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).parent / "evidence_store.db"


class StateStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def save(self, record: dict[str, Any]) -> str:
        record_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO records (id, data) VALUES (?, ?)",
                (record_id, json.dumps(record)),
            )
            conn.commit()
        finally:
            conn.close()
        return record_id

    def get(self, record_id: str) -> Optional[dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT data, created_at FROM records WHERE id = ?", (record_id,)
            )
            row = cursor.fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        data = json.loads(row[0])
        data["_stored_at"] = row[1]
        return data
