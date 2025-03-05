# Stock Analytics Dashboard - API Documentation

## Overview

- Base URL: `http://localhost:5001` (local development)
- No authentication required
- Telegram bot for user interactions and alerts
- CORS enabled for cross-origin requests
- File-based storage using YAML

## Endpoints

### 1. Main Page
```
GET /
```
Returns the main web application HTML page for stock visualization

### 2. Stock Data
```
GET /data/<ticker>/<period>
```
Retrieves stock data and analysis for a ticker symbol and specified time period

**Parameters**:
- ticker: Stock symbol (e.g., AAPL)
- period: Time period (valid values: 1y, 3y, 5y, max)

**Response Format**:
```json
{
  "dates": ["2022-01-01", "2022-01-02", ...],
  "prices": [172.34, 173.45, ...],
  "ma_200": [168.23, 168.34, ...],
  "pct_diff": [2.45, 3.04, ...],
  "percentiles": {
    "p5": -10.2,
    "p95": 12.5
  }
}
```

### 3. Telegram Webhook
```
POST /webhook
```
Webhook endpoint for Telegram bot updates. This endpoint handles all user interactions.

**Request Body**: Telegram Update object
**Response**: Empty 200 OK

## Bot Commands

### Available Commands
- `/start` - Initialize bot and show help message
- `/add <ticker>` - Add stock to your watchlist
- `/remove <ticker>` - Remove stock from your watchlist
- `/list` - Show your current watchlist

## Configuration Files

### 1. User Watchlists
```yaml
# config/watchlists/<telegram_id>.yaml
name: "John Doe"
stocks:
  - AAPL
  - GOOGL
last_notified: "2024-03-10"
```

### 2. Stock Cache
```yaml
# config/cache/stocks.yaml
AAPL:
  last_check: "2024-03-10"
  price_history:
    - date: "2024-03-10"
      price: 175.34
      percentile: 95.2
  ma_200: 168.45
```

### 3. Bot Configuration
```yaml
# config/bot.yaml
telegram_token: "your_bot_token"
check_day: "sunday"
check_time: "18:00"
percentile_thresholds:
  low: 5
  high: 95
```

## Error Responses

```json
{ "error": "Invalid period. Must be one of: 1y, 3y, 5y, max", "code": 400 }
{ "error": "No data available for ticker", "code": 404 }
{ "error": "Failed to process data: [error details]", "code": 500 }
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
- Weekly alerts run every Sunday at 18:00 UTC

**File Storage**:
- All configuration in YAML files
- User watchlists stored in individual files
- Stock data cached to minimize API calls
- System logs track all operations

**Future Endpoints**:
- `/data/<ticker>/indicators` - Additional technical indicators
- `/compare/<tickers>` - Multi-stock comparison
- `/search/<query>` - Ticker symbol search