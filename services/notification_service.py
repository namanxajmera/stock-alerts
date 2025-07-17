"""
Notification service for handling alert notifications.

This service provides a centralized way to send notifications through
different channels (currently Telegram) and decouples the periodic
checker from specific notification implementations.
"""

import logging
from typing import Any, Dict, List

from database import DatabaseManager

logger = logging.getLogger("StockAlerts.NotificationService")


class NotificationService:
    """Service for sending notifications through various channels."""

    def __init__(self, db_manager: DatabaseManager, webhook_handler: Any) -> None:
        """
        Initialize the notification service.

        Args:
            db_manager: Database manager instance
            webhook_handler: Webhook handler for Telegram notifications
        """
        self.db_manager = db_manager
        self.webhook_handler = webhook_handler
        self.logger = logging.getLogger("StockAlerts.NotificationService")

    def send_alert(
        self,
        user_id: str,
        symbol: str,
        price: float,
        percentile: float,
        percentile_16: float,
        percentile_84: float,
    ) -> bool:
        """
        Send a single stock alert to a user.

        Args:
            user_id: User ID to send alert to
            symbol: Stock symbol
            price: Current stock price
            percentile: Current percentile deviation
            percentile_16: 16th percentile threshold
            percentile_84: 84th percentile threshold

        Returns:
            bool: True if alert was sent successfully
        """
        try:
            return bool(self.webhook_handler.send_alert(
                user_id, symbol, price, percentile, percentile_16, percentile_84
            ))
        except Exception as e:
            self.logger.error(f"Error sending alert for {symbol} to user {user_id}: {e}")
            return False

    def send_batched_alerts(self, user_id: str, alerts: List[Dict[str, Any]]) -> bool:
        """
        Send multiple alerts in a single notification.

        Args:
            user_id: User ID to send alerts to
            alerts: List of alert data dictionaries

        Returns:
            bool: True if alerts were sent successfully
        """
        try:
            return bool(self.webhook_handler.send_batched_alert(user_id, alerts))
        except Exception as e:
            self.logger.error(f"Error sending batched alerts to user {user_id}: {e}")
            return False