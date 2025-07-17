-- Fix user ID column type from TEXT to BIGINT for better performance
-- This migration changes users.id from TEXT to BIGINT and updates all foreign key references

BEGIN;

-- Step 1: Create a new temporary table with the correct schema
CREATE TABLE users_new (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_notified TIMESTAMP,
    notification_enabled BOOLEAN DEFAULT TRUE,
    preferred_check_day TEXT DEFAULT 'sunday',
    preferred_check_time TEXT DEFAULT '18:00',
    max_stocks INTEGER DEFAULT 20,
    CONSTRAINT valid_check_day CHECK (
        preferred_check_day IN ('sunday','monday','tuesday','wednesday','thursday','friday','saturday')
    )
);

-- Step 2: Report on users that will be dropped (non-numeric IDs)
DO $$
DECLARE
    dropped_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO dropped_count
    FROM users 
    WHERE NOT (id ~ '^[0-9]+$' AND CAST(id AS BIGINT) BETWEEN -9223372036854775808 AND 9223372036854775807);
    
    IF dropped_count > 0 THEN
        RAISE NOTICE 'WARNING: % user(s) with non-numeric IDs will be dropped during migration', dropped_count;
        
        -- Log the users that will be dropped
        INSERT INTO logs (timestamp, log_type, message, user_id, symbol)
        SELECT 
            NOW(),
            'migration_warning',
            'User with non-numeric ID dropped during BIGINT migration: ' || id || ' (' || name || ')',
            NULL,
            NULL
        FROM users 
        WHERE NOT (id ~ '^[0-9]+$' AND CAST(id AS BIGINT) BETWEEN -9223372036854775808 AND 9223372036854775807);
    END IF;
END $$;

-- Copy data from old table to new table (converting TEXT to BIGINT)
-- Only copy rows where the id can be converted to a valid BIGINT
INSERT INTO users_new (id, name, joined_at, last_notified, notification_enabled, preferred_check_day, preferred_check_time, max_stocks)
SELECT 
    CAST(id AS BIGINT),
    name,
    joined_at,
    last_notified,
    notification_enabled,
    preferred_check_day,
    preferred_check_time,
    max_stocks
FROM users 
WHERE id ~ '^[0-9]+$' AND CAST(id AS BIGINT) BETWEEN -9223372036854775808 AND 9223372036854775807;

-- Step 3: Drop foreign key constraints that reference the old users table
ALTER TABLE watchlist_items DROP CONSTRAINT IF EXISTS watchlist_items_user_id_fkey;
ALTER TABLE alert_history DROP CONSTRAINT IF EXISTS alert_history_user_id_fkey;
ALTER TABLE logs DROP CONSTRAINT IF EXISTS logs_user_id_fkey;

-- Step 4: Create temporary tables for related data with new foreign key types
CREATE TABLE watchlist_items_new (
    user_id BIGINT,
    symbol TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_threshold_low REAL DEFAULT 5.0,
    alert_threshold_high REAL DEFAULT 95.0,
    last_alerted_at TIMESTAMP,
    is_owned BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, symbol),
    CONSTRAINT valid_thresholds CHECK (
        alert_threshold_low > 0 
        AND alert_threshold_high < 100 
        AND alert_threshold_low < alert_threshold_high
    )
);

CREATE TABLE alert_history_new (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    symbol TEXT,
    price REAL,
    percentile REAL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK (status IN ('sent', 'failed')),
    error_message TEXT
);

CREATE TABLE logs_new (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    log_type TEXT NOT NULL,
    message TEXT NOT NULL,
    user_id BIGINT,
    symbol TEXT
);

-- Step 5: Copy data to new tables (only for users that exist in the new users table)
INSERT INTO watchlist_items_new (user_id, symbol, added_at, alert_threshold_low, alert_threshold_high, last_alerted_at, is_owned)
SELECT 
    CAST(w.user_id AS BIGINT),
    w.symbol,
    w.added_at,
    w.alert_threshold_low,
    w.alert_threshold_high,
    w.last_alerted_at,
    COALESCE(w.is_owned, FALSE)
