-- Enhanced Cognee - Undo Log Table Migration
-- Version: 1.0.0
-- Date: 2026-02-06
-- Description: Create undo_log table for tracking undoable operations

-- Create undo_log table
CREATE TABLE IF NOT EXISTS cognee_db.undo_log (
    -- Primary key
    undo_id VARCHAR(36) PRIMARY KEY,  -- UUID

    -- Operation details
    operation_type VARCHAR(50) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- State tracking
    original_state JSONB NOT NULL,  -- State before operation
    new_state JSONB NOT NULL,        -- State after operation

    -- Related entities
    memory_id UUID,
    category VARCHAR(255),
    operation_chain_id VARCHAR(36),  -- For grouping related operations

    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, completed, failed, expired
    error_message TEXT,

    -- Expiration
    expiration_date TIMESTAMPTZ NOT NULL,

    -- Additional metadata
    metadata JSONB,

    -- Constraints
    CONSTRAINT valid_undo_status CHECK (status IN ('pending', 'completed', 'failed', 'expired'))
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_undo_log_timestamp ON cognee_db.undo_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_undo_log_agent_id ON cognee_db.undo_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_undo_log_operation_type ON cognee_db.undo_log(operation_type);
CREATE INDEX IF NOT EXISTS idx_undo_log_status ON cognee_db.undo_log(status);
CREATE INDEX IF NOT EXISTS idx_undo_log_memory_id ON cognee_db.undo_log(memory_id);
CREATE INDEX IF NOT EXISTS idx_undo_log_chain_id ON cognee_db.undo_log(operation_chain_id);
CREATE INDEX IF NOT EXISTS idx_undo_log_expiration ON cognee_db.undo_log(expiration_date);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_undo_log_agent_timestamp
    ON cognee_db.undo_log(agent_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_undo_log_status_timestamp
    ON cognee_db.undo_log(status, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_undo_log_chain_timestamp
    ON cognee_db.undo_log(operation_chain_id, timestamp DESC);

-- GIN index for JSONB state data (for advanced queries)
CREATE INDEX IF NOT EXISTS idx_undo_log_original_state_gin
    ON cognee_db.undo_log USING GIN (original_state);

CREATE INDEX IF NOT EXISTS idx_undo_log_new_state_gin
    ON cognee_db.undo_log USING GIN (new_state);

CREATE INDEX IF NOT EXISTS idx_undo_log_metadata_gin
    ON cognee_db.undo_log USING GIN (metadata);

-- Create view for undo operations pending undo
CREATE OR REPLACE VIEW cognee_db.v_pending_undo_operations AS
SELECT
    undo_id,
    operation_type,
    agent_id,
    timestamp,
    memory_id,
    category,
    operation_chain_id,
    expiration_date
FROM cognee_db.undo_log
WHERE status = 'pending'
  AND expiration_date > NOW()
ORDER BY timestamp DESC;

-- Create view for undo statistics by agent
CREATE OR REPLACE VIEW cognee_db.v_undo_statistics_by_agent AS
SELECT
    agent_id,
    COUNT(*) AS total_operations,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_undos,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_undos,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_undos,
    MAX(timestamp) AS last_undo_timestamp
FROM cognee_db.undo_log
GROUP BY agent_id
ORDER BY total_operations DESC;

-- Create view for undo operations by type
CREATE OR REPLACE VIEW cognee_db.v_undo_statistics_by_type AS
SELECT
    operation_type,
    COUNT(*) AS total_operations,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS successful_undos,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_undos,
    AVG(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS success_rate
FROM cognee_db.undo_log
GROUP BY operation_type
ORDER BY total_operations DESC;

-- Create view for operation chains
CREATE OR REPLACE VIEW cognee_db.v_operation_chains AS
SELECT
    operation_chain_id,
    COUNT(*) AS operation_count,
    ARRAY_AGG(operation_type ORDER BY timestamp) AS operations,
    MIN(timestamp) AS chain_start,
    MAX(timestamp) AS chain_end,
    agent_id,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_count,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_count
FROM cognee_db.undo_log
WHERE operation_chain_id IS NOT NULL
GROUP BY operation_chain_id, agent_id
ORDER BY chain_start DESC;

-- Function to cleanup expired undo entries
CREATE OR REPLACE FUNCTION cognee_db.cleanup_expired_undo_entries()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM cognee_db.undo_log
    WHERE expiration_date < NOW()
      AND status = 'pending';  -- Only delete pending entries

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cognee_db.cleanup_expired_undo_entries() IS
'Cleanup expired undo entries that are still pending';

-- Function to get undo history for an agent
CREATE OR REPLACE FUNCTION cognee_db.get_undo_history_for_agent(
    p_agent_id VARCHAR,
    p_limit INTEGER DEFAULT 50
) RETURNS TABLE (
    undo_id VARCHAR,
    operation_type VARCHAR,
    timestamp TIMESTAMPTZ,
    memory_id UUID,
    status VARCHAR,
    expiration_date TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ul.undo_id,
        ul.operation_type,
        ul.timestamp,
        ul.memory_id,
        ul.status,
        ul.expiration_date
    FROM cognee_db.undo_log ul
    WHERE ul.agent_id = p_agent_id
      AND ul.expiration_date > NOW()
    ORDER BY ul.timestamp DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cognee_db.get_undo_history_for_agent(VARCHAR, INTEGER) IS
'Get undo history for a specific agent';

-- Function to get operations in a chain
CREATE OR REPLACE FUNCTION cognee_db.get_operation_chain(
    p_chain_id VARCHAR
) RETURNS TABLE (
    undo_id VARCHAR,
    operation_type VARCHAR,
    timestamp TIMESTAMPTZ,
    memory_id UUID,
    status VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ul.undo_id,
        ul.operation_type,
        ul.timestamp,
        ul.memory_id,
        ul.status
    FROM cognee_db.undo_log ul
    WHERE ul.operation_chain_id = p_chain_id
    ORDER BY ul.timestamp ASC;  -- Oldest first for chain viewing
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cognee_db.get_operation_chain(VARCHAR) IS
'Get all operations in an undo chain';

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE ON cognee_db.undo_log TO cognee_user;
-- GRANT SELECT ON cognee_db.v_pending_undo_operations TO cognee_user;
-- GRANT SELECT ON cognee_db.v_undo_statistics_by_agent TO cognee_user;
-- GRANT SELECT ON cognee_db.v_undo_statistics_by_type TO cognee_user;
-- GRANT SELECT ON cognee_db.v_operation_chains TO cognee_user;
-- GRANT EXECUTE ON FUNCTION cognee_db.get_undo_history_for_agent(VARCHAR, INTEGER) TO cognee_user;
-- GRANT EXECUTE ON FUNCTION cognee_db.get_operation_chain(VARCHAR) TO cognee_user;

-- Add helpful comments
COMMENT ON TABLE cognee_db.undo_log IS 'Undo log for tracking reversible automated operations';
COMMENT ON COLUMN cognee_db.undo_log.undo_id IS 'Unique identifier for the undo entry (UUID)';
COMMENT ON COLUMN cognee_db.undo_log.operation_type IS 'Type of operation (e.g., memory_add, memory_update)';
COMMENT ON COLUMN cognee_db.undo_log.agent_id IS 'ID of the agent that performed the operation';
COMMENT ON COLUMN cognee_db.undo_log.original_state IS 'State before the operation (JSON)';
COMMENT ON COLUMN cognee_db.undo_log.new_state IS 'State after the operation (JSON)';
COMMENT ON COLUMN cognee_db.undo_log.memory_id IS 'Associated memory ID (if applicable)';
COMMENT ON COLUMN cognee_db.undo_log.operation_chain_id IS 'ID for grouping related operations in a chain';
COMMENT ON COLUMN cognee_db.undo_log.status IS 'Undo status: pending, completed, failed, or expired';
COMMENT ON COLUMN cognee_db.undo_log.expiration_date IS 'When this undo entry expires and can no longer be used';
COMMENT ON COLUMN cognee_db.undo_log.metadata IS 'Additional metadata about the operation (JSON)';

-- Verify table creation
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'undo_log') AS column_count
FROM information_schema.tables
WHERE table_name = 'undo_log' AND table_schema = 'cognee_db';
