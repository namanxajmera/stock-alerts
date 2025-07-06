#!/usr/bin/env python3
"""
Standalone migration runner for Railway deployment.
Run this script to apply pending database migrations.
"""

import os
import sys
import logging
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# Load environment variables
load_dotenv(".env")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("Migration")

def run_migrations():
    """Run all pending database migrations."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        sys.exit(1)
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Create migrations table if it doesn't exist
        logger.info("Ensuring migrations table exists...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Get list of applied migrations
        cursor.execute("SELECT filename FROM migrations")
        applied_migrations = {row["filename"] for row in cursor.fetchall()}
        logger.info(f"Applied migrations: {applied_migrations}")
        
        # Get list of migration files
        migrations_dir = "migrations"
        if not os.path.exists(migrations_dir):
            logger.error(f"Migrations directory '{migrations_dir}' not found")
            sys.exit(1)
        
        migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
        logger.info(f"Available migrations: {migration_files}")
        
        # Apply pending migrations
        pending_migrations = [f for f in migration_files if f not in applied_migrations]
        
        if not pending_migrations:
            logger.info("No pending migrations to apply")
            return
        
        logger.info(f"Applying {len(pending_migrations)} pending migrations...")
        
        for migration_file in pending_migrations:
            logger.info(f"Applying migration: {migration_file}")
            
            try:
                # Read migration file
                with open(os.path.join(migrations_dir, migration_file), "r", encoding="utf-8") as f:
                    migration_sql = f.read()
                
                # Apply migration in a transaction
                cursor.execute("BEGIN")
                cursor.execute(migration_sql)
                cursor.execute("INSERT INTO migrations (filename) VALUES (%s)", (migration_file,))
                cursor.execute("COMMIT")
                
                logger.info(f"✓ Successfully applied migration: {migration_file}")
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                logger.error(f"✗ Error applying migration {migration_file}: {e}")
                raise
        
        logger.info("All migrations applied successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    run_migrations() 