-- Enhanced Cognee PostgreSQL Initialization
-- Initializes pgvector extension and creates core schema for Enhanced Cognee.
--
-- Important design decisions baked into this file:
--
--   * Categories are DYNAMIC (configured via .enhanced-cognee-config.json),
--     so memory_category is a plain TEXT column with no CHECK constraint.
--     Earlier versions of this script hardcoded ('ats', 'oma', 'smc') which
--     directly violated the project's dynamic-categories rule and made any
--     custom category (e.g. "trading") fail with a constraint violation.
--
--   * Indexes are declared with separate CREATE INDEX statements (PostgreSQL
--     syntax). Inline INDEX clauses inside CREATE TABLE are MySQL-only and
--     would error out on Postgres.
--
--   * Multi-tenant per-tenant tables are NOT pre-created here -- the
--     application bootstraps them lazily via src.multi_tenant.ensure_tenant_schema
--     using CREATE TABLE LIKE INCLUDING ALL once a tenant context is active.

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- Shared memory schema -- the single source of truth for documents,
-- embeddings, entities, relationships, and metrics. Per-tenant variants are
-- materialised by ensure_tenant_schema at runtime.
-- ---------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS shared_memory;

-- Documents -----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS shared_memory.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500),
    content TEXT,
    file_path VARCHAR(1000),
    file_type VARCHAR(50),
    file_size BIGINT,
    checksum VARCHAR(64),
    mime_type VARCHAR(100),
    encoding VARCHAR(50),
    language VARCHAR(10),
    author VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_status VARCHAR(20) DEFAULT 'pending',
    agent_id VARCHAR(100),
    memory_category VARCHAR(100),
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_documents_agent_id
    ON shared_memory.documents (agent_id);
CREATE INDEX IF NOT EXISTS idx_documents_memory_category
    ON shared_memory.documents (memory_category);
CREATE INDEX IF NOT EXISTS idx_documents_created_at
    ON shared_memory.documents (created_at);
