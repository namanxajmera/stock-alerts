import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('.env')

def setup_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs('logs', exist_ok=True)
    os.makedirs('db', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

setup_directories()

from flask import Flask, render_template, jsonify, send_from_directory, request, abort, g
from flask_cors import CORS
import yfinance as yf
from yfinance.exceptions import YFRateLimitError
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

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/stock_alerts.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('StockAlerts.App')

logger = setup_logging()
mimetypes.add_type('application/javascript', '.js')

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
        os.getenv('TELEGRAM_BOT_TOKEN'),
        os.getenv('TELEGRAM_WEBHOOK_SECRET')
    )
    
    app = Flask(__name__)
    app.json_encoder = CustomJSONEncoder
    CORS(app) # Enable CORS for all routes by default for simplicity
    logger.info("Flask app initialized with CORS.")
    
except Exception as e:
    logger.critical(f"FATAL: Error during initialization: {e}", exc_info=True)
    raise

def fetch_yahoo_data_with_retry(ticker_symbol, max_retries=3):
    """Fetch data from Yahoo Finance with retry logic and exponential backoff."""
    ticker = yf.Ticker(ticker_symbol)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching Yahoo Finance data for {ticker_symbol} (attempt {attempt + 1}/{max_retries})")
            complete_data = ticker.history(period="max")
            
            if complete_data.empty:
                logger.warning(f"No data returned from Yahoo Finance for {ticker_symbol}")
                return None
                
            logger.info(f"Successfully fetched {len(complete_data)} data points for {ticker_symbol}")
            return complete_data
            
        except YFRateLimitError as e:
            wait_time = (2 ** attempt) * 2  # Exponential backoff: 2, 4, 8 seconds
            logger.warning(f"Rate limited on attempt {attempt + 1} for {ticker_symbol}. Waiting {wait_time} seconds...")
            
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                time.sleep(wait_time)
            else:
                logger.error(f"Rate limited after {max_retries} attempts for {ticker_symbol}")
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error fetching data for {ticker_symbol} on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:  # Last attempt
                raise
            time.sleep(1)  # Brief pause before retry
    
    return None

