-- Database initialization script for SentinelMonitorIA
-- Run on PostgreSQL container startup

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create additional roles if needed
-- Note: The main user is created by Docker environment variables

-- Set search path
SET search_path TO public;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'SentinelMonitorIA database initialization started';
END $$;