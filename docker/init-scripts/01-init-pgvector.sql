-- Enhanced Cognee PostgreSQL Initialization
-- Initializes pgVector extension and creates core schema for Enhanced Cognee

-- Enable pgVector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enhanced Cognee specific schemas
CREATE SCHEMA IF NOT EXISTS ats_memory;
CREATE SCHEMA IF NOT EXISTS oma_memory;
CREATE SCHEMA IF NOT EXISTS smc_memory;
CREATE SCHEMA IF NOT EXISTS shared_memory;

-- Document metadata table (enhanced from default SQLite)
CREATE TABLE IF NOT EXISTS shared_memory.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
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
    agent_id VARCHAR(50),
    memory_category VARCHAR(10) CHECK (memory_category IN ('ats', 'oma', 'smc')),
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Enhanced indexing for performance
    INDEX idx_documents_agent_id (agent_id),
    INDEX idx_documents_memory_category (memory_category),
    INDEX idx_documents_created_at (created_at),
    INDEX idx_documents_processing_status (processing_status),
    INDEX idx_documents_tags USING GIN (tags),
    INDEX idx_documents_metadata USING GIN (metadata)
);

-- Enhanced embeddings table (replaces LanceDB with pgVector)
CREATE TABLE IF NOT EXISTS shared_memory.embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES shared_memory.documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(2560) NOT NULL,  -- Using qwen3-embedding:4b-q4_K_M dimensions
    embedding_model VARCHAR(100) DEFAULT 'qwen3-embedding:4b-q4_K_M',
    token_count INTEGER,
    chunk_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    agent_id VARCHAR(50),
    memory_category VARCHAR(10) CHECK (memory_category IN ('ats', 'oma', 'smc')),

    -- Enhanced vector indexing for performance
    INDEX idx_embeddings_document_id (document_id),
    INDEX idx_embeddings_agent_id (agent_id),
    INDEX idx_embeddings_memory_category (memory_category),
    INDEX idx_embeddings_created_at (created_at),

    -- Vector similarity index
    CREATE INDEX idx_embeddings_vector_cosine
        ON shared_memory.embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
);

-- Knowledge graph entities table (enhanced from default)
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
    agent_id VARCHAR(50),
    memory_category VARCHAR(10) CHECK (memory_category IN ('ats', 'oma', 'smc')),

    INDEX idx_entities_type (entity_type),
    INDEX idx_entities_agent_id (agent_id),
    INDEX idx_entities_memory_category (memory_category),
    INDEX idx_entities_confidence (confidence_score),
    INDEX idx_entities_properties USING GIN (properties)
);

-- Knowledge graph relationships table (enhanced from default)
CREATE TABLE IF NOT EXISTS shared_memory.relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES shared_memory.entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES shared_memory.entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}'::jsonb,
    confidence_score FLOAT DEFAULT 1.0,
    source_documents UUID[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    agent_id VARCHAR(50),
    memory_category VARCHAR(10) CHECK (memory_category IN ('ats', 'oma', 'smc')),

    -- Unique constraint to prevent duplicate relationships
    UNIQUE(source_entity_id, target_entity_id, relationship_type),

    INDEX idx_relationships_source (source_entity_id),
    INDEX idx_relationships_target (target_entity_id),
    INDEX idx_relationships_type (relationship_type),
    INDEX idx_relationships_agent_id (agent_id),
    INDEX idx_relationships_memory_category (memory_category),
    INDEX idx_relationships_confidence (confidence_score)
);

-- Agent-specific memory tables
CREATE TABLE IF NOT EXISTS ats_memory.agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(50) NOT NULL,
    memory_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(2560),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,

    INDEX idx_ats_memory_agent (agent_id),
    INDEX idx_ats_memory_type (memory_type),
    INDEX idx_ats_memory_created (created_at),
    CREATE INDEX idx_ats_memory_vector
        ON ats_memory.agent_memory
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
);

