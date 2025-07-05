# System Architecture

This document provides a comprehensive overview of the Stock Alerts application's architecture, designed for both product managers and engineers. The system combines interactive web analytics with automated Telegram alerts through a unified backend.

## 1. High-Level Overview

Stock Alerts is a monolithic Flask application organized into a clean, service-oriented structure following a 3-tier architecture:

### 1.1 Architecture Tiers

1. **Presentation Tier:** Interactive web dashboard built with ApexCharts.js and vanilla JavaScript
2. **Application Tier:** Flask backend with modular services and background job processing  
3. **Data Tier:** PostgreSQL database with connection pooling and automated migrations

### 1.2 Business Value Architecture

**For Product Managers:** This unified architecture powers two distinct user experiences:
- **Rich Web Interface:** Interactive charts and analytics for detailed stock analysis
- **Telegram Bot:** Simple, conversational interface for managing watchlists and receiving alerts

The single backend ensures data consistency and reduces operational complexity while enabling automated, proactive alerts without external dependencies.

**For Engineers:** Clean separation of concerns with:
- Service-oriented business logic
- Automated database migrations
- Built-in caching and connection pooling
- Comprehensive input validation and security
- Ready-to-deploy configuration

## 2. Component Architecture

### 2.1 Frontend Layer

The frontend is a single-page application focused on interactive stock data visualization.

