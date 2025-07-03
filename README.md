# Stock Analytics Dashboard & Telegram Alerts

A comprehensive web application for visualizing stock price history and technical analysis, with intelligent Telegram bot alerts for historically extreme stock movements.

## 🚀 Quick Start

1. **Install Dependencies** (see [`requirements.txt`](./requirements.txt))
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment** (see [setup instructions](#environment-configuration))
   ```bash
   cp .env.example .env
   # Edit .env with your Telegram bot token
   ```

3. **Initialize Database** (automatic on first run via [`db_manager.py:initialize_database()`](./db_manager.py#L44))
   ```bash
   python app.py
   ```

4. **Access Application**
   - Web Interface: `http://localhost:5001`
   - Telegram Bot: Send `/start` to your bot

## 📊 Core Features

### Web Dashboard
- **Interactive Charts**: Built with Plotly.js ([`templates/index.html`](./templates/index.html))
- **Real-time Data**: Yahoo Finance integration ([`app.py:fetch_yahoo_data_with_retry()`](./app.py#L75))
- **Technical Analysis**: 200-day moving average with percentile bands
- **Smart Caching**: 1-hour cache system ([`app.py:calculate_metrics()`](./app.py#L109))

### Telegram Bot Features
- **Watchlist Management**: Add/remove stocks ([`webhook_handler.py:_handle_add_command()`](./webhook_handler.py#L177))
- **Smart Alerts**: Notifications when stocks hit 16th/84th percentiles (1σ)
- **Secure Webhooks**: HMAC validation ([`webhook_handler.py:validate_webhook()`](./webhook_handler.py#L24))

### Technical Capabilities
- **Rate Limiting Protection**: Exponential backoff for Yahoo Finance API
- **Database Management**: SQLite with migrations ([`migrations/001_initial.sql`](./migrations/001_initial.sql))
- **Error Recovery**: Comprehensive logging and error handling
- **Performance Optimization**: Data caching and efficient queries

## 🏗️ Architecture Overview

### Tech Stack
- **Backend**: Python 3.8+ with Flask ([`app.py`](./app.py))
- **Database**: SQLite with comprehensive schema ([`db_manager.py`](./db_manager.py))
- **Frontend**: TypeScript + Plotly.js ([`static/js/main.js`](./static/js/main.js))
- **Bot Framework**: Telegram Bot API ([`webhook_handler.py`](./webhook_handler.py))
- **Data Source**: Yahoo Finance via `yfinance` library

### Core Components

#### 1. Web Application (`app.py`)
- **Flask Server**: Handles web requests and API endpoints
- **Stock Data API**: `/data/<ticker>/<period>` endpoint ([`app.py:get_stock_data()`](./app.py#L231))
- **Caching Logic**: Intelligent data caching ([`app.py:calculate_metrics()`](./app.py#L109))
- **Error Handling**: Comprehensive exception management

#### 2. Database Layer (`db_manager.py`)
- **Connection Management**: Context managers for safe DB operations ([`db_manager.py:_managed_cursor()`](./db_manager.py#L28))
- **Migration System**: Automatic schema updates ([`db_manager.py:initialize_database()`](./db_manager.py#L44))
- **Data Models**: Users, watchlists, alerts, and cache tables

#### 3. Telegram Integration (`webhook_handler.py`)
- **Webhook Processing**: Secure message handling ([`webhook_handler.py:process_update()`](./webhook_handler.py#L46))
- **Command System**: `/start`, `/add`, `/remove`, `/list` commands
- **Alert System**: Intelligent stock movement notifications

#### 4. Periodic Monitoring (`periodic_checker.py`)
- **Watchlist Scanner**: Checks all active watchlists ([`periodic_checker.py:check_watchlists()`](./periodic_checker.py#L23))
- **Alert Triggering**: Sends notifications for extreme movements
- **Batch Processing**: Efficient symbol grouping ([`periodic_checker.py:_process_symbol()`](./periodic_checker.py#L84))

## 🗃️ Database Schema

The application uses a comprehensive SQLite schema defined in [`migrations/001_initial.sql`](./migrations/001_initial.sql):

### Core Tables
- **`users`**: User profiles and notification preferences
- **`watchlist_items`**: User stock watchlists with thresholds
- **`stock_cache`**: Cached stock data with timestamps
- **`alert_history`**: Complete alert audit trail
- **`logs`**: Application event logging

### Key Features
- **Foreign Key Constraints**: Data integrity enforcement
- **Optimized Indexes**: Fast query performance
- **Data Validation**: CHECK constraints for data quality
- **Audit Trails**: Complete history tracking

## 🔧 Configuration

### Environment Variables
```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_WEBHOOK_SECRET=your_secure_random_string

# Optional
PORT=5001  # Default Flask port
```

### Database Configuration
The database auto-initializes with default settings stored in the `config` table:
- `cache_duration_hours`: 24 (configurable via [`db_manager.py:get_config()`](./db_manager.py#L194))
- `max_stocks_per_user`: 20
- `default_threshold_low`: 16.0 (16th percentile)
- `default_threshold_high`: 84.0 (84th percentile)

## 📡 API Endpoints

### Web API
- **`GET /`**: Main dashboard ([`app.py:index()`](./app.py#L223))
- **`GET /data/<ticker>/<period>`**: Stock data endpoint ([`app.py:get_stock_data()`](./app.py#L231))
- **`GET /health`**: Health check endpoint ([`app.py:health_check()`](./app.py#L247))

### Telegram Webhook
- **`POST /webhook`**: Secure Telegram webhook ([`app.py:telegram_webhook()`](./app.py#L237))

## 🤖 Bot Commands

| Command | Description | Implementation |
|---------|-------------|----------------|
| `/start` | Initialize bot and show help | [`webhook_handler.py:_get_welcome_message()`](./webhook_handler.py#L103) |
| `/add <TICKER>...` | Add stocks to watchlist | [`webhook_handler.py:_handle_add_command()`](./webhook_handler.py#L177) |
| `/remove <TICKER>...` | Remove stocks from watchlist | [`webhook_handler.py:_handle_remove_command()`](./webhook_handler.py#L199) |
| `/list` | Show current watchlist | [`webhook_handler.py:_handle_list_command()`](./webhook_handler.py#L164) |

## 🚨 Alert System

### Alert Triggers
Alerts are sent when a stock's current price deviation from its 200-day moving average reaches:
- **16th Percentile or Lower**: Statistically significant low (1σ below)
- **84th Percentile or Higher**: Statistically significant high (1σ above)

### Alert Logic Flow
1. **Data Collection**: [`periodic_checker.py:_fetch_symbol_data_with_retry()`](./periodic_checker.py#L51)
2. **Calculation**: Moving average and percentile analysis
3. **Threshold Check**: Compare against historical percentiles
4. **Notification**: Send formatted alert via Telegram
5. **Logging**: Record alert in [`alert_history`](./migrations/001_initial.sql#L56) table

## 🛠️ Development

### Project Structure
```
stock-alerts/
├── app.py                      # Main Flask application
├── db_manager.py              # Database operations layer
├── webhook_handler.py         # Telegram bot logic
├── periodic_checker.py        # Alert monitoring service
├── requirements.txt           # Python dependencies
├── static/
│   ├── css/style.css         # UI styling
│   └── js/main.js            # Frontend TypeScript/JavaScript
├── templates/
│   └── index.html            # Main web interface
└── migrations/
    └── 001_initial.sql       # Database schema
```

### Key Design Patterns
- **Service Layer**: Clean separation of concerns ([`db_manager.py`](./db_manager.py))
- **Error Boundaries**: Comprehensive exception handling
- **Caching Strategy**: Intelligent data freshness management
- **Security First**: HMAC webhook validation and input sanitization

## 📈 Performance Features

### Caching System
- **Smart Cache**: 1-hour web cache, 2-hour periodic cache
- **Cache Keys**: Symbol-based with timestamp validation
- **Implementation**: [`db_manager.py:get_fresh_cache()`](./db_manager.py#L247)

### Rate Limiting
- **Exponential Backoff**: Handles Yahoo Finance rate limits ([`app.py:fetch_yahoo_data_with_retry()`](./app.py#L75))
- **Request Spacing**: 0.5-1 second delays between requests
- **Retry Logic**: Up to 3 attempts with increasing delays

### Database Optimization
- **Indexed Queries**: Strategic indexes on frequently queried columns
- **Connection Pooling**: Context managers for efficient connection usage
- **Batch Operations**: Group processing for multiple symbols

## 🔒 Security Features

### Webhook Security
- **HMAC Validation**: Cryptographic webhook verification ([`webhook_handler.py:validate_webhook()`](./webhook_handler.py#L24))
- **Secret Token**: Environment-based secret management
- **Request Validation**: JSON structure and content validation

### Data Protection
- **SQL Injection Prevention**: Parameterized queries throughout
- **Input Sanitization**: User input validation and cleaning
- **Error Information Leakage**: Sanitized error messages

## 📊 Monitoring & Logging

### Logging System
- **Structured Logging**: Consistent log format across components
- **Multiple Handlers**: File and console output ([`app.py:setup_logging()`](./app.py#L31))
- **Event Tracking**: Database event logging ([`db_manager.py:log_event()`](./db_manager.py#L183))

### Health Monitoring
- **Health Endpoint**: `/health` for monitoring systems
- **Database Connectivity**: Validates database access
- **Error Tracking**: Comprehensive error logging and history

## 🚀 Deployment Ready

### Production Considerations
- **Environment Variables**: Secure configuration management
- **Process Management**: Designed for process managers (systemd, supervisor)
- **Monitoring Integration**: Health checks and structured logging
- **Scalability**: Efficient database design and caching

### Performance Metrics
- **Response Times**: Cached responses under 100ms
- **Database Efficiency**: Optimized queries with proper indexing
- **Memory Usage**: Efficient data structures and connection management
- **Error Rates**: Comprehensive error handling and recovery

## 📋 Quick Setup Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Telegram bot created via @BotFather
- [ ] Environment variables configured (`.env` file)
- [ ] Webhook URL set (for production deployment)
- [ ] Application started (`python app.py`)
- [ ] Health check verified (`/health` endpoint)
- [ ] Bot commands tested (`/start` in Telegram)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Follow existing code patterns and add tests
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

## 🧪 Testing & Development

### Automated Testing (Pre-Commit Hooks)

The project includes comprehensive automated testing that runs before every commit:

```bash
# Setup once
pip install -r requirements.txt
pre-commit install

# Now every commit automatically runs:
git commit -m "your changes"
# ✅ Database Tests.............................Passed
# ✅ Type Check (MyPy).........................Passed
# ✅ Lint Check (Pylint).......................Passed
# ✅ Format Check (Black)......................Passed
```

### Manual Testing

```bash
# Quick pre-deployment validation
./pre_deploy.sh

# Full test suite with PostgreSQL
./test_local.sh

# Database-specific tests
python test_db.py
```

### What Gets Tested
- **Database Operations**: PostgreSQL compatibility, migrations, CRUD operations
- **API Endpoints**: Response formats, error handling, performance
- **Type Safety**: MyPy static analysis for type correctness
- **Code Quality**: Pylint standards and best practices
- **Data Integrity**: Split-adjusted price calculations

## 📚 Additional Documentation

- [**SETUP.md**](docs/SETUP.md) - Complete installation and configuration guide
- [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) - Detailed technical architecture
- [**API.md**](docs/API.md) - Comprehensive API documentation
- [**DEPLOYMENT.md**](docs/DEPLOYMENT.md) - Production deployment procedures
- [**TROUBLESHOOTING.md**](docs/TROUBLESHOOTING.md) - Common issues and solutions

---

**Built with ❤️ for intelligent stock market analysis**
