# Troubleshooting Guide

Comprehensive solutions for common issues during setup, deployment, and operation. Always check application logs first for detailed error messages.

## 🔍 Quick Diagnosis

### Log Files Location
- **Application Logs**: `logs/stock_alerts.log`
- **Platform Logs**: See platform-specific sections below
- **Database Logs**: Check PostgreSQL server logs

### Health Check Commands
```bash
# Application health
curl http://localhost:5001/health
# Expected: {"status": "healthy"}

# Database connectivity (via admin panel)
curl -u admin:password http://localhost:5001/admin

# Telegram webhook status
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

---

## 🚨 Application Startup Issues

### Application Won't Start

**Symptoms:**
- `python app.py` exits immediately
- Gunicorn process crashes on startup
- 503/502 errors from platform

#### Missing Environment Variables

**Error Messages:**
```
ValueError: DATABASE_URL environment variable is required
ValueError: Missing required environment variables: TELEGRAM_BOT_TOKEN, TIINGO_API_TOKEN
```

**Source:** [`utils/config.py:_validate_required_config()`](../utils/config.py)

**Solutions:**
```bash
# Check current environment variables
env | grep -E "DATABASE_URL|TELEGRAM_BOT_TOKEN|TIINGO_API_TOKEN"

# Create .env file with required variables
cat > .env << EOF
DATABASE_URL=postgresql://user:pass@localhost:5432/stockalerts
TELEGRAM_BOT_TOKEN=your_bot_token_here
TIINGO_API_TOKEN=your_tiingo_token_here
EOF

# Verify configuration loading
python -c "from utils.config import config; print(config.get_config_summary())"
```

#### Python Dependencies Missing

**Error Messages:**
```
ModuleNotFoundError: No module named 'flask'
ModuleNotFoundError: No module named 'psycopg2'
```

**Source:** Missing packages from [`requirements.txt`](../requirements.txt)

**Solutions:**
```bash
# Verify virtual environment is activated
which python  # Should show venv/bin/python

# Install all dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify key packages
python -c "import flask, psycopg2, pandas; print('Dependencies OK')"
```

#### Database Connection Failure

**Error Messages:**
```
psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed
psycopg2.OperationalError: FATAL: database "stockalerts" does not exist
psycopg2.OperationalError: FATAL: password authentication failed
```

**Source:** [`db_manager.py:__init__()`](../db_manager.py)

**Solutions:**

1. **Check PostgreSQL Service**
   ```bash
   # Linux/macOS
   sudo systemctl status postgresql  # or brew services list | grep postgres
   
   # Start if not running
   sudo systemctl start postgresql   # or brew services start postgresql
   ```

2. **Verify Database Exists**
   ```bash
   # Connect to PostgreSQL and create database
   sudo -u postgres psql
   CREATE DATABASE stockalerts;
   CREATE USER stockalerts WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE stockalerts TO stockalerts;
   \q
   ```

3. **Test Connection String**
   ```bash
   # Test DATABASE_URL format
   psql "postgresql://user:pass@localhost:5432/stockalerts" -c "SELECT version();"
   ```

---

## 📊 Web Dashboard Issues

### Charts Not Loading or Empty

**Symptoms:**
- Web page loads but charts remain empty
- Error messages after entering ticker
- API request failures in browser console

#### Invalid Tiingo API Token

**Error Messages:**
```
# In logs/stock_alerts.log
HTTPError: 401 Client Error: Unauthorized for url: https://api.tiingo.com/tiingo/daily/...
TiingoClient: Authentication failed - check API token

# In browser console
Fetch error: 500 Internal Server Error
```

**Source:** [`utils/tiingo_client.py:fetch_historical_data()`](../utils/tiingo_client.py)

**Solutions:**
```bash
# Test Tiingo API token directly
curl "https://api.tiingo.com/api/test?token=${TIINGO_API_TOKEN}"
# Expected: {"message": "You successfully sent a request"}

# Check token in environment
echo $TIINGO_API_TOKEN

# Verify token in .env file
grep TIINGO_API_TOKEN .env

