#!/usr/bin/env python3
"""
Reset database to new schema - drop old tables and create new ones.
"""

from database import get_db_connection

def reset_schema():
    """Drop old tables and create new schema."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("Dropping old tables...")
    
    # Drop old tables
    cur.execute("DROP TABLE IF EXISTS heart_rate_data")
    cur.execute("DROP TABLE IF EXISTS activities")
    
    # Drop new tables if they exist (to start completely fresh)
    cur.execute("DROP TABLE IF EXISTS daily_data")
    cur.execute("DROP TABLE IF EXISTS activity_data")
    
    print("Creating new schema...")
    
    # Create new tables
    cur.execute("""
        CREATE TABLE daily_data (
            date DATE PRIMARY KEY,
            heart_rate_series JSON,
            trimp_data JSON,
            total_trimp FLOAT,
            daily_score FLOAT,
            activity_type VARCHAR(50),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE activity_data (
            activity_id VARCHAR(50) PRIMARY KEY,
            date DATE,
            activity_name VARCHAR(255),
            activity_type VARCHAR(50),
            start_time_local TIMESTAMP,
            duration_seconds INTEGER,
            distance_meters FLOAT NULL,
            elevation_gain FLOAT NULL,
            average_hr INTEGER NULL,
            max_hr INTEGER NULL,
            heart_rate_series JSON,
            trimp_data JSON,
            total_trimp FLOAT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (date) REFERENCES daily_data(date)
        )
    """)
    
    # Keep existing tables that we still need
    print("Keeping existing tables: users, garmin_credentials, background_jobs")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("Schema reset completed!")
    print("Note: You'll need to re-enter your Garmin credentials and HR parameters.")

if __name__ == "__main__":
    reset_schema() 