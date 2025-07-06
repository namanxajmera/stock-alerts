-- Migration: Add rate limiting tables
-- Description: Create tables to track API requests and user requests for rate limiting

-- Table for tracking API requests (like Tiingo API calls)
CREATE TABLE IF NOT EXISTS api_requests (
    id SERIAL PRIMARY KEY,
    api_name VARCHAR(50) NOT NULL,
    request_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    success BOOLEAN DEFAULT TRUE
);

-- Index for efficient time-based queries
CREATE INDEX IF NOT EXISTS idx_api_requests_name_time ON api_requests(api_name, request_time);

-- Table for tracking user requests to prevent abuse
CREATE TABLE IF NOT EXISTS user_requests (
    id SERIAL PRIMARY KEY,
    user_identifier VARCHAR(255) NOT NULL, -- IP address or user ID
    endpoint VARCHAR(255) NOT NULL,
    request_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient user-based queries
CREATE INDEX IF NOT EXISTS idx_user_requests_user_time ON user_requests(user_identifier, request_time);

-- Cleanup old records periodically (keep only last 30 days)
-- This can be run as a periodic cleanup job
-- DELETE FROM api_requests WHERE request_time < NOW() - INTERVAL '30 days';
-- DELETE FROM user_requests WHERE request_time < NOW() - INTERVAL '30 days';