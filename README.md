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
├── app.py                  # Flask backend
├── db_manager.py           # Database access layer
├── bot_handler.py          # Telegram bot integration
├── weekly_checker.py       # Periodic stock analysis and alerts
├── requirements.txt        # Python dependencies
├── package.json           # Node.js dependencies (for TypeScript)
├── tsconfig.json         # TypeScript configuration
├── db/
│   └── stockalerts.db     # SQLite database file
├── migrations/            # Database migration scripts
│   ├── 001_initial.sql
│   └── 002_add_indexes.sql
├── static/
│   ├── css/
│   │   └── style.css
│   ├── ts/
│   │   └── main.ts       # TypeScript frontend code
│   └── js/               # Compiled JavaScript (generated)
└── templates/
    └── index.html        # Flask template
```

## Setup & Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/stock-alerts.git
cd stock-alerts
```

2. Create and activate a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the SQLite database:
```bash
sqlite3 db/stockalerts.db < migrations/001_initial.sql
sqlite3 db/stockalerts.db < migrations/002_add_indexes.sql
```

5. Install Node.js dependencies and build TypeScript:
```bash
npm install
npm run build
```

6. Run the application:
```bash
python app.py
```

7. Open your browser and navigate to `http://localhost:5001`

8. Create a new Telegram bot using BotFather and set the webhook to your server's `/webhook` endpoint

## Development

The application uses a modular architecture:
- Flask backend serves the webpage and provides API endpoints
- SQLite database stores user preferences, watchlists, and alert history
- Telegram bot handles user interactions and sends alerts
- Periodic checker analyzes stocks and triggers alerts
- Frontend makes API calls to fetch stock data
- Plotly.js handles all chart rendering
- All styling is done with plain CSS

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[TBD - Choose a license]
