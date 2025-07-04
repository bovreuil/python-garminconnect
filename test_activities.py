#!/usr/bin/env python3
"""
Test script to explore activity data collection and TRIMP calculation
"""

import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from garminconnect import Garmin
from models import HeartRateAnalyzer

# Load environment variables
load_dotenv('env.local')

def test_activity_collection():
    """Test collecting activities for a specific date."""
    
    # Initialize Garmin API
    api = Garmin(os.getenv('GARMIN_EMAIL'), os.getenv('GARMIN_PASSWORD'))
    
    try:
        # Login
        api.login()
        print("Successfully logged in to Garmin Connect")
        
        # Test date
        test_date = '2025-07-02'
        
        # Get activities for the date
        activities = api.get_activities_fordate(test_date)
        print(f"\nActivities for {test_date}:")
        print(json.dumps(activities, indent=2))
        
        if activities:
            # Test getting detailed activity data for first activity
            first_activity = activities[0]
            activity_id = first_activity.get('activityId')
            
            if activity_id:
                print(f"\nGetting details for activity {activity_id}...")
                activity_details = api.get_activity(activity_id)
                print(json.dumps(activity_details, indent=2))
                
                # Test getting heart rate data for the activity
                print(f"\nGetting HR data for activity {activity_id}...")
                hr_data = api.get_activity_hr_in_timezones(activity_id)
                print(json.dumps(hr_data, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

def test_activity_trimp_calculation():
    """Test TRIMP calculation for activities."""
    
    # Sample activity data structure
    sample_activity = {
        "activityId": "12345",
        "activityName": "Morning Run",
        "activityType": {"typeKey": "running"},
        "startTimeLocal": "2025-07-02 06:00:00",
        "duration": 3600,  # 1 hour in seconds
        "distance": 10000,  # 10km in meters
        "elevationGain": 100,
        "averageHR": 140,
        "maxHR": 165
    }
    
    # Sample heart rate data (would come from get_activity_hr_in_timezones)
    sample_hr_data = {
        "heartRateValues": [
            [1751410800000, 120],  # [timestamp, hr]
            [1751410860000, 125],
            [1751410920000, 130],
            [1751410980000, 135],
            [1751411040000, 140],
            [1751411100000, 145],
            [1751411160000, 150],
            [1751411220000, 155],
            [1751411280000, 160],
            [1751411340000, 165]
        ]
    }
    
    # Initialize analyzer
    analyzer = HeartRateAnalyzer(resting_hr=48, max_hr=167)
    
    # Calculate TRIMP
    results = analyzer.analyze_heart_rate_data(sample_hr_data)
    
    print("Sample Activity TRIMP Calculation:")
    print(f"Activity: {sample_activity['activityName']}")
    print(f"Duration: {sample_activity['duration']} seconds")
    print(f"Total TRIMP: {results['total_trimp']:.2f}")
    print(f"Presentation Buckets: {json.dumps(results['presentation_buckets'], indent=2)}")

if __name__ == "__main__":
    print("=== Testing Activity Collection ===")
    test_activity_collection()
    
    print("\n=== Testing Activity TRIMP Calculation ===")
    test_activity_trimp_calculation() 