"""Webhook routes for Telegram bot integration."""
import logging
from typing import Tuple
from flask import Blueprint, request, abort
from flask import current_app

logger = logging.getLogger("StockAlerts.Webhook")

webhook_bp = Blueprint('webhook', __name__)


@webhook_bp.route("/webhook", methods=["POST"])
def telegram_webhook() -> Tuple[str, int]:
    """Handle incoming webhook requests from Telegram."""
    # Get webhook handler from app context
    webhook_handler = getattr(current_app, 'webhook_handler', None)
    
    if webhook_handler is None:
        logger.error("Webhook handler not initialized")
        abort(503)  # Service Unavailable
        
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not webhook_handler.validate_webhook(request.get_data(), secret_token):
        logger.warning("Invalid webhook request validation failed.")
        abort(403)

    webhook_handler.process_update(request.get_data())
    return "", 200