FROM watchlist_items w
WHERE w.user_id ~ '^[0-9]+$' 
  AND CAST(w.user_id AS BIGINT) IN (SELECT id FROM users_new);

INSERT INTO alert_history_new (id, user_id, symbol, price, percentile, sent_at, status, error_message)
SELECT 
    a.id,
    CAST(a.user_id AS BIGINT),
    a.symbol,
    a.price,
    a.percentile,
    a.sent_at,
    a.status,
    a.error_message
FROM alert_history a
WHERE a.user_id ~ '^[0-9]+$' 
  AND CAST(a.user_id AS BIGINT) IN (SELECT id FROM users_new);

INSERT INTO logs_new (id, timestamp, log_type, message, user_id, symbol)
SELECT 
    l.id,
    l.timestamp,
    l.log_type,
    l.message,
    CASE 
        WHEN l.user_id IS NOT NULL AND l.user_id ~ '^[0-9]+$' 
        THEN CAST(l.user_id AS BIGINT)
        ELSE NULL
    END,
    l.symbol
FROM logs l;

-- Step 6: Drop old tables
DROP TABLE IF EXISTS watchlist_items CASCADE;
DROP TABLE IF EXISTS alert_history CASCADE;
DROP TABLE IF EXISTS logs CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Step 7: Rename new tables to original names
ALTER TABLE users_new RENAME TO users;
ALTER TABLE watchlist_items_new RENAME TO watchlist_items;
ALTER TABLE alert_history_new RENAME TO alert_history;
ALTER TABLE logs_new RENAME TO logs;

-- Step 8: Recreate indexes
CREATE INDEX idx_users_notification ON users(notification_enabled, preferred_check_day, preferred_check_time);
CREATE INDEX idx_watchlist_symbol ON watchlist_items(symbol);
CREATE INDEX idx_watchlist_user ON watchlist_items(user_id);
CREATE INDEX idx_alert_user ON alert_history(user_id);
CREATE INDEX idx_alert_symbol ON alert_history(symbol);
CREATE INDEX idx_alert_time ON alert_history(sent_at);
CREATE INDEX idx_logs_type ON logs(log_type);
CREATE INDEX idx_logs_time ON logs(timestamp);

-- Step 9: Recreate foreign key constraints
ALTER TABLE watchlist_items ADD CONSTRAINT watchlist_items_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE alert_history ADD CONSTRAINT alert_history_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE alert_history ADD CONSTRAINT alert_history_watchlist_fkey 
    FOREIGN KEY (user_id, symbol) REFERENCES watchlist_items(user_id, symbol) ON DELETE CASCADE;

ALTER TABLE logs ADD CONSTRAINT logs_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- Step 10: Recreate views with updated schema
DROP VIEW IF EXISTS active_watchlists CASCADE;
DROP VIEW IF EXISTS alert_statistics CASCADE;

CREATE VIEW active_watchlists AS
SELECT 
    w.user_id,
    u.name as user_name,
    w.symbol,
    w.alert_threshold_low,
    w.alert_threshold_high,
    w.last_alerted_at,
    w.is_owned,
    sc.last_price,
    sc.ma_200
FROM watchlist_items w
JOIN users u ON w.user_id = u.id
LEFT JOIN stock_cache sc ON w.symbol = sc.symbol
WHERE u.notification_enabled = TRUE;

CREATE VIEW alert_statistics AS
SELECT 
    user_id,
    symbol,
    COUNT(*) as total_alerts,
    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as successful_alerts,
    MAX(sent_at) as last_alert_time
FROM alert_history
GROUP BY user_id, symbol;

-- Reset the alert_history sequence to continue from the max ID (only if sequence exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'alert_history_id_seq') THEN
        PERFORM setval('alert_history_id_seq', COALESCE((SELECT MAX(id) FROM alert_history), 1));
    END IF;
END $$;

-- Reset the logs sequence to continue from the max ID (only if sequence exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'logs_id_seq') THEN
        PERFORM setval('logs_id_seq', COALESCE((SELECT MAX(id) FROM logs), 1));
    END IF;
END $$;

COMMIT;