# Test with a known stock
curl "https://api.tiingo.com/tiingo/daily/AAPL/prices?token=${TIINGO_API_TOKEN}&startDate=2024-01-01"
```

#### Invalid Ticker Symbol

**Error Messages:**
```
# Browser console
GET /data/INVALID/5y 400 (Bad Request)
{"error": "Invalid ticker symbol: INVALID"}

# Application logs
Validation error: Invalid ticker symbol format
```

**Source:** [`utils/validators.py:validate_ticker_symbol()`](../utils/validators.py)

**Solutions:**
```bash
# Test with known valid tickers
curl "http://localhost:5001/data/AAPL/1y"
curl "http://localhost:5001/data/GOOGL/1y"
curl "http://localhost:5001/data/TSLA/1y"

# Check ticker symbol format requirements:
# - 1-5 characters
# - Alphanumeric only
# - Automatically converted to uppercase
```

#### API Rate Limiting

**Error Messages:**
```
HTTPError: 429 Too Many Requests
TiingoClient: Rate limit exceeded, retrying in 60 seconds
```

**Solutions:**
```bash
# Check current cache status
curl -u admin:password "http://localhost:5001/admin"
# Look for recent cache entries in stock_cache table

# Increase cache duration (default 1 hour)
echo "CACHE_HOURS=24" >> .env

# Check API request delay setting
echo "TIINGO_REQUEST_DELAY=5.0" >> .env
```

#### JavaScript/Frontend Issues

**Error Messages:**
```
# Browser console
Uncaught TypeError: Cannot read property 'dates' of undefined
Fetch failed: NetworkError when attempting to fetch resource
```

**Solutions:**
```bash
# Check if static files are being served correctly
curl "http://localhost:5001/static/js/main.js"
curl "http://localhost:5001/static/css/style.css"

# Test API endpoint directly
curl "http://localhost:5001/data/AAPL/1y" | jq .

# Check for CORS issues (should be enabled)
grep -r "CORS" app.py
```

---

## 🤖 Telegram Bot Issues

### Bot Not Responding to Commands

**Symptoms:**
- Commands like `/start`, `/add`, `/list` get no response
- Bot appears offline or unresponsive
- Messages sent but no replies received

#### Webhook Not Configured

**Diagnosis:**
```bash
# Check webhook status
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"

