"""
Rate limiting utilities for API calls.

This module provides rate limiting functionality to stay within API quotas,
particularly for the Tiingo API free plan limits (50 requests/hour, 1,000 requests/day).
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from db_manager import DatabaseManager


class RateLimiter:
    """Rate limiter for API calls with database persistence."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the rate limiter.
        
        Args:
            db_manager: Database manager instance for persistent storage
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger("StockAlerts.RateLimiter")
        
        # Tiingo free plan limits
        self.HOURLY_LIMIT = 50
        self.DAILY_LIMIT = 1000
        
        # Keep some margin for safety
        self.SAFE_HOURLY_LIMIT = 48
        self.SAFE_DAILY_LIMIT = 980

    def can_make_request(self, api_name: str = "tiingo") -> Tuple[bool, Optional[str]]:
        """
        Check if we can make an API request without exceeding limits.
        
        Args:
            api_name: Name of the API (e.g., 'tiingo')
            
        Returns:
            Tuple of (can_make_request, reason_if_not)
        """
        try:
            now = datetime.now()
            
            # Get current usage counts
            hourly_count = self._get_hourly_count(api_name, now)
            daily_count = self._get_daily_count(api_name, now)
            
            # Check hourly limit
            if hourly_count >= self.SAFE_HOURLY_LIMIT:
                next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                wait_minutes = int((next_hour - now).total_seconds() / 60)
                return False, f"Hourly limit reached ({hourly_count}/{self.SAFE_HOURLY_LIMIT}). Try again in {wait_minutes} minutes."
            
            # Check daily limit
            if daily_count >= self.SAFE_DAILY_LIMIT:
                next_day = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                wait_hours = int((next_day - now).total_seconds() / 3600)
                return False, f"Daily limit reached ({daily_count}/{self.SAFE_DAILY_LIMIT}). Try again in {wait_hours} hours."
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error checking rate limit: {e}")
            # In case of error, be conservative and allow the request
            return True, None

    def record_request(self, api_name: str = "tiingo", success: bool = True) -> None:
        """
        Record an API request in the database.
        
        Args:
            api_name: Name of the API
            success: Whether the request was successful
        """
        try:
            self.db_manager.record_api_request(api_name, success)
        except Exception as e:
            self.logger.error(f"Error recording API request: {e}")

    def get_usage_stats(self, api_name: str = "tiingo") -> Dict[str, int]:
        """
        Get current usage statistics.
        
        Args:
            api_name: Name of the API
            
        Returns:
            Dictionary with usage statistics
        """
        try:
            now = datetime.now()
            hourly_count = self._get_hourly_count(api_name, now)
            daily_count = self._get_daily_count(api_name, now)
            
            return {
                "hourly_used": hourly_count,
                "hourly_limit": self.SAFE_HOURLY_LIMIT,
                "hourly_remaining": max(0, self.SAFE_HOURLY_LIMIT - hourly_count),
                "daily_used": daily_count,
                "daily_limit": self.SAFE_DAILY_LIMIT,
                "daily_remaining": max(0, self.SAFE_DAILY_LIMIT - daily_count),
            }
        except Exception as e:
            self.logger.error(f"Error getting usage stats: {e}")
            return {
                "hourly_used": 0,
                "hourly_limit": self.SAFE_HOURLY_LIMIT,
                "hourly_remaining": self.SAFE_HOURLY_LIMIT,
                "daily_used": 0,
                "daily_limit": self.SAFE_DAILY_LIMIT,
                "daily_remaining": self.SAFE_DAILY_LIMIT,
            }

    def _get_hourly_count(self, api_name: str, current_time: datetime) -> int:
        """Get the number of API calls made in the current hour."""
        try:
            hour_start = current_time.replace(minute=0, second=0, microsecond=0)
            return self.db_manager.get_api_request_count(api_name, hour_start, current_time)
        except Exception as e:
            self.logger.error(f"Error getting hourly count: {e}")
            return 0

    def _get_daily_count(self, api_name: str, current_time: datetime) -> int:
        """Get the number of API calls made in the current day."""
        try:
            day_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            return self.db_manager.get_api_request_count(api_name, day_start, current_time)
        except Exception as e:
            self.logger.error(f"Error getting daily count: {e}")
            return 0

    def wait_if_needed(self, api_name: str = "tiingo") -> bool:
        """
        Wait if necessary to avoid hitting rate limits.
        
        Args:
            api_name: Name of the API
            
        Returns:
            True if we can proceed, False if we should abort
        """
        can_proceed, reason = self.can_make_request(api_name)
        
        if not can_proceed:
            self.logger.warning(f"Rate limit check failed: {reason}")
            return False
        
        return True


class UserRateLimiter:
    """Rate limiter for user-facing endpoints."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the user rate limiter.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger("StockAlerts.UserRateLimiter")
        
        # Per-user limits to prevent abuse
        self.USER_HOURLY_LIMIT = 100  # requests per hour per user
        self.USER_DAILY_LIMIT = 500   # requests per day per user

    def can_user_make_request(self, user_identifier: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a user can make a request.
        
        Args:
            user_identifier: User IP address or identifier
            
        Returns:
            Tuple of (can_make_request, reason_if_not)
        """
        try:
            now = datetime.now()
            
            # Get user's request counts
            hourly_count = self._get_user_hourly_count(user_identifier, now)
            daily_count = self._get_user_daily_count(user_identifier, now)
            
            # Check hourly limit
            if hourly_count >= self.USER_HOURLY_LIMIT:
                return False, f"Too many requests. Limit: {self.USER_HOURLY_LIMIT} per hour."
            
            # Check daily limit
            if daily_count >= self.USER_DAILY_LIMIT:
                return False, f"Daily limit exceeded. Limit: {self.USER_DAILY_LIMIT} per day."
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error checking user rate limit: {e}")
            return True, None

    def record_user_request(self, user_identifier: str, endpoint: str) -> None:
        """
        Record a user request.
        
        Args:
            user_identifier: User IP address or identifier
            endpoint: API endpoint accessed
        """
        try:
            self.db_manager.record_user_request(user_identifier, endpoint)
        except Exception as e:
            self.logger.error(f"Error recording user request: {e}")

    def _get_user_hourly_count(self, user_identifier: str, current_time: datetime) -> int:
        """Get the number of requests made by a user in the current hour."""
        try:
            hour_start = current_time.replace(minute=0, second=0, microsecond=0)
            return self.db_manager.get_user_request_count(user_identifier, hour_start, current_time)
        except Exception as e:
            self.logger.error(f"Error getting user hourly count: {e}")
            return 0

    def _get_user_daily_count(self, user_identifier: str, current_time: datetime) -> int:
        """Get the number of requests made by a user in the current day."""
        try:
            day_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            return self.db_manager.get_user_request_count(user_identifier, day_start, current_time)
        except Exception as e:
            self.logger.error(f"Error getting user daily count: {e}")
            return 0