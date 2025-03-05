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
    def __init__(self, db_manager):
        self.db = db_manager
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        logger.info("Webhook handler initialized")

    def validate_webhook(self, request_data):
        """Validate that the webhook request is from Telegram."""
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
            logger.error(f"Invalid JSON in webhook request: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error validating webhook: {str(e)}")
            return False

    def process_update(self, update_data):
        """Process an update from Telegram."""
        try:
            update = json.loads(update_data)
            update_id = update.get('update_id')
            logger.info(f"Processing update ID: {update_id}")
            
            # Log the incoming update
            self.db.log_event(
                'telegram_update',
                f"Received update ID: {update_id}",
                user_id=update.get('message', {}).get('from', {}).get('id')
            )
            
            if 'message' not in update:
                logger.debug(f"Update {update_id} contains no message")
                return True
                
            message = update['message']
            user_id = str(message['from']['id'])
            username = message['from'].get('username') or message['from'].get('first_name')
            
            logger.info(f"Processing message from user {username} ({user_id})")
            
            # Add or update user
            self.db.add_user(user_id, username)
            
            # Process command if present
            if 'text' in message and message['text'].startswith('/'):
                return self._handle_command(message)
                
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in update data: {str(e)}")
            self.db.log_event('error', f"Invalid JSON in update: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}")
            self.db.log_event('error', f"Error processing update: {str(e)}")
            return False

    def _handle_command(self, message):
        """Handle bot commands."""
        try:
            command = message['text'].split()[0].lower()
            user_id = str(message['from']['id'])
            
            if command == '/start':
                return self._send_message(user_id, self._get_welcome_message())
            elif command == '/list':
                return self._handle_list_command(user_id)
            elif command == '/settings':
                return self._handle_settings_command(user_id)
            elif command == '/add':
                return self._handle_add_command(user_id, message['text'])
            elif command == '/remove':
                return self._handle_remove_command(user_id, message['text'])
            elif command == '/thresholds':
                return self._handle_thresholds_command(user_id, message['text'])
            else:
                return self._send_message(user_id, "Unknown command. Type /start for help.")
                
        except Exception as e:
            self.db.log_event('error', f"Error handling command: {str(e)}")
            return False

    def _get_welcome_message(self):
        """Get the welcome message text."""
        return (
            "Welcome to Stock Alerts Bot! 📈\n\n"
            "Available commands:\n"
            "/add <ticker> - Add a stock to track\n"
            "/remove <ticker> - Remove a tracked stock\n"
            "/list - Show your watchlist\n"
            "/thresholds <ticker> <low> <high> - Set price alerts\n"
            "/settings - View current settings"
        )

    def _send_message(self, chat_id, text):
        """Send a message to a Telegram chat."""
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    'chat_id': chat_id,
                    'text': text,
                    'parse_mode': 'HTML'
                }
            )
            response.raise_for_status()
            return True
        except Exception as e:
            self.db.log_event('error', f"Error sending message: {str(e)}")
            return False

    def send_alert(self, user_id, symbol, price, percentile, percentile_5=None, percentile_95=None):
        """Send a stock alert to a user."""
        try:
            message = (
                f"🚨 <b>Stock Alert for {symbol}</b>\n\n"
                f"Current Price: ${price:.2f}\n"
                f"Current Deviation from 200MA: {percentile:.1f}%\n"
            )

            if percentile_5 is not None and percentile_95 is not None:
                message += (
                    f"\n📊 Historical Context:\n"
                    f"• Current deviation: {percentile:.1f}%\n"
                    f"• 5th percentile: {percentile_5:.1f}%\n"
                    f"• 95th percentile: {percentile_95:.1f}%\n\n"
                    f"📈 Analysis: The price is currently "
                )
                
                if percentile <= percentile_5:
                    message += (
                        f"EXTREMELY LOW compared to historical patterns.\n"
                        f"Only {5}% of the time has it been lower relative to its 200-day MA."
                    )
                elif percentile >= percentile_95:
                    message += (
                        f"EXTREMELY HIGH compared to historical patterns.\n"
                        f"Only {5}% of the time has it been higher relative to its 200-day MA."
                    )
            
            success = self._send_message(user_id, message)
            
            # Log the alert
            self.db.add_alert_history(
                user_id=user_id,
                symbol=symbol,
                price=price,
                percentile=percentile,
                status='sent' if success else 'failed',
                error_message=None if success else "Failed to send message"
            )
            
            # Update user's last notification time
            if success:
                self.db.update_user_notification_time(user_id)
            
            return success
            
        except Exception as e:
            self.db.log_event('error', f"Error sending alert: {str(e)}")
            self.db.add_alert_history(
                user_id=user_id,
                symbol=symbol,
                price=price,
                percentile=percentile,
                status='failed',
                error_message=str(e)
            )
            return False

    def _handle_list_command(self, user_id):
        """Handle the /list command."""
        try:
            watchlist = self.db.get_watchlist(user_id)
            
            if not watchlist:
                return self._send_message(user_id, "Your watchlist is empty. Add stocks using /add <ticker>")
            
            message = "📋 Your Watchlist:\n\n"
            for item in watchlist:
                message += (
                    f"• {item['symbol']}\n"
                    f"  Thresholds: {item['alert_threshold_low']}% - {item['alert_threshold_high']}%\n"
                    f"  Current Price: ${item['last_price'] or 'N/A'}\n\n"
                )
            
            return self._send_message(user_id, message)
            
        except Exception as e:
            self.db.log_event('error', f"Error handling list command: {str(e)}")
            return False

    def _handle_settings_command(self, user_id):
        """Handle the /settings command."""
        try:
            # Get user settings from database
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT notification_enabled, preferred_check_day, preferred_check_time, max_stocks
                FROM users WHERE id = ?
            """, (user_id,))
            
            settings = cursor.fetchone()
            
            if not settings:
                return self._send_message(user_id, "Error: User settings not found")
            
            message = (
                "⚙️ Your Settings:\n\n"
                f"Notifications: {'Enabled' if settings['notification_enabled'] else 'Disabled'}\n"
                f"Check Day: {settings['preferred_check_day'].title()}\n"
                f"Check Time: {settings['preferred_check_time']}\n"
                f"Max Stocks: {settings['max_stocks']}"
            )
            
            return self._send_message(user_id, message)
            
        except Exception as e:
            self.db.log_event('error', f"Error handling settings command: {str(e)}")
            return False 