import sqlite3
import os
from datetime import datetime
from termcolor import colored
import traceback

class DatabaseManager:
    def __init__(self, db_path='db/stockalerts.db'):
        """Initialize the database manager."""
        self.db_path = db_path
        self._ensure_db_directory()
        self.initialize_database()

    def _ensure_db_directory(self):
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
            print(colored("Initializing database...", "cyan"))
            conn = self._get_connection()
            
            # Read and execute all migration files in order
            migrations_dir = 'migrations'
            migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
            
            for migration_file in migration_files:
                print(colored(f"Applying migration: {migration_file}", "cyan"))
                with open(os.path.join(migrations_dir, migration_file), 'r', encoding='utf-8') as f:
                    migration_sql = f.read()
                    conn.executescript(migration_sql)
            
            conn.commit()
            print(colored("Database initialization complete.", "green"))
        except Exception as e:
            print(colored(f"Error initializing database: {str(e)}", "red"))
            print(colored(traceback.format_exc(), "red"))
            raise
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
        """Log an event to the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO logs (timestamp, log_type, message, user_id, symbol)
                VALUES (datetime('now'), ?, ?, ?, ?)
            """, (log_type, message, user_id, symbol))
            
            conn.commit()
        except Exception as e:
            print(colored(f"Error logging event: {str(e)}", "red"))
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