# Local Development Setup Guide

Complete instructions for setting up the Stock Alerts application locally. For production deployment, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## 🚀 Quick Start

### One-Click Setup Scripts
The project includes automated setup scripts:
- **Linux/macOS:** [`start.sh`](../start.sh) - Full automated setup and launch
- **Windows:** [`start.bat`](../start.bat) - Windows-compatible setup script

```bash
# Linux/macOS
./start.sh

# Windows
start.bat
```

These scripts handle virtual environment creation, dependency installation, and application launch.

## 📝 Prerequisites

### Required Software
- **Python 3.9+** (verified by [`start.sh`](../start.sh) script)
  ```bash
  python3 --version  # Should show 3.9 or higher
  ```
- **PostgreSQL Database** - Local or remote instance
- **Git** - For repository cloning

### Required API Keys
- **Tiingo API Token** - Free registration at [tiingo.com](https://tiingo.com)
- **Telegram Bot Token** - Create bot via [@BotFather](https://t.me/BotFather) on Telegram

## 📁 Installation Steps

### 1. Clone Repository
```bash
git clone <repository-url>
cd stock-alerts
```

### 2. Environment Configuration

Configuration is managed by [`utils/config.py`](../utils/config.py) which loads and validates environment variables.

#### Create Environment File
```bash
# Create .env file for your configuration
touch .env
```

#### Required Environment Variables
Edit your `.env` file with the following configuration:

```bash
# === REQUIRED CONFIGURATION ===

# Database (PostgreSQL required)
DATABASE_URL=postgresql://username:password@localhost:5432/stockalerts

# Telegram Bot (get from @BotFather)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ123456789

# Tiingo API (free at tiingo.com)
TIINGO_API_TOKEN=your_tiingo_api_token_here

# === OPTIONAL CONFIGURATION ===

# Webhook Security (auto-generated if not provided)
TELEGRAM_WEBHOOK_SECRET=your_secure_random_string_here

# Admin Panel Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_admin_password
ADMIN_API_KEY=your_admin_api_key_here

# Application Settings
PORT=5001
DEBUG=False
CACHE_HOURS=1
YF_REQUEST_DELAY=3.0
```

#### Environment Variable Details

| Variable | Required | Description | Example |
|----------|----------|-------------|----------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string | `postgresql://user:pass@localhost/db` |
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather | `123456:ABC...` |
| `TIINGO_API_TOKEN` | ✅ | Free API key from tiingo.com | `abc123...` |
| `TELEGRAM_WEBHOOK_SECRET` | ⚠️ | Webhook security token | Auto-generated if omitted |
| `ADMIN_USERNAME` | ❌ | Admin panel username | `admin` |
| `ADMIN_PASSWORD` | ❌ | Admin panel password | Strong password |
| `PORT` | ❌ | Server port (default: 5001) | `5001` |

**Note:** The application uses `psycopg2-binary` (see [`requirements.txt`](../requirements.txt)) and requires PostgreSQL - SQLite is not supported.

### 3. Virtual Environment Setup

Python virtual environment is strongly recommended for dependency isolation.

#### Create and Activate Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

#### Install Dependencies
All dependencies are specified in [`requirements.txt`](../requirements.txt):

```bash
# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Key Dependencies
| Package | Purpose | Version |
|---------|---------|----------|
| `flask` | Web framework | Latest |
| `psycopg2-binary` | PostgreSQL adapter | Latest |
| `pandas` | Data analysis | Latest |
| `requests` | HTTP client | Latest |
| `apscheduler` | Background tasks | Latest |
| `tiingo` | Stock API client | Latest |

See [`pyproject.toml`](../pyproject.toml) for complete dependency specifications.

### 4. Database Setup

The application uses automated database migrations for schema management.

#### Database Requirements
- **PostgreSQL server** must be running and accessible
- **Database created** (the application won't create the database itself)
- **Connection permissions** for the user specified in `DATABASE_URL`

#### Automatic Migration System
Migrations are handled by [`db_manager.py:initialize_database()`](../db_manager.py):

1. **Migration Tracking:** [`migrations/000_migrations_table.sql`](../migrations/000_migrations_table.sql)
2. **Core Schema:** [`migrations/001_initial.sql`](../migrations/001_initial.sql)
   - `users` table - Telegram user management
   - `watchlist_items` table - User stock watchlists
   - `stock_cache` table - API response caching
   - `alert_history` table - Alert audit trail
   - `logs` table - Application event logging
   - `config` table - Application configuration

#### Database Connection Testing
```bash
# Test PostgreSQL connection with your DATABASE_URL
psql "postgresql://username:password@localhost:5432/stockalerts" -c "SELECT version();"
```

**Important:** The application will automatically create tables and apply migrations on first startup. Ensure PostgreSQL is running before launching the application.

## 🚀 Running the Application

### Method 1: Direct Launch
Start the Flask development server:

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate     # Windows

# Launch application
python app.py
```

### Method 2: Using Startup Scripts
Automated launch with environment setup:

```bash
# Linux/macOS
./start.sh

# Windows
start.bat
```

### Expected Output
Successful startup shows:

```
[SUCCESS] 🚀 Starting Stock Alerts Dashboard on port 5001
[SUCCESS] 📊 Web Dashboard: http://localhost:5001
[SUCCESS] 📱 Bot commands: /start, /add, /list, /remove, /help
[INFO] Press Ctrl+C to stop the application
[INFO] Logs are being written to logs/stock_alerts.log
```

### Application Access

#### Web Dashboard
- **URL:** [http://localhost:5001](http://localhost:5001)
- **Features:** Interactive stock charts, trading intelligence, multi-timeframe analysis
- **No authentication required** for public endpoints

#### Admin Panel
- **URL:** [http://localhost:5001/admin](http://localhost:5001/admin)
- **Authentication:** HTTP Basic Auth using `ADMIN_USERNAME` and `ADMIN_PASSWORD`
- **Features:** Database inspection, manual alert triggers, system monitoring

#### Telegram Bot (Local Development)
⚠️ **Webhook Limitation:** Telegram requires HTTPS webhooks, so localhost won't work directly.

**Solution - Use ngrok for local testing:**

1. **Install ngrok:** [Download from ngrok.com](https://ngrok.com/)
2. **Expose local server:**
   ```bash
   # In a new terminal
   ngrok http 5001
   ```
3. **Configure webhook:**
   ```bash
   # Use the https URL from ngrok (e.g., https://abc123.ngrok.io)
   python setup_webhook.py
   ```
4. **Test bot:** Message your bot on Telegram

The [`setup_webhook.py`](../setup_webhook.py) script provides an interactive setup for webhook configuration with security token generation.

### Directory Structure Created
The application automatically creates:
```
stock-alerts/
├── logs/                    # Application logs
│   └── stock_alerts.log    # Main log file
├── db/                     # Database files (if using local setup)
└── static/js/              # JavaScript assets
```

## 🔧 Development Tools

### Code Quality Tools
The project includes development tools in [`pyproject.toml`](../pyproject.toml):

```bash
# Install development dependencies
pip install -e ".[dev]"

# Code formatting
black .

# Import sorting
isort .

# Type checking
mypy .

# Linting
flake8 .

# Testing
pytest
```

### Configuration Files
- **[`pyproject.toml`](../pyproject.toml)** - Project metadata and tool configuration
- **[`setup.cfg`](../setup.cfg)** - Additional tool settings
- **[`requirements.txt`](../requirements.txt)** - Production dependencies

## 🚫 Common Issues & Solutions

### Database Connection Issues
```bash
# Error: "database does not exist"
creatdb stockalerts

# Error: "role does not exist"
creatuser username

# Error: "connection refused"
sudo systemctl start postgresql  # Linux
brew services start postgresql  # macOS
```

### Python Version Issues
```bash
# Error: "Python 3.9+ required"
pyenv install 3.11.0
pyenv local 3.11.0

# Error: "python3 not found"
alias python3=python  # Windows with Python from Microsoft Store
```

### Virtual Environment Issues
```bash
# Error: "venv module not found"
python -m pip install virtualenv
python -m virtualenv venv

# Error: "activation script not found"
# Use absolute path
source /path/to/project/venv/bin/activate
```

### Missing Dependencies
```bash
# Error: "wheel build failed"
pip install --upgrade pip setuptools wheel

# Error: "psycopg2 installation failed"
# Install PostgreSQL development headers
sudo apt-get install postgresql-dev  # Ubuntu/Debian
brew install postgresql             # macOS
```

### Telegram Bot Issues
```bash
# Error: "webhook validation failed"
# Check TELEGRAM_WEBHOOK_SECRET in .env
# Regenerate with: python -c "from webhook_handler import WebhookHandler; print(WebhookHandler.generate_webhook_secret())"

# Error: "bot not responding"
# Verify token: curl "https://api.telegram.org/bot<TOKEN>/getMe"
```

## 📚 Additional Resources

### Documentation
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design and component overview
- **[API.md](./API.md)** - API endpoints and usage examples
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Production deployment guide
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Comprehensive troubleshooting guide

### Configuration References
- **Configuration Management:** [`utils/config.py`](../utils/config.py)
- **Database Schema:** [`migrations/001_initial.sql`](../migrations/001_initial.sql)
- **Startup Scripts:** [`start.sh`](../start.sh) and [`start.bat`](../start.bat)
- **Webhook Setup:** [`setup_webhook.py`](../setup_webhook.py)

### External Services
- **Tiingo API Documentation:** [https://api.tiingo.com/docs/](https://api.tiingo.com/docs/)
- **Telegram Bot API:** [https://core.telegram.org/bots/api](https://core.telegram.org/bots/api)
- **PostgreSQL Documentation:** [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)

---

**Next Steps:** After successful setup, see [ARCHITECTURE.md](./ARCHITECTURE.md) to understand the system components or [API.md](./API.md) for endpoint documentation.