def calculate_metrics(ticker_symbol, period="5y"):
    """Calculate stock metrics including MA and percentiles with caching and retry logic."""
    try:
        logger.info(f"Processing request for {ticker_symbol} with period {period}")
        
        valid_periods = ['1y', '3y', '5y', 'max']
        if period not in valid_periods:
            return {"error": f"Invalid period. Must be one of: {', '.join(valid_periods)}"}, 400

        # Check cache first (1 hour cache)
        cached_data = db_manager.get_fresh_cache(ticker_symbol, max_age_hours=1)
        
        if cached_data and cached_data.get('data_json'):
            logger.info(f"Using cached data for {ticker_symbol}")
            try:
                cache_data = json.loads(cached_data['data_json'])
                # Use cached percentiles if available
                if 'percentiles' in cache_data:
                    percentile_5th = cache_data['percentiles']['p5']
                    percentile_95th = cache_data['percentiles']['p95']
                else:
                    # Fallback percentiles
                    percentile_5th = -10.0
                    percentile_95th = 10.0
                    
                # Return cached data notice for now, we'd need to store full historical data for complete cache support
                return {
                    "error": f"Using recent cached data for {ticker_symbol}. Full historical cache not yet implemented.",
                    "cache_info": f"Last updated: {cached_data['last_check']}, Price: ${cached_data['last_price']:.2f}"
                }, 202
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid cached data for {ticker_symbol}: {e}")
                # Continue to fetch fresh data

        # Fetch fresh data with retry logic
        try:
            complete_data = fetch_yahoo_data_with_retry(ticker_symbol)
            
            if complete_data is None or complete_data.empty:
                return {"error": "No data available for this ticker symbol"}, 404

        except YFRateLimitError:
            return {
                "error": "Yahoo Finance is temporarily limiting requests. Please try again in a few minutes.",
                "retry_after": "2-3 minutes"
            }, 429
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {ticker_symbol}: {e}")
            return {"error": "Unable to fetch stock data. Please try again later."}, 500

        # Calculate technical indicators
        complete_data['MA200'] = complete_data['Close'].rolling(window=200).mean()
        complete_data['pct_diff'] = ((complete_data['Close'] - complete_data['MA200']) / complete_data['MA200']) * 100
        
        valid_pct_diff = complete_data['pct_diff'].dropna()
        if len(valid_pct_diff) < 20:
            return {"error": "Insufficient data for meaningful analysis (need at least 20 data points)"}, 400
            
        percentile_5th = np.percentile(valid_pct_diff, 5)
        percentile_95th = np.percentile(valid_pct_diff, 95)

        previous_close = complete_data['Close'].iloc[-2] if len(complete_data) >= 2 else None
        current_price = complete_data['Close'].iloc[-1]
        current_ma_200 = complete_data['MA200'].iloc[-1]

        # Filter data by period
        if period != "max":
            years = int(period[:-1])
            start_date = datetime.now(pytz.utc) - timedelta(days=years*365)
            # Ensure index is timezone-aware for comparison
            if complete_data.index.tz is None:
                complete_data.index = complete_data.index.tz_localize('UTC')
            data = complete_data[complete_data.index >= start_date]
        else:
            data = complete_data

        # Prepare result
        result = {
            "dates": data.index.strftime('%Y-%m-%d').tolist(),
            "prices": data['Close'].fillna(np.nan).replace([np.inf, -np.inf], np.nan).tolist(),
            "ma_200": data['MA200'].fillna(np.nan).replace([np.inf, -np.inf], np.nan).tolist(),
            "pct_diff": data['pct_diff'].fillna(np.nan).replace([np.inf, -np.inf], np.nan).tolist(),
            "percentiles": {"p5": percentile_5th, "p95": percentile_95th},
            "previous_close": previous_close,
        }
        
        # Update cache with fresh data
        cache_data = {
            'price': float(current_price),
            'ma_200': float(current_ma_200) if not pd.isna(current_ma_200) else None,
            'percentiles': {"p5": percentile_5th, "p95": percentile_95th},
            'last_updated': datetime.now().isoformat()
        }
        
        db_manager.update_stock_cache(
            symbol=ticker_symbol,
            price=current_price,
            ma_200=current_ma_200 if not pd.isna(current_ma_200) else None,
            data_json=json.dumps(cache_data)
        )
        
        # Add small delay to be respectful to Yahoo Finance
        time.sleep(0.5)
        
        logger.info(f"Successfully processed {ticker_symbol} with {len(data)} data points")
        return result, 200
        
    except Exception as e:
        error_msg = f"Unexpected error processing {ticker_symbol}: {e}"
        logger.error(error_msg, exc_info=True)
        return {"error": "An unexpected error occurred. Please try again later."}, 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('static/js', filename, mimetype='application/javascript')

@app.route('/data/<ticker>/<period>')
def get_stock_data(ticker, period):
    logger.info(f"Request for ticker: {ticker}, period: {period}")
    result, status_code = calculate_metrics(ticker.upper(), period)
    return jsonify(result), status_code

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if not webhook_handler.validate_webhook(request.get_data(), secret_token):
        logger.warning("Invalid webhook request validation failed.")
        abort(403)
    
    webhook_handler.process_update(request.get_data())
    return '', 200

@app.route('/health', methods=['GET'])
def health_check():
    try:
        db_manager.get_config('telegram_token')
        logger.info("Health check passed")
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not Found'}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server Error: {error}", exc_info=True)
    return jsonify({'error': 'Internal Server Error'}), 500

@app.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5001))
        logger.info(f"Starting Stock Analytics Dashboard server on port {port}...")
        app.run(debug=False, host='0.0.0.0', port=port)
    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True) 