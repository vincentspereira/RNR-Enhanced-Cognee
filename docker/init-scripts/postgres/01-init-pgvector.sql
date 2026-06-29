-- RNR Enhanced Cognee PostgreSQL Initialization
-- Initialize pgVector extension and create necessary schemas

-- Enable pgVector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schemas for different memory categories
CREATE SCHEMA IF NOT EXISTS ats_memory;
CREATE SCHEMA IF NOT EXISTS oma_memory;
CREATE SCHEMA IF NOT EXISTS smc_memory;
CREATE SCHEMA IF NOT EXISTS shared_memory;

-- Create indexes for better performance on memory operations
-- These will be populated by Cognee as needed

-- Grant permissions to the cognee user
GRANT ALL PRIVILEGES ON SCHEMA ats_memory TO cognee_user;
GRANT ALL PRIVILEGES ON SCHEMA oma_memory TO cognee_user;
GRANT ALL PRIVILEGES ON SCHEMA smc_memory TO cognee_user;
GRANT ALL PRIVILEGES ON SCHEMA shared_memory TO cognee_user;

-- Set default permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA ats_memory GRANT ALL ON TABLES TO cognee_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA oma_memory GRANT ALL ON TABLES TO cognee_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA smc_memory GRANT ALL ON TABLES TO cognee_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA shared_memory GRANT ALL ON TABLES TO cognee_user;

-- Create initial configuration table for RNR Enhanced Cognee
CREATE TABLE IF NOT EXISTS shared_memory.cognee_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for configuration lookups
CREATE INDEX IF NOT EXISTS idx_cognee_config_key ON shared_memory.cognee_config(key);

-- Insert default configuration
INSERT INTO shared_memory.cognee_config (key, value) VALUES
    ('enhanced_mode', 'true'),
    ('memory_categorization', 'true'),
    ('vector_dimensions', '2560'),
    ('version', '0.3.9-enhanced')
ON CONFLICT (key) DO NOTHING;

-- Log initialization completion
DO $$
BEGIN
    RAISE NOTICE 'RNR Enhanced Cognee PostgreSQL initialization completed successfully';
    RAISE NOTICE 'pgVector extension enabled';
    RAISE NOTICE 'Memory schemas created: ats_memory, oma_memory, smc_memory, shared_memory';
END $$;