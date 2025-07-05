# Production Deployment Guide

Comprehensive guide for deploying the Stock Alerts application to production environments. For local development setup, see [SETUP.md](./SETUP.md).

## 🏗️ Supported Platforms

The application is configured for deployment on multiple platforms with automatic build detection and PostgreSQL support:

- **Railway** - Primary target with [`railway.json`](../railway.json) configuration
- **Heroku** - Classic PaaS with [`Procfile`](../Procfile) support
- **Docker** - Containerized deployment (manual setup)
- **Self-hosted** - VPS/dedicated servers with systemd or similar

## 🚀 Quick Deploy: Railway

**Recommended Platform** - Zero-config deployment with automatic PostgreSQL provisioning.

### Railway Configuration
**Build System:** [`railway.json`](../railway.json) configures Nixpacks auto-detection

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn --bind 0.0.0.0:$PORT --timeout 300 --workers 1 app:app",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### Railway Deployment Steps

1. **Connect Repository**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login and connect
   railway login
   railway link
   ```

2. **Add PostgreSQL Database**
   ```bash
   railway add postgresql
   ```

3. **Configure Environment Variables**
   ```bash
   # Set required variables
   railway variables set TELEGRAM_BOT_TOKEN=your_bot_token
   railway variables set TIINGO_API_TOKEN=your_tiingo_token
   railway variables set ADMIN_API_KEY=your_admin_key
   ```

4. **Deploy**
   ```bash
   railway deploy
   ```

### Railway Features
- **Automatic SSL**: HTTPS enabled by default
- **Database Backups**: Automatic PostgreSQL backups
- **Logging**: Centralized log aggregation
- **Metrics**: Built-in performance monitoring
- **Zero Downtime**: Rolling deployments

---

## 🔥 Deploy: Heroku

**Classic PaaS** - Procfile-based deployment with add-on ecosystem.

### Heroku Configuration
**Process Definition:** [`Procfile`](../Procfile)

```
web: gunicorn --bind 0.0.0.0:$PORT app:app
```

### Heroku Deployment Steps

1. **Create Application**
   ```bash
   # Install Heroku CLI and login
   heroku create your-app-name
   ```

2. **Add PostgreSQL**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

3. **Configure Variables**
   ```bash
   heroku config:set TELEGRAM_BOT_TOKEN=your_bot_token
   heroku config:set TIINGO_API_TOKEN=your_tiingo_token
   heroku config:set ADMIN_API_KEY=your_admin_key
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

### Heroku Add-ons
- **Heroku Postgres**: Managed PostgreSQL database
- **Papertrail**: Log management and search
- **New Relic**: Application performance monitoring
- **Heroku Scheduler**: Alternative to internal APScheduler

---

## 🐳 Deploy: Docker

**Containerized Deployment** - For Kubernetes, Docker Swarm, or standalone containers.

### Dockerfile Creation
Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash stockalerts
USER stockalerts

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

# Start application
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--timeout", "300", "--workers", "1", "app:app"]
```

### Docker Compose Setup
Create `docker-compose.yml` for development/testing:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5001:5001"
    environment:
      - DATABASE_URL=postgresql://stockalerts:password@db:5432/stockalerts
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TIINGO_API_TOKEN=${TIINGO_API_TOKEN}
      - ADMIN_API_KEY=${ADMIN_API_KEY}
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=stockalerts
      - POSTGRES_USER=stockalerts
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### Docker Deployment Commands

```bash
# Build and run locally
docker-compose up --build

# Production build
docker build -t stock-alerts .
docker run -d \
  --name stock-alerts \
  -p 5001:5001 \
  -e DATABASE_URL="your_postgres_url" \
  -e TELEGRAM_BOT_TOKEN="your_bot_token" \
  stock-alerts
```

---

## 🖥️ Self-Hosted Deployment

**VPS/Dedicated Server** - Full control with manual configuration.

### System Requirements
- **OS**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **RAM**: 512MB minimum, 1GB recommended
- **Storage**: 2GB minimum, 10GB recommended
- **Python**: 3.9+ with pip and venv
- **Database**: PostgreSQL 12+
- **Web Server**: Nginx (recommended) or Apache

### Manual Installation Steps

1. **System Setup**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3 python3-venv python3-pip postgresql nginx
   
   # CentOS/RHEL
   sudo dnf install python3 python3-pip postgresql-server nginx
   ```

