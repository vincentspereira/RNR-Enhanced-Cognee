-- Enhanced Cognee - LLM Rate Limit Statistics Table Migration
-- Version: 1.0.0
-- Date: 2026-02-06
-- Description: Create table for tracking LLM API rate limit statistics

-- Create llm_rate_limit_stats table
CREATE TABLE IF NOT EXISTS cognee_db.llm_rate_limit_stats (
    -- Tracking
    provider VARCHAR(50) NOT NULL,
    api_key_hash VARCHAR(32) NOT NULL,  -- SHA-256 hash (first 16 chars)
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Request statistics
    total_requests BIGINT NOT NULL DEFAULT 0,
    successful_requests BIGINT NOT NULL DEFAULT 0,
    rate_limited_requests BIGINT NOT NULL DEFAULT 0,
    retried_requests BIGINT NOT NULL DEFAULT 0,

    -- Timing statistics
    total_wait_time FLOAT NOT NULL DEFAULT 0,  -- Total seconds waiting
    average_wait_time FLOAT NOT NULL DEFAULT 0,  -- Avg seconds per request

    -- Constraints and indexes
    PRIMARY KEY (provider, api_key_hash)
);

-- Create indexes for time-series queries
CREATE INDEX IF NOT EXISTS idx_llm_rate_limit_stats_timestamp
    ON cognee_db.llm_rate_limit_stats(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_llm_rate_limit_stats_provider
    ON cognee_db.llm_rate_limit_stats(provider);

-- Create view for rate limit performance
CREATE OR REPLACE VIEW cognee_db.v_rate_limit_performance AS
SELECT
    provider,
    api_key_hash,
    timestamp,
    total_requests,
    successful_requests,
    rate_limited_requests,
    retried_requests,
    ROUND(100.0 * successful_requests / NULLIF(total_requests, 0), 2) as success_rate,
    ROUND(100.0 * rate_limited_requests / NULLIF(total_requests, 0), 2) as rate_limit_hit_rate,
    ROUND(100.0 * retried_requests / NULLIF(total_requests, 0), 2) as retry_rate,
    ROUND(average_wait_time, 3) as avg_wait_seconds,
    ROUND(total_wait_time, 2) as total_wait_seconds
FROM cognee_db.llm_rate_limit_stats;

-- Create view for provider summary
CREATE OR REPLACE VIEW cognee_db.v_rate_limit_provider_summary AS
SELECT
    provider,
    COUNT(*) as number_of_keys,
    SUM(total_requests) as total_requests,
    SUM(successful_requests) as successful_requests,
    SUM(rate_limited_requests) as rate_limited_requests,
    SUM(retried_requests) as retried_requests,
    ROUND(AVG(average_wait_time), 3) as avg_wait_seconds,
    MAX(timestamp) as last_activity
FROM cognee_db.llm_rate_limit_stats
GROUP BY provider
ORDER BY total_requests DESC;

-- Function to cleanup old stats
CREATE OR REPLACE FUNCTION cognee_db.cleanup_old_rate_limit_stats(p_retention_days INTEGER DEFAULT 7)
RETURNS BIGINT AS $$
DECLARE
    deleted_count BIGINT;
BEGIN
    DELETE FROM cognee_db.llm_rate_limit_stats
    WHERE timestamp < NOW() - (p_retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE cognee_db.llm_rate_limit_stats IS 'Tracks LLM API rate limiting statistics and performance';
COMMENT ON COLUMN cognee_db.llm_rate_limit_stats.api_key_hash IS 'SHA-256 hash of API key (first 16 chars) for privacy';
COMMENT ON COLUMN cognee_db.llm_rate_limit_stats.success_rate IS 'Percentage of requests that succeeded';
COMMENT ON COLUMN cognee_db.llm_rate_limit_stats.rate_limit_hit_rate IS 'Percentage of requests that hit rate limits';
COMMENT ON COLUMN cognee_db.llm_rate_limit_stats.retry_rate IS 'Percentage of requests that were retried';

-- Verify table creation
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'llm_rate_limit_stats') AS column_count
FROM information_schema.tables
WHERE table_name = 'llm_rate_limit_stats' AND table_schema = 'cognee_db';