# Expected for properly configured webhook:
{
  "ok": true,
  "result": {
    "url": "https://your-app.com/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}

# If webhook is not set:
{
  "ok": true, 
  "result": {
    "url": "",
    "has_custom_certificate": false
  }
}
```

**Solutions:**

1. **Local Development (ngrok required)**
   ```bash
   # Install and start ngrok
   ngrok http 5001
   
   # Use the HTTPS URL provided by ngrok
   python setup_webhook.py
   # Enter: https://abc123.ngrok.io/webhook
   ```

2. **Production Deployment**
   ```bash
   # Set webhook to your production URL
   python setup_webhook.py
   # Enter: https://your-app.railway.app/webhook
   ```

3. **Manual Webhook Setup**
   ```bash
   curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://your-app.com/webhook",
       "secret_token": "your_webhook_secret"
     }'
   ```

#### Invalid Webhook Secret Token

**Error Messages:**
```
# In logs/stock_alerts.log
Invalid secret token in webhook request
Webhook validation failed: timing attack detected
```

**Source:** [`webhook_handler.py:validate_webhook()`](../webhook_handler.py)

**Solutions:**
```bash
# Generate new webhook secret
python -c "from webhook_handler import WebhookHandler; print(WebhookHandler.generate_webhook_secret())"

# Update .env file
echo "TELEGRAM_WEBHOOK_SECRET=new_generated_secret" >> .env

# Reconfigure webhook with new secret
python setup_webhook.py
```

#### Bot Token Issues

**Error Messages:**
```
HTTPError: 401 Unauthorized
Invalid bot token provided
```

**Solutions:**
```bash
# Test bot token
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"

# Expected response:
{
  "ok": true,
  "result": {
    "id": 123456789,
    "is_bot": true,
    "first_name": "YourBotName",
    "username": "yourbotname_bot"
  }
}

# If invalid token, get new one from @BotFather
```

#### Application Not Receiving Webhooks

**Error Messages:**
```
# Telegram getWebhookInfo shows errors
"last_error_date": 1640995200,
"last_error_message": "Connection refused"
```

**Solutions:**
```bash
# Test webhook endpoint directly
curl -X POST "https://your-app.com/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: your_secret" \
  -d '{"update_id": 1, "message": {"text": "test"}}'

# Check if app is accessible
curl "https://your-app.com/health"

# Check application logs for webhook processing
tail -f logs/stock_alerts.log | grep -i webhook
```

---

## ⏰ Alert System Issues

### Daily Alerts Not Being Sent

**Symptoms:**
- Users have stocks in watchlist but receive no alerts
- Expected alerts during market volatility not triggered
- No alert history in admin panel

#### Background Scheduler Issues

**Diagnosis:**
```bash
# Check scheduler status in logs
grep -i "scheduler\|apscheduler" logs/stock_alerts.log

# Expected log entries:
# [INFO] APScheduler started successfully - daily stock checks scheduled for 1 AM UTC
# [INFO] Starting scheduled stock check...
# [INFO] Scheduled stock check completed successfully

# Check if scheduler is configured
grep -r "setup_scheduler" app.py utils/scheduler.py
```

**Error Messages:**
```
# Scheduler not starting
APScheduler failed to start: [error details]
Scheduler job execution failed: [error details]

# Job execution errors
Error in scheduled stock check: [error details]
PeriodicChecker.check_watchlists() failed: [error details]
```

**Source:** [`utils/scheduler.py:setup_scheduler()`](../utils/scheduler.py)

**Solutions:**

1. **Manual Trigger Test**
   ```bash
   # Test alert system manually
   curl -X POST "http://localhost:5001/admin/check" \
     -H "X-API-Key: ${ADMIN_API_KEY}" \
     -H "Content-Type: application/json"
   
   # Check response for execution details
   ```

2. **Check Scheduler Configuration**
   ```bash
   # Verify scheduler is enabled
   python -c "
   from utils.scheduler import setup_scheduler
   scheduler = setup_scheduler()
   print('Scheduler jobs:', [job.name for job in scheduler.get_jobs()])
   "
   ```

3. **Platform-Specific Issues**
   ```bash
   # Some platforms may kill background processes
   # Check platform documentation for persistent workers
   
   # For Heroku - consider using Heroku Scheduler add-on instead
   # For Railway - should work out of the box
   # For Docker - ensure container doesn't exit
   ```

#### Alert Logic Issues

**Error Messages:**
```
# Data fetching failures
TiingoClient: Failed to fetch data for AAPL: HTTPError 429
Stock data unavailable for alert checking

# Calculation errors  
Insufficient data for meaningful analysis (need at least 20 data points)
Percentile calculation failed: division by zero

# Alert sending failures
Telegram API error: HTTPError 400 Bad Request
Webhook send_alert() failed: connection timeout
```

**Source:** [`periodic_checker.py:check_watchlists()`](../periodic_checker.py)

**Solutions:**

1. **Check Watchlist Data**
   ```bash
   # Verify users have active watchlists
   curl -u admin:password "http://localhost:5001/admin"
   # Look for entries in watchlist_items table
   
   # Check notification preferences
   # notification_enabled should be TRUE for users
   ```

2. **Test Stock Data Pipeline**
   ```bash
   # Test data fetching for watchlist symbols
   curl "http://localhost:5001/data/AAPL/5y"
   curl "http://localhost:5001/trading-stats/AAPL/5y"
   
   # Verify percentile calculation works
   ```

3. **Check Alert Thresholds**
   ```python
   # Default alert thresholds in database
   # alert_threshold_low: 5.0 (5th percentile)
   # alert_threshold_high: 95.0 (95th percentile)
   
   # Alerts only sent when stock moves outside 16th-84th percentile range
   # This is relatively rare - may need manual testing with volatile stocks
   ```

#### Alert History and Debugging

**Check Alert History:**
```bash
# View recent alert attempts
curl -u admin:password "http://localhost:5001/admin" | grep -A 10 "alert_history"

# Check database directly
psql "$DATABASE_URL" -c "SELECT * FROM alert_history ORDER BY sent_at DESC LIMIT 10;"
```

**Debug Alert Conditions:**
```python
# Test alert logic manually
python -c "
from periodic_checker import PeriodicChecker
from db_manager import DatabaseManager
from utils.config import config

db = DatabaseManager(config.DATABASE_URL)
checker = PeriodicChecker()

# Get active watchlists
watchlists = db.get_active_watchlists()
print(f'Active watchlists: {len(watchlists)}')

# Test specific stock
result = checker._check_stock_for_alerts('AAPL', [{'user_id': 'test'}])
print(f'Alert result: {result}')
"
```

---

## 🔐 Authentication & Access Issues

### Admin Panel Access Denied

**Symptoms:**
- Browser repeatedly prompts for username/password
- 401 Unauthorized errors when accessing `/admin`
- Authentication popup never accepts credentials

#### HTTP Basic Auth Issues

**Error Messages:**
```
HTTP 401 Unauthorized
WWW-Authenticate: Basic realm="Admin Area"
```

**Source:** [`services/auth_service.py:require_admin_auth()`](../services/auth_service.py)

**Solutions:**

1. **Verify Credentials**
   ```bash
   # Check environment variables
   echo "Username: $ADMIN_USERNAME"
   echo "Password set: $([ -n "$ADMIN_PASSWORD" ] && echo 'Yes' || echo 'No')"
   
   # Check .env file
   grep -E "ADMIN_USERNAME|ADMIN_PASSWORD" .env
   ```

2. **Test Authentication**
   ```bash
   # Test with curl
   curl -u "$ADMIN_USERNAME:$ADMIN_PASSWORD" "http://localhost:5001/admin"
   
   # Should return HTML content, not 401 error
   ```

3. **Browser Issues**
   ```bash
   # Clear browser cache and stored passwords
   # Try incognito/private browsing mode
   # Manually enter credentials in URL: http://username:password@localhost:5001/admin
   ```

#### Missing Admin Credentials

**Error Messages:**
```
# In application logs
Admin credentials not configured - admin panel disabled
ADMIN_USERNAME or ADMIN_PASSWORD not set
```

**Solutions:**
```bash
# Set admin credentials in .env
echo "ADMIN_USERNAME=admin" >> .env
echo "ADMIN_PASSWORD=secure_password_here" >> .env

# Restart application to load new credentials
```

### API Key Authentication Issues

**Symptoms:**
- `/admin/check` endpoint returns 401 errors
- Manual alert triggers fail with unauthorized

#### Missing or Invalid API Key

**Error Messages:**
```
{"status": "error", "message": "API key required"}
{"status": "error", "message": "Unauthorized"}
```

**Source:** [`services/auth_service.py:validate_admin_api_key()`](../services/auth_service.py)

**Solutions:**
```bash
# Generate secure API key
ADMIN_API_KEY=$(openssl rand -hex 32)
echo "ADMIN_API_KEY=$ADMIN_API_KEY" >> .env

# Test API key
curl -X POST "http://localhost:5001/admin/check" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json"
```

---

## 🖥️ Platform-Specific Issues

### Railway Deployment Problems

**Common Issues:**
- Build failures during deployment
- Environment variables not loading
- Database connection timeouts

**Solutions:**
```bash
# Check deployment logs
railway logs

# Verify environment variables
railway variables

# Check service status
railway status

# Redeploy if needed
railway deploy
```

### Heroku Deployment Problems

**Common Issues:**
- Slug size too large
- Dyno sleeping (free tier)
- Add-on configuration issues

**Solutions:**
```bash
# Check app status
heroku ps

# View logs
heroku logs --tail

# Check configuration
heroku config

# Scale dynos
heroku ps:scale web=1
```

### Docker Container Issues

**Common Issues:**
- Container exits immediately
- Port binding problems
- Volume mount issues

**Solutions:**
```bash
# Check container logs
docker logs container_name

# Debug container interactively
docker run -it --entrypoint /bin/bash stock-alerts

# Check port mapping
docker port container_name

# Verify environment variables
docker inspect container_name | jq '.Config.Env'
```

---

## 📊 Performance Issues

### Slow API Responses

**Symptoms:**
- Charts take long time to load
- Timeout errors on stock data requests
- Poor user experience

**Diagnosis:**
```bash
# Test API response times
time curl "http://localhost:5001/data/AAPL/5y"

# Check cache hit rates
curl -u admin:password "http://localhost:5001/admin" | grep "stock_cache"

# Monitor database connections
psql "$DATABASE_URL" -c "SELECT count(*) FROM pg_stat_activity;"
```

**Solutions:**

1. **Optimize Caching**
   ```bash
   # Increase cache duration
   echo "CACHE_HOURS=24" >> .env
   
   # Pre-populate cache for popular stocks
   for symbol in AAPL GOOGL MSFT TSLA; do
     curl "http://localhost:5001/data/$symbol/5y" > /dev/null
   done
   ```

2. **Database Optimization**
   ```sql
   -- Check for missing indexes
   SELECT schemaname, tablename, attname, n_distinct, correlation 
   FROM pg_stats 
   WHERE tablename IN ('stock_cache', 'watchlist_items', 'users');
   
   -- Analyze query performance
   EXPLAIN ANALYZE SELECT * FROM stock_cache WHERE symbol = 'AAPL';
   ```

3. **Application Tuning**
   ```bash
   # Increase worker processes (if sufficient memory)
   # Gunicorn: --workers 2
   # Railway.json: already configured optimally
   
   # Adjust API request delays
   echo "TIINGO_REQUEST_DELAY=1.0" >> .env
   ```

---

## 🔍 Debugging Tools

### Log Analysis

```bash
# Real-time log monitoring
tail -f logs/stock_alerts.log

# Filter for specific issues
grep -i "error\|warning\|fail" logs/stock_alerts.log

# Search for specific components
grep -i "webhook\|scheduler\|tiingo" logs/stock_alerts.log

# Check recent activity
tail -50 logs/stock_alerts.log
```

### Database Inspection

```sql
-- Check application health
SELECT 
  (SELECT count(*) FROM users) as users,
  (SELECT count(*) FROM watchlist_items) as watchlist_items,
  (SELECT count(*) FROM stock_cache) as cached_stocks,
  (SELECT count(*) FROM alert_history WHERE sent_at > NOW() - INTERVAL '24 hours') as recent_alerts;

-- Find problematic data
SELECT symbol, last_check, 
  EXTRACT(epoch FROM NOW() - last_check)/3600 as hours_old
FROM stock_cache 
WHERE last_check < NOW() - INTERVAL '24 hours';

-- Check alert patterns
SELECT symbol, status, count(*) 
FROM alert_history 
WHERE sent_at > NOW() - INTERVAL '7 days'
GROUP BY symbol, status;
```

### Network Diagnostics

```bash
# Test external API connectivity
curl -I "https://api.tiingo.com/api/test"
curl -I "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"

# Test application endpoints
curl -I "http://localhost:5001/health"
curl -I "http://localhost:5001/data/AAPL/1y"

# Check DNS resolution
nslookup api.tiingo.com
nslookup api.telegram.org
```

---

## 🆘 Getting Additional Help

### Contact Information
- **Documentation**: [SETUP.md](./SETUP.md), [DEPLOYMENT.md](./DEPLOYMENT.md), [API.md](./API.md)
- **Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md) for system understanding
- **Contributing**: [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup

### Debug Information to Collect

When reporting issues, include:

1. **Environment Details**
   ```bash
   python --version
   pip freeze | grep -E "flask|psycopg2|pandas|requests"
   echo "OS: $(uname -a)"
   ```

2. **Configuration Summary**
   ```bash
   python -c "from utils.config import config; print(config.get_config_summary())"
   ```

3. **Recent Logs**
   ```bash
   tail -100 logs/stock_alerts.log
   ```

4. **Database Status**
   ```bash
   curl -u admin:password "http://localhost:5001/admin" 2>/dev/null | grep -c "table"
   ```

5. **Network Connectivity**
   ```bash
   curl -s "http://localhost:5001/health"
   curl -s "https://api.tiingo.com/api/test?token=${TIINGO_API_TOKEN}" | head -1
   ```