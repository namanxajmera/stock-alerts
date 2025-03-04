# Stock Analytics Dashboard - API Documentation

## Overview

- Base URL: `http://localhost:5000` (local development)
- No authentication required
- No rate limiting (but Yahoo Finance API has limits)

## Endpoints

### 1. Main Page
```
GET /
```
Returns the main web application HTML page

### 2. Stock Data
```
GET /data/<ticker>
```
Retrieves stock data and analysis for a ticker symbol (e.g., AAPL)

**Response Format**:

```json
{
  "ticker": "AAPL",
  "data": {
    "dates": ["2022-01-01", "2022-01-02", ...],
    "prices": [172.34, 173.45, ...],
    "ma_200": [168.23, 168.34, ...],
    "pct_diff": [2.45, 3.04, ...],
    "percentiles": { "p5": -10.2, "p95": 12.5 }
  },
  "summary": {
    "current_price": 178.45,
    "current_ma": 170.23,
    "current_diff_pct": 4.83
  }
}
```

**Error Responses**:

```json
{ "error": "Invalid ticker symbol", "code": 400 }
{ "error": "No data available for ticker", "code": 404 }
{ "error": "Internal server error", "code": 500 }
```

## Implementation Notes

**Processing Steps**:
1. Validate ticker symbol → Fetch data → Calculate metrics → Return JSON

**Data Limitations**:
- First 200 days will have null MA values
- Historical data limited by Yahoo Finance availability

**Future Endpoints**:
- `/data/<ticker>/indicators` - Additional technical indicators
- `/compare/<tickers>` - Multi-stock comparison
- `/search/<query>` - Ticker symbol search