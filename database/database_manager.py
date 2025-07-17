"""
Unified Database Manager using Repository Pattern.

This module provides a unified interface to all database operations
while maintaining the repository pattern for better organization.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

from database.connection_manager import ConnectionManager
from database.repositories.alert_repository import AlertRepository
from database.repositories.stock_repository import StockRepository
from database.repositories.system_repository import SystemRepository
from database.repositories.user_repository import UserRepository
from type_definitions.stock_types import StockCacheRow
from type_definitions.user_types import WatchlistItemWithPrice

logger = logging.getLogger("StockAlerts.DatabaseManager")


class DatabaseManager:
    """
    Unified database manager using repository pattern.
    
    This class provides a single interface to all database operations
    while delegating to specialized repository classes.
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        pool_min_conn: int = 1,
        pool_max_conn: int = 20,
    ) -> None:
        """Initialize the database manager with repositories."""
        logger.info("DatabaseManager __init__ starting...")
        
        # Initialize connection manager
        self.connection_manager = ConnectionManager(db_url, pool_min_conn, pool_max_conn)
        
        # Initialize repositories
        self.users = UserRepository(self.connection_manager)
        self.stocks = StockRepository(self.connection_manager)
        self.alerts = AlertRepository(self.connection_manager)
        self.system = SystemRepository(self.connection_manager)
        
        logger.info("DatabaseManager initialized with repository pattern")

    def close_pool(self) -> None:
        """Close all connections in the pool."""
        self.connection_manager.close_pool()

    # User-related methods (delegate to UserRepository)
    def add_user(self, user_id: Union[str, int], name: str) -> bool:
        """Add a new user or update their name."""
        return self.users.add_user(user_id, name)

    def add_to_watchlist(
        self, user_id: Union[str, int], symbol: str
    ) -> Tuple[bool, Optional[str]]:
        """Add a stock to user's watchlist."""
        return self.users.add_to_watchlist(user_id, symbol)

    def remove_from_watchlist(self, user_id: Union[str, int], symbol: str) -> bool:
        """Remove a stock from user's watchlist."""
        return self.users.remove_from_watchlist(user_id, symbol)

    def get_watchlist(self, user_id: Union[str, int]) -> List[WatchlistItemWithPrice]:
        """Get user's watchlist with current prices."""
        return self.users.get_watchlist(user_id)

    def set_position_owned(self, user_id: Union[str, int], symbol: str, is_owned: bool = True) -> bool:
        """Mark a stock as owned or not owned in user's watchlist."""
        return self.users.set_position_owned(user_id, symbol, is_owned)

    def get_positions(self, user_id: Union[str, int]) -> List[WatchlistItemWithPrice]:
        """Get user's owned positions."""
        return self.users.get_positions(user_id)

    def get_watchlist_only(self, user_id: Union[str, int]) -> List[WatchlistItemWithPrice]:
        """Get user's watched stocks (not owned)."""
        return self.users.get_watchlist_only(user_id)

    def update_user_notification_time(self, user_id: Union[str, int]) -> bool:
        """Update the last notification time for a user."""
        return self.users.update_user_notification_time(user_id)

    # Stock-related methods (delegate to StockRepository)
    def update_stock_cache(
        self, symbol: str, price: float, ma_200: Optional[float], data_json: str
    ) -> bool:
        """Update or insert stock data in cache."""
        return self.stocks.update_stock_cache(symbol, price, ma_200, data_json)

    def get_fresh_cache(
        self, symbol: str, max_age_hours: int = 1
    ) -> Optional[StockCacheRow]:
        """Get cached stock data if it's recent enough."""
        return self.stocks.get_fresh_cache(symbol, max_age_hours)

    def get_fresh_trading_stats_cache(
        self, symbol: str, period: str, max_age_hours: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Get cached trading stats if recent enough."""
        return self.stocks.get_fresh_trading_stats_cache(symbol, period, max_age_hours)

    def update_trading_stats_cache(
        self, symbol: str, period: str, stats_json: str
    ) -> bool:
        """Update or insert trading stats cache."""
        return self.stocks.update_trading_stats_cache(symbol, period, stats_json)

    # Alert-related methods (delegate to AlertRepository)
    def add_alert_history(
        self,
        user_id: Union[str, int],
        symbol: str,
        price: float,
        percentile: float,
        status: str = "sent",
        error_message: Optional[str] = None,
    ) -> bool:
        """Add an alert to the history."""
        return self.alerts.add_alert_history(user_id, symbol, price, percentile, status, error_message)

    def get_active_watchlists(self) -> List[Dict[str, Union[str, int]]]:
        """Get all active watchlists."""
        return self.alerts.get_active_watchlists()

    # System-related methods (delegate to SystemRepository)
    def log_event(
        self,
        log_type: str,
        message: str,
        user_id: Optional[Union[str, int]] = None,
        symbol: Optional[str] = None,
    ) -> None:
        """Log an event to the database."""
        self.system.log_event(log_type, message, user_id, symbol)

    def get_config(self, key: str) -> Optional[str]:
        """Get configuration value."""
        return self.system.get_config(key)

    def record_api_request(self, api_name: str, success: bool = True) -> bool:
        """Record an API request for rate limiting."""
        return self.system.record_api_request(api_name, success)

    def get_api_request_count(
        self, api_name: str, start_time: datetime, end_time: datetime
    ) -> int:
        """Get the number of API requests in a time period."""
        return self.system.get_api_request_count(api_name, start_time, end_time)

    def record_user_request(self, user_identifier: str, endpoint: str) -> bool:
        """Record a user request for rate limiting."""
        return self.system.record_user_request(user_identifier, endpoint)

    def get_user_request_count(
        self, user_identifier: str, start_time: datetime, end_time: datetime
    ) -> int:
        """Get the number of user requests in a time period."""
        return self.system.get_user_request_count(user_identifier, start_time, end_time)

    def get_admin_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve all admin panel data from the database."""
        return self.system.get_admin_data()

    # Backward compatibility methods (maintain existing interface)
    def initialize_database(self) -> None:
        """Initialize the database schema (handled by ConnectionManager)."""
        # This is now handled by the ConnectionManager during initialization
        pass

    def _managed_cursor(self, commit: bool = False) -> Any:
        """Backward compatibility method - use connection_manager.get_cursor instead."""
        return self.connection_manager.get_cursor(commit=commit)
