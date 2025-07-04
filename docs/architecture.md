# System Architecture

This document provides a comprehensive overview of the StockViz application's architecture. It is designed for both product managers seeking to understand the system's capabilities and engineers needing a deep dive into its components.

## 1. High-Level Overview

StockViz is a monolithic web application built with Python and Flask. It follows a classic 3-tier architecture:

1.  **Presentation Tier (Frontend):** An interactive web dashboard built with HTML, CSS, and JavaScript. It communicates with the backend via a REST API.
2.  **Application Tier (Backend):** The core Flask application that handles business logic, serves the frontend, processes API requests, and manages interactions with external services.
3.  **Data Tier (Backend):** A PostgreSQL database for persistent storage of user data, watchlists, and cached stock information.

 <!-- Placeholder for a real diagram -->

### For Product Managers: Business Context

This architecture allows for two distinct user experiences—a rich web interface for analysis and a simple, alert-driven Telegram bot—to be powered by a single, unified backend. This consolidation reduces complexity and ensures data consistency across both platforms. The asynchronous job system enables proactive, automated alerts, which is a core value proposition.

## 2. Component Breakdown

### 2.1. Frontend

The frontend is a single-page application responsible for data visualization.

*   **Framework:** Standard HTML, CSS, and vanilla JavaScript.
*   **Charting Library:** [Plotly.js](https://plotly.com/javascript/) is used for creating interactive charts.
*   **Core Files:**
    *   [`templates/index.html`](../templates/index.html): The main HTML structure of the page.
    *   [`static/css/style.css`](../static/css/style.css): All styling for the application.
    *   [`static/js/main.js`](../static/js/main.js): Handles user input, fetches data from the backend API, and renders the Plotly charts.

### 2.2. Backend (Flask Application)

The backend is orchestrated by the main Flask application file, [`app.py`](./app.py).

*   **Web Server & API:** [`app.py`](../app.py) defines all URL routes, including serving the frontend, the data API for the charts, and the admin panel. It uses Gunicorn for production execution as defined in [`Procfile`](../Procfile) and [`railway.json`](../railway.json).
*   **Database Manager:** [`db_manager.py`](../db_manager.py) provides an abstraction layer for all database operations. It handles connections, schema migrations, and CRUD (Create, Read, Update, Delete) operations. It uses the `psycopg2-binary` library to connect to PostgreSQL.
*   **Telegram Webhook Handler:** [`webhook_handler.py`](../webhook_handler.py) processes incoming messages from the Telegram Bot API. It handles user commands (`/add`, `/list`, etc.) and sends messages back to users. It is registered as the `/webhook` endpoint in [`app.py:telegram_webhook()`](../app.py).
*   **Periodic Checker:** [`periodic_checker.py`](../periodic_checker.py) contains the logic for the primary background task: checking all user watchlists for stocks that meet alert criteria. This is not a continuously running process but a script designed for single-run execution.

### 2.3. Data Layer

The data layer consists of a PostgreSQL database. The schema is managed via SQL migration files.

*   **Database Engine:** PostgreSQL.
*   **Schema Definition:** The complete initial schema is defined in [`migrations/001_initial.sql`](../migrations/001_initial.sql).
*   **Key Tables:**
    *   `users`: Stores information about Telegram users.
    *   `watchlist_items`: Associates users with the stock symbols they are tracking.
    *   `stock_cache`: Caches historical stock data from Tiingo to reduce API calls and improve performance. The `get_fresh_cache()` function in [`db_manager.py`](../db_manager.py) is used to retrieve recent data.
    *   `alert_history`: Logs every alert sent to a user for tracking and analytics.
    *   `migrations`: Tracks which schema migrations have been applied. The logic is in [`db_manager.py:initialize_database()`](../db_manager.py).

## 3. Data and Logic Flow

### 3.1. Web Dashboard Data Flow

1.  A user enters a stock ticker in the browser ([`templates/index.html`](../templates/index.html)).
2.  JavaScript in [`static/js/main.js`](../static/js/main.js) sends a request to the backend API endpoint `/data/<ticker>/<period>`.
3.  The `get_stock_data()` function in [`app.py`](../app.py) receives the request.
4.  It calls `calculate_metrics()`, which first checks the `stock_cache` table via `db_manager.py`.
5.  If the cache is stale or empty, it calls `fetch_tiingo_data()` to get fresh data from the Tiingo API.
6.  The data is processed (e.g., calculating moving averages and percentiles), returned as JSON to the frontend, and cached in the database.
7.  The frontend JavaScript renders the received data into charts using Plotly.js.

### 3.2. Telegram Alert Flow

1.  A user sends a command (e.g., `/add TSLA`) to the Telegram bot.
2.  Telegram sends a POST request to the application's `/webhook` endpoint.
3.  [`webhook_handler.py:process_update()`](../webhook_handler.py) validates and parses the request.
4.  The command is handled (e.g., `_handle_add_command()`), and a new entry is created in the `watchlist_items` table via `db_manager.py`.
5.  A confirmation message is sent back to the user.

### 3.3. Asynchronous Alert Generation Flow

1.  A cron-scheduled GitHub Action, defined in [`.github/workflows/stock-alerts.yml`](../.github/workflows/stock-alerts.yml), runs daily.
2.  The workflow sends a POST request to the `/admin/check` endpoint on the production server.
3.  This trigger is handled by `trigger_stock_check()` in [`app.py`](../app.py).
4.  An instance of `PeriodicChecker` from [`periodic_checker.py`](../periodic_checker.py) is created.
5.  The `check_watchlists()` method is called. It fetches all active watchlists, retrieves stock data (using cache where possible), and checks if any stock's deviation from its 200-day MA is outside the 16th-84th percentile range.
6.  If a stock meets the alert criteria, the `send_alert()` method in [`webhook_handler.py`](../webhook_handler.py) is called to send a notification to the user via the Telegram API.

## 4. External Services

*   **Tiingo API:** Used as the primary source for historical stock market data. The function `_fetch_symbol_data_tiingo()` in [`periodic_checker.py`](../periodic_checker.py) implements the data fetching with retry logic.
*   **Telegram Bot API:** Used for all interactions with the Telegram bot, including receiving commands and sending alerts/messages.
