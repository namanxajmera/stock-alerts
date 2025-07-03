# Troubleshooting Guide

Comprehensive troubleshooting guide for the Stock Analytics Dashboard & Telegram Alert system.

## Quick Diagnostic Commands

### System Health Check
```bash
# Check application status
curl -s http://localhost:5001/health | jq .

# Check database connectivity
sqlite3 db/stockalerts.db "SELECT COUNT(*) FROM users;"

# Check log files for errors
tail -n 50 logs/stock_alerts.log | grep ERROR

# Check Python environment
source venv/bin/activate && python -c "import app; print('OK')"
```

---

## Installation & Setup Issues

### Python Environment Problems

#### Issue: `ModuleNotFoundError` when starting application
**Symptoms:**
```bash
$ python app.py
ModuleNotFoundError: No module named 'flask'
```

**Diagnosis:**
- Virtual environment not activated
- Dependencies not installed
- Wrong Python version

**Solutions:**
```bash
# 1. Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# 2. Verify Python version
python --version  # Should be 3.8+

# 3. Reinstall dependencies
pip install -r requirements.txt

# 4. Test imports
python -c "import flask, yfinance, pandas; print('All modules available')"
```

#### Issue: Virtual environment creation fails
**Symptoms:**
```bash
$ python -m venv venv
Error: No module named venv
```

**Solutions:**
```bash
# Ubuntu/Debian - install python3-venv
sudo apt install python3-venv

# CentOS/RHEL - use python3.8
python3.8 -m venv venv

# Alternative: use virtualenv
pip install virtualenv
virtualenv venv
```

### Database Issues

#### Issue: Database permission errors
**Symptoms:**
```bash
sqlite3.OperationalError: unable to open database file
PermissionError: [Errno 13] Permission denied: 'db/stockalerts.db'
```

**Diagnosis:**
- Incorrect file permissions
- Directory doesn't exist
- Insufficient disk space

**Solutions:**
```bash
# 1. Check and create directory
mkdir -p db
ls -la db/

# 2. Fix permissions
chmod 755 db/
chmod 644 db/stockalerts.db  # if file exists

# 3. Check disk space
df -h .

# 4. Check file ownership
sudo chown $USER:$USER db/stockalerts.db
```

#### Issue: Database schema errors
**Symptoms:**
```bash
sqlite3.OperationalError: no such table: users
```

**Solutions:**
```bash
# 1. Check if database was initialized
sqlite3 db/stockalerts.db ".tables"

# 2. Manual initialization
python -c "from db_manager import DatabaseManager; DatabaseManager()"

# 3. Check migration files
ls -la migrations/
cat migrations/001_initial.sql

# 4. Force re-initialization (WARNING: deletes data)
rm db/stockalerts.db
python app.py
```

---

## Web Application Issues

### Server Startup Problems

#### Issue: Flask server won't start
**Symptoms:**
```bash
$ python app.py
Traceback (most recent call last):
OSError: [Errno 48] Address already in use
```

**Diagnosis:**
- Port 5001 already in use
- Another instance running
- Permission issues

**Solutions:**
```bash
# 1. Check what's using the port
sudo netstat -tulpn | grep :5001
# or
sudo lsof -i :5001

# 2. Kill existing process
sudo kill -9 $(sudo lsof -t -i:5001)

# 3. Use different port
PORT=5002 python app.py

# 4. Check for running instances
ps aux | grep "python.*app.py"
```

#### Issue: Import errors in [`app.py`](./app.py)
**Symptoms:**
```bash
ImportError: cannot import name 'DatabaseManager' from 'db_manager'
```

**Solutions:**
```bash
# 1. Verify file structure
ls -la *.py
# Should show: app.py, db_manager.py, webhook_handler.py, periodic_checker.py

# 2. Check Python path
python -c "import sys; print(sys.path)"

# 3. Test individual imports
python -c "from db_manager import DatabaseManager; print('OK')"
python -c "from webhook_handler import WebhookHandler; print('OK')"

# 4. Check for syntax errors
python -m py_compile app.py
python -m py_compile db_manager.py
```

### Stock Data API Issues

#### Issue: Yahoo Finance rate limiting
**Symptoms:**
```bash
yfinance.exceptions.YFRateLimitError: Too Many Requests
HTTP 429 responses from /data/AAPL/5y
```

