"""
Database connection management for Stock Alerts application.

This module provides centralized database connection pooling and management
using PostgreSQL with psycopg2.
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool

logger = logging.getLogger("StockAlerts.ConnectionManager")


class ConnectionManager:
    """Database connection manager with connection pooling for PostgreSQL operations."""

    def __init__(
        self,
        db_url: Optional[str] = None,
        pool_min_conn: int = 1,
        pool_max_conn: int = 20,
    ) -> None:
        """Initialize the connection manager with connection pooling."""
        logger.info("ConnectionManager __init__ starting...")
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
            logger.info(
                f"Connection pool created successfully (min: {pool_min_conn}, max: {pool_max_conn})"
            )
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}", exc_info=True)
            raise

        logger.info("Starting database initialization...")
        self.initialize_database()
        logger.info("ConnectionManager __init__ completed successfully")

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
    def get_cursor(
        self, commit: bool = False
    ) -> Generator[psycopg2.extras.RealDictCursor, None, None]:
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
            if hasattr(self, "connection_pool") and self.connection_pool:
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

                # Always check for pending migrations (don't skip based on users table)
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