# Deployment Guide

This document provides instructions for deploying the StockViz application to a production environment.

## 1. Deployment Platforms

The application is configured for deployment on platforms that support Python applications and PostgreSQL databases, such as Railway or Heroku.

### Railway

The [`railway.json`](../railway.json) file provides the necessary configuration for deploying on Railway.

*   **Build:** Railway will use Nixpacks to automatically detect the Python environment and install dependencies from [`requirements.txt`](../requirements.txt).
*   **Start Command:** The application is started using Gunicorn, as defined in the `deploy.startCommand`:
    ```json
    "startCommand": "gunicorn --bind 0.0.0.0:$PORT --timeout 300 --workers 1 app:app"
    ```

### Heroku (or other Procfile-based platforms)

The [`Procfile`](../Procfile) is configured to run the application using Gunicorn.

```
web: gunicorn --bind 0.0.0.0:$PORT app:app
```

## 2. Environment Variables

Before deploying, you must configure all the environment variables from [`.env.example`](../.env.example) in your production environment's settings.

**Critical Production Settings:**

*   `FLASK_ENV`: Set to `production`.
*   `DATABASE_URL`: This must be the connection string provided by your managed PostgreSQL service.
*   `TELEGRAM_BOT_TOKEN`: Your bot's production token.
*   `TELEGRAM_WEBHOOK_SECRET`: A strong, unique secret for webhook validation.
*   `TIINGO_API_TOKEN`: Your Tiingo API token.
*   `ADMIN_USERNAME` & `ADMIN_PASSWORD`: Secure credentials for the admin panel.

**Never commit your production `.env` file to version control.**

## 3. Database Setup

1.  **Provision a PostgreSQL Database:** Add a PostgreSQL database service to your deployment platform.
2.  **Configure `DATABASE_URL`:** Use the connection string from your provisioned database as the value for the `DATABASE_URL` environment variable.
3.  **Run Migrations:** The application is designed to run database migrations on startup. The `initialize_database()` function in [`db_manager.py`](../db_manager.py) will create the schema from the files in the [`migrations/`](../migrations/) directory if the tables do not already exist.

## 4. Setting up the Telegram Webhook

For the Telegram bot to function, you must tell Telegram where to send updates.

1.  **Get your application's public URL:** e.g., `https://your-app-name.up.railway.app`.
2.  **Construct the Webhook URL:** Append `/webhook` to your public URL: `https://your-app-name.up.railway.app/webhook`.
3.  **Set the Webhook via Telegram API:** You can do this by sending a request to the Telegram API. Replace `<YOUR_BOT_TOKEN>`, `<YOUR_WEBHOOK_URL>`, and `<YOUR_SECRET_TOKEN>` with your actual values.
    ```sh
    curl --request POST \
      --url https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
      --header 'Content-Type: application/json' \
      --data '{
        "url": "<YOUR_WEBHOOK_URL>",
        "secret_token": "<YOUR_SECRET_TOKEN>"
      }'
    ```

## 5. Configuring Scheduled Tasks (Periodic Check)

The daily stock check is triggered by an external scheduler. The repository includes a GitHub Actions workflow for this purpose.

*   **File:** [`.github/workflows/stock-alerts.yml`](../.github/workflows/stock-alerts.yml)

**To enable this:**

1.  Ensure the URL in the `curl` command inside `stock-alerts.yml` points to your production application's `/admin/check` endpoint.
    ```yaml
    # .github/workflows/stock-alerts.yml
    response=$(curl -s -w "\n%{http_code}" -X POST https://web-production-59017.up.railway.app/admin/check \
      -H "Content-Type: application/json")
    ```
2.  The GitHub Action is scheduled to run daily at 1 AM UTC (`cron: '0 1 * * *'`). You can adjust this schedule as needed.
3.  The workflow can also be triggered manually from the "Actions" tab in your GitHub repository.
