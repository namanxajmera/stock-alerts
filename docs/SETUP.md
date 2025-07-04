# Local Development Setup Guide

This guide provides step-by-step instructions to set up and run the StockViz application on a local machine. For a production environment, see [DEPLOYMENT.md](./DEPLOYMENT.md).

The project includes one-click startup scripts for convenience:
*   For Windows: [`start.bat`](./start.bat)
*   For Linux/macOS: [`start.sh`](./start.sh)

These scripts automate the steps below. For manual setup or troubleshooting, follow these instructions.

## 1. Prerequisites

*   **Python 3.8+:** Verify your installation:
    ```sh
    python3 --version
    ```
*   **Git:** To clone the repository.
*   **PostgreSQL:** The application requires a running PostgreSQL server. Ensure you have the server installed and know your connection credentials (user, password, host, port, database name).

## 2. Clone the Repository

```sh
git clone <repository-url>
cd <repository-name>
```

## 3. Environment Configuration

The application uses environment variables for configuration. All required variables are listed in [`.env.example`](./.env.example).

1.  **Create a `.env` file:**
    ```sh
    cp .env.example .env
    ```

2.  **Edit the `.env` file** with your specific settings. This is the most critical step.

    ```dotenv
    # .env

    # Telegram Bot Configuration
    # Get this from @BotFather on Telegram
    TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
    TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_token_here # Generate a strong random string

    # Server Configuration
    PORT=5001
    FLASK_ENV=development # Use 'development' for local setup

    # Database Configuration
    # This must be a valid PostgreSQL connection string.
    # Format: postgresql://<user>:<password>@<host>:<port>/<dbname>
    DATABASE_URL=postgresql://user:password@localhost:5432/stockalerts

    # Logging Configuration
    LOG_LEVEL=INFO

    # Tiingo API Configuration
    # Get this from https://www.tiingo.com/
    TIINGO_API_TOKEN=your_tiingo_api_token_here

    # Admin Panel Authentication
    ADMIN_USERNAME=admin
    ADMIN_PASSWORD=your_secure_password_here
    ```

**IMPORTANT:** The `DATABASE_URL` is required for the application to connect to PostgreSQL. The default file-based database path in [`.env.example`](./.env.example) is for a SQLite setup which is not supported by the current `psycopg2` driver in [`requirements.txt`](./requirements.txt).

## 4. Virtual Environment and Dependencies

It is highly recommended to use a Python virtual environment to manage dependencies.

1.  **Create a virtual environment:**
    ```sh
    python3 -m venv venv
    ```

2.  **Activate the virtual environment:**
    *   **Linux/macOS:**
        ```sh
        source venv/bin/activate
        ```
    *   **Windows:**
        ```cmd
        venv\Scripts\activate
        ```

3.  **Install the required Python packages:**
    The project's dependencies are listed in [`requirements.txt`](./requirements.txt).
    ```sh
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

## 5. Database Initialization

The application can initialize the database schema automatically on the first run. The schema is defined in the migration files located in the [`migrations/`](./migrations/) directory.

*   [`migrations/000_migrations_table.sql`](./migrations/000_migrations_table.sql): Creates the table to track which migrations have been applied.
*   [`migrations/001_initial.sql`](./migrations/001_initial.sql): Defines the core application schema (`users`, `watchlist_items`, `stock_cache`, etc.).

The initialization logic is handled by the `initialize_database()` function in [`db_manager.py`](./db_manager.py). When you run the application, it will connect to the PostgreSQL database specified in your `DATABASE_URL` and apply any pending migrations.

**Ensure your PostgreSQL server is running before proceeding.**

## 6. Running the Application

Once the setup is complete, you can start the Flask development server.

```sh
python app.py
```

You should see output indicating the server has started:

```
[SUCCESS] 🚀 Starting Stock Alerts Dashboard on port 5001
[SUCCESS] 📊 Web Dashboard: http://localhost:5001
[SUCCESS] 📱 Bot commands: /start, /add, /list, /remove, /help
[INFO] Press Ctrl+C to stop the application
[INFO] Logs are being written to logs/stock_alerts.log
```

*   **Web Dashboard:** Open [http://localhost:5001](http://localhost:5001) in your browser.
*   **Telegram Bot:** The bot will not work on `localhost` unless you use a tunneling service like `ngrok` to expose your local server to the internet and set the Telegram webhook accordingly. For local development, it's easier to test bot logic by directly invoking functions.
