from db_manager import DatabaseManager
from webhook_handler import WebhookHandler
import yfinance as yf
from termcolor import colored
import time
from datetime import datetime
import pytz
import json
import traceback
import logging

logger = logging.getLogger('StockAlerts.PeriodicChecker')

class PeriodicChecker:
    def __init__(self):
        """Initialize the periodic checker."""
        self.db = DatabaseManager()
        self.webhook_handler = WebhookHandler(self.db)
        logger.info("Periodic checker initialized")

    def check_watchlists(self):
        """Check all active watchlists for alerts."""
        try:
            logger.info("Starting watchlist check")
            
            # Get all active watchlists
            watchlists = self.db.get_active_watchlists()
            logger.info(f"Found {len(watchlists)} active watchlists")
            
            for watchlist in watchlists:
                self._process_watchlist_item(watchlist)
                
            logger.info("Watchlist check completed")
            
        except Exception as e:
            error_msg = f"Error checking watchlists: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.db.log_event('error', error_msg)

    def _process_watchlist_item(self, item):
        """Process a single watchlist item."""
        try:
            symbol = item['symbol']
            user_id = item['user_id']
            logger.info(f"Processing {symbol} for user {user_id}")
            
            # Get ALL historical data instead of just 1 year
            ticker = yf.Ticker(symbol)
            historical_data = ticker.history(period="max")  # Get maximum available history
            
            if historical_data.empty:
                logger.warning(f"No data available for {symbol}")
                return
            
            current_price = float(historical_data['Close'].iloc[-1])
            logger.debug(f"{symbol} current price: ${current_price}")
            
            # Calculate 200-day MA for the entire dataset
            historical_data['ma_200'] = historical_data['Close'].rolling(window=200).mean()
            
            # Calculate percent differences from MA
            historical_data['pct_diff'] = ((historical_data['Close'] - historical_data['ma_200']) / historical_data['ma_200']) * 100
            
            # Remove NaN values (first 200 days won't have MA)
            valid_diffs = historical_data['pct_diff'].dropna()
            
            # Calculate current percent difference
            current_ma_200 = float(historical_data['ma_200'].iloc[-1])
            current_pct_diff = ((current_price - current_ma_200) / current_ma_200) * 100
            
            # Calculate historical percentiles using all data
            percentile_5 = float(valid_diffs.quantile(0.05))
            percentile_95 = float(valid_diffs.quantile(0.95))
            
            logger.debug(f"{symbol} current percent difference from MA: {current_pct_diff:.2f}%")
            logger.debug(f"{symbol} 5th percentile: {percentile_5:.2f}%, 95th percentile: {percentile_95:.2f}%")
            logger.debug(f"{symbol} historical min: {valid_diffs.min():.2f}%, max: {valid_diffs.max():.2f}%")
            
            # Update stock cache
            cache_data = {
                'last_updated': datetime.now().isoformat(),
                'price': current_price,
                'ma_200': current_ma_200,
                'pct_diff': current_pct_diff,
                'percentile_5': percentile_5,
                'percentile_95': percentile_95,
                'historical_min': float(valid_diffs.min()),
                'historical_max': float(valid_diffs.max())
            }
            
            self.db.update_stock_cache(
                symbol=symbol,
                price=current_price,
                ma_200=current_ma_200,
                data_json=json.dumps(cache_data)
            )
            
            # Check if we should alert - now comparing against actual percentiles
            if (current_pct_diff <= percentile_5 or current_pct_diff >= percentile_95):
                logger.info(f"Alert threshold reached for {symbol} - Current: {current_pct_diff:.2f}%, 5th: {percentile_5:.2f}%, 95th: {percentile_95:.2f}%")
                
                # Send alert with percentile information
                self.webhook_handler.send_alert(
                    user_id=user_id,
                    symbol=symbol,
                    price=current_price,
                    percentile=current_pct_diff,
                    percentile_5=percentile_5,
                    percentile_95=percentile_95
                )
                
        except Exception as e:
            error_msg = f"Error processing {item['symbol']}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.db.log_event(
                'error',
                error_msg,
                user_id=item['user_id'],
                symbol=item['symbol']
            )

def main():
    """Main function to run the periodic checker."""
    checker = PeriodicChecker()
    
    logger.info("Starting periodic checker service")
    
    # Run immediately
    checker.check_watchlists()
    
    # Comment out the scheduling logic
    # while True:
    #     try:
    #         now = datetime.now(pytz.UTC)
    #         if now.strftime('%A').lower() == 'sunday' and now.hour == 18:
    #             logger.info("Running scheduled watchlist check")
    #             checker.check_watchlists()
    #         time.sleep(3600)
    #     except Exception as e:
    #         error_msg = f"Error in main loop: {str(e)}\n{traceback.format_exc()}"
    #         logger.error(error_msg)
    #         time.sleep(300)  # Sleep for 5 minutes on error

if __name__ == '__main__':
    main() 