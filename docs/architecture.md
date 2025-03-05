# Stock Analytics Dashboard - Architecture

## System Overview

A lightweight client-server application with:
- **Frontend**: Vanilla JavaScript, HTML, CSS with Plotly.js for charts
- **Backend**: Python Flask server with yfinance package
- **Data Source**: Yahoo Finance API
- **Config**: YAML files for configuration and data storage
- **Alerts**: Telegram Bot API for notifications

## Data Flow
```
User → Browser → Flask Server → Yahoo Finance API
                     ↓
Yahoo Finance → Data Processing → JSON → Browser → Charts
                     ↓
Config Files ← → Weekly Checker → Telegram Bot
```

## Key Design Decisions

1. **Lightweight Architecture**: No complex frameworks or databases; easier to maintain and deploy
2. **Server-side Processing**: All calculations done on server for consistency and client simplicity
3. **Single-page Application**: Smoother user experience with no page reloads
4. **Simple Alert System**: 5th/95th percentile thresholds only
5. **Weekly Checking**: Sunday analysis for significant stock movements

## Data Storage

All data is stored in YAML files, organized by purpose:

### 1. User Watchlists
```yaml
# config/watchlists/<telegram_id>.yaml
# Example: config/watchlists/123456789.yaml
name: "John Doe"  # User's Telegram name
stocks:
  - AAPL
  - GOOGL
  - MSFT
last_notified: "2024-03-10"  # Track last notification time
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
GOOGL:
  last_check: "2024-03-10"
  price_history:
    - date: "2024-03-10"
      price: 142.56
      percentile: 45.7
  ma_200: 138.92
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

### 4. System Logs
```yaml
# config/logs.yaml
last_run: "2024-03-10T18:00:00Z"
errors:
  - timestamp: "2024-03-10T18:01:23Z"
    error: "Failed to fetch AAPL data"
    user_id: "123456789"
successes:
  - timestamp: "2024-03-10T18:00:05Z"
    stock: "GOOGL"
    users_notified: 3
```

## File Structure
```
config/
  ├── bot.yaml           # Bot configuration
  ├── logs.yaml          # System logs
  ├── cache/
  │   └── stocks.yaml    # Stock data cache
  └── watchlists/        # User watchlists
      ├── 123456789.yaml # One file per user
      └── 987654321.yaml
```

## Implementation Plan

### Phase 1: Core Infrastructure (Current)
- Set up YAML file structure
- Implement stock data processing and caching
- Add Telegram bot integration
- Create weekly checker script

### Phase 2: Future Improvements
- Add data retention policies for cache
- Implement backup system for YAML files
- Add user-specific alert thresholds
- Add web UI for visualization

## Security & Infrastructure

**Current Security**:
- No website authentication needed
- Telegram user IDs used as file names
- API keys stored in bot.yaml
- Each user can only access their own watchlist
- Regular backups of YAML files recommended

**Deployment Options**:
- Any Python-compatible web server
- Container-friendly (Docker)
- Low resource requirements
- Can run as a simple cron job on any server

## Service Dependencies
- Telegram Bot API: Alert delivery
- Yahoo Finance: Stock data (rate limited)

## Data Flow Process

1. **Weekly Check Initialization**:
   - Script reads `bot.yaml` for configuration
   - Logs start time in `logs.yaml`

2. **User Processing**:
   - Reads all files in `watchlists/` directory
   - For each user's watchlist:
     - Check last notification time
     - Process their stocks

3. **Stock Data Processing**:
   - For each unique stock:
     - Check `cache/stocks.yaml` for recent data
     - If cache miss/expired, fetch from Yahoo Finance
     - Update cache with new data

4. **Alert Generation**:
   - Compare stock metrics against thresholds
   - Send alerts to relevant users
   - Update user's `last_notified` timestamp
   - Log successes and failures