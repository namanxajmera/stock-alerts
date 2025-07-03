from flask import request, abort
import hmac
import hashlib
from termcolor import colored
from db_manager import DatabaseManager
import os
import json
import requests
import logging

logger = logging.getLogger('StockAlerts.WebhookHandler')

class WebhookHandler:
    def __init__(self, db_manager, bot_token, secret_token=None):
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

    def validate_webhook(self, request_data, secret_token_header):
        """Validate that the webhook request is from Telegram."""
        if self.secret_token:
            if not secret_token_header or not hmac.compare_digest(self.secret_token, secret_token_header):
                logger.warning("Invalid secret token on incoming webhook.")
                return False
        
        if not request_data:
            logger.warning("Empty webhook request received")
            return False
            
        try:
            data = json.loads(request_data)
            if 'update_id' not in data:
                logger.warning("Invalid webhook data: missing update_id")
                return False
            logger.debug(f"Valid webhook request received: {data.get('update_id')}")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook request: {e}")
            return False

    def process_update(self, update_data):
        """Process an update from Telegram."""
        try:
            update = json.loads(update_data)
            update_id = update.get('update_id')
            logger.info(f"Processing update ID: {update_id}")
            
            if 'message' not in update:
                logger.debug(f"Update {update_id} contains no message, skipping.")
                return True
                
            message = update['message']
            user_id = str(message['from']['id'])
            username = message['from'].get('username') or message['from'].get('first_name')
            
            logger.info(f"Processing message from user {username} ({user_id})")
            
            # Add or update user. Log the raw event before any DB writes.
            self.db.log_event(
                'telegram_update', f"Received update ID: {update_id}", user_id=user_id
            )
            self.db.add_user(user_id, username)
            
            if 'text' in message and message['text'].startswith('/'):
                self._handle_command(message)
                
            return True
            
        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)
            # Log error to DB
            user_id_for_log = update.get('message', {}).get('from', {}).get('id')
            self.db.log_event('error', f"Error processing update: {e}", user_id=user_id_for_log)
            return False

    def _handle_command(self, message):
        """Handle bot commands."""
        command, *args = message['text'].split()
        command = command.lower()
        user_id = str(message['from']['id'])
        
        try:
            if command == '/start':
                self._send_message(user_id, self._get_welcome_message())
            elif command == '/list':
                self._handle_list_command(user_id)
            elif command == '/add':
                self._handle_add_command(user_id, args)
            elif command == '/remove':
                self._handle_remove_command(user_id, args)
            else:
                self._send_message(user_id, "Unknown command. Type /start for help.")
        except Exception as e:
            logger.error(f"Error handling command '{command}': {e}", exc_info=True)
            self.db.log_event('error', f"Error handling command '{command}': {e}", user_id=user_id)
            self._send_message(user_id, "An internal error occurred. Please try again later.")

    def _get_welcome_message(self):
        """Get the welcome message text."""
        return (
            "Welcome to Stock Alerts Bot! 📈\n\n"
            "I will alert you when your stocks reach historically high or low prices compared to their 200-day moving average.\n\n"
            "<b>Available commands:</b>\n"
            "/add TICKER [TICKER...] - Add one or more stocks to track\n"
            "/remove TICKER [TICKER...] - Remove stock(s)\n"
            "/list - Show your watchlist\n"
        )

    def _send_message(self, chat_id, text, parse_mode='HTML'):
        """Send a message to a Telegram chat."""
        payload = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
        try:
            response = requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"Message sent to chat_id {chat_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            self.db.log_event('error', f"Error sending message: {e}", user_id=chat_id)
            return False

    def send_alert(self, user_id, symbol, price, percentile, percentile_16, percentile_84):
        """Send a stock alert to a user."""
        try:
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
                user_id=user_id, symbol=symbol, price=price, percentile=percentile,
                status='sent' if success else 'failed',
                error_message=None if success else "Failed to send Telegram message"
            )
            
            if success:
                self.db.update_user_notification_time(user_id)
            
            return success
        except Exception as e:
            logger.error(f"Error composing or sending alert: {e}", exc_info=True)
            self.db.add_alert_history(
                user_id=user_id, symbol=symbol, price=price, percentile=percentile,
                status='failed', error_message=str(e)
            )
            return False

    def _handle_list_command(self, user_id):
        """Handle the /list command."""
        watchlist = self.db.get_watchlist(user_id)
        if not watchlist:
            return self._send_message(user_id, "Your watchlist is empty. Add stocks using /add <TICKER>")
        
        message_lines = ["📋 <b>Your Watchlist:</b>"]
        for item in watchlist:
            message_lines.append(f" • {item['symbol'].upper()}")
        
        self._send_message(user_id, "\n".join(message_lines))

    def _handle_add_command(self, user_id, tickers):
        """Handle the /add command."""
        if not tickers:
            return self._send_message(user_id, "Please provide at least one ticker. Usage: /add AAPL TSLA")
        
        added = []
        errors = []
        for ticker in tickers:
            success, err_msg = self.db.add_to_watchlist(user_id, ticker.upper())
            if success:
                added.append(ticker.upper())
            else:
                errors.append(f"{ticker.upper()}: {err_msg}")

        response = ""
        if added:
            response += f"✅ Added {', '.join(added)} to your watchlist.\n"
        if errors:
            response += f"❌ Could not add:\n" + "\n".join(errors)
        
        self._send_message(user_id, response.strip())

    def _handle_remove_command(self, user_id, tickers):
        """Handle the /remove command."""
        if not tickers:
            return self._send_message(user_id, "Please provide at least one ticker. Usage: /remove AAPL TSLA")

        removed_count = 0
        for ticker in tickers:
            if self.db.remove_from_watchlist(user_id, ticker.upper()):
                removed_count += 1
        
        if removed_count > 0:
            self._send_message(user_id, f"✅ Removed {removed_count} stock(s) from your watchlist.")
        else:
            self._send_message(user_id, "None of the specified stocks were found in your watchlist.") 