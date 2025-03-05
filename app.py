from flask import Flask, render_template, jsonify, send_from_directory
from flask_cors import CORS  # Add CORS support
import yfinance as yf
import pandas as pd
import numpy as np
from termcolor import colored
import traceback
import json
from datetime import datetime, timedelta
import pytz
import mimetypes

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

app = Flask(__name__)
app.json_encoder = CustomJSONEncoder  # Use custom JSON encoder
CORS(app)  # Enable CORS for all routes

# Add route to serve JavaScript files with correct MIME type
@app.route('/static/js/<path:filename>')
def serve_js(filename):
    response = send_from_directory('static/js', filename)
    response.headers['Content-Type'] = 'application/javascript'
    return response

def calculate_metrics(ticker_symbol, period="5y"):
    """Calculate stock metrics including MA and percentiles."""
    try:
        print(colored(f"Fetching data for {ticker_symbol} with period {period}...", "cyan"))
        
        # Validate period
        valid_periods = ['1y', '3y', '5y', 'max']
        if period not in valid_periods:
            print(colored(f"Invalid period: {period}", "red"))
            return {"error": f"Invalid period. Must be one of: {', '.join(valid_periods)}"}, 400

        # Create ticker object with proper config
        ticker = yf.Ticker(ticker_symbol)
        
        # First fetch complete historical data for calculations
        print(colored("Downloading complete historical data...", "cyan"))
        complete_data = ticker.history(period="max")
        
        if complete_data.empty:
            print(colored(f"No data available for ticker {ticker_symbol}", "yellow"))
            return {"error": "No data available for ticker"}, 404

        print(colored(f"Retrieved {len(complete_data)} total data points", "green"))

        # Calculate 200-day moving average on complete dataset
        complete_data['MA200'] = complete_data['Close'].rolling(window=200).mean()
        
        # Calculate percentage difference from MA
        complete_data['pct_diff'] = ((complete_data['Close'] - complete_data['MA200']) / complete_data['MA200']) * 100
        
        # Calculate percentiles on complete dataset
        valid_pct_diff = complete_data['pct_diff'].dropna()
        if len(valid_pct_diff) == 0:
            return {"error": "Insufficient data for analysis"}, 400
            
        percentile_5th = float(np.percentile(valid_pct_diff, 5))
        percentile_95th = float(np.percentile(valid_pct_diff, 95))

        # Filter data for requested period
        if period != "max":
            years = int(period[:-1])
            # Create timezone-aware datetime for comparison
            ny_tz = pytz.timezone('America/New_York')
            start_date = datetime.now(ny_tz) - timedelta(days=years*365)
            data = complete_data[complete_data.index >= start_date]
        else:
            data = complete_data

        print(colored(f"Filtered to {len(data)} data points for requested period", "green"))

        # Convert numpy arrays to lists, replacing NaN with None
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
        
        print(colored("Data processing completed successfully", "green"))
        return result, 200
        
    except Exception as e:
        error_msg = f"Error processing data: {str(e)}\n{traceback.format_exc()}"
        print(colored(error_msg, "red"))
        return {"error": f"Failed to process data: {str(e)}"}, 500

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/data/<ticker>/<period>')
def get_stock_data(ticker, period):
    """Get stock data for the specified ticker and period."""
    print(colored(f"Received request for ticker: {ticker}, period: {period}", "cyan"))
    result, status_code = calculate_metrics(ticker.upper(), period)
    return jsonify(result), status_code

if __name__ == '__main__':
    print(colored("\nStarting Stock Analytics Dashboard server...", "green"))
    print(colored("Available at http://localhost:5001", "cyan"))
    app.run(debug=True, host='0.0.0.0', port=5001) 