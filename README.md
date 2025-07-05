# Stock Alerts: Intelligent Stock Analytics & Telegram Bot

A comprehensive stock analysis platform that combines interactive web analytics with automated Telegram alerts. Built for investors who want to make data-driven decisions by understanding when stocks reach statistically significant price levels.

## 🚀 Key Features

### Interactive Web Dashboard
- **Real-time Stock Analysis:** Powered by ApexCharts.js (see [templates/index.html](./templates/index.html) and [static/js/main.js](./static/js/main.js))
- **200-Day Moving Average Analysis:** Visual trend identification with historical context
- **Statistical Momentum Indicators:** Shows percentage deviation from MA with 16th/84th percentile bands
- **Trading Intelligence Stats:** Fear/greed metrics, alert frequency analysis, and opportunity scoring
- **Multi-timeframe Support:** 1Y, 3Y, 5Y, and MAX period analysis

### Telegram Bot Integration
- **Personal Watchlists:** Add/remove stocks via simple commands (`/add TSLA`, `/remove AAPL`)
- **Automated Alerts:** Daily background checks for extreme price movements
- **Secure Webhook Handling:** HMAC-SHA256 validation (see [webhook_handler.py](./webhook_handler.py))
- **User Management:** Individual watchlist limits and notification preferences

### Technical Architecture
- **Backend:** Python Flask with PostgreSQL database
- **Data Source:** Tiingo API for real-time and historical stock data
- **Caching:** Intelligent data caching to minimize API calls
- **Deployment:** Ready for Railway, Heroku, or self-hosted environments
- **Security:** Input validation, secure configuration management, and webhook authentication

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Web Dashboard  │    │  Telegram Bot   │    │  Admin Panel    │
│                 │    │                 │    │                 │
│  ApexCharts.js  │    │  Webhook API    │    │  System Stats   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Flask API     │
                    │                 │
                    │  Routes & Auth  │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Service Layer  │
                    │                 │
                    │ Stock | Admin   │
                    │  Auth Service   │
                    └─────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
 ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
 │  Database      │    │  Tiingo API    │    │  Background    │
 │  Manager       │    │  Client        │    │  Scheduler     │
 │                │    │                │    │                │
 │  PostgreSQL    │    │  Stock Data    │    │  Daily Checks  │
 └────────────────┘    └────────────────┘    └────────────────┘
```

## 📁 Project Structure

```
stock-alerts/
├── app.py                 # Flask application entry point
├── db_manager.py         # Database operations and connection pooling
├── webhook_handler.py    # Telegram bot webhook processing
├── periodic_checker.py   # Background alert checking logic
├── routes/              # API endpoint definitions
│   ├── api_routes.py    # Stock data endpoints
│   ├── webhook_routes.py # Telegram webhook
│   ├── admin_routes.py  # Admin panel
│   └── health_routes.py # Health check
├── services/            # Business logic layer
│   ├── stock_service.py # Stock data processing
│   ├── admin_service.py # Admin operations
│   └── auth_service.py  # Authentication logic
├── utils/               # Utilities and configuration
│   ├── config.py        # Environment configuration
│   ├── tiingo_client.py # API client for Tiingo
│   ├── validators.py    # Input validation
│   └── scheduler.py     # Background task scheduler
├── templates/           # HTML templates
├── static/             # CSS, JavaScript, and assets
├── migrations/         # Database schema migrations
└── docs/              # Documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL database
- Tiingo API key (free at [tiingo.com](https://tiingo.com))
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd stock-alerts
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure database**
   ```bash
   # Update DATABASE_URL in .env
   # Database schema is automatically created on first run
   ```

5. **Start the application**
   ```bash
   python app.py
   ```

6. **Access the dashboard**
   - Web: http://localhost:5001
   - Telegram: Message your bot to start

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [SETUP.md](./docs/SETUP.md) | Complete installation and configuration guide |
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System design and component overview |
| [API.md](./docs/API.md) | API endpoints and usage examples |
| [DEPLOYMENT.md](./docs/DEPLOYMENT.md) | Production deployment instructions |
| [TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [CONTRIBUTING.md](./docs/CONTRIBUTING.md) | Development workflow and guidelines |

## 🔧 Configuration

Key environment variables (see [utils/config.py](./utils/config.py)):

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost/stockalerts
TELEGRAM_BOT_TOKEN=your_bot_token_here
TIINGO_API_TOKEN=your_tiingo_api_key_here

# Optional
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret
ADMIN_API_KEY=your_admin_api_key
PORT=5001
DEBUG=False
CACHE_HOURS=1
```

## 🛡️ Security Features

- **Input Validation:** All user inputs are validated using [utils/validators.py](./utils/validators.py)
- **Webhook Security:** HMAC-SHA256 validation for Telegram webhooks
- **Database Security:** Parameterized queries and connection pooling
- **Configuration Management:** Centralized and validated environment variables
- **Admin Authentication:** HTTP Basic Auth and API key protection

## 📊 API Endpoints

### Stock Data
- `GET /data/{ticker}/{period}` - Stock price and moving average data
- `GET /trading-stats/{ticker}/{period}` - Trading intelligence metrics

### Telegram Bot
- `POST /webhook` - Telegram webhook endpoint

### Admin
- `GET /admin` - Admin dashboard (requires auth)
- `POST /admin/check` - Manual alert check (requires API key)
- `GET /health` - Health check endpoint

## 🤝 Contributing

See [CONTRIBUTING.md](./docs/CONTRIBUTING.md) for development setup, code standards, and contribution guidelines.

## 📄 License

MIT License - See project configuration in [pyproject.toml](./pyproject.toml)

---

**Built with:** Python • Flask • PostgreSQL • ApexCharts.js • Tiingo API
