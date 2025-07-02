# Production Deployment Guide

Comprehensive guide for deploying the Stock Analytics Dashboard & Telegram Alert system to production environments.

## Pre-Deployment Checklist

### System Requirements

**Hardware Requirements:**
- **CPU**: 1+ cores (2+ recommended for production load)
- **RAM**: 1GB minimum (2GB+ recommended)
- **Storage**: 1GB for application + database growth space
- **Network**: Stable internet connection with HTTPS capability

**Software Requirements:**
- **Operating System**: Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- **Python**: 3.8 or higher
- **Process Manager**: systemd, supervisor, or PM2
- **Reverse Proxy**: nginx or Apache (recommended)
- **SSL Certificate**: Let's Encrypt or commercial certificate

### Security Preparation

**Environment Secrets:**
- [ ] Generate secure `TELEGRAM_WEBHOOK_SECRET` (64+ character hex string)
- [ ] Obtain production `TELEGRAM_BOT_TOKEN` from @BotFather
- [ ] Configure firewall rules (ports 80, 443, SSH only)
- [ ] Set up SSL/TLS certificates for HTTPS

**Access Control:**
- [ ] Create dedicated application user (non-root)
- [ ] Configure SSH key-based authentication
- [ ] Disable password authentication
- [ ] Set up log rotation and monitoring

---

## Deployment Options

### Option 1: Traditional Server Deployment

#### 1. Server Setup

**Create Application User:**
```bash
# Create dedicated user for the application
sudo adduser stockalerts
sudo usermod -aG sudo stockalerts

# Switch to application user
sudo su - stockalerts
```

**Install System Dependencies:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.8 python3.8-venv python3-pip nginx sqlite3 supervisor

# CentOS/RHEL
sudo yum update
sudo yum install -y python38 python38-devel nginx sqlite supervisor
```

#### 2. Application Deployment

**Deploy Application Code:**
```bash
# Clone repository to production location
cd /opt
sudo git clone <repository-url> stockalerts
sudo chown -R stockalerts:stockalerts stockalerts
cd stockalerts

# Create virtual environment
python3.8 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install production WSGI server
pip install gunicorn
```

**Configure Environment:**
```bash
# Create production environment file
cat > .env << EOF
TELEGRAM_BOT_TOKEN=your_production_bot_token
TELEGRAM_WEBHOOK_SECRET=your_secure_webhook_secret_64_chars_minimum
PORT=5001
EOF

# Set secure permissions
chmod 600 .env
```

**Initialize Database:**
```bash
# Test application startup
python app.py
# Verify database creation at db/stockalerts.db
# Stop with Ctrl+C
```

#### 3. Process Management with Systemd

**Create Service File:**
```bash
sudo tee /etc/systemd/system/stockalerts.service << EOF
[Unit]
Description=Stock Alerts Web Application
After=network.target

[Service]
Type=exec
User=stockalerts
Group=stockalerts
WorkingDirectory=/opt/stockalerts
Environment=PATH=/opt/stockalerts/venv/bin
ExecStart=/opt/stockalerts/venv/bin/gunicorn --bind 127.0.0.1:5001 --workers 2 app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

**Enable and Start Service:**
```bash
# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable stockalerts
sudo systemctl start stockalerts

# Check service status
sudo systemctl status stockalerts

# View logs
sudo journalctl -u stockalerts -f
```

#### 4. Periodic Checker Service

**Create Periodic Checker Service:**
```bash
sudo tee /etc/systemd/system/stockalerts-checker.service << EOF
[Unit]
Description=Stock Alerts Periodic Checker
After=network.target

[Service]
Type=oneshot
User=stockalerts
Group=stockalerts
WorkingDirectory=/opt/stockalerts
Environment=PATH=/opt/stockalerts/venv/bin
ExecStart=/opt/stockalerts/venv/bin/python periodic_checker.py
EOF
```

**Create Timer for Daily Execution:**
```bash
sudo tee /etc/systemd/system/stockalerts-checker.timer << EOF
[Unit]
Description=Run Stock Alerts Checker Daily
Requires=stockalerts-checker.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

**Enable Timer:**
```bash
sudo systemctl enable stockalerts-checker.timer
sudo systemctl start stockalerts-checker.timer

# Check timer status
sudo systemctl list-timers stockalerts-checker.timer
```

#### 5. Nginx Reverse Proxy

**Create Nginx Configuration:**
```bash
sudo tee /etc/nginx/sites-available/stockalerts << EOF
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files
    location /static/ {
        alias /opt/stockalerts/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:5001;
        access_log off;
    }
}
EOF
```

**Enable Site:**
```bash
# Enable site and restart nginx
sudo ln -s /etc/nginx/sites-available/stockalerts /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
sudo systemctl enable nginx
```

#### 6. SSL Certificate with Let's Encrypt

**Install Certbot:**
```bash
# Ubuntu/Debian
sudo apt install -y certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install -y certbot python3-certbot-nginx
```

**Obtain Certificate:**
```bash
# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

#### 7. Set Telegram Webhook

