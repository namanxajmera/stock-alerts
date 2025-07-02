# Complete Setup Guide

Comprehensive installation and configuration guide for the Stock Analytics Dashboard & Telegram Alert system.

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 512MB RAM (1GB+ recommended)
- **Storage**: 100MB for application, additional space for database growth
- **Network**: Internet connection for Yahoo Finance API and Telegram

### External Services
- **Telegram Account**: Required for bot creation and webhook setup
- **Public URL**: Required for production Telegram webhook (ngrok for development)

## Installation

### 1. Environment Setup

#### Option A: Using Virtual Environment (Recommended)
```bash
# Clone the repository
git clone <repository-url>
cd stock-alerts

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Verify Python version
python --version  # Should be 3.8+
```

#### Option B: Using System Python
```bash
# Ensure Python 3.8+ is installed
python3 --version

# Clone repository
git clone <repository-url>
cd stock-alerts
```

### 2. Dependency Installation

Install required Python packages from [`requirements.txt`](./requirements.txt):

```bash
pip install -r requirements.txt
```

**Core Dependencies Installed:**
- `flask` - Web framework ([`app.py:15`](./app.py#L15))
- `yfinance` - Yahoo Finance data ([`app.py:17`](./app.py#L17))
- `pandas`, `numpy` - Data processing ([`app.py:19-20`](./app.py#L19-20))
- `requests` - HTTP client for Telegram API ([`webhook_handler.py:8`](./webhook_handler.py#L8))
- `python-dotenv` - Environment variable management ([`app.py:2`](./app.py#L2))

### 3. Directory Structure Verification

The application automatically creates necessary directories via [`app.py:setup_directories()`](./app.py#L7-12):

```bash
# Verify directory structure
ls -la
# Should show:
# - app.py (main application)
# - db_manager.py (database layer)
# - webhook_handler.py (Telegram bot)
# - requirements.txt (dependencies)
# - static/ (frontend assets)
# - templates/ (HTML templates)
# - migrations/ (database schema)
```

## Telegram Bot Configuration

### 1. Create Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. **Start conversation** and send `/newbot`
3. **Follow prompts** to create your bot:
   ```
   BotFather: Alright, a new bot. How are we going to call it?
   You: Stock Alerts Bot
   
   BotFather: Good. Now let's choose a username for your bot.
   You: your_unique_bot_name_bot
   ```
4. **Save the token** provided by BotFather (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Generate Webhook Secret

Create a secure secret for webhook validation:

```bash
# Generate a secure 64-character hex string
python -c "import secrets; print(secrets.token_hex(32))"
# Example output: a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

### 3. Environment Configuration

Create environment file from template:

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` file with your configuration:

```bash
# .env file contents
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_SECRET=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456

# Optional configurations
PORT=5001                    # Flask server port (default: 5001)
```

**Environment Variables Explained:**
- `TELEGRAM_BOT_TOKEN`: Bot token from BotFather (used in [`webhook_handler.py:16`](./webhook_handler.py#L16))
- `TELEGRAM_WEBHOOK_SECRET`: HMAC secret for webhook validation (used in [`webhook_handler.py:17`](./webhook_handler.py#L17))
- `PORT`: Web server port (used in [`app.py:272`](./app.py#L272))

## Database Setup

### Automatic Initialization

The database automatically initializes on first run via [`db_manager.py:initialize_database()`](./db_manager.py#L44-95):

1. **Creates SQLite database** at `db/stockalerts.db`
2. **Runs migrations** from [`migrations/`](./migrations/) directory
3. **Sets up tables** as defined in [`migrations/001_initial.sql`](./migrations/001_initial.sql)
4. **Creates indexes** for optimal performance

### Manual Database Verification

```bash
# Start the application to trigger database creation
python app.py

# Verify database creation
ls -la db/
# Should show: stockalerts.db

# Check database tables (optional)
sqlite3 db/stockalerts.db ".tables"
# Should show: users, watchlist_items, stock_cache, alert_history, logs, config, migrations
```

### Database Schema Overview

The schema includes the following tables created by [`migrations/001_initial.sql`](./migrations/001_initial.sql):

- **`users`**: Telegram user profiles ([Line 4-16](./migrations/001_initial.sql#L4-16))
- **`watchlist_items`**: User stock watchlists ([Line 22-36](./migrations/001_initial.sql#L22-36))
- **`stock_cache`**: Cached stock data ([Line 43-50](./migrations/001_initial.sql#L43-50))
- **`alert_history`**: Alert audit trail ([Line 56-67](./migrations/001_initial.sql#L56-67))
- **`config`**: Application configuration ([Line 75-82](./migrations/001_initial.sql#L75-82))
- **`logs`**: Event logging ([Line 93-101](./migrations/001_initial.sql#L93-101))

## Application Testing

### 1. Local Development Server

Start the Flask development server:

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Start the application
python app.py
```

**Expected Output:**
```
INFO - StockAlerts.App - Initializing database manager and webhook handler...
INFO - StockAlerts.DB - Database initialization complete
INFO - StockAlerts.App - Flask app initialized with CORS.
INFO - StockAlerts.WebhookHandler - Webhook handler initialized
INFO - StockAlerts.App - Starting Stock Analytics Dashboard server on port 5001...
```

### 2. Web Interface Testing

**Access Dashboard:**
1. Open browser to `http://localhost:5001`
2. Verify the interface loads (based on [`templates/index.html`](./templates/index.html))
3. Test stock lookup (try "AAPL" in 5Y period)
4. Verify charts render using Plotly.js

**API Testing:**
```bash
# Test health endpoint
curl http://localhost:5001/health
# Expected: {"status": "healthy"}

# Test stock data endpoint
curl http://localhost:5001/data/AAPL/5y
# Expected: JSON with dates, prices, ma_200, pct_diff, percentiles
```

## Telegram Webhook Setup

### Development Setup (ngrok)

For local development, use ngrok to expose your local server:

#### 1. Install ngrok
```bash
# Visit https://ngrok.com/download and install
# Or use package manager:
# macOS: brew install ngrok
# Linux: snap install ngrok
```

#### 2. Expose Local Server
```bash
# In a separate terminal, expose port 5001
ngrok http 5001

# ngrok will display:
# Forwarding: https://abc123.ngrok.io -> http://localhost:5001
```

#### 3. Set Telegram Webhook
```bash
# Replace placeholders with your values:
# <NGROK_URL>: The https URL from ngrok (e.g., https://abc123.ngrok.io)
# <BOT_TOKEN>: Your bot token from BotFather
# <WEBHOOK_SECRET>: Your generated webhook secret

curl -F "url=<NGROK_URL>/webhook" \
     -F "secret_token=<WEBHOOK_SECRET>" \
     "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook"
```

**Example:**
```bash
curl -F "url=https://abc123.ngrok.io/webhook" \
     -F "secret_token=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456" \
     "https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/setWebhook"
```

**Expected Response:**
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

### Production Setup

For production, replace ngrok URL with your actual domain:

```bash
curl -F "url=https://yourdomain.com/webhook" \
     -F "secret_token=<WEBHOOK_SECRET>" \
     "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook"
```

## Bot Testing

### 1. Basic Bot Commands

Test each command implemented in [`webhook_handler.py`](./webhook_handler.py):

1. **Start Bot:**
   - Send `/start` to your bot
   - Expected: Welcome message with command list ([`webhook_handler.py:_get_welcome_message()`](./webhook_handler.py#L103))

2. **Add Stocks:**
   - Send `/add AAPL MSFT`
   - Expected: Confirmation message ([`webhook_handler.py:_handle_add_command()`](./webhook_handler.py#L177))

3. **List Watchlist:**
   - Send `/list`
   - Expected: Current watchlist display ([`webhook_handler.py:_handle_list_command()`](./webhook_handler.py#L164))

4. **Remove Stocks:**
   - Send `/remove AAPL`
   - Expected: Removal confirmation ([`webhook_handler.py:_handle_remove_command()`](./webhook_handler.py#L199))

### 2. Webhook Validation

Check webhook processing in application logs:

```bash
# Monitor application logs for webhook requests
tail -f logs/stock_alerts.log

# Send a message to your bot and verify logs show:
# INFO - StockAlerts.WebhookHandler - Processing update ID: 123456789
# INFO - StockAlerts.WebhookHandler - Processing message from user username (123456789)
```

## Periodic Alert Setup

### 1. Manual Testing

Test the periodic checker manually:

```bash
# Run periodic checker once
python periodic_checker.py
```

**Expected Behavior:**
- Fetches active watchlists from database ([`periodic_checker.py:check_watchlists()`](./periodic_checker.py#L23))
- Groups users by symbol for efficient processing
- Fetches stock data with retry logic ([`periodic_checker.py:_fetch_symbol_data_with_retry()`](./periodic_checker.py#L51))
- Triggers alerts if thresholds are met

### 2. Automated Scheduling

Set up periodic execution using cron (Linux/macOS) or Task Scheduler (Windows):

#### Linux/macOS Cron Setup
```bash
# Edit crontab
crontab -e

# Add entry to run daily at 6 PM (adjust path to your installation)
0 18 * * * cd /path/to/stock-alerts && /path/to/venv/bin/python periodic_checker.py

# Example with full paths:
0 18 * * * cd /home/user/stock-alerts && /home/user/stock-alerts/venv/bin/python periodic_checker.py
```

#### Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., Daily at 6:00 PM)
4. Set action: Start Program
   - Program: `C:\Path\To\Python\python.exe`
   - Arguments: `periodic_checker.py`
   - Start in: `C:\Path\To\stock-alerts`

## Configuration Tuning

### Application Settings

Modify configuration via the database `config` table (initialized in [`migrations/001_initial.sql:85-90`](./migrations/001_initial.sql#L85-90)):

```sql
-- Connect to database
sqlite3 db/stockalerts.db

-- View current configuration
SELECT * FROM config;

-- Update cache duration (default: 24 hours)
UPDATE config SET value = '12' WHERE key = 'cache_duration_hours';

-- Update max stocks per user (default: 20)
UPDATE config SET value = '50' WHERE key = 'max_stocks_per_user';

-- Update alert thresholds (default: 5.0 and 95.0)
UPDATE config SET value = '10.0' WHERE key = 'default_threshold_low';
UPDATE config SET value = '90.0' WHERE key = 'default_threshold_high';
```

### Performance Tuning

**Database Optimization:**
- **Vacuum Database**: `sqlite3 db/stockalerts.db "VACUUM;"`
- **Analyze Statistics**: `sqlite3 db/stockalerts.db "ANALYZE;"`
- **Monitor Size**: `ls -lh db/stockalerts.db`

**Cache Management:**
- **Clear Old Cache**: Automatic via [`db_manager.py:get_fresh_cache()`](./db_manager.py#L247) TTL
- **Manual Clear**: `DELETE FROM stock_cache WHERE datetime(last_check) < datetime('now', '-24 hours');`

## Troubleshooting Setup Issues

### Common Issues

#### 1. Database Permission Errors
```bash
# Issue: Permission denied when creating database
# Solution: Ensure write permissions
chmod 755 db/
chown user:user db/
```

#### 2. Python Version Conflicts
```bash
# Issue: Using wrong Python version
# Solution: Use explicit Python 3.8+
python3.8 -m venv venv
source venv/bin/activate
python --version  # Verify version
```

#### 3. Telegram Webhook Failures
```bash
# Issue: Webhook not receiving updates
# Solution: Verify webhook URL and secret

# Check current webhook
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"

# Clear webhook if needed
curl -F "url=" "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook"
```

#### 4. Module Import Errors
```bash
# Issue: ImportError for required modules
# Solution: Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Verification Checklist

- [ ] Python 3.8+ installed and activated
- [ ] All dependencies installed via `pip install -r requirements.txt`
- [ ] Environment variables configured in `.env` file
- [ ] Database created and migrated (check `db/stockalerts.db` exists)
- [ ] Web server starts without errors (`python app.py`)
- [ ] Health endpoint responds (`curl localhost:5001/health`)
- [ ] Telegram bot created and token obtained
- [ ] Webhook URL set and verified
- [ ] Bot responds to `/start` command
- [ ] Stock data API works (`/data/AAPL/5y`)
- [ ] Periodic checker runs without errors

## Next Steps

After successful setup:

1. **Read [DEPLOYMENT.md](./DEPLOYMENT.md)** for production deployment
2. **Review [API.md](./API.md)** for detailed API documentation
3. **Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** for common issues
4. **Monitor logs** in `logs/stock_alerts.log` for ongoing operation

## Security Considerations

### Development Environment
- **Environment Files**: Never commit `.env` files to version control
- **Log Files**: Regularly rotate and secure log files
- **Database**: Backup database regularly

### Production Environment
- **HTTPS Only**: Always use HTTPS for webhook URLs
- **Secret Rotation**: Regularly rotate webhook secrets
- **Access Control**: Limit file system permissions
- **Monitoring**: Set up log monitoring and alerting

---

Your Stock Alerts system is now ready for operation! 🚀