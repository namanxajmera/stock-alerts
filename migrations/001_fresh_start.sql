-- Fresh start - clean simple schema
-- Drop everything and start over

-- Drop all tables if they exist
DROP TABLE IF EXISTS alert_history CASCADE;
DROP TABLE IF EXISTS watchlist_items CASCADE; 
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS stock_cache CASCADE;
DROP TABLE IF EXISTS trading_stats_cache CASCADE;
DROP TABLE IF EXISTS api_requests CASCADE;
DROP TABLE IF EXISTS user_requests CASCADE;
DROP TABLE IF EXISTS logs CASCADE;
DROP TABLE IF EXISTS config CASCADE;
DROP TABLE IF EXISTS migrations CASCADE;

-- Drop sequences if they exist
DROP SEQUENCE IF EXISTS alert_history_id_seq CASCADE;
DROP SEQUENCE IF EXISTS logs_id_seq CASCADE;

-- Create migrations table first
CREATE TABLE migrations (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE users (
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

-- Watchlist items
CREATE TABLE watchlist_items (
    user_id BIGINT,
    symbol TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_threshold_low REAL DEFAULT 5.0,
    alert_threshold_high REAL DEFAULT 95.0,
    last_alerted_at TIMESTAMP,
    is_owned BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, symbol),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT valid_thresholds CHECK (
        alert_threshold_low > 0 
        AND alert_threshold_high < 100 
        AND alert_threshold_low < alert_threshold_high
    )
);

-- Alert history
CREATE TABLE alert_history (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    symbol TEXT,
    price REAL,
    percentile REAL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK (status IN ('sent', 'failed')),
    error_message TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Stock cache
CREATE TABLE stock_cache (
    symbol TEXT PRIMARY KEY,
    last_price REAL,
    ma_200 REAL,
    data_json TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trading stats cache
CREATE TABLE trading_stats_cache (
    symbol TEXT,
    period TEXT,
    stats_json TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, period)
);

-- API request tracking
CREATE TABLE api_requests (
    id SERIAL PRIMARY KEY,
    api_name TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE
);

-- User request tracking  
CREATE TABLE user_requests (
    id SERIAL PRIMARY KEY,
    user_identifier TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Logs
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    log_type TEXT NOT NULL,
    message TEXT NOT NULL,
    user_id BIGINT,
    symbol TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Config
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_users_notification ON users(notification_enabled, preferred_check_day, preferred_check_time);
CREATE INDEX idx_watchlist_symbol ON watchlist_items(symbol);
CREATE INDEX idx_watchlist_user ON watchlist_items(user_id);
CREATE INDEX idx_alert_user ON alert_history(user_id);
CREATE INDEX idx_alert_symbol ON alert_history(symbol);
CREATE INDEX idx_alert_time ON alert_history(sent_at);
CREATE INDEX idx_logs_type ON logs(log_type);
CREATE INDEX idx_logs_time ON logs(timestamp);
CREATE INDEX idx_api_requests_name_time ON api_requests(api_name, timestamp);
CREATE INDEX idx_user_requests_user_time ON user_requests(user_identifier, timestamp);

-- Create views
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