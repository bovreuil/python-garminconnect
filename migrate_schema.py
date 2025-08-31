#!/usr/bin/env python3
"""
Migration script to add caching columns to existing tables.
"""

import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a SQLite database connection."""
    conn = sqlite3.connect('garmin_hr.db')
    conn.row_factory = sqlite3.Row
    return conn

def check_column_exists(conn, table_name, column_name):
    """Check if a column exists in a table."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = cur.fetchall()
    
    for column in columns:
        if column['name'] == column_name:
            return True
    return False

def migrate_database():
    """Migrate the database to add caching columns."""
    logger.info("Starting database migration...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check and add columns to daily_data table
        logger.info("Checking daily_data table...")
        
        if not check_column_exists(conn, 'daily_data', 'cached_trimp_data'):
            logger.info("Adding cached_trimp_data column to daily_data table")
            cur.execute("ALTER TABLE daily_data ADD COLUMN cached_trimp_data JSON")
        else:
            logger.info("cached_trimp_data column already exists in daily_data table")
        
        if not check_column_exists(conn, 'daily_data', 'trimp_calculation_hash'):
            logger.info("Adding trimp_calculation_hash column to daily_data table")
            cur.execute("ALTER TABLE daily_data ADD COLUMN trimp_calculation_hash VARCHAR(64)")
        else:
            logger.info("trimp_calculation_hash column already exists in daily_data table")
        
        # Check and add columns to activity_data table
        logger.info("Checking activity_data table...")
        
        if not check_column_exists(conn, 'activity_data', 'cached_trimp_data'):
            logger.info("Adding cached_trimp_data column to activity_data table")
            cur.execute("ALTER TABLE activity_data ADD COLUMN cached_trimp_data JSON")
        else:
            logger.info("cached_trimp_data column already exists in activity_data table")
        
        if not check_column_exists(conn, 'activity_data', 'trimp_calculation_hash'):
            logger.info("Adding trimp_calculation_hash column to activity_data table")
            cur.execute("ALTER TABLE activity_data ADD COLUMN trimp_calculation_hash VARCHAR(64)")
        else:
            logger.info("trimp_calculation_hash column already exists in activity_data table")
        
        # Commit changes
        conn.commit()
        logger.info("Migration completed successfully!")
        
        # Verify the changes
        logger.info("Verifying migration...")
        
        # Check daily_data columns
        cur.execute("PRAGMA table_info(daily_data)")
        daily_columns = [col['name'] for col in cur.fetchall()]
        logger.info(f"daily_data columns: {daily_columns}")
        
        # Check activity_data columns
        cur.execute("PRAGMA table_info(activity_data)")
        activity_columns = [col['name'] for col in cur.fetchall()]
        logger.info(f"activity_data columns: {activity_columns}")
        
        # Check data counts
        cur.execute("SELECT COUNT(*) FROM daily_data")
        daily_count = cur.fetchone()[0]
        logger.info(f"daily_data records: {daily_count}")
        
        cur.execute("SELECT COUNT(*) FROM activity_data")
        activity_count = cur.fetchone()[0]
        logger.info(f"activity_data records: {activity_count}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    migrate_database()
