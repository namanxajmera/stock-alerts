"""
Stock repository for handling stock-related database operations.

This repository encapsulates all stock-related database operations including
stock cache management and trading statistics.
"""

import json
import logging
from typing import Any, Dict, Optional

from database.connection_manager import ConnectionManager
from type_definitions.stock_types import StockCacheRow

logger = logging.getLogger("StockAlerts.StockRepository")


class StockRepository:
    """Repository class for stock-related database operations."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """
        Initialize the StockRepository.

        Args:
            connection_manager: Database connection manager instance
        """
        self.connection_manager = connection_manager
        self.logger = logging.getLogger("StockAlerts.StockRepository")

    def update_stock_cache(
        self, symbol: str, price: float, ma_200: Optional[float], data_json: str
    ) -> bool:
        """Update or insert stock data in cache."""
        sql = """
            INSERT INTO stock_cache (symbol, last_check, last_price, ma_200, data_json)
            VALUES (%s, NOW(), %s, %s, %s)
            ON CONFLICT(symbol) DO UPDATE SET
                last_check = NOW(),
                last_price = excluded.last_price,
                ma_200 = excluded.ma_200,
                data_json = excluded.data_json
        """
        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute(sql, (symbol.upper(), price, ma_200, data_json))
            return True
        except Exception:
            logger.error(f"Error updating stock cache for {symbol}")
            return False

    def get_fresh_cache(
        self, symbol: str, max_age_hours: int = 1
    ) -> Optional[StockCacheRow]:
        """Get cached stock data if it's recent enough."""
        sql = """
            SELECT symbol, last_check, last_price, ma_200, data_json
            FROM stock_cache
            WHERE symbol = %s
            AND last_check > NOW() - INTERVAL '%s hours'
        """

        try:
            with self.connection_manager.get_cursor() as cursor:
                cursor.execute(sql, (symbol.upper(), max_age_hours))
                row = cursor.fetchone()
                if row:
                    logger.info(
                        f"Using cached data for {symbol} (age: {row['last_check']})"
                    )
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error getting cached data for {symbol}: {e}")
            return None

    def get_fresh_trading_stats_cache(
        self, symbol: str, period: str, max_age_hours: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Get cached trading stats if recent enough."""
        sql = """
            SELECT symbol, period, stats_json, last_updated
            FROM trading_stats_cache
            WHERE symbol = %s AND period = %s
            AND last_updated > NOW() - INTERVAL '%s hours'
        """

        try:
            with self.connection_manager.get_cursor() as cursor:
                cursor.execute(sql, (symbol.upper(), period, max_age_hours))
                row = cursor.fetchone()
                if row:
                    logger.info(
                        f"Using cached trading stats for {symbol}/{period} (age: {row['last_updated']})"
                    )
                    return {
                        "symbol": row["symbol"],
                        "period": row["period"],
                        "stats_json": row["stats_json"],
                        "last_updated": row["last_updated"],
                    }
                return None
        except Exception as e:
            logger.error(
                f"Error getting cached trading stats for {symbol}/{period}: {e}"
            )
            return None

    def update_trading_stats_cache(
        self, symbol: str, period: str, stats_json: str
    ) -> bool:
        """Update or insert trading stats cache."""
        sql = """
            INSERT INTO trading_stats_cache (symbol, period, stats_json, last_updated)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (symbol, period) DO UPDATE SET
                stats_json = EXCLUDED.stats_json,
                last_updated = EXCLUDED.last_updated
        """

        try:
            with self.connection_manager.get_cursor(commit=True) as cursor:
                cursor.execute(sql, (symbol.upper(), period, stats_json))
                logger.info(f"Updated trading stats cache for {symbol}/{period}")
                return True
        except Exception as e:
            logger.error(
                f"Error updating trading stats cache for {symbol}/{period}: {e}"
            )
            return False