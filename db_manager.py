import psycopg2
import psycopg2.extras
import psycopg2.pool
import os
from datetime import datetime
import traceback
import logging
from contextlib import contextmanager
from urllib.parse import urlparse
from typing import Dict, List, Optional, Union, Any, Tuple, Generator
from type_definitions.user_types import User, WatchlistItem, AlertHistory, WatchlistItemWithPrice, UserRow, WatchlistItemRow, AlertHistoryRow
from type_definitions.stock_types import StockCache, StockCacheRow

logger = logging.getLogger("StockAlerts.DB")


class DatabaseManager:
    def __init__(self, db_url: Optional[str] = None, pool_min_conn: int = 1, pool_max_conn: int = 20) -> None:
        """Initialize the database manager with connection pooling."""
        logger.info("DatabaseManager __init__ starting...")
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.error("DATABASE_URL environment variable is missing")
            raise ValueError("DATABASE_URL environment variable is required")
        
        logger.info(f"DATABASE_URL configured: {self.db_url[:50]}...")
        logger.info("Initializing connection pool...")
        
        # Initialize connection pool
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                pool_min_conn, pool_max_conn, self.db_url
            )
            logger.info(f"Connection pool created successfully (min: {pool_min_conn}, max: {pool_max_conn})")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}", exc_info=True)
            raise
        
        logger.info("Starting database initialization...")
        self.initialize_database()
        logger.info("DatabaseManager __init__ completed successfully")

    def _get_connection(self) -> psycopg2.extensions.connection:
        """Get a database connection from the pool."""
        try:
            conn = self.connection_pool.getconn()
            if conn is None:
                raise psycopg2.pool.PoolError("Unable to get connection from pool")
            return conn
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}", exc_info=True)
            raise

    def _return_connection(self, conn: psycopg2.extensions.connection) -> None:
        """Return a connection to the pool."""
        try:
            self.connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}", exc_info=True)

    @contextmanager
    def _managed_cursor(self, commit: bool = False) -> Generator[psycopg2.extras.RealDictCursor, None, None]:
        """A context manager for database connections and cursors using connection pool."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            yield cursor
            if commit:
                conn.commit()
        except psycopg2.Error as e:
            logger.error(f"Database error: {e}", exc_info=True)
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self._return_connection(conn)

    def close_pool(self) -> None:
        """Close all connections in the pool."""
        try:
            if hasattr(self, 'connection_pool') and self.connection_pool:
                self.connection_pool.closeall()
                logger.info("Connection pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}", exc_info=True)

    def initialize_database(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        try:
            logger.info("Initializing database...")
            logger.info("Attempting database connection...")
            with self._get_connection() as conn:
                logger.info("Database connection successful")
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # Check if database needs migration by looking for users table
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'users'
                    )
                """
                )
                result = cursor.fetchone()
                if result and result["exists"]:
                    logger.info("Database already initialized, skipping.")
                    return

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS migrations (
                        id SERIAL PRIMARY KEY,
                        filename TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                conn.commit()

                cursor.execute("SELECT filename FROM migrations")
                applied_migrations = {row["filename"] for row in cursor.fetchall()}

                migrations_dir = "migrations"
                if not os.path.exists(migrations_dir):
                    logger.warning(f"Migrations directory '{migrations_dir}' not found")
                    return

                migration_files = sorted(
                    [f for f in os.listdir(migrations_dir) if f.endswith(".sql")]
                )

                for migration_file in migration_files:
                    if migration_file in applied_migrations:
                        continue

                    logger.info(f"Applying migration: {migration_file}")
                    try:
                        with open(
                            os.path.join(migrations_dir, migration_file),
                            "r",
                            encoding="utf-8",
                        ) as f:
                            migration_sql = f.read()

                        cursor.execute("BEGIN")
                        cursor.execute(migration_sql)
                        cursor.execute(
                            "INSERT INTO migrations (filename) VALUES (%s)",
                            (migration_file,),
                        )
                        cursor.execute("COMMIT")
                        logger.info(f"Successfully applied migration: {migration_file}")
                    except Exception as e:
                        cursor.execute("ROLLBACK")
                        logger.error(
                            f"Error applying migration {migration_file}: {e}",
                            exc_info=True,
                        )
                        raise
            logger.info("Database initialization complete")
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)

    def add_user(self, user_id: str, name: str) -> bool:
        """Add a new user or update their name."""
        sql = """
            INSERT INTO users (id, name) VALUES (%s, %s)
            ON CONFLICT(id) DO UPDATE SET name = excluded.name
        """
        try:
            with self._managed_cursor(commit=True) as cursor:
                cursor.execute(sql, (user_id, name))
            logger.info(f"User {name} ({user_id}) added/updated successfully")
            return True
        except Exception:
            logger.error(f"Error adding/updating user {user_id}")
            return False

    def add_to_watchlist(self, user_id: str, symbol: str) -> Tuple[bool, Optional[str]]:
        """Add a stock to user's watchlist."""
        try:
            with self._managed_cursor(commit=True) as cursor:
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

    def remove_from_watchlist(self, user_id: str, symbol: str) -> bool:
        """Remove a stock from user's watchlist."""
        try:
            with self._managed_cursor(commit=True) as cursor:
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

    def get_watchlist(self, user_id: str) -> List[WatchlistItemWithPrice]:
        """Get user's watchlist with current prices."""
        sql = """
            SELECT w.symbol, w.alert_threshold_low, w.alert_threshold_high, sc.last_price, sc.ma_200
            FROM watchlist_items w
            LEFT JOIN stock_cache sc ON w.symbol = sc.symbol
            WHERE w.user_id = %s ORDER BY w.symbol
        """
        try:
            with self._managed_cursor() as cursor:
                cursor.execute(sql, (user_id,))
                rows = cursor.fetchall()
                return [WatchlistItemWithPrice(
                    symbol=row['symbol'],
                    alert_threshold_low=row['alert_threshold_low'],
                    alert_threshold_high=row['alert_threshold_high'],
                    last_price=row['last_price'],
                    ma_200=row['ma_200']
                ) for row in rows]
        except Exception:
            logger.error(f"Error getting watchlist for user {user_id}")
            return []

    def update_stock_cache(self, symbol: str, price: float, ma_200: Optional[float], data_json: str) -> bool:
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
            with self._managed_cursor(commit=True) as cursor:
                cursor.execute(sql, (symbol.upper(), price, ma_200, data_json))
            return True
        except Exception:
            logger.error(f"Error updating stock cache for {symbol}")
            return False

    def log_event(self, log_type: str, message: str, user_id: Optional[str] = None, symbol: Optional[str] = None) -> None:
        """Log an event to the database."""
        sql = "INSERT INTO logs (timestamp, log_type, message, user_id, symbol) VALUES (NOW(), %s, %s, %s, %s)"
        try:
            with self._managed_cursor(commit=True) as cursor:
                cursor.execute(sql, (log_type, message, user_id, symbol))
        except Exception as e:
            # Log to logger as a fallback if DB logging fails
            logger.error(f"CRITICAL: Failed to write log to database: {e}")
            logger.error(f"Original log message: [{log_type}] {message}")

    def get_config(self, key: str) -> Optional[str]:
        """Get configuration value."""
        try:
            with self._managed_cursor() as cursor:
                cursor.execute("SELECT value FROM config WHERE key = %s", (key,))
                row = cursor.fetchone()
                return row["value"] if row else None
        except Exception:
            logger.error(f"Error getting config for key {key}")
            return None

    def add_alert_history(
        self, user_id: str, symbol: str, price: float, percentile: float, status: str = "sent", error_message: Optional[str] = None
    ) -> bool:
        """Add an alert to the history."""
        sql = """
            INSERT INTO alert_history (user_id, symbol, price, percentile, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            with self._managed_cursor(commit=True) as cursor:
                cursor.execute(
                    sql,
                    (user_id, symbol.upper(), price, percentile, status, error_message),
                )
            logger.info(f"Added alert history for {symbol} for user {user_id}")
            return True
        except Exception:
            logger.error(f"Error adding alert history for {symbol} user {user_id}")
            return False

    def get_active_watchlists(self) -> List[Dict[str, Union[str, int]]]:
        """Get all active watchlists."""
        sql = """
            SELECT w.user_id, w.symbol
            FROM watchlist_items w
            JOIN users u ON w.user_id = u.id
            WHERE u.notification_enabled = TRUE
        """
        try:
            with self._managed_cursor() as cursor:
                cursor.execute(sql)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting active watchlists: {e}")
            return []

    def update_user_notification_time(self, user_id: str) -> bool:
        """Update the last notification time for a user."""
        sql = "UPDATE users SET last_notified = NOW() WHERE id = %s"
        try:
            with self._managed_cursor(commit=True) as cursor:
                cursor.execute(sql, (user_id,))
            return True
        except Exception:
            logger.error(f"Error updating notification time for user {user_id}")
            return False

    def get_fresh_cache(self, symbol: str, max_age_hours: int = 1) -> Optional[StockCacheRow]:
        """Get cached stock data if it's recent enough."""
        sql = """
            SELECT symbol, last_check, last_price, ma_200, data_json
            FROM stock_cache
            WHERE symbol = %s
            AND last_check > NOW() - INTERVAL '%s hours'
        """

        try:
            with self._managed_cursor() as cursor:
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
