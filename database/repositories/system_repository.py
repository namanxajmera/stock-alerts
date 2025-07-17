"""
System repository for handling system-related database operations.

This repository encapsulates system-related database operations including
logging, configuration, and rate limiting.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from database.connection_manager import ConnectionManager

logger = logging.getLogger("StockAlerts.SystemRepository")


class SystemRepository:
    """Repository class for system-related database operations."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """
        Initialize the SystemRepository.

        Args:
            connection_manager: Database connection manager instance
        """
        self.connection_manager = connection_manager
        self.logger = logging.getLogger("StockAlerts.SystemRepository")

    def log_event(
        self,
        log_type: str,
        message: str,
        user_id: Optional[Union[str, int]] = None,
        symbol: Optional[str] = None,
    ) -> None:
        """Log an event to the database."""
        sql = "INSERT INTO logs (timestamp, log_type, message, user_id, symbol) VALUES (NOW(), %s, %s, %s, %s)"
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute(sql, (log_type, message, user_id, symbol))
        except Exception as e:
            # Log to logger as a fallback if DB logging fails
            logger.error(f"CRITICAL: Failed to write log to database: {e}")
            logger.error(f"Original log message: [{log_type}] {message}")

    def get_config(self, key: str) -> Optional[str]:
        """Get configuration value."""
        try:
            with self.connection_manager.get_cursor() as cursor:
                cursor.execute("SELECT value FROM config WHERE key = %s", (key,))
                row = cursor.fetchone()
                return row["value"] if row else None
        except Exception:
            logger.error(f"Error getting config for key {key}")
            return None

    # Rate Limiting Methods
    def record_api_request(self, api_name: str, success: bool = True) -> bool:
        """Record an API request for rate limiting."""
        sql = """
            INSERT INTO api_requests (api_name, request_time, success)
            VALUES (%s, NOW(), %s)
        """
        
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute(sql, (api_name, success))
                return True
        except Exception as e:
            logger.error(f"Error recording API request: {e}")
            return False

    def get_api_request_count(
        self, api_name: str, start_time: datetime, end_time: datetime
    ) -> int:
        """Get the number of API requests in a time period."""
        sql = """
            SELECT COUNT(*) as count
            FROM api_requests
            WHERE api_name = %s
            AND request_time >= %s
            AND request_time <= %s
        """
        
        try:
            with self.connection_manager.get_cursor() as cursor:
                cursor.execute(sql, (api_name, start_time, end_time))
                row = cursor.fetchone()
                return row["count"] if row else 0
        except Exception as e:
            logger.error(f"Error getting API request count: {e}")
            return 0

    def record_user_request(self, user_identifier: str, endpoint: str) -> bool:
        """Record a user request for rate limiting."""
        sql = """
            INSERT INTO user_requests (user_identifier, endpoint, request_time)
            VALUES (%s, %s, NOW())
        """
        
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute(sql, (user_identifier, endpoint))
                return True
        except Exception as e:
            logger.error(f"Error recording user request: {e}")
            return False

    def get_user_request_count(
        self, user_identifier: str, start_time: datetime, end_time: datetime
    ) -> int:
        """Get the number of user requests in a time period."""
        sql = """
            SELECT COUNT(*) as count
            FROM user_requests
            WHERE user_identifier = %s
            AND request_time >= %s
            AND request_time <= %s
        """
        
        try:
            with self.connection_manager.get_cursor() as cursor:
                cursor.execute(sql, (user_identifier, start_time, end_time))
                row = cursor.fetchone()
                return row["count"] if row else 0
        except Exception as e:
            logger.error(f"Error getting user request count: {e}")
            return 0

    def get_admin_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all admin panel data from the database.

        Returns:
            Dictionary containing users, watchlist, alerts, cache, and config data
        """
        try:
            with self.connection_manager.get_cursor() as cursor:
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