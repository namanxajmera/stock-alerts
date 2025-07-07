"""
Webhook handler for Telegram bot integration.

This module handles incoming webhook requests from Telegram bot API,
validates them, and processes bot commands for managing stock watchlists.
"""

import hmac
import json
import logging
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests

from db_manager import DatabaseManager

logger = logging.getLogger("StockAlerts.WebhookHandler")


class WebhookHandler:
    """Handler for Telegram webhook requests and bot commands."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        bot_token: str,
        secret_token: Optional[str] = None,
    ) -> None:
        logger.info("WebhookHandler __init__ starting...")
        self.db = db_manager
        self.token = bot_token
        self.secret_token = secret_token
        logger.info(f"Bot token present: {bool(bot_token)}")
        logger.info(f"Secret token present: {bool(secret_token)}")
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN is not configured")
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured")
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        logger.info("WebhookHandler initialized successfully")

    @staticmethod
    def generate_webhook_secret() -> str:
        """
        Generate a cryptographically secure secret token for webhook validation.

        Returns a URL-safe base64 encoded token that can be used as the
        X-Telegram-Bot-Api-Secret-Token header value.

        Returns:
            str: A secure random token (32 bytes encoded as base64)
        """
        # Generate 32 random bytes and encode as URL-safe base64
        token = secrets.token_urlsafe(32)
        logger.info("Generated new webhook secret token")
        return token

    def validate_webhook(
        self, request_data: bytes, secret_token_header: Optional[str]
    ) -> bool:
        """
        Validate that the webhook request is from Telegram using HMAC-SHA256.

        This implements Telegram's recommended security validation:
        1. Verify the X-Telegram-Bot-Api-Secret-Token header if configured
        2. Validate the request data is valid JSON with required fields

        Args:
            request_data: Raw request body as bytes
            secret_token_header: X-Telegram-Bot-Api-Secret-Token header value

        Returns:
            bool: True if the webhook is valid, False otherwise
        """
        # Validate secret token if configured
        if self.secret_token:
            if not secret_token_header:
                logger.warning("Missing X-Telegram-Bot-Api-Secret-Token header")
                return False

            # Use timing-safe comparison to prevent timing attacks
            if not hmac.compare_digest(self.secret_token, secret_token_header):
                logger.warning("Invalid secret token in webhook request")
                return False

        # Validate request data
        if not request_data:
            logger.warning("Empty webhook request received")
            return False

        try:
            # Parse and validate JSON structure
            data = json.loads(request_data)

            # Validate required Telegram webhook fields
            if "update_id" not in data:
                logger.warning("Invalid webhook data: missing update_id")
                return False

            # Additional validation for webhook structure
            if not isinstance(data.get("update_id"), int):
                logger.warning("Invalid webhook data: update_id must be integer")
                return False

            logger.debug(
                f"Valid webhook request received: update_id={data.get('update_id')}"
            )
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook request: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating webhook: {e}")
            return False

    def process_update(self, update_data: bytes) -> bool:
        """Process an update from Telegram."""
        try:
            update = json.loads(update_data)
            update_id = update.get("update_id")
            logger.info(f"Processing update ID: {update_id}")

            if "message" not in update:
                logger.debug(f"Update {update_id} contains no message, skipping.")
                return True

            message = update["message"]
            user_id = str(message["from"]["id"])
            username = message["from"].get("username") or message["from"].get(
                "first_name"
            )

            logger.info(f"Processing message from user {username} ({user_id})")

            # Add or update user. Log the raw event before any DB writes.
            self.db.log_event(
                "telegram_update", f"Received update ID: {update_id}", user_id=user_id
            )
            self.db.add_user(user_id, username)

            if "text" in message and message["text"].startswith("/"):
                self._handle_command(message)

            return True

        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)
            # Log error to DB
            user_id_for_log = update.get("message", {}).get("from", {}).get("id")
            self.db.log_event(
                "error", f"Error processing update: {e}", user_id=user_id_for_log
            )
            return False

    def _handle_command(self, message: Dict[str, Any]) -> None:
        """Handle bot commands with enhanced validation and security."""
        try:
            # Extract and validate user ID first
            user_id_raw = message.get("from", {}).get("id")
            if not user_id_raw:
                logger.warning("Message missing user ID")
                return

            # Import validation functions
            from utils.validators import (
                ValidationError,
                validate_command_args,
                validate_user_id,
            )

            # Validate user ID
            is_valid_user, validated_user_id = validate_user_id(str(user_id_raw))
            if not is_valid_user:
                logger.warning(f"Invalid user ID: {user_id_raw} - {validated_user_id}")
                return

            # Extract and validate command text
            command_text = message.get("text", "").strip()
            if not command_text:
                logger.warning(f"Empty command from user {validated_user_id}")
                return

            # Parse command and arguments
            parts = command_text.split()
            if not parts:
                return

            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            # Remove leading slash and validate command
            if command.startswith("/"):
                command = command[1:]

            # Validate command and arguments
            is_valid_cmd, validated_args = validate_command_args(command, args)
            if not is_valid_cmd:
                logger.warning(
                    f"Invalid command from user {validated_user_id}: {command} - {validated_args}"
                )
                self._send_message(validated_user_id, f"❌ {validated_args}")
                return

            # At this point, validated_args is guaranteed to be List[str] since validation succeeded
            assert isinstance(
                validated_args, list
            ), "validated_args should be List[str] when validation succeeds"

            # Log command execution for security monitoring
            logger.info(
                f"Executing command /{command} for user {validated_user_id} with {len(validated_args)} args"
            )

            # Execute validated commands
            if command == "start":
                self._send_message(validated_user_id, self._get_welcome_message())
            elif command == "list":
                self._handle_list_command(validated_user_id)
            elif command == "add":
                self._handle_add_command(validated_user_id, validated_args)
            elif command == "remove":
                self._handle_remove_command(validated_user_id, validated_args)
            elif command == "own":
                self._handle_own_command(validated_user_id, validated_args)
            elif command == "unown":
                self._handle_unown_command(validated_user_id, validated_args)
            else:
                # This shouldn't happen due to validation, but handle it gracefully
                logger.warning(f"Unhandled validated command: {command}")
                self._send_message(
                    validated_user_id, "Unknown command. Type /start for help."
                )

        except ValidationError as e:
            # Handle validation errors gracefully
            user_id = str(message.get("from", {}).get("id", "unknown"))
            logger.warning(f"Command validation error from user {user_id}: {e.message}")
            self._send_message(user_id, f"❌ {e.message}")
        except Exception as e:
            # Handle unexpected errors
            user_id = str(message.get("from", {}).get("id", "unknown"))
            command = message.get("text", "unknown")[:50]  # Limit log length
            logger.error(
                f"Error handling command '{command}' from user {user_id}: {e}",
                exc_info=True,
            )
            self.db.log_event(
                "error", f"Error handling command '{command}': {e}", user_id=user_id
            )
            self._send_message(
                user_id, "⚠️ An internal error occurred. Please try again later."
            )

    def _get_welcome_message(self) -> str:
        """Get the welcome message text."""
        return (
            "Welcome to Stock Alerts Bot! 📈\n\n"
            "I will alert you when your stocks reach historically high or low prices compared to their 200-day moving average.\n\n"
            "<b>Available commands:</b>\n"
            "/add TICKER [TICKER...] - Add stocks to track\n"
            "/own TICKER [TICKER...] - Mark stocks as owned positions\n"
            "/unown TICKER [TICKER...] - Mark stocks as watchlist only\n"
            "/remove TICKER [TICKER...] - Remove stock(s)\n"
            "/list - Show your stocks with commands\n\n"
            "💡 <b>Tip:</b> Mark stocks you own with /own to get position-specific alerts!"
        )

    def _send_message(
        self, chat_id: Union[str, int], text: str, parse_mode: str = "HTML"
    ) -> bool:
        """Send a message to a Telegram chat."""
        payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage", json=payload, timeout=5
            )
            response.raise_for_status()
            logger.info(f"Message sent to chat_id {chat_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            self.db.log_event(
                "error", f"Error sending message: {e}", user_id=str(chat_id)
            )
            return False

    def send_alert(
        self,
        user_id: str,
        symbol: str,
        price: float,
        percentile: float,
        percentile_16: float,
        percentile_84: float,
    ) -> bool:
        """Send a stock alert to a user."""
        try:
            # Check if today is a valid alert day (Mon-Thu, Sun)
            today = datetime.now().weekday()  # 0=Monday, 6=Sunday
            valid_days = [0, 1, 2, 3, 6]  # Monday-Thursday, Sunday
            
            if today not in valid_days:
                day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][today]
                logger.info(f"Skipping alert for {symbol} - today is {day_name}. Alerts only sent Mon-Thu and Sunday.")
                
                # Still log to history but mark as skipped
                self.db.add_alert_history(
                    user_id=user_id,
                    symbol=symbol,
                    price=price,
                    percentile=percentile,
                    status="skipped",
                    error_message=f"Alert skipped - {day_name} is not a valid alert day",
                )
                return False
            message = (
                f"🚨 <b>Stock Alert for {symbol.upper()}</b>\n\n"
                f"Current Price: ${price:.2f}\n"
                f"Current Deviation from 200MA: {percentile:.1f}%\n\n"
                f"📊 <b>Historical Context:</b>\n"
                f" • 16th percentile: {percentile_16:.1f}%\n"
                f" • 84th percentile: {percentile_84:.1f}%\n\n"
            )

            if percentile <= percentile_16:
                message += f"This is <b>SIGNIFICANTLY LOW</b>. Only 16% of the time has {symbol.upper()} been this far below its 200-day moving average."
            elif percentile >= percentile_84:
                message += f"This is <b>SIGNIFICANTLY HIGH</b>. Only 16% of the time has {symbol.upper()} been this far above its 200-day moving average."

            success = self._send_message(user_id, message)

            self.db.add_alert_history(
                user_id=user_id,
                symbol=symbol,
                price=price,
                percentile=percentile,
                status="sent" if success else "failed",
                error_message=None if success else "Failed to send Telegram message",
            )

            if success:
                self.db.update_user_notification_time(user_id)

            return success
        except Exception as e:
            logger.error(f"Error composing or sending alert: {e}", exc_info=True)
            self.db.add_alert_history(
                user_id=user_id,
                symbol=symbol,
                price=price,
                percentile=percentile,
                status="failed",
                error_message=str(e),
            )
            return False

    def send_batched_alert(self, user_id: str, alerts: List[Dict[str, Any]]) -> bool:
        """Send a combined alert message for multiple stocks to a user."""
        try:
            if not alerts:
                return True
                
            # Check if today is a valid alert day (Mon-Thu, Sun)
            today = datetime.now().weekday()  # 0=Monday, 6=Sunday
            valid_days = [0, 1, 2, 3, 6]  # Monday-Thursday, Sunday
            
            if today not in valid_days:
                day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][today]
                logger.info(f"Skipping batched alerts - today is {day_name}. Alerts only sent Mon-Thu and Sunday.")
                
                # Log all alerts as skipped
                for alert in alerts:
                    self.db.add_alert_history(
                        user_id=user_id,
                        symbol=alert["symbol"],
                        price=alert["price"],
                        percentile=alert["percentile"],
                        status="skipped",
                        error_message=f"Alert skipped - {day_name} is not a valid alert day",
                    )
                return False

            # Separate alerts by ownership
            position_alerts = [alert for alert in alerts if alert.get("is_owned", False)]
            watchlist_alerts = [alert for alert in alerts if not alert.get("is_owned", False)]

            # Build header
            total_count = len(alerts)
            message = f"📊 <b>Daily Stock Alerts ({total_count} item{'s' if total_count > 1 else ''} need attention)</b>\n\n"

            # Add position alerts first (higher priority)
            if position_alerts:
                message += f"🔴 <b>YOUR POSITIONS ({len(position_alerts)}):</b>\n"
                for alert in position_alerts:
                    symbol = alert["symbol"]
                    percentile = alert["percentile"]
                    percentile_16 = alert["percentile_16"]
                    percentile_84 = alert["percentile_84"]
                    
                    if percentile <= percentile_16:
                        status = "Unusually low"
                    elif percentile >= percentile_84:
                        status = "Unusually high"
                    else:
                        status = "Alert"
                    
                    message += f"• {symbol.upper()} - {status} ({percentile:+.1f}%)\n"
                message += "\n"

            # Add watchlist alerts
            if watchlist_alerts:
                message += f"🟡 <b>WATCHLIST ({len(watchlist_alerts)}):</b>\n"
                for alert in watchlist_alerts:
                    symbol = alert["symbol"]
                    percentile = alert["percentile"]
                    percentile_16 = alert["percentile_16"]
                    percentile_84 = alert["percentile_84"]
                    
                    if percentile <= percentile_16:
                        status = "Unusually low"
                    elif percentile >= percentile_84:
                        status = "Unusually high"
                    else:
                        status = "Alert"
                    
                    message += f"• {symbol.upper()} - {status} ({percentile:+.1f}%)\n"
                message += "\n"

            # Add footer
            message += "💡 <i>These stocks are outside their normal trading ranges.</i>"

            success = self._send_message(user_id, message)

            # Log each alert to history
            for alert in alerts:
                self.db.add_alert_history(
                    user_id=user_id,
                    symbol=alert["symbol"],
                    price=alert["price"],
                    percentile=alert["percentile"],
                    status="sent" if success else "failed",
                    error_message=(
                        None if success else "Failed to send batched Telegram message"
                    ),
                )

            if success:
                self.db.update_user_notification_time(user_id)

            return success

        except Exception as e:
            logger.error(
                f"Error composing or sending batched alert: {e}", exc_info=True
            )
            # Log all alerts as failed
            for alert in alerts:
                self.db.add_alert_history(
                    user_id=user_id,
                    symbol=alert["symbol"],
                    price=alert["price"],
                    percentile=alert["percentile"],
                    status="failed",
                    error_message=str(e),
                )
            return False

    def _handle_list_command(self, user_id: str) -> None:
        """Handle the /list command."""
        watchlist = self.db.get_watchlist(user_id)
        if not watchlist:
            self._send_message(
                user_id, "Your watchlist is empty. Add stocks using /add <TICKER>"
            )
            return

        # Separate owned positions from watchlist
        positions = [item for item in watchlist if item.get('is_owned', False)]
        watched = [item for item in watchlist if not item.get('is_owned', False)]

        message_lines = ["📋 <b>Your Stocks:</b>\n"]

        if positions:
            message_lines.append("💼 <b>POSITIONS</b> (stocks you own):")
            for item in positions:
                status = self._get_stock_status(item)
                message_lines.append(f" • {item['symbol'].upper()} - {status}")
            message_lines.append("")

        if watched:
            message_lines.append("👁️ <b>WATCHLIST</b> (stocks you're watching):")
            for item in watched:
                status = self._get_stock_status(item)
                message_lines.append(f" • {item['symbol'].upper()} - {status}")
            message_lines.append("")

        message_lines.append("💡 <b>Commands:</b>")
        message_lines.append("/own TICKER - Mark as owned position")
        message_lines.append("/unown TICKER - Mark as watchlist only")
        message_lines.append("/add TICKER - Add new stock")
        message_lines.append("/remove TICKER - Remove stock")

        self._send_message(user_id, "\n".join(message_lines))

    def _handle_add_command(self, user_id: str, validated_tickers: List[str]) -> None:
        """
        Handle the /add command with pre-validated ticker symbols.

        Args:
            user_id: Validated Telegram user ID
            validated_tickers: List of validated ticker symbols
        """
        # At this point, tickers are already validated by validate_command_args
        added = []
        errors = []

        for ticker in validated_tickers:
            try:
                success, err_msg = self.db.add_to_watchlist(user_id, ticker)
                if success:
                    added.append(ticker)
                    logger.info(
                        f"Added ticker {ticker} to watchlist for user {user_id}"
                    )
                else:
                    errors.append(f"{ticker}: {err_msg}")
                    logger.warning(
                        f"Failed to add ticker {ticker} for user {user_id}: {err_msg}"
                    )
            except Exception as e:
                logger.error(
                    f"Database error adding ticker {ticker} for user {user_id}: {e}"
                )
                errors.append(f"{ticker}: Database error")

        # Build response message
        response_parts = []
        if added:
            response_parts.append(f"✅ Added {', '.join(added)} to your watchlist.")
        if errors:
            response_parts.append("❌ Could not add:")
            response_parts.extend(f"  • {error}" for error in errors)

        response = "\n".join(response_parts)
        self._send_message(user_id, response)

    def _handle_remove_command(
        self, user_id: str, validated_tickers: List[str]
    ) -> None:
        """
        Handle the /remove command with pre-validated ticker symbols.

        Args:
            user_id: Validated Telegram user ID
            validated_tickers: List of validated ticker symbols
        """
        removed = []
        not_found = []
        errors = []

        for ticker in validated_tickers:
            try:
                success = self.db.remove_from_watchlist(user_id, ticker)
                if success:
                    removed.append(ticker)
                    logger.info(
                        f"Removed ticker {ticker} from watchlist for user {user_id}"
                    )
                else:
                    not_found.append(ticker)
                    logger.info(
                        f"Ticker {ticker} not found in watchlist for user {user_id}"
                    )
            except Exception as e:
                logger.error(
                    f"Database error removing ticker {ticker} for user {user_id}: {e}"
                )
                errors.append(f"{ticker}: Database error")

        # Build response message
        response_parts = []
        if removed:
            response_parts.append(
                f"✅ Removed {', '.join(removed)} from your watchlist."
            )
        if not_found:
            response_parts.append(f"ℹ️ Not found in watchlist: {', '.join(not_found)}")
        if errors:
            response_parts.append("❌ Errors occurred:")
            response_parts.extend(f"  • {error}" for error in errors)

        if not response_parts:
            response_parts.append("ℹ️ No changes made to your watchlist.")

        response = "\n".join(response_parts)
        self._send_message(user_id, response)

    def _handle_own_command(self, user_id: str, validated_tickers: List[str]) -> None:
        """Handle the /own command to mark stocks as owned positions."""
        marked_owned = []
        not_found = []
        errors = []

        for ticker in validated_tickers:
            try:
                success = self.db.set_position_owned(user_id, ticker, True)
                if success:
                    marked_owned.append(ticker)
                    logger.info(f"Marked {ticker} as owned for user {user_id}")
                else:
                    not_found.append(ticker)
                    logger.info(f"Ticker {ticker} not found in watchlist for user {user_id}")
            except Exception as e:
                logger.error(f"Database error marking {ticker} as owned for user {user_id}: {e}")
                errors.append(f"{ticker}: Database error")

        # Build response message
        response_parts = []
        if marked_owned:
            response_parts.append(f"💼 Marked {', '.join(marked_owned)} as owned positions.")
        if not_found:
            response_parts.append(f"ℹ️ Not found in watchlist: {', '.join(not_found)}")
            response_parts.append("💡 Use /add to add stocks to your watchlist first.")
        if errors:
            response_parts.append("❌ Errors occurred:")
            response_parts.extend(f"  • {error}" for error in errors)

        if not response_parts:
            response_parts.append("ℹ️ No changes made.")

        response = "\n".join(response_parts)
        self._send_message(user_id, response)

    def _handle_unown_command(self, user_id: str, validated_tickers: List[str]) -> None:
        """Handle the /unown command to mark stocks as watchlist only."""
        marked_watchlist = []
        not_found = []
        errors = []

        for ticker in validated_tickers:
            try:
                success = self.db.set_position_owned(user_id, ticker, False)
                if success:
                    marked_watchlist.append(ticker)
                    logger.info(f"Marked {ticker} as watchlist only for user {user_id}")
                else:
                    not_found.append(ticker)
                    logger.info(f"Ticker {ticker} not found in watchlist for user {user_id}")
            except Exception as e:
                logger.error(f"Database error marking {ticker} as watchlist for user {user_id}: {e}")
                errors.append(f"{ticker}: Database error")

        # Build response message
        response_parts = []
        if marked_watchlist:
            response_parts.append(f"👁️ Marked {', '.join(marked_watchlist)} as watchlist only.")
        if not_found:
            response_parts.append(f"ℹ️ Not found in watchlist: {', '.join(not_found)}")
        if errors:
            response_parts.append("❌ Errors occurred:")
            response_parts.extend(f"  • {error}" for error in errors)

        if not response_parts:
            response_parts.append("ℹ️ No changes made.")

        response = "\n".join(response_parts)
        self._send_message(user_id, response)


    def _get_stock_status(self, item: Union[Dict[str, Any], Any]) -> str:
        """Get current status text for a stock."""
        if not item.get('last_price') or not item.get('ma_200'):
            return "No data"
        
        price = float(item['last_price'])
        ma_200 = float(item['ma_200'])
        pct_diff = ((price - ma_200) / ma_200) * 100
        
        if pct_diff >= 8:  # Rough threshold for "high"
            return "Unusually high"
        elif pct_diff <= -8:  # Rough threshold for "low"
            return "Unusually low"
        else:
            return "Normal range"
