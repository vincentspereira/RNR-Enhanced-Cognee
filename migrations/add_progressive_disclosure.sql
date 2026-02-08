-- Enhanced Cognee - Progressive Disclosure Support
--
-- This migration adds support for progressive disclosure (token-efficient search).
-- Adds summary column and indexes for efficient 3-layer search.
--
-- Author: Enhanced Cognee Team
-- Version: 1.0.0
-- Date: 2026-02-06

-- Add summary column to documents table
ALTER TABLE shared_memory.documents
ADD COLUMN IF NOT EXISTS summary TEXT;

-- Add comment for new column
COMMENT ON COLUMN shared_memory.documents.summary IS 'Brief summary for progressive disclosure (token-efficient search)';

-- Create index on summary for text search
CREATE INDEX IF NOT EXISTS idx_documents_summary_trgm
ON shared_memory.documents
USING gin (summary gin_trgm_ops);

-- Add computed column for character count (useful for token estimation)
ALTER TABLE shared_memory.documents
ADD COLUMN IF NOT EXISTS char_count INTEGER;

-- Update char_count for existing documents
UPDATE shared_memory.documents
SET char_count = LENGTH(data_text)
WHERE char_count IS NULL;

-- Add index on char_count for filtering
CREATE INDEX IF NOT EXISTS idx_documents_char_count
ON shared_memory.documents(char_count);

-- Comment on char_count
COMMENT ON COLUMN shared_memory.documents.char_count IS 'Character count for token estimation and filtering';

-- Create view for progressive disclosure index
CREATE OR REPLACE VIEW shared_memory.progressive_disclosure_index AS
SELECT
    id,
    COALESCE(summary, SUBSTRING(data_text FROM 1 FOR 200)) AS summary,
    data_type,
    created_at,
    updated_at,
    char_count,
    ROUND(CHAR_LENGTH(COALESCE(data_text, '')) / 4.0) AS estimated_tokens,
    metadata
FROM shared_memory.documents
ORDER BY created_at DESC;

COMMENT ON VIEW shared_memory.progressive_disclosure_index IS 'Compact index for Layer 1 progressive disclosure search';

-- Create view for timeline context
CREATE OR REPLACE VIEW shared_memory.timeline_context AS
SELECT
    id,
    data_type,
    created_at,
    LAG(created_at) OVER (ORDER BY created_at) AS previous_memory_at,
    LEAD(created_at) OVER (ORDER BY created_at) AS next_memory_at,
    char_count,
    ROUND(CHAR_LENGTH(COALESCE(data_text, '')) / 4.0) AS estimated_tokens
FROM shared_memory.documents;

COMMENT ON VIEW shared_memory.timeline_context IS 'Chronological context for Layer 2 timeline queries';

-- Function to generate summary for existing documents
CREATE OR REPLACE FUNCTION shared_memory.generate_document_summary(p_doc_id UUID)
RETURNS TEXT AS $$
DECLARE
    v_summary TEXT;
    v_data_text TEXT;
BEGIN
    -- Get document text
    SELECT data_text INTO v_data_text
    FROM shared_memory.documents
    WHERE id = p_doc_id;

    -- Generate summary (first 200 chars + ...)
    v_summary := SUBSTRING(v_data_text FROM 1 FOR 200);
    IF LENGTH(v_data_text) > 200 THEN
        v_summary := v_summary || '...';
    END IF;

    -- Update document
    UPDATE shared_memory.documents
    SET summary = v_summary,
        char_count = LENGTH(v_data_text)
    WHERE id = p_doc_id;

    RETURN v_summary;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.generate_document_summary(UUID) IS 'Generate summary for a document (first 200 chars)';

-- Function to batch generate summaries for all documents
CREATE OR REPLACE FUNCTION shared_memory.generate_all_summaries()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Update all documents without summaries
    UPDATE shared_memory.documents
    SET summary = SUBSTRING(data_text FROM 1 FOR 200) ||
        CASE WHEN LENGTH(data_text) > 200 THEN '...' ELSE '' END,
        char_count = LENGTH(data_text)
    WHERE summary IS NULL;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.generate_all_summaries() IS 'Generate summaries for all documents missing them';