**Technology Stack:**
- HTML5 with semantic structure
- CSS3 with custom properties and responsive design
- Vanilla JavaScript with modular ES6 patterns
- [ApexCharts.js](https://apexcharts.com/) for advanced charting

**Core Files:**
- [`templates/index.html`](../templates/index.html) - Main HTML structure with ApexCharts CDN integration
- [`static/css/style.css`](../static/css/style.css) - Complete styling with CSS variables and responsive layout
- [`static/js/main.js`](../static/js/main.js) - StockAnalyzer module with chart rendering and API integration

**Key Frontend Features:**
- Real-time chart updates via REST API calls
- Multi-timeframe period selection (1Y, 3Y, 5Y, MAX)
- Interactive tooltips and hover states
- Responsive design for mobile and desktop
- Trading intelligence stats display

### 2.2 Backend Application Layer

The Flask backend is orchestrated through a modular architecture with clear separation of concerns.

#### 2.2.1 Application Bootstrap
**Entry Point:** [`app.py`](../app.py)
- Initializes Flask application with CORS and custom JSON encoder
- Loads configuration via [`utils/config.py`](../utils/config.py)
- Sets up logging with file and console handlers
- Creates service instances and stores them in app context
- Registers all blueprint routes
- Configures background scheduler

#### 2.2.2 Route Layer (`routes/`)
Blueprint-based route organization:

- **[`routes/api_routes.py`](../routes/api_routes.py)** - Public stock data endpoints
  - `GET /data/<ticker>/<period>` - Stock price and MA data via `get_stock_data()`
  - `GET /trading-stats/<ticker>/<period>` - Trading intelligence via `get_trading_stats()`
  
- **[`routes/webhook_routes.py`](../routes/webhook_routes.py)** - Telegram bot integration
  - `POST /webhook` - Telegram webhook endpoint via `telegram_webhook()`
  
- **[`routes/admin_routes.py`](../routes/admin_routes.py)** - Administrative interface
  - `GET /admin` - HTML admin panel via `admin_panel()`
  - `POST /admin/check` - Manual alert trigger via `trigger_stock_check()`
  
- **[`routes/health_routes.py`](../routes/health_routes.py)** - System monitoring
  - `GET /health` - Application health check via `health_check()`

#### 2.2.3 Service Layer (`services/`)
Encapsulates core business logic:

- **[`services/stock_service.py`](../services/stock_service.py)** - Stock data processing
  - `calculate_metrics()` - Calculates MA, percentiles, and statistical indicators
  - `calculate_trading_stats()` - Fear/greed analysis and opportunity scoring
  - `get_stock_data()` - Data fetching with intelligent caching
  
- **[`services/admin_service.py`](../services/admin_service.py)** - Admin operations
  - `get_admin_data()` - Database table data for admin dashboard
  - `trigger_stock_check()` - Manual watchlist check execution
  
- **[`services/auth_service.py`](../services/auth_service.py)** - Authentication & authorization
  - `require_admin_auth()` - HTTP Basic Auth decorator
  - `validate_admin_api_key()` - API key validation for admin endpoints

#### 2.2.4 Core Components

- **[`webhook_handler.py`](../webhook_handler.py)** - Telegram bot message processing
  - `validate_webhook()` - HMAC-SHA256 webhook validation
  - `process_update()` - Command parsing and routing
  - `send_alert()` - Alert message dispatch
  
- **[`periodic_checker.py`](../periodic_checker.py)** - Background alert logic
  - `check_watchlists()` - Processes all user watchlists for alert conditions
  
- **[`utils/scheduler.py`](../utils/scheduler.py)** - Background job scheduling
  - `setup_scheduler()` - Configures APScheduler with daily stock checks at 1 AM UTC
  - `scheduled_stock_check()` - Wrapper function for periodic checker execution

### 2.3 Data Layer

PostgreSQL database with automated schema management and connection pooling.

#### 2.3.1 Database Management
**[`db_manager.py`](../db_manager.py)** - Database abstraction layer:
- **Connection Pooling:** `psycopg2.pool.SimpleConnectionPool` with configurable min/max connections
- **Context Management:** `_managed_cursor()` context manager for automatic connection handling
- **Transaction Safety:** Automatic rollback on errors with comprehensive exception handling
- **Migration System:** `initialize_database()` automatically applies SQL migrations on startup

#### 2.3.2 Schema Management
**Migration System:** [`migrations/`](../migrations/) directory
- [`migrations/000_migrations_table.sql`](../migrations/000_migrations_table.sql) - Migration tracking table
- [`migrations/001_initial.sql`](../migrations/001_initial.sql) - Complete application schema

#### 2.3.3 Database Schema
**Core Tables:**

**`users`** - Telegram user management
```sql
id TEXT PRIMARY KEY,                    -- Telegram user ID
name TEXT NOT NULL,                     -- User display name
joined_at TIMESTAMP DEFAULT NOW(),     -- Registration timestamp
last_notified TIMESTAMP,                -- Last alert sent
notification_enabled BOOLEAN DEFAULT TRUE,
max_stocks INTEGER DEFAULT 20          -- Watchlist limit
```

**`watchlist_items`** - User stock watchlists
```sql
user_id TEXT,                          -- Foreign key to users
symbol TEXT,                           -- Stock ticker symbol
added_at TIMESTAMP DEFAULT NOW(),      -- When stock was added
alert_threshold_low REAL DEFAULT 5.0,  -- Lower percentile threshold
alert_threshold_high REAL DEFAULT 95.0 -- Upper percentile threshold
```

**`stock_cache`** - Performance optimization
```sql
symbol TEXT PRIMARY KEY,               -- Stock ticker
last_check TIMESTAMP NOT NULL,        -- Cache timestamp
ma_200 REAL,                          -- 200-day moving average
last_price REAL,                       -- Most recent price
data_json TEXT                         -- Complete time series data
```

**`alert_history`** - Audit trail
```sql
user_id TEXT,                          -- User who received alert
symbol TEXT,                           -- Stock that triggered alert
price REAL,                            -- Price at alert time
percentile REAL,                       -- Statistical position
status TEXT,                           -- sent/failed/error
sent_at TIMESTAMP DEFAULT NOW()        -- Alert timestamp
```

### 2.4 Utility Layer (`utils/`)

Shared utilities and external integrations.

#### 2.4.1 Configuration Management
**[`utils/config.py`](../utils/config.py)** - Centralized configuration:
- **Environment Loading:** Validates and loads all required environment variables
- **Type Conversion:** Automatic conversion of string env vars to appropriate types
- **Validation:** `_validate_required_config()` ensures critical values are present
- **Security:** `get_config_summary()` logs config status without exposing sensitive values

#### 2.4.2 External API Integration
**[`utils/tiingo_client.py`](../utils/tiingo_client.py)** - Tiingo API client:
- **Centralized Requests:** `fetch_historical_data()` with configurable retry logic
- **Error Handling:** Comprehensive exception handling for network and API errors
- **Rate Limiting:** Built-in request delays to respect API limits
- **Data Processing:** Returns pandas DataFrames with proper date indexing

#### 2.4.3 Security & Validation
**[`utils/validators.py`](../utils/validators.py)** - Input sanitization:
- **Ticker Validation:** `validate_ticker_symbol()` prevents injection attacks
- **Period Validation:** `validate_period()` ensures only allowed timeframes
- **Command Validation:** `validate_command_args()` for Telegram bot security
- **SQL Injection Prevention:** Parameterized query validation

#### 2.4.4 Background Processing
**[`utils/scheduler.py`](../utils/scheduler.py)** - APScheduler integration:
- **Cron Configuration:** Daily execution at 1 AM UTC via `CronTrigger`
- **Job Management:** `setup_scheduler()` with graceful shutdown handling
- **Error Recovery:** Exception handling with detailed logging
- **Timezone Handling:** UTC-based scheduling for consistency

## 3. Data Flow Architecture

### 3.1 Web Dashboard Request Flow

**User Interaction to Chart Rendering:**

1. **User Input:** Ticker entry in [`templates/index.html`](../templates/index.html) form
2. **Frontend Request:** [`static/js/main.js`](../static/js/main.js) StockAnalyzer module sends AJAX request to `/data/<ticker>/<period>`
3. **Route Handling:** [`routes/api_routes.py:get_stock_data()`](../routes/api_routes.py) receives and processes request
4. **Input Validation:** [`utils/validators.py`](../utils/validators.py) functions validate ticker symbol and period
5. **Service Delegation:** Route calls [`services/stock_service.py:calculate_metrics()`](../services/stock_service.py)
6. **Cache Check:** [`db_manager.py:get_fresh_cache()`](../db_manager.py) checks for recent data (default 1 hour)
7. **Data Fetching:** If cache miss, [`utils/tiingo_client.py:fetch_historical_data()`](../utils/tiingo_client.py) fetches from Tiingo API
8. **Data Processing:** Calculate 200-day MA, percentiles, and statistical indicators
9. **Cache Update:** Fresh data stored via [`db_manager.py:update_stock_cache()`](../db_manager.py)
10. **Response:** JSON data with dates, prices, MA, and percentiles returned to frontend
11. **Chart Rendering:** ApexCharts.js renders interactive price and momentum charts

### 3.2 Telegram Bot Command Flow

**Bot Command Processing Pipeline:**

1. **User Command:** User sends `/add TSLA` or similar command to Telegram bot
2. **Webhook Delivery:** Telegram POSTs update to `/webhook` endpoint
3. **Route Handling:** [`routes/webhook_routes.py:telegram_webhook()`](../routes/webhook_routes.py) receives request
4. **Security Validation:** [`webhook_handler.py:validate_webhook()`](../webhook_handler.py) performs HMAC-SHA256 verification
5. **Update Processing:** [`webhook_handler.py:process_update()`](../webhook_handler.py) parses JSON and extracts message
6. **Command Routing:** `_handle_command()` identifies command type and validates arguments
7. **Input Validation:** [`utils/validators.py:validate_command_args()`](../utils/validators.py) sanitizes ticker symbols
8. **Database Operations:** Appropriate handler calls [`db_manager.py`](../db_manager.py) methods:
   - `add_to_watchlist()` for `/add` commands
   - `remove_from_watchlist()` for `/remove` commands
   - `get_watchlist()` for `/list` commands
9. **Response Generation:** Success/error message prepared based on operation result
10. **Message Delivery:** [`webhook_handler.py:_send_message()`](../webhook_handler.py) sends response via Telegram API

### 3.3 Automated Alert Generation Flow

**Background Alert Processing:**

1. **Scheduler Trigger:** [`utils/scheduler.py`](../utils/scheduler.py) APScheduler executes `scheduled_stock_check()` daily at 1 AM UTC
2. **Checker Instantiation:** [`periodic_checker.py:PeriodicChecker`](../periodic_checker.py) instance created
3. **Watchlist Retrieval:** `check_watchlists()` calls [`db_manager.py:get_active_watchlists()`](../db_manager.py) to fetch all enabled user watchlists
4. **Data Processing Loop:** For each unique stock symbol:
   - **Cache Check:** [`db_manager.py:get_fresh_cache()`](../db_manager.py) attempts to use cached data
   - **API Fallback:** If cache miss, [`utils/tiingo_client.py:fetch_historical_data()`](../utils/tiingo_client.py) fetches fresh data
   - **Metric Calculation:** Compute 200-day MA and percentage deviation
   - **Percentile Analysis:** Calculate 16th and 84th percentiles for historical context
5. **Alert Logic:** Check if current price deviation exceeds historical percentile thresholds
6. **Alert Dispatch:** If criteria met:
   - [`webhook_handler.py:send_alert()`](../webhook_handler.py) sends formatted message via Telegram API
   - [`db_manager.py:add_alert_history()`](../db_manager.py) logs alert for audit trail
   - [`db_manager.py:update_user_notification_time()`](../db_manager.py) updates user's last notification timestamp
7. **Error Handling:** Comprehensive logging and graceful failure handling throughout the process

### 3.4 Trading Intelligence Flow

**Advanced Analytics Pipeline:**

1. **API Request:** Frontend requests `/trading-stats/<ticker>/<period>` endpoint
2. **Data Retrieval:** [`services/stock_service.py:calculate_trading_stats()`](../services/stock_service.py) leverages existing `calculate_metrics()` data
3. **Statistical Analysis:** 
   - Fear/greed zone classification based on percentile ranges
   - Alert frequency calculation over time periods
   - Average price analysis for different market conditions
   - Consecutive streak analysis for extreme movements
4. **Opportunity Scoring:** Algorithm calculates current opportunity score based on:
   - Current price relative to historical fear/greed averages
   - Time spent in different zones
   - Volatility patterns and streak analysis
5. **Response Formation:** Comprehensive JSON response with trading insights and recommendations