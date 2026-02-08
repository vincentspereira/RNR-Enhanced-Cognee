-- Enhanced Cognee - Structured Memory Model Migration
--
-- This migration adds hierarchical observation structure like claude-mem.
-- Enables structured memory types, concepts, and rich metadata.
--
-- Author: Enhanced Cognee Team
-- Version: 1.0.0
-- Date: 2026-02-06

-- Create memory type enumeration
CREATE TYPE memory_type AS ENUM (
    'bugfix',      -- Fixing a bug or error
    'feature',     -- Adding new functionality
    'decision',    -- Making a design or architectural decision
    'refactor',    -- Refactoring existing code
    'discovery',   -- Discovering how something works
    'general'      -- General observations
);

-- Create memory concept enumeration
CREATE TYPE memory_concept AS ENUM (
    'how-it-works',   -- Understanding how something works
    'gotcha',          -- Common pitfalls or edge cases
    'trade-off',       -- Trade-offs between alternatives
    'pattern',         -- Design patterns or best practices
    'general'          -- General concepts
);

-- Add structured columns to documents table
ALTER TABLE shared_memory.documents
ADD COLUMN IF NOT EXISTS memory_type memory_type DEFAULT 'general',
ADD COLUMN IF NOT EXISTS memory_concept memory_concept DEFAULT 'general',
ADD COLUMN IF NOT EXISTS narrative TEXT,
ADD COLUMN IF NOT EXISTS before_state TEXT,
ADD COLUMN IF NOT EXISTS after_state TEXT,
ADD COLUMN IF NOT EXISTS files JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS facts JSONB DEFAULT '[]'::jsonb;

-- Add comments for new columns
COMMENT ON COLUMN shared_memory.documents.memory_type IS 'Structured memory type (bugfix, feature, decision, refactor, discovery, general)';
COMMENT ON COLUMN shared_memory.documents.memory_concept IS 'Memory concept classification (how-it-works, gotcha, trade-off, pattern, general)';
COMMENT ON COLUMN shared_memory.documents.narrative IS 'Detailed narrative explanation of the memory';
COMMENT ON COLUMN shared_memory.documents.before_state IS 'State before the change (for bugfixes, refactors)';
COMMENT ON COLUMN shared_memory.documents.after_state IS 'State after the change';
COMMENT ON COLUMN shared_memory.documents.files IS 'List of files referenced in this memory';
COMMENT ON COLUMN shared_memory.documents.facts IS 'Key facts extracted from the memory';

-- Create indexes for filtering by type and concept
CREATE INDEX idx_documents_memory_type ON shared_memory.documents(memory_type);
CREATE INDEX idx_documents_memory_concept ON shared_memory.documents(memory_concept);
CREATE INDEX idx_documents_type_concept ON shared_memory.documents(memory_type, memory_concept);
CREATE INDEX idx_documents_files ON shared_memory.documents USING gin (files jsonb_path_ops);

-- Create view for structured observations
CREATE OR REPLACE VIEW shared_memory.structured_observations AS
SELECT
    id,
    agent_id,
    memory_type,
    memory_concept,
    COALESCE(summary, SUBSTRING(data_text FROM 1 FOR 200)) AS summary,
    narrative,
    created_at,
    files,
    facts
FROM shared_memory.documents
ORDER BY created_at DESC;

COMMENT ON VIEW shared_memory.structured_observations IS 'Structured observations with types and concepts';

-- Create view for observations by type
CREATE OR REPLACE VIEW shared_memory.observations_by_type AS
SELECT
    memory_type,
    COUNT(*) AS count,
    COUNT(*) FILTER (WHERE memory_concept = 'how-it-works') AS how_it_works,
    COUNT(*) FILTER (WHERE memory_concept = 'gotcha') AS gotchas,
    COUNT(*) FILTER (WHERE memory_concept = 'trade-off') AS trade_offs,
    COUNT(*) FILTER (WHERE memory_concept = 'pattern') AS patterns
