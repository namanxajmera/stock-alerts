"""
Periodic stock price checker for Stock Alerts application.

This module handles periodic checking of stock prices for all users'
watchlists and sends alerts when price conditions are met.
"""

import json
import logging
import os
import time
import traceback
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import DatabaseManager
from type_definitions.stock_types import DataFrameType
from utils.config import config
from utils.tiingo_client import TiingoClient

# from type_definitions.api_types import TiingoResponse  # Not needed for type hints

logger = logging.getLogger("StockAlerts.PeriodicChecker")


class PeriodicChecker:
    """Periodic checker for stock prices and alert generation."""

    def __init__(self, db_manager: DatabaseManager, notification_service: Any) -> None:
        """Initialize the periodic checker with required dependencies."""
        self.db = db_manager
        self.notification_service = notification_service
        self.tiingo_client = TiingoClient()
        logger.info("Periodic checker initialized")

    def check_watchlists(self) -> None:
        """Check all active watchlists for alerts efficiently."""
        try:
            # Check if today is a valid alert day (Mon-Thu, Sun) using UTC
            today = datetime.utcnow().weekday()  # 0=Monday, 6=Sunday
            valid_days = [0, 1, 2, 3, 6]  # Monday-Thursday, Sunday
            
            if today not in valid_days:
                day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][today]
                logger.info(f"Skipping watchlist check - today is {day_name} (UTC). Alerts only run Mon-Thu and Sunday.")
                return
                
            logger.info("Starting watchlist check")

            watchlists = self.db.get_active_watchlists()
            if not watchlists:
                logger.info("No active watchlists to check.")
                return

            # Group users by symbol with ownership info
            symbol_user_map = defaultdict(list)
            for item in watchlists:
                symbol_user_map[item["symbol"]].append({
                    "user_id": str(item["user_id"]),
                    "is_owned": item.get("is_owned", False)
                })

            logger.info(
                f"Found {len(watchlists)} total watchlist items for {len(symbol_user_map)} unique symbols."
            )

            # Collect all alerts by user instead of sending immediately
            user_alerts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

            for symbol, user_data_list in symbol_user_map.items():
                alert_data = self._process_symbol(str(symbol), user_data_list)
                if alert_data:  # If this symbol triggered an alert
                    for user_data in user_data_list:
                        # Add ownership info to alert data
                        alert_with_ownership = alert_data.copy()
                        alert_with_ownership["is_owned"] = user_data["is_owned"]
                        user_id = str(user_data["user_id"])
                        user_alerts[user_id].append(alert_with_ownership)
                # Longer delay between symbols to be more respectful
                time.sleep(config.TIINGO_REQUEST_DELAY)

            # Send combined alerts to each user
            self._send_batched_alerts(user_alerts)

            logger.info("Watchlist check completed")

        except Exception as e:
            error_msg = f"Error checking watchlists: {e}"
            logger.error(error_msg, exc_info=True)
            self.db.log_event("error", f"{error_msg}\n{traceback.format_exc()}")

    def _fetch_symbol_data_tiingo(
        self, symbol: str, max_retries: int = 3
    ) -> Optional[DataFrameType]:
        """Fetch symbol data from Tiingo API using the centralized client."""
        return self.tiingo_client.fetch_historical_data(symbol, "2y", max_retries)

    def _process_symbol(
        self, symbol: str, user_data_list: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Process a single symbol for all interested users."""
        logger.info(f"Processing {symbol} for {len(user_data_list)} user(s)")
        try:
            # Check cache first
            cached_data = self.db.get_fresh_cache(
                symbol, max_age_hours=config.CACHE_HOURS
            )

            if cached_data:
                logger.info(f"Using cached data for {symbol} in periodic check")
                try:
                    cache_data = json.loads(cached_data["data_json"])
                    current_price = cached_data["last_price"]
                    current_ma_200 = cached_data["ma_200"]

                    if "percentiles" in cache_data:
                        percentile_16 = cache_data["percentiles"]["p16"]
                        percentile_84 = cache_data["percentiles"]["p84"]
                        current_pct_diff = (
                            (current_price - current_ma_200) / current_ma_200
                        ) * 100

                        # Check if alert should be sent
                        if (
                            current_pct_diff <= percentile_16
                            or current_pct_diff >= percentile_84
                        ):
                            logger.info(
                                f"ALERT TRIGGERED for {symbol} at {current_pct_diff:.2f}% (cached data)"
                            )
                            return {
                                "symbol": symbol,
                                "price": current_price,
                                "percentile": current_pct_diff,
                                "percentile_16": percentile_16,
                                "percentile_84": percentile_84,
                            }
                        return None
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Invalid cached data for {symbol}: {e}")

            # Fetch fresh data from Tiingo API
            historical_data = self._fetch_symbol_data_tiingo(symbol)

            if historical_data is None:
                logger.error(f"Failed to fetch data for {symbol} after retries")
                return None

            current_price = float(historical_data["Close"].iloc[-1])

            # Calculate metrics
            historical_data["ma_200"] = (
                historical_data["Close"].rolling(window=200).mean()
            )
            historical_data["pct_diff"] = (
                (historical_data["Close"] - historical_data["ma_200"])
                / historical_data["ma_200"]
            ) * 100
            valid_diffs = historical_data["pct_diff"].dropna()

            if valid_diffs.empty:
                logger.warning(f"Not enough data to calculate MA for {symbol}")
                return None

            current_ma_200 = float(historical_data["ma_200"].iloc[-1])
            current_pct_diff = ((current_price - current_ma_200) / current_ma_200) * 100

            percentile_16 = float(valid_diffs.quantile(0.16))
            percentile_84 = float(valid_diffs.quantile(0.84))

            logger.debug(
                f"{symbol} | Price: ${current_price:.2f} | MA200: ${current_ma_200:.2f} | Diff: {current_pct_diff:.2f}%"
            )
            logger.debug(
                f"{symbol} | 16th Pct: {percentile_16:.2f}% | 84th Pct: {percentile_84:.2f}%"
            )

            # Update stock cache
            cache_data = {
                "price": current_price,
                "ma_200": current_ma_200,
                "pct_diff": current_pct_diff,
                "percentile_16": percentile_16,
                "percentile_84": percentile_84,
                "historical_min": float(valid_diffs.min()),
                "historical_max": float(valid_diffs.max()),
            }
            self.db.update_stock_cache(
                symbol=symbol,
                price=current_price,
                ma_200=current_ma_200,
                data_json=json.dumps(cache_data),
            )

            # Check if an alert should be sent
            if current_pct_diff <= percentile_16 or current_pct_diff >= percentile_84:
                logger.info(f"ALERT TRIGGERED for {symbol} at {current_pct_diff:.2f}%")
                return {
                    "symbol": symbol,
                    "price": current_price,
                    "percentile": current_pct_diff,
                    "percentile_16": percentile_16,
                    "percentile_84": percentile_84,
                }
            else:
                logger.info(
                    f"No alert for {symbol} (current diff: {current_pct_diff:.2f}%)"
                )
                return None

        except Exception as e:
            error_msg = f"Error processing symbol {symbol}: {e}"
            logger.error(error_msg, exc_info=True)
            self.db.log_event("error", error_msg, symbol=symbol)
            return None

    def _send_batched_alerts(
        self, user_alerts: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """Send combined alerts to each user."""
        for user_id, alerts in user_alerts.items():
            if alerts:  # Only send if user has alerts
                logger.info(
                    f"Sending batched alerts to user {user_id} for {len(alerts)} stocks"
                )
                self.notification_service.send_batched_alerts(user_id, alerts)


from features.webhook_handler import WebhookHandler


def main() -> None:
    """Main function to run the periodic checker."""
    # This script is intended to be run by a scheduler like cron.
    # The infinite loop is removed in favor of single-run execution.
    from services.notification_service import NotificationService
    
    logger.info("Starting periodic checker run...")
    db_manager = DatabaseManager(config.DATABASE_URL)
    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not configured")
    webhook_handler = WebhookHandler(
        db_manager,
        config.TELEGRAM_BOT_TOKEN,
        config.TELEGRAM_WEBHOOK_SECRET,
    )
    notification_service = NotificationService(db_manager, webhook_handler)
    checker = PeriodicChecker(db_manager, notification_service)
    checker.check_watchlists()
    logger.info("Periodic checker run finished.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    main()