CREATE TABLE IF NOT EXISTS oma_memory.agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(50) NOT NULL,
    memory_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(2560),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,

    INDEX idx_oma_memory_agent (agent_id),
    INDEX idx_oma_memory_type (memory_type),
    INDEX idx_oma_memory_created (created_at),
    CREATE INDEX idx_oma_memory_vector
        ON oma_memory.agent_memory
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
);

CREATE TABLE IF NOT EXISTS smc_memory.agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(50) NOT NULL,
    memory_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(2560),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,

    INDEX idx_smc_memory_agent (agent_id),
    INDEX idx_smc_memory_type (memory_type),
    INDEX idx_smc_memory_created (created_at),
    CREATE INDEX idx_smc_memory_vector
        ON smc_memory.agent_memory
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
);

-- Performance monitoring tables
CREATE TABLE IF NOT EXISTS shared_memory.performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit VARCHAR(50),
    tags JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    agent_id VARCHAR(50),

    INDEX idx_performance_metric_name (metric_name),
    INDEX idx_performance_timestamp (timestamp),
    INDEX idx_performance_agent (agent_id),
    INDEX idx_performance_tags USING GIN (tags)
);

-- Memory usage statistics
CREATE TABLE IF NOT EXISTS shared_memory.memory_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(50) NOT NULL,
    memory_category VARCHAR(10) CHECK (memory_category IN ('ats', 'oma', 'smc')),
    total_documents INTEGER DEFAULT 0,
    total_embeddings INTEGER DEFAULT 0,
    total_entities INTEGER DEFAULT 0,
    total_relationships INTEGER DEFAULT 0,
    storage_used_bytes BIGINT DEFAULT 0,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_memory_usage_agent (agent_id),
    INDEX idx_memory_usage_category (memory_category),
    INDEX idx_memory_usage_activity (last_activity)
);

-- Enhanced stored procedures for memory operations
CREATE OR REPLACE FUNCTION shared_memory.semantic_search(
    query_vector vector(2560),
    limit_count INTEGER DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.7,
    memory_filter VARCHAR(10) DEFAULT NULL,
    agent_filter VARCHAR(50) DEFAULT NULL
)
RETURNS TABLE (
    document_id UUID,
    content TEXT,
    similarity_score FLOAT,
    agent_id VARCHAR(50),
    memory_category VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.document_id,
        e.content,
        1 - (e.embedding <=> query_vector) as similarity_score,
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

-- Procedure to clean up expired memory
CREATE OR REPLACE FUNCTION shared_memory.cleanup_expired_memory()
RETURNS INTEGER AS $$
DECLARE
    cleanup_count INTEGER := 0;
BEGIN
    -- Clean up expired agent memory
    DELETE FROM ats_memory.agent_memory WHERE expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS cleanup_count = ROW_COUNT;

    DELETE FROM oma_memory.agent_memory WHERE expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS cleanup_count = cleanup_count + ROW_COUNT;

    DELETE FROM smc_memory.agent_memory WHERE expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS cleanup_count = cleanup_count + ROW_COUNT;

    RETURN cleanup_count;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update memory usage statistics
CREATE OR REPLACE FUNCTION shared_memory.update_memory_usage()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO shared_memory.memory_usage (
        agent_id,
        memory_category,
        total_documents,
        last_activity
    ) VALUES (
        NEW.agent_id,
        NEW.memory_category,
        1,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (agent_id, memory_category)
    DO UPDATE SET
        total_documents = memory_usage.total_documents + 1,
        last_activity = CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to documents table
CREATE TRIGGER update_memory_stats_after_insert
    AFTER INSERT ON shared_memory.documents
    FOR EACH ROW
    EXECUTE FUNCTION shared_memory.update_memory_usage();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA shared_memory TO cognee_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ats_memory TO cognee_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA oma_memory TO cognee_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA smc_memory TO cognee_user;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA shared_memory TO cognee_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ats_memory TO cognee_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA oma_memory TO cognee_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA smc_memory TO cognee_user;