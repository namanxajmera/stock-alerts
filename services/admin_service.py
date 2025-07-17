"""
Admin service for handling admin panel operations.

This service provides admin-related functionality including:
- Admin panel data retrieval
- Database queries for admin operations
"""

import logging
from typing import Any, Dict, List, TYPE_CHECKING

import psycopg2.extras

if TYPE_CHECKING:
    from features import PeriodicChecker


class AdminService:
    """Service class for admin operations."""

    def __init__(
        self, db_manager: Any, notification_service: Any, periodic_checker: "PeriodicChecker"
    ) -> None:
        """
        Initialize the AdminService.

        Args:
            db_manager: Database manager instance for database operations
            notification_service: Notification service for sending alerts
            periodic_checker: PeriodicChecker instance for triggering checks
        """
        self.db_manager = db_manager
        self.notification_service = notification_service
        self.periodic_checker = periodic_checker
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
            # Use the new repository pattern method
            return dict(self.db_manager.get_admin_data())
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
            self.periodic_checker.check_watchlists()
            self.logger.info("Manual stock check completed successfully")

        except Exception as e:
            self.logger.error(f"Error in manual stock check: {e}", exc_info=True)
            raise