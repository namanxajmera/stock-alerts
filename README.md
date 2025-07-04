# StockViz: Intelligent Stock Analytics & Alerts

StockViz is a comprehensive stock analysis tool designed to provide users with insights into market trends and deliver timely alerts. It offers two primary interfaces:

1.  **An Interactive Web Dashboard:** A rich, visual platform for analyzing stock price history, moving averages, and historical deviation patterns.
2.  **A Telegram Bot:** A conversational interface for managing a personal watchlist and receiving alerts when stocks reach significant price levels.

This tool is built for investors and analysts who want to make data-driven decisions by understanding when a stock's price is at a statistical extreme compared to its historical performance.

## Key Features

### For Product Users & Managers

*   **Interactive Charting:** Visualize stock prices against their 200-day moving average to quickly identify trends. The front-end is defined in [`templates/index.html`](./templates/index.html) and powered by [`static/js/main.js`](./static/js/main.js).
*   **Momentum Analysis:** A unique chart shows the percentage deviation from the 200-day moving average, with historical 16th and 84th percentile bands to highlight statistically significant price movements.
*   **Telegram Watchlist & Alerts:** Users can interact with a Telegram bot to add or remove stocks from a personal watchlist. The system periodically checks these stocks and sends an alert when a price moves outside the normal historical range (e.g., below the 16th percentile or above the 84th percentile). The bot logic is handled in [`webhook_handler.py`](./webhook_handler.py).
*   **Automated Background Checks:** The system automatically checks for alert conditions on a daily schedule, ensuring users receive timely information without manual intervention. This is managed by [`periodic_checker.py`](./periodic_checker.py) and triggered by a GitHub workflow ([`.github/workflows/stock-alerts.yml`](./.github/workflows/stock-alerts.yml)).

### For Engineers

*   **Technology Stack:** Python, Flask, PostgreSQL, Pandas, Plotly.js, Tiingo API.
*   **Scalable Architecture:** A modular design separates concerns for the web server, database management, Telegram bot logic, and periodic checks.
*   **Database Migrations:** Schema is managed through SQL migration files, ensuring consistent database state across environments.
*   **Deployment Ready:** Includes configurations for Gunicorn, Railway, and Heroku-style deployments.

## Getting Started

*   **To set up your local development environment**, follow the detailed instructions in the [**SETUP.md**](./docs/SETUP.md) guide.
*   **To understand the system's components and data flow**, please review the [**ARCHITECTURE.md**](./docs/ARCHITECTURE.md) document.
*   **To learn about the available API endpoints**, see the [**API.md**](./docs/API.md) documentation.
