-- Enhanced Cognee - Audit Log Table Migration
-- Version: 1.0.0
-- Date: 2026-02-06
-- Description: Create audit_log table for tracking all automated operations

-- Create audit_log table
CREATE TABLE IF NOT EXISTS cognee_db.audit_log (
    -- Primary key
    log_id VARCHAR(32) PRIMARY KEY,

    -- Timestamp
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Operation details
    operation_type VARCHAR(50) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'success', 'failure', 'partial'

    -- Related entities
    memory_id UUID,

    -- Operation details (JSON)
    details JSONB,

    -- Performance metrics
    execution_time_ms FLOAT,

    -- Error tracking
    error_message TEXT,

    -- Additional context (JSON)
    additional_context JSONB,

    -- Indexes for efficient querying
    CONSTRAINT valid_status CHECK (status IN ('success', 'failure', 'partial'))
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON cognee_db.audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_operation_type ON cognee_db.audit_log(operation_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_agent_id ON cognee_db.audit_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_status ON cognee_db.audit_log(status);
CREATE INDEX IF NOT EXISTS idx_audit_log_memory_id ON cognee_db.audit_log(memory_id);

-- Composite index for time-range queries with filters
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp_agent
    ON cognee_db.audit_log(timestamp DESC, agent_id);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp_operation
    ON cognee_db.audit_log(timestamp DESC, operation_type);

-- GIN index for JSONB details (for advanced queries)
CREATE INDEX IF NOT EXISTS idx_audit_log_details_gin
    ON cognee_db.audit_log USING GIN (details);

CREATE INDEX IF NOT EXISTS idx_audit_log_context_gin
    ON cognee_db.audit_log USING GIN (additional_context);

-- Create a partitioned table for large-scale deployments (optional)
-- Uncomment if you expect very high log volumes

/*
-- Partition by month (for better performance and easier cleanup)
CREATE TABLE cognee_db.audit_log_partitioned (
    LIKE cognee_db.audit_log INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create partitions for current and future months
CREATE TABLE cognee_db.audit_log_2026_02 PARTITION OF cognee_db.audit_log_partitioned
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE cognee_db.audit_log_2026_03 PARTITION OF cognee_db.audit_log_partitioned
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Function to create future partitions automatically
CREATE OR REPLACE FUNCTION cognee_db.create_monthly_partition()
RETURNS void AS $$
DECLARE
    partition_date TEXT;
    start_date TEXT;
    end_date TEXT;
BEGIN
    partition_date := to_char(CURRENT_DATE + interval '1 month', 'YYYY_MM');
    start_date := to_char(CURRENT_DATE + interval '1 month', 'YYYY-MM-DD');
    end_date := to_char(CURRENT_DATE + interval '2 months', 'YYYY-MM-DD');

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS cognee_db.audit_log_%s PARTITION OF cognee_db.audit_log_partitioned
         FOR VALUES FROM (%L) TO (%L)',
        partition_date, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;
*/

-- Create view for common analytics queries
CREATE OR REPLACE VIEW cognee_db.v_audit_log_summary AS
SELECT
    date_trunc('day', timestamp) AS date,
    operation_type,
    agent_id,
    COUNT(*) AS total_operations,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successful_operations,
    SUM(CASE WHEN status = 'failure' THEN 1 ELSE 0 END) AS failed_operations,
    AVG(execution_time_ms) AS avg_execution_time_ms,
    MIN(execution_time_ms) AS min_execution_time_ms,
    MAX(execution_time_ms) AS max_execution_time_ms
FROM cognee_db.audit_log
GROUP BY date_trunc('day', timestamp), operation_type, agent_id
ORDER BY date DESC, operation_type;

-- Create view for error tracking
CREATE OR REPLACE VIEW cognee_db.v_audit_log_errors AS
SELECT
    timestamp,
    log_id,
    operation_type,
    agent_id,
    error_message,
    details
FROM cognee_db.audit_log
WHERE status = 'failure'
ORDER BY timestamp DESC;

-- Create view for performance metrics
CREATE OR REPLACE VIEW cognee_db.v_audit_log_performance AS
SELECT
    operation_type,
    COUNT(*) AS call_count,
    AVG(execution_time_ms) AS avg_time_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY execution_time_ms) AS median_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms) AS p95_time_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY execution_time_ms) AS p99_time_ms,
    MIN(execution_time_ms) AS min_time_ms,
    MAX(execution_time_ms) AS max_time_ms
FROM cognee_db.audit_log
WHERE execution_time_ms IS NOT NULL
GROUP BY operation_type
ORDER BY call_count DESC;

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT ON cognee_db.audit_log TO cognee_user;
-- GRANT SELECT ON cognee_db.v_audit_log_summary TO cognee_user;
-- GRANT SELECT ON cognee_db.v_audit_log_errors TO cognee_user;
-- GRANT SELECT ON cognee_db.v_audit_log_performance TO cognee_user;

-- Add helpful comments
COMMENT ON TABLE cognee_db.audit_log IS 'Audit log for all automated operations in Enhanced Cognee';
COMMENT ON COLUMN cognee_db.audit_log.log_id IS 'Unique identifier for the log entry (SHA-256 hash)';
COMMENT ON COLUMN cognee_db.audit_log.timestamp IS 'Timestamp of the operation (UTC)';
COMMENT ON COLUMN cognee_db.audit_log.operation_type IS 'Type of operation performed (e.g., memory_add, deduplicate_run)';
COMMENT ON COLUMN cognee_db.audit_log.agent_id IS 'ID of the agent that performed the operation';
COMMENT ON COLUMN cognee_db.audit_log.status IS 'Operation status: success, failure, or partial';
COMMENT ON COLUMN cognee_db.audit_log.memory_id IS 'Associated memory ID (if applicable)';
COMMENT ON COLUMN cognee_db.audit_log.details IS 'JSON details of the operation (inputs, outputs, etc.)';
COMMENT ON COLUMN cognee_db.audit_log.execution_time_ms IS 'Execution time in milliseconds';
COMMENT ON COLUMN cognee_db.audit_log.error_message IS 'Error message if the operation failed';
COMMENT ON COLUMN cognee_db.audit_log.additional_context IS 'Additional context information (JSON)';

-- Function to cleanup old audit logs
CREATE OR REPLACE FUNCTION cognee_db.cleanup_old_audit_log(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM cognee_db.audit_log
    WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cognee_db.cleanup_old_audit_log(INTEGER) IS 'Cleanup audit logs older than specified retention period';

-- Verify table creation
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'audit_log') AS column_count
FROM information_schema.tables
WHERE table_name = 'audit_log' AND table_schema = 'cognee_db';
