# API Documentation

Complete API reference for the Stock Analytics Dashboard & Telegram Alert system.

## Web API Endpoints

### Base URL
```
http://localhost:5001  # Development
https://yourdomain.com # Production
```

### Authentication
The web API currently operates without authentication for public stock data access. Telegram webhook endpoints require HMAC validation.

---

## Stock Data API

### Get Stock Data
Retrieve historical stock data with technical analysis.

**Endpoint:** `GET /data/<ticker>/<period>`  
**Implementation:** [`app.py:get_stock_data()`](./app.py#L231-235)  
**Processing Logic:** [`app.py:calculate_metrics()`](./app.py#L109-221)

#### Parameters

| Parameter | Type | Required | Description | Valid Values |
|-----------|------|----------|-------------|--------------|
| `ticker` | string | Yes | Stock symbol | Any valid ticker (e.g., AAPL, MSFT) |
| `period` | string | Yes | Time period | `1y`, `3y`, `5y`, `max` |

#### Request Example
```bash
curl "http://localhost:5001/data/AAPL/5y"
```

#### Response Format

**Success Response (200 OK):**
```json
{
  "dates": [
    "2019-01-02",
    "2019-01-03",
    "..."
  ],
  "prices": [
    157.92,
    142.19,
    null
  ],
  "ma_200": [
    null,
    null,
    159.45
  ],
  "pct_diff": [
    null,
    null,
    -10.95
  ],
  "percentiles": {
    "p16": -15.2,
    "p84": 12.8
  },
  "previous_close": 142.19
}
```

**Response Fields:**
- `dates`: Array of date strings (YYYY-MM-DD format)
- `prices`: Array of closing prices (null for missing data)
- `ma_200`: Array of 200-day moving average values
- `pct_diff`: Array of percentage differences from MA200
- `percentiles`: Historical 16th and 84th percentiles (1σ)
- `previous_close`: Previous trading day's closing price

#### Error Responses

**Invalid Ticker (404 Not Found):**
```json
{
  "error": "No data available for this ticker symbol"
}
```

**Invalid Period (400 Bad Request):**
```json
{
  "error": "Invalid period. Must be one of: 1y, 3y, 5y, max"
}
```

**Rate Limited (429 Too Many Requests):**
```json
{
  "error": "Yahoo Finance is temporarily limiting requests. Please try again in a few minutes.",
  "retry_after": "2-3 minutes"
}
```

**Cached Data Notice (202 Accepted):**
```json
{
  "error": "Using recent cached data for AAPL. Full historical cache not yet implemented.",
  "cache_info": "Last updated: 2024-01-15 14:30:00, Price: $185.64"
}
```

#### Implementation Details

**Caching Strategy** ([`app.py:calculate_metrics():118-142`](./app.py#L118-142))
```python
# Check cache first (1 hour cache)
cached_data = db_manager.get_fresh_cache(ticker_symbol, max_age_hours=1)

if cached_data and cached_data.get('data_json'):
    cache_data = json.loads(cached_data['data_json'])
    # Use cached percentiles if available
    if 'percentiles' in cache_data:
        percentile_16th = cache_data['percentiles']['p16']
        percentile_84th = cache_data['percentiles']['p84']
```

**Rate Limiting** ([`app.py:fetch_yahoo_data_with_retry()`](./app.py#L75-107))
```python
def fetch_yahoo_data_with_retry(ticker_symbol, max_retries=3):
    for attempt in range(max_retries):
        try:
            complete_data = ticker.history(period="max")
            return complete_data
        except YFRateLimitError as e:
            wait_time = (2 ** attempt) * 2  # Exponential backoff
            time.sleep(wait_time)
```

---

## Health Check API

### Health Status
Check application health and database connectivity.

**Endpoint:** `GET /health`  
**Implementation:** [`app.py:health_check()`](./app.py#L247-255)

#### Request Example
```bash
curl "http://localhost:5001/health"
```

#### Response Format

**Healthy (200 OK):**
```json
{
  "status": "healthy"
}
```

**Unhealthy (500 Internal Server Error):**
```json
{
  "status": "unhealthy",
  "error": "Database connection failed"
}
```

#### Implementation
```python
def health_check():
    try:
        db_manager.get_config('telegram_token')  # Test DB connectivity
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
```

---

## Static Assets API

### JavaScript Assets
Serve compiled JavaScript files with proper MIME types.

**Endpoint:** `GET /static/js/<filename>`  
**Implementation:** [`app.py:serve_js()`](./app.py#L227-229)

#### Request Example
```bash
curl "http://localhost:5001/static/js/main.js"
```

#### Response
Returns JavaScript file with `application/javascript` MIME type.

#### Implementation
```python
@app.route('/static/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('static/js', filename, mimetype='application/javascript')
```

---

## Telegram Webhook API

### Webhook Endpoint
Secure webhook for Telegram bot updates.

**Endpoint:** `POST /webhook`  
**Implementation:** [`app.py:telegram_webhook()`](./app.py#L237-245)  
**Validation:** [`webhook_handler.py:validate_webhook()`](./webhook_handler.py#L24-44)

#### Security Requirements

**HMAC Validation:**
- Header: `X-Telegram-Bot-Api-Secret-Token`
- Value: Must match `TELEGRAM_WEBHOOK_SECRET` environment variable
- Validation: Uses `hmac.compare_digest()` for timing-safe comparison

#### Request Format
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 123,
    "from": {
      "id": 987654321,
      "is_bot": false,
      "first_name": "John",
      "username": "john_doe"
    },
    "chat": {
      "id": 987654321,
      "first_name": "John",
      "username": "john_doe",
      "type": "private"
    },
    "date": 1640995200,
    "text": "/start"
  }
}
```

#### Response Format

**Success (200 OK):**
```
(Empty response body)
```

**Invalid Webhook (403 Forbidden):**
```json
{
  "error": "Forbidden"
}
```

#### Processing Flow

1. **Validation** ([`webhook_handler.py:validate_webhook()`](./webhook_handler.py#L24-44))
   ```python
   def validate_webhook(self, request_data, secret_token_header):
       if self.secret_token:
           if not hmac.compare_digest(self.secret_token, secret_token_header):
               return False
       
       data = json.loads(request_data)
       if 'update_id' not in data:
           return False
   ```

2. **Message Processing** ([`webhook_handler.py:process_update()`](./webhook_handler.py#L46-79))
   ```python
   def process_update(self, update_data):
       update = json.loads(update_data)
       message = update['message']
       user_id = str(message['from']['id'])
       
       # Add or update user
       self.db.add_user(user_id, username)
       
       # Handle commands
       if message['text'].startswith('/'):
           self._handle_command(message)
   ```

---

## Telegram Bot Commands API

### Command Processing
All bot commands are processed through the webhook endpoint.

#### Command Handlers

**Start Command** ([`webhook_handler.py:_get_welcome_message()`](./webhook_handler.py#L103-112))
```
Command: /start
Response: Welcome message with available commands
```

**Add Stocks** ([`webhook_handler.py:_handle_add_command()`](./webhook_handler.py#L177-197))
```
Command: /add AAPL MSFT GOOGL
Response: "✅ Added AAPL, MSFT, GOOGL to your watchlist."
```

**Remove Stocks** ([`webhook_handler.py:_handle_remove_command()`](./webhook_handler.py#L199-212))
```
Command: /remove AAPL
Response: "✅ Removed 1 stock(s) from your watchlist."
```

**List Watchlist** ([`webhook_handler.py:_handle_list_command()`](./webhook_handler.py#L164-175))
```
Command: /list
Response: "📋 Your Watchlist:
• AAPL (Last Price: $185.64)
• MSFT (Last Price: $378.91)"
```

#### Error Handling

**Unknown Command:**
```
Command: /unknown
Response: "Unknown command. Type /start for help."
```

**Invalid Parameters:**
```
Command: /add
Response: "Please provide at least one ticker. Usage: /add AAPL TSLA"
```

**Watchlist Limit Exceeded:**
```
Command: /add AAPL (when already at limit)
Response: "❌ Could not add:
AAPL: Watchlist limit of 20 stocks reached"
```

---

## Database API

### Internal Database Operations

The application uses an internal database API through [`db_manager.py`](./db_manager.py).

#### Core Operations

**User Management** ([`db_manager.py:add_user()`](./db_manager.py#L97-110))
```python
def add_user(self, user_id, name):
    sql = """
        INSERT INTO users (id, name) VALUES (?, ?)
        ON CONFLICT(id) DO UPDATE SET name = excluded.name
    """
```

**Watchlist Operations** ([`db_manager.py:add_to_watchlist()`](./db_manager.py#L112-133))
```python
def add_to_watchlist(self, user_id, symbol):
    # Check user limits
    cursor.execute("SELECT max_stocks FROM users WHERE id = ?", (user_id,))
    max_stocks = cursor.fetchone()['max_stocks']
    
    # Add to watchlist
    cursor.execute("INSERT INTO watchlist_items (user_id, symbol) VALUES (?, ?)", 
                  (user_id, symbol.upper()))
```

**Cache Management** ([`db_manager.py:get_fresh_cache()`](./db_manager.py#L247-266))
```python
def get_fresh_cache(self, symbol, max_age_hours=1):
    sql = """
        SELECT symbol, last_check, last_price, ma_200, data_json
        FROM stock_cache 
        WHERE symbol = ? 
        AND datetime(last_check) > datetime('now', '-{} hours')
    """.format(max_age_hours)
```

#### Connection Management

**Context Manager** ([`db_manager.py:_managed_cursor()`](./db_manager.py#L28-42))
```python
@contextmanager
def _managed_cursor(self, commit=False):
    conn = self._get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise
    finally:
        conn.close()
```

---

## Alert System API

### Alert Processing
Alerts are processed by the periodic checker system.

#### Alert Logic ([`periodic_checker.py:_process_symbol()`](./periodic_checker.py#L84-167))

**Threshold Evaluation:**
```python
# Check if alert should be sent
if current_pct_diff <= percentile_5 or current_pct_diff >= percentile_95:
    for user_id in user_ids:
        self.webhook_handler.send_alert(
            user_id=user_id, symbol=symbol, price=current_price,
            percentile=current_pct_diff, 
            percentile_5=percentile_5, 
            percentile_95=percentile_95
        )
```

**Alert Message Format** ([`webhook_handler.py:send_alert()`](./webhook_handler.py#L127-162))
```python
message = (
    f"🚨 <b>Stock Alert for {symbol.upper()}</b>\n\n"
    f"Current Price: ${price:.2f}\n"
    f"Current Deviation from 200MA: {percentile:.1f}%\n\n"
    f"📊 <b>Historical Context:</b>\n"
    f" • 16th percentile: {percentile_16:.1f}%\n"
    f" • 84th percentile: {percentile_84:.1f}%\n\n"
)

if percentile <= percentile_16:
    message += f"This is <b>SIGNIFICANTLY LOW</b>. Only 16% of the time has {symbol.upper()} been this far below its 200-day moving average."
elif percentile >= percentile_84:
    message += f"This is <b>SIGNIFICANTLY HIGH</b>. Only 16% of the time has {symbol.upper()} been this far above its 200-day moving average."
```

#### Alert History

All alerts are logged in the database ([`db_manager.py:add_alert_history()`](./db_manager.py#L205-218)):
```python
def add_alert_history(self, user_id, symbol, price, percentile, status='sent', error_message=None):
    sql = """
        INSERT INTO alert_history (user_id, symbol, price, percentile, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
    """
```

---

## Error Handling

### Global Error Handlers

**404 Not Found** ([`app.py:not_found()`](./app.py#L257-259))
```python
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not Found'}), 404
```

**500 Internal Server Error** ([`app.py:server_error()`](./app.py#L261-264))
```python
@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server Error: {error}", exc_info=True)
    return jsonify({'error': 'Internal Server Error'}), 500
```

**403 Forbidden** ([`app.py:forbidden()`](./app.py#L266-268))
```python
@app.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403
```

### Logging

**Structured Logging** ([`app.py:setup_logging()`](./app.py#L31-41))
```python
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/stock_alerts.log'),
            logging.StreamHandler()
        ]
    )
```

**Database Event Logging** ([`db_manager.py:log_event()`](./db_manager.py#L183-192))
```python
def log_event(self, log_type, message, user_id=None, symbol=None):
    sql = "INSERT INTO logs (timestamp, log_type, message, user_id, symbol) VALUES (datetime('now'), ?, ?, ?, ?)"
    cursor.execute(sql, (log_type, message, user_id, symbol))
```

---

## Rate Limiting & Performance

### Yahoo Finance API Limits

**Request Throttling:**
- **Web Requests**: 0.5 second delay between requests
- **Periodic Checks**: 1 second delay between symbols
- **Exponential Backoff**: 2, 4, 8 seconds for rate limit errors

**Cache Strategy:**
- **Web Cache**: 1 hour TTL for interactive requests
- **Periodic Cache**: 2 hour TTL for automated checks
- **Cache Keys**: Symbol-based with timestamp validation

### Database Performance

**Connection Optimization:**
- **Timeout**: 10 second connection timeout
- **Row Factory**: `sqlite3.Row` for efficient access
- **Foreign Keys**: Enabled for data integrity

**Query Optimization:**
- **Indexes**: Strategic indexes on frequently queried columns
- **Prepared Statements**: Parameterized queries for security and performance
- **Batch Operations**: Group processing for multiple symbols

---

## Testing

### API Testing Examples

**Stock Data Testing:**
```bash
# Test valid ticker
curl -s "http://localhost:5001/data/AAPL/5y" | jq .

# Test invalid ticker
curl -s "http://localhost:5001/data/INVALID/5y" | jq .

# Test invalid period
curl -s "http://localhost:5001/data/AAPL/invalid" | jq .

# Test health endpoint
curl -s "http://localhost:5001/health" | jq .
```

**Webhook Testing:**
```bash
# Test webhook with valid secret
curl -X POST "http://localhost:5001/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: your_secret_here" \
  -d '{"update_id": 1, "message": {"message_id": 1, "from": {"id": 123, "first_name": "Test"}, "chat": {"id": 123, "type": "private"}, "date": 1640995200, "text": "/start"}}'

# Test webhook without secret (should return 403)
curl -X POST "http://localhost:5001/webhook" \
  -H "Content-Type: application/json" \
  -d '{"update_id": 1}'
```

### Load Testing

**Stock Data Load Test:**
```bash
# Multiple concurrent requests
for i in {1..10}; do
  curl -s "http://localhost:5001/data/AAPL/5y" &
done
wait
```

---

## API Versioning

### Current Version
- **Version**: 1.0
- **Status**: Stable
- **Backward Compatibility**: Maintained for core endpoints

### Future Considerations
- **API Versioning**: URL-based versioning (`/api/v1/data/...`)
- **Rate Limiting**: Per-user rate limiting for production
- **Authentication**: JWT tokens for authenticated endpoints
- **WebSocket**: Real-time price updates
- **GraphQL**: Flexible data fetching for complex queries

---

This API documentation provides complete coverage of all endpoints and functionality in the Stock Alerts system. For implementation details, refer to the source code files referenced throughout this document.