# Stock Analytics Dashboard - Architecture

## System Overview

A lightweight client-server application with:
- **Frontend**: Vanilla JavaScript, HTML, CSS with Plotly.js for charts
- **Backend**: Python Flask server with yfinance package
- **Data Source**: Yahoo Finance API
- **Database**: Supabase PostgreSQL for watchlist storage
- **Email**: Resend.com for alert notifications

## Data Flow
```
User → Browser → Flask Server → Yahoo Finance API
                     ↓
Yahoo Finance → Data Processing → JSON → Browser → Charts
                     ↓
Watchlist DB ← → Alert Checker → Email Service
```

## Key Design Decisions

1. **Lightweight Architecture**: No complex frameworks; easier to maintain and deploy
2. **Server-side Processing**: All calculations done on server for consistency and client simplicity
3. **Single-page Application**: Smoother user experience with no page reloads
4. **Simple Alert System**: 5th/95th percentile thresholds only
5. **Periodic Checking**: Hourly stock checks to respect API limits

## Data Storage

### Stock Data
- No persistent storage
- All stock data fetched on-demand

### Watchlist Data
```sql
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    last_check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_price REAL,
    last_percentile REAL,
    email TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, email)
);
```

## Implementation Plan

### Phase 1: Core Infrastructure (Current)
- Set up Supabase database
- Implement watchlist CRUD operations
- Add email service integration
- Create periodic checker

### Phase 2: Future Improvements
- Add Redis for stock data caching
- Implement request queue for multiple connections
- Add custom percentile thresholds
- Support multiple notification channels

## Security & Infrastructure

**Current Security**:
- No authentication needed
- Email addresses stored in database
- API keys stored in environment variables

**Deployment Options**:
- Any Python-compatible web server
- Container-friendly (Docker)
- Low resource requirements

## Service Dependencies
- Supabase: Database hosting
- Resend.com: Email delivery (100/day free)
- Yahoo Finance: Stock data (rate limited)