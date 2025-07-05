"""
Comprehensive validation utilities for input sanitization and validation.

This module provides security-focused validation functions to prevent
injection attacks, ensure data integrity, and validate business logic constraints.
"""

import html
import logging
import re
from typing import Any, List, Optional, Tuple, Union

logger = logging.getLogger("StockAlerts.Validators")

# Constants for validation
MAX_TICKER_LENGTH = 10
MAX_TICKERS_PER_REQUEST = 50
MAX_STRING_LENGTH = 1000
VALID_PERIODS = ["1y", "3y", "5y", "max"]
VALID_API_KEYS_LENGTH = (10, 200)  # Min and max API key lengths

# SQL injection patterns to detect
SQL_INJECTION_PATTERNS = [
    r"['\"]\s*[;]\s*",  # Quote followed by semicolon
    r"union\s+select",  # UNION SELECT
    r"drop\s+table",  # DROP TABLE
    r"insert\s+into",  # INSERT INTO
    r"delete\s+from",  # DELETE FROM
    r"update\s+\w+\s+set",  # UPDATE SET
    r"exec\s*\(",  # EXEC(
    r"xp_\w+",  # SQL Server extended procedures
    r"sp_\w+",  # SQL Server stored procedures
]

# XSS patterns to detect
XSS_PATTERNS = [
    r"<script[^>]*>",  # Script tags
    r"javascript:",  # JavaScript protocol
    r"vbscript:",  # VBScript protocol
    r"onload\s*=",  # Event handlers
    r"onclick\s*=",
    r"onerror\s*=",
    r"onmouseover\s*=",
]


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


def sanitize_string(value: str, max_length: int = MAX_STRING_LENGTH) -> str:
    """
    Sanitize a string to prevent XSS and injection attacks.

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Raises:
        ValidationError: If input is invalid
    """
    if not isinstance(value, str):
        raise ValidationError("Input must be a string")

    # Trim whitespace
    value = value.strip()

    # Check length
    if len(value) > max_length:
        raise ValidationError(f"Input too long (max {max_length} characters)")

    # HTML escape to prevent XSS
    value = html.escape(value)

    # Log suspicious patterns
    for pattern in XSS_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(f"Suspicious XSS pattern detected in input: {pattern}")
            raise ValidationError("Input contains potentially malicious content")

    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(f"Suspicious SQL injection pattern detected: {pattern}")
            raise ValidationError("Input contains potentially malicious content")

    return value


def validate_ticker_symbol(ticker: str) -> Tuple[bool, str]:
    """
    Validate that the ticker symbol is in a valid format.

    Enhanced with additional security checks and business logic validation.

    Args:
        ticker: Stock ticker symbol to validate

    Returns:
        Tuple of (is_valid, validated_ticker_or_error_message)
    """
    try:
        if not ticker:
            return False, "Ticker symbol cannot be empty"

        # Sanitize input
        ticker = sanitize_string(ticker, MAX_TICKER_LENGTH)

        # Remove whitespace and convert to uppercase
        ticker = ticker.strip().upper()

        # Length validation
        if len(ticker) > MAX_TICKER_LENGTH:
            return False, f"Ticker symbol too long (max {MAX_TICKER_LENGTH} characters)"

        if len(ticker) < 1:
            return False, "Ticker symbol cannot be empty"

        # Format validation: letters and numbers, may include dots and dashes for some international symbols
        if not re.match(r"^[A-Z0-9.-]{1,10}$", ticker):
            return (
                False,
                "Ticker symbol must contain only letters, numbers, dots, and dashes",
            )

        # Business logic validation
        if ticker.isdigit():
            return False, "Ticker symbol cannot be all numbers"

        # Check for common invalid patterns
        invalid_patterns = [
            r"^\.+$",  # Only dots
            r"^-+$",  # Only dashes
            r"^[.-]+$",  # Only dots and dashes
            r"\.{2,}",  # Multiple consecutive dots
            r"-{2,}",  # Multiple consecutive dashes
        ]

        for pattern in invalid_patterns:
            if re.match(pattern, ticker):
                return False, "Invalid ticker symbol format"

        # Reserved/common invalid symbols
        reserved_symbols = {"NULL", "NONE", "UNDEFINED", "ADMIN", "ROOT", "TEST"}
        if ticker in reserved_symbols:
            return False, "Invalid ticker symbol"

        logger.debug(f"Validated ticker symbol: {ticker}")
        return True, ticker

    except ValidationError as e:
        logger.warning(f"Ticker validation failed: {e.message}")
        return False, e.message
    except Exception as e:
        logger.error(f"Unexpected error validating ticker: {e}")
        return False, "Invalid ticker symbol format"


