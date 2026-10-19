"""Actual legacy installer/upgrade qualification on disposable pgvector only.

Each fixture creates and preserves a separate database. No existing schema is
replaced or dropped. Set RNR_QUALIFICATION_SCHEMA_URL explicitly to the isolated
test server's administrative database; normal POSTGRES_* settings are ignored.
"""
import importlib.util
import os
from pathlib import Path
import uuid

import pytest


def load_revision(name):
    path = Path("alembic_enhanced/versions") / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("installation", ["fresh_alembic", "docker_uuid", "existing_text_tenant"])
def test_legacy_upgrade_preserves_records_and_enables_helper_columns(installation):
    url = os.getenv("RNR_QUALIFICATION_SCHEMA_URL")
    if not url:
        pytest.skip("Requires a disposable pgvector PostgreSQL administrative connection")
    import psycopg2
    from psycopg2 import sql
    import sqlalchemy as sa
    from sqlalchemy.engine import make_url
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    database = "schema_q_" + uuid.uuid4().hex[:20]
    admin = psycopg2.connect(url)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    finally:
        admin.close()
    parsed = make_url(url).set(drivername="postgresql+psycopg2", database=database)
    engine = sa.create_engine(parsed)
    ident = str(uuid.uuid4())
    try:
        with engine.begin() as conn:
            if installation == "docker_uuid":
                conn.exec_driver_sql("""DO $$ BEGIN IF NOT EXISTS (
                    SELECT 1 FROM pg_roles WHERE rolname='cognee_user') THEN
                    CREATE ROLE cognee_user NOLOGIN; END IF; END $$""")
                conn.exec_driver_sql(Path("docker/init-scripts/01-init-pgvector.sql").read_text())
                conn.execute(sa.text("""INSERT INTO shared_memory.documents(id,content,agent_id)
                    VALUES(:id,'Synthetic schema fixture','migration')"""), {"id": ident})
            if installation == "existing_text_tenant":
                conn.exec_driver_sql("CREATE SCHEMA shared_memory")
                conn.exec_driver_sql("""CREATE TABLE shared_memory.documents (
                    id TEXT PRIMARY KEY, title TEXT, content TEXT,
                    agent_id TEXT, created_at TIMESTAMPTZ DEFAULT now())""")
                conn.execute(sa.text("INSERT INTO shared_memory.documents(id,content) VALUES(:id,'Synthetic schema fixture')"), {"id": ident})
                conn.exec_driver_sql("CREATE TABLE shared_memory.documents_t_existing (LIKE shared_memory.documents INCLUDING ALL)")
            with Operations.context(MigrationContext.configure(conn)):
                for revision in ("0001_enhanced_cognee_baseline", "0002_memory_versioning", "0003_legacy_document_columns"):
                    load_revision(revision).upgrade()
                # Compatibility DDL is safe to retry; existing source is retained.
                load_revision("0003_legacy_document_columns").upgrade()
            new_id = str(uuid.uuid4())
            conn.execute(sa.text("""INSERT INTO shared_memory.documents
                (id,title,content,agent_id,memory_category,tags,metadata)
                VALUES(:id,'Fixture','New synthetic fixture','qualification','custom_fixture',ARRAY[]::text[],'{}'::jsonb)"""), {"id": new_id})
            conn.execute(sa.text("""INSERT INTO shared_memory.memory_versions
                (memory_id,version_number,content) VALUES(:id,1,'New synthetic fixture')"""), {"id": new_id})
            if installation != "fresh_alembic":
                assert conn.execute(sa.text("SELECT content FROM shared_memory.documents WHERE id::text=:id"), {"id": ident}).scalar_one() == "Synthetic schema fixture"
            source_type = conn.execute(sa.text("""SELECT data_type FROM information_schema.columns
                WHERE table_schema='shared_memory' AND table_name='documents' AND column_name='id'""")).scalar_one()
            assert source_type == ("uuid" if installation == "docker_uuid" else "text")
            if installation == "existing_text_tenant":
                fields = set(conn.execute(sa.text("""SELECT column_name FROM information_schema.columns
                    WHERE table_schema='shared_memory' AND table_name='documents_t_existing'""")).scalars())
                assert {"memory_category", "tags", "expire_at", "metadata", "updated_at"} <= fields
            if installation == "docker_uuid":
                vector_type = conn.execute(sa.text("""SELECT format_type(a.atttypid,a.atttypmod)
                    FROM pg_attribute a WHERE a.attrelid='shared_memory.embeddings'::regclass
                    AND a.attname='embedding'""")).scalar_one()
                assert vector_type == "vector(2560)"
    finally:
        engine.dispose()
