#!/usr/bin/env python3
"""
Garmin Heart Rate Analyzer with TRIMP Calculations
Uses SQLite for both local and production, with Google OAuth authentication
"""

import os
import json
import logging
import math
import threading
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import sqlite3
import garminconnect
import random
import time

# Import database functions
from database import (
    get_db_connection, 
    encrypt_password, 
    decrypt_password, 
    get_user_hr_parameters, 
    update_job_status,
    get_user_data,
    save_user_data,
    delete_user_data
)

# Import job functions
from jobs import collect_garmin_data_job

# Import models
from models import HeartRateAnalyzer, TRIMPCalculator

# Import configuration
from config import SERVER_CONFIG, API_CONFIG

# Load environment variables
load_dotenv('env.local')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

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
            resting_hr INTEGER,
            max_hr INTEGER,
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
            raw_hr_data TEXT,
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
    
    # Ensure we have default HR parameters (only if none exist)
    cur.execute("SELECT COUNT(*) FROM hr_parameters")
    count = cur.fetchone()[0]
    if count == 0:
        cur.execute("""
            INSERT INTO hr_parameters (id, resting_hr, max_hr)
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



def create_background_job(job_type: str, target_date: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """Create a background job record and return the job ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Generate a unique job ID with microseconds and random component
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
    random_suffix = random.randint(1000, API_CONFIG['MAX_ACTIVITIES_LIMIT'])
    job_id = f"{job_type}_{timestamp}_{random_suffix}"
    
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
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/<date>')
def date_view(date):
    """Route for specific date navigation."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return redirect(url_for('index'))
    
    return render_template('dashboard.html', initial_date=date)

@app.route('/<date>/<activity_id>')
def activity_view(date, activity_id):
    """Route for specific activity navigation."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return redirect(url_for('index'))
    
    return render_template('dashboard.html', initial_date=date, initial_activity_id=activity_id)

@app.route('/<period>/<date>')
def period_date_view(period, date):
    """Route for specific two-week period and date navigation."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Validate period format (YYYY-MM-DD-YYYY-MM-DD)
    try:
        start_date, end_date = period.split('-', 4)[:4], period.split('-', 4)[4:]
        start_str = '-'.join(start_date)
        end_str = '-'.join(end_date)
        datetime.strptime(start_str, '%Y-%m-%d')
        datetime.strptime(end_str, '%Y-%m-%d')
        datetime.strptime(date, '%Y-%m-%d')
    except (ValueError, IndexError):
        return redirect(url_for('index'))
    
    return render_template('dashboard.html', initial_period=period, initial_date=date)

@app.route('/<period>/<date>/<activity_id>')
def period_activity_view(period, date, activity_id):
    """Route for specific two-week period, date, and activity navigation."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Validate period format (YYYY-MM-DD-YYYY-MM-DD)
    try:
        start_date, end_date = period.split('-', 4)[:4], period.split('-', 4)[4:]
        start_str = '-'.join(start_date)
        end_str = '-'.join(end_date)
        datetime.strptime(start_str, '%Y-%m-%d')
        datetime.strptime(end_str, '%Y-%m-%d')
        datetime.strptime(date, '%Y-%m-%d')
    except (ValueError, IndexError):
        return redirect(url_for('index'))
    
    return render_template('dashboard.html', initial_period=period, initial_date=date, initial_activity_id=activity_id)

@app.route('/login')
def login():
    """Google OAuth login."""
    redirect_uri = url_for('auth_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    """Logout user."""
    session.clear()
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
            return redirect(url_for('login'))
        
        app.logger.info("auth_callback: Redirecting to index")
        return redirect(url_for('index'))
        
    except Exception as e:
        app.logger.error(f"auth_callback: Error during OAuth callback: {str(e)}")
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
        logger.info(f"setup_garmin: Redirecting to admin page")
        return redirect(url_for('admin'))
    
    return render_template('setup_garmin.html')

@app.route('/admin')
def admin():
    """Admin panel page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Only admin can access
    if session.get('user_role') != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    return render_template('admin.html', today=date.today().isoformat())

@app.route('/collect-data', methods=['POST'])
def collect_data():
    """Start a background job to collect Garmin data."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Only admin can collect data
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    start_date = request.form.get('start_date', date.today().isoformat())
    end_date = request.form.get('end_date', start_date)
    
    logger.info(f"collect_data: start_date={start_date}, end_date={end_date}")
    
    # Determine if this is single date or range based on dates
    if start_date == end_date:
        # Single date - create one job
        job_id = create_background_job('collect_data', target_date=start_date)
        # Run the job in a separate thread
        thread = threading.Thread(target=collect_garmin_data_job, args=(start_date, job_id), daemon=True)
        thread.start()
        
        logger.info(f"collect_data: Created single job {job_id} for {start_date}")
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': f'Data collection job started for {start_date}',
            'status': 'pending'
        })
    else:
        # Date range - create parallel jobs for each date
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            logger.info(f"collect_data: Processing date range from {start} to {end}")
            
            if (end - start).days > 30:  # Limit to 30 days
                return jsonify({'error': f'Date range too large. Maximum {API_CONFIG["MAX_DATE_RANGE_DAYS"]} days allowed.'}), 400
            
            job_ids = []
            current_date = start
            job_count = 0
            
            while current_date <= end:
                job_id = create_background_job('collect_data', target_date=current_date.isoformat())
                # Run the job in a separate thread
                thread = threading.Thread(target=collect_garmin_data_job, args=(current_date.isoformat(), job_id), daemon=True)
                thread.start()
                job_ids.append(job_id)
                logger.info(f"collect_data: Created job {job_id} for {current_date.isoformat()}")
                current_date += timedelta(days=1)
                job_count += 1
                
                # Add a small delay between job creation to prevent rate limiting
                if job_count % 3 == 0:  # Every 3 jobs
                    time.sleep(0.5)  # 500ms delay between jobs
            
            logger.info(f"collect_data: Created {len(job_ids)} jobs total")
            
            return jsonify({
                'success': True,
                'job_ids': job_ids,
                'message': f'Started {len(job_ids)} data collection jobs from {start_date} to {end_date}',
                'status': 'pending'
            })
            
        except ValueError as e:
            logger.error(f"collect_data: ValueError: {e}")
            return jsonify({'error': 'Invalid date format'}), 400

