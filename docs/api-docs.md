# Stock Analytics Dashboard - API Documentation

## Overview

- **Base URL**: `http://localhost:5001` (local development)
- **Authentication**: Endpoints are public, but the webhook is secured.
- **Data Format**: JSON
- Telegram bot for user interactions and alerts
- CORS enabled for cross-origin requests
- SQLite database for data storage with robust schema design

## Endpoints

### 1. Main Page
- **`GET /`**
- **Description**: Returns the main single-page web application.
- **Response**: `text/html`

### 2. Stock Data
- **`GET /data/<ticker>/<period>`**
- **Description**: Retrieves processed stock data and technical analysis for a given stock symbol and time period.
- **URL Parameters**:
  - `ticker` (string): The stock symbol (e.g., `AAPL`).
  - `period` (string): The time period. Valid values: `1y`, `3y`, `5y`, `max`.
- **Success Response (200 OK)**:
```json
{
  "dates": ["2022-01-01", "2022-01-02", ...],
  "prices": [172.34, 173.45, ...],
  "ma_200": [168.23, 168.34, ...],
  "pct_diff": [2.45, 3.04, ...],
  "percentiles": {
    "p5": -10.2,
    "p95": 12.5
  },
  "previous_close": 172.00
}
```
- **Error Responses**:
  - `400 Bad Request`: If the period is invalid.
  - `404 Not Found`: If the ticker symbol returns no data.
  - `500 Internal Server Error`: If an error occurs during data processing.

### 3. Telegram Webhook
- **`POST /webhook`**
- **Description**: The secure endpoint for receiving updates from the Telegram Bot API. This endpoint handles all user interactions with the bot.
- **Headers**:
  - `X-Telegram-Bot-Api-Secret-Token` (string, **required**): A secret token that must match the one configured on the server. Requests without this header or with an invalid token will be rejected with a `403 Forbidden` error.
- **Request Body**: A standard Telegram `Update` object.
- **Success Response**: An empty `200 OK`.

## Bot Commands

Users interact with the service via the Telegram bot.

- `/start` - Initializes the bot and shows the welcome message.
- `/add <TICKER> [TICKER...]` - Adds one or more stocks to the user's watchlist.
- `/remove <TICKER> [TICKER...]` - Removes one or more stocks from the watchlist.
- `/list` - Shows the user's current watchlist.

## Database Schema

### 1. Users Table
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
```

### 2. Watchlist Items Table
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
```

### 3. Stock Cache Table
```sql
CREATE TABLE stock_cache (
    symbol TEXT PRIMARY KEY,
    last_check TIMESTAMP NOT NULL,
    ma_200 REAL,
    last_price REAL,
    volume INTEGER,
    market_cap REAL,
    data_json TEXT,
    CONSTRAINT valid_price CHECK (last_price > 0)
);
```

### 4. Alert History Table
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
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id, symbol) REFERENCES watchlist_items(user_id, symbol) ON DELETE CASCADE
);
```

### 5. Configuration Table
```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    validation_regex TEXT,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by TEXT
);
```

### 6. Logs Table
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
```

## Common Database Views

### Active Watchlists View
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

### Alert Statistics View
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

## Error Responses

```json
{ "error": "Invalid period. Must be one of: 1y, 3y, 5y, max", "code": 400 }
{ "error": "No data available for ticker", "code": 404 }
{ "error": "Failed to process data: [error details]", "code": 500 }
{ "error": "User watchlist limit reached", "code": 403 }
```

## Implementation Notes

**Processing Steps**:
1. Validate inputs (ticker/period)
2. Check cache for recent data
3. Fetch from Yahoo Finance if needed
4. Process data and calculate metrics
5. Return JSON response

**Data Limitations**:
- First 200 days will have null MA values
- Historical data limited by Yahoo Finance availability
- NaN and Infinity values are converted to null
- Stock data cached for 24 hours
- Weekly alerts run based on user preferences
- Maximum 20 stocks per user watchlist

**Database Storage**:
- Single SQLite file for all data storage
- Foreign key constraints ensure data integrity
- Transaction support for atomic operations
- Automatic timestamp management
- Custom threshold support per stock
- Comprehensive logging and alert history

**Future Endpoints**:
- `/data/<ticker>/indicators` - Additional technical indicators
- `/compare/<tickers>` - Multi-stock comparison
- `/search/<query>` - Ticker symbol search
- `/stats` - User-specific alert statistics
- `/preferences` - User preference management