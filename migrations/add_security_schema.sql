-- Enhanced Cognee - Security Schema Migration
--
-- This migration adds tables for JWT authentication, API keys, RBAC, and security audit.
--
-- Author: Enhanced Cognee Team
-- Version: 1.0.0
-- Date: 2026-02-06

-- Create users table
CREATE TABLE IF NOT EXISTS shared_memory.users (
    user_id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- bcrypt hash
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE shared_memory.users IS 'User accounts for authentication and authorization';
COMMENT ON COLUMN shared_memory.users.role IS 'User role for RBAC (admin, user, readonly, api_client)';

-- Create API keys table
CREATE TABLE IF NOT EXISTS shared_memory.api_keys (
    id SERIAL PRIMARY KEY,
    key_id VARCHAR(64) UNIQUE NOT NULL,
    key_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 hash
    user_id VARCHAR(255) NOT NULL REFERENCES shared_memory.users(user_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'api_client',
    scopes JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used TIMESTAMP,
    revoked_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE shared_memory.api_keys IS 'API keys for authentication';
COMMENT ON COLUMN shared_memory.api_keys.key_hash IS 'SHA256 hash of the API key for secure storage';

-- Create user permissions table (for granular permissions beyond roles)
CREATE TABLE IF NOT EXISTS shared_memory.user_permissions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES shared_memory.users(user_id) ON DELETE CASCADE,
    permission VARCHAR(100) NOT NULL,
    granted_by VARCHAR(255) REFERENCES shared_memory.users(user_id),
    granted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, permission)
);

COMMENT ON TABLE shared_memory.user_permissions IS 'Granular permissions beyond role-based access';

-- Create security audit log table
CREATE TABLE IF NOT EXISTS shared_memory.security_audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(255),
    api_key_id VARCHAR(64),
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    success BOOLEAN NOT NULL,
    failure_reason TEXT,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE shared_memory.security_audit_log IS 'Audit log for security events';

-- Create indexes
CREATE INDEX idx_users_username ON shared_memory.users(username);
CREATE INDEX idx_users_email ON shared_memory.users(email);
CREATE INDEX idx_users_role ON shared_memory.users(role);
CREATE INDEX idx_api_keys_user_id ON shared_memory.api_keys(user_id);
CREATE INDEX idx_api_keys_key_id ON shared_memory.api_keys(key_id);
CREATE INDEX idx_api_keys_is_active ON shared_memory.api_keys(is_active);
CREATE INDEX idx_user_permissions_user_id ON shared_memory.user_permissions(user_id);
CREATE INDEX idx_security_audit_log_user_id ON shared_memory.security_audit_log(user_id);
CREATE INDEX idx_security_audit_log_timestamp ON shared_memory.security_audit_log(timestamp DESC);
CREATE INDEX idx_security_audit_log_event_type ON shared_memory.security_audit_log(event_type);

-- Create views
CREATE OR REPLACE VIEW shared_memory.active_api_keys AS
SELECT
    ak.key_id,
    ak.name,
    u.username,
    u.email,
    ak.role,
    ak.scopes,
    ak.created_at,
    ak.last_used,
    ak.expires_at
FROM shared_memory.api_keys ak
JOIN shared_memory.users u ON u.user_id = ak.user_id
WHERE ak.is_active = true
  AND (ak.expires_at IS NULL OR ak.expires_at > NOW());

COMMENT ON VIEW shared_memory.active_api_keys IS 'Currently active API keys with user info';

CREATE OR REPLACE VIEW shared_memory.user_permissions_view AS
SELECT
    u.user_id,
    u.username,
    u.role AS base_role,
    jsonb_agg(
        jsonb_build_object(
            'permission', up.permission,
            'granted_by', up.granted_by,
            'granted_at', up.granted_at
        )
    ) AS additional_permissions
FROM shared_memory.users u
LEFT JOIN shared_memory.user_permissions up ON up.user_id = u.user_id
GROUP BY u.user_id, u.username, u.role;

COMMENT ON VIEW shared_memory.user_permissions_view IS 'Users with their roles and additional permissions';

-- Function to create user
CREATE OR REPLACE FUNCTION shared_memory.create_user(
    p_username VARCHAR,
    p_email VARCHAR,
    p_password_hash VARCHAR,
    p_role VARCHAR DEFAULT 'user',
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS VARCHAR AS $$
DECLARE
    v_user_id VARCHAR;
BEGIN
    -- Generate user ID
    v_user_id := 'user_' || encode(gen_random_bytes(16), 'hex');

    -- Insert user
    INSERT INTO shared_memory.users (user_id, username, email, password_hash, role, metadata)
    VALUES (v_user_id, p_username, p_email, p_password_hash, p_role, p_metadata);

    RETURN v_user_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.create_user IS 'Create a new user account';

-- Function to log security event
CREATE OR REPLACE FUNCTION shared_memory.log_security_event(
    p_event_type VARCHAR,
    p_user_id VARCHAR DEFAULT NULL,
    p_api_key_id VARCHAR DEFAULT NULL,
    p_action VARCHAR,
    p_resource_type VARCHAR DEFAULT NULL,
    p_resource_id VARCHAR DEFAULT NULL,
    p_success BOOLEAN,
    p_failure_reason VARCHAR DEFAULT NULL,
    p_ip_address INET DEFAULT NULL,
    p_user_agent VARCHAR DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS INTEGER AS $$
DECLARE
    v_log_id INTEGER;
BEGIN
    INSERT INTO shared_memory.security_audit_log (
        event_type, user_id, api_key_id, action, resource_type, resource_id,
        success, failure_reason, ip_address, user_agent, metadata
    ) VALUES (
        p_event_type, p_user_id, p_api_key_id, p_action, p_resource_type, p_resource_id,
        p_success, p_failure_reason, p_ip_address, p_user_agent, p_metadata
    )
    RETURNING id INTO v_log_id;

    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION shared_memory.log_security_event IS 'Log a security event to the audit log';

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION shared_memory.update_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at_trigger ON shared_memory.users;
CREATE TRIGGER users_updated_at_trigger
    BEFORE UPDATE ON shared_memory.users
    FOR EACH ROW
    EXECUTE FUNCTION shared_memory.update_users_updated_at();

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON shared_memory.users TO your_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON shared_memory.api_keys TO your_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON shared_memory.user_permissions TO your_user;
-- GRANT SELECT ON shared_memory.security_audit_log TO your_user;
-- GRANT SELECT ON shared_memory.active_api_keys TO your_user;
-- GRANT SELECT ON shared_memory.user_permissions_view TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.create_user TO your_user;
-- GRANT EXECUTE ON FUNCTION shared_memory.log_security_event TO your_user;
