"""
User repository for handling user-related database operations.

This repository encapsulates all user-related database operations including
user management, watchlists, and notification preferences.
"""

import logging
from typing import List, Optional, Tuple, Union

from database.connection_manager import ConnectionManager
from type_definitions.user_types import WatchlistItemWithPrice

logger = logging.getLogger("StockAlerts.UserRepository")


class UserRepository:
    """Repository class for user-related database operations."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """
        Initialize the UserRepository.

        Args:
            connection_manager: Database connection manager instance
        """
        self.connection_manager = connection_manager
        self.logger = logging.getLogger("StockAlerts.UserRepository")

    def add_user(self, user_id: Union[str, int], name: str) -> bool:
        """Add a new user or update their name."""
        sql = """
            INSERT INTO users (id, name) VALUES (%s, %s)
            ON CONFLICT(id) DO UPDATE SET name = excluded.name
        """
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute(sql, (user_id, name))
            logger.info(f"User {name} ({user_id}) added/updated successfully")
            return True
        except Exception:
            logger.error(f"Error adding/updating user {user_id}")
            return False

    def add_to_watchlist(self, user_id: Union[str, int], symbol: str) -> Tuple[bool, Optional[str]]:
        """Add a stock to user's watchlist."""
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute("SELECT max_stocks FROM users WHERE id = %s", (user_id,))
                user_row = cursor.fetchone()
                if not user_row:
                    raise ValueError("User does not exist")
                max_stocks = user_row["max_stocks"]

                cursor.execute(
                    "SELECT COUNT(*) as count FROM watchlist_items WHERE user_id = %s",
                    (user_id,),
                )
                current_count = cursor.fetchone()["count"]

                if current_count >= max_stocks:
                    raise ValueError(f"Watchlist limit of {max_stocks} stocks reached")

                cursor.execute(
                    "INSERT INTO watchlist_items (user_id, symbol) VALUES (%s, %s)",
                    (user_id, symbol.upper()),
                )
            logger.info(f"Added {symbol} to watchlist for user {user_id}")
            return True, None
        except Exception as e:
            logger.error(f"Error adding to watchlist for user {user_id}: {e}")
            return False, str(e)

    def remove_from_watchlist(self, user_id: Union[str, int], symbol: str) -> bool:
        """Remove a stock from user's watchlist."""
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute(
                    "DELETE FROM watchlist_items WHERE user_id = %s AND symbol = %s",
                    (user_id, symbol.upper()),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Stock {symbol} not found in watchlist")
            logger.info(f"Removed {symbol} from watchlist for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing from watchlist for user {user_id}: {e}")
            return False

    def get_watchlist(self, user_id: Union[str, int]) -> List[WatchlistItemWithPrice]:
        """Get user's watchlist with current prices."""
        sql = """
            SELECT w.symbol, w.is_owned, w.alert_threshold_low, w.alert_threshold_high, sc.last_price, sc.ma_200
            FROM watchlist_items w
            LEFT JOIN stock_cache sc ON w.symbol = sc.symbol
            WHERE w.user_id = %s ORDER BY w.is_owned DESC, w.symbol
        """
        try:
            with self.connection_manager.get_cursor() as cursor:
                cursor.execute(sql, (user_id,))
                rows = cursor.fetchall()
                return [
                    WatchlistItemWithPrice(
                        symbol=row["symbol"],
                        is_owned=row["is_owned"],
                        alert_threshold_low=row["alert_threshold_low"],
                        alert_threshold_high=row["alert_threshold_high"],
                        last_price=row["last_price"],
                        ma_200=row["ma_200"],
                    )
                    for row in rows
                ]
        except Exception:
            logger.error(f"Error getting watchlist for user {user_id}")
            return []

    def set_position_owned(self, user_id: Union[str, int], symbol: str, is_owned: bool = True) -> bool:
        """Mark a stock as owned or not owned in user's watchlist."""
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute(
                    "UPDATE watchlist_items SET is_owned = %s WHERE user_id = %s AND symbol = %s",
                    (is_owned, user_id, symbol.upper()),
                )
                if cursor.rowcount == 0:
                    return False  # Stock not found in watchlist
            logger.info(f"Set {symbol} as {'owned' if is_owned else 'watched'} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting position for {symbol} for user {user_id}: {e}")
            return False

    def get_positions(self, user_id: Union[str, int]) -> List[WatchlistItemWithPrice]:
        """Get user's owned positions."""
        sql = """
            SELECT w.symbol, w.is_owned, w.alert_threshold_low, w.alert_threshold_high, sc.last_price, sc.ma_200
            FROM watchlist_items w
            LEFT JOIN stock_cache sc ON w.symbol = sc.symbol
            WHERE w.user_id = %s AND w.is_owned = TRUE ORDER BY w.symbol
        """
        try:
            with self.connection_manager.get_cursor() as cursor:
                cursor.execute(sql, (user_id,))
                rows = cursor.fetchall()
                return [
                    WatchlistItemWithPrice(
                        symbol=row["symbol"],
                        is_owned=row["is_owned"],
                        alert_threshold_low=row["alert_threshold_low"],
                        alert_threshold_high=row["alert_threshold_high"],
                        last_price=row["last_price"],
                        ma_200=row["ma_200"],
                    )
                    for row in rows
                ]
        except Exception:
            logger.error(f"Error getting positions for user {user_id}")
            return []

    def get_watchlist_only(self, user_id: Union[str, int]) -> List[WatchlistItemWithPrice]:
        """Get user's watched stocks (not owned)."""
        sql = """
            SELECT w.symbol, w.is_owned, w.alert_threshold_low, w.alert_threshold_high, sc.last_price, sc.ma_200
            FROM watchlist_items w
            LEFT JOIN stock_cache sc ON w.symbol = sc.symbol
            WHERE w.user_id = %s AND w.is_owned = FALSE ORDER BY w.symbol
        """
        try:
            with self.connection_manager.get_cursor() as cursor:
                cursor.execute(sql, (user_id,))
                rows = cursor.fetchall()
                return [
                    WatchlistItemWithPrice(
                        symbol=row["symbol"],
                        is_owned=row["is_owned"],
                        alert_threshold_low=row["alert_threshold_low"],
                        alert_threshold_high=row["alert_threshold_high"],
                        last_price=row["last_price"],
                        ma_200=row["ma_200"],
                    )
                    for row in rows
                ]
        except Exception:
            logger.error(f"Error getting watchlist for user {user_id}")
            return []

    def update_user_notification_time(self, user_id: Union[str, int]) -> bool:
        """Update the last notification time for a user."""
        sql = "UPDATE users SET last_notified = NOW() WHERE id = %s"
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute(sql, (user_id,))
            return True
        except Exception:
            logger.error(f"Error updating notification time for user {user_id}")
            return False