-- Initial database schema

-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
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

-- Index for notification scheduling
CREATE INDEX idx_users_notification ON users(notification_enabled, preferred_check_day, preferred_check_time);

-- Watchlist items table
CREATE TABLE watchlist_items (
    user_id TEXT,
    symbol TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_threshold_low REAL DEFAULT 5.0,
    alert_threshold_high REAL DEFAULT 95.0,
    last_alerted_at TIMESTAMP,
    PRIMARY KEY (user_id, symbol),
    FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT valid_thresholds CHECK (
        alert_threshold_low > 0 
        AND alert_threshold_high < 100 
        AND alert_threshold_low < alert_threshold_high
    )
);

-- Indexes for watchlist queries
CREATE INDEX idx_watchlist_symbol ON watchlist_items(symbol);
CREATE INDEX idx_watchlist_user ON watchlist_items(user_id);

-- Stock cache table
CREATE TABLE stock_cache (
    symbol TEXT PRIMARY KEY,
    last_check TIMESTAMP NOT NULL,
    ma_200 REAL,
    last_price REAL,
    data_json TEXT,
    CONSTRAINT valid_price CHECK (last_price > 0)
);

-- Index for cache invalidation
CREATE INDEX idx_cache_check ON stock_cache(last_check);

-- Alert history table
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    symbol TEXT,
    price REAL,
    percentile REAL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK (status IN ('sent', 'failed')),
    error_message TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (user_id, symbol) REFERENCES watchlist_items(user_id, symbol)
);

-- Indexes for alert history queries
CREATE INDEX idx_alert_user ON alert_history(user_id);
CREATE INDEX idx_alert_symbol ON alert_history(symbol);
CREATE INDEX idx_alert_time ON alert_history(sent_at);

-- Configuration table
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    validation_regex TEXT,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by TEXT
);

-- Default configuration values
INSERT INTO config (key, value, description) VALUES
    ('telegram_token', 'your_bot_token', 'Telegram Bot API Token'),
    ('cache_duration_hours', '24', 'How long to cache stock data'),
    ('max_stocks_per_user', '20', 'Maximum stocks per user watchlist'),
    ('default_threshold_low', '5.0', 'Default lower percentile threshold'),
    ('default_threshold_high', '95.0', 'Default upper percentile threshold');

-- Logs table
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    log_type TEXT NOT NULL,
    message TEXT NOT NULL,
    user_id TEXT,
    symbol TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for log queries
CREATE INDEX idx_logs_type ON logs(log_type);
CREATE INDEX idx_logs_time ON logs(timestamp);

-- Views
CREATE VIEW active_watchlists AS
SELECT 
    w.user_id,
    u.name as user_name,
    w.symbol,
    w.alert_threshold_low,
    w.alert_threshold_high,
    w.last_alerted_at,
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