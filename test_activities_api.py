#!/usr/bin/env python3
"""
Test script to check what the activities API returns
"""

import os
import json
from dotenv import load_dotenv
from garminconnect import Garmin

# Load environment variables
load_dotenv('env.local')

def test_activities_api():
    """Test the activities API for a specific date."""
    
    # Initialize Garmin API
    api = Garmin(os.getenv('GARMIN_EMAIL'), os.getenv('GARMIN_PASSWORD'))
    
    try:
        # Login
        api.login()
        print("Successfully logged in to Garmin Connect")
        
        # Test date
        test_date = '2025-07-02'
        
        # Get activities for the date
        print(f"\n=== Testing activities for {test_date} ===")
        activities = api.get_activities_fordate(test_date)
        
        print(f"Activities type: {type(activities)}")
        print(f"Activities: {json.dumps(activities, indent=2)}")
        
        if activities:
            if isinstance(activities, dict):
                print(f"Activities dict keys: {list(activities.keys())}")
                if 'activities' in activities:
                    print(f"Found 'activities' key with {len(activities['activities'])} items")
                    for i, activity in enumerate(activities['activities']):
                        print(f"Activity {i}: {activity}")
            else:
                print(f"Activities is not a dict, length: {len(activities) if hasattr(activities, '__len__') else 'No length'}")
                for i, activity in enumerate(activities):
                    print(f"Activity {i}: {activity}")
        else:
            print("No activities returned")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_activities_api() 