@app.route('/api/data/<date>')
def get_data(date):
    """Get heart rate data for a specific date label."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Treat date as a string label, not a real date
    # Validate format: YYYY-MM-DD
    if not (len(date) == 10 and date[4] == '-' and date[7] == '-'):
        return jsonify({'error': 'Invalid date label format. Expected YYYY-MM-DD'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get data from new daily_data table using date as string
    cur.execute("""
        SELECT heart_rate_series, trimp_data, total_trimp, daily_score, activity_type
        FROM daily_data 
        WHERE date = ?
    """, (date,))
    
    data = cur.fetchone()
    cur.close()
    conn.close()
    
    if data:
        # Convert from new schema format
        heart_rate_series = json.loads(data['heart_rate_series']) if data['heart_rate_series'] else []
        trimp_data = json.loads(data['trimp_data']) if data['trimp_data'] else {}
        
        # Debug logging
        print(f"API DEBUG: trimp_data keys: {list(trimp_data.keys())}")
        print(f"API DEBUG: trimp_data has presentation_buckets: {'presentation_buckets' in trimp_data}")
        
        return jsonify({
            'date': date,
            'heart_rate_values': heart_rate_series,
            'presentation_buckets': trimp_data.get('presentation_buckets', {}),
            'total_trimp': data['total_trimp'],
            'daily_score': data['daily_score'],
            'activity_type': data['activity_type']
        })
    else:
        # Check if there are TRIMP overrides for this date (even without daily data)
        trimp_overrides = get_user_data('daily_trimp_overrides', date)
        if trimp_overrides:
            # Parse the TRIMP overrides
            try:
                overrides_data = json.loads(trimp_overrides)
                # Calculate total TRIMP from overrides
                total_trimp = sum(float(value) for value in overrides_data.values() if value is not None and value != '')
                
                return jsonify({
                    'date': date,
                    'heart_rate_values': [],  # No HR data
                    'presentation_buckets': overrides_data,
                    'total_trimp': total_trimp,
                    'daily_score': None,
                    'activity_type': None
                })
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing TRIMP overrides for {date}: {e}")
                return jsonify({'error': 'No data found for this date'}), 404
        else:
            return jsonify({'error': 'No data found for this date'}), 404

@app.route('/api/activities/<date>')
def get_activities(date):
    """Get activities for a specific date label."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Treat date as a string label, not a real date
    # Validate format: YYYY-MM-DD
    if not (len(date) == 10 and date[4] == '-' and date[7] == '-'):
        return jsonify({'error': 'Invalid date label format. Expected YYYY-MM-DD'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get activities from new activity_data table using date as string
    cur.execute("""
        SELECT activity_id, activity_name, activity_type, start_time_local, duration_seconds,
               distance_meters, elevation_gain, average_hr, max_hr, heart_rate_series, 
               breathing_rate_series, trimp_data, total_trimp
        FROM activity_data 
        WHERE date = ?
        ORDER BY start_time_local
    """, (date,))
    
    activities = cur.fetchall()
    cur.close()
    conn.close()
    
    activities_list = []
    for activity in activities:
        # Convert from new schema format
        heart_rate_series = json.loads(activity['heart_rate_series']) if activity['heart_rate_series'] else []
        breathing_rate_series = json.loads(activity['breathing_rate_series']) if activity['breathing_rate_series'] else []
        trimp_data = json.loads(activity['trimp_data']) if activity['trimp_data'] else {}
        
        # Check for CSV override
        csv_override = get_user_data('activity_hr_csv', activity['activity_id'])
        if csv_override:
            # Use CSV override data instead of original HR series
            heart_rate_series = csv_override
        
        # Get user data (SpO2 and notes) from user_data table
        spo2_series = get_user_data('activity_spo2', activity['activity_id'])
        activity_notes = get_user_data('activity_notes', activity['activity_id'])
        
        activities_list.append({
            'activity_id': activity['activity_id'],
            'activity_name': activity['activity_name'],
            'activity_type': activity['activity_type'],
            'start_time_local': activity['start_time_local'],
            'duration_seconds': activity['duration_seconds'],
            'distance_meters': activity['distance_meters'],
            'elevation_gain': activity['elevation_gain'],
            'average_hr': activity['average_hr'],
            'max_hr': activity['max_hr'],
            'individual_hr_buckets': trimp_data.get('individual_hr_buckets', {}),
            'presentation_buckets': trimp_data.get('presentation_buckets', {}),
            'trimp_data': trimp_data,
            'total_trimp': activity['total_trimp'],
            'heart_rate_values': heart_rate_series,
            'breathing_rate_values': breathing_rate_series,
            'spo2_values': spo2_series or []
        })
    
    return jsonify(activities_list)


@app.route('/api/activity/<activity_id>/spo2', methods=['POST'])
def save_activity_spo2(activity_id):
    """Save SpO2 data for a specific activity."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        spo2_entries = data.get('spo2_entries', [])
        
        # Validate SpO2 entries
        for entry in spo2_entries:
            if not isinstance(entry, dict) or 'time_offset' not in entry or 'spo2_value' not in entry:
                return jsonify({'error': 'Invalid SpO2 entry format'}), 400
            
            # Validate time offset format (MM:SS)
            time_offset = entry['time_offset']
            if not isinstance(time_offset, str) or ':' not in time_offset:
                return jsonify({'error': 'Time offset must be in MM:SS format'}), 400
            
            # Validate SpO2 value
            spo2_value = entry['spo2_value']
            if not isinstance(spo2_value, int) or spo2_value < 0 or spo2_value > 100:
                return jsonify({'error': 'SpO2 value must be an integer between 0 and 100'}), 400
        
        # Check if activity exists
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT heart_rate_series FROM activity_data WHERE activity_id = ?", (activity_id,))
        activity = cur.fetchone()
        cur.close()
        conn.close()
        
        if not activity:
            return jsonify({'error': 'Activity not found'}), 404
        
        # Get first HR timestamp to calculate base timestamp
        heart_rate_series = json.loads(activity['heart_rate_series']) if activity['heart_rate_series'] else []
        if not heart_rate_series:
            return jsonify({'error': 'Activity has no HR data to calculate timestamps'}), 400
        
        # Get first HR timestamp
        first_hr_timestamp = heart_rate_series[0][0] if heart_rate_series and len(heart_rate_series) > 0 else None
        if not first_hr_timestamp:
            return jsonify({'error': 'Cannot determine base timestamp from HR data'}), 400
        
        # Convert SpO2 entries to timestamp series
        spo2_series = []
        for entry in spo2_entries:
            time_offset = entry['time_offset']
            spo2_value = entry['spo2_value']
            
            # Parse time offset (MM:SS format)
            minutes, seconds = map(int, time_offset.split(':'))
            offset_seconds = minutes * 60 + seconds
            
            # Calculate timestamp by adding offset to first HR timestamp
            spo2_timestamp = first_hr_timestamp + (offset_seconds * 1000)  # Convert to milliseconds
            
            spo2_series.append([spo2_timestamp, spo2_value])
        
        # Save SpO2 series to user_data table
        if spo2_series:
            save_user_data('activity_spo2', activity_id, spo2_series)
        else:
            # Delete existing SpO2 data if empty
            delete_user_data('activity_spo2', activity_id)
        
        return jsonify({
            'success': True,
            'message': f'Saved {len(spo2_series)} SpO2 entries for activity {activity_id}',
            'spo2_series': spo2_series
        })
        
    except Exception as e:
        logger.error(f"Error saving SpO2 data for activity {activity_id}: {e}")
        return jsonify({'error': f'Error saving SpO2 data: {str(e)}'}), 500


@app.route('/api/activity/<activity_id>/hr-csv')
def download_activity_hr_csv(activity_id):
    """Download HR data for a specific activity as CSV."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get activity HR data
    cur.execute("""
        SELECT activity_name, heart_rate_series
        FROM activity_data 
        WHERE activity_id = ?
    """, (activity_id,))
    
    activity = cur.fetchone()
    cur.close()
    conn.close()
    
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404
    
    heart_rate_series = json.loads(activity['heart_rate_series']) if activity['heart_rate_series'] else []
    
    if not heart_rate_series:
        return jsonify({'error': 'No HR data available for this activity'}), 404
    
    # Create CSV content
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'hr'])  # Header
    
    for entry in heart_rate_series:
        if entry and len(entry) >= 2:
            timestamp = entry[0]
            hr = entry[1]
            writer.writerow([timestamp, hr])
    
    output.seek(0)
    
    # Create response with CSV content
    from flask import Response
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=activity_{activity_id}_hr_data.csv'}
    )
    
    return response

