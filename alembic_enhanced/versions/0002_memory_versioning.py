"""Add memory_versions table for Phase 10 (15.1)

Revision ID: 0002_memory_versioning
Revises: 0001_enhanced_cognee_baseline
Create Date: 2026-05-13 00:00:00.000000

Adds shared_memory.memory_versions which records an immutable snapshot of
every content-changing write to documents.  Also adds supporting columns to
documents for Phase 10 features (provenance JSONB, confidence score).
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_memory_versioning"
down_revision: Union[str, None] = "0001_enhanced_cognee_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create memory_versions table and add Phase 10 columns to documents."""
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 15.1 - memory_versions table
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS shared_memory.memory_versions (
            id              BIGSERIAL PRIMARY KEY,
            memory_id       TEXT NOT NULL,
            version_number  INTEGER NOT NULL,
            content         TEXT NOT NULL,
            agent_id        TEXT,
            change_reason   TEXT,
            metadata        JSONB,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_memory_versions_doc
                FOREIGN KEY (memory_id)
                REFERENCES shared_memory.documents(id)
                ON DELETE CASCADE
        )
    """))

    conn.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uix_memory_versions_id_ver
        ON shared_memory.memory_versions (memory_id, version_number)
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_memory_versions_memory_id
        ON shared_memory.memory_versions (memory_id, version_number DESC)
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_memory_versions_agent
        ON shared_memory.memory_versions (agent_id, created_at DESC)
    """))

    # ------------------------------------------------------------------
    # 15.2 - provenance column on documents
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        ALTER TABLE shared_memory.documents
        ADD COLUMN IF NOT EXISTS provenance JSONB
    """))

    # ------------------------------------------------------------------
    # 15.3 - confidence score column on documents
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        ALTER TABLE shared_memory.documents
        ADD COLUMN IF NOT EXISTS confidence NUMERIC(5, 4)
            DEFAULT 1.0
            CHECK (confidence >= 0 AND confidence <= 1)
    """))

    # ------------------------------------------------------------------
    # 15.4 - consolidation tracking columns on documents
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        ALTER TABLE shared_memory.documents
        ADD COLUMN IF NOT EXISTS consolidated_into TEXT
    """))

    conn.execute(sa.text("""
        ALTER TABLE shared_memory.documents
        ADD COLUMN IF NOT EXISTS consolidation_score NUMERIC(5, 4)
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_documents_confidence
        ON shared_memory.documents (confidence)
        WHERE confidence IS NOT NULL
    """))


def downgrade() -> None:
    """Remove Phase 10 additions (DESTRUCTIVE)."""
    conn = op.get_bind()
    conn.execute(sa.text(
        "ALTER TABLE shared_memory.documents DROP COLUMN IF EXISTS consolidation_score"
    ))
    conn.execute(sa.text(
        "ALTER TABLE shared_memory.documents DROP COLUMN IF EXISTS consolidated_into"
    ))
    conn.execute(sa.text(
        "ALTER TABLE shared_memory.documents DROP COLUMN IF EXISTS confidence"
    ))
    conn.execute(sa.text(
        "ALTER TABLE shared_memory.documents DROP COLUMN IF EXISTS provenance"
    ))
    conn.execute(sa.text(
        "DROP TABLE IF EXISTS shared_memory.memory_versions CASCADE"
    ))