**Diagnosis:**
- Too many requests to Yahoo Finance
- Rate limiting not working properly
- Multiple instances making requests

**Solutions:**
```bash
# 1. Check cache effectiveness
sqlite3 db/stockalerts.db "SELECT symbol, last_check FROM stock_cache ORDER BY last_check DESC LIMIT 10;"

# 2. Increase delays in app.py:fetch_yahoo_data_with_retry()
# Edit line 92-96 to increase wait times

# 3. Clear cache to reset state
sqlite3 db/stockalerts.db "DELETE FROM stock_cache WHERE last_check < datetime('now', '-1 hours');"

# 4. Monitor request frequency
tail -f logs/stock_alerts.log | grep "Fetching Yahoo Finance data"
```

#### Issue: Invalid stock data responses
**Symptoms:**
```json
{"error": "No data available for this ticker symbol"}
```

**Diagnosis:**
- Invalid ticker symbol
- Yahoo Finance API changes
- Network connectivity issues

**Solutions:**
```bash
# 1. Test ticker validity
python -c "import yfinance as yf; print(yf.Ticker('AAPL').history(period='1d'))"

# 2. Check network connectivity
curl -s "https://finance.yahoo.com" > /dev/null && echo "Yahoo Finance accessible"

# 3. Test with known good ticker
curl "http://localhost:5001/data/AAPL/1y"

# 4. Check application logs
grep "No data available" logs/stock_alerts.log
```

#### Issue: Frontend chart rendering problems
**Symptoms:**
- Charts not displaying
- JavaScript errors in browser console
- Blank dashboard

**Diagnosis:**
- Plotly.js CDN issues
- JavaScript compilation problems
- CSS/static file serving issues

**Solutions:**
```bash
# 1. Check static file serving
curl "http://localhost:5001/static/js/main.js"
curl "http://localhost:5001/static/css/style.css"

# 2. Verify Plotly.js CDN in templates/index.html:7
curl -s "https://cdn.plot.ly/plotly-2.29.1.min.js" > /dev/null && echo "Plotly CDN accessible"

# 3. Check browser console (F12) for JavaScript errors

# 4. Test API endpoint separately
curl "http://localhost:5001/data/AAPL/5y" | jq .
```

---

## Telegram Bot Issues

### Bot Setup Problems

#### Issue: Telegram webhook not receiving updates
**Symptoms:**
- Bot doesn't respond to messages
- No logs in webhook handler
- `/start` command ignored

**Diagnosis:**
- Webhook URL not set correctly
- Secret token mismatch
- HTTPS/SSL issues
- Firewall blocking requests

**Solutions:**
```bash
# 1. Check webhook configuration
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# 2. Verify webhook URL accessibility
curl -X POST "https://yourdomain.com/webhook" \
     -H "X-Telegram-Bot-Api-Secret-Token: your_secret" \
     -H "Content-Type: application/json" \
     -d '{"update_id": 1, "message": {"message_id": 1, "from": {"id": 123}, "text": "/start"}}'

# 3. Check application logs for webhook requests
tail -f logs/stock_alerts.log | grep "webhook\|telegram"

# 4. Reset webhook (remove and set again)
curl -F "url=" "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook"
curl -F "url=https://yourdomain.com/webhook" \
     -F "secret_token=your_secret" \
     "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook"
```

#### Issue: Bot token authentication failures
**Symptoms:**
```bash
telegram.error.InvalidToken: Invalid token
requests.exceptions.HTTPError: 401 Unauthorized
```

**Solutions:**
```bash
# 1. Verify bot token format (should be like: 123456789:ABCdef...)
echo $TELEGRAM_BOT_TOKEN

# 2. Test token with Telegram API
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"

# 3. Check environment variable loading
python -c "import os; print('Token:', os.getenv('TELEGRAM_BOT_TOKEN')[:10] + '...')"

# 4. Regenerate token with @BotFather if needed
# Message @BotFather -> /mybots -> select bot -> API Token
```

#### Issue: Webhook secret validation failures
**Symptoms:**
```bash
WARNING - Invalid secret token on incoming webhook
HTTP 403 Forbidden responses
```

**Diagnosis:**
- Environment variable not loaded
- Secret token mismatch
- Webhook not using secret

