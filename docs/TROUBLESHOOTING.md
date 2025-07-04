# Troubleshooting Guide

This guide provides solutions to common problems you might encounter during setup or operation.

### 1. Application Fails to Start

**Symptom:** The `python app.py` command or Gunicorn process exits immediately with an error.

*   **Cause 1: Missing Environment Variables**
    *   **Error Log:** `ValueError: DATABASE_URL environment variable is required` or similar messages about missing tokens.
    *   **Solution:** Ensure you have created a `.env` file by copying [`.env.example`](./.env.example) and have filled in all required values, especially `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, and `TIINGO_API_TOKEN`.

*   **Cause 2: Dependencies Not Installed**
    *   **Error Log:** `ModuleNotFoundError: No module named 'flask'` (or any other package from [`requirements.txt`](./requirements.txt)).
    *   **Solution:** Make sure your virtual environment is activated and you have installed all dependencies: `pip install -r requirements.txt`.

*   **Cause 3: Database Connection Failure**
    *   **Error Log:** `psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed`. This error is logged in [`db_manager.py`](./db_manager.py).
    *   **Solution:**
        1.  Verify that your PostgreSQL server is running.
        2.  Check that the `DATABASE_URL` in your `.env` file is correct (username, password, host, port, dbname).
        3.  Ensure your firewall is not blocking the connection to the PostgreSQL port.

### 2. Web Dashboard Shows an Error or No Chart

**Symptom:** The web page loads, but after entering a ticker, a red error message appears, or the charts remain empty.

*   **Cause 1: Invalid Tiingo API Token**
    *   **Error Log (in `logs/stock_alerts.log`):** `HTTPError: 401 Client Error: Unauthorized for url` from [`periodic_checker.py:_fetch_symbol_data_tiingo()`](./periodic_checker.py) or `app.py:fetch_tiingo_data()`.
    *   **Solution:** Check that the `TIINGO_API_TOKEN` in your `.env` file is correct and the account is active.

*   **Cause 2: Invalid Ticker Symbol**
    *   **Error Log (in browser console and `logs/stock_alerts.log`):** `404 Not Found` for the `/data/...` API call.
    *   **Solution:** Ensure you are using a valid stock ticker. Tiingo may not have data for all symbols. Try a common one like `AAPL` or `GOOGL`.

### 3. Telegram Bot is Not Responding

**Symptom:** Sending commands like `/start` or `/add` to the bot gets no reply.

*   **Cause 1: Webhook Not Set Correctly**
    *   **Solution:** The Telegram API needs to know where to send updates. For local development, this requires a tunneling service like `ngrok`. For production, ensure you have set the webhook correctly as described in [DEPLOYMENT.md](./DEPLOYMENT.md). You can check your current webhook status by visiting `https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo`.

*   **Cause 2: Invalid Webhook Secret Token**
    *   **Error Log (in `logs/stock_alerts.log`):** `Invalid secret token on incoming webhook.` from [`webhook_handler.py:validate_webhook()`](./webhook_handler.py).
    *   **Solution:** Verify that the `TELEGRAM_WEBHOOK_SECRET` in your `.env` file matches the `secret_token` you provided when setting the webhook.

### 4. Daily Alerts Are Not Being Sent

**Symptom:** Users have items in their watchlist, but no alerts are sent, even when conditions seem to be met.

*   **Cause 1: Scheduled Job (GitHub Action) is Failing**
    *   **Solution:** Go to the "Actions" tab in your GitHub repository and check the run history for the "Daily Stock Alerts" workflow defined in [`.github/workflows/stock-alerts.yml`](./.github/workflows/stock-alerts.yml). Look for any errors in the logs. The most common issue is the `curl` command failing because the URL is incorrect or the server is down.

*   **Cause 2: Logic Error in `periodic_checker.py`**
    *   **Solution:** Check the application logs (`logs/stock_alerts.log`) for errors during the time the check was supposed to run. There might be issues fetching data, calculating metrics, or sending the alert via the `send_alert()` function in [`webhook_handler.py`](./webhook_handler.py).

### 5. Admin Panel Access Denied

**Symptom:** When trying to access the `/admin` page, the browser keeps prompting for a username and password.

*   **Cause:** Incorrect credentials.
*   **Solution:** Ensure the username and password you are entering match the `ADMIN_USERNAME` and `ADMIN_PASSWORD` values set in your `.env` file. The authentication logic is in the `require_admin_auth` decorator in [`app.py`](./app.py).
