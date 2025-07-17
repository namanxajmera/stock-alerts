"""
Alert repository for handling alert-related database operations.

This repository encapsulates all alert-related database operations including
alert history, active watchlists, and notification management.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from database.connection_manager import ConnectionManager

logger = logging.getLogger("StockAlerts.AlertRepository")


class AlertRepository:
    """Repository class for alert-related database operations."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """
        Initialize the AlertRepository.

        Args:
            connection_manager: Database connection manager instance
        """
        self.connection_manager = connection_manager
        self.logger = logging.getLogger("StockAlerts.AlertRepository")

    def add_alert_history(
        self,
        user_id: Union[str, int],
        symbol: str,
        price: float,
        percentile: float,
        status: str = "sent",
        error_message: Optional[str] = None,
    ) -> bool:
        """Add an alert to the history."""
        sql = """
            INSERT INTO alert_history (user_id, symbol, price, percentile, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute(
                    sql,
                    (user_id, symbol.upper(), price, percentile, status, error_message),
                )
            logger.info(f"Added alert history for {symbol} for user {user_id}")
            return True
        except Exception:
            logger.error(f"Error adding alert history for {symbol} user {user_id}")
            return False

    def get_active_watchlists(self) -> List[Dict[str, Union[str, int]]]:
        """Get all active watchlists."""
        sql = """
            SELECT w.user_id, w.symbol, w.is_owned
            FROM watchlist_items w
            JOIN users u ON w.user_id = u.id
            WHERE u.notification_enabled = TRUE
        """
        try:
            with self.connection_manager.get_cursor() as cursor:
                cursor.execute(sql)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting active watchlists: {e}")
            return []