**Solutions:**
```bash
# 1. Check secret token environment variable
python -c "import os; print('Secret length:', len(os.getenv('TELEGRAM_WEBHOOK_SECRET', '')))"

# 2. Verify webhook_handler.py:validate_webhook() logic
python -c "
import hmac
secret = 'your_secret'
test_header = 'your_secret'
print('HMAC comparison:', hmac.compare_digest(secret, test_header))
"

# 3. Check webhook request headers
# Add logging to webhook_handler.py:validate_webhook() to see incoming headers

# 4. Regenerate secret token
python -c "import secrets; print(secrets.token_hex(32))"
```

### Bot Command Issues

#### Issue: Bot commands not working
**Symptoms:**
- `/start` returns no response
- `/add AAPL` shows errors
- Commands timeout

**Diagnosis:**
- Database connection issues
- Command parsing problems
- Message sending failures

**Solutions:**
```bash
# 1. Test database operations manually
python -c "
from db_manager import DatabaseManager
db = DatabaseManager()
db.add_user('test123', 'Test User')
print('Database OK')
"

# 2. Check command parsing in webhook_handler.py:_handle_command()
# Add debug logging to see parsed commands

# 3. Test Telegram API message sending
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
     -H "Content-Type: application/json" \
     -d '{"chat_id": "YOUR_CHAT_ID", "text": "Test message"}'

# 4. Check for rate limiting from Telegram
grep "Too Many Requests" logs/stock_alerts.log
```

#### Issue: Watchlist operations failing
**Symptoms:**
```bash
❌ Could not add: AAPL: Watchlist limit of 20 stocks reached
Database errors when adding stocks
```

**Solutions:**
```bash
# 1. Check user limits in database
sqlite3 db/stockalerts.db "
SELECT id, name, max_stocks, 
       (SELECT COUNT(*) FROM watchlist_items WHERE user_id = users.id) as current_stocks
FROM users;
"

# 2. Update user limits if needed
sqlite3 db/stockalerts.db "UPDATE users SET max_stocks = 50 WHERE id = 'USER_ID';"

# 3. Check for database constraints
sqlite3 db/stockalerts.db ".schema watchlist_items"

# 4. Test watchlist operations manually
python -c "
from db_manager import DatabaseManager
db = DatabaseManager()
success, error = db.add_to_watchlist('test123', 'AAPL')
print('Success:', success, 'Error:', error)
"
```

---

## Periodic Checker Issues

### Alert System Problems

#### Issue: Periodic checker not running
**Symptoms:**
- No alerts being sent
- No periodic_checker logs
- Watchlist not being processed

**Diagnosis:**
- Cron job not configured
- Service not enabled
- Script errors

**Solutions:**
```bash
# 1. Test manual execution
cd /path/to/stock-alerts
source venv/bin/activate
python periodic_checker.py

# 2. Check cron configuration
crontab -l | grep periodic_checker

# 3. Check systemd timer (if using)
sudo systemctl status stockalerts-checker.timer
sudo systemctl list-timers | grep stockalerts

# 4. Check script permissions and paths
ls -la periodic_checker.py
which python
```

#### Issue: Alerts not being sent despite thresholds met
**Symptoms:**
- Stocks hit extreme percentiles
- No Telegram notifications
- Alert logic not triggering

**Diagnosis:**
- Notification settings disabled
- Alert threshold logic errors
- Telegram sending failures

**Solutions:**
```bash
# 1. Check user notification settings
sqlite3 db/stockalerts.db "
SELECT id, name, notification_enabled, last_notified 
FROM users WHERE notification_enabled = TRUE;
"

# 2. Check stock percentiles manually
python -c "
from periodic_checker import PeriodicChecker
checker = PeriodicChecker()
checker._process_symbol('AAPL', ['test_user'])
"

# 3. Check alert history
sqlite3 db/stockalerts.db "
SELECT * FROM alert_history 
ORDER BY sent_at DESC LIMIT 10;
"

# 4. Test alert sending manually
python -c "
from webhook_handler import WebhookHandler
from db_manager import DatabaseManager
import os
wh = WebhookHandler(DatabaseManager(), os.getenv('TELEGRAM_BOT_TOKEN'))
wh.send_alert('USER_ID', 'AAPL', 150.0, -18.5, -20.0, 15.0)
"
```

#### Issue: Yahoo Finance data fetching errors in periodic checker
**Symptoms:**
```bash
ERROR - Error processing symbol AAPL: Rate limited after 3 attempts
WARNING - No data available for TSLA
```

