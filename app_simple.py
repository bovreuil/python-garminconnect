#!/usr/bin/env python3
"""
Simplified version of the app for testing core functionality.
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64

# Add the garminconnect library to the path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'garminconnect'))

# Load environment variables
load_dotenv('test.env')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Encryption key for passwords
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def encrypt_password(password: str) -> str:
    """Encrypt a password using Fernet."""
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a password using Fernet."""
    return cipher_suite.decrypt(encrypted_password.encode()).decode()

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
            import garminconnect
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

# Simple test route
@app.route('/test')
def test():
    """Test route to verify the app works."""
    return jsonify({
        "status": "success",
        "message": "App is running successfully!",
        "garmin_connect_available": True
    })

@app.route('/test-garmin')
def test_garmin():
    """Test Garmin connection."""
    try:
        # Get credentials from environment
        email = os.getenv('GARMIN_EMAIL')
        password = os.getenv('GARMIN_PASSWORD')
        
        if not email or not password:
            return jsonify({
                "status": "error",
                "message": "Missing Garmin credentials in environment"
            })
        
        # Test connection
        collector = GarminDataCollector(email, password)
        success, result = collector.authenticate()
        
        if success:
            # Test data retrieval
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            heart_rate_data = collector.get_heart_rate_data(yesterday)
            
            if heart_rate_data:
                # Test analysis
                analyzer = HeartRateAnalyzer()
                zone_buckets = analyzer.bucket_heart_rates(heart_rate_data)
                daily_score, activity_type = analyzer.calculate_daily_score(zone_buckets)
                
                return jsonify({
                    "status": "success",
                    "message": "Garmin connection and analysis working!",
                    "data": {
                        "date": yesterday,
                        "heart_rate_samples": len(heart_rate_data.get('heartRateValues', [])),
                        "zone_buckets": zone_buckets,
                        "daily_score": daily_score,
                        "activity_type": activity_type
                    }
                })
            else:
                return jsonify({
                    "status": "warning",
                    "message": "Authentication successful but no heart rate data available",
                    "date": yesterday
                })
        else:
            return jsonify({
                "status": "error",
                "message": f"Authentication failed: {result}"
            })
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        })

if __name__ == '__main__':
    print("🚀 Starting simplified Garmin Heart Rate Analyzer...")
    print("📊 Test endpoints:")
    print("   - http://localhost:5001/test (basic app test)")
    print("   - http://localhost:5001/test-garmin (Garmin connection test)")
    app.run(debug=True, host='0.0.0.0', port=5001) 