def validate_period(period: str) -> Tuple[bool, str]:
    """
    Validate time period parameter for stock data requests.

    Args:
        period: Time period string (1y, 3y, 5y, max)

    Returns:
        Tuple of (is_valid, validated_period_or_error_message)
    """
    try:
        if not period:
            return False, "Period cannot be empty"

        # Sanitize input
        period = sanitize_string(period, 10).lower().strip()

        # Validate against allowed periods
        if period not in VALID_PERIODS:
            return False, f"Invalid period. Must be one of: {', '.join(VALID_PERIODS)}"

        logger.debug(f"Validated period: {period}")
        return True, period

    except ValidationError as e:
        return False, e.message
    except Exception as e:
        logger.error(f"Unexpected error validating period: {e}")
        return False, "Invalid period format"


def validate_ticker_list(
    tickers: Any, max_count: int = MAX_TICKERS_PER_REQUEST
) -> Tuple[bool, Union[List[str], str]]:
    """
    Validate a list of ticker symbols.

    Args:
        tickers: List of ticker symbol strings
        max_count: Maximum number of tickers allowed

    Returns:
        Tuple of (is_valid, validated_tickers_or_error_message)
    """
    try:
        if not tickers:
            return False, "Ticker list cannot be empty"

        if not isinstance(tickers, list):
            return False, "Tickers must be provided as a list"

        if len(tickers) > max_count:
            return False, f"Too many tickers (max {max_count} allowed)"

        validated_tickers = []
        for ticker in tickers:
            if not isinstance(ticker, str):
                return False, "All tickers must be strings"

            is_valid, result = validate_ticker_symbol(ticker)
            if not is_valid:
                return False, f"Invalid ticker '{ticker}': {result}"

            validated_tickers.append(result)

        # Check for duplicates
        if len(set(validated_tickers)) != len(validated_tickers):
            return False, "Duplicate ticker symbols are not allowed"

        logger.debug(f"Validated ticker list: {validated_tickers}")
        return True, validated_tickers

    except Exception as e:
        logger.error(f"Unexpected error validating ticker list: {e}")
        return False, "Invalid ticker list format"


def validate_user_id(user_id: str) -> Tuple[bool, str]:
    """
    Validate Telegram user ID.

    Args:
        user_id: Telegram user ID string

    Returns:
        Tuple of (is_valid, validated_user_id_or_error_message)
    """
    try:
        if not user_id:
            return False, "User ID cannot be empty"

        # Sanitize input
        user_id = sanitize_string(user_id, 50).strip()

        # Telegram user IDs are numeric strings
        if not user_id.isdigit():
            return False, "User ID must be numeric"

        # Check reasonable bounds (Telegram IDs are typically 5-10 digits)
        if len(user_id) < 5 or len(user_id) > 15:
            return False, "Invalid user ID length"

        # Convert to int and back to ensure it's a valid number
        user_id_int = int(user_id)
        if user_id_int <= 0:
            return False, "User ID must be positive"

        return True, str(user_id_int)

    except (ValueError, ValidationError):
        return False, "Invalid user ID format"
    except Exception as e:
        logger.error(f"Unexpected error validating user ID: {e}")
        return False, "Invalid user ID format"


def validate_api_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate API key format and length.

    Args:
        api_key: API key string

    Returns:
        Tuple of (is_valid, validated_key_or_error_message)
    """
    try:
        if not api_key:
            return False, "API key cannot be empty"

        # Don't sanitize API keys as they may contain special characters
        api_key = api_key.strip()

        # Length validation
        min_len, max_len = VALID_API_KEYS_LENGTH
        if len(api_key) < min_len or len(api_key) > max_len:
            return False, f"API key must be between {min_len} and {max_len} characters"

        # Basic format validation (alphanumeric + common special chars)
        if not re.match(r"^[A-Za-z0-9_\-\.=+/]+$", api_key):
            return False, "API key contains invalid characters"

        return True, api_key

    except Exception as e:
        logger.error(f"Unexpected error validating API key: {e}")
        return False, "Invalid API key format"


def validate_command_args(
    command: str, args: List[str]
) -> Tuple[bool, Union[List[str], str]]:
    """
    Validate Telegram bot command arguments.

    Args:
        command: Bot command name (without /)
        args: List of command arguments

    Returns:
        Tuple of (is_valid, validated_args_or_error_message)
    """
    try:
        # Sanitize command
        command = sanitize_string(command, 50).lower().strip()

        if command in ["add", "remove"]:
            if not args:
                return False, f"Command /{command} requires at least one ticker symbol"

            # Validate ticker symbols
            return validate_ticker_list(args)

        elif command == "list":
            if args:
                return False, "Command /list does not accept arguments"
            return True, []

        elif command == "start":
            if args:
                return False, "Command /start does not accept arguments"
            return True, []

        else:
            return False, f"Unknown command: /{command}"

    except ValidationError as e:
        return False, e.message
    except Exception as e:
        logger.error(f"Unexpected error validating command args: {e}")
        return False, "Invalid command format"
