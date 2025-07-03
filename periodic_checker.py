from db_manager import DatabaseManager
from webhook_handler import WebhookHandler
from tiingo import TiingoClient
import time
from datetime import datetime, timedelta
import json
import traceback
import logging
from collections import defaultdict
import os
import pandas as pd

logger = logging.getLogger('StockAlerts.PeriodicChecker')

class PeriodicChecker:
    def __init__(self):
        """Initialize the periodic checker."""
        self.db = DatabaseManager()
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.webhook_handler = WebhookHandler(self.db, bot_token)
        logger.info("Periodic checker initialized")

    def check_watchlists(self):
        """Check all active watchlists for alerts efficiently."""
        try:
            logger.info("Starting watchlist check")
            
            watchlists = self.db.get_active_watchlists()
            if not watchlists:
                logger.info("No active watchlists to check.")
                return

            # Group users by symbol to fetch data only once per symbol
            symbol_user_map = defaultdict(list)
            for item in watchlists:
                symbol_user_map[item['symbol']].append(item['user_id'])
            
            logger.info(f"Found {len(watchlists)} total watchlist items for {len(symbol_user_map)} unique symbols.")
            
            for symbol, user_ids in symbol_user_map.items():
                self._process_symbol(symbol, user_ids)
                # Longer delay between symbols to be more respectful
                symbol_delay = float(os.getenv('YF_REQUEST_DELAY', 3.0))
                time.sleep(symbol_delay)

            logger.info("Watchlist check completed")
            
        except Exception as e:
            error_msg = f"Error checking watchlists: {e}"
            logger.error(error_msg, exc_info=True)
            self.db.log_event('error', f"{error_msg}\n{traceback.format_exc()}")

    def _fetch_symbol_data_tiingo(self, symbol):
        """Fetch symbol data from Tiingo API using direct REST calls."""
        try:
            # Get API token from environment
            api_token = os.getenv('TIINGO_API_TOKEN')
            if not api_token:
                raise ValueError("TIINGO_API_TOKEN not found in environment variables")
            
            logger.info(f"Fetching Tiingo data for {symbol}")
            
            # Calculate start date for sufficient historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2*365)  # 2 years should be enough for periodic checks
            
            # Build the REST API URL as per Tiingo docs
            url = f"https://api.tiingo.com/tiingo/daily/{symbol}/prices"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Token {api_token}'
            }
            
            params = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d')
            }
            
            # Make the API request
            import requests
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No data available for {symbol}")
                return None
            
            # Convert JSON response to DataFrame
            df = pd.DataFrame(data)
            
            # Rename columns to match expected format
            column_mapping = {
                'date': 'Date',
                'adjClose': 'Close',
            }
            
            # Select and rename only the columns we need
            df_filtered = df[list(column_mapping.keys())].rename(columns=column_mapping)
            
            # Convert date string to datetime and set as index
            df_filtered['Date'] = pd.to_datetime(df_filtered['Date'])
            df_filtered.set_index('Date', inplace=True)
            
            # Sort by date (oldest first)
            df_filtered = df_filtered.sort_index()
            
            logger.info(f"Successfully fetched {len(df_filtered)} data points for {symbol} from Tiingo")
            return df_filtered
            
        except Exception as e:
            logger.error(f"Error fetching data from Tiingo for {symbol}: {e}")
            return None

    def _process_symbol(self, symbol, user_ids):
        """Process a single symbol for all interested users."""
        logger.info(f"Processing {symbol} for {len(user_ids)} user(s)")
        try:
            # Check cache first
            cached_data = self.db.get_fresh_cache(symbol, max_age_hours=2)  # Longer cache for periodic checker
            
            if cached_data:
                logger.info(f"Using cached data for {symbol} in periodic check")
                try:
                    cache_data = json.loads(cached_data['data_json'])
                    current_price = cached_data['last_price']
                    current_ma_200 = cached_data['ma_200']
                    
                    if 'percentiles' in cache_data:
                        percentile_5 = cache_data['percentiles']['p5']
                        percentile_95 = cache_data['percentiles']['p95']
                        current_pct_diff = ((current_price - current_ma_200) / current_ma_200) * 100
                        
                        # Check if alert should be sent
                        if current_pct_diff <= percentile_5 or current_pct_diff >= percentile_95:
                            logger.info(f"ALERT TRIGGERED for {symbol} at {current_pct_diff:.2f}% (cached data)")
                            for user_id in user_ids:
                                self.webhook_handler.send_alert(
                                    user_id=user_id, symbol=symbol, price=current_price,
                                    percentile=current_pct_diff, percentile_5=percentile_5, percentile_95=percentile_95
                                )
                        return
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Invalid cached data for {symbol}: {e}")
            
            # Fetch fresh data from Tiingo API
            historical_data = self._fetch_symbol_data_tiingo(symbol)
            
            if historical_data is None:
                logger.error(f"Failed to fetch data for {symbol} after retries")
                return
            
            current_price = float(historical_data['Close'].iloc[-1])
            
            # Calculate metrics
            historical_data['ma_200'] = historical_data['Close'].rolling(window=200).mean()
            historical_data['pct_diff'] = ((historical_data['Close'] - historical_data['ma_200']) / historical_data['ma_200']) * 100
            valid_diffs = historical_data['pct_diff'].dropna()

            if valid_diffs.empty:
                logger.warning(f"Not enough data to calculate MA for {symbol}")
                return

            current_ma_200 = float(historical_data['ma_200'].iloc[-1])
            current_pct_diff = ((current_price - current_ma_200) / current_ma_200) * 100
            
            percentile_5 = float(valid_diffs.quantile(0.05))
            percentile_95 = float(valid_diffs.quantile(0.95))
            
            logger.debug(f"{symbol} | Price: ${current_price:.2f} | MA200: ${current_ma_200:.2f} | Diff: {current_pct_diff:.2f}%")
            logger.debug(f"{symbol} | 5th Pct: {percentile_5:.2f}% | 95th Pct: {percentile_95:.2f}%")
            
            # Update stock cache
            cache_data = {
                'price': current_price, 'ma_200': current_ma_200, 'pct_diff': current_pct_diff,
                'percentile_5': percentile_5, 'percentile_95': percentile_95,
                'historical_min': float(valid_diffs.min()), 'historical_max': float(valid_diffs.max())
            }
            self.db.update_stock_cache(
                symbol=symbol, price=current_price, ma_200=current_ma_200, data_json=json.dumps(cache_data)
            )
            
            # Check if an alert should be sent
            if current_pct_diff <= percentile_5 or current_pct_diff >= percentile_95:
                logger.info(f"ALERT TRIGGERED for {symbol} at {current_pct_diff:.2f}%")
                for user_id in user_ids:
                    logger.info(f"Sending alert for {symbol} to user {user_id}")
                    self.webhook_handler.send_alert(
                        user_id=user_id, symbol=symbol, price=current_price,
                        percentile=current_pct_diff, percentile_5=percentile_5, percentile_95=percentile_95
                    )
            else:
                logger.info(f"No alert for {symbol} (current diff: {current_pct_diff:.2f}%)")

        except Exception as e:
            error_msg = f"Error processing symbol {symbol}: {e}"
            logger.error(error_msg, exc_info=True)
            self.db.log_event('error', error_msg, symbol=symbol)

def main():
    """Main function to run the periodic checker."""
    # This script is intended to be run by a scheduler like cron.
    # The infinite loop is removed in favor of single-run execution.
    logger.info("Starting periodic checker run...")
    checker = PeriodicChecker()
    checker.check_watchlists()
    logger.info("Periodic checker run finished.")

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    main() 