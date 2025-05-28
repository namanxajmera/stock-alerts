import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('.env')

def setup_directories():
    """Create necessary directories if they don't exist."""
    directories = ['logs', 'db', 'static/js']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Create directories before any other imports
setup_directories()

from flask import Flask, render_template, jsonify, send_from_directory, request, abort
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
from termcolor import colored
import traceback
import json
from datetime import datetime, timedelta
import pytz
import mimetypes
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

# Setup logging after directories are created
logger = setup_logging()

# Add proper MIME type for JavaScript modules
mimetypes.add_type('application/javascript', '.js')

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NaN/Infinity values."""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        return super().default(obj)

try:
    # Initialize database and webhook handler
    logger.info("Initializing database manager...")
    db_manager = DatabaseManager()
    
    logger.info("Initializing webhook handler...")
    webhook_handler = WebhookHandler(db_manager)
    
    app = Flask(__name__)
    app.json_encoder = CustomJSONEncoder
    
    # Configure CORS with proper settings
    CORS(app, resources={
        r"/data/*": {"origins": "*"},
        r"/webhook": {"origins": "api.telegram.org"}
    })
    logger.info("CORS configured successfully")
    
except Exception as e:
    logger.error(f"Error during initialization: {str(e)}")
    logger.error(traceback.format_exc())
    raise

def calculate_metrics(ticker_symbol, period="5y"):
    """Calculate stock metrics including MA and percentiles."""
    try:
        logger.info(f"Fetching data for {ticker_symbol} with period {period}")
        
        # Validate period
        valid_periods = ['1y', '3y', '5y', 'max']
        if period not in valid_periods:
            logger.warning(f"Invalid period requested: {period}")
            return {"error": f"Invalid period. Must be one of: {', '.join(valid_periods)}"}, 400

        # Create ticker object
        ticker = yf.Ticker(ticker_symbol)
        
        # Fetch complete historical data
        logger.info("Downloading historical data...")
        complete_data = ticker.history(period="max")
        
        if complete_data.empty:
            logger.warning(f"No data available for ticker {ticker_symbol}")
            return {"error": "No data available for ticker"}, 404

        logger.info(f"Retrieved {len(complete_data)} total data points")

        # Calculate metrics
        complete_data['MA200'] = complete_data['Close'].rolling(window=200).mean()
        complete_data['pct_diff'] = ((complete_data['Close'] - complete_data['MA200']) / complete_data['MA200']) * 100
        
        # Calculate percentiles
        valid_pct_diff = complete_data['pct_diff'].dropna()
        if len(valid_pct_diff) == 0:
            logger.warning("Insufficient data for analysis")
            return {"error": "Insufficient data for analysis"}, 400
            
        percentile_5th = float(np.percentile(valid_pct_diff, 5))
        percentile_95th = float(np.percentile(valid_pct_diff, 95))

        # Filter data for requested period
        if period != "max":
            years = int(period[:-1])
            ny_tz = pytz.timezone('America/New_York')
            start_date = datetime.now(ny_tz) - timedelta(days=years*365)
            data = complete_data[complete_data.index >= start_date]
        else:
            data = complete_data

        logger.info(f"Filtered to {len(data)} data points for requested period")

        result = {
            "dates": data.index.strftime('%Y-%m-%d').tolist(),
            "prices": [float(x) if not np.isnan(x) else None for x in data['Close']],
            "ma_200": [float(x) if not np.isnan(x) else None for x in data['MA200']],
            "pct_diff": [float(x) if not np.isnan(x) else None for x in data['pct_diff']],
            "percentiles": {
                "p5": percentile_5th,
                "p95": percentile_95th
            }
        }
        
        logger.info("Data processing completed successfully")
        return result, 200
        
    except Exception as e:
        error_msg = f"Error processing data: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {"error": f"Failed to process data: {str(e)}"}, 500

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/static/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files with correct MIME type."""
    response = send_from_directory('static/js', filename)
    response.headers['Content-Type'] = 'application/javascript'
    return response

@app.route('/data/<ticker>/<period>')
def get_stock_data(ticker, period):
    """Get stock data for the specified ticker and period."""
    logger.info(f"Received request for ticker: {ticker}, period: {period}")
    result, status_code = calculate_metrics(ticker.upper(), period)
    return jsonify(result), status_code

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Handle incoming updates from Telegram."""
    logger.info("Received webhook request from Telegram")
    
    if not webhook_handler.validate_webhook(request.get_data()):
        logger.warning("Invalid webhook request")
        abort(403)
    
    success = webhook_handler.process_update(request.get_data())
    return '', 200 if success else 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        db_manager.get_config('test')
        logger.info("Health check passed")
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        error_msg = f"Health check failed: {str(e)}"
        logger.error(error_msg)
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.url}")
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"500 error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(403)
def forbidden(error):
    logger.warning(f"403 error: {request.url}")
    return jsonify({'error': 'Forbidden'}), 403

if __name__ == '__main__':
    try:
        logger.info("Starting Stock Analytics Dashboard server...")
        logger.info("Available at http://localhost:5001")
        app.run(debug=True, host='0.0.0.0', port=5001)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        logger.error(traceback.format_exc())
        raise 