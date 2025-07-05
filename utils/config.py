"""
Centralized configuration management for the Stock Alerts application.

This module loads all environment variables in one place and provides
validated configuration values to all other modules.
"""

import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")

logger = logging.getLogger("StockAlerts.Config")


class Config:
    """Centralized configuration class for the Stock Alerts application."""

    def __init__(self) -> None:
        """Initialize configuration by loading and validating environment variables."""
        self._load_config()
        self._validate_required_config()

    def _load_config(self) -> None:
        """Load all configuration values from environment variables."""
        # Database configuration
        self.DATABASE_URL = os.getenv("DATABASE_URL")

        # Telegram bot configuration
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")

        # API configuration
        self.TIINGO_API_TOKEN = os.getenv("TIINGO_API_TOKEN")

        # Admin authentication
        self.ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
        self.ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
        self.ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
        self.API_SECRET_KEY = os.getenv("API_SECRET_KEY")

        # Application settings with defaults
        self.CACHE_HOURS = int(os.getenv("CACHE_HOURS", "1"))
        self.YF_REQUEST_DELAY = float(os.getenv("YF_REQUEST_DELAY", "3.0"))
        self.PORT = int(os.getenv("PORT", "5001"))

        # Optional settings
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

        logger.info("Configuration loaded successfully")

    def _validate_required_config(self) -> None:
        """Validate that all required configuration values are present."""
        required_configs = {
            "DATABASE_URL": self.DATABASE_URL,
            "TELEGRAM_BOT_TOKEN": self.TELEGRAM_BOT_TOKEN,
            "TIINGO_API_TOKEN": self.TIINGO_API_TOKEN,
        }

        missing_configs = [key for key, value in required_configs.items() if not value]

        if missing_configs:
            error_msg = (
                f"Missing required environment variables: {', '.join(missing_configs)}"
            )
            logger.critical(error_msg)
            raise ValueError(error_msg)

        logger.info("Required configuration validation passed")

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of configuration for logging (excluding sensitive values)."""
        return {
            "DATABASE_URL": bool(self.DATABASE_URL),
            "TELEGRAM_BOT_TOKEN": bool(self.TELEGRAM_BOT_TOKEN),
            "TELEGRAM_WEBHOOK_SECRET": bool(self.TELEGRAM_WEBHOOK_SECRET),
            "TIINGO_API_TOKEN": bool(self.TIINGO_API_TOKEN),
            "ADMIN_USERNAME": bool(self.ADMIN_USERNAME),
            "ADMIN_PASSWORD": bool(self.ADMIN_PASSWORD),
            "ADMIN_API_KEY": bool(self.ADMIN_API_KEY),
            "API_SECRET_KEY": bool(self.API_SECRET_KEY),
            "CACHE_HOURS": self.CACHE_HOURS,
            "YF_REQUEST_DELAY": self.YF_REQUEST_DELAY,
            "PORT": self.PORT,
            "DEBUG": self.DEBUG,
            "LOG_LEVEL": self.LOG_LEVEL,
        }


# Global configuration instance
config = Config()
