# Watchlist Feature Documentation

## Overview
The watchlist system allows users to track stocks and receive alerts when they hit significant price thresholds. Each user has their own watchlist stored in the SQLite database. The system checks these stocks based on the user's preferred schedule, sending Telegram alerts when notable movements are detected.

## Database Schema

### 1. Watchlist Items Table
```sql
CREATE TABLE watchlist_items (
    user_id TEXT,
    symbol TEXT,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    alert_threshold_low REAL DEFAULT 16.0,
    alert_threshold_high REAL DEFAULT 84.0,
    last_alerted_at TEXT,
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

### 2. Users Table
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_notified TEXT,
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

### 3. Alert History Table
```sql
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    symbol TEXT,
    price REAL,
    percentile REAL,
    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
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

## Working with Dates in SQLite

SQLite stores dates as TEXT in ISO8601 format. The following built-in functions are available for date manipulation:

### Date Functions
- `datetime()`: Current date and time in UTC
- `date()`: Current date only
- `strftime()`: Format dates for display or comparison

### Common Date Queries
```sql
-- Get alerts from last 7 days
SELECT * FROM alert_history 
WHERE datetime(sent_at) >= datetime('now', '-7 days');

-- Format date for display
SELECT strftime('%Y-%m-%d %H:%M', sent_at) as formatted_date 
FROM alert_history;

-- Group by date
SELECT date(sent_at) as alert_date, COUNT(*) as alert_count 
FROM alert_history 
GROUP BY date(sent_at);
```

### Best Practices
- Store dates in UTC using TEXT type
- Use ISO8601 format: YYYY-MM-DD HH:MM:SS
- Use SQLite date functions for comparisons
- Consider timezone handling in application code

## Components

### 1. Database Manager
The `DatabaseManager` class handles all interactions with the SQLite database. It provides methods for:
- Initializing the database schema
- Adding and removing users
- Managing watchlist items per user
- Updating the stock cache
- Logging events and errors

See the `db_manager.py` file for the full implementation.

### 2. Telegram Bot Service
The `AlertBot` class integrates with the Telegram Bot API to handle user interactions and send alerts. Key functionality includes:
- Loading the bot configuration from the database
- Sending alert messages to users
- Handling incoming commands (/start, /add, /remove, /list)
- Logging successes and errors to the database

See the `bot_handler.py` file for the full implementation.

### 3. Periodic Checker
The `check_all_watchlists` function runs periodically to analyze stock data and send alerts to users. The process involves:
1. Querying the database for users and their watchlist items
2. Checking the stock cache for recent data, fetching from Yahoo Finance if needed
3. Comparing stock metrics against user-defined thresholds
4. Sending alerts via the Telegram bot for significant movements
5. Updating the user's last notification time and alert history

See the `weekly_checker.py` file for the full implementation.

## Bot Commands

The Telegram bot supports the following commands:
- `/start` - Initialize the bot and show the help message
- `/add <symbol>` - Add a stock to the user's watchlist
- `/remove <symbol>` - Remove a stock from the user's watchlist
- `/list` - Show the user's current watchlist
- `/settings` - View and update alert preferences
- `/thresholds <symbol> <low> <high>` - Set custom alert thresholds for a stock

The command handlers interact with the `DatabaseManager` to update the user's watchlist and preferences in the database.

## Error Handling
The SQLite database provides several features for error handling and data integrity:
- Foreign key constraints to ensure data consistency
- Unique constraints to prevent duplicate entries
- Check constraints to validate data before insertion
- Transactions to ensure atomic operations
- Parameterized queries to prevent SQL injection

The `DatabaseManager` and `AlertBot` classes catch and log any errors that occur during database operations or Telegram interactions. The logs are stored in the `logs` table for debugging and monitoring purposes.

## Future Improvements
- Add support for multiple watchlists per user
- Implement a web interface for managing watchlists and preferences
- Integrate with additional data sources beyond Yahoo Finance
- Support more granular alert frequencies (daily, hourly)
- Provide portfolio tracking and performance analysis
- Offer machine learning-based stock recommendations
- Integrate with brokerages for automated trading