@app.route('/api/activity/<activity_id>/hr-csv-upload', methods=['POST'])
def upload_activity_hr_csv(activity_id):
    """Upload HR CSV data for a specific activity."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    logger.info(f"CSV upload request for activity {activity_id}")
    
    # Check if file was uploaded
    if 'file' not in request.files:
        logger.error("No file in request.files")
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({'error': 'No file selected'}), 400
    
    logger.info(f"Processing file: {file.filename}")
    
    # Validate file extension
    if not file.filename.lower().endswith('.csv'):
        logger.error(f"Invalid file extension: {file.filename}")
        return jsonify({'error': 'File must be a CSV'}), 400
    
    try:
        # Read and parse CSV
        import io
        import csv
        
        # Read file content
        content = file.read().decode('utf-8')
        logger.info(f"CSV content length: {len(content)} characters")
        logger.info(f"First 200 chars of CSV: {content[:200]}")
        
        csv_file = io.StringIO(content)
        reader = csv.reader(csv_file)
        
        # Parse CSV data
        hr_series = []
        header_skipped = False
        row_count = 0
        valid_rows = 0
        
        for row in reader:
            row_count += 1
            logger.info(f"Processing row {row_count}: {row}")
            
            if not header_skipped:
                # Skip header row
                header_skipped = True
                logger.info("Skipping header row")
                continue
            
            if len(row) >= 2:
                try:
                    timestamp = float(row[0])
                    hr = int(row[1])
                    hr_series.append([timestamp, hr])
                    valid_rows += 1
                    logger.info(f"Valid row: timestamp={timestamp}, hr={hr}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid row {row_count}: {row}, error: {e}")
                    continue  # Skip invalid rows
            else:
                logger.warning(f"Row {row_count} has insufficient columns: {row}")
        
        logger.info(f"CSV processing complete: {row_count} total rows, {valid_rows} valid rows, {len(hr_series)} HR points")
        
        if not hr_series:
            logger.error("No valid HR data found in CSV")
            return jsonify({'error': 'No valid HR data found in CSV'}), 400
        
        # Sort by timestamp
        hr_series.sort(key=lambda x: x[0])
        logger.info(f"Sorted HR series: {len(hr_series)} points, first: {hr_series[0] if hr_series else 'None'}, last: {hr_series[-1] if hr_series else 'None'}")
        
        # Save to user_data table
        from database import save_user_data
        logger.info(f"Saving CSV override to database for activity {activity_id}")
        save_user_data('activity_hr_csv', activity_id, hr_series)
        
        # Recalculate TRIMP and update activity data
        logger.info(f"Recalculating TRIMP for activity {activity_id}")
        recalculate_activity_trimp(activity_id, hr_series)
        
        logger.info(f"CSV upload successful for activity {activity_id}")
        return jsonify({'success': True, 'message': 'CSV uploaded successfully'})
        
    except Exception as e:
        logger.error(f"Error processing CSV for activity {activity_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error processing CSV: {str(e)}'}), 500

@app.route('/api/activity/<activity_id>/hr-csv-clear', methods=['POST'])
def clear_activity_hr_csv(activity_id):
    """Clear uploaded HR CSV data for a specific activity."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Delete from user_data table
        from database import delete_user_data
        delete_user_data('activity_hr_csv', activity_id)
        
        # Recalculate TRIMP using original activity data
        recalculate_activity_trimp(activity_id, None)
        
        return jsonify({'success': True, 'message': 'CSV data cleared successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Error clearing CSV data: {str(e)}'}), 500