**Configure Production Webhook:**
```bash
# Set webhook to your production domain
curl -F "url=https://yourdomain.com/webhook" \
     -F "secret_token=your_secure_webhook_secret_64_chars_minimum" \
     "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook"

# Verify webhook
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

---

### Option 2: Docker Deployment

#### 1. Create Dockerfile

**Create Dockerfile:**
```dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs db static/js

# Set permissions
RUN chmod +x app.py periodic_checker.py

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

# Run application
CMD ["python", "app.py"]
```

#### 2. Docker Compose Configuration

**Create docker-compose.yml:**
```yaml
version: '3.8'

services:
  stockalerts:
    build: .
    ports:
      - "5001:5001"
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_WEBHOOK_SECRET=${TELEGRAM_WEBHOOK_SECRET}
      - PORT=5001
    volumes:
      - ./db:/app/db
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - stockalerts
    restart: unless-stopped

  periodic-checker:
    build: .
    command: python periodic_checker.py
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    volumes:
      - ./db:/app/db
      - ./logs:/app/logs
    profiles:
      - cron
    restart: "no"
```

#### 3. Deploy with Docker

**Deploy Application:**
```bash
# Create production environment file
echo "TELEGRAM_BOT_TOKEN=your_bot_token" > .env
echo "TELEGRAM_WEBHOOK_SECRET=your_webhook_secret" >> .env

# Build and start services
docker-compose up -d

# Check service status
docker-compose ps
docker-compose logs -f stockalerts

# Set up cron for periodic checker
echo "0 18 * * * cd /path/to/stockalerts && docker-compose run --rm periodic-checker" | crontab -
```

---

### Option 3: Cloud Platform Deployment

#### Heroku Deployment

**Create Heroku App:**
```bash
# Install Heroku CLI and login
heroku login

# Create app
heroku create your-stockalerts-app

# Set environment variables
heroku config:set TELEGRAM_BOT_TOKEN=your_bot_token
heroku config:set TELEGRAM_WEBHOOK_SECRET=your_webhook_secret

# Deploy
git push heroku main

# Set webhook
curl -F "url=https://your-stockalerts-app.herokuapp.com/webhook" \
     -F "secret_token=your_webhook_secret" \
     "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook"
```

**Create Procfile:**
```
web: gunicorn app:app
```

**Configure Heroku Scheduler:**
```bash
# Add Heroku Scheduler addon
heroku addons:create scheduler:standard

# Open scheduler dashboard
heroku addons:open scheduler

# Add daily job: python periodic_checker.py
```

---

## Configuration Management

### Production Environment Variables

**Required Variables:**
```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_SECRET=64_character_hex_string_for_security

# Application Configuration
PORT=5001                    # Application port
FLASK_ENV=production        # Flask environment
```

**Optional Variables:**
```bash
# Database Configuration
DATABASE_PATH=db/stockalerts.db    # SQLite database path

# Logging Configuration
LOG_LEVEL=INFO                     # Logging level
LOG_FILE=logs/stock_alerts.log     # Log file path

# Performance Configuration
CACHE_TTL_HOURS=1                  # Cache time-to-live
MAX_WORKERS=2                      # Gunicorn workers
```

### Application Configuration

**Update Database Configuration** (via [`migrations/001_initial.sql:85-90`](./migrations/001_initial.sql#L85-90))
```sql
-- Connect to production database
sqlite3 db/stockalerts.db

-- Update configuration for production
UPDATE config SET value = '12' WHERE key = 'cache_duration_hours';
UPDATE config SET value = '100' WHERE key = 'max_stocks_per_user';
UPDATE config SET value = 'stockalerts@yourdomain.com' WHERE key = 'admin_email';
```

---

## Monitoring & Maintenance

### Application Monitoring

**Log Monitoring:**
```bash
# Monitor application logs
sudo journalctl -u stockalerts -f

# Monitor nginx access logs
sudo tail -f /var/log/nginx/access.log

# Monitor error logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /opt/stockalerts/logs/stock_alerts.log
```

**Health Monitoring Script:**
```bash
#!/bin/bash
# health_check.sh

HEALTH_URL="https://yourdomain.com/health"
ALERT_EMAIL="admin@yourdomain.com"

# Check application health
if ! curl -f -s "$HEALTH_URL" > /dev/null; then
    echo "Stock Alerts application health check failed" | \
    mail -s "Stock Alerts Alert: Health Check Failed" "$ALERT_EMAIL"
    
    # Restart service
    sudo systemctl restart stockalerts
fi
```

**Set up Health Monitoring Cron:**
```bash
# Add to crontab (check every 5 minutes)
*/5 * * * * /opt/stockalerts/health_check.sh
```

### Database Maintenance

**Backup Script:**
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/stockalerts"
DB_PATH="/opt/stockalerts/db/stockalerts.db"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create database backup
sqlite3 "$DB_PATH" ".backup $BACKUP_DIR/stockalerts_$DATE.db"

# Compress backup
gzip "$BACKUP_DIR/stockalerts_$DATE.db"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
```

