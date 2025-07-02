from db_manager import DatabaseManager
from webhook_handler import WebhookHandler
import yfinance as yf
from yfinance.exceptions import YFRateLimitError
import time
from datetime import datetime
import json
import traceback
import logging
from collections import defaultdict
import os

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
                time.sleep(1) # Be respectful to the API provider

            logger.info("Watchlist check completed")
            
        except Exception as e:
            error_msg = f"Error checking watchlists: {e}"
            logger.error(error_msg, exc_info=True)
            self.db.log_event('error', f"{error_msg}\n{traceback.format_exc()}")

    def _fetch_symbol_data_with_retry(self, symbol, max_retries=3):
        """Fetch symbol data with retry logic for rate limiting."""
        ticker = yf.Ticker(symbol)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching data for {symbol} (attempt {attempt + 1}/{max_retries})")
                historical_data = ticker.history(period="max")
                
                if historical_data.empty:
                    logger.warning(f"No data available for {symbol}")
                    return None
                    
                return historical_data
                
            except YFRateLimitError:
                wait_time = (2 ** attempt) * 5  # Exponential backoff: 5, 10, 20 seconds
                logger.warning(f"Rate limited on attempt {attempt + 1} for {symbol}. Waiting {wait_time} seconds...")
                
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error(f"Rate limited after {max_retries} attempts for {symbol}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error fetching data for {symbol} on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2)  # Brief pause before retry
        
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
            
            # Fetch fresh data with retry logic
            historical_data = self._fetch_symbol_data_with_retry(symbol)
            
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