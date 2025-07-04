"""
Authentication service for handling authentication and authorization.

This service provides authentication methods and decorators for:
- Admin panel authentication
- API key authentication
- Request validation
"""

import os
import base64
import logging
from functools import wraps
from typing import Any, Callable, Tuple, Dict

from flask import request, jsonify


class AuthService:
    """Service class for authentication operations."""
    
    def __init__(self) -> None:
        """Initialize the AuthService."""
        self.logger = logging.getLogger("StockAlerts.AuthService")
        
    def require_admin_auth(self, f: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator to require admin authentication for sensitive endpoints.
        
        Args:
            f: The function to decorate
            
        Returns:
            Decorated function that requires admin authentication
        """
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            auth_header = request.headers.get('Authorization')
            
            def authenticate() -> Tuple[str, int, Dict[str, str]]:
                """Send a 401 response with WWW-Authenticate header to trigger browser popup."""
                return ('Authentication required', 401, {
                    'WWW-Authenticate': 'Basic realm="Admin Panel"'
                })
            
            if not auth_header:
                return authenticate()
            
            try:
                # Parse Basic Auth header
                if not auth_header.startswith('Basic '):
                    return authenticate()
                
                encoded_credentials = auth_header.split(' ', 1)[1]
                decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
                username, password = decoded_credentials.split(':', 1)
                
                # Get admin credentials from environment
                admin_username = os.getenv('ADMIN_USERNAME')
                admin_password = os.getenv('ADMIN_PASSWORD')
                
                if not admin_username or not admin_password:
                    self.logger.error("Admin credentials not configured in environment")
                    return jsonify({"error": "Admin authentication not configured"}), 500
                
                if username != admin_username or password != admin_password:
                    self.logger.warning(f"Failed admin authentication attempt from {request.remote_addr}")
                    return authenticate()
                
                return f(*args, **kwargs)
                
            except Exception as e:
                self.logger.error(f"Authentication error: {e}")
                return authenticate()
        
        return decorated_function
    
    def require_api_key(self, f: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator to require API key authentication for automated endpoints.
        
        Args:
            f: The function to decorate
            
        Returns:
            Decorated function that requires API key authentication
        """
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                return jsonify({"error": "API key required"}), 401
            
            expected_api_key = os.getenv('API_SECRET_KEY')
            if not expected_api_key:
                self.logger.error("API secret key not configured in environment")
                return jsonify({"error": "API authentication not configured"}), 500
            
            if api_key != expected_api_key:
                self.logger.warning(f"Failed API key authentication attempt from {request.remote_addr}")
                return jsonify({"error": "Invalid API key"}), 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def validate_admin_api_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Validate admin API key for manual operations.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        expected_key = os.getenv('ADMIN_API_KEY')
        
        if not expected_key:
            self.logger.warning("ADMIN_API_KEY not configured - admin endpoint disabled")
            return False, "Admin endpoint not configured"
        
        if not api_key or api_key != expected_key:
            self.logger.warning("Unauthorized access attempt to admin endpoint")
            return False, "Unauthorized"
        
        return True, ""