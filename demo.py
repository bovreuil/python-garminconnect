#!/usr/bin/env python3
"""
Garmin Heart Rate Analyzer - Demo Script

This script demonstrates the core functionality of the Garmin Heart Rate Analyzer:
- Garmin Connect authentication
- Heart rate data retrieval
- Zone analysis and scoring
- Activity type classification
"""

import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv

# Add the garminconnect library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'garminconnect'))

# Load environment variables
load_dotenv('test.env')

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"🎯 {title}")
    print("=" * 60)

def print_section(title):
    """Print a formatted section header."""
    print(f"\n📋 {title}")
    print("-" * 40)

def demo_garmin_connection():
    """Demonstrate Garmin Connect connection and data retrieval."""
    print_header("Garmin Connect Demo")
    
    # Get credentials
    email = os.getenv('GARMIN_EMAIL')
    password = os.getenv('GARMIN_PASSWORD')
    
    if not email or not password:
        print("❌ Missing Garmin credentials in test.env")
        print("   Please create test.env with GARMIN_EMAIL and GARMIN_PASSWORD")
        return False
    
    print(f"📧 Email: {email}")
    print("🔐 Attempting to authenticate...")
    
    try:
        # Import our classes
        from app_simple import GarminDataCollector, HeartRateAnalyzer
        
        # Test authentication
        print_section("Authentication")
        collector = GarminDataCollector(email, password)
        success, result = collector.authenticate()
        
        if not success:
            print(f"❌ Authentication failed: {result}")
            return False
        
        print("✅ Authentication successful!")
        
        # Test data retrieval
        print_section("Data Retrieval")
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        print(f"📅 Fetching heart rate data for: {yesterday}")
        
        heart_rate_data = collector.get_heart_rate_data(yesterday)
        
        if not heart_rate_data:
            print("❌ No heart rate data available")
            return False
        
        print("✅ Heart rate data retrieved successfully!")
        
        # Display basic info
        heart_rate_values = heart_rate_data.get('heartRateValues', [])
        print(f"📊 Total samples: {len(heart_rate_values)}")
        print(f"💓 Resting HR: {heart_rate_data.get('restingHeartRate', 'N/A')} BPM")
        print(f"📈 Min HR: {heart_rate_data.get('minHeartRate', 'N/A')} BPM")
        print(f"📉 Max HR: {heart_rate_data.get('maxHeartRate', 'N/A')} BPM")
        
        # Test analysis
        print_section("Heart Rate Analysis")
        analyzer = HeartRateAnalyzer()
        
        # Zone bucketing
        zone_buckets = analyzer.bucket_heart_rates(heart_rate_data)
        print("📊 Heart Rate Zones:")
        for zone, count in zone_buckets.items():
            print(f"   {zone} BPM: {count} samples")
        
        # Score calculation
        daily_score, activity_type = analyzer.calculate_daily_score(zone_buckets)
        print(f"\n🎯 Daily Score: {daily_score:.1f}")
        print(f"🏃 Activity Type: {activity_type}")
        
        # Activity type explanation
        activity_explanations = {
            "long_low_intensity": "Extended periods in lower heart rate zones (good for endurance)",
            "short_high_intensity": "Brief periods in higher heart rate zones (good for intensity)",
            "mixed": "Balanced distribution across zones (good for overall fitness)",
            "no_activity": "No significant heart rate activity detected"
        }
        
        explanation = activity_explanations.get(activity_type, "Unknown activity pattern")
        print(f"💡 {explanation}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_zone_customization():
    """Demonstrate custom zone configuration."""
    print_header("Custom Zone Configuration Demo")
    
    try:
        from app_simple import HeartRateAnalyzer
        
        # Create custom zones for different fitness levels
        custom_zones = [
            (60, 70),   # Very light
            (70, 80),   # Light
            (80, 90),   # Moderate
            (90, 100),  # Moderate-high
            (100, 110), # High
            (110, 120), # Very high
            (120, 999)  # Maximum
        ]
        
        print("🔧 Testing custom zone configuration...")
        analyzer = HeartRateAnalyzer(zones=custom_zones)
        
        # Test with sample data
        test_data = {
            "heartRateValues": [
                {"value": 65, "timestamp": "2024-01-15T08:00:00"},
                {"value": 75, "timestamp": "2024-01-15T08:01:00"},
                {"value": 85, "timestamp": "2024-01-15T08:02:00"},
                {"value": 95, "timestamp": "2024-01-15T08:03:00"},
                {"value": 105, "timestamp": "2024-01-15T08:04:00"},
                {"value": 115, "timestamp": "2024-01-15T08:05:00"},
                {"value": 125, "timestamp": "2024-01-15T08:06:00"},
            ]
        }
        
        zone_buckets = analyzer.bucket_heart_rates(test_data)
        print("📊 Custom Zone Results:")
        for zone, count in zone_buckets.items():
            print(f"   {zone} BPM: {count} samples")
        
        daily_score, activity_type = analyzer.calculate_daily_score(zone_buckets)
        print(f"\n🎯 Score with custom zones: {daily_score:.1f}")
        print(f"🏃 Activity type: {activity_type}")
        
        print("✅ Custom zone configuration working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run the demo."""
    print("🚀 Garmin Heart Rate Analyzer - Demo")
    print("=" * 60)
    print("This demo showcases the core functionality of the analyzer.")
    print("Make sure you have test.env configured with your Garmin credentials.")
    
    # Demo 1: Garmin Connection and Analysis
    success1 = demo_garmin_connection()
    
    # Demo 2: Custom Zone Configuration
    success2 = demo_zone_customization()
    
    # Summary
    print_header("Demo Summary")
    print(f"✅ Garmin Connection: {'PASS' if success1 else 'FAIL'}")
    print(f"✅ Custom Zones: {'PASS' if success2 else 'FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All demos completed successfully!")
        print("\n📝 Next steps:")
        print("1. Run the web app: python3 app_simple.py")
        print("2. Visit: http://localhost:5001/test-garmin")
        print("3. Set up the full application with database and OAuth")
    else:
        print("\n⚠️  Some demos failed. Check the errors above.")
        if not success1:
            print("   - Verify your Garmin credentials in test.env")
            print("   - Check your internet connection")
            print("   - Ensure your device has synced data")

if __name__ == "__main__":
    main() 