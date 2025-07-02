# Stock Analytics Dashboard - Architecture

## System Overview

A lightweight client-server application with:
- **Frontend**: Vanilla TypeScript, HTML, CSS with Plotly.js for charts
- **Backend**: Python Flask server with yfinance package
- **Data Source**: Yahoo Finance API
- **Storage**: SQLite database with robust schema design
- **Alerts**: Secure Telegram Bot API integration for notifications

## Data Flow
```
User → Browser → Flask Server → Yahoo Finance API
                     ↓
Yahoo Finance → Data Processing → JSON → Browser → Charts
                     ↓
        (DB Read/Write)
                     ↓
SQLite Database ← → Periodic Checker Script → Telegram API → User Alert
```

## Key Design Decisions

1. **Lightweight Architecture**: Simple Flask server with a single SQLite database file for easy deployment and portability.
2. **Server-side Processing**: All financial calculations are performed on the server to ensure consistency and keep the frontend light.
3. **Single-page Application**: Provides a smooth user experience with dynamic chart updates and no page reloads.
4. **Secure Webhook**: Telegram webhook is validated using a secret token to prevent unauthorized access.
5. **Efficient Alert System**: The periodic checker script fetches data once per unique stock symbol, regardless of how many users are watching it.
6. **Robust Data Storage**: SQLite is configured with foreign key constraints and accessed via a manager that ensures transactional integrity.

## Database Architecture

### Core Tables

#### 1. Users Table
```sql
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
```

#### 2. Watchlist Items Table
```sql
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

-- Indexes for common queries
CREATE INDEX idx_watchlist_symbol ON watchlist_items(symbol);
CREATE INDEX idx_watchlist_user ON watchlist_items(user_id);
```

### Data Storage Tables

#### 3. Stock Cache Table
```sql
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
```

#### 4. Alert History Table
```sql
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
```

### Configuration and Logging

#### 5. Configuration Table
```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    validation_regex TEXT,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by TEXT
);

-- Default configuration
INSERT INTO config (key, value, description) VALUES
    ('telegram_token', 'your_bot_token', 'Telegram Bot API Token'),
    ('cache_duration_hours', '24', 'How long to cache stock data'),
    ('max_stocks_per_user', '20', 'Maximum stocks per user watchlist'),
    ('default_threshold_low', '5.0', 'Default lower percentile threshold'),
    ('default_threshold_high', '95.0', 'Default upper percentile threshold');
```

#### 6. Logs Table
```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    log_type TEXT NOT NULL,
    message TEXT NOT NULL,
    user_id TEXT,
    symbol TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Index for log queries
CREATE INDEX idx_logs_type ON logs(log_type);
CREATE INDEX idx_logs_time ON logs(timestamp);
```

### Database Views

#### Active Watchlists View
```sql
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
```

#### Alert Statistics View
```sql
CREATE VIEW alert_statistics AS
SELECT 
    user_id,
    symbol,
    COUNT(*) as total_alerts,
    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as successful_alerts,
    MAX(sent_at) as last_alert_time
FROM alert_history
GROUP BY user_id, symbol;
```

## File Structure
```
project/
  ├── db/
  │   └── stockalerts.db     # SQLite database file (auto-created)
  ├── app.py                 # Flask application entry point and API
  ├── db_manager.py          # Database access and management layer
  ├── webhook_handler.py     # Securely handles incoming Telegram updates
  ├── periodic_checker.py    # Script for stock analysis and sending alerts
  ├── migrations/            # Database migration scripts
  │   └── 001_initial.sql
  └── static/                # Frontend assets
      ├── css/
      ├── ts/                # TypeScript source files
      └── js/                # Compiled JavaScript files
```

## Database Management

### Backup Strategy
A simple cron job can be used to back up the SQLite database file daily.
```bash
# Example daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
sqlite3 /path/to/project/db/stockalerts.db ".backup '/path/to/backups/stockalerts_${DATE}.db'"
# Prune old backups
find /path/to/backups/ -name "stockalerts_*.db" -mtime +7 -delete
```

### Schema Migration Strategy
- A simple, linear versioning scheme (e.g., 001, 002, etc.) is used.
- SQL scripts are located in the `migrations` directory.
- The `db_manager.py` automatically applies new, unapplied migrations on startup.
- Scripts are idempotent where possible and run within transactions to ensure atomicity.

## Security & Infrastructure

### Data Security
- **Webhook Security**: `X-Telegram-Bot-Api-Secret-Token` header is used to validate all incoming webhook calls.
- **SQL Injection**: All database queries are parameterized.
- **File Permissions**: The `db/` directory and database file should have restricted permissions on a production server.

### Deployment
- The application is a standard WSGI app and can be deployed with Gunicorn, uWSGI, etc.
- The `periodic_checker.py` script should be run by a scheduler like cron.
- A public-facing URL is required for the Telegram webhook to function.

## Service Dependencies
- **Telegram Bot API**: Required for alert delivery and user interaction.
- **Yahoo Finance**: The primary source for stock data (subject to rate limiting).

## Performance Considerations
1. Indexed queries for common operations
2. Connection pooling for concurrent access
3. Prepared statements for repeated queries
4. Regular VACUUM ANALYZE for optimization
5. Cache invalidation strategy
6. Query optimization using EXPLAIN QUERY PLAN