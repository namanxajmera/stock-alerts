# API Documentation

This document details the API endpoints provided by the StockViz application.

## 1. Web Dashboard API

This API is used by the frontend to fetch and display stock data.

### `GET /data/<ticker>/<period>`

Fetches historical stock data, moving averages, and percentile analysis for a given stock ticker and time period.

*   **File Reference:** [`app.py:get_stock_data()`](../app.py)
*   **URL Parameters:**
    *   `ticker` (string, required): The stock symbol (e.g., `AAPL`, `TSLA`).
    *   `period` (string, required): The time period to display. Valid options: `1y`, `3y`, `5y`, `max`.
*   **Authentication:** None. This is a public endpoint.

*   **Success Response (200 OK):**

    ```json
    {
        "dates": ["2022-01-01", "2022-01-02", ...],
        "prices": [150.0, 151.5, ...],
        "ma_200": [null, ..., 145.0, 145.2],
        "pct_diff": [null, ..., 3.4, 4.3],
        "percentiles": {
            "p16": -10.5,
            "p84": 12.8
        },
        "previous_close": 149.75
    }
    ```

*   **Error Response (400 Bad Request):**

    ```json
    {
        "error": "Invalid period. Must be one of: 1y, 3y, 5y, max"
    }
    ```

*   **Error Response (404 Not Found):**

    ```json
    {
        "error": "No data available for this ticker symbol"
    }
    ```

## 2. Telegram Bot API

This endpoint acts as the webhook for the Telegram Bot API.

### `POST /webhook`

Receives updates from Telegram whenever a user interacts with the bot.

*   **File Reference:** [`app.py:telegram_webhook()`](../app.py) and [`webhook_handler.py`](../webhook_handler.py)
*   **Request Body:** A JSON object sent by Telegram, containing the update information. See [Telegram Bot API Docs](https://core.telegram.org/bots/api#update) for the full structure.
*   **Authentication:** The request must include a secret token in the `X-Telegram-Bot-Api-Secret-Token` header, which is validated against the `TELEGRAM_WEBHOOK_SECRET` environment variable. This validation occurs in `webhook_handler.py:validate_webhook()`.

*   **Response:**
    *   A successful processing of the update returns an empty response with a `200 OK` status code.
    *   If validation fails, the server responds with `403 Forbidden`.
    *   If the webhook handler is not initialized, it returns `503 Service Unavailable`.

## 3. Admin & Utility API

These endpoints are for administrative, health-checking, and automation purposes.

### `GET /health`

A health check endpoint to verify that the application and its database connection are operational.

*   **File Reference:** [`app.py:health_check()`](../app.py)
*   **Authentication:** None.

*   **Success Response (200 OK):**
    ```json
    {
        "status": "healthy"
    }
    ```
*   **Error Response (500 Internal Server Error):**
    ```json
    {
        "status": "unhealthy",
        "error": "Database manager not initialized"
    }
    ```

### `GET /admin`

A simple HTML admin panel to view data from the database tables.

*   **File Reference:** [`app.py:admin_panel()`](../app.py)
*   **Authentication:** HTTP Basic Authentication. Credentials must match `ADMIN_USERNAME` and `ADMIN_PASSWORD` from the environment variables. The auth logic is implemented in the `require_admin_auth` decorator in [`app.py`](../app.py).

*   **Response:** Returns an HTML page with tables for `users`, `watchlist_items`, `alert_history`, etc.

### `POST /admin/check`

An endpoint designed to be triggered by an external scheduler (like a cron job or GitHub Action) to run the periodic stock check.

*   **File Reference:** [`app.py:trigger_stock_check()`](../app.py)
*   **Authentication:** None by default in the provided code, but it is implicitly protected by being an obscure POST endpoint. **Recommendation:** This endpoint should be protected, for example, by requiring a secret API key.
*   **Use Case:** The GitHub Action defined in [`.github/workflows/stock-alerts.yml`](../.github/workflows/stock-alerts.yml) calls this endpoint to kick off the daily alert process.

*   **Success Response (200 OK):**
    ```json
    {
        "status": "success",
        "message": "Stock check completed"
    }
    ```

*   **Error Response (500 Internal Server Error):**
    ```json
    {
        "status": "error",
        "message": "Error details here"
    }
    ```