**Solutions:**
```bash
# 1. Check periodic checker rate limiting
# Edit periodic_checker.py:_fetch_symbol_data_with_retry()
# Increase delays: wait_time = (2 ** attempt) * 10  # More aggressive backoff

# 2. Verify cache usage in periodic checks
sqlite3 db/stockalerts.db "
SELECT symbol, last_check, 
       ROUND((julianday('now') - julianday(last_check)) * 24, 2) as hours_old
FROM stock_cache 
ORDER BY last_check DESC;
"

# 3. Stagger periodic checks
# Modify cron to run at different times for different symbols

# 4. Monitor API usage
tail -f logs/stock_alerts.log | grep "Fetching data for"
```

---

## Performance Issues

### Memory and CPU Problems

#### Issue: High memory usage
**Symptoms:**
- Application using excessive RAM
- System running out of memory
- Slow response times

**Diagnosis:**
- Memory leaks
- Large datasets not being cleared
- Too many concurrent requests

**Solutions:**
```bash
# 1. Monitor memory usage
ps aux | grep python
top -p $(pgrep -f "python.*app.py")

# 2. Check for memory leaks
python -c "
import gc
gc.collect()
print('Objects:', len(gc.get_objects()))
"

# 3. Optimize database queries
sqlite3 db/stockalerts.db "
.timer on
EXPLAIN QUERY PLAN SELECT * FROM watchlist_items w JOIN users u ON w.user_id = u.id;
"

# 4. Implement pagination for large datasets
# Modify db_manager.py methods to use LIMIT and OFFSET
```

#### Issue: Slow API responses
**Symptoms:**
- `/data/AAPL/5y` takes >10 seconds
- Frontend timeouts
- Poor user experience

**Solutions:**
```bash
# 1. Check cache hit rate
sqlite3 db/stockalerts.db "
SELECT 
    COUNT(*) as total_requests,
    SUM(CASE WHEN last_check > datetime('now', '-1 hour') THEN 1 ELSE 0 END) as cache_hits
FROM stock_cache;
"

# 2. Optimize database indexes
sqlite3 db/stockalerts.db "
CREATE INDEX IF NOT EXISTS idx_cache_symbol_time ON stock_cache(symbol, last_check);
ANALYZE;
"

# 3. Enable compression in nginx
# Add gzip configuration to nginx.conf

# 4. Monitor response times
tail -f logs/stock_alerts.log | grep "Successfully processed"
```

### Database Performance Issues

#### Issue: Database locks and timeouts
**Symptoms:**
```bash
sqlite3.OperationalError: database is locked
sqlite3.OperationalError: database timeout
```

**Solutions:**
```bash
# 1. Check for long-running transactions
# Add connection timeout monitoring to db_manager.py

# 2. Reduce connection timeout
# Edit db_manager.py:_get_connection() timeout parameter

# 3. Check database file integrity
sqlite3 db/stockalerts.db "PRAGMA integrity_check;"

# 4. Optimize database settings
sqlite3 db/stockalerts.db "
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
"

# 5. Consider PostgreSQL for high concurrency
# See DEPLOYMENT.md for PostgreSQL migration guide
```

---

## Security Issues

### SSL/TLS Problems

#### Issue: HTTPS certificate errors
**Symptoms:**
- Webhook failures with SSL errors
- Browser security warnings
- Certificate validation failures

**Solutions:**
```bash
# 1. Check certificate validity
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/fullchain.pem -text -noout

# 2. Test SSL configuration
curl -I https://yourdomain.com

# 3. Renew Let's Encrypt certificate
sudo certbot renew --dry-run
sudo certbot renew

# 4. Check nginx SSL configuration
sudo nginx -t
sudo systemctl reload nginx
```

#### Issue: Webhook security validation failing
**Symptoms:**
- 403 Forbidden errors on webhook
- Security token mismatches

