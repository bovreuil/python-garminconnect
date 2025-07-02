#!/usr/bin/env python3
"""
Garmin Heart Rate Analyzer with TRIMP Calculations
Uses SQLite for both local and production, with Google OAuth authentication
"""

import os
import json
import logging
import math
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import sqlite3
from rq import Queue
from redis import Redis
import garminconnect

# Import database functions
from database import (
    get_db_connection, 
    encrypt_password, 
    decrypt_password, 
    get_user_hr_parameters, 
    update_job_status
)

# Import job functions
from jobs import collect_garmin_data_job

# Import models
from models import HeartRateAnalyzer, TRIMPCalculator

# Load environment variables
load_dotenv('env.local')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Redis and RQ setup
redis_conn = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
queue = Queue(connection=redis_conn)

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_SECRET', '')
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

# Allowed users (restrict access to specific emails)
ALLOWED_USERS = {
    'peter.buckney@gmail.com': 'Peter Buckney'
    # Add more users here as needed
}

# OAuth setup
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url=GOOGLE_DISCOVERY_URL,
    client_kwargs={
        'scope': 'openid email profile',
    }
)

# Encryption key for passwords
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Users table (simplified for admin/viewer roles)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) UNIQUE,
            name VARCHAR(255),
            google_id VARCHAR(255) UNIQUE,
            role VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Garmin credentials (single set for the system)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS garmin_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) NOT NULL,
            password_encrypted TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Heart rate parameters (single set for the system)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hr_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resting_hr INTEGER DEFAULT 48,
            max_hr INTEGER DEFAULT 167,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Heart rate data (no user_id needed - single user system)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS heart_rate_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE,
            individual_hr_buckets TEXT,
            presentation_buckets TEXT,
            trimp_data TEXT,
            total_trimp REAL,
            daily_score REAL,
            activity_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Background jobs (no user_id needed - single user system)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS background_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id VARCHAR(255) UNIQUE,
            job_type VARCHAR(100),
            target_date DATE,
            start_date DATE,
            end_date DATE,
            status VARCHAR(50),
            result TEXT,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Ensure we have default HR parameters
    cur.execute("""
        INSERT OR IGNORE INTO hr_parameters (id, resting_hr, max_hr)
        VALUES (1, 48, 167)
    """)
    
    conn.commit()
    cur.close()
    conn.close()

def ensure_user_hr_parameters(resting_hr: int, max_hr: int):
    """Ensure user has HR parameters set in database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT OR REPLACE INTO hr_parameters (resting_hr, max_hr, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (resting_hr, max_hr))
    
    cur.close()
    conn.close()

def get_user_hr_parameters():
    """Get HR parameters for the system."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT resting_hr, max_hr FROM hr_parameters LIMIT 1")
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result:
        return result['resting_hr'], result['max_hr']
    return 48, 167  # Default values

