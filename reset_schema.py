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
    cur.execute("DROP TABLE IF EXISTS user_data")
    cur.execute("DROP TABLE IF EXISTS users")
    cur.execute("DROP TABLE IF EXISTS garmin_credentials")
    cur.execute("DROP TABLE IF EXISTS background_jobs")
    cur.execute("DROP TABLE IF EXISTS hr_parameters")
    
    print("Creating new schema...")
    
    # Create users table
    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            role TEXT DEFAULT 'user',
            google_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create garmin_credentials table
    cur.execute("""
        CREATE TABLE garmin_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            password_encrypted TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create hr_parameters table
    cur.execute("""
        CREATE TABLE hr_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resting_hr INTEGER,
            max_hr INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create background_jobs table
    cur.execute("""
        CREATE TABLE background_jobs (
            job_id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            target_date TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'pending',
            result TEXT,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create daily_data table (new schema)
    cur.execute("""
        CREATE TABLE daily_data (
            date DATE PRIMARY KEY,
            heart_rate_series JSON,
            trimp_data JSON,
            total_trimp FLOAT,
            daily_score FLOAT,
            activity_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create activity_data table (new schema)
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
            breathing_rate_series JSON,
            trimp_data JSON,
            total_trimp FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (date) REFERENCES daily_data(date)
        )
    """)
    
    # Create user_data table for SpO2 and notes (separate from system data)
    cur.execute("""
        CREATE TABLE user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_type VARCHAR(50) NOT NULL,  -- 'activity_spo2', 'activity_notes', 'daily_notes'
            target_id VARCHAR(100) NOT NULL,  -- activity_id for activities, date for daily
            data_content JSON,                -- SpO2 series or text notes
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(data_type, target_id)
        )
    """)
    
    # Insert default HR parameters
    cur.execute("""
        INSERT INTO hr_parameters (id, resting_hr, max_hr)
        VALUES (1, 48, 167)
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("Schema reset completed!")
    print("Note: You'll need to re-enter your Garmin credentials.")

if __name__ == "__main__":
    reset_schema() 