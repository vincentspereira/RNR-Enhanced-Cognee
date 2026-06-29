"""RNR Enhanced Cognee shared_memory schema baseline

Revision ID: 0001_enhanced_cognee_baseline
Revises: (none - initial migration)
Create Date: 2026-05-13 00:00:00.000000

Creates the shared_memory PostgreSQL schema used by all RNR Enhanced Cognee
database operations.  This migration is idempotent (uses IF NOT EXISTS).
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_enhanced_cognee_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create shared_memory schema and all RNR Enhanced Cognee tables."""
    conn = op.get_bind()

    # Create schema
    conn.execute(sa.text("CREATE SCHEMA IF NOT EXISTS shared_memory"))

    # Enable pgvector extension
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Core documents table
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS shared_memory.documents (
            id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title       TEXT NOT NULL DEFAULT '',
            content     TEXT NOT NULL,
            agent_id    TEXT NOT NULL DEFAULT 'default',
            metadata    JSONB,
            embedding   vector(1536),
            expire_at   TIMESTAMPTZ,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_documents_agent_id
        ON shared_memory.documents (agent_id)
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_documents_created_at
        ON shared_memory.documents (created_at DESC)
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_documents_expire_at
        ON shared_memory.documents (expire_at)
        WHERE expire_at IS NOT NULL
    """))

    # Sessions table (Phase 7 SessionManager)
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS shared_memory.sessions (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL DEFAULT 'default',
            agent_id    TEXT NOT NULL DEFAULT 'claude-code',
            start_time  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            end_time    TIMESTAMPTZ,
            summary     TEXT,
            metadata    JSONB,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_agent
        ON shared_memory.sessions (user_id, agent_id, start_time DESC)
    """))

    # LLM usage tracking (Plan 14.8)
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS shared_memory.llm_usage (
            id               BIGSERIAL PRIMARY KEY,
            agent_id         TEXT,
            tool_name        TEXT,
            model            TEXT,
            input_tokens     INTEGER,
            output_tokens    INTEGER,
            estimated_cost_usd  NUMERIC(12, 8),
            recorded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_llm_usage_agent_recorded
        ON shared_memory.llm_usage (agent_id, recorded_at DESC)
    """))

    # LLM budget limits (Plan 14.8)
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS shared_memory.llm_budgets (
            agent_id    TEXT PRIMARY KEY,
            monthly_usd NUMERIC(10, 2) NOT NULL,
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    # Audit log table (Phase 9)
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS shared_memory.audit_log (
            id               BIGSERIAL PRIMARY KEY,
            operation_type   TEXT NOT NULL,
            agent_id         TEXT,
            status           TEXT NOT NULL,
            details          JSONB,
            execution_time_ms  FLOAT,
            error_message    TEXT,
            timestamp        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_agent_timestamp
        ON shared_memory.audit_log (agent_id, timestamp DESC)
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_operation_status
        ON shared_memory.audit_log (operation_type, status)
    """))


def downgrade() -> None:
    """Drop all RNR Enhanced Cognee tables (DESTRUCTIVE - use with caution)."""
    conn = op.get_bind()
    conn.execute(sa.text("DROP TABLE IF EXISTS shared_memory.audit_log CASCADE"))
    conn.execute(sa.text("DROP TABLE IF EXISTS shared_memory.llm_budgets CASCADE"))
    conn.execute(sa.text("DROP TABLE IF EXISTS shared_memory.llm_usage CASCADE"))
    conn.execute(sa.text("DROP TABLE IF EXISTS shared_memory.sessions CASCADE"))
    conn.execute(sa.text("DROP TABLE IF EXISTS shared_memory.documents CASCADE"))
    conn.execute(sa.text("DROP SCHEMA IF EXISTS shared_memory CASCADE"))