CREATE INDEX IF NOT EXISTS idx_documents_processing_status
    ON shared_memory.documents (processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_tags
    ON shared_memory.documents USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_documents_metadata
    ON shared_memory.documents USING GIN (metadata);
-- Full-text search index. MUST match the query expression in
-- src/enhanced_cognee_mcp.py search_memory() exactly --
-- to_tsvector('english', coalesce(content, '')) -- or the planner won't use
-- it and every search recomputes the tsvector for all rows (seq scan). This
-- is the index that keeps search_memories' p95 under the 200ms SLA at load.
CREATE INDEX IF NOT EXISTS idx_documents_content_fts
    ON shared_memory.documents
    USING GIN (to_tsvector('english', coalesce(content, '')));

-- Embeddings ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS shared_memory.embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES shared_memory.documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(2560) NOT NULL,
    embedding_model VARCHAR(100) DEFAULT 'qwen3-embedding:4b-q4_K_M',
    token_count INTEGER,
    chunk_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    agent_id VARCHAR(100),
    memory_category VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_document_id
    ON shared_memory.embeddings (document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_agent_id
    ON shared_memory.embeddings (agent_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_memory_category
    ON shared_memory.embeddings (memory_category);
CREATE INDEX IF NOT EXISTS idx_embeddings_created_at
    ON shared_memory.embeddings (created_at);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_cosine
    ON shared_memory.embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Entities ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS shared_memory.entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(500) NOT NULL UNIQUE,
    entity_type VARCHAR(100) NOT NULL,
    description TEXT,
    properties JSONB DEFAULT '{}'::jsonb,
    confidence_score FLOAT DEFAULT 1.0,
    source_documents UUID[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    agent_id VARCHAR(100),
    memory_category VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_entities_type
    ON shared_memory.entities (entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_agent_id
    ON shared_memory.entities (agent_id);
CREATE INDEX IF NOT EXISTS idx_entities_memory_category
    ON shared_memory.entities (memory_category);
CREATE INDEX IF NOT EXISTS idx_entities_confidence
    ON shared_memory.entities (confidence_score);
CREATE INDEX IF NOT EXISTS idx_entities_properties
    ON shared_memory.entities USING GIN (properties);

-- Relationships -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS shared_memory.relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES shared_memory.entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES shared_memory.entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}'::jsonb,
    confidence_score FLOAT DEFAULT 1.0,
    source_documents UUID[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    agent_id VARCHAR(100),
    memory_category VARCHAR(100),
    UNIQUE (source_entity_id, target_entity_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_relationships_source
    ON shared_memory.relationships (source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target
    ON shared_memory.relationships (target_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type
    ON shared_memory.relationships (relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_agent_id
    ON shared_memory.relationships (agent_id);
CREATE INDEX IF NOT EXISTS idx_relationships_memory_category
    ON shared_memory.relationships (memory_category);
CREATE INDEX IF NOT EXISTS idx_relationships_confidence
    ON shared_memory.relationships (confidence_score);

-- Performance + memory usage telemetry --------------------------------------

CREATE TABLE IF NOT EXISTS shared_memory.performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit VARCHAR(50),
    tags JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    agent_id VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_performance_metric_name
    ON shared_memory.performance_metrics (metric_name);
CREATE INDEX IF NOT EXISTS idx_performance_timestamp
    ON shared_memory.performance_metrics (timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_agent
    ON shared_memory.performance_metrics (agent_id);
CREATE INDEX IF NOT EXISTS idx_performance_tags
    ON shared_memory.performance_metrics USING GIN (tags);

CREATE TABLE IF NOT EXISTS shared_memory.memory_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,
    memory_category VARCHAR(100) NOT NULL DEFAULT 'general',
    total_documents INTEGER DEFAULT 0,
    total_embeddings INTEGER DEFAULT 0,
    total_entities INTEGER DEFAULT 0,
    total_relationships INTEGER DEFAULT 0,
    storage_used_bytes BIGINT DEFAULT 0,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (agent_id, memory_category)
);

CREATE INDEX IF NOT EXISTS idx_memory_usage_agent
    ON shared_memory.memory_usage (agent_id);
CREATE INDEX IF NOT EXISTS idx_memory_usage_category
    ON shared_memory.memory_usage (memory_category);
CREATE INDEX IF NOT EXISTS idx_memory_usage_activity
    ON shared_memory.memory_usage (last_activity);

-- ---------------------------------------------------------------------------
-- Stored procedures + triggers
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION shared_memory.semantic_search(
    query_vector vector(2560),
    limit_count INTEGER DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.7,
    memory_filter VARCHAR(100) DEFAULT NULL,
    agent_filter VARCHAR(100) DEFAULT NULL
)
RETURNS TABLE (
    document_id UUID,
    content TEXT,
    similarity_score FLOAT,
    agent_id VARCHAR(100),
    memory_category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.document_id,
        e.content,
        1 - (e.embedding <=> query_vector) AS similarity_score,
        e.agent_id,
        e.memory_category,
        e.created_at
    FROM shared_memory.embeddings e
    WHERE
        (e.embedding <=> query_vector) < (1 - similarity_threshold)
        AND (memory_filter IS NULL OR e.memory_category = memory_filter)
        AND (agent_filter IS NULL OR e.agent_id = agent_filter)
    ORDER BY e.embedding <=> query_vector
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION shared_memory.cleanup_expired_memory()
RETURNS INTEGER AS $$
DECLARE
    total_cleaned INTEGER := 0;
    last_count INTEGER;
BEGIN
    -- The per-agent legacy schemas (ats_memory / oma_memory / smc_memory)
    -- were dropped along with the hardcoded categories. If you previously
    -- ran against the old schema, run the manual cleanup once and then
    -- remove this stub. Kept here so the function signature stays stable
    -- for any external callers.
    DELETE FROM shared_memory.documents
    WHERE metadata ? 'expires_at'
      AND (metadata->>'expires_at')::timestamptz < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS last_count = ROW_COUNT;
    total_cleaned := total_cleaned + last_count;
    RETURN total_cleaned;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION shared_memory.update_memory_usage()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO shared_memory.memory_usage (
        agent_id,
        memory_category,
        total_documents,
        last_activity
    )
    VALUES (
        COALESCE(NEW.agent_id, 'unknown'),
        COALESCE(NEW.memory_category, 'general'),
        1,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (agent_id, memory_category)
    DO UPDATE SET
        total_documents = shared_memory.memory_usage.total_documents + 1,
        last_activity = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_memory_stats_after_insert ON shared_memory.documents;
CREATE TRIGGER update_memory_stats_after_insert
    AFTER INSERT ON shared_memory.documents
    FOR EACH ROW
    EXECUTE FUNCTION shared_memory.update_memory_usage();

-- ---------------------------------------------------------------------------
-- Permissions
-- ---------------------------------------------------------------------------

GRANT USAGE ON SCHEMA shared_memory TO cognee_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA shared_memory TO cognee_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA shared_memory TO cognee_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA shared_memory TO cognee_user;