-- Function to get compact search results (Layer 1)
CREATE OR REPLACE FUNCTION shared_memory.search_compact(
    p_query TEXT,
    p_agent_id VARCHAR DEFAULT 'default',
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    memory_id UUID,
    summary TEXT,
    data_type VARCHAR,
    created_at TIMESTAMP,
    estimated_tokens NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.summary,
        d.data_type,
        d.created_at,
        ROUND(LENGTH(d.data_text) / 4.0) AS estimated_tokens
    FROM shared_memory.documents d
    WHERE d.agent_id = p_agent_id
      AND (
          d.data_text ILIKE ('%' || p_query || '%')
          OR d.summary ILIKE ('%' || p_query || '%')
      )
    ORDER BY d.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.search_compact(TEXT, VARCHAR, INTEGER) IS 'Layer 1: Compact search results (IDs + summaries only)';

-- Function to get timeline context (Layer 2)
CREATE OR REPLACE FUNCTION shared_memory.get_timeline_context(
    p_memory_id UUID,
    p_before INT DEFAULT 5,
    p_after INT DEFAULT 5
)
RETURNS TABLE (
    memory_id UUID,
    summary TEXT,
    data_type VARCHAR,
    created_at TIMESTAMP,
    position VARCHAR,  -- 'before', 'current', or 'after'
    estimated_tokens NUMERIC
) AS $$
DECLARE
    v_created_at TIMESTAMP;
BEGIN
    -- Get the target memory's created_at timestamp
    SELECT created_at INTO v_created_at
    FROM shared_memory.documents
    WHERE id = p_memory_id;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Memories before (chronological)
    RETURN QUERY
    SELECT
        id,
        summary,
        data_type,
        created_at,
        'before'::VARCHAR,
        ROUND(LENGTH(data_text) / 4.0)
    FROM shared_memory.documents
    WHERE created_at < v_created_at
    ORDER BY created_at DESC
    LIMIT p_before

    UNION ALL

    -- Current memory
    SELECT
        id,
        summary,
        data_type,
        created_at,
        'current'::VARCHAR,
        ROUND(LENGTH(data_text) / 4.0)
    FROM shared_memory.documents
    WHERE id = p_memory_id

    UNION ALL

    -- Memories after (chronological)
    SELECT
        id,
        summary,
        data_type,
        created_at,
        'after'::VARCHAR,
        ROUND(LENGTH(data_text) / 4.0)
    FROM shared_memory.documents
    WHERE created_at > v_created_at
    ORDER BY created_at ASC
    LIMIT p_after;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.get_timeline_context(UUID, INT, INT) IS 'Layer 2: Get chronological context around a memory';

-- Function to batch get memories (Layer 3)
CREATE OR REPLACE FUNCTION shared_memory.get_memories_batch(
    p_memory_ids UUID[]
)
RETURNS TABLE (
    memory_id UUID,
    data_text TEXT,
    data_type VARCHAR,
    summary TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.data_text,
        d.data_type,
        d.summary,
        d.created_at,
        d.updated_at,
        d.metadata
    FROM shared_memory.documents d
    WHERE d.id = ANY(p_memory_ids)
    ORDER BY d.created_at;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.get_memories_batch(UUID[]) IS 'Layer 3: Get full details for multiple memories';

-- Trigger to auto-generate summary on insert
CREATE OR REPLACE FUNCTION shared_memory.auto_generate_summary()
RETURNS TRIGGER AS $$
BEGIN
    -- Generate summary from first 200 characters
    NEW.summary := SUBSTRING(NEW.data_text FROM 1 FOR 200);
    IF LENGTH(NEW.data_text) > 200 THEN
        NEW.summary := NEW.summary || '...';
    END IF;

    -- Update char_count
    NEW.char_count := LENGTH(NEW.data_text);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-generate summary
DROP TRIGGER IF EXISTS documents_auto_summary_trigger ON shared_memory.documents;
CREATE TRIGGER documents_auto_summary_trigger
    BEFORE INSERT ON shared_memory.documents
    FOR EACH ROW
    EXECUTE FUNCTION shared_memory.auto_generate_summary();

-- Trigger to update summary on data_text update
CREATE OR REPLACE FUNCTION shared_memory.update_summary_on_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update if data_text has changed
    IF NEW.data_text IS DISTINCT FROM OLD.data_text THEN
        NEW.summary := SUBSTRING(NEW.data_text FROM 1 FOR 200);
        IF LENGTH(NEW.data_text) > 200 THEN
            NEW.summary := NEW.summary || '...';
        END IF;
        NEW.char_count := LENGTH(NEW.data_text);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updates
DROP TRIGGER IF EXISTS documents_update_summary_trigger ON shared_memory.documents;
CREATE TRIGGER documents_update_summary_trigger
    BEFORE UPDATE OF data_text ON shared_memory.documents
    FOR EACH ROW
    EXECUTE FUNCTION shared_memory.update_summary_on_change();

-- Create index for improved search performance
CREATE INDEX IF NOT EXISTS idx_documents_data_text_trgm
ON shared_memory.documents
USING gin (data_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_documents_data_type_created
ON shared_memory.documents(data_type, created_at DESC);

-- Create index for agent_id filtering
CREATE INDEX IF NOT EXISTS idx_documents_agent_id_created
ON shared_memory.documents(agent_id, created_at DESC);

-- Statistics view for token efficiency
CREATE OR REPLACE VIEW shared_memory.token_efficiency_stats AS
SELECT
    COUNT(*) AS total_memories,
    COUNT(*) FILTER (WHERE char_count <= 500) AS small_memories,
    COUNT(*) FILTER (WHERE char_count > 500 AND char_count <= 2000) AS medium_memories,
    COUNT(*) FILTER (WHERE char_count > 2000) AS large_memories,
    ROUND(AVG(ROUND(CHAR_LENGTH(data_text) / 4.0)), 2) AS avg_tokens_per_memory,
    ROUND(AVG(CHAR_LENGTH(summary)), 2) AS avg_summary_chars,
    ROUND(
        (1.0 - (AVG(CHAR_LENGTH(summary)) / AVG(CHAR_LENGTH(data_text)))) * 100.0,
        2
    ) AS token_efficiency_percent
FROM shared_memory.documents;

COMMENT ON VIEW shared_memory.token_efficiency_stats IS 'Statistics on token efficiency of progressive disclosure';

-- Generate summaries for existing documents
SELECT shared_memory.generate_all_summaries() AS summaries_generated;

-- Grant permissions (adjust as needed)
-- GRANT SELECT ON shared_memory.progressive_disclosure_index TO your_user;
-- GRANT SELECT ON shared_memory.timeline_context TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.search_compact(TEXT, VARCHAR, INTEGER) TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.get_timeline_context(UUID, INT, INT) TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.get_memories_batch(UUID[]) TO your_user;
