#!/usr/bin/env python3
"""
Simple test script to verify Garmin Connect connection and heart rate data retrieval.
"""

import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv

# Add the garminconnect library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'garminconnect'))

def test_garmin_connection():
    """Test basic Garmin Connect connection and authentication."""
    print("🧪 Testing Garmin Connect Connection")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment or user input
    email = os.getenv('GARMIN_EMAIL')
    password = os.getenv('GARMIN_PASSWORD')
    
    if not email:
        email = input("Enter your Garmin Connect email: ")
    
    if not password:
        password = input("Enter your Garmin Connect password: ")
    
    print(f"\n📧 Using email: {email}")
    print("🔐 Attempting to authenticate...")
    
    try:
        # Import and initialize Garmin API from local directory
        from garminconnect import Garmin
        
        # Create API instance with 2FA support
        api = Garmin(
            email=email,
            password=password,
            return_on_mfa=True
        )
        
        # Attempt login
        print("🔄 Logging in to Garmin Connect...")
        token1, token2 = api.login()
        
        if token1 and token2:
            # 2FA required
            print("⚠️  2FA required! Please enter your authentication code.")
            mfa_code = input("Enter 6-digit MFA code: ")
            
            # Resume login with MFA code
            api.resume_login(token1, mfa_code)
            print("✅ 2FA authentication successful!")
        else:
            print("✅ Authentication successful!")
        
        # Test basic API calls
        print("\n📊 Testing API functionality...")
        
        # Get user info
        try:
            full_name = api.get_full_name()
            print(f"👤 User: {full_name}")
        except Exception as e:
            print(f"⚠️  Could not get user name: {e}")
        
        # Get yesterday's date
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        print(f"📅 Testing heart rate data for: {yesterday}")
        
        # Get heart rate data
        print("💓 Fetching heart rate data...")
        heart_rate_data = api.get_heart_rates(yesterday)
        
        if heart_rate_data:
            print("✅ Heart rate data retrieved successfully!")
            
            # Display basic info
            print(f"\n📈 Heart Rate Summary for {yesterday}:")
            print(f"   Calendar Date: {heart_rate_data.get('calendarDate', 'N/A')}")
            print(f"   Resting HR: {heart_rate_data.get('restingHeartRate', 'N/A')} BPM")
            print(f"   Min HR: {heart_rate_data.get('minHeartRate', 'N/A')} BPM")
            print(f"   Max HR: {heart_rate_data.get('maxHeartRate', 'N/A')} BPM")
            
            # Check heart rate values
            heart_rate_values = heart_rate_data.get('heartRateValues', [])
            print(f"   Total HR samples: {len(heart_rate_values)}")
            
            if heart_rate_values:
                print("\n📊 Sample heart rate data:")
                for i, hr_sample in enumerate(heart_rate_values[:5]):  # Show first 5 samples
                    print(f"   Sample {i+1}: {hr_sample.get('value', 'N/A')} BPM at {hr_sample.get('timestamp', 'N/A')}")
                
                if len(heart_rate_values) > 5:
                    print(f"   ... and {len(heart_rate_values) - 5} more samples")
            else:
                print("   ⚠️  No heart rate samples found for this date")
                
        else:
            print("❌ No heart rate data available for this date")
            print("   This might be normal if:")
            print("   - Your device wasn't worn that day")
            print("   - Data hasn't synced yet")
            print("   - The date is too far in the past")
        
        # Test with today's date as well
        today = date.today().isoformat()
        print(f"\n📅 Testing heart rate data for today: {today}")
        
        try:
            today_hr_data = api.get_heart_rates(today)
            if today_hr_data:
                today_samples = len(today_hr_data.get('heartRateValues', []))
                print(f"✅ Today's data: {today_samples} heart rate samples")
            else:
                print("ℹ️  No data for today yet (normal if it's early in the day)")
        except Exception as e:
            print(f"⚠️  Could not fetch today's data: {e}")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔍 Troubleshooting tips:")
        print("1. Verify your email and password are correct")
        print("2. Check if your Garmin device has synced recently")
        print("3. Ensure you have heart rate data for the test date")
        print("4. Check your internet connection")
        return False

def test_heart_rate_analysis():
    """Test the heart rate analysis functionality."""
    print("\n🧮 Testing Heart Rate Analysis")
    print("=" * 50)
    
    try:
        # Import our analyzer
        from app import HeartRateAnalyzer
        
        # Create test data
        test_data = {
            "calendarDate": "2024-01-15",
            "heartRateValues": [
                {"value": 95, "timestamp": "2024-01-15T08:00:00"},
                {"value": 105, "timestamp": "2024-01-15T08:01:00"},
                {"value": 115, "timestamp": "2024-01-15T08:02:00"},
                {"value": 125, "timestamp": "2024-01-15T08:03:00"},
                {"value": 135, "timestamp": "2024-01-15T08:04:00"},
                {"value": 145, "timestamp": "2024-01-15T08:05:00"},
                {"value": 155, "timestamp": "2024-01-15T08:06:00"},
            ]
        }
        
        analyzer = HeartRateAnalyzer()
        
        # Test zone bucketing
        zone_buckets = analyzer.bucket_heart_rates(test_data)
        print(f"📊 Zone buckets: {zone_buckets}")
        
        # Test score calculation
        daily_score, activity_type = analyzer.calculate_daily_score(zone_buckets)
        print(f"🎯 Daily score: {daily_score:.1f}")
        print(f"🏃 Activity type: {activity_type}")
        
        print("✅ Heart rate analysis test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Heart rate analysis test failed: {e}")
        return False

def main():
    """Run the tests."""
    print("🚀 Garmin Heart Rate Analyzer - Connection Test")
    print("=" * 60)
    
    # Test 1: Garmin Connection
    connection_success = test_garmin_connection()
    
    # Test 2: Heart Rate Analysis (if connection worked)
    analysis_success = False
    if connection_success:
        analysis_success = test_heart_rate_analysis()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   Garmin Connection: {'✅ PASS' if connection_success else '❌ FAIL'}")
    print(f"   Heart Rate Analysis: {'✅ PASS' if analysis_success else '❌ FAIL'}")
    
    if connection_success and analysis_success:
        print("\n🎉 All tests passed! You're ready to use the application.")
        print("\n📝 Next steps:")
        print("1. Set up your environment variables in .env file")
        print("2. Run the full application: python3 app.py")
        print("3. Access the web interface at http://localhost:5000")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        if not connection_success:
            print("   - Verify your Garmin credentials")
            print("   - Check your internet connection")
            print("   - Ensure your device has synced data")

if __name__ == "__main__":
    main() 