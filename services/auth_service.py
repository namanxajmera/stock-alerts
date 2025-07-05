"""
Authentication service for handling admin authentication and API key validation.

This service provides secure authentication mechanisms for admin access
and API key validation for protected endpoints.
"""

import functools
import hmac
import logging
from typing import Any, Callable, Tuple

from flask import Response, jsonify, request

from utils.config import config

logger = logging.getLogger("StockAlerts.AuthService")


class AuthService:
    """Service class for authentication operations."""

    def __init__(self) -> None:
        """Initialize the AuthService."""
        self.logger = logging.getLogger("StockAlerts.AuthService")

    def require_admin_auth(self, f: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator for routes requiring admin authentication.

        Args:
            f: The function to wrap with authentication

        Returns:
            Wrapped function with authentication check
        """

        @functools.wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            auth = request.authorization

            if not auth:
                self.logger.warning("Admin access attempt without credentials")
                return Response(
                    "Access denied. Authentication required.",
                    401,
                    {"WWW-Authenticate": 'Basic realm="Admin"'},
                )

            admin_username = config.ADMIN_USERNAME
            admin_password = config.ADMIN_PASSWORD

            if not admin_username or not admin_password:
                self.logger.error("Admin credentials not configured")
                return (
                    jsonify({"error": "Admin authentication not properly configured"}),
                    503,
                )

            if auth.username != admin_username or auth.password != admin_password:
                self.logger.warning(
                    f"Failed admin login attempt for username: {auth.username}"
                )
                return Response(
                    "Access denied. Invalid credentials.",
                    401,
                    {"WWW-Authenticate": 'Basic realm="Admin"'},
                )

            self.logger.info(
                f"Successful admin authentication for user: {auth.username}"
            )
            return f(*args, **kwargs)

        return decorated_function

    def validate_admin_api_key(self, provided_key: str) -> Tuple[bool, str]:
        """
        Validate admin API key for programmatic access.

        Args:
            provided_key: The API key provided by the client

        Returns:
            Tuple of (is_valid, error_message)
        """
        expected_api_key = config.ADMIN_API_KEY

        if not expected_api_key:
            self.logger.error("ADMIN_API_KEY not configured")
            return False, "Service configuration error"

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(provided_key, expected_api_key):
            self.logger.warning("Invalid API key provided for admin access")
            return False, "Unauthorized"

        self.logger.info("Valid admin API key provided")
        return True, "Authorized"

    def validate_admin_access_key(self, provided_key: str) -> Tuple[bool, str]:
        """
        Validate admin access key for admin panel operations.

        Args:
            provided_key: The admin access key provided by the client

        Returns:
            Tuple of (is_valid, error_message)
        """
        expected_key = config.ADMIN_API_KEY

        if not expected_key:
            self.logger.error("ADMIN_API_KEY not configured")
            return False, "Service configuration error"

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(provided_key, expected_key):
            self.logger.warning("Invalid admin access key provided")
            return False, "Unauthorized"

        self.logger.info("Valid admin access key provided")
        return True, "Authorized"
