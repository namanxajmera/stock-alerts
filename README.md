# Stock Analytics Dashboard

A simple, single-page web application for visualizing stock price history and technical analysis, with a Telegram bot for personalized stock alerts.

## Features

- 📈 Clean, minimal UI inspired by Robinhood
- 🔍 Simple stock ticker input with period selection
- 📊 Two-chart visualization:
  - Main chart: Daily closing prices with 200-day moving average
  - Sub-chart: Percent difference from 200-day MA with percentile bands
- 🤖 Telegram bot for managing watchlists and receiving alerts
- 💾 SQLite database for storing user preferences, watchlists, and alert history
- 🔄 CORS support for cross-origin requests
- 🎨 Custom JSON handling for NaN/Infinity values
- 📝 Detailed console logging with color coding

## Tech Stack

- Frontend: HTML, CSS, JavaScript with Plotly.js
- Backend: Python (Flask) with yfinance
- Database: SQLite
- Bot: Telegram Bot API
- Data: Yahoo Finance API
- Utils: termcolor for console logging, CustomJSONEncoder for JSON handling

## Project Structure

```
stock-alerts/
├── app.py                  # Flask web server & API
├── bot.js                  # Node.js Telegram bot (for local development)
├── db_manager.py           # Database access layer
├── webhook_handler.py      # Telegram webhook handler (for production)
├── periodic_checker.py     # Periodic stock analysis and alerts
├── requirements.txt        # Python dependencies
├── package.json           # Node.js dependencies
├── tsconfig.json          # TypeScript configuration
├── .env                   # Environment variables (create this)
├── db/
│   └── stockalerts.db     # SQLite database (auto-created)
├── migrations/            # Database migration scripts
│   ├── 001_initial.sql
│   └── 002_add_indexes.sql
├── static/
│   ├── css/
│   │   └── style.css      # Frontend styling
│   ├── ts/
│   │   └── main.ts        # TypeScript source
│   └── js/
│       └── main.js        # Compiled JavaScript
├── templates/
│   └── index.html         # Main web page
└── logs/                  # Application logs (auto-created)
    └── stock_alerts.log
```

## Setup & Installation

### Prerequisites
- Python 3.8+ 
- Node.js 14+
- A Telegram account

### 1. Clone and Setup Environment

```bash
git clone https://github.com/yourusername/stock-alerts.git
cd stock-alerts

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies and build TypeScript
npm install
npm run build
```

### 2. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 3. Configure Environment

Create a `.env` file in the project root:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 4. Initialize Database

The database will be automatically created when you first run the application. If you need to manually set it up:

```bash
# Create missing tables (if needed)
source venv/bin/activate
python -c "from db_manager import DatabaseManager; DatabaseManager()"
```

### 5. Run the Application

You need to run **both** services:

#### Terminal 1 - Web Interface:
```bash
source venv/bin/activate
python app.py
```
Access at: `http://localhost:5001`

#### Terminal 2 - Telegram Bot:
```bash
node bot.js
```

### 6. Test the Setup

1. **Web Interface**: Open `http://localhost:5001` and try searching for a stock (e.g., AAPL)
2. **Telegram Bot**: 
   - Find your bot in Telegram (search for the name you gave it)
   - Send `/start` to begin
   - Try commands like `/add AAPL` or `/list`

## Bot Commands

- `/start` - Initialize the bot and see available commands
- `/add <ticker>` - Add stock(s) to your watchlist (e.g., `/add AAPL MSFT`)
- `/remove <ticker>` - Remove a stock from watchlist
- `/list` - Show your current watchlist
- `/help` - Show available commands

## Troubleshooting

### Bot Not Responding
1. **Check bot token**: Ensure your `.env` file has the correct `TELEGRAM_BOT_TOKEN`
2. **Restart bot**: Stop `node bot.js` (Ctrl+C) and restart it
3. **Check logs**: Look for error messages in the terminal running the bot

### Web Interface Issues
1. **Port conflict**: If port 5001 is busy, the app will show an error
2. **Rate limiting**: Yahoo Finance may temporarily block requests - this is normal
3. **Check browser console**: Press F12 to see any JavaScript errors

### Database Issues
1. **Permissions**: Ensure the `db/` directory is writable
2. **Reset database**: Delete `db/stockalerts.db` and restart the app to recreate it

### Common Error Messages
- `"TELEGRAM_BOT_TOKEN environment variable not set"` → Check your `.env` file
- `"Too Many Requests. Rate limited"` → Yahoo Finance rate limiting (temporary)
- `"Database locked"` → Stop all running instances and restart

## Development

The application uses a modular architecture:
- **Flask backend** (`app.py`) - Web server and stock data API
- **Node.js bot** (`bot.js`) - Direct Telegram integration for development
- **Webhook handler** (`webhook_handler.py`) - Production Telegram integration
- **Database layer** (`db_manager.py`) - All database operations
- **Frontend** - TypeScript/JavaScript with Plotly.js for charts
- **SQLite database** - Stores users, watchlists, and alert history

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[TBD - Choose a license]
