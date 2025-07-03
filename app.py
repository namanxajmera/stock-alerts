import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")


def setup_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs("logs", exist_ok=True)
    os.makedirs("db", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)


setup_directories()

from flask import (
    Flask,
    render_template,
    jsonify,
    send_from_directory,
    request,
    abort,
    g,
)
from flask_cors import CORS
from tiingo import TiingoClient
import pandas as pd
import numpy as np
import traceback
import json
from datetime import datetime, timedelta
import pytz
import mimetypes
import time
from db_manager import DatabaseManager
from webhook_handler import WebhookHandler
import logging
import psycopg2.extras


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/stock_alerts.log"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("StockAlerts.App")


logger = setup_logging()
mimetypes.add_type("application/javascript", ".js")


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NaN/Infinity values."""

    def default(self, obj):
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super().default(obj)


try:
    logger.info("Initializing database manager and webhook handler...")
    db_manager = DatabaseManager()
    webhook_handler = WebhookHandler(
        db_manager,
        os.getenv("TELEGRAM_BOT_TOKEN"),
        os.getenv("TELEGRAM_WEBHOOK_SECRET"),
    )

    app = Flask(__name__)
    app.json_encoder = CustomJSONEncoder
    CORS(app)  # Enable CORS for all routes by default for simplicity
    logger.info(
        "Flask app initialized with CORS and ready for Railway deployment. Environment variables fixed."
    )

except Exception as e:
    logger.critical(f"FATAL: Error during initialization: {e}", exc_info=True)
    raise


def fetch_tiingo_data(ticker_symbol):
    """Fetch data from Tiingo API using direct REST calls."""
    try:
        # Get API token from environment
        api_token = os.getenv("TIINGO_API_TOKEN")
        if not api_token:
            raise ValueError("TIINGO_API_TOKEN not found in environment variables")

        logger.info(f"Fetching Tiingo data for {ticker_symbol}")

        # Calculate start date for maximum historical data (30+ years available)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * 365)  # 30 years ago

        # Build the REST API URL as per Tiingo docs
        url = f"https://api.tiingo.com/tiingo/daily/{ticker_symbol}/prices"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {api_token}",
        }

        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
        }

        logger.info(
            f"Making request to: {url} with dates {params['startDate']} to {params['endDate']}"
        )

        # Make the API request
        import requests

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        if not data:
            logger.warning(f"No data returned from Tiingo for {ticker_symbol}")
            return None

        # Convert JSON response to DataFrame
        df = pd.DataFrame(data)

        # Convert Tiingo format to match expected format
        # Tiingo returns: date, close, high, low, open, volume, adjClose, adjHigh, adjLow, adjOpen, adjVolume, divCash, splitFactor
        # Use adjusted prices which incorporate split and dividend adjustments per CRSP methodology

        # Use split-adjusted prices for accurate historical charts
        column_mapping = {
            "date": "Date",
            "adjOpen": "Open",
            "adjHigh": "High",
            "adjLow": "Low",
            "adjClose": "Close",
            "adjVolume": "Volume",
        }

        # Select and rename only the columns we need
        df_filtered = df[list(column_mapping.keys())].rename(columns=column_mapping)

        # Convert date string to datetime and set as index
        df_filtered["Date"] = pd.to_datetime(df_filtered["Date"])
        df_filtered.set_index("Date", inplace=True)

        # Sort by date (oldest first)
        df_filtered = df_filtered.sort_index()

        logger.info(
            f"Successfully fetched {len(df_filtered)} data points for {ticker_symbol} from Tiingo"
        )
        return df_filtered

    except Exception as e:
        logger.error(f"Error fetching data from Tiingo for {ticker_symbol}: {e}")
        raise


def calculate_metrics(ticker_symbol, period="5y"):
    """Calculate stock metrics including MA and percentiles with caching and retry logic."""
    try:
        logger.info(f"Processing request for {ticker_symbol} with period {period}")

        valid_periods = ["1y", "3y", "5y", "max"]
        if period not in valid_periods:
            return {
                "error": f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            }, 400

        # Check cache first (1 hour cache)
        cache_hours = int(os.getenv("CACHE_HOURS", 1))
        cached_data = db_manager.get_fresh_cache(
            ticker_symbol, max_age_hours=cache_hours
        )

        if cached_data and cached_data.get("data_json"):
            logger.info(f"Using cached data for {ticker_symbol}")
            try:
                cache_data = json.loads(cached_data["data_json"])
                # Use cached percentiles if available
                if "percentiles" in cache_data:
                    percentile_5th = cache_data["percentiles"]["p5"]
                    percentile_95th = cache_data["percentiles"]["p95"]
                else:
                    # Fallback percentiles
                    percentile_5th = -10.0
                    percentile_95th = 10.0

                # For now, fetch fresh data but note it was in cache
                # In a full implementation, we'd store the complete time series data in cache
                logger.info(
                    f"Cache hit for {ticker_symbol}, but fetching fresh data for complete time series"
                )
                # Fall through to fetch fresh data, but we'll use the cached price info

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid cached data for {ticker_symbol}: {e}")
                # Continue to fetch fresh data

        # Fetch fresh data from Tiingo API
        try:
            complete_data = fetch_tiingo_data(ticker_symbol)

            if complete_data is None or complete_data.empty:
                return {"error": "No data available for this ticker symbol"}, 404

        except Exception as e:
            logger.error(f"Failed to fetch data from Tiingo for {ticker_symbol}: {e}")
            return {"error": "Unable to fetch stock data. Please try again later."}, 500

        # Calculate technical indicators
        complete_data["MA200"] = complete_data["Close"].rolling(window=200).mean()
        complete_data["pct_diff"] = (
            (complete_data["Close"] - complete_data["MA200"]) / complete_data["MA200"]
        ) * 100

        valid_pct_diff = complete_data["pct_diff"].dropna()
        if len(valid_pct_diff) < 20:
            return {
                "error": "Insufficient data for meaningful analysis (need at least 20 data points)"
            }, 400

        percentile_5th = np.percentile(valid_pct_diff, 5)
        percentile_95th = np.percentile(valid_pct_diff, 95)

        previous_close = (
            complete_data["Close"].iloc[-2] if len(complete_data) >= 2 else None
        )
        current_price = complete_data["Close"].iloc[-1]
        current_ma_200 = complete_data["MA200"].iloc[-1]

        # Filter data by period
        if period != "max":
            years = int(period[:-1])
            start_date = datetime.now(pytz.utc) - timedelta(days=years * 365)
            # Ensure index is timezone-aware for comparison
            if complete_data.index.tz is None:
                complete_data.index = complete_data.index.tz_localize("UTC")
            data = complete_data[complete_data.index >= start_date]
        else:
            data = complete_data

        # Prepare result - convert NaN to None for valid JSON
        def clean_for_json(series):
            """Convert pandas series to list with NaN/inf converted to None"""
            # Replace inf/-inf with NaN, then convert to list and replace NaN with None
            cleaned = series.replace([np.inf, -np.inf], np.nan)
            result = cleaned.tolist()
            # Replace any remaining NaN values with None for valid JSON
            return [None if pd.isna(x) else x for x in result]

        result = {
            "dates": data.index.strftime("%Y-%m-%d").tolist(),
            "prices": clean_for_json(data["Close"]),
            "ma_200": clean_for_json(data["MA200"]),
            "pct_diff": clean_for_json(data["pct_diff"]),
            "percentiles": {"p5": percentile_5th, "p95": percentile_95th},
            "previous_close": previous_close,
        }

        # Update cache with fresh data
        cache_data = {
            "price": float(current_price),
            "ma_200": float(current_ma_200) if not pd.isna(current_ma_200) else None,
            "percentiles": {"p5": percentile_5th, "p95": percentile_95th},
            "last_updated": datetime.now().isoformat(),
        }

        db_manager.update_stock_cache(
            symbol=ticker_symbol,
            price=current_price,
            ma_200=current_ma_200 if not pd.isna(current_ma_200) else None,
            data_json=json.dumps(cache_data),
        )

        # Add small delay to be respectful to Yahoo Finance
        time.sleep(0.5)

        logger.info(
            f"Successfully processed {ticker_symbol} with {len(data)} data points"
        )
        return result, 200

    except Exception as e:
        error_msg = f"Unexpected error processing {ticker_symbol}: {e}"
        logger.error(error_msg, exc_info=True)
        return {"error": "An unexpected error occurred. Please try again later."}, 500


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/static/js/<path:filename>")
def serve_js(filename):
    return send_from_directory("static/js", filename, mimetype="application/javascript")


@app.route("/data/<ticker>/<period>")
def get_stock_data(ticker, period):
    logger.info(f"Request for ticker: {ticker}, period: {period}")
    result, status_code = calculate_metrics(ticker.upper(), period)
    return jsonify(result), status_code


@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not webhook_handler.validate_webhook(request.get_data(), secret_token):
        logger.warning("Invalid webhook request validation failed.")
        abort(403)

    webhook_handler.process_update(request.get_data())
    return "", 200


@app.route("/health", methods=["GET"])
def health_check():
    try:
        db_manager.get_config("telegram_token")
        logger.info("Health check passed")
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/admin", methods=["GET"])
def admin_panel():
    try:
        # Get all table data
        with db_manager._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Users
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()

            # Watchlist items
            cursor.execute("SELECT * FROM watchlist_items ORDER BY user_id, symbol")
            watchlist = cursor.fetchall()

            # Alert history (last 50)
            cursor.execute("SELECT * FROM alert_history ORDER BY sent_at DESC LIMIT 50")
            alerts = cursor.fetchall()

            # Stock cache
            cursor.execute("SELECT * FROM stock_cache ORDER BY last_check DESC")
            cache = cursor.fetchall()

            # Config (filter out sensitive data)
            cursor.execute("SELECT * FROM config WHERE key != 'telegram_token'")
            config = cursor.fetchall()

        # Simple HTML template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Panel</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                h2 {{ color: #333; cursor: pointer; user-select: none; }}
                h2:hover {{ background-color: #f5f5f5; }}
                .count {{ color: #666; font-size: 14px; }}
                .section {{ border: 1px solid #ddd; margin: 10px 0; }}
                .section-header {{ background-color: #f8f9fa; padding: 10px; }}
                .section-content {{ padding: 10px; display: block; }}
                .collapsed {{ display: none; }}
                .toggle {{ font-size: 18px; margin-right: 10px; }}
            </style>
            <script>
                function toggleSection(id) {{
                    const content = document.getElementById(id);
                    const toggle = document.getElementById(id + '-toggle');
                    if (content.classList.contains('collapsed')) {{
                        content.classList.remove('collapsed');
                        toggle.textContent = '▼';
                    }} else {{
                        content.classList.add('collapsed');
                        toggle.textContent = '▶';
                    }}
                }}
            </script>
        </head>
        <body>
            <h1>Database Admin Panel</h1>

            <div class="section">
                <div class="section-header" onclick="toggleSection('users')">
                    <span id="users-toggle" class="toggle">▼</span>
                    <strong>Users</strong> <span class="count">({len(users)} total)</span>
                </div>
                <div id="users" class="section-content">
                    <table>
                        <tr><th>ID</th><th>Name</th><th>Joined</th><th>Max Stocks</th><th>Notifications</th></tr>
                        {''.join([f"<tr><td>{u['id']}</td><td>{u['name']}</td><td>{u['joined_at']}</td><td>{u['max_stocks']}</td><td>{'✓' if u['notification_enabled'] else '✗'}</td></tr>" for u in users])}
                    </table>
                </div>
            </div>

            <div class="section">
                <div class="section-header" onclick="toggleSection('watchlist')">
                    <span id="watchlist-toggle" class="toggle">▼</span>
                    <strong>Watchlist Items</strong> <span class="count">({len(watchlist)} total)</span>
                </div>
                <div id="watchlist" class="section-content">
                    <table>
                        <tr><th>User ID</th><th>Symbol</th><th>Added</th><th>Low Threshold</th><th>High Threshold</th></tr>
                        {''.join([f"<tr><td>{w['user_id']}</td><td>{w['symbol']}</td><td>{w['added_at']}</td><td>{w['alert_threshold_low']}</td><td>{w['alert_threshold_high']}</td></tr>" for w in watchlist])}
                    </table>
                </div>
            </div>

            <div class="section">
                <div class="section-header" onclick="toggleSection('alerts')">
                    <span id="alerts-toggle" class="toggle">▼</span>
                    <strong>Alert History</strong> <span class="count">({len(alerts)} recent)</span>
                </div>
                <div id="alerts" class="section-content">
                    <table>
                        <tr><th>User ID</th><th>Symbol</th><th>Price</th><th>Percentile</th><th>Status</th><th>Sent At</th></tr>
                        {''.join([f"<tr><td>{a['user_id']}</td><td>{a['symbol']}</td><td>${a['price']:.2f}</td><td>{a['percentile']:.1f}%</td><td>{a['status']}</td><td>{a['sent_at']}</td></tr>" for a in alerts])}
                    </table>
                </div>
            </div>

            <div class="section">
                <div class="section-header" onclick="toggleSection('cache')">
                    <span id="cache-toggle" class="toggle">▼</span>
                    <strong>Stock Cache</strong> <span class="count">({len(cache)} cached)</span>
                </div>
                <div id="cache" class="section-content">
                    <table>
                        <tr><th>Symbol</th><th>Last Price</th><th>MA200</th><th>Last Check</th></tr>
                        {''.join([f"<tr><td>{c['symbol']}</td><td>{'${:.2f}'.format(c['last_price']) if c['last_price'] else 'N/A'}</td><td>{'${:.2f}'.format(c['ma_200']) if c['ma_200'] else 'N/A'}</td><td>{c['last_check']}</td></tr>" for c in cache])}
                    </table>
                </div>
            </div>

            <div class="section">
                <div class="section-header" onclick="toggleSection('config')">
                    <span id="config-toggle" class="toggle">▼</span>
                    <strong>Configuration</strong> <span class="count">({len(config)} settings)</span>
                </div>
                <div id="config" class="section-content">
                    <table>
                        <tr><th>Key</th><th>Value</th><th>Description</th></tr>
                        {''.join([f"<tr><td>{cfg['key']}</td><td>{cfg['value']}</td><td>{cfg['description'] or ''}</td></tr>" for cfg in config])}
                    </table>
                </div>
            </div>
        </body>
        </html>
        """

        return html
    except Exception as e:
        logger.error(f"Admin panel error: {e}", exc_info=True)
        return f"<h1>Error</h1><p>{e}</p>", 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found"}), 404


@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server Error: {error}", exc_info=True)
    return jsonify({"error": "Internal Server Error"}), 500


@app.errorhandler(403)
def forbidden(error):
    return jsonify({"error": "Forbidden"}), 403


if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 5001))
        logger.info(f"Starting Stock Analytics Dashboard server on port {port}...")
        app.run(debug=False, host="0.0.0.0", port=port)
    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True)
