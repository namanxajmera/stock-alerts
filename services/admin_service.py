"""
Admin service for handling admin panel operations.

This service provides admin-related functionality including:
- Admin panel data retrieval
- Database queries for admin operations
"""

import logging
from typing import Any, Dict, List

import psycopg2.extras


class AdminService:
    """Service class for admin operations."""

    def __init__(self, db_manager: Any) -> None:
        """
        Initialize the AdminService.

        Args:
            db_manager: Database manager instance for database operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger("StockAlerts.AdminService")

    def get_admin_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all admin panel data from the database.

        Returns:
            Dictionary containing users, watchlist, alerts, cache, and config data

        Raises:
            Exception: If database operations fail
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # Users
                cursor.execute("SELECT * FROM users")
                users = cursor.fetchall()

                # Watchlist items
                cursor.execute("SELECT * FROM watchlist_items ORDER BY user_id, symbol")
                watchlist = cursor.fetchall()

                # Alert history (last 50)
                cursor.execute(
                    "SELECT * FROM alert_history ORDER BY sent_at DESC LIMIT 50"
                )
                alerts = cursor.fetchall()

                # Stock cache
                cursor.execute("SELECT * FROM stock_cache ORDER BY last_check DESC")
                cache = cursor.fetchall()

                # Config (filter out sensitive data)
                cursor.execute("SELECT * FROM config WHERE key != 'telegram_token'")
                config = cursor.fetchall()

                return {
                    "users": users,
                    "watchlist": watchlist,
                    "alerts": alerts,
                    "cache": cache,
                    "config": config,
                }

        except Exception as e:
            self.logger.error(f"Error retrieving admin data: {e}", exc_info=True)
            raise

    def trigger_stock_check(self) -> None:
        """
        Trigger a manual stock check operation.

        Raises:
            Exception: If the stock check operation fails
        """
        try:
            self.logger.info("Triggering manual stock check...")

            # Import and run the periodic checker
            from periodic_checker import PeriodicChecker

            checker = PeriodicChecker()
            checker.check_watchlists()

            self.logger.info("Manual stock check completed successfully")

        except Exception as e:
            self.logger.error(f"Error in manual stock check: {e}", exc_info=True)
            raise