2. **Database Setup**
   ```bash
   sudo -u postgres createuser stockalerts
   sudo -u postgres createdb stockalerts -O stockalerts
   sudo -u postgres psql -c "ALTER USER stockalerts PASSWORD 'secure_password';"
   ```

3. **Application Deployment**
   ```bash
   # Create application directory
   sudo mkdir -p /opt/stock-alerts
   sudo chown $USER:$USER /opt/stock-alerts
   cd /opt/stock-alerts
   
   # Clone and setup
   git clone <repository-url> .
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   # Create production environment file
   cat > .env << EOF
   DATABASE_URL=postgresql://stockalerts:secure_password@localhost:5432/stockalerts
   TELEGRAM_BOT_TOKEN=your_bot_token
   TIINGO_API_TOKEN=your_tiingo_token
   ADMIN_API_KEY=your_admin_key
   PORT=5001
   DEBUG=False
   EOF
   ```

5. **Systemd Service Setup**
   ```bash
   sudo cat > /etc/systemd/system/stock-alerts.service << EOF
   [Unit]
   Description=Stock Alerts Application
   After=network.target postgresql.service
   
   [Service]
   Type=exec
   User=stockalerts
   Group=stockalerts
   WorkingDirectory=/opt/stock-alerts
   Environment=PATH=/opt/stock-alerts/venv/bin
   ExecStart=/opt/stock-alerts/venv/bin/gunicorn --bind 127.0.0.1:5001 --timeout 300 --workers 2 app:app
   Restart=always
   RestartSec=3
   
   [Install]
   WantedBy=multi-user.target
   EOF
   
   sudo systemctl enable stock-alerts
   sudo systemctl start stock-alerts
   ```

