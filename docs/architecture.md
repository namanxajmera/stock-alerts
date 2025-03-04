# Stock Analytics Dashboard - Architecture

## System Overview

A lightweight client-server application with:
- **Frontend**: Vanilla JavaScript, HTML, CSS with Plotly.js for charts
- **Backend**: Python Flask server with yfinance package
- **Data Source**: Yahoo Finance API

## Data Flow
```
User → Browser → Flask Server → Yahoo Finance API
                     ↓
Yahoo Finance → Data Processing → JSON → Browser → Charts
```

## Key Design Decisions

1. **Lightweight Architecture**: No complex frameworks; easier to maintain and deploy
2. **Server-side Processing**: All calculations done on server for consistency and client simplicity
3. **Single-page Application**: Smoother user experience with no page reloads

## Data Storage
- No persistent database
- All stock data fetched on-demand

## Scalability

**Current Limitations**:
- Yahoo Finance API rate limits
- No caching mechanism

**Future Improvements**:
- Add Redis for caching stock queries
- Implement request queue for handling multiple connections

## Security & Infrastructure

**Current Security**:
- No authentication needed
- No sensitive data stored

**Deployment Options**:
- Any Python-compatible web server
- Container-friendly (Docker)
- Low resource requirements