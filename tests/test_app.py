#!/usr/bin/env python3
"""
Simple test script to verify the Garmin Heart Rate Analyzer components.
"""

import os
import sys
from datetime import date
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import HeartRateAnalyzer, init_database, get_db_connection

def test_heart_rate_analyzer():
    """Test the HeartRateAnalyzer class."""
    print("Testing HeartRateAnalyzer...")
    
    analyzer = HeartRateAnalyzer()
    
    # Test data structure similar to what Garmin Connect returns
    test_heart_rate_data = {
        "calendarDate": "2024-01-15",
        "heartRateValues": [
            {"value": 95, "timestamp": "2024-01-15T08:00:00"},
            {"value": 105, "timestamp": "2024-01-15T08:01:00"},
            {"value": 115, "timestamp": "2024-01-15T08:02:00"},
            {"value": 125, "timestamp": "2024-01-15T08:03:00"},
            {"value": 135, "timestamp": "2024-01-15T08:04:00"},
            {"value": 145, "timestamp": "2024-01-15T08:05:00"},
            {"value": 155, "timestamp": "2024-01-15T08:06:00"},
            {"value": 98, "timestamp": "2024-01-15T08:07:00"},
            {"value": 108, "timestamp": "2024-01-15T08:08:00"},
            {"value": 118, "timestamp": "2024-01-15T08:09:00"},
        ]
    }
    
    # Test zone bucketing
    zone_buckets = analyzer.bucket_heart_rates(test_heart_rate_data)
    print(f"Zone buckets: {zone_buckets}")
    
    # Test score calculation
    daily_score, activity_type = analyzer.calculate_daily_score(zone_buckets)
    print(f"Daily score: {daily_score}")
    print(f"Activity type: {activity_type}")
    
    # Verify results
    assert len(zone_buckets) > 0, "Zone bucketing failed"
    assert daily_score > 0, "Score calculation failed"
    assert activity_type in ["long_low_intensity", "short_high_intensity", "mixed"], "Invalid activity type"
    
    print("✅ HeartRateAnalyzer tests passed!")

def test_database_connection():
    """Test database connection and initialization."""
    print("\nTesting database connection...")
    
    try:
        # Test database initialization
        init_database()
        print("✅ Database initialization successful")
        
        # Test connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ Database connection successful - PostgreSQL version: {version[0]}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    return True

def test_environment_variables():
    """Test that required environment variables are set."""
    print("\nTesting environment variables...")
    
    load_dotenv()
    
    required_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
        'GOOGLE_ID',
        'GOOGLE_SECRET',
        'ENCRYPTION_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please set these variables in your .env file")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def test_imports():
    """Test that all required modules can be imported."""
    print("\nTesting imports...")
    
    try:
        import flask
        import psycopg2
        import garminconnect
        import cryptography
        from flask_oauthlib.client import OAuth
        print("✅ All required modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install missing dependencies: pip install -r requirements.txt")
        return False

def main():
    """Run all tests."""
    print("🧪 Running Garmin Heart Rate Analyzer Tests")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Environment Variables", test_environment_variables),
        ("Database Connection", test_database_connection),
        ("Heart Rate Analyzer", test_heart_rate_analyzer),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is ready to run.")
        print("\nNext steps:")
        print("1. Run: python3 app.py")
        print("2. Open: http://localhost:5000")
        print("3. Login with Google and setup Garmin credentials")
    else:
        print("❌ Some tests failed. Please fix the issues before running the application.")
        sys.exit(1)

if __name__ == "__main__":
    main() 