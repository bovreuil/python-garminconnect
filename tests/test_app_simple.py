#!/usr/bin/env python3
"""
Simple test version of the app to verify Garmin functionality works.
"""

import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv

# Add the garminconnect library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'garminconnect'))

# Load environment variables
load_dotenv('test.env')

def test_garmin_functionality():
    """Test the core Garmin functionality from the app."""
    print("🧪 Testing App's Garmin Functionality")
    print("=" * 50)
    
    # Get credentials
    email = os.getenv('GARMIN_EMAIL')
    password = os.getenv('GARMIN_PASSWORD')
    
    if not email or not password:
        print("❌ Missing Garmin credentials in test.env")
        return False
    
    print(f"📧 Using email: {email}")
    
    try:
        # Import the app's GarminDataCollector
        from app import GarminDataCollector, HeartRateAnalyzer
        
        # Test authentication
        print("🔄 Testing authentication...")
        collector = GarminDataCollector(email, password)
        success, result = collector.authenticate()
        
        if success:
            print("✅ Authentication successful!")
            
            # Test heart rate data collection
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            print(f"📅 Testing heart rate data for: {yesterday}")
            
            heart_rate_data = collector.get_heart_rate_data(yesterday)
            
            if heart_rate_data:
                print("✅ Heart rate data retrieved successfully!")
                
                # Test heart rate analysis
                print("🧮 Testing heart rate analysis...")
                analyzer = HeartRateAnalyzer()
                
                # Test zone bucketing
                zone_buckets = analyzer.bucket_heart_rates(heart_rate_data)
                print(f"📊 Zone buckets: {zone_buckets}")
                
                # Test score calculation
                daily_score, activity_type = analyzer.calculate_daily_score(zone_buckets)
                print(f"🎯 Daily score: {daily_score:.1f}")
                print(f"🏃 Activity type: {activity_type}")
                
                print("✅ All app functionality tests passed!")
                return True
            else:
                print("❌ No heart rate data available")
                return False
        else:
            print(f"❌ Authentication failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the tests."""
    print("🚀 Testing App's Core Functionality")
    print("=" * 60)
    
    success = test_garmin_functionality()
    
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   App Garmin Functionality: {'✅ PASS' if success else '❌ FAIL'}")
    
    if success:
        print("\n🎉 All app functionality tests passed!")
        print("\n📝 The app is ready to run with:")
        print("1. Install full dependencies (may need to resolve conflicts)")
        print("2. Set up PostgreSQL database")
        print("3. Configure Google OAuth")
        print("4. Run: python3 app.py")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main() 