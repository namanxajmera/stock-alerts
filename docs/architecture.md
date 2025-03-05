# Stock Analytics Dashboard - Architecture

## System Overview

A lightweight client-server application with:
- **Frontend**: Vanilla JavaScript, HTML, CSS with Plotly.js for charts
- **Backend**: Python Flask server with yfinance package
- **Data Source**: Yahoo Finance API
- **Storage**: SQLite database with robust schema design
- **Alerts**: Telegram Bot API for notifications

## Data Flow
```
User → Browser → Flask Server → Yahoo Finance API
                     ↓
Yahoo Finance → Data Processing → JSON → Browser → Charts
                     ↓
SQLite Database ← → Weekly Checker → Telegram Bot
```

## Key Design Decisions

1. **Lightweight Architecture**: Simple Flask server with SQLite database for easy deployment
2. **Server-side Processing**: All calculations done on server for consistency
3. **Single-page Application**: Smoother user experience with no page reloads
4. **Flexible Alert System**: Per-user and per-stock threshold configuration
5. **Customizable Scheduling**: User-defined check days and times
6. **Robust Data Storage**: SQLite with foreign key constraints and transactions

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
  │   └── stockalerts.db     # SQLite database file
  ├── app.py                 # Flask application entry point
  ├── db_manager.py          # Database access layer
  ├── stock_analyzer.py      # Stock data analysis
  ├── bot_handler.py         # Telegram bot handler
  ├── weekly_checker.py      # Weekly alert system
  ├── migrations/            # Database migration scripts
  │   ├── 001_initial.sql
  │   └── 002_add_indexes.sql
  └── static/               # Frontend assets
      ├── css/
      ├── js/
      └── ts/
```

## Database Management

### Backup Strategy
```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
sqlite3 stockalerts.db ".backup 'backup/stockalerts_${DATE}.db'"
find backup/ -name "stockalerts_*.db" -mtime +7 -delete
```

### Maintenance Tasks
1. Regular vacuum to reclaim space
2. Index rebuilding for performance
3. Cache invalidation for old stock data
4. Log rotation for size management

### Schema Migration Strategy
- Use a simple, linear versioning scheme (e.g. 001, 002, etc.)
- Each version has an associated SQL script in the `migrations` directory 
- Scripts are applied in order when setting up a new environment or upgrading an existing one
- Scripts should be idempotent and able to run multiple times without error
- Use transactions to ensure scripts run completely or not at all 
- Avoid modifying existing migration scripts, create a new version instead

## Security & Infrastructure

### Data Security
- SQLite file permissions set to 600
- All SQL queries use parameterized statements
- Input validation before database operations
- Regular backups with encryption
- Transaction isolation for concurrent access

### Deployment Options
- Any Python-compatible web server
- Container-friendly (Docker)
- Low resource requirements
- Automatic database migrations
- Monitoring and alerting setup

## Service Dependencies
- Telegram Bot API: Alert delivery
- Yahoo Finance: Stock data (rate limited)
- SQLite: Data storage

## Performance Considerations
1. Indexed queries for common operations
2. Connection pooling for concurrent access
3. Prepared statements for repeated queries
4. Regular VACUUM ANALYZE for optimization
5. Cache invalidation strategy
6. Query optimization using EXPLAIN QUERY PLAN