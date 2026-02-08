-- Enhanced Cognee - LLM Token Usage Tracking Table Migration
-- Version: 1.0.0
-- Date: 2026-02-06
-- Description: Create table for tracking LLM token usage and costs

-- Create llm_token_usage table
CREATE TABLE IF NOT EXISTS cognee_db.llm_token_usage (
    -- Primary tracking
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Request details
    agent_id VARCHAR(255) NOT NULL,
    operation VARCHAR(100) NOT NULL,  -- summarization, deduplication, extraction, etc.
    provider VARCHAR(50) NOT NULL,     -- anthropic, openai, litellm
    model VARCHAR(100) NOT NULL,       -- claude-3-5-sonnet-20241022, gpt-4, etc.

    -- Token counts
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,

    -- Cost tracking
    cost_usd DECIMAL(10, 6) NOT NULL,  -- Cost in USD

    -- Optional request tracking
    request_id VARCHAR(100),

    -- Additional metadata
    metadata JSONB,

    -- Constraints
    CONSTRAINT valid_tokens CHECK (input_tokens >= 0 AND output_tokens >= 0),
    CONSTRAINT valid_cost CHECK (cost_usd >= 0)
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_llm_token_usage_timestamp ON cognee_db.llm_token_usage(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_llm_token_usage_agent_id ON cognee_db.llm_token_usage(agent_id);
CREATE INDEX IF NOT EXISTS idx_llm_token_usage_operation ON cognee_db.llm_token_usage(operation);
CREATE INDEX IF NOT EXISTS idx_llm_token_usage_provider ON cognee_db.llm_token_usage(provider);
CREATE INDEX IF NOT EXISTS idx_llm_token_usage_model ON cognee_db.llm_token_usage(model);
CREATE INDEX IF NOT EXISTS idx_llm_token_usage_request_id ON cognee_db.llm_token_usage(request_id);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_llm_token_usage_agent_timestamp
    ON cognee_db.llm_token_usage(agent_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_llm_token_usage_operation_timestamp
    ON cognee_db.llm_token_usage(operation, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_llm_token_usage_provider_model
    ON cognee_db.llm_token_usage(provider, model);

-- Create view for usage summary by agent
CREATE OR REPLACE VIEW cognee_db.v_llm_usage_by_agent AS
SELECT
    agent_id,
    COUNT(*) as total_requests,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_tokens) as total_tokens,
    SUM(cost_usd) as total_cost_usd,
    AVG(total_tokens) as avg_tokens_per_request,
    MIN(timestamp) as first_request,
    MAX(timestamp) as last_request
FROM cognee_db.llm_token_usage
GROUP BY agent_id
ORDER BY total_tokens DESC;

-- Create view for usage summary by operation
CREATE OR REPLACE VIEW cognee_db.v_llm_usage_by_operation AS
SELECT
    operation,
    COUNT(*) as total_requests,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_tokens) as total_tokens,
    SUM(cost_usd) as total_cost_usd,
    AVG(total_tokens) as avg_tokens_per_request,
    AVG(input_tokens) as avg_input_tokens,
    AVG(output_tokens) as avg_output_tokens
FROM cognee_db.llm_token_usage
GROUP BY operation
ORDER BY total_tokens DESC;

-- Create view for usage summary by model
CREATE OR REPLACE VIEW cognee_db.v_llm_usage_by_model AS
SELECT
    provider,
    model,
    COUNT(*) as total_requests,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_tokens) as total_tokens,
    SUM(cost_usd) as total_cost_usd,
    AVG(total_tokens) as avg_tokens_per_request,
    MAX(total_tokens) as max_tokens_in_request
FROM cognee_db.llm_token_usage
GROUP BY provider, model
ORDER BY total_tokens DESC;

-- Create view for daily usage trends
CREATE OR REPLACE VIEW cognee_db.v_llm_daily_usage_trends AS
SELECT
    DATE_TRUNC('day', timestamp) as date,
    agent_id,
    operation,
    COUNT(*) as request_count,
    SUM(total_tokens) as total_tokens,
    SUM(cost_usd) as total_cost
FROM cognee_db.llm_token_usage
GROUP BY DATE_TRUNC('day', timestamp), agent_id, operation
ORDER BY date DESC, agent_id, operation;

-- Create view for cost analysis
CREATE OR REPLACE VIEW cognee_db.v_llm_cost_analysis AS
SELECT
    DATE_TRUNC('day', timestamp) as date,
    provider,
    model,
    SUM(cost_usd) as daily_cost,
    SUM(total_tokens) as daily_tokens,
    COUNT(*) as request_count,
    SUM(cost_usd) / NULLIF(SUM(total_tokens), 0) as cost_per_1k_tokens
FROM cognee_db.llm_token_usage
GROUP BY DATE_TRUNC('day', timestamp), provider, model
ORDER BY date DESC, daily_cost DESC;

-- Function to get token usage for an agent
CREATE OR REPLACE FUNCTION cognee_db.get_token_usage_for_agent(
    p_agent_id VARCHAR,
    p_hours_back INTEGER DEFAULT 24
) RETURNS TABLE (
    total_requests BIGINT,
    total_input_tokens BIGINT,
    total_output_tokens BIGINT,
    total_tokens BIGINT,
    total_cost DECIMAL(10, 6)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT,
        COALESCE(SUM(input_tokens), 0)::BIGINT,
        COALESCE(SUM(output_tokens), 0)::BIGINT,
        COALESCE(SUM(total_tokens), 0)::BIGINT,
        COALESCE(SUM(cost_usd), 0)::DECIMAL(10, 6)
    FROM cognee_db.llm_token_usage
    WHERE agent_id = p_agent_id
      AND timestamp > NOW() - (p_hours_back || ' hours')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cognee_db.get_token_usage_for_agent(VARCHAR, INTEGER) IS
'Get token usage statistics for a specific agent within time window';

-- Function to cleanup old token usage records
CREATE OR REPLACE FUNCTION cognee_db.cleanup_old_token_usage(p_retention_days INTEGER DEFAULT 90)
RETURNS BIGINT AS $$
DECLARE
    deleted_count BIGINT;
BEGIN
    DELETE FROM cognee_db.llm_token_usage
    WHERE timestamp < NOW() - (p_retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cognee_db.cleanup_old_token_usage(INTEGER) IS
'Cleanup token usage records older than specified retention period';

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT ON cognee_db.llm_token_usage TO cognee_user;
-- GRANT SELECT ON cognee_db.v_llm_usage_by_agent TO cognee_user;
-- GRANT SELECT ON cognee_db.v_llm_usage_by_operation TO cognee_user;
-- GRANT SELECT ON cognee_db.v_llm_usage_by_model TO cognee_user;
-- GRANT SELECT ON cognee_db.v_llm_daily_usage_trends TO cognee_user;
-- GRANT SELECT ON cognee_db.v_llm_cost_analysis TO cognee_user;
-- GRANT EXECUTE ON FUNCTION cognee_db.get_token_usage_for_agent(VARCHAR, INTEGER) TO cognee_user;

-- Add helpful comments
COMMENT ON TABLE cognee_db.llm_token_usage IS 'Tracks LLM API token usage and costs for Enhanced Cognee';
COMMENT ON COLUMN cognee_db.llm_token_usage.agent_id IS 'ID of the agent that made the LLM request';
COMMENT ON COLUMN cognee_db.llm_token_usage.operation IS 'Type of operation (summarization, deduplication, extraction, etc.)';
COMMENT ON COLUMN cognee_db.llm_token_usage.provider IS 'LLM provider (anthropic, openai, litellm)';
COMMENT ON COLUMN cognee_db.llm_token_usage.model IS 'Model name (claude-3-5-sonnet-20241022, gpt-4, etc.)';
COMMENT ON COLUMN cognee_db.llm_token_usage.input_tokens IS 'Number of tokens in the prompt';
COMMENT ON COLUMN cognee_db.llm_token_usage.output_tokens IS 'Number of tokens in the completion';
COMMENT ON COLUMN cognee_db.llm_token_usage.cost_usd IS 'Cost in USD based on provider pricing';
COMMENT ON COLUMN cognee_db.llm_token_usage.request_id IS 'Optional request identifier for tracking';

-- Verify table creation
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'llm_token_usage') AS column_count
FROM information_schema.tables
WHERE table_name = 'llm_token_usage' AND table_schema = 'cognee_db';
