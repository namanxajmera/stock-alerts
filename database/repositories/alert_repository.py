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
        except Exception as e:
            # Check if it's a sequence issue and try to fix it
            if "duplicate key value violates unique constraint" in str(e) and "alert_history" in str(e):
                logger.warning(f"Sequence issue detected for alert_history, attempting to fix...")
                try:
                    self._fix_alert_history_sequence()
                    # Retry the insert
                    with self.connection_manager.get_cursor(commit=True) as cursor:
                        cursor.execute(
                            sql,
                            (user_id, symbol.upper(), price, percentile, status, error_message),
                        )
                    logger.info(f"Added alert history for {symbol} for user {user_id} after sequence fix")
                    return True
                except Exception as retry_error:
                    logger.error(f"Failed to add alert history even after sequence fix: {retry_error}")
                    return False
            else:
                logger.error(f"Error adding alert history for {symbol} user {user_id}: {e}")
                return False

    def _fix_alert_history_sequence(self) -> None:
        """Fix the alert_history sequence to be in sync with the table data."""
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                # Check if sequence exists first
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_class WHERE relname = 'alert_history_id_seq'
                    );
                """)
                sequence_exists = cursor.fetchone()[0]
                
                if sequence_exists:
                    cursor.execute("""
                        SELECT setval('alert_history_id_seq', 
                                     COALESCE((SELECT MAX(id) FROM alert_history), 1), 
                                     true);
                    """)
                    new_value = cursor.fetchone()[0]
                    logger.info(f"Fixed alert_history sequence, set to {new_value}")
                else:
                    logger.warning("alert_history_id_seq sequence does not exist, cannot fix")
                    # This might indicate the table uses a different primary key setup
                    # We should investigate the table structure
                    cursor.execute("SELECT column_name, column_default FROM information_schema.columns WHERE table_name = 'alert_history' AND column_name = 'id';")
                    id_info = cursor.fetchone()
                    if id_info:
                        logger.info(f"alert_history.id column info: {id_info}")
                    else:
                        logger.warning("alert_history table does not have an 'id' column")
        except Exception as e:
            logger.error(f"Failed to fix alert_history sequence: {e}")
            raise

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