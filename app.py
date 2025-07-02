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

def init_database():
    """Initialize the SQLite database with required tables."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            google_id VARCHAR(255) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create garmin_credentials table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS garmin_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            email VARCHAR(255) NOT NULL,
            password_encrypted VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create user_hr_parameters table for personal HR settings
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_hr_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            resting_hr INTEGER NOT NULL DEFAULT 48,
            max_hr INTEGER NOT NULL DEFAULT 167,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create heart_rate_data table with TRIMP support
    cur.execute("""
        CREATE TABLE IF NOT EXISTS heart_rate_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date DATE NOT NULL,
            heart_rate_values TEXT,
            individual_hr_buckets TEXT,
            presentation_buckets TEXT,
            trimp_data TEXT,
            total_trimp REAL,
            daily_score REAL,
            activity_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, date)
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()

class TRIMPCalculator:
    """Class to calculate TRIMP (Training Impulse) using exponential model."""
    
    def __init__(self, resting_hr: int = 48, max_hr: int = 167):
        """
        Initialize TRIMP calculator with personal HR parameters.
        
        Args:
            resting_hr: Resting heart rate in BPM
            max_hr: Maximum heart rate in BPM
        """
        self.resting_hr = resting_hr
        self.max_hr = max_hr
        self.hr_reserve = max_hr - resting_hr
        
        # Presentation buckets (10 BPM each) for charts
        self.presentation_buckets = [
            (90, 99), (100, 109), (110, 119), (120, 129),
            (130, 139), (140, 149), (150, 159), (160, 999)
        ]
        
        # Color temperature scale for presentation buckets
        self.bucket_colors = [
            '#1f77b4',  # Blue (90-99)
            '#7fb3d3',  # Light blue (100-109)
            '#17becf',  # Cyan (110-119)
            '#2ca02c',  # Green (120-129)
            '#ff7f0e',  # Orange (130-139)
            '#ff6b35',  # Dark orange (140-149)
            '#d62728',  # Red (150-159)
            '#8b0000'   # Dark red (160+)
        ]
    
    def calculate_hr_reserve_ratio(self, hr: int) -> float:
        """Calculate heart rate reserve ratio for a given HR."""
        if hr <= self.resting_hr:
            return 0.0
        return (hr - self.resting_hr) / self.hr_reserve
    
    def calculate_trimp_for_hr(self, hr: int, minutes: int) -> float:
        """
        Calculate TRIMP for a specific heart rate and time duration.
        
        Args:
            hr: Heart rate in BPM
            minutes: Time spent at this HR in minutes
            
        Returns:
            TRIMP value for this HR/duration combination
        """
        if hr < 90:  # Below exercise threshold
            return 0.0
        
        hr_reserve_ratio = self.calculate_hr_reserve_ratio(hr)
        y = 1.92 * hr_reserve_ratio
        trimp = minutes * hr_reserve_ratio * 0.64 * (math.exp(y))
        
        return trimp
    
    def bucket_heart_rates(self, heart_rate_data: Dict) -> Dict:
        """
        Bucket heart rate values into individual buckets and calculate TRIMP.
        
        Returns:
            Dict with individual buckets, presentation buckets, and TRIMP data
        """
        if not heart_rate_data or 'heartRateValues' not in heart_rate_data:
            return {
                'individual_buckets': {},
                'presentation_buckets': {},
                'trimp_data': {},
                'total_trimp': 0.0
            }
        
        # Initialize buckets
        individual_buckets = {}  # 90, 91, 92, etc.
        presentation_buckets = {  # 90-99, 100-109, etc.
            '90-99': {'minutes': 0, 'trimp': 0.0},
            '100-109': {'minutes': 0, 'trimp': 0.0},
            '110-119': {'minutes': 0, 'trimp': 0.0},
            '120-129': {'minutes': 0, 'trimp': 0.0},
            '130-139': {'minutes': 0, 'trimp': 0.0},
            '140-149': {'minutes': 0, 'trimp': 0.0},
            '150-159': {'minutes': 0, 'trimp': 0.0},
            '160+': {'minutes': 0, 'trimp': 0.0}
        }
        trimp_data = {}
        total_trimp = 0.0
        
        heart_rate_values = heart_rate_data['heartRateValues']
        
        for hr_value in heart_rate_values:
            # Handle both list and dict formats
            if isinstance(hr_value, list):
                # Format: [timestamp, value]
                timestamp, hr = hr_value
            else:
                # Format: {"value": x, "timestamp": y}
                hr = hr_value.get('value')
            
            if hr is not None and hr >= 90:  # Only count HR >= 90
                # Individual bucket
                individual_buckets[hr] = individual_buckets.get(hr, 0) + 1
                
                # Calculate TRIMP for this HR
                trimp = self.calculate_trimp_for_hr(hr, 1)  # 1 minute intervals
                trimp_data[hr] = trimp_data.get(hr, 0.0) + trimp
                total_trimp += trimp
                
                # Presentation bucket
                for i, (min_hr, max_hr) in enumerate(self.presentation_buckets):
                    if min_hr <= hr <= max_hr:
                        bucket_name = f"{min_hr}-{max_hr if max_hr != 999 else '999'}"
                        if bucket_name == "160-999":
                            bucket_name = "160+"
                        presentation_buckets[bucket_name]['minutes'] += 1
                        presentation_buckets[bucket_name]['trimp'] += trimp
                        break
        
        return {
            'individual_buckets': individual_buckets,
            'presentation_buckets': presentation_buckets,
            'trimp_data': trimp_data,
            'total_trimp': total_trimp
        }

