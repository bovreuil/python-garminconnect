#!/usr/bin/env python3
"""
Migration script to add breathing_rate_series column to activity_data table.
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_breathing_rate_column():
    """Add breathing_rate_series column to activity_data table if it doesn't exist."""
    conn = sqlite3.connect('garmin_hr.db')
    cur = conn.cursor()
    
    try:
        # Check if column already exists
        cur.execute("PRAGMA table_info(activity_data)")
        columns = [column[1] for column in cur.fetchall()]
        
        if 'breathing_rate_series' not in columns:
            logger.info("Adding breathing_rate_series column to activity_data table")
            cur.execute("ALTER TABLE activity_data ADD COLUMN breathing_rate_series JSON")
            conn.commit()
            logger.info("Successfully added breathing_rate_series column")
        else:
            logger.info("breathing_rate_series column already exists")
            
    except Exception as e:
        logger.error(f"Error adding breathing_rate_series column: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_breathing_rate_column() 