**Database Optimization:**
```sql
-- Run weekly maintenance
sqlite3 db/stockalerts.db "VACUUM;"
sqlite3 db/stockalerts.db "ANALYZE;"

-- Clean old logs (keep 90 days)
sqlite3 db/stockalerts.db "DELETE FROM logs WHERE timestamp < datetime('now', '-90 days');"

-- Clean old cache (keep 7 days)
sqlite3 db/stockalerts.db "DELETE FROM stock_cache WHERE last_check < datetime('now', '-7 days');"
```

### Performance Monitoring

**Resource Monitoring:**
```bash
# CPU and memory usage
top -p $(pgrep -f "python.*app.py")

# Disk usage
df -h /opt/stockalerts
du -sh /opt/stockalerts/db/
du -sh /opt/stockalerts/logs/

# Network connections
netstat -tulpn | grep :5001
```

**Application Metrics Script:**
```bash
#!/bin/bash
# metrics.sh

# Database size
DB_SIZE=$(du -h /opt/stockalerts/db/stockalerts.db | cut -f1)

# Log file size
LOG_SIZE=$(du -h /opt/stockalerts/logs/stock_alerts.log | cut -f1)

# Memory usage
MEM_USAGE=$(ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem -p $(pgrep -f "python.*app.py") | tail -n +2)

echo "Database size: $DB_SIZE"
echo "Log size: $LOG_SIZE"
echo "Memory usage: $MEM_USAGE"
```

---

## Security Hardening

### Application Security

**File Permissions:**
```bash
# Set secure file permissions
sudo chown -R stockalerts:stockalerts /opt/stockalerts
sudo chmod 755 /opt/stockalerts
sudo chmod 600 /opt/stockalerts/.env
sudo chmod 644 /opt/stockalerts/db/stockalerts.db
sudo chmod 755 /opt/stockalerts/logs
```

**Firewall Configuration:**
```bash
# Configure UFW (Ubuntu)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw deny 5001  # Block direct access to app port

# View firewall status
sudo ufw status verbose
```

### Database Security

**Database Backup Encryption:**
```bash
# Encrypted backup script
gpg --symmetric --cipher-algo AES256 --output backup_encrypted.gpg backup.db
```

**Access Control:**
```bash
# Restrict database file access
sudo chmod 640 /opt/stockalerts/db/stockalerts.db
sudo chgrp stockalerts /opt/stockalerts/db/stockalerts.db
```

---

## Scaling Considerations

### Horizontal Scaling

**Load Balancer Configuration:**
```nginx
upstream stockalerts_backend {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
}

server {
    # ... SSL configuration ...
    
    location / {
        proxy_pass http://stockalerts_backend;
        # ... proxy configuration ...
    }
}
```

**Multi-Instance Deployment:**
```bash
# Create multiple service instances
for i in {1..3}; do
    PORT=$((5000 + i))
    sed "s/5001/$PORT/g" /etc/systemd/system/stockalerts.service > \
        /etc/systemd/system/stockalerts-$i.service
    sudo systemctl enable stockalerts-$i
    sudo systemctl start stockalerts-$i
done
```

### Database Scaling

**PostgreSQL Migration:**
```python
# For production scale, consider PostgreSQL
# Update db_manager.py connection string:
DATABASE_URL = "postgresql://user:password@localhost/stockalerts"
```

**Read Replicas:**
```python
# Implement read/write splitting in db_manager.py
def get_read_connection(self):
    return psycopg2.connect(self.read_database_url)

def get_write_connection(self):
    return psycopg2.connect(self.write_database_url)
```

---

## Troubleshooting Production Issues

### Common Deployment Issues

**Service Not Starting:**
```bash
# Check service status and logs
sudo systemctl status stockalerts
sudo journalctl -u stockalerts --no-pager

# Check Python environment
cd /opt/stockalerts
source venv/bin/activate
python -c "import app; print('OK')"
```

**Database Issues:**
```bash
# Check database file permissions
ls -la /opt/stockalerts/db/stockalerts.db

# Verify database integrity
sqlite3 /opt/stockalerts/db/stockalerts.db "PRAGMA integrity_check;"

# Check table structure
sqlite3 /opt/stockalerts/db/stockalerts.db ".schema"
```

**Telegram Webhook Issues:**
```bash
# Verify webhook configuration
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# Test webhook endpoint
curl -X POST "https://yourdomain.com/webhook" \
     -H "X-Telegram-Bot-Api-Secret-Token: your_secret" \
     -H "Content-Type: application/json" \
     -d '{"update_id": 1}'
```

### Performance Issues

**High Memory Usage:**
```bash
# Check process memory usage
ps aux | grep python

# Monitor memory over time
while true; do
    ps -o pid,ppid,cmd,%mem --sort=-%mem -p $(pgrep -f "python.*app.py")
    sleep 60
done
```

**Database Performance:**
```sql
-- Check query performance
.timer on
SELECT COUNT(*) FROM watchlist_items;

-- Check database size
.dbinfo

-- Vacuum database if needed
VACUUM;
```

---

This deployment guide provides comprehensive instructions for production deployment with multiple options and thorough security considerations. Choose the deployment method that best fits your infrastructure and requirements.