class HeartRateAnalyzer:
    """Class to analyze heart rate data using TRIMP calculations."""
    
    def __init__(self, resting_hr: int = 48, max_hr: int = 167):
        """
        Initialize with personal HR parameters.
        
        Args:
            resting_hr: Resting heart rate in BPM
            max_hr: Maximum heart rate in BPM
        """
        self.trimp_calculator = TRIMPCalculator(resting_hr, max_hr)
    
    def analyze_heart_rate_data(self, heart_rate_data: Dict) -> Dict:
        """
        Analyze heart rate data and return comprehensive results.
        
        Returns:
            Dict with buckets, TRIMP data, and analysis results
        """
        # Get TRIMP calculations
        trimp_results = self.trimp_calculator.bucket_heart_rates(heart_rate_data)
        
        # Calculate activity type based on TRIMP distribution
        presentation_buckets = trimp_results['presentation_buckets']
        activity_type = self._determine_activity_type(presentation_buckets)
        
        # Calculate legacy daily score (keeping for compatibility)
        daily_score = self._calculate_legacy_score(presentation_buckets)
        
        return {
            'individual_hr_buckets': trimp_results['individual_buckets'],
            'presentation_buckets': trimp_results['presentation_buckets'],
            'trimp_data': trimp_results['trimp_data'],
            'total_trimp': trimp_results['total_trimp'],
            'daily_score': daily_score,
            'activity_type': activity_type
        }
    
    def _determine_activity_type(self, presentation_buckets: Dict) -> str:
        """Determine activity type based on TRIMP distribution."""
        low_intensity_trimp = (
            presentation_buckets['90-99']['trimp'] +
            presentation_buckets['100-109']['trimp'] +
            presentation_buckets['110-119']['trimp']
        )
        high_intensity_trimp = (
            presentation_buckets['130-139']['trimp'] +
            presentation_buckets['140-149']['trimp'] +
            presentation_buckets['150-159']['trimp'] +
            presentation_buckets['160+']['trimp']
        )
        
        if low_intensity_trimp > high_intensity_trimp * 2:
            return "long_low_intensity"
        elif high_intensity_trimp > low_intensity_trimp * 2:
            return "short_high_intensity"
        else:
            return "mixed"
    
    def _calculate_legacy_score(self, presentation_buckets: Dict) -> float:
        """Calculate legacy daily score for backward compatibility."""
        total_minutes = sum(bucket['minutes'] for bucket in presentation_buckets.values())
        if total_minutes == 0:
            return 0.0
        
        # Weighted score based on time in each zone
        zone_weights = {
            "90-99": 1.0, "100-109": 1.5, "110-119": 2.0, "120-129": 2.5,
            "130-139": 3.0, "140-149": 3.5, "150-159": 4.0, "160+": 4.5
        }
        
        total_score = 0
        for zone, data in presentation_buckets.items():
            weight = zone_weights.get(zone, 1.0)
            total_score += (data['minutes'] / total_minutes) * weight * 100
        
        return total_score

def get_user_hr_parameters(user_id: int) -> Tuple[int, int]:
    """Get user's HR parameters (resting_hr, max_hr)."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT resting_hr, max_hr FROM user_hr_parameters 
        WHERE user_id = ?
    """, (user_id,))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result:
        return result['resting_hr'], result['max_hr']
    else:
        # Default values for Pete
        return 48, 167

