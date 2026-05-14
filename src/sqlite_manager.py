"""
SQLite Manager
==============
Lightweight SQLite wrapper used by the backup and recovery subsystem to store
local backup metadata.  This is intentionally minimal — it handles only what
the backup stack needs (add, get, search, delete) using plain sqlite3.

Not related to any "lite" mode; the Enhanced stack still runs on PostgreSQL /
Qdrant / Neo4j for primary storage.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class SQLiteManager:
    """Thin SQLite wrapper for local backup-metadata persistence."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id          TEXT PRIMARY KEY,
                    data_id     TEXT,
                    data_text   TEXT,
                    data_type   TEXT,
                    metadata    TEXT,
                    user_id     TEXT,
                    agent_id    TEXT,
                    created_at  TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_data_id ON documents(data_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_id ON documents(user_id)"
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_document(
        self,
        data_id: Optional[str] = None,
        data_text: Optional[str] = None,
        data_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> str:
        """Insert or replace a document. Returns the internal row id."""
        row_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata) if metadata else "{}"

        with sqlite3.connect(self.db_path) as conn:
            # Upsert by data_id so re-inserting the same backup replaces it
            existing = conn.execute(
                "SELECT id FROM documents WHERE data_id = ?", (data_id,)
            ).fetchone()
            if existing:
                row_id = existing[0]
                conn.execute(
                    """UPDATE documents
                       SET data_text=?, data_type=?, metadata=?, user_id=?, agent_id=?
                       WHERE id=?""",
                    (data_text, data_type, meta_json, user_id, agent_id, row_id),
                )
            else:
                conn.execute(
                    """INSERT INTO documents
                       (id, data_id, data_text, data_type, metadata, user_id, agent_id, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (row_id, data_id, data_text, data_type, meta_json,
                     user_id, agent_id, now),
                )
            conn.commit()
        return row_id

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its data_id or internal id."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM documents WHERE data_id=? OR id=? LIMIT 1",
                (doc_id, doc_id),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def search_documents(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search documents by data_id match or full-text substring."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            like = f"%{query}%"
            if user_id:
                rows = conn.execute(
                    """SELECT * FROM documents
                       WHERE user_id=? AND (data_id=? OR data_text LIKE ?)
                       ORDER BY created_at DESC LIMIT ?""",
                    (user_id, query, like, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM documents
                       WHERE data_id=? OR data_text LIKE ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (query, like, limit),
                ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete_document(self, doc_id: str) -> bool:
        """Delete by data_id or internal id. Returns True if a row was deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM documents WHERE data_id=? OR id=?",
                (doc_id, doc_id),
            )
            conn.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["metadata"] = json.loads(d.get("metadata") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["metadata"] = {}
        return d
