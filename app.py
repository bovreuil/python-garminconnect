import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_oauthlib.client import OAuth
from werkzeug.security import generate_password_hash, check_password_hash
import garminconnect
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# Google OAuth configuration
app.config['GOOGLE_ID'] = os.getenv('GOOGLE_ID')
app.config['GOOGLE_SECRET'] = os.getenv('GOOGLE_SECRET')
app.config['OAUTH_OAUTH_SCOPE'] = 'https://www.googleapis.com/auth/userinfo.email'

# Encryption key for passwords
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

oauth = OAuth(app)
google = oauth.remote_app(
    'google',
    consumer_key=app.config['GOOGLE_ID'],
    consumer_secret=app.config['GOOGLE_SECRET'],
    request_token_params={
        'scope': 'https://www.googleapis.com/auth/userinfo.email'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth'
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a database connection."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

def encrypt_password(password: str) -> str:
    """Encrypt a password using Fernet."""
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a password using Fernet."""
    return cipher_suite.decrypt(encrypted_password.encode()).decode()

def init_database():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            google_id VARCHAR(255) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create garmin_credentials table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS garmin_credentials (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            password_encrypted VARCHAR(255) NOT NULL,
            tokens TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create heart_rate_data table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS heart_rate_data (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            heart_rate_values JSONB,
            zone_buckets JSONB,
            daily_score FLOAT,
            activity_type VARCHAR(50), -- 'long_low_intensity' or 'short_high_intensity'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, date)
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()

class HeartRateAnalyzer:
    """Class to analyze heart rate data and calculate zones and scores."""
    
    def __init__(self, zones: Optional[List[Tuple[int, int]]] = None):
        """
        Initialize with custom heart rate zones.
        Default zones: 90-100, 100-110, 110-120, 120-130, 130-140, 140-150, 150+
        """
        self.zones = zones or [
            (90, 100), (100, 110), (110, 120), (120, 130), 
            (130, 140), (140, 150), (150, 999)
        ]
    
    def bucket_heart_rates(self, heart_rate_data: Dict) -> Dict[str, int]:
        """Bucket heart rate values into zones and count time spent in each."""
        if not heart_rate_data or 'heartRateValues' not in heart_rate_data:
            return {}
        
        zone_counts = defaultdict(int)
        heart_rate_values = heart_rate_data['heartRateValues']
        
        for hr_value in heart_rate_values:
            # Handle both list and dict formats
            if isinstance(hr_value, list):
                # Format: [timestamp, value]
                timestamp, hr = hr_value
            else:
                # Format: {"value": x, "timestamp": y}
                hr = hr_value.get('value')
            
            if hr is not None:
                # Find which zone this heart rate belongs to
                for i, (min_hr, max_hr) in enumerate(self.zones):
                    if min_hr <= hr < max_hr:
                        zone_name = f"{min_hr}-{max_hr if max_hr != 999 else '+'}"
                        zone_counts[zone_name] += 1
                        break
        
        return dict(zone_counts)
    
    def calculate_daily_score(self, zone_buckets: Dict[str, int]) -> Tuple[float, str]:
        """
        Calculate a weighted daily score based on time spent in each zone.
        Returns (score, activity_type)
        """
        if not zone_buckets:
            return 0.0, "no_activity"
        
        # Define weights for each zone (higher zones = higher weights)
        zone_weights = {
            "90-100": 1.0,
            "100-110": 1.5,
            "110-120": 2.0,
            "120-130": 2.5,
            "130-140": 3.0,
            "140-150": 3.5,
            "150+": 4.0
        }
        
        total_score = 0
        total_time = sum(zone_buckets.values())
        
        if total_time == 0:
            return 0.0, "no_activity"
        
        for zone, time_spent in zone_buckets.items():
            weight = zone_weights.get(zone, 1.0)
            total_score += (time_spent / total_time) * weight * 100
        
        # Determine activity type based on distribution
        low_intensity_time = sum(
            time_spent for zone, time_spent in zone_buckets.items() 
            if zone in ["90-100", "100-110", "110-120"]
        )
        high_intensity_time = sum(
            time_spent for zone, time_spent in zone_buckets.items() 
            if zone in ["130-140", "140-150", "150+"]
        )
        
        if low_intensity_time > high_intensity_time * 2:
            activity_type = "long_low_intensity"
        elif high_intensity_time > low_intensity_time * 2:
            activity_type = "short_high_intensity"
        else:
            activity_type = "mixed"
        
        return total_score, activity_type

class GarminDataCollector:
    """Class to handle Garmin Connect data collection."""
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.api = None
    
    def authenticate(self, mfa_code: Optional[str] = None, client_state: Optional[Dict] = None) -> Tuple[bool, Optional[Dict]]:
        """Authenticate with Garmin Connect, handling 2FA if needed."""
        try:
            # Since return_on_mfa is not supported by current garth version,
            # we'll use the standard login approach that prompts for MFA
            self.api = garminconnect.Garmin(
                email=self.email,
                password=self.password,
                return_on_mfa=False  # Use standard MFA prompt
            )
            
            # Attempt login - this will prompt for MFA if needed
            token1, token2 = self.api.login()
            
            # If we get here, login was successful (either no MFA or MFA was handled)
            return True, None
                    
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, {"error": str(e)}
    
    def get_heart_rate_data(self, target_date: str) -> Optional[Dict]:
        """Get heart rate data for a specific date."""
        try:
            if not self.api:
                return None
            
            heart_rate_data = self.api.get_heart_rates(target_date)
            return heart_rate_data
            
        except Exception as e:
            logger.error(f"Error fetching heart rate data: {e}")
            return None

def get_heart_rate_data_for_date(target_date: str, email: str, password: str) -> Optional[Dict]:
    """Helper function to get heart rate data for a date."""
    try:
        collector = GarminDataCollector(email, password)
        success, result = collector.authenticate()
        
        if success:
            return collector.get_heart_rate_data(target_date)
        else:
            logger.error(f"Authentication failed: {result}")
            return None
            
    except Exception as e:
        logger.error(f"Error in get_heart_rate_data_for_date: {e}")
        return None

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
    return google.authorize(callback=url_for('authorized', _external=True))

@app.route('/logout')
def logout():
    """Logout user."""
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_name', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/login/authorized')
def authorized():
    """Handle OAuth callback."""
    resp = google.authorized_response()
    if resp is None or resp.get('access_token') is None:
        return 'Access denied: reason={} error={}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )
    
    session['google_token'] = (resp['access_token'], '')
    me = google.get('userinfo')
    
    # Store user in database
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        INSERT INTO users (email, name, google_id) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (google_id) DO UPDATE SET 
        email = EXCLUDED.email, name = EXCLUDED.name
        RETURNING id
    """, (me.data['email'], me.data.get('name', ''), me.data['id']))
    
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    session['user_id'] = user['id']
    session['user_email'] = me.data['email']
    session['user_name'] = me.data.get('name', '')
    
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
        
        # Test authentication
        collector = GarminDataCollector(email, password)
        success, result = collector.authenticate()
        
        if success:
            # Store credentials
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO garmin_credentials (user_id, email, password_encrypted) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (user_id) DO UPDATE SET 
                email = EXCLUDED.email, password_encrypted = EXCLUDED.password_encrypted,
                updated_at = CURRENT_TIMESTAMP
            """, (session['user_id'], email, encrypt_password(password)))
            
            cur.close()
            conn.close()
            
            flash('Garmin credentials saved successfully!', 'success')
            return redirect(url_for('index'))
        elif result and result.get('mfa_required'):
            # Store temporary credentials for MFA
            session['temp_garmin_email'] = email
            session['temp_garmin_password'] = password
            session['garmin_client_state'] = result['client_state']
            return render_template('mfa.html')
        else:
            flash('Invalid Garmin credentials. Please try again.', 'error')
    
    return render_template('setup_garmin.html')

@app.route('/mfa', methods=['POST'])
def handle_mfa():
    """Handle MFA code submission."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    mfa_code = request.form['mfa_code']
    email = session.get('temp_garmin_email')
    password = session.get('temp_garmin_password')
    client_state = session.get('garmin_client_state')
    
    if not all([email, password, client_state]):
        flash('Session expired. Please try again.', 'error')
        return redirect(url_for('setup_garmin'))
    
    collector = GarminDataCollector(email, password)
    success, result = collector.authenticate(mfa_code, client_state)
    
    if success:
        # Store credentials
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO garmin_credentials (user_id, email, password_encrypted) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (user_id) DO UPDATE SET 
            email = EXCLUDED.email, password_encrypted = EXCLUDED.password_encrypted,
            updated_at = CURRENT_TIMESTAMP
        """, (session['user_id'], email, encrypt_password(password)))
        
        cur.close()
        conn.close()
        
        # Clean up session
        session.pop('temp_garmin_email', None)
        session.pop('temp_garmin_password', None)
        session.pop('garmin_client_state', None)
        
        flash('Garmin credentials saved successfully!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Invalid MFA code. Please try again.', 'error')
        return render_template('mfa.html')

@app.route('/collect-data', methods=['POST'])
def collect_data():
    """Collect heart rate data for a specific date."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    target_date = request.form.get('date', date.today().isoformat())
    
    # Get user's Garmin credentials
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT email, password_encrypted FROM garmin_credentials 
        WHERE user_id = %s
    """, (session['user_id'],))
    
    creds = cur.fetchone()
    cur.close()
    conn.close()
    
    if not creds:
        return jsonify({'error': 'Garmin credentials not found. Please setup your credentials first.'}), 404
    
    # Decrypt password
    try:
        password = decrypt_password(creds['password_encrypted'])
    except Exception as e:
        logger.error(f"Password decryption error: {e}")
        return jsonify({'error': 'Credential decryption failed'}), 500
    
    # Collect data
    analyzer = HeartRateAnalyzer()
    
    # Get heart rate data
    heart_rate_data = get_heart_rate_data_for_date(target_date, creds['email'], password)
    
    if not heart_rate_data:
        return jsonify({'error': 'No heart rate data available for this date'}), 404
    
    # Analyze data
    zone_buckets = analyzer.bucket_heart_rates(heart_rate_data)
    daily_score, activity_type = analyzer.calculate_daily_score(zone_buckets)
    
    # Store in database
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO heart_rate_data (user_id, date, heart_rate_values, zone_buckets, daily_score, activity_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, date) DO UPDATE SET
        heart_rate_values = EXCLUDED.heart_rate_values,
        zone_buckets = EXCLUDED.zone_buckets,
        daily_score = EXCLUDED.daily_score,
        activity_type = EXCLUDED.activity_type,
        created_at = CURRENT_TIMESTAMP
    """, (
        session['user_id'], 
        target_date, 
        json.dumps(heart_rate_data),
        json.dumps(zone_buckets),
        daily_score,
        activity_type
    ))
    
    cur.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'date': target_date,
        'zone_buckets': zone_buckets,
        'daily_score': daily_score,
        'activity_type': activity_type
    })

@app.route('/api/data/<date>')
def get_data(date):
    """Get heart rate data for a specific date."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT * FROM heart_rate_data 
        WHERE user_id = %s AND date = %s
    """, (session['user_id'], date))
    
    data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not data:
        return jsonify({'error': 'No data found for this date'}), 404
    
    return jsonify({
        'date': data['date'].isoformat(),
        'zone_buckets': data['zone_buckets'],
        'daily_score': data['daily_score'],
        'activity_type': data['activity_type']
    })

@google.tokengetter
def get_google_oauth_token():
    """Get Google OAuth token from session."""
    return session.get('google_token')

if __name__ == '__main__':
    init_database()
    app.run(debug=True) 