def ensure_user_hr_parameters(user_id: int, resting_hr: int = 48, max_hr: int = 167):
    """Ensure user has HR parameters set in database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT OR REPLACE INTO user_hr_parameters (user_id, resting_hr, max_hr, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (user_id, resting_hr, max_hr))
    
    cur.close()
    conn.close()

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
    """Handle Google OAuth callback."""
    token = oauth.google.authorize_access_token()
    
    # Get user info from the token response
    resp = oauth.google.get('https://www.googleapis.com/oauth2/v1/userinfo')
    userinfo = resp.json()
    
    user_email = userinfo.get('email')
    user_name = userinfo.get('name', user_email)
    user_id = userinfo.get('id')

    # Restrict to allowed users
    if user_email not in ALLOWED_USERS:
        flash('Access denied. Your email is not authorized to use this application.', 'error')
        return redirect(url_for('logout'))

    # Store user in database
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO users (email, name, google_id)
        VALUES (?, ?, ?)
    """, (user_email, user_name, user_id))
    cur.execute("SELECT id FROM users WHERE google_id = ?", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    session['user_id'] = user['id']
    session['user_email'] = user_email
    session['user_name'] = user_name
    flash('Successfully logged in!', 'success')
    return redirect(url_for('index'))

@app.route('/setup-garmin', methods=['GET', 'POST'])
def setup_garmin():
    """Setup Garmin credentials."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Store credentials
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT OR REPLACE INTO garmin_credentials (user_id, email, password_encrypted, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (session['user_id'], email, encrypt_password(password)))
        
        cur.close()
        conn.close()
        
        flash('Garmin credentials saved successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('setup_garmin.html')

@app.route('/collect-data', methods=['POST'])
def collect_data():
    """Collect heart rate data for a specific date."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    target_date = request.form.get('date', date.today().isoformat())
    
    # For now, return sample data for testing
    # In production, this would fetch from Garmin Connect
    sample_data = {
        'heartRateValues': [
            [1000, 90],   # 1 minute at 90 BPM
            [2000, 100],  # 1 minute at 100 BPM
            [3000, 110],  # 1 minute at 110 BPM
            [4000, 120],  # 1 minute at 120 BPM
            [5000, 130],  # 1 minute at 130 BPM
            [6000, 140],  # 1 minute at 140 BPM
            [7000, 150],  # 1 minute at 150 BPM
            [8000, 160],  # 1 minute at 160 BPM
            [9000, 129],  # 1 minute at 129 BPM
            [10000, 129], # Another minute at 129 BPM
        ]
    }
    
    # Get user's HR parameters
    resting_hr, max_hr = get_user_hr_parameters(session['user_id'])
    
    # Analyze data
    analyzer = HeartRateAnalyzer(resting_hr, max_hr)
    analysis_results = analyzer.analyze_heart_rate_data(sample_data)
    
    # Store in database
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT OR REPLACE INTO heart_rate_data 
        (user_id, date, heart_rate_values, individual_hr_buckets, presentation_buckets, trimp_data, total_trimp, daily_score, activity_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        session['user_id'], 
        target_date, 
        json.dumps(sample_data),
        json.dumps(analysis_results['individual_hr_buckets']),
        json.dumps(analysis_results['presentation_buckets']),
        json.dumps(analysis_results['trimp_data']),
        analysis_results['total_trimp'],
        analysis_results['daily_score'],
        analysis_results['activity_type']
    ))
    
    cur.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'date': target_date,
        'individual_hr_buckets': analysis_results['individual_hr_buckets'],
        'presentation_buckets': analysis_results['presentation_buckets'],
        'trimp_data': analysis_results['trimp_data'],
        'total_trimp': analysis_results['total_trimp'],
        'daily_score': analysis_results['daily_score'],
        'activity_type': analysis_results['activity_type']
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
        WHERE user_id = ? AND date = ?
    """, (session['user_id'], date))
    
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
        WHERE user_id = ? AND date >= ? AND date <= ?
        ORDER BY date
    """, (session['user_id'], start, end))
    
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
    """Get or update user's HR parameters."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if request.method == 'POST':
        data = request.get_json()
        resting_hr = data.get('resting_hr', 48)
        max_hr = data.get('max_hr', 167)
        
        ensure_user_hr_parameters(session['user_id'], resting_hr, max_hr)
        return jsonify({'success': True, 'resting_hr': resting_hr, 'max_hr': max_hr})
    
    else:  # GET
        resting_hr, max_hr = get_user_hr_parameters(session['user_id'])
        return jsonify({'resting_hr': resting_hr, 'max_hr': max_hr})

@app.route('/setup-hr-parameters', methods=['GET', 'POST'])
def setup_hr_parameters():
    """Setup page for HR parameters."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        resting_hr = int(request.form.get('resting_hr', 48))
        max_hr = int(request.form.get('max_hr', 167))
        
        ensure_user_hr_parameters(session['user_id'], resting_hr, max_hr)
        flash('HR parameters updated successfully!', 'success')
        return redirect(url_for('index'))
    
    # GET request - show current values
    resting_hr, max_hr = get_user_hr_parameters(session['user_id'])
    return render_template('setup_hr_parameters.html', resting_hr=resting_hr, max_hr=max_hr)

if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5001) 