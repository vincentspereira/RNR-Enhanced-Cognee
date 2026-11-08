"""Complete the legacy document column contract without rewriting IDs/vectors.

Revision ID: 0003_legacy_document_columns
Revises: 0002_memory_versioning

The restricted service's encrypted records are a separate, versioned schema.
This revision only makes old document helpers compatible with both installers.
It does not migrate private records or silently replace embedding dimensions.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_legacy_document_columns"
down_revision = "0002_memory_versioning"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Include already bootstrapped tenant tables. An explicit schema catalog
    # lookup supplies identifiers, which are still quoted through the dialect.
    tables = conn.execute(sa.text("""SELECT table_name FROM information_schema.tables
        WHERE table_schema='shared_memory' AND table_type='BASE TABLE'
        AND (table_name='documents' OR table_name LIKE 'documents\\_t\\_%' ESCAPE '\\')""")).scalars().all()
    quote = conn.dialect.identifier_preparer.quote
    for name in tables:
        table = "shared_memory." + quote(name)
        conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS memory_category TEXT DEFAULT 'general'"))
        conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{{}}'"))
        conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS expire_at TIMESTAMPTZ"))
        conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{{}}'::jsonb"))
        conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()"))


def downgrade():
    # Dropping these columns could erase user metadata/retention information.
    # Keep the additive compatibility columns if an application is rolled back.
    pass
