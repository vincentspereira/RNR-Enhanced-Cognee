-- Enhanced Cognee - Sessions Table Migration
--
-- This migration adds session tracking for Claude Code integration.
-- Sessions allow for multi-prompt conversation tracking and context continuity.
--
-- Author: Enhanced Cognee Team
-- Version: 1.0.0
-- Date: 2026-02-06

-- Create sessions table
CREATE TABLE IF NOT EXISTS shared_memory.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL DEFAULT 'default',
    agent_id VARCHAR(255) NOT NULL DEFAULT 'claude-code',
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP,
    summary TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Add comments
COMMENT ON TABLE shared_memory.sessions IS 'Tracks Claude Code sessions for context continuity';
COMMENT ON COLUMN shared_memory.sessions.id IS 'Unique session identifier';
COMMENT ON COLUMN shared_memory.sessions.user_id IS 'User who owns the session';
COMMENT ON COLUMN shared_memory.sessions.agent_id IS 'Agent that participated in the session';
COMMENT ON COLUMN shared_memory.sessions.start_time IS 'When the session started';
COMMENT ON COLUMN shared_memory.sessions.end_time IS 'When the session ended (NULL if active)';
COMMENT ON COLUMN shared_memory.sessions.summary IS 'LLM-generated summary of the session';
COMMENT ON COLUMN shared_memory.sessions.metadata IS 'Additional session metadata (JSON)';
COMMENT ON COLUMN shared_memory.sessions.created_at IS 'When the session record was created';
COMMENT ON COLUMN shared_memory.sessions.updated_at IS 'When the session record was last updated';

-- Create indexes for efficient queries
CREATE INDEX idx_sessions_user_id ON shared_memory.sessions(user_id);
CREATE INDEX idx_sessions_agent_id ON shared_memory.sessions(agent_id);
CREATE INDEX idx_sessions_start_time ON shared_memory.sessions(start_time DESC);
CREATE INDEX idx_sessions_end_time ON shared_memory.sessions(end_time) WHERE end_time IS NOT NULL;
CREATE INDEX idx_sessions_active ON shared_memory.sessions(user_id, agent_id) WHERE end_time IS NULL;

-- Add session_id to documents table
ALTER TABLE shared_memory.documents
ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES shared_memory.sessions(id) ON DELETE SET NULL;

-- Create index for session-document queries
CREATE INDEX idx_documents_session_id ON shared_memory.documents(session_id) WHERE session_id IS NOT NULL;

-- Add comment for new column
COMMENT ON COLUMN shared_memory.documents.session_id IS 'Optional session association for context tracking';

-- Create view for active sessions
CREATE OR REPLACE VIEW shared_memory.active_sessions AS
SELECT
    id,
    user_id,
    agent_id,
    start_time,
    EXTRACT(EPOCH FROM (NOW() - start_time)) / 60 AS duration_minutes,
    metadata,
    created_at,
    updated_at
FROM shared_memory.sessions
WHERE end_time IS NULL;

COMMENT ON VIEW shared_memory.active_sessions IS 'Currently active sessions (end_time is NULL)';

-- Create view for session statistics
CREATE OR REPLACE VIEW shared_memory.session_stats AS
SELECT
    user_id,
    agent_id,
    COUNT(*) AS total_sessions,
    COUNT(*) FILTER (WHERE end_time IS NULL) AS active_sessions,
    COUNT(*) FILTER (WHERE end_time IS NOT NULL) AS completed_sessions,
    AVG(EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time)) / 60) AS avg_duration_minutes,
    MAX(start_time) AS last_session_start
FROM shared_memory.sessions
GROUP BY user_id, agent_id;

COMMENT ON VIEW shared_memory.session_stats IS 'Session statistics per user and agent';

-- Create view for session with memory counts
CREATE OR REPLACE VIEW shared_memory.session_memory_counts AS
SELECT
    s.id AS session_id,
    s.user_id,
    s.agent_id,
    s.start_time,
    s.end_time,
    COUNT(d.id) AS memory_count,
    COUNT(d.id) FILTER (WHERE d.data_type = 'document') AS document_count,
    COUNT(d.id) FILTER (WHERE d.data_type = 'observation') AS observation_count
FROM shared_memory.sessions s
LEFT JOIN shared_memory.documents d ON d.session_id = s.id
GROUP BY s.id, s.user_id, s.agent_id, s.start_time, s.end_time;

COMMENT ON VIEW shared_memory.session_memory_counts IS 'Sessions with associated memory counts';

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION shared_memory.update_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at
DROP TRIGGER IF EXISTS sessions_updated_at_trigger ON shared_memory.sessions;
CREATE TRIGGER sessions_updated_at_trigger
    BEFORE UPDATE ON shared_memory.sessions
    FOR EACH ROW
    EXECUTE FUNCTION shared_memory.update_sessions_updated_at();

-- Function to automatically end stale sessions
CREATE OR REPLACE FUNCTION shared_memory.end_stale_sessions()
RETURNS INTEGER AS $$
DECLARE
    stale_count INTEGER;
BEGIN
    -- End sessions that have been inactive for more than 24 hours
    UPDATE shared_memory.sessions
    SET end_time = NOW(),
        updated_at = NOW()
    WHERE end_time IS NULL
      AND start_time < NOW() - INTERVAL '24 hours';

    GET DIAGNOSTICS stale_count = ROW_COUNT;
    RETURN stale_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.end_stale_sessions() IS 'Automatically end sessions inactive for 24+ hours';

-- Function to get session context
CREATE OR REPLACE FUNCTION shared_memory.get_session_context(p_session_id UUID)
RETURNS TABLE (
    memory_id UUID,
    data_text TEXT,
    data_type VARCHAR(50),
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.data_text,
        d.data_type,
        d.created_at
    FROM shared_memory.documents d
    WHERE d.session_id = p_session_id
    ORDER BY d.created_at ASC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.get_session_context(UUID) IS 'Get all memories associated with a session';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON shared_memory.sessions TO your_user;
-- GRANT USAGE, SELECT ON SEQUENCE shared_memory.sessions_id_seq TO your_user;
-- GRANT SELECT ON shared_memory.active_sessions TO your_user;
-- GRANT SELECT ON shared_memory.session_stats TO your_user;
-- GRANT SELECT ON shared_memory.session_memory_counts TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.get_session_context(UUID) TO your_user;
