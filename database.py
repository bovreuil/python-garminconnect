#!/usr/bin/env python3
"""
Database utilities for Garmin Heart Rate Analyzer
"""

import sqlite3
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('env.local')

# Encryption key for passwords
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

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
        return result['resting_hr'], result['max_hr']
    else:
        # Default values for Pete
        return 48, 167 