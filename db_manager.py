import sqlite3
import os
from datetime import datetime
from termcolor import colored
import traceback
import logging

logger = logging.getLogger('StockAlerts.DB')

class DatabaseManager:
    def __init__(self, db_path='db/stockalerts.db'):
        """Initialize the database manager."""
        self.db_path = db_path
        self._ensure_directories()
        self.initialize_database()

    def _ensure_directories(self):
        """Ensure the database directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _get_connection(self):
        """Get a database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize_database(self):
        """Initialize the database schema if it doesn't exist."""
        try:
            logger.info("Initializing database...")
            conn = self._get_connection()
            cursor = conn.cursor()

            # Check if tables already exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if cursor.fetchone() is not None:
                logger.info("Database already initialized, skipping...")
                return

            # If tables don't exist, create them from migrations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

            # Get list of applied migrations
            cursor.execute("SELECT filename FROM migrations")
            applied_migrations = {row['filename'] for row in cursor.fetchall()}

            # Read and execute new migration files
            migrations_dir = 'migrations'
            if not os.path.exists(migrations_dir):
                logger.warning(f"Migrations directory '{migrations_dir}' not found")
                return

            migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
            
            for migration_file in migration_files:
                if migration_file in applied_migrations:
                    logger.debug(f"Skipping already applied migration: {migration_file}")
                    continue

                logger.info(f"Applying migration: {migration_file}")
                try:
                    with open(os.path.join(migrations_dir, migration_file), 'r', encoding='utf-8') as f:
                        migration_sql = f.read()
                        
                    cursor.execute("BEGIN TRANSACTION")
                    cursor.executescript(migration_sql)
                    cursor.execute(
                        "INSERT INTO migrations (filename) VALUES (?)",
                        (migration_file,)
                    )
                    cursor.execute("COMMIT")
                    logger.info(f"Successfully applied migration: {migration_file}")
                    
                except Exception as e:
                    cursor.execute("ROLLBACK")
                    logger.error(f"Error applying migration {migration_file}: {str(e)}")
                    logger.error(traceback.format_exc())
                    raise

            logger.info("Database initialization complete")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            conn.close()

    def add_user(self, user_id, name):
        """Add a new user to the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO users (id, name)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name
            """, (user_id, name))
            
            conn.commit()
            print(colored(f"User {name} ({user_id}) added/updated successfully", "green"))
            return True
        except Exception as e:
            print(colored(f"Error adding user: {str(e)}", "red"))
            return False
        finally:
            conn.close()

    def add_to_watchlist(self, user_id, symbol):
        """Add a stock to user's watchlist."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE id = ?", (user_id,))
            if cursor.fetchone()[0] == 0:
                raise ValueError("User does not exist")
            
            # Check watchlist limit
            cursor.execute("SELECT COUNT(*) FROM watchlist_items WHERE user_id = ?", (user_id,))
            current_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT max_stocks FROM users WHERE id = ?", (user_id,))
            max_stocks = cursor.fetchone()[0]
            
            if current_count >= max_stocks:
                raise ValueError(f"Watchlist limit of {max_stocks} stocks reached")
            
            # Add to watchlist
            cursor.execute("""
                INSERT INTO watchlist_items (user_id, symbol)
                VALUES (?, ?)
            """, (user_id, symbol.upper()))
            
            conn.commit()
            print(colored(f"Added {symbol} to watchlist for user {user_id}", "green"))
            return True
        except Exception as e:
            print(colored(f"Error adding to watchlist: {str(e)}", "red"))
            return False
        finally:
            conn.close()

    def remove_from_watchlist(self, user_id, symbol):
        """Remove a stock from user's watchlist."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM watchlist_items
                WHERE user_id = ? AND symbol = ?
            """, (user_id, symbol.upper()))
            
            if cursor.rowcount == 0:
                raise ValueError(f"Stock {symbol} not found in watchlist")
            
            conn.commit()
            print(colored(f"Removed {symbol} from watchlist for user {user_id}", "green"))
            return True
        except Exception as e:
            print(colored(f"Error removing from watchlist: {str(e)}", "red"))
            return False
        finally:
            conn.close()

    def get_watchlist(self, user_id):
        """Get user's watchlist with current prices."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT w.symbol, w.alert_threshold_low, w.alert_threshold_high,
                       sc.last_price, sc.ma_200
                FROM watchlist_items w
                LEFT JOIN stock_cache sc ON w.symbol = sc.symbol
                WHERE w.user_id = ?
                ORDER BY w.symbol
            """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(colored(f"Error getting watchlist: {str(e)}", "red"))
            return []
        finally:
            conn.close()

    def update_stock_cache(self, symbol, price, ma_200, data_json):
        """Update or insert stock data in cache."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO stock_cache (symbol, last_check, last_price, ma_200, data_json)
                VALUES (?, datetime('now'), ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    last_check = datetime('now'),
                    last_price = excluded.last_price,
                    ma_200 = excluded.ma_200,
                    data_json = excluded.data_json
            """, (symbol.upper(), price, ma_200, data_json))
            
            conn.commit()
            print(colored(f"Updated cache for {symbol}", "green"))
            return True
        except Exception as e:
            print(colored(f"Error updating stock cache: {str(e)}", "red"))
            return False
        finally:
            conn.close()

    def log_event(self, log_type, message, user_id=None, symbol=None):
        """Log an event to both the database and log file."""
        try:
            # Log to database
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO logs (timestamp, log_type, message, user_id, symbol)
                VALUES (datetime('now'), ?, ?, ?, ?)
            """, (log_type, message, user_id, symbol))
            
            conn.commit()

            # Log to file
            log_message = f"{log_type}: {message}"
            if user_id:
                log_message += f" [User: {user_id}]"
            if symbol:
                log_message += f" [Symbol: {symbol}]"

            if log_type == 'error':
                logger.error(log_message)
            else:
                logger.info(log_message)

        except Exception as e:
            logger.error(f"Error logging event: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            conn.close()

    def get_config(self, key):
        """Get configuration value."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            return row['value'] if row else None
        except Exception as e:
            print(colored(f"Error getting config: {str(e)}", "red"))
            return None
        finally:
            conn.close()

    def set_config(self, key, value, modified_by=None):
        """Set configuration value."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE config 
                SET value = ?, last_modified = datetime('now'), modified_by = ?
                WHERE key = ?
            """, (value, modified_by, key))
            
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO config (key, value, modified_by)
                    VALUES (?, ?, ?)
                """, (key, value, modified_by))
            
            conn.commit()
            return True
        except Exception as e:
            print(colored(f"Error setting config: {str(e)}", "red"))
            return False
        finally:
            conn.close()

    def add_alert_history(self, user_id, symbol, price, percentile, status='sent', error_message=None):
        """Add an alert to the history."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO alert_history 
                (user_id, symbol, price, percentile, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, symbol.upper(), price, percentile, status, error_message))
            
            conn.commit()
            print(colored(f"Added alert history for {symbol}", "green"))
            return True
        except Exception as e:
            print(colored(f"Error adding alert history: {str(e)}", "red"))
            return False
        finally:
            conn.close()

    def get_user_alerts(self, user_id, days=7):
        """Get recent alerts for a user."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT *
                FROM alert_history
                WHERE user_id = ?
                AND datetime(sent_at) >= datetime('now', ?)
                ORDER BY sent_at DESC
            """, (user_id, f'-{days} days'))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(colored(f"Error getting user alerts: {str(e)}", "red"))
            return []
        finally:
            conn.close()

    def get_active_watchlists(self):
        """Get all active watchlists with current prices."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    w.user_id,
                    w.symbol,
                    w.alert_threshold_low,
                    w.alert_threshold_high,
                    w.last_alerted_at,
                    sc.last_price,
                    sc.ma_200
                FROM watchlist_items w
                LEFT JOIN stock_cache sc ON w.symbol = sc.symbol
            """)
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(colored(f"Error getting active watchlists: {str(e)}", "red"))
            return []
        finally:
            conn.close()

    def get_alert_statistics(self, user_id=None):
        """Get alert statistics, optionally filtered by user."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("""
                    SELECT * FROM alert_statistics
                    WHERE user_id = ?
                """, (user_id,))
            else:
                cursor.execute("SELECT * FROM alert_statistics")
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(colored(f"Error getting alert statistics: {str(e)}", "red"))
            return []
        finally:
            conn.close()

    def update_user_notification_time(self, user_id):
        """Update the last notification time for a user."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users
                SET last_notified = datetime('now')
                WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(colored(f"Error updating notification time: {str(e)}", "red"))
            return False
        finally:
            conn.close() 