def create_background_job(job_type: str, target_date: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """Create a background job record and return the job ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Generate a unique job ID
    job_id = f"{job_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    cur.execute("""
        INSERT INTO background_jobs (job_id, job_type, target_date, start_date, end_date, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (job_id, job_type, target_date, start_date, end_date))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return job_id

# Routes
@app.route('/')
def index():
    """Main dashboard page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', today=date.today().isoformat())

@app.route('/login')
def login():
    """Google OAuth login."""
    redirect_uri = url_for('auth_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    """Logout user."""
    session.clear()
    flash('You have been logged out from this application.', 'info')
    return render_template('logout.html')

@app.route('/logout-google')
def logout_google():
    """Complete logout by redirecting to Google's logout."""
    return redirect("https://accounts.google.com/logout")

@app.route('/auth/callback')
def auth_callback():
    """Handle OAuth callback from Google."""
    app.logger.info("auth_callback: Starting OAuth callback")
    
    try:
        token = oauth.google.authorize_access_token()
        app.logger.info("auth_callback: Got access token")
        
        # Get user info from Google's userinfo endpoint
        resp = oauth.google.get('https://www.googleapis.com/oauth2/v2/userinfo')
        userinfo = resp.json()
        app.logger.info(f"auth_callback: Got userinfo: {userinfo}")
        
        email = userinfo.get('email')
        name = userinfo.get('name', 'Unknown')
        google_id = userinfo.get('id')
        
        app.logger.info(f"auth_callback: User email: {email}, name: {name}, id: {google_id}")
        
        # Simplified user model - only two users
        if email == 'peter.buckney@gmail.com':
            user_role = 'admin'
            app.logger.info("auth_callback: User peter.buckney@gmail.com is authorized as admin")
        else:
            # For now, allow any other user as viewer (you can restrict this later)
            user_role = 'viewer'
            app.logger.info(f"auth_callback: User {email} is authorized as viewer")
        
        # Insert or update user in database
        conn = get_db_connection()
        cur = conn.cursor()
        
        app.logger.info("auth_callback: Inserting user into database")
        cur.execute("""
            INSERT OR REPLACE INTO users (email, name, google_id, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (email, name, google_id, user_role))
        
        conn.commit()
        app.logger.info("auth_callback: User inserted/updated in database")
        
        # Get the user ID
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user:
            app.logger.info(f"auth_callback: Found user in database with id: {user['id']}")
            session['user_id'] = user['id']
            session['user_email'] = email
            session['user_name'] = name
            session['user_role'] = user_role
            app.logger.info(f"auth_callback: Session set - user_id: {user['id']}, email: {email}, role: {user_role}")
        else:
            app.logger.error("auth_callback: Failed to retrieve user from database")
            flash('Authentication failed', 'error')
            return redirect(url_for('login'))
        
        app.logger.info("auth_callback: Redirecting to index")
        return redirect(url_for('index'))
        
    except Exception as e:
        app.logger.error(f"auth_callback: Error during OAuth callback: {str(e)}")
        flash('Authentication failed', 'error')
        return redirect(url_for('login'))

@app.route('/setup-garmin', methods=['GET', 'POST'])
def setup_garmin():
    """Setup Garmin credentials."""
    if 'user_id' not in session:
        logger.warning("setup_garmin: No user_id in session")
        return redirect(url_for('login'))
    
    logger.info(f"setup_garmin: User {session['user_id']} accessing setup page")
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        logger.info(f"setup_garmin: Saving credentials for user {session['user_id']}, email: {email}")
        
        # Store credentials
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            encrypted_password = encrypt_password(password)
            logger.info(f"setup_garmin: Password encrypted successfully")
            
            cur.execute("""
                INSERT OR REPLACE INTO garmin_credentials (email, password_encrypted, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (email, encrypted_password))
            
            conn.commit()
            logger.info(f"setup_garmin: Credentials saved to database successfully")
            
            # Verify the save worked
            cur.execute("SELECT * FROM garmin_credentials WHERE email = ?", (email,))
            saved_creds = cur.fetchone()
            if saved_creds:
                logger.info(f"setup_garmin: Verified credentials saved - email: {saved_creds['email']}")
            else:
                logger.error(f"setup_garmin: Credentials not found after save!")
            
        except Exception as e:
            logger.error(f"setup_garmin: Error saving credentials: {str(e)}")
            flash(f'Error saving credentials: {str(e)}', 'error')
            cur.close()
            conn.close()
            return redirect(url_for('setup_garmin'))
        
        cur.close()
        conn.close()
        
        flash('Garmin credentials saved successfully!', 'success')
        logger.info(f"setup_garmin: Redirecting to dashboard")
        return redirect(url_for('index'))
    
    return render_template('setup_garmin.html')

@app.route('/collect-data', methods=['POST'])
def collect_data():
    """Start a background job to collect Garmin data."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Only admin can collect data
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    target_date = request.form.get('date', date.today().isoformat())
    
    # Create background job
    job_id = create_background_job('collect_data', target_date=target_date)
    
    # Queue the job
    job = queue.enqueue(collect_garmin_data_job, target_date, job_id)
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'message': f'Data collection job started for {target_date}',
        'status': 'pending'
    })

@app.route('/api/data/<date>')
def get_data(date):
    """Get heart rate data for a specific date."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM heart_rate_data 
        WHERE date = ?
    """, (date,))
    
    data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not data:
        return jsonify({'error': 'No data found for this date'}), 404
    
    return jsonify({
        'date': data['date'],
        'individual_hr_buckets': json.loads(data['individual_hr_buckets']),
        'presentation_buckets': json.loads(data['presentation_buckets']),
        'trimp_data': json.loads(data['trimp_data']),
        'total_trimp': data['total_trimp'],
        'daily_score': data['daily_score'],
        'activity_type': data['activity_type']
    })

@app.route('/api/weekly-data/<start_date>')
def get_weekly_data(start_date):
    """Get heart rate data for a week starting from start_date."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = start + timedelta(days=6)
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT date, presentation_buckets, total_trimp, daily_score, activity_type
        FROM heart_rate_data 
        WHERE date >= ? AND date <= ?
        ORDER BY date
    """, (start, end))
    
    data = cur.fetchall()
    cur.close()
    conn.close()
    
    # Convert to list of dicts
    weekly_data = []
    for row in data:
        weekly_data.append({
            'date': row['date'],
            'presentation_buckets': json.loads(row['presentation_buckets']),
            'total_trimp': row['total_trimp'],
            'daily_score': row['daily_score'],
            'activity_type': row['activity_type']
        })
    
    return jsonify(weekly_data)

@app.route('/api/hr-parameters', methods=['GET', 'POST'])
def hr_parameters():
    """Get or update HR parameters."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Only admin can update parameters
    if request.method == 'POST' and session.get('user_role') != 'admin':
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    if request.method == 'POST':
        data = request.get_json()
        resting_hr = data.get('resting_hr', 48)
        max_hr = data.get('max_hr', 167)
        
        ensure_user_hr_parameters(resting_hr, max_hr)
        return jsonify({'success': True, 'resting_hr': resting_hr, 'max_hr': max_hr})
    
    else:  # GET
        resting_hr, max_hr = get_user_hr_parameters()
        return jsonify({'resting_hr': resting_hr, 'max_hr': max_hr})

@app.route('/setup-hr-parameters', methods=['GET', 'POST'])
def setup_hr_parameters():
    """Setup page for HR parameters."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Only admin can update parameters
    if request.method == 'POST' and session.get('user_role') != 'admin':
        flash('Only admin can update HR parameters', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        resting_hr = int(request.form.get('resting_hr', 48))
        max_hr = int(request.form.get('max_hr', 167))
        
        ensure_user_hr_parameters(resting_hr, max_hr)
        flash('HR parameters updated successfully!', 'success')
        return redirect(url_for('index'))
    
    # GET request - show current values
    resting_hr, max_hr = get_user_hr_parameters()
    return render_template('setup_hr_parameters.html', resting_hr=resting_hr, max_hr=max_hr)

@app.route('/api/jobs')
def get_jobs():
    """Get background jobs."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT job_id, job_type, status, target_date, start_date, end_date, 
               result, error_message, created_at, updated_at
        FROM background_jobs 
        ORDER BY created_at DESC
        LIMIT 20
    """)
    
    jobs = []
    for row in cur.fetchall():
        job = {
            'job_id': row['job_id'],
            'job_type': row['job_type'],
            'status': row['status'],
            'target_date': row['target_date'],
            'start_date': row['start_date'],
            'end_date': row['end_date'],
            'result': json.loads(row['result']) if row['result'] else None,
            'error_message': row['error_message'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }
        jobs.append(job)
    
    cur.close()
    conn.close()
    
    return jsonify(jobs)

@app.route('/api/jobs/<job_id>')
def get_job_status(job_id):
    """Get status of a specific job."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT job_id, job_type, status, target_date, start_date, end_date, 
               result, error_message, created_at, updated_at
        FROM background_jobs 
        WHERE job_id = ?
    """, (job_id,))
    
    job = cur.fetchone()
    cur.close()
    conn.close()
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({
        'job_id': job['job_id'],
        'job_type': job['job_type'],
        'status': job['status'],
        'target_date': job['target_date'],
        'start_date': job['start_date'],
        'end_date': job['end_date'],
        'result': json.loads(job['result']) if job['result'] else None,
        'error_message': job['error_message'],
        'created_at': job['created_at'],
        'updated_at': job['updated_at']
    })

if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5001) 