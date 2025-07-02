# Stock Analytics Dashboard & Telegram Alerts

A simple, single-page web application for visualizing stock price history and technical analysis, with a Telegram bot for personalized stock alerts.

## Features

- 📈 Clean, minimal UI for stock visualization
- 🔍 Simple stock ticker input with period selection (1Y, 3Y, 5Y, MAX)
- 📊 Two-chart visualization:
  - Main chart: Daily closing prices with 200-day moving average
  - Sub-chart: Percent difference from 200-day MA with 5th and 95th percentile bands
- 🤖 Secure Telegram bot for managing watchlists and receiving alerts
- 💾 SQLite database for storing user data, watchlists, and alert history
- 🚀 Efficient backend processing and secure, validated webhooks
- ⚡ **Rate Limiting Protection**: Automatic retry logic with exponential backoff for Yahoo Finance API
- 🗄️ **Smart Caching**: 1-hour cache system to reduce API calls and improve performance
- 🛡️ **Error Recovery**: Graceful handling of API failures with user-friendly error messages

## Tech Stack

- **Frontend**: HTML, CSS, TypeScript with Plotly.js
- **Backend**: Python (Flask) with `yfinance` for data
- **Database**: SQLite
- **Bot**: Telegram Bot API (via Python `requests`)
- **Data Source**: Yahoo Finance API

## Project Structure

```
stock-alerts/
├── app.py                  # Flask web server & API
├── db_manager.py           # Database access layer
├── webhook_handler.py      # Secure Telegram webhook handler
├── periodic_checker.py     # Script for checking stocks and sending alerts
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment variables
├── static/
│   ├── ts/main.ts          # TypeScript source for the frontend
│   └── ...
├── templates/
│   └── index.html          # Main web page
└── migrations/
    └── 001_initial.sql     # Database schema migrations
```

## Setup & Installation

### Prerequisites
- Python 3.8+
- A Telegram account and a public server/URL for webhooks (e.g., using ngrok for local testing)

### 1. Clone and Setup Environment

```bash
git clone https://github.com/yourusername/stock-alerts.git
cd stock-alerts

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Compile TypeScript (requires Node.js and TypeScript compiler)
# If you don't have Node/npm, you can skip this if you don't change main.ts
npm install # Installs typescript
npx tsc # Compiles ts to js
```

### 2. Create Telegram Bot

1.  Open Telegram and search for `@BotFather`.
2.  Send the `/newbot` command and follow the prompts to create your bot.
3.  Copy the **bot token** you receive.

### 3. Configure Environment

Create a `.env` file in the project root (you can copy `.env.example`). You will need to generate a secure secret for the webhook.

```bash
# .env file

# Your token from BotFather
TELEGRAM_BOT_TOKEN=your_bot_token_here

# A long, random, secret string for webhook security.
# You can generate one with: python -c "import secrets; print(secrets.token_hex(32))"
TELEGRAM_WEBHOOK_SECRET=your_super_secret_string_here
```

### 4. Initialize Database

The database and its tables will be automatically created when you first run the application.

### 5. Run the Application

#### Step 5.1: Run the Web Server

```bash
source venv/bin/activate
python app.py
```
The server will start on `http://localhost:5001`.

#### Step 5.2: Set the Telegram Webhook

Your bot needs a public URL to send updates to. For local development, you can use a tool like `ngrok`.

1.  **Expose your local server:** `ngrok http 5001`
2.  `ngrok` will give you a public HTTPS URL (e.g., `https://abcd-1234.ngrok.io`).
3.  **Set the webhook** using `curl`. Replace `<YOUR_NGROK_URL>`, `<YOUR_BOT_TOKEN>`, and `<YOUR_WEBHOOK_SECRET>` with your actual values.

```bash
curl -F "url=<YOUR_NGROK_URL>/webhook" \
     -F "secret_token=<YOUR_WEBHOOK_SECRET>" \
     "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook"
```

You should see `{"ok":true,"result":true,"description":"Webhook was set"}`. Your bot is now ready.

### 6. Run the Periodic Checker

The `periodic_checker.py` script checks for stock alerts. It's designed to be run periodically (e.g., daily or weekly) by a scheduler like `cron`.

To run it manually:
```bash
source venv/bin/activate
python periodic_checker.py
```

## Bot Commands

- `/start` - Initialize the bot and see available commands.
- `/add <TICKER> [TICKER...]` - Add one or more stocks to your watchlist (e.g., `/add AAPL MSFT`).
- `/remove <TICKER> [TICKER...]` - Remove stock(s) from your watchlist.
- `/list` - Show your current watchlist.

## Troubleshooting

- **Bot not responding:**
  - Ensure your webhook is set correctly to a public URL.
  - Check the `app.py` terminal for incoming requests and errors on the `/webhook` route.
- **Web interface issues:**
  - Check your browser's developer console (F12) for JavaScript errors.
  - Yahoo Finance may temporarily block your IP if you make too many requests.
- **"Forbidden" error on webhook:** This is expected if a random person tries to access your webhook URL. It means your secret token validation is working.

## Development

The application uses a modular architecture:
- **Flask backend** (`app.py`) - Web server and stock data API
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
