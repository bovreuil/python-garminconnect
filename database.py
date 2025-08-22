#!/usr/bin/env python3
"""
Database utilities for Garmin Heart Rate Analyzer
"""

import sqlite3
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
import logging
import json

# Load environment variables
load_dotenv('env.local')

# Encryption key for passwords
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if ENCRYPTION_KEY:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
else:
    cipher_suite = Fernet(Fernet.generate_key())

logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a SQLite database connection."""
    conn = sqlite3.connect('garmin_hr.db')
    conn.row_factory = sqlite3.Row
    return conn

def encrypt_password(password: str) -> str:
    """Encrypt a password using Fernet."""
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a password using Fernet."""
    return cipher_suite.decrypt(encrypted_password.encode()).decode()

def update_job_status(job_id: str, status: str, result: str = None, error_message: str = None):
    """Update the status of a background job."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE background_jobs 
        SET status = ?, result = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
        WHERE job_id = ?
    """, (status, result, error_message, job_id))
    
    conn.commit()
    cur.close()
    conn.close()

def get_user_hr_parameters():
    """Get system HR parameters (resting_hr, max_hr)."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT resting_hr, max_hr FROM hr_parameters LIMIT 1")
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result:
        logger.info(f"get_user_hr_parameters: Found HR parameters - resting: {result['resting_hr']}, max: {result['max_hr']}")
        return result['resting_hr'], result['max_hr']
    else:
        logger.warning(f"get_user_hr_parameters: No HR parameters found in database, using defaults")
        # Default values for Pete
        return 48, 167

def get_user_data(data_type: str, target_id: str):
    """
    Get user-entered data (SpO2 or notes) for a specific target.
    
    Args:
        data_type: 'activity_spo2', 'activity_notes', or 'daily_notes'
        target_id: activity_id for activities, date for daily
        
    Returns:
        The data content or None if not found
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT data_content
        FROM user_data 
        WHERE data_type = ? AND target_id = ?
    """, (data_type, target_id))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result and result['data_content']:
        return json.loads(result['data_content'])
    return None

def save_user_data(data_type: str, target_id: str, data_content):
    """
    Save user-entered data (SpO2 or notes) for a specific target.
    
    Args:
        data_type: 'activity_spo2', 'activity_notes', or 'daily_notes'
        target_id: activity_id for activities, date for daily
        data_content: The data to save (will be JSON serialized)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Convert to JSON string
    json_content = json.dumps(data_content) if data_content else None
    
    cur.execute("""
        INSERT OR REPLACE INTO user_data (data_type, target_id, data_content, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (data_type, target_id, json_content))
    
    conn.commit()
    cur.close()
    conn.close()

def delete_user_data(data_type: str, target_id: str):
    """
    Delete user-entered data for a specific target.
    
    Args:
        data_type: 'activity_spo2', 'activity_notes', or 'daily_notes'
        target_id: activity_id for activities, date for daily
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        DELETE FROM user_data 
        WHERE data_type = ? AND target_id = ?
    """, (data_type, target_id))
    
    conn.commit()
    cur.close()
    conn.close()

def init_database():
    """Initialize the database with all required tables."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create garmin_credentials table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS garmin_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            password_encrypted TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create background_jobs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS background_jobs (
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
        CREATE TABLE IF NOT EXISTS daily_data (
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
        CREATE TABLE IF NOT EXISTS activity_data (
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
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_type VARCHAR(50) NOT NULL,  -- 'activity_spo2', 'activity_notes', 'daily_notes'
            target_id VARCHAR(100) NOT NULL,  -- activity_id for activities, date for daily
            data_content JSON,                -- SpO2 series or text notes
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(data_type, target_id)
        )
    """)
    
    # Create legacy tables for migration (if they don't exist)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS heart_rate_data (
            date DATE PRIMARY KEY,
            heart_rate_values JSON,
            presentation_buckets JSON,
            total_trimp FLOAT,
            daily_score FLOAT,
            activity_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            activity_id VARCHAR(50) PRIMARY KEY,
            date DATE,
            activity_name VARCHAR(255),
            activity_type VARCHAR(50),
            start_time_local TIMESTAMP,
            duration_seconds INTEGER,
            distance_meters FLOAT,
            elevation_gain FLOAT,
            average_hr INTEGER,
            max_hr INTEGER,
            individual_hr_buckets JSON,
            presentation_buckets JSON,
            trimp_data JSON,
            total_trimp FLOAT,
            raw_activity_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create O2Ring data tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS o2ring_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename VARCHAR(255) NOT NULL,
            first_timestamp BIGINT NOT NULL,  -- Unix timestamp in milliseconds
            last_timestamp BIGINT NOT NULL,   -- Unix timestamp in milliseconds
            row_count INTEGER NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS o2ring_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            timestamp BIGINT NOT NULL,        -- Unix timestamp in milliseconds
            spo2_value INTEGER NOT NULL,      -- 0-100
            heart_rate INTEGER NOT NULL,      -- BPM
            motion_warnings INTEGER NOT NULL, -- Number of low SpO2 warnings
            hr_warnings INTEGER NOT NULL,     -- Number of HR range warnings
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES o2ring_files(id) ON DELETE CASCADE
        )
    """)
    
    # Create index for efficient timestamp queries
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_o2ring_data_timestamp 
        ON o2ring_data(timestamp)
    """)
    
    # Create index for file-based queries
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_o2ring_data_file_id 
        ON o2ring_data(file_id)
    """)
    
    conn.commit()
    cur.close()
    conn.close() 