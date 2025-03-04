# Stock Analytics Dashboard - API Documentation

## Overview

- Base URL: `http://localhost:5001` (local development)
- No authentication required
- No rate limiting (but Yahoo Finance API has limits)
- CORS enabled for cross-origin requests

## Endpoints

### 1. Main Page
```
GET /
```
Returns the main web application HTML page

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

**Error Responses**:

```json
{ "error": "Invalid period. Must be one of: 1y, 3y, 5y, max", "code": 400 }
{ "error": "No data available for ticker", "code": 404 }
{ "error": "Failed to process data: [error details]", "code": 500 }
```

## Implementation Notes

**Processing Steps**:
1. Validate ticker symbol and period
2. Fetch complete historical data
3. Calculate 200-day MA and metrics
4. Filter data for requested period
5. Return JSON response

**Data Limitations**:
- First 200 days will have null MA values
- Historical data limited by Yahoo Finance availability
- NaN and Infinity values are converted to null in JSON response

**Future Endpoints**:
- `/data/<ticker>/indicators` - Additional technical indicators
- `/compare/<tickers>` - Multi-stock comparison
- `/search/<query>` - Ticker symbol search