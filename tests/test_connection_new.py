#!/usr/bin/env python3
"""
New test script to verify Garmin Connect connection and heart rate data retrieval.
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
    load_dotenv('test.env')
    
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
        
        # Create API instance - will prompt for MFA if needed
        api = Garmin(
            email=email,
            password=password,
            return_on_mfa=False  # This will prompt for MFA automatically
        )
        
        # Attempt login - this will prompt for MFA if required
        print("🔄 Logging in to Garmin Connect...")
        print("⚠️  If 2FA is required, you'll be prompted for the code.")
        
        try:
            token1, token2 = api.login()
            print("✅ Authentication successful!")
        except TypeError as e:
            if "cannot unpack non-iterable NoneType object" in str(e):
                print("❌ Login failed - garth.login() returned None")
                print("   This usually means the login process failed before MFA")
                print("   Possible causes:")
                print("   - Invalid email/password")
                print("   - Network connectivity issues")
                print("   - Garmin Connect service issues")
                return False
            else:
                raise
        except Exception as e:
            print(f"❌ Login failed with error: {e}")
            return False
        
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
                    # Handle both list and dict formats
                    if isinstance(hr_sample, list):
                        # Format: [timestamp, value]
                        timestamp, value = hr_sample
                        print(f"   Sample {i+1}: {value} BPM at {timestamp}")
                    else:
                        # Format: {"value": x, "timestamp": y}
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
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n🔍 Troubleshooting tips:")
        print("1. Verify your email and password are correct")
        print("2. Check if your Garmin device has synced recently")
        print("3. Ensure you have heart rate data for the test date")
        print("4. Check your internet connection")
        return False

def main():
    """Run the tests."""
    print("🚀 Garmin Heart Rate Analyzer - Connection Test")
    print("=" * 60)
    
    # Test 1: Garmin Connection
    connection_success = test_garmin_connection()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   Garmin Connection: {'✅ PASS' if connection_success else '❌ FAIL'}")
    
    if connection_success:
        print("\n🎉 All tests passed! You're ready to use the application.")
        print("\n📝 Next steps:")
        print("1. Set up your environment variables in .env file")
        print("2. Run the full application: python3 app.py")
        print("3. Access the web interface at http://localhost:5000")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("   - Verify your Garmin credentials")
        print("   - Check your internet connection")
        print("   - Ensure your device has synced data")

if __name__ == "__main__":
    main() 