FROM shared_memory.documents
GROUP BY memory_type
ORDER BY count DESC;

COMMENT ON VIEW shared_memory.observations_by_type IS 'Statistics on observations by memory type';

-- Create view for file references
CREATE OR REPLACE VIEW shared_memory.file_references AS
SELECT
    DISTINCT jsonb_array_elements_text(files) AS file_path,
    COUNT(*) AS reference_count,
    array_agg(DISTINCT id) AS memory_ids
FROM shared_memory.documents
WHERE jsonb_array_length(files) > 0
GROUP BY jsonb_array_elements_text(files)
ORDER BY reference_count DESC;

COMMENT ON VIEW shared_memory.file_references IS 'Files referenced in memories with counts';

-- Function to auto-categorize memory
CREATE OR REPLACE FUNCTION shared_memory.auto_categorize_memory(
    p_data_text TEXT,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS JSONB AS $$
DECLARE
    v_content_lower TEXT;
    v_memory_type memory_type;
    v_memory_concept memory_concept;
    v_files JSONB;
    v_facts JSONB;
BEGIN
    v_content_lower := LOWER(p_data_text);

    -- Auto-detect memory type
    IF v_content_lower ~* 'fix|bug|error|issue|patch|resolve' THEN
        v_memory_type := 'bugfix';
    ELSIF v_content_lower ~* 'add|implement|create|new|feature' THEN
        v_memory_type := 'feature';
    ELSIF v_content_lower ~* 'decided|choice|chose|selected|architecture|design' THEN
        v_memory_type := 'decision';
    ELSIF v_content_lower ~* 'refactor|clean|simplify|restructure|reorganize' THEN
        v_memory_type := 'refactor';
    ELSIF v_content_lower ~* 'discover|found|learned|investigate|explore' THEN
        v_memory_type := 'discovery';
    ELSE
        v_memory_type := 'general';
    END IF;

    -- Auto-detect memory concept
    IF v_content_lower ~* 'works|how to|implementation|mechanism' THEN
        v_memory_concept := 'how-it-works';
    ELSIF v_content_lower ~* 'gotcha|pitfall|edge case|watch out|be careful' THEN
        v_memory_concept := 'gotcha';
    ELSIF v_content_lower ~* 'trade-off|balance|between|versus|pro|con' THEN
        v_memory_concept := 'trade-off';
    ELSIF v_content_lower ~* 'pattern|practice|approach|method' THEN
        v_memory_concept := 'pattern';
    ELSE
        v_memory_concept := 'general';
    END IF;

    -- Extract file paths (simple heuristic)
    -- Look for common file patterns: path/to/file.ext, ./file.ext, etc.
    v_files := COALESCE(p_metadata->>'files', '[]')::jsonb;

    -- Extract facts (simple heuristic - sentences ending with periods)
    SELECT jsonb_agg(jsonb_build_object('fact', regexp_matches[1]))
    INTO v_facts
    FROM (
        SELECT regexp_matches[1]
        FROM regexp_matches(p_data_text, '([^.]+\\.)', 'g')
        LIMIT 10
    ) regexp_matches;

    IF v_facts IS NULL THEN
        v_facts := '[]'::jsonb;
    END IF;

    -- Return categorization
    RETURN jsonb_build_object(
        'memory_type', v_memory_type,
        'memory_concept', v_memory_concept,
        'files', v_files,
        'facts', v_facts
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.auto_categorize_memory(TEXT, JSONB) IS 'Auto-categorize a memory based on content analysis';

-- Trigger to auto-categorize on insert
CREATE OR REPLACE FUNCTION shared_memory.auto_categorize_on_insert()
RETURNS TRIGGER AS $$
DECLARE
    categorization JSONB;
BEGIN
    -- Auto-categorize the new memory
    categorization := shared_memory.auto_categorize_memory(NEW.data_text, NEW.metadata);

    -- Apply categorization
    NEW.memory_type := categorization->>'memory_type';
    NEW.memory_concept := categorization->>'memory_concept';
    NEW.files := COALESCE(categorization->'files', '[]'::jsonb);
    NEW.facts := COALESCE(categorization->'facts', '[]'::jsonb);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for auto-categorization
DROP TRIGGER IF EXISTS documents_auto_categorize_trigger ON shared_memory.documents;
CREATE TRIGGER documents_auto_categorize_trigger
    BEFORE INSERT ON shared_memory.documents
    FOR EACH ROW
    EXECUTE FUNCTION shared_memory.auto_categorize_on_insert();

-- Function to add structured observation
CREATE OR REPLACE FUNCTION shared_memory.add_structured_observation(
    p_data_text TEXT,
    p_agent_id VARCHAR DEFAULT 'default',
    p_memory_type memory_type DEFAULT 'general',
    p_memory_concept memory_concept DEFAULT 'general',
    p_narrative TEXT DEFAULT NULL,
    p_before_state TEXT DEFAULT NULL,
    p_after_state TEXT DEFAULT NULL,
    p_files JSONB DEFAULT '[]'::jsonb,
    p_facts JSONB DEFAULT '[]'::jsonb,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS UUID AS $$
DECLARE
    v_doc_id UUID;
    v_auto_cat JSONB;
BEGIN
    -- Auto-categorize if types are general
    IF p_memory_type = 'general' AND p_memory_concept = 'general' THEN
        v_auto_cat := shared_memory.auto_categorize_memory(p_data_text, p_metadata);

        -- Use detected values if not explicitly provided
        IF p_memory_type = 'general' THEN
            p_memory_type := v_auto_cat->>'memory_type';
        END IF;
        IF p_memory_concept = 'general' THEN
            p_memory_concept := v_auto_cat->>'memory_concept';
        END IF;

        -- Use extracted values if not provided
        IF jsonb_array_length(p_files) = 0 THEN
            p_files := COALESCE(v_auto_cat->'files', '[]'::jsonb);
        END IF;
        IF jsonb_array_length(p_facts) = 0 THEN
            p_facts := COALESCE(v_auto_cat->'facts', '[]'::jsonb);
        END IF;
    END IF;

    -- Insert the structured observation
    INSERT INTO shared_memory.documents (
        data_text,
        agent_id,
        memory_type,
        memory_concept,
        summary,
        narrative,
        before_state,
        after_state,
        files,
        facts,
        metadata,
        data_type,
        char_count
    ) VALUES (
        p_data_text,
        p_agent_id,
        p_memory_type,
        p_memory_concept,
        SUBSTRING(p_data_text FROM 1 FOR 200) || CASE WHEN LENGTH(p_data_text) > 200 THEN '...' ELSE '' END,
        p_narrative,
        p_before_state,
        p_after_state,
        p_files,
        p_facts,
        p_metadata,
        'observation',
        LENGTH(p_data_text)
    )
    RETURNING id INTO v_doc_id;

    RETURN v_doc_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.add_structured_observation IS 'Add a structured observation with auto-categorization';

-- Function to search by memory type
CREATE OR REPLACE FUNCTION shared_memory.search_by_type(
    p_memory_type memory_type,
    p_agent_id VARCHAR DEFAULT 'default',
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    memory_id UUID,
    data_text TEXT,
    memory_type memory_type,
    memory_concept memory_concept,
    summary TEXT,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.data_text,
        d.memory_type,
        d.memory_concept,
        d.summary,
        d.created_at
    FROM shared_memory.documents d
    WHERE d.agent_id = p_agent_id
      AND d.memory_type = p_memory_type
    ORDER BY d.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to search by memory concept
CREATE OR REPLACE FUNCTION shared_memory.search_by_concept(
    p_memory_concept memory_concept,
    p_agent_id VARCHAR DEFAULT 'default',
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    memory_id UUID,
    data_text TEXT,
    memory_type memory_type,
    memory_concept memory_concept,
    summary TEXT,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.data_text,
        d.memory_type,
        d.memory_concept,
        d.summary,
        d.created_at
    FROM shared_memory.documents d
    WHERE d.agent_id = p_agent_id
      AND d.memory_concept = p_memory_concept
    ORDER BY d.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to search by file reference
CREATE OR REPLACE FUNCTION shared_memory.search_by_file(
    p_file_path TEXT,
    p_agent_id VARCHAR DEFAULT 'default',
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    memory_id UUID,
    data_text TEXT,
    memory_type memory_type,
    memory_concept memory_concept,
    summary TEXT,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.data_text,
        d.memory_type,
        d.memory_concept,
        d.summary,
        d.created_at
    FROM shared_memory.documents d
    WHERE d.agent_id = p_agent_id
      AND p_file_path = ANY(SELECT jsonb_array_elements_text(d.files))
    ORDER BY d.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to migrate existing data
CREATE OR REPLACE FUNCTION shared_memory.migrate_to_structured()
RETURNS INTEGER AS $$
DECLARE
    v_migrated INTEGER;
BEGIN
    -- Categorize existing documents that don't have structured data
    UPDATE shared_memory.documents d
    SET
        memory_type = (auto_categorize_memory(d.data_text, d.metadata)->>'memory_type')::memory_type,
        memory_concept = (auto_categorize_memory(d.data_text, d.metadata)->>'memory_concept')::memory_concept,
        files = COALESCE(auto_categorize_memory(d.data_text, d.metadata)->'files', '[]'::jsonb),
        facts = COALESCE(auto_categorize_memory(d.data_text, d.metadata)->'facts', '[]'::jsonb)
    WHERE d.memory_type IS NULL OR d.memory_type = 'general';

    GET DIAGNOSTICS v_migrated = ROW_COUNT;

    RETURN v_migrated;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.migrate_to_structured() IS 'Migrate existing documents to structured format';

-- Run migration for existing data
-- SELECT shared_memory.migrate_to_structured() AS migrated_count;

-- Statistics view for structured observations
CREATE OR REPLACE VIEW shared_memory.structured_stats AS
SELECT
    COUNT(*) AS total_observations,
    COUNT(*) FILTER (WHERE memory_type = 'bugfix') AS bugfix_count,
    COUNT(*) FILTER (WHERE memory_type = 'feature') AS feature_count,
    COUNT(*) FILTER (WHERE memory_type = 'decision') AS decision_count,
    COUNT(*) FILTER (WHERE memory_type = 'refactor') AS refactor_count,
    COUNT(*) FILTER (WHERE memory_type = 'discovery') AS discovery_count,
    COUNT(*) FILTER (WHERE memory_type = 'general') AS general_count,
    COUNT(*) FILTER (WHERE memory_concept = 'how-it-works') AS how_it_works_count,
    COUNT(*) FILTER (WHERE memory_concept = 'gotcha') AS gotcha_count,
    COUNT(*) FILTER (WHERE memory_concept = 'trade-off') AS trade_off_count,
    COUNT(*) FILTER (WHERE memory_concept = 'pattern') AS pattern_count,
    COUNT(DISTINCT jsonb_array_elements_text(files)) AS unique_files_referenced
FROM shared_memory.documents;

COMMENT ON VIEW shared_memory.structured_stats IS 'Statistics on structured observations';

-- Grant permissions (adjust as needed)
-- GRANT USAGE ON TYPE memory_type TO your_user;
-- GRANT USAGE ON TYPE memory_concept TO your_user;
-- GRANT SELECT ON shared_memory.structured_observations TO your_user;
-- GRANT SELECT ON shared_memory.observations_by_type TO your_user;
-- GRANT SELECT ON shared_memory.file_references TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.auto_categorize_memory(TEXT, JSONB) TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.add_structured_observation TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.search_by_type TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.search_by_concept TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.search_by_file TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.migrate_to_structured TO your_user;
