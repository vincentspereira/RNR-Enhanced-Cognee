-- Enhanced Cognee Lite Mode Schema
-- SQLite database with FTS5 full-text search
-- No Docker required, lightweight setup

-- Enable FTS5 extension (usually built-in)
-- CREATE EXTENSION IF NOT EXISTS fts5;  -- Not needed in SQLite

-- Documents table (memories)
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    data_id TEXT UNIQUE NOT NULL,
    data_type TEXT NOT NULL DEFAULT 'text',
    data_text TEXT NOT NULL,
    data_metadata TEXT,  -- JSON string
    user_id TEXT DEFAULT 'default',
    agent_id TEXT DEFAULT 'claude-code',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- FTS5 full-text search table
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    data_text,
    content='documents',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

-- FTS5 triggers to keep search index synchronized
CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, data_text)
    VALUES (new.rowid, new.data_text);
END;

CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    DELETE FROM documents_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    UPDATE documents_fts SET data_text = new.data_text WHERE rowid = new.rowid;
END;

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    agent_id TEXT NOT NULL DEFAULT 'claude-code',
    start_time TEXT NOT NULL DEFAULT (datetime('now')),
    end_time TEXT,
    summary TEXT,
    memory_count INTEGER DEFAULT 0,
    metadata TEXT  -- JSON string
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_agent_id ON documents(agent_id);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_data_type ON documents(data_type);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_agent_id ON sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);

-- Backup metadata table
CREATE TABLE IF NOT EXISTS backup_metadata (
    id TEXT PRIMARY KEY,
    backup_type TEXT NOT NULL,  -- 'manual', 'daily', 'weekly', 'monthly'
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    status TEXT DEFAULT 'completed',  -- 'completed', 'failed', 'verifying'
    databases_backed_up TEXT NOT NULL,  -- JSON array: ['postgresql', 'qdrant', 'neo4j', 'redis']
    verification_status TEXT,  -- 'verified', 'failed', 'pending'
    verified_at TEXT
);

-- Scheduled tasks table
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    task_type TEXT NOT NULL,  -- 'cleanup', 'archive', 'optimize', 'deduplicate', 'summarize'
    schedule TEXT NOT NULL,  -- 'daily', 'weekly', 'monthly'
    last_run TEXT,
    next_run TEXT NOT NULL,
    status TEXT DEFAULT 'active',  -- 'active', 'paused', 'disabled'
    last_status TEXT,  -- 'success', 'failed', 'running'
    metadata TEXT  -- JSON string
);

-- Deduplication history table
CREATE TABLE IF NOT EXISTS deduplication_history (
    id TEXT PRIMARY KEY,
    run_at TEXT NOT NULL DEFAULT (datetime('now')),
    memories_merged INTEGER NOT NULL,
    duplicates_found INTEGER NOT NULL,
    status TEXT NOT NULL,  -- 'completed', 'failed', 'dry_run'
    merge_details TEXT  -- JSON string with details of merges
);

-- Summarization history table
CREATE TABLE IF NOT EXISTS summarization_history (
    id TEXT PRIMARY KEY,
    run_at TEXT NOT NULL DEFAULT (datetime('now')),
    memories_summarized INTEGER NOT NULL,
    total_characters INTEGER NOT NULL,
    status TEXT NOT NULL,  -- 'completed', 'failed'
    summary_details TEXT  -- JSON string
);

-- Insert default scheduled tasks
INSERT OR IGNORE INTO scheduled_tasks (id, task_name, task_type, schedule, next_run, status, metadata) VALUES
    ('cleanup-expired', 'Cleanup Expired Memories', 'cleanup', 'daily', datetime('now', '+1 day'), 'active', '{"days": 90}'),
    ('archive-sessions', 'Archive Old Sessions', 'archive', 'weekly', datetime('now', '+7 days'), 'active', '{"days": 365}'),
    ('optimize-indexes', 'Optimize Indexes', 'optimize', 'monthly', datetime('now', '+30 days'), 'active', '{}'),
    ('clear-cache', 'Clear Cache', 'cleanup', 'daily', datetime('now', '+1 day'), 'active', '{}'),
    ('deduplicate', 'Deduplicate Memories', 'deduplicate', 'weekly', datetime('now', '+7 days'), 'active', '{"dry_run_first": true}'),
    ('summarize', 'Summarize Old Memories', 'summarize', 'monthly', datetime('now', '+30 days'), 'active', '{"days": 30, "min_length": 1000}');

-- System info table
CREATE TABLE IF NOT EXISTS system_info (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Insert system info
INSERT OR IGNORE INTO system_info (key, value) VALUES
    ('schema_version', '1.0.0'),
    ('lite_mode_enabled', 'true'),
    ('initial_setup_date', datetime('now'));

-- Views for common queries
CREATE VIEW IF NOT EXISTS v_recent_memories AS
SELECT
    id,
    data_id,
    data_type,
    SUBSTR(data_text, 1, 200) as summary,
    user_id,
    agent_id,
    created_at,
    updated_at
FROM documents
ORDER BY created_at DESC;

CREATE VIEW IF NOT EXISTS v_active_sessions AS
SELECT
    id,
    user_id,
    agent_id,
    start_time,
    memory_count
FROM sessions
WHERE end_time IS NULL
ORDER BY start_time DESC;

CREATE VIEW IF NOT EXISTS v_backup_status AS
SELECT
    backup_type,
    COUNT(*) as total_backups,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    MAX(created_at) as last_backup
FROM backup_metadata
GROUP BY backup_type;