6. **Nginx Reverse Proxy**
   ```nginx
   # /etc/nginx/sites-available/stock-alerts
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:5001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

7. **SSL Certificate (Let's Encrypt)**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

## 🔐 Environment Configuration

Production environment variables must be configured through your platform's settings panel. **Never commit production secrets to version control.**

### Required Variables
These environment variables are **mandatory** for production deployment:

| Variable | Description | Example | Source |
|----------|-------------|---------|--------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` | Platform-provided |
| `TELEGRAM_BOT_TOKEN` | Bot authentication token | `123456:ABC-DEF...` | [@BotFather](https://t.me/BotFather) |
| `TIINGO_API_TOKEN` | Stock data API key | `abc123...` | [tiingo.com](https://tiingo.com) |

### Security Variables
These variables secure admin endpoints and webhooks:

| Variable | Description | Generation Method | Required |
|----------|-------------|------------------|----------|
| `TELEGRAM_WEBHOOK_SECRET` | Webhook validation token | [`setup_webhook.py`](../setup_webhook.py) | ⚠️ Recommended |
| `ADMIN_API_KEY` | Admin endpoint protection | `openssl rand -hex 32` | ⚠️ Recommended |
| `ADMIN_USERNAME` | Admin panel username | Custom choice | ❌ Optional |
| `ADMIN_PASSWORD` | Admin panel password | Strong password | ❌ Optional |

### Application Settings
Optional configuration with sensible defaults:

| Variable | Default | Description | Valid Values |
|----------|---------|-------------|---------------|
| `PORT` | `5001` | Application port | Any valid port |
| `DEBUG` | `False` | Debug mode | `True`/`False` |
| `CACHE_HOURS` | `1` | Stock data cache TTL | Integer hours |
| `YF_REQUEST_DELAY` | `3.0` | API request delay | Float seconds |

### Configuration Loading
All variables are loaded and validated by [`utils/config.py:Config`](../utils/config.py):

```python
# Automatic validation on startup
config = Config()  # Validates required variables
config.get_config_summary()  # Logs status without exposing secrets
```

### Platform-Specific Setup

**Railway:**
```bash
railway variables set TELEGRAM_BOT_TOKEN=your_token
railway variables set TIINGO_API_TOKEN=your_token
```

**Heroku:**
```bash
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set TIINGO_API_TOKEN=your_token
```

**Docker:**
```bash
docker run -e TELEGRAM_BOT_TOKEN=your_token stock-alerts
```

**Self-hosted:**
```bash
# Create .env file (see SETUP.md for template)
echo "TELEGRAM_BOT_TOKEN=your_token" >> .env
```

## 📋 Database Setup

The application requires PostgreSQL and handles schema management automatically.

### Database Provisioning

**Platform-Managed (Recommended):**
- **Railway**: Automatic PostgreSQL with `railway add postgresql`
- **Heroku**: `heroku addons:create heroku-postgresql:mini`
- **AWS RDS**: Managed PostgreSQL instance
- **Google Cloud SQL**: Cloud PostgreSQL service

**Self-Hosted:**
```bash
# Ubuntu/Debian
sudo apt install postgresql
sudo -u postgres createdb stockalerts

# Create application user
sudo -u postgres createuser stockalerts
sudo -u postgres psql -c "ALTER USER stockalerts PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE stockalerts TO stockalerts;"
```

### Automatic Migration System

**Migration Management:** [`db_manager.py:initialize_database()`](../db_manager.py)

On application startup:
1. **Connection Check**: Validates `DATABASE_URL` connectivity
2. **Migration Tracking**: Creates/checks `migrations` table
3. **Schema Application**: Applies pending SQL files from [`migrations/`](../migrations/)
4. **Idempotent Operation**: Safe to run multiple times

**Migration Files:**
- [`migrations/000_migrations_table.sql`](../migrations/000_migrations_table.sql) - Migration tracking
- [`migrations/001_initial.sql`](../migrations/001_initial.sql) - Core schema (users, watchlists, cache, etc.)

### Database Connection Pooling

**Implementation:** [`db_manager.py:DatabaseManager`](../db_manager.py)
- **Connection Pool**: `psycopg2.pool.SimpleConnectionPool`
- **Pool Size**: 1-20 connections (configurable)
- **Connection Management**: Automatic acquisition/release
- **Error Handling**: Graceful connection failure recovery

```python
# Automatic connection pooling
with self._managed_cursor(commit=True) as cursor:
    cursor.execute("SELECT * FROM users")  # Connection handled automatically
```

### Database Schema Overview

**Core Tables:**
```sql
-- User management
users (id, name, joined_at, notification_enabled, max_stocks)

-- Stock watchlists  
watchlist_items (user_id, symbol, alert_threshold_low, alert_threshold_high)

-- API response caching
stock_cache (symbol, last_check, last_price, ma_200, data_json)

-- Alert audit trail
alert_history (user_id, symbol, price, percentile, status, sent_at)

-- Application logs
logs (timestamp, log_type, message, user_id, symbol)

-- Configuration storage
config (key, value)
```

### Production Database Considerations

**Performance:**
- **Indexes**: Automatically created for common query patterns
- **Constraints**: Data validation at database level
- **Efficient Queries**: All queries use indexes and proper joins

**Security:**
- **Parameterized Queries**: No SQL injection vulnerabilities
- **Limited Permissions**: Application user has only necessary privileges
- **Connection Encryption**: SSL/TLS for production connections

**Monitoring:**
- **Health Checks**: `/health` endpoint tests database connectivity
- **Error Logging**: Database errors logged to application logs
- **Connection Status**: Pool status available in admin panel

## 🤖 Telegram Bot Configuration

Configure Telegram webhook to enable bot functionality in production.

### Webhook Requirements

**Telegram Requirements:**
- **HTTPS Only**: Telegram requires SSL/TLS encrypted webhooks
- **Valid Certificate**: Self-signed certificates not supported
- **Public URL**: No localhost or private IP addresses
- **Port Restrictions**: Standard HTTPS ports (443, 8443, etc.)

### Webhook Setup Process

#### Step 1: Get Application URL
Obtain your deployed application's public HTTPS URL:

```bash
# Railway
railway status  # Shows deployment URL

# Heroku
heroku info  # Shows web URL

# Custom domain
https://yourdomain.com
```

#### Step 2: Configure Webhook

**Method 1: Automated Setup (Recommended)**

Use the included [`setup_webhook.py`](../setup_webhook.py) utility:

```bash
# Set bot token locally
export TELEGRAM_BOT_TOKEN=your_bot_token

# Run interactive setup
python setup_webhook.py
```

**Script Features:**
- **Interactive Prompts**: Guides through URL and secret configuration
- **Security Token Generation**: Creates cryptographically secure webhook secrets
- **Validation**: Verifies webhook URL format and accessibility
- **Error Handling**: Clear error messages for common issues

**Method 2: Manual API Call**

```bash
# Set webhook with secret token
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://your-app.railway.app/webhook\",
    \"secret_token\": \"your_webhook_secret\"
  }"
```

#### Step 3: Verify Webhook

```bash
# Check webhook status
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"

# Expected response
{
  "ok": true,
  "result": {
    "url": "https://your-app.railway.app/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "last_error_date": null
  }
}
```

### Webhook Security Implementation

**Security Features:** [`webhook_handler.py:validate_webhook()`](../webhook_handler.py)

1. **HMAC Validation**: Timing-safe comparison of secret tokens
2. **JSON Validation**: Verifies Telegram update structure
3. **Request Logging**: Security events logged for monitoring
4. **Error Handling**: Graceful handling of malformed requests

```python
# Webhook validation process
def validate_webhook(self, request_data: bytes, secret_token_header: Optional[str]) -> bool:
    # 1. Validate secret token with timing-safe comparison
    if not hmac.compare_digest(self.secret_token, secret_token_header):
        return False
    
    # 2. Validate JSON structure and required fields
    data = json.loads(request_data)
    if "update_id" not in data:
        return False
        
    return True
```

### Bot Testing & Debugging

**Test Bot Functionality:**
```bash
# Send test message to verify webhook
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{
    \"chat_id\": \"your_user_id\",
    \"text\": \"Webhook test message\"
  }"
```

**Common Issues & Solutions:**

| Issue | Cause | Solution |
|-------|-------|----------|
| "Webhook validation failed" | Invalid secret token | Regenerate token with `setup_webhook.py` |
| "Connection refused" | App not responding | Check application logs and health endpoint |
| "SSL certificate verify failed" | Invalid certificate | Ensure platform provides valid SSL |
| "Bot not responding to commands" | Webhook not set | Run `getWebhookInfo` to verify setup |

### Webhook URL Format

**Correct Format:**
```
https://your-domain.com/webhook
```

**Supported Platforms:**
- Railway: `https://your-app.up.railway.app/webhook`
- Heroku: `https://your-app.herokuapp.com/webhook`
- Custom Domain: `https://yourdomain.com/webhook`

**Important Notes:**
- Webhook URL must be **publicly accessible**
- **HTTPS is mandatory** (no HTTP allowed)
- URL must respond to **POST requests**
- Response should be **200 OK** for successful processing

## ⏰ Background Task Scheduling

Automated stock alert checking using built-in APScheduler - no external cron jobs required.

### Scheduler Architecture

**Implementation:** [`utils/scheduler.py:setup_scheduler()`](../utils/scheduler.py)  
**Background Process:** [`periodic_checker.py:PeriodicChecker`](../periodic_checker.py)  
**Initialization:** Automatic startup in [`app.py`](../app.py)

### Default Schedule Configuration

```python
# Daily execution at 1 AM UTC
scheduler.add_job(
    func=scheduled_stock_check,
    trigger=CronTrigger(hour=1, minute=0, timezone=pytz.UTC),
    id="stock_check",
    name="Daily Stock Check",
    replace_existing=True,
)
```

**Schedule Details:**
- **Frequency**: Daily
- **Time**: 1:00 AM UTC
- **Timezone**: UTC for consistency across deployments
- **Execution**: Background thread, non-blocking

### Background Task Flow

1. **Scheduler Trigger**: APScheduler executes `scheduled_stock_check()`
2. **Process Creation**: [`periodic_checker.py:PeriodicChecker`](../periodic_checker.py) instance created
3. **Watchlist Processing**: `check_watchlists()` fetches all active user watchlists
4. **Data Analysis**: Stock data retrieved and analyzed for alert conditions
5. **Alert Dispatch**: Telegram notifications sent for triggered alerts
6. **Audit Logging**: All activities logged to database and files

### Platform Compatibility

**Supported Platforms:**
- ✅ **Railway**: Full background task support
- ✅ **Heroku**: Supports with standard dynos
- ✅ **Docker**: Works in containerized environments
- ✅ **Self-hosted**: Full functionality

**Platform Requirements:**
- Long-running process support
- Background thread execution
- Persistent memory between tasks
- No forced process restarts during execution

### Alternative Scheduling Options

For platforms with limitations or custom requirements:

#### External Cron Job

Disable internal scheduler and use external cron:

```bash
# Disable APScheduler in production
export DISABLE_SCHEDULER=true

# Add to crontab (daily at 1 AM UTC)
0 1 * * * curl -X POST https://your-app.com/admin/check \
  -H "X-API-Key: ${ADMIN_API_KEY}"
```

#### GitHub Actions

Scheduled workflow for external triggering:

```yaml
# .github/workflows/stock-check.yml
name: Daily Stock Check
on:
  schedule:
    - cron: '0 1 * * *'  # 1 AM UTC daily
    
jobs:
  stock-check:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger stock check
        run: |
          curl -X POST ${{ secrets.APP_URL }}/admin/check \
            -H "X-API-Key: ${{ secrets.ADMIN_API_KEY }}"
```

#### Platform-Specific Schedulers

**Heroku Scheduler:**
```bash
# Add Heroku Scheduler add-on
heroku addons:create scheduler:standard

# Schedule daily job
heroku addons:open scheduler
# Add job: curl -X POST $APP_URL/admin/check -H "X-API-Key: $ADMIN_API_KEY"
```

**AWS EventBridge:**
```json
{
  "ScheduleExpression": "cron(0 1 * * ? *)",
  "Target": {
    "Arn": "your-api-gateway-arn",
    "HttpParameters": {
      "HeaderParameters": {
        "X-API-Key": "your-admin-api-key"
      }
    }
  }
}
```

### Monitoring & Debugging

**Health Monitoring:**
```bash
# Check scheduler status via admin panel
curl -u admin:password https://your-app.com/admin

# Manual trigger for testing
curl -X POST https://your-app.com/admin/check \
  -H "X-API-Key: your_admin_api_key"
```

**Log Analysis:**
```bash
# Application logs contain scheduler information
[INFO] APScheduler started successfully - daily stock checks scheduled for 1 AM UTC
[INFO] Starting scheduled stock check...
[INFO] Scheduled stock check completed successfully
```

**Error Handling:**
- **Exception Recovery**: Scheduler continues running after individual job failures
- **Retry Logic**: Failed jobs logged but don't stop future executions
- **Graceful Shutdown**: Scheduler stops cleanly on application termination

### Performance Considerations

**Resource Usage:**
- **Memory**: Background scheduler uses minimal memory
- **CPU**: Alert processing is CPU-light
- **Database**: Connection pooling handles concurrent operations
- **API Limits**: Built-in rate limiting respects Tiingo API constraints

**Scaling:**
- **Single Instance**: Scheduler only runs on one application instance
- **Multiple Instances**: Use external scheduling to avoid duplicate runs
- **High Availability**: Manual trigger endpoint provides backup execution path

---

## 🗺️ Post-Deployment Checklist

### Essential Verification Steps

1. **Application Health**
   ```bash
   curl https://your-app.com/health
   # Expected: {"status": "healthy"}
   ```

2. **Database Connectivity**
   ```bash
   # Check admin panel loads
   curl -u admin:password https://your-app.com/admin
   ```

3. **API Endpoints**
   ```bash
   # Test stock data endpoint
   curl https://your-app.com/data/AAPL/1y
   ```

4. **Telegram Webhook**
   ```bash
   curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
   ```

5. **Background Scheduler**
   ```bash
   # Manual trigger test
   curl -X POST https://your-app.com/admin/check \
     -H "X-API-Key: your_admin_api_key"
   ```

### Security Verification

- **Environment Variables**: All sensitive data in environment, not code
- **HTTPS**: All endpoints accessible via HTTPS only
- **Admin Authentication**: Admin panel requires valid credentials
- **API Key Protection**: Admin endpoints require valid API key
- **Webhook Security**: Telegram webhook validates secret token

### Performance Optimization

**Database:**
- Connection pooling enabled
- Indexes created for common queries
- Cache TTL configured appropriately

**Application:**
- Gunicorn workers configured for platform
- Request timeout settings appropriate
- Static file serving optimized

**Monitoring:**
- Application logs centralized
- Error tracking configured
- Health checks automated

---

## 🛠️ Troubleshooting

For comprehensive troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

### Common Deployment Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| App won't start | 503/502 errors | Check environment variables and logs |
| Database connection failed | 500 errors on API calls | Verify `DATABASE_URL` format and connectivity |
| Telegram bot not responding | Commands ignored | Check webhook configuration and logs |
| Stock data not loading | Empty charts, API errors | Verify `TIINGO_API_TOKEN` validity |
| Admin panel inaccessible | 401 authentication errors | Check `ADMIN_USERNAME`/`ADMIN_PASSWORD` |

### Platform-Specific Help

**Railway:**
- Logs: `railway logs`
- Environment: `railway variables`
- Status: `railway status`

**Heroku:**
- Logs: `heroku logs --tail`
- Config: `heroku config`
- Status: `heroku ps`

**Docker:**
- Logs: `docker logs container_name`
- Environment: `docker inspect container_name`
- Status: `docker ps`

---

**Next Steps:** After successful deployment, see [API.md](./API.md) for endpoint documentation or [ARCHITECTURE.md](./ARCHITECTURE.md) for system understanding.