@app.route('/api/activity/<activity_id>/hr-csv-status')
def get_activity_hr_csv_status(activity_id):
    """Check if activity has uploaded CSV data."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from database import get_user_data
    csv_data = get_user_data('activity_hr_csv', activity_id)
    
    return jsonify({
        'success': True,
        'has_csv_override': csv_data is not None
    })

def recalculate_activity_trimp(activity_id, hr_series_override=None):
    """Recalculate TRIMP for an activity using either override or original data."""
    logger.info(f"Recalculating TRIMP for activity {activity_id}, override provided: {hr_series_override is not None}")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get activity data
    cur.execute("""
        SELECT activity_name, heart_rate_series, breathing_rate_series, start_time_local, duration_seconds
        FROM activity_data 
        WHERE activity_id = ?
    """, (activity_id,))
    
    activity = cur.fetchone()
    if not activity:
        logger.error(f"Activity {activity_id} not found in database")
        cur.close()
        conn.close()
        return
    
    logger.info(f"Found activity: {activity['activity_name']}")
    
    # Use override data if provided, otherwise use original
    if hr_series_override is not None:
        hr_series = hr_series_override
        logger.info(f"Using override HR series: {len(hr_series)} points")
    else:
        hr_series = json.loads(activity['heart_rate_series']) if activity['heart_rate_series'] else []
        logger.info(f"Using original HR series: {len(hr_series)} points")
    
    breathing_series = json.loads(activity['breathing_rate_series']) if activity['breathing_rate_series'] else []
    logger.info(f"Breathing series: {len(breathing_series)} points")
    
    # Calculate TRIMP using the same logic as in jobs.py
    from jobs import calculate_trimp_from_timeseries
    
    logger.info(f"Calculating TRIMP for {len(hr_series)} HR points")
    trimp_results = calculate_trimp_from_timeseries(hr_series)
    logger.info(f"TRIMP results: {trimp_results}")
    
    # Update activity data - but DON'T overwrite the original heart_rate_series
    # Only update the TRIMP data and total_trimp
    logger.info(f"Updating activity TRIMP data: {trimp_results.get('total_trimp', 0.0)}")
    cur.execute("""
        UPDATE activity_data 
        SET trimp_data = ?, total_trimp = ?, updated_at = CURRENT_TIMESTAMP
        WHERE activity_id = ?
    """, (
        json.dumps(trimp_results),
        trimp_results.get('total_trimp', 0.0),
        activity_id
    ))
    
    # Update daily data to reflect the change
    # Get the date from the activity data instead of trying to parse it from activity_id
    start_time = activity['start_time_local']
    logger.info(f"Activity start_time_local: {start_time}")
    
    # Extract date from start_time_local - handle different formats
    date = None
    if start_time:
        if ' ' in start_time:
            # Format: "2025-07-08 07:14:25"
            date = start_time.split(' ')[0]
        elif 'T' in start_time:
            # Format: "2025-07-08T07:14:25.0"
            date = start_time.split('T')[0]
        else:
            # Assume it's already a date
            date = start_time
    
    if date:
        logger.info(f"Extracted date: {date}")
        # Rebuild daily HR series and TRIMP
        from jobs import build_daily_hr_timeseries, calculate_trimp_from_timeseries
        
        daily_hr_series = build_daily_hr_timeseries(date, conn, cur)
        logger.info(f"Daily HR series: {len(daily_hr_series)} points")
        daily_trimp_results = calculate_trimp_from_timeseries(daily_hr_series)
        logger.info(f"Daily TRIMP results: {daily_trimp_results}")
        
        cur.execute("""
            UPDATE daily_data 
            SET heart_rate_series = ?, trimp_data = ?, total_trimp = ?, updated_at = CURRENT_TIMESTAMP
            WHERE date = ?
        """, (
            json.dumps(daily_hr_series),
            json.dumps(daily_trimp_results),
            daily_trimp_results.get('total_trimp', 0.0),
            date
        ))
    else:
        logger.warning(f"Could not extract date from activity start_time_local: {activity['start_time_local']}")
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"TRIMP recalculation complete for activity {activity_id}")

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
        SELECT date, trimp_data, total_trimp, daily_score, activity_type
        FROM daily_data 
        WHERE date >= ? AND date <= ?
        ORDER BY date
    """, (start, end))
    
    data = cur.fetchall()
    cur.close()
    conn.close()
    
    # Convert to list of dicts
    weekly_data = []
    for row in data:
        trimp_data = json.loads(row['trimp_data']) if row['trimp_data'] else {}
        weekly_data.append({
            'date': row['date'],
            'presentation_buckets': trimp_data.get('presentation_buckets', {}),
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
        # Get current HR parameters from database as defaults
        current_resting_hr, current_max_hr = get_user_hr_parameters()
        resting_hr = data.get('resting_hr', current_resting_hr)
        max_hr = data.get('max_hr', current_max_hr)
        
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
        # Get current HR parameters from database as defaults
        current_resting_hr, current_max_hr = get_user_hr_parameters()
        resting_hr = int(request.form.get('resting_hr', current_resting_hr))
        max_hr = int(request.form.get('max_hr', current_max_hr))
        
        ensure_user_hr_parameters(resting_hr, max_hr)
        flash('HR parameters updated successfully!', 'success')
        return redirect(url_for('admin'))
    
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

@app.route('/api/activity/<activity_id>/notes', methods=['GET', 'POST'])
def activity_notes(activity_id):
    """Get or update notes for a specific activity."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            notes = data.get('notes', '').strip()
            
            # Save activity notes to user_data table
            if notes:
                save_user_data('activity_notes', activity_id, notes)
            else:
                # Delete existing notes if empty
                delete_user_data('activity_notes', activity_id)
            
            return jsonify({
                'success': True,
                'message': 'Notes saved successfully',
                'notes': notes
            })
            
        except Exception as e:
            logger.error(f"Error saving activity notes for {activity_id}: {e}")
            return jsonify({'error': f'Error saving notes: {str(e)}'}), 500
    
    else:  # GET
        try:
            # Get current notes from user_data table
            notes = get_user_data('activity_notes', activity_id)
            
            return jsonify({
                'success': True,
                'notes': notes or ''
            })
            
        except Exception as e:
            logger.error(f"Error loading activity notes for {activity_id}: {e}")
            return jsonify({'error': f'Error loading notes: {str(e)}'}), 500


@app.route('/api/data/<date>/notes', methods=['GET', 'POST'])
def daily_notes(date):
    """Get or update notes for a specific date label."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Treat date as a string label, not a real date
    # Validate format: YYYY-MM-DD
    if not (len(date) == 10 and date[4] == '-' and date[7] == '-'):
        return jsonify({'error': 'Invalid date label format. Expected YYYY-MM-DD'}), 400
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            notes = data.get('notes', '').strip()
            
            # Save daily notes to user_data table
            if notes:
                save_user_data('daily_notes', date, notes)
            else:
                # Delete existing notes if empty
                delete_user_data('daily_notes', date)
            
            return jsonify({
                'success': True,
                'message': 'Notes saved successfully',
                'notes': notes
            })
            
        except Exception as e:
            logger.error(f"Error saving daily notes for {date}: {e}")
            return jsonify({'error': f'Error saving notes: {str(e)}'}), 500
    
    else:  # GET
        try:
            # Get current notes from user_data table
            notes = get_user_data('daily_notes', date)
            
            return jsonify({
                'success': True,
                'notes': notes or ''
            })
            
        except Exception as e:
            logger.error(f"Error loading daily notes for {date}: {e}")
            return jsonify({'error': f'Error loading notes: {str(e)}'}), 500

@app.route('/api/data/<date>/trimp-overrides', methods=['GET', 'POST'])
def daily_trimp_overrides(date):
    """Get or update TRIMP overrides for a specific date label."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Treat date as a string label, not a real date
    # Validate format: YYYY-MM-DD
    if not (len(date) == 10 and date[4] == '-' and date[7] == '-'):
        return jsonify({'error': 'Invalid date label format. Expected YYYY-MM-DD'}), 400
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            trimp_overrides = data.get('trimp_overrides', {})
            
            # Validate TRIMP overrides - ensure all values are positive numbers
            for zone, value in trimp_overrides.items():
                if value is not None and value != '':
                    try:
                        float_value = float(value)
                        if float_value < 0:
                            return jsonify({'error': f'TRIMP value for zone {zone} must be positive'}), 400
                        trimp_overrides[zone] = float_value
                    except (ValueError, TypeError):
                        return jsonify({'error': f'Invalid TRIMP value for zone {zone}'}), 400
            
            # Save TRIMP overrides to user_data table
            # If we have overrides object with any keys, save it (even if all values are 0)
            if trimp_overrides and len(trimp_overrides) > 0:
                save_user_data('daily_trimp_overrides', date, json.dumps(trimp_overrides))
            else:
                # Delete existing overrides if empty
                delete_user_data('daily_trimp_overrides', date)
            
            return jsonify({
                'success': True,
                'message': 'TRIMP overrides saved successfully',
                'trimp_overrides': trimp_overrides
            })
            
        except Exception as e:
            logger.error(f"Error saving TRIMP overrides for {date}: {e}")
            return jsonify({'error': f'Error saving TRIMP overrides: {str(e)}'}), 500
    
    else:  # GET
        try:
            # Get current TRIMP overrides from user_data table
            overrides_json = get_user_data('daily_trimp_overrides', date)
            trimp_overrides = json.loads(overrides_json) if overrides_json else {}
            
            return jsonify({
                'success': True,
                'trimp_overrides': trimp_overrides
            })
            
        except Exception as e:
            logger.error(f"Error loading TRIMP overrides for {date}: {e}")
            return jsonify({'error': f'Error loading TRIMP overrides: {str(e)}'}), 500

@app.route('/api/data/<date>/hr-csv')
def download_daily_hr_csv(date):
    """Download HR data for a specific date label as CSV."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Treat date as a string label, not a real date
    # Validate format: YYYY-MM-DD
    if not (len(date) == 10 and date[4] == '-' and date[7] == '-'):
        return jsonify({'error': 'Invalid date label format. Expected YYYY-MM-DD'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get daily HR data using date as string
    cur.execute("""
        SELECT heart_rate_series
        FROM daily_data 
        WHERE date = ?
    """, (date,))
    
    daily_data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not daily_data:
        return jsonify({'error': 'Daily data not found'}), 404
    
    heart_rate_series = json.loads(daily_data['heart_rate_series']) if daily_data['heart_rate_series'] else []
    
    if not heart_rate_series:
        return jsonify({'error': 'No HR data available for this date'}), 404
    
    # Create CSV content
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'hr'])  # Header
    
    for entry in heart_rate_series:
        if entry and len(entry) >= 2:
            timestamp = entry[0]
            hr = entry[1]
            writer.writerow([timestamp, hr])
    
    output.seek(0)
    
    # Create response with CSV content
    from flask import Response
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=daily_{date}_hr_data.csv'}
    )
    
    return response

if __name__ == '__main__':
    init_database()
    app.run(debug=SERVER_CONFIG['DEBUG'], host=SERVER_CONFIG['HOST'], port=SERVER_CONFIG['DEFAULT_PORT']) 