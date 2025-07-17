#!/usr/bin/env python3
"""
Script to fix sequence synchronization issues in production database.

This script connects to the production database and resets the sequences
to be in sync with the actual data in the tables.
"""

import os
import psycopg2
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_sequences():
    """Fix sequence synchronization issues."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        logger.info("Connected to database successfully")
        
        # Fix alert_history sequence
        logger.info("Fixing alert_history sequence...")
        cursor.execute("""
            SELECT setval('alert_history_id_seq', 
                         COALESCE((SELECT MAX(id) FROM alert_history), 1), 
                         true);
        """)
        new_seq_value = cursor.fetchone()[0]
        logger.info(f"Set alert_history_id_seq to {new_seq_value}")
        
        # Fix logs sequence if it exists
        logger.info("Checking and fixing logs sequence...")
        cursor.execute("""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'logs_id_seq') THEN
                    PERFORM setval('logs_id_seq', 
                                 COALESCE((SELECT MAX(id) FROM logs), 1), 
                                 true);
                END IF;
            END $$;
        """)
        
        # Verify sequences
        cursor.execute("SELECT last_value FROM alert_history_id_seq;")
        alert_seq = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(id) FROM alert_history;")
        alert_max = cursor.fetchone()[0] or 0
        
        logger.info(f"Alert history sequence: {alert_seq}, Max ID in table: {alert_max}")
        
        # Check if logs table exists and get info
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'logs'
            );
        """)
        logs_exists = cursor.fetchone()[0]
        
        if logs_exists:
            cursor.execute("SELECT COALESCE(MAX(id), 0) FROM logs;")
            logs_max = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_class WHERE relname = 'logs_id_seq'
                );
            """)
            logs_seq_exists = cursor.fetchone()[0]
            
            if logs_seq_exists:
                cursor.execute("SELECT last_value FROM logs_id_seq;")
                logs_seq = cursor.fetchone()[0]
                logger.info(f"Logs sequence: {logs_seq}, Max ID in table: {logs_max}")
            else:
                logger.info(f"Logs sequence doesn't exist, Max ID in table: {logs_max}")
        
        # Commit changes
        conn.commit()
        logger.info("Sequences fixed successfully!")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error fixing sequences: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = fix_sequences()
    if success:
        print("✅ Sequences fixed successfully!")
    else:
        print("❌ Failed to fix sequences!")
        exit(1)