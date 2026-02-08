"""
Enhanced Cognee Lite Mode - SQLite Database Manager

Lightweight SQLite-based database manager for Enhanced Cognee Lite mode.
No Docker required, FTS5 full-text search, fast setup.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import sqlite3
import threading
import json
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
import uuid

logger = logging.getLogger(__name__)


class SQLiteManager:
    """
    SQLite database manager for Enhanced Cognee Lite mode.

    Features:
    - Thread-safe connection pooling
    - FTS5 full-text search
    - Automatic schema creation
    - Transaction management
    - Connection context managers
    """

    def __init__(self, db_path: str = "cognee_lite.db"):
        """
        Initialize SQLite manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.local = threading.local()
        self._ensure_database_exists()
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get thread-local database connection.

        Returns:
            SQLite connection for current thread
        """
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection

    @contextmanager
    def get_cursor(self):
        """
        Context manager for database cursor.

        Yields:
            SQLite cursor
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise

    def _ensure_database_exists(self):
        """Ensure database directory and file exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _initialize_schema(self):
        """Initialize database schema from SQL file."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'migrations',
            'create_lite_schema.sql'
        )

        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()

            with self.get_cursor() as cursor:
                # Split and execute each statement
                for statement in schema_sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        try:
                            cursor.execute(statement)
                        except sqlite3.OperationalError as e:
                            # Ignore "already exists" errors
                            if "already exists" not in str(e):
                                logger.warning(f"Schema initialization warning: {e}")

            logger.info("SQLite database schema initialized")
        else:
            logger.warning(f"Schema file not found: {schema_path}")

    def add_document(
        self,
        data_id: str,
        data_text: str,
        data_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
        agent_id: str = "claude-code"
    ) -> str:
        """
        Add a document to the database.

        Args:
            data_id: Unique data identifier
            data_text: Document text content
            data_type: Document type (text, json, etc.)
            metadata: Optional metadata dictionary
            user_id: User identifier
            agent_id: Agent identifier

        Returns:
            Document ID (UUID)
        """
        doc_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None

        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO documents (
                    id, data_id, data_type, data_text, data_metadata,
                    user_id, agent_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (
                doc_id, data_id, data_type, data_text, metadata_json,
                user_id, agent_id
            ))

        logger.info(f"Document added: {doc_id}")
        return doc_id

    def search_documents(
        self,
        query: str,
        user_id: str = "default",
        agent_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Full-text search using FTS5.

        Args:
            query: Search query
            user_id: User identifier filter
            agent_id: Optional agent identifier filter
            limit: Maximum results

        Returns:
            List of matching documents
        """
        with self.get_cursor() as cursor:
            if agent_id:
                cursor.execute("""
                    SELECT
                        d.id, d.data_id, d.data_type, d.data_text,
                        d.data_metadata, d.user_id, d.agent_id,
                        d.created_at, d.updated_at,
                        bm25(documents_fts) as rank
                    FROM documents d
                    JOIN documents_fts fts ON d.rowid = fts.rowid
                    WHERE d.data_text MATCH ?
                        AND d.user_id = ?
                        AND d.agent_id = ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, user_id, agent_id, limit))
            else:
                cursor.execute("""
                    SELECT
                        d.id, d.data_id, d.data_type, d.data_text,
                        d.data_metadata, d.user_id, d.agent_id,
                        d.created_at, d.updated_at,
                        bm25(documents_fts) as rank
                    FROM documents d
                    JOIN documents_fts fts ON d.rowid = fts.rowid
                    WHERE d.data_text MATCH ?
                        AND d.user_id = ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, user_id, limit))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'data_id': row['data_id'],
                    'data_type': row['data_type'],
                    'data_text': row['data_text'],
                    'metadata': json.loads(row['data_metadata']) if row['data_metadata'] else None,
                    'user_id': row['user_id'],
                    'agent_id': row['agent_id'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'rank': row['rank']
                })

        return results

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document dictionary or None
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, data_id, data_type, data_text, data_metadata,
                       user_id, agent_id, created_at, updated_at
                FROM documents
                WHERE id = ?
            """, (doc_id,))

            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'data_id': row['data_id'],
                    'data_type': row['data_type'],
                    'data_text': row['data_text'],
                    'metadata': json.loads(row['data_metadata']) if row['data_metadata'] else None,
                    'user_id': row['user_id'],
                    'agent_id': row['agent_id'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }

        return None

    def list_documents(
        self,
        user_id: str = "default",
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List documents with pagination.

        Args:
            user_id: User identifier
            agent_id: Optional agent filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of documents
        """
        with self.get_cursor() as cursor:
            if agent_id:
                cursor.execute("""
                    SELECT id, data_id, data_type, SUBSTR(data_text, 1, 200) as summary,
                           user_id, agent_id, created_at, updated_at
                    FROM documents
                    WHERE user_id = ? AND agent_id = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (user_id, agent_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT id, data_id, data_type, SUBSTR(data_text, 1, 200) as summary,
                           user_id, agent_id, created_at, updated_at
                    FROM documents
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'data_id': row['data_id'],
                    'data_type': row['data_type'],
                    'summary': row['summary'],
                    'user_id': row['user_id'],
                    'agent_id': row['agent_id'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })

        return results

    def update_document(
        self,
        doc_id: str,
        data_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update document.

        Args:
            doc_id: Document ID
            data_text: Optional new text content
            metadata: Optional new metadata

        Returns:
            True if updated, False otherwise
        """
        updates = []
        values = []

        if data_text is not None:
            updates.append("data_text = ?")
            values.append(data_text)

        if metadata is not None:
            updates.append("data_metadata = ?")
            values.append(json.dumps(metadata))

        if not updates:
            return False

        updates.append("updated_at = datetime('now')")
        values.append(doc_id)

        with self.get_cursor() as cursor:
            cursor.execute(f"""
                UPDATE documents
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)

        logger.info(f"Document updated: {doc_id}")
        return cursor.rowcount > 0

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete document.

        Args:
            doc_id: Document ID

        Returns:
            True if deleted, False otherwise
        """
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Document deleted: {doc_id}")

        return deleted

    def create_session(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new session.

        Args:
            user_id: User identifier
            agent_id: Agent identifier
            metadata: Optional metadata

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None

        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO sessions (id, user_id, agent_id, metadata)
                VALUES (?, ?, ?, ?)
            """, (session_id, user_id, agent_id, metadata_json))

        logger.info(f"Session created: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session dictionary or None
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, user_id, agent_id, start_time, end_time,
                       summary, memory_count, metadata
                FROM sessions
                WHERE id = ?
            """, (session_id,))

            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'agent_id': row['agent_id'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'summary': row['summary'],
                    'memory_count': row['memory_count'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else None
                }

        return None

    def list_sessions(
        self,
        user_id: str = "default",
        agent_id: Optional[str] = None,
        active_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        List sessions.

        Args:
            user_id: User identifier
            agent_id: Optional agent filter
            active_only: Only show active sessions
            limit: Maximum results

        Returns:
            List of sessions
        """
        with self.get_cursor() as cursor:
            query = """
                SELECT id, user_id, agent_id, start_time, memory_count
                FROM sessions
                WHERE user_id = ?
            """
            params = [user_id]

            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)

            if active_only:
                query += " AND end_time IS NULL"

            query += " ORDER BY start_time DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'agent_id': row['agent_id'],
                    'start_time': row['start_time'],
                    'memory_count': row['memory_count']
                })

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Statistics dictionary
        """
        with self.get_cursor() as cursor:
            # Total documents
            cursor.execute("SELECT COUNT(*) as count FROM documents")
            total_docs = cursor.fetchone()['count']

            # Total sessions
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            total_sessions = cursor.fetchone()['count']

            # Active sessions
            cursor.execute("SELECT COUNT(*) as count FROM sessions WHERE end_time IS NULL")
            active_sessions = cursor.fetchone()['count']

            # Documents by agent
            cursor.execute("""
                SELECT agent_id, COUNT(*) as count
                FROM documents
                GROUP BY agent_id
            """)
            agents = {row['agent_id']: row['count'] for row in cursor.fetchall()}

            # Database size
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        return {
            'total_documents': total_docs,
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'agents': agents,
            'database_size_bytes': db_size,
            'database_path': self.db_path,
            'mode': 'lite'
        }

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all agents with memory counts.

        Returns:
            List of agents
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT
                    agent_id,
                    COUNT(*) as memory_count,
                    MIN(created_at) as first_memory,
                    MAX(created_at) as last_memory
                FROM documents
                GROUP BY agent_id
                ORDER BY memory_count DESC
            """)

            results = []
            for row in cursor.fetchall():
                results.append({
                    'agent_id': row['agent_id'],
                    'memory_count': row['memory_count'],
                    'first_memory': row['first_memory'],
                    'last_memory': row['last_memory']
                })

        return results

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health status dictionary
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            return {
                'status': 'OK',
                'database': 'SQLite',
                'path': self.db_path,
                'mode': 'lite'
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'ERR',
                'database': 'SQLite',
                'error': str(e),
                'mode': 'lite'
            }

    def close(self):
        """Close database connection."""
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            delattr(self.local, 'connection')

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