**Solutions:**
```bash
# 1. Verify environment variables in production
sudo systemctl show stockalerts | grep Environment

# 2. Test HMAC validation logic
python -c "
import hmac
import hashlib
secret = b'your_secret'
data = b'test_data'
signature = hmac.new(secret, data, hashlib.sha256).hexdigest()
print('Test signature:', signature)
"

# 3. Check webhook handler validation logs
# Add debug logging to webhook_handler.py:validate_webhook()

# 4. Verify Telegram webhook configuration
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

---

## Data Issues

### Cache Problems

#### Issue: Stale data being served
**Symptoms:**
- Old stock prices displayed
- Cache not refreshing
- Inconsistent data

**Solutions:**
```bash
# 1. Check cache timestamps
sqlite3 db/stockalerts.db "
SELECT symbol, last_check, last_price,
       ROUND((julianday('now') - julianday(last_check)) * 24, 2) as hours_old
FROM stock_cache 
WHERE hours_old > 1
ORDER BY hours_old DESC;
"

# 2. Clear specific cache entries
sqlite3 db/stockalerts.db "DELETE FROM stock_cache WHERE symbol = 'AAPL';"

# 3. Check cache logic in app.py:calculate_metrics()
# Verify max_age_hours parameter usage

# 4. Force cache refresh
curl "http://localhost:5001/data/AAPL/5y?nocache=1"
```

#### Issue: Database corruption
**Symptoms:**
```bash
sqlite3.DatabaseError: database disk image is malformed
Data inconsistencies
```

**Solutions:**
```bash
# 1. Check database integrity
sqlite3 db/stockalerts.db "PRAGMA integrity_check;"

# 2. Repair database
sqlite3 db/stockalerts.db "
.clone backup_db.db
.quit
"
mv backup_db.db db/stockalerts.db

# 3. Restore from backup
cp /backup/stockalerts_latest.db db/stockalerts.db

# 4. Prevent future corruption
# Ensure proper shutdown procedures
# Monitor disk space
# Regular backups
```

---

## Log Analysis

### Understanding Log Messages

**Common log patterns and meanings:**

**Normal Operation:**
```bash
INFO - StockAlerts.App - Successfully processed AAPL with 1825 data points
INFO - StockAlerts.WebhookHandler - Message sent to chat_id 123456789
INFO - StockAlerts.DB - Added MSFT to watchlist for user 123456789
```

**Warning Conditions:**
```bash
WARNING - Rate limited on attempt 2 for TSLA. Waiting 4 seconds...
WARNING - Invalid cached data for GOOGL: JSON decode error
WARNING - No data returned from Yahoo Finance for INVALID_TICKER
```

**Error Conditions:**
```bash
ERROR - Failed to fetch data for AAPL: Request timeout
ERROR - Database error in add_to_watchlist: UNIQUE constraint failed
CRITICAL - FATAL: Error during initialization: No module named 'flask'
```

### Log Analysis Commands

```bash
# Check for errors in last 24 hours
grep "ERROR\|CRITICAL" logs/stock_alerts.log | tail -20

# Monitor rate limiting issues
grep "Rate limited" logs/stock_alerts.log | wc -l

# Check webhook activity
grep "Processing update" logs/stock_alerts.log | tail -10

# Database operation summary
grep "Database" logs/stock_alerts.log | cut -d'-' -f4- | sort | uniq -c
```

---

## Getting Help

### Information to Collect Before Reporting Issues

1. **System Information:**
   ```bash
   python --version
   uname -a
   df -h
   ```

2. **Application Logs:**
   ```bash
   tail -50 logs/stock_alerts.log
   ```

3. **Configuration:**
   ```bash
   ls -la .env  # (don't share contents!)
   sqlite3 db/stockalerts.db ".tables"
   ```

4. **Error Details:**
   - Exact error message
   - Steps to reproduce
   - Expected vs actual behavior
   - Timestamp of occurrence

### Emergency Recovery Procedures

**Service Down:**
```bash
# 1. Restart application service
sudo systemctl restart stockalerts

# 2. Check service status
sudo systemctl status stockalerts

# 3. If database is corrupted, restore from backup
cp /backup/stockalerts_latest.db db/stockalerts.db

# 4. Clear cache if needed
sqlite3 db/stockalerts.db "DELETE FROM stock_cache;"
```

**Complete System Recovery:**
```bash
# 1. Stop all services
sudo systemctl stop stockalerts nginx

# 2. Restore application code
git checkout HEAD -- .

# 3. Restore database
cp /backup/stockalerts_latest.db db/stockalerts.db

# 4. Restart services
sudo systemctl start stockalerts nginx
```

---

This troubleshooting guide covers the most common issues encountered with the Stock Alerts system. For additional support, check the application logs and provide specific error messages when seeking help.