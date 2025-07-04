#!/usr/bin/env python3
"""
Test script to check activities API using database credentials
"""

import os
import json
import sqlite3
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from garminconnect import Garmin
import math

# Load environment variables
load_dotenv('env.local')

def get_db_connection():
    """Create a SQLite database connection."""
    conn = sqlite3.connect('garmin_hr.db')
    conn.row_factory = sqlite3.Row
    return conn

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a password using Fernet."""
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("Encryption key not found")
    cipher_suite = Fernet(key.encode())
    return cipher_suite.decrypt(encrypted_password.encode()).decode()

def test_activities_api():
    """Test the activities API using database credentials."""
    
    # Get credentials from database
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT email, password_encrypted FROM garmin_credentials LIMIT 1")
    creds = cur.fetchone()
    
    if not creds:
        print("No Garmin credentials found in database")
        return
    
    # Decrypt password
    password = decrypt_password(creds['password_encrypted'])
    
    print(f"Using credentials for: {creds['email']}")
    
    # Initialize Garmin API
    api = Garmin(creds['email'], password)
    
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
        
        if activities:
            if isinstance(activities, dict):
                print(f"Activities dict keys: {list(activities.keys())}")
                if 'ActivitiesForDay' in activities:
                    activities_response = activities['ActivitiesForDay']
                    print(f"ActivitiesForDay type: {type(activities_response)}")
                    print(f"ActivitiesForDay keys: {list(activities_response.keys()) if isinstance(activities_response, dict) else 'Not a dict'}")
                    
                    if isinstance(activities_response, dict):
                        print(f"Status code: {activities_response.get('statusCode')}")
                        print(f"Successful: {activities_response.get('successful')}")
                        print(f"Error message: {activities_response.get('errorMessage')}")
                        
                        payload = activities_response.get('payload')
                        if payload:
                            print(f"Payload type: {type(payload)}")
                            print(f"Payload: {json.dumps(payload, indent=2)}")
                            
                            if isinstance(payload, list):
                                print(f"Payload is a list with {len(payload)} items")
                                for i, item in enumerate(payload):
                                    print(f"Payload item {i}: {item}")
                            elif isinstance(payload, dict):
                                print(f"Payload is a dict with keys: {list(payload.keys())}")
                        else:
                            print("No payload found")
                else:
                    print("No 'ActivitiesForDay' key found")
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
    finally:
        cur.close()
        conn.close()

def test_hr_data_structure():
    """Test the structure of HR data returned by the Garmin API."""
    print(f"\n=== Testing HR data structure ===")
    
    # Get credentials from database
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT email, password_encrypted FROM garmin_credentials LIMIT 1")
    creds = cur.fetchone()
    
    if not creds:
        print("No Garmin credentials found in database")
        return
    
    # Decrypt password
    password = decrypt_password(creds['password_encrypted'])
    
    # Initialize Garmin API
    api = Garmin(creds['email'], password)
    
    try:
        # Login
        api.login()
        print("Successfully logged in to Garmin Connect")
        
        # Test activity ID from the database
        activity_id = '19611720955'  # Morning mobility activity
        
        print(f"Getting HR data for activity {activity_id} using get_activity_details")
        details = api.get_activity_details(activity_id)
        print(f"Details type: {type(details)}")
        if isinstance(details, dict):
            print(f"Details keys: {list(details.keys())}")
            # Print first 10 metrics arrays from activityDetailMetrics
            if 'activityDetailMetrics' in details:
                adm = details['activityDetailMetrics']
                print(f"activityDetailMetrics type: {type(adm)} length: {len(adm) if hasattr(adm, '__len__') else 'N/A'}")
                if isinstance(adm, list) and len(adm) > 0:
                    print("First 10 metrics arrays from activityDetailMetrics:")
                    for i, entry in enumerate(adm[:10]):
                        print(f"  metrics[{i}]: {entry['metrics']}")
                else:
                    print("activityDetailMetrics is empty or not a list")
            else:
                print("No 'activityDetailMetrics' key in details")
            # Print first few entries of heartRateDTOs
            if 'heartRateDTOs' in details:
                hrdto = details['heartRateDTOs']
                print(f"heartRateDTOs type: {type(hrdto)} length: {len(hrdto) if hasattr(hrdto, '__len__') else 'N/A'}")
                if isinstance(hrdto, list) and len(hrdto) > 0:
                    print(f"First 2 heartRateDTOs: {json.dumps(hrdto[:2], indent=2)}")
                else:
                    print("heartRateDTOs is empty or not a list")
            else:
                print("No 'heartRateDTOs' key in details")
        else:
            print("Details is not a dict")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
    finally:
        cur.close()
        conn.close()

def check_activities_in_db():
    """Check what activities are stored in the database."""
    print(f"\n=== Checking activities in database ===")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check activities for 2025-07-02
    cur.execute("""
        SELECT activity_id, activity_name, total_trimp, presentation_buckets, 
               individual_hr_buckets, trimp_data, duration_seconds
        FROM activities 
        WHERE date = '2025-07-02'
        ORDER BY start_time_local
    """)
    
    activities = cur.fetchall()
    
    if not activities:
        print("No activities found for 2025-07-02")
        return
    
    print(f"Found {len(activities)} activities for 2025-07-02:")
    
    for activity in activities:
        print(f"\nActivity: {activity['activity_name']} (ID: {activity['activity_id']})")
        print(f"  Duration: {activity['duration_seconds']} seconds ({activity['duration_seconds']/60:.1f} minutes)")
        print(f"  Total TRIMP: {activity['total_trimp']}")
        
        if activity['presentation_buckets']:
            try:
                buckets = json.loads(activity['presentation_buckets'])
                print(f"  Presentation buckets:")
                for bucket, data in buckets.items():
                    print(f"    {bucket}: TRIMP={data.get('trimp', 0):.2f}, Minutes={data.get('minutes', 0):.2f}")
            except Exception as e:
                print(f"  Error parsing presentation_buckets: {e}")
        
        if activity['individual_hr_buckets']:
            try:
                buckets = json.loads(activity['individual_hr_buckets'])
                print(f"  Individual HR buckets:")
                for bucket, data in buckets.items():
                    print(f"    {bucket}: TRIMP={data.get('trimp', 0):.2f}, Minutes={data.get('minutes', 0):.2f}")
            except Exception as e:
                print(f"  Error parsing individual_hr_buckets: {e}")
        
        if activity['trimp_data']:
            try:
                trimp_data = json.loads(activity['trimp_data'])
                print(f"  TRIMP data keys: {list(trimp_data.keys()) if isinstance(trimp_data, dict) else 'Not a dict'}")
            except Exception as e:
                print(f"  Error parsing trimp_data: {e}")
    
    conn.close()

def check_hr_values_causing_overflow():
    """Check what heart rate values are causing the math overflow."""
    print(f"\n=== Checking HR values that could cause overflow ===")
    
    # Get credentials from database
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT email, password_encrypted FROM garmin_credentials LIMIT 1")
    creds = cur.fetchone()
    
    if not creds:
        print("No Garmin credentials found in database")
        return
    
    # Decrypt password
    password = decrypt_password(creds['password_encrypted'])
    
    # Initialize Garmin API
    api = Garmin(creds['email'], password)
    
    try:
        # Login
        api.login()
        print("Successfully logged in to Garmin Connect")
        
        # Test activity ID from the database
        activity_id = "19611720955"
        
        # Get activity details
        activity_details = api.get_activity_details(activity_id)
        
        if activity_details and 'activityDetailMetrics' in activity_details:
            activity_metrics = activity_details['activityDetailMetrics']
            
            # Extract heart rate values and check for potential overflow
            hr_values = []
            for metric_entry in activity_metrics:
                if 'metrics' in metric_entry and len(metric_entry['metrics']) > 8:
                    metrics = metric_entry['metrics']
                    heart_rate = metrics[0]  # heart rate at index 0
                    timestamp = metrics[8]  # timestamp at index 8
                    
                    if timestamp and heart_rate and heart_rate >= 80:
                        hr_values.append(int(heart_rate))
            
            print(f"Extracted {len(hr_values)} HR values")
            print(f"HR range: {min(hr_values)} - {max(hr_values)}")
            print(f"Unique HR values: {sorted(set(hr_values))}")
            
            # Check which values could cause overflow
            resting_hr = 48
            max_hr = 167
            hr_reserve = max_hr - resting_hr
            
            print(f"\nChecking for overflow with resting_hr={resting_hr}, max_hr={max_hr}")
            
            for hr in sorted(set(hr_values)):
                if hr <= resting_hr:
                    hr_reserve_ratio = 0.0
                else:
                    hr_reserve_ratio = (hr - resting_hr) / hr_reserve
                
                y = 1.92 * hr_reserve_ratio
                
                print(f"HR {hr}: ratio={hr_reserve_ratio:.3f}, y={y:.3f}")
                
                if y > 700:  # math.exp(700) is approximately the limit
                    print(f"  *** OVERFLOW RISK: y={y:.3f} > 700 ***")
                else:
                    try:
                        exp_y = math.exp(y)
                        print(f"  exp(y)={exp_y:.2e}")
                    except OverflowError:
                        print(f"  *** OVERFLOW ERROR ***")
    
    except Exception as e:
        print(f"Error: {e}")
    
    conn.close()

def compare_daily_vs_activity_hr():
    """Compare daily heart rate data with activity heart rate data."""
    print(f"\n=== Comparing Daily vs Activity HR Data ===")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get daily heart rate data for 2025-07-02
    cur.execute("""
        SELECT raw_hr_data 
        FROM heart_rate_data 
        WHERE date = '2025-07-02'
    """)
    
    daily_result = cur.fetchone()
    if not daily_result:
        print("No daily heart rate data found for 2025-07-02")
        return
    
    daily_hr_data = json.loads(daily_result['raw_hr_data'])
    print(f"Daily HR data: {len(daily_hr_data)} points")
    print(f"Daily HR range: {min([p[1] for p in daily_hr_data])} - {max([p[1] for p in daily_hr_data])}")
    print(f"Daily HR sample times: {daily_hr_data[0][0]} to {daily_hr_data[-1][0]}")
    
    # Get activities for 2025-07-02
    cur.execute("""
        SELECT activity_id, activity_name, start_time_local, duration_seconds, 
               raw_activity_data, total_trimp, presentation_buckets
        FROM activities 
        WHERE date = '2025-07-02'
        ORDER BY start_time_local
    """)
    
    activities = cur.fetchall()
    
    for activity in activities:
        print(f"\n--- Activity: {activity['activity_name']} ---")
        print(f"Start time: {activity['start_time_local']}")
        print(f"Duration: {activity['duration_seconds']} seconds ({activity['duration_seconds']/60:.1f} minutes)")
        print(f"Total TRIMP: {activity['total_trimp']}")
        
        # Parse activity details
        activity_details = json.loads(activity['raw_activity_data'])
        
        if 'activityDetailMetrics' in activity_details:
            activity_metrics = activity_details['activityDetailMetrics']
            
            # Extract heart rate time series from activity
            activity_hr_data = []
            for metric_entry in activity_metrics:
                if 'metrics' in metric_entry and len(metric_entry['metrics']) > 8:
                    metrics = metric_entry['metrics']
                    heart_rate = metrics[0]  # heart rate at index 0
                    timestamp = metrics[8]  # timestamp at index 8
                    
                    if timestamp and heart_rate and 80 <= heart_rate <= 200:
                        activity_hr_data.append([timestamp, int(heart_rate)])
            
            print(f"Activity HR data: {len(activity_hr_data)} points")
            if activity_hr_data:
                print(f"Activity HR range: {min([p[1] for p in activity_hr_data])} - {max([p[1] for p in activity_hr_data])}")
                print(f"Activity HR sample times: {activity_hr_data[0][0]} to {activity_hr_data[-1][0]}")
                
                # Convert timestamps to datetime for comparison
                import datetime
                
                # Activity start time
                activity_start = datetime.datetime.fromisoformat(activity['start_time_local'].replace('Z', '+00:00'))
                activity_start_ts = activity_start.timestamp() * 1000  # Convert to milliseconds
                
                # Find daily HR data points that overlap with activity time
                activity_end_ts = activity_start_ts + (activity['duration_seconds'] * 1000)
                
                overlapping_daily_hr = []
                for daily_point in daily_hr_data:
                    daily_ts = daily_point[0]
                    if activity_start_ts <= daily_ts <= activity_end_ts:
                        overlapping_daily_hr.append(daily_point)
                
                print(f"Overlapping daily HR points: {len(overlapping_daily_hr)}")
                if overlapping_daily_hr:
                    print(f"Overlapping daily HR range: {min([p[1] for p in overlapping_daily_hr])} - {max([p[1] for p in overlapping_daily_hr])}")
                    
                    # Compare a few sample points
                    print(f"\nSample comparison (first 5 overlapping points):")
                    for i, daily_point in enumerate(overlapping_daily_hr[:5]):
                        daily_ts, daily_hr = daily_point
                        print(f"  Daily: {datetime.datetime.fromtimestamp(daily_ts/1000)} HR={daily_hr}")
                        
                        # Find closest activity HR point
                        closest_activity = min(activity_hr_data, key=lambda x: abs(x[0] - daily_ts))
                        activity_ts, activity_hr = closest_activity
                        print(f"  Activity: {datetime.datetime.fromtimestamp(activity_ts/1000)} HR={activity_hr}")
                        print()
        
        # Show presentation buckets
        if activity['presentation_buckets']:
            try:
                buckets = json.loads(activity['presentation_buckets'])
                print(f"Presentation buckets:")
                for bucket, data in buckets.items():
                    print(f"  {bucket}: TRIMP={data.get('trimp', 0):.2f}, Minutes={data.get('minutes', 0):.2f}")
            except Exception as e:
                print(f"Error parsing presentation_buckets: {e}")
    
    conn.close()

def analyze_activity_metrics_series():
    """Analyze all data series in activity metrics to identify heart rate and timestamp data."""
    print(f"\n=== Analyzing Activity Metrics Series ===")
    
    # Get credentials from database
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT email, password_encrypted FROM garmin_credentials LIMIT 1")
    creds = cur.fetchone()
    
    if not creds:
        print("No Garmin credentials found in database")
        return
    
    # Decrypt password
    password = decrypt_password(creds['password_encrypted'])
    
    # Initialize Garmin API
    api = Garmin(creds['email'], password)
    
    try:
        # Login
        api.login()
        print("Successfully logged in to Garmin Connect")
        
        # Test both activities
        activity_ids = ["19611720955", "19614024984"]
        
        for activity_id in activity_ids:
            print(f"\n--- Activity {activity_id} ---")
            
            # Get activity details
            activity_details = api.get_activity_details(activity_id)
            
            if activity_details and 'activityDetailMetrics' in activity_details:
                activity_metrics = activity_details['activityDetailMetrics']
                
                if not activity_metrics:
                    print("No activityDetailMetrics found")
                    continue
                
                print(f"Found {len(activity_metrics)} metric entries")
                
                # Analyze the first few entries to understand the structure
                sample_entries = activity_metrics[:5]
                
                for i, entry in enumerate(sample_entries):
                    if 'metrics' in entry:
                        metrics = entry['metrics']
                        print(f"\nEntry {i}: {len(metrics)} values")
                        print(f"  Raw metrics: {metrics}")
                        
                        # Analyze each position in the metrics array
                        for pos, value in enumerate(metrics):
                            if value is not None:
                                print(f"    Position {pos}: {value} (type: {type(value).__name__})")
                
                # Now analyze all entries to find patterns
                print(f"\n--- Analyzing all {len(activity_metrics)} entries ---")
                
                # Collect all values for each position
                position_data = {}
                for entry in activity_metrics:
                    if 'metrics' in entry:
                        metrics = entry['metrics']
                        for pos, value in enumerate(metrics):
                            if pos not in position_data:
                                position_data[pos] = []
                            if value is not None:
                                position_data[pos].append(value)
                
                # Analyze each position
                for pos in sorted(position_data.keys()):
                    values = position_data[pos]
                    if values:
                        unique_values = list(set(values))
                        unique_values.sort()
                        
                        print(f"\nPosition {pos}:")
                        print(f"  Total values: {len(values)}")
                        print(f"  Unique values: {len(unique_values)}")
                        print(f"  Range: {min(values)} to {max(values)}")
                        print(f"  Sample values: {unique_values[:10]}{'...' if len(unique_values) > 10 else ''}")
                        
                        # Check if this looks like heart rate data (50-120 range)
                        if min(values) >= 50 and max(values) <= 120:
                            print(f"  *** POTENTIAL HEART RATE DATA ***")
                        
                        # Check if this looks like timestamp data (large numbers around 1751410800000)
                        if min(values) > 1000000000000:  # Timestamps are in milliseconds since epoch
                            print(f"  *** POTENTIAL TIMESTAMP DATA ***")
                            # Convert to readable dates
                            import datetime
                            min_date = datetime.datetime.fromtimestamp(min(values)/1000)
                            max_date = datetime.datetime.fromtimestamp(max(values)/1000)
                            print(f"  Date range: {min_date} to {max_date}")
                        
                        # Check if this looks like seconds data (small integers)
                        if all(isinstance(v, (int, float)) and 0 <= v <= 10000 for v in values):
                            print(f"  *** POTENTIAL SECONDS/COUNTER DATA ***")
                        
                        # Check if this looks like distance data (small floats)
                        if all(isinstance(v, (int, float)) and 0 <= v <= 1000 for v in values):
                            print(f"  *** POTENTIAL DISTANCE/SPEED DATA ***")
                
                # Look for patterns in the data
                print(f"\n--- Pattern Analysis ---")
                
                # Find the most likely heart rate series (values 50-120, many unique values)
                hr_candidates = []
                for pos, values in position_data.items():
                    if values and min(values) >= 50 and max(values) <= 120:
                        unique_count = len(set(values))
                        if unique_count > 10:  # Should have many different heart rate values
                            hr_candidates.append((pos, unique_count, min(values), max(values)))
                
                if hr_candidates:
                    print(f"Heart rate candidates:")
                    for pos, unique_count, min_val, max_val in sorted(hr_candidates, key=lambda x: x[1], reverse=True):
                        print(f"  Position {pos}: {unique_count} unique values, range {min_val}-{max_val}")
                
                # Find the most likely timestamp series (large numbers, increasing)
                ts_candidates = []
                for pos, values in position_data.items():
                    if values and min(values) > 1000000000000:
                        # Check if values are generally increasing (timestamps should increase)
                        sorted_values = sorted(values)
                        if sorted_values == values or len(set(values)) > 100:  # Many unique timestamps
                            ts_candidates.append((pos, len(set(values)), min(values), max(values)))
                
                if ts_candidates:
                    print(f"Timestamp candidates:")
                    for pos, unique_count, min_val, max_val in sorted(ts_candidates, key=lambda x: x[1], reverse=True):
                        print(f"  Position {pos}: {unique_count} unique values, range {min_val}-{max_val}")
                        import datetime
                        min_date = datetime.datetime.fromtimestamp(min_val/1000)
                        max_date = datetime.datetime.fromtimestamp(max_val/1000)
                        print(f"    Date range: {min_date} to {max_date}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    conn.close()

def analyze_all_activity_series():
    """Analyze all data series in both activities to identify heart rate and timestamp data."""
    print(f"\n=== Comprehensive Activity Series Analysis ===")
    
    # Get credentials from database
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT email, password_encrypted FROM garmin_credentials LIMIT 1")
    creds = cur.fetchone()
    
    if not creds:
        print("No Garmin credentials found in database")
        return
    
    # Decrypt password
    password = decrypt_password(creds['password_encrypted'])
    
    # Initialize Garmin API
    api = Garmin(creds['email'], password)
    
    try:
        # Login
        api.login()
        print("Successfully logged in to Garmin Connect")
        
        # Test both activities
        activity_ids = ["19611720955", "19614024984"]
        activity_names = ["Morning mobility & first Rope Flow", "Walk up One Tree Hill"]
        
        for i, activity_id in enumerate(activity_ids):
            print(f"\n{'='*80}")
            print(f"ACTIVITY {i+1}: {activity_names[i]} (ID: {activity_id})")
            print(f"{'='*80}")
            
            # Get activity details
            activity_details = api.get_activity_details(activity_id)
            
            if activity_details and 'activityDetailMetrics' in activity_details:
                activity_metrics = activity_details['activityDetailMetrics']
                
                if not activity_metrics:
                    print("No activityDetailMetrics found")
                    continue
                
                print(f"Found {len(activity_metrics)} metric entries")
                
                # Collect all values for each position
                position_data = {}
                for entry in activity_metrics:
                    if 'metrics' in entry:
                        metrics = entry['metrics']
                        for pos, value in enumerate(metrics):
                            if pos not in position_data:
                                position_data[pos] = []
                            if value is not None:
                                position_data[pos].append(value)
                
                # Analyze each position
                print(f"\n{'Position':<8} {'Count':<8} {'Min':<15} {'Max':<15} {'Type':<20} {'Constraints':<30}")
                print("-" * 100)
                
                for pos in sorted(position_data.keys()):
                    values = position_data[pos]
                    if values:
                        count = len(values)
                        min_val = min(values)
                        max_val = max(values)
                        
                        # Determine data type and check constraints
                        data_type = "Unknown"
                        constraints = []
                        
                        # Check if this looks like timestamp data
                        if min_val > 1000000000000:  # Timestamps are in milliseconds since epoch
                            data_type = "Timestamp"
                            if 1751410800000 <= min_val <= 1751497080000 and 1751410800000 <= max_val <= 1751497080000:
                                constraints.append("✓ Timestamp range OK")
                            else:
                                constraints.append("✗ Timestamp range OUTSIDE")
                        
                        # Check if this looks like heart rate data
                        elif min_val >= 50 and max_val <= 120:
                            data_type = "Heart Rate"
                            constraints.append("✓ HR range OK")
                        elif min_val >= 40 and max_val <= 200:
                            data_type = "Heart Rate (extended)"
                            constraints.append("⚠ HR range extended")
                        
                        # Check if this looks like seconds/counter data
                        elif all(isinstance(v, (int, float)) and 0 <= v <= 10000 for v in values):
                            data_type = "Seconds/Counter"
                            constraints.append("Small integers")
                        
                        # Check if this looks like distance/speed data
                        elif all(isinstance(v, (int, float)) and 0 <= v <= 1000 for v in values):
                            data_type = "Distance/Speed"
                            constraints.append("Small floats")
                        
                        # Check if this looks like percentage data
                        elif all(isinstance(v, (int, float)) and 0 <= v <= 100 for v in values):
                            data_type = "Percentage"
                            constraints.append("0-100 range")
                        
                        # Check if this looks like boolean data
                        elif all(v in [0, 1, True, False] for v in values):
                            data_type = "Boolean"
                            constraints.append("0/1 values")
                        
                        # Check if this looks like null/zero data
                        elif all(v == 0 or v is None for v in values):
                            data_type = "Null/Zero"
                            constraints.append("All zeros")
                        
                        else:
                            data_type = "Other"
                            constraints.append(f"Range {min_val:.2f}-{max_val:.2f}")
                        
                        # Format output
                        min_str = f"{min_val:.2f}" if isinstance(min_val, float) else str(min_val)
                        max_str = f"{max_val:.2f}" if isinstance(max_val, float) else str(max_val)
                        constraints_str = ", ".join(constraints)
                        
                        print(f"{pos:<8} {count:<8} {min_str:<15} {max_str:<15} {data_type:<20} {constraints_str}")
                
                # Summary of findings
                print(f"\n{'='*80}")
                print(f"SUMMARY FOR {activity_names[i]}")
                print(f"{'='*80}")
                
                # Find best timestamp candidates
                ts_candidates = []
                for pos, values in position_data.items():
                    if values and min(values) > 1000000000000:
                        if 1751410800000 <= min(values) <= 1751497080000 and 1751410800000 <= max(values) <= 1751497080000:
                            ts_candidates.append((pos, len(values), min(values), max(values)))
                
                if ts_candidates:
                    print(f"TIMESTAMP CANDIDATES ({len(ts_candidates)}):")
                    for pos, count, min_ts, max_ts in sorted(ts_candidates, key=lambda x: x[1], reverse=True):
                        import datetime
                        min_date = datetime.datetime.fromtimestamp(min_ts/1000)
                        max_date = datetime.datetime.fromtimestamp(max_ts/1000)
                        print(f"  Position {pos}: {count} values, {min_date} to {max_date}")
                else:
                    print("NO VALID TIMESTAMP CANDIDATES FOUND")
                
                # Find best heart rate candidates
                hr_candidates = []
                for pos, values in position_data.items():
                    if values and min(values) >= 50 and max(values) <= 120:
                        unique_count = len(set(values))
                        if unique_count > 5:  # Should have many different heart rate values
                            hr_candidates.append((pos, unique_count, min(values), max(values)))
                
                if hr_candidates:
                    print(f"\nHEART RATE CANDIDATES ({len(hr_candidates)}):")
                    for pos, unique_count, min_hr, max_hr in sorted(hr_candidates, key=lambda x: x[1], reverse=True):
                        print(f"  Position {pos}: {unique_count} unique values, range {min_hr}-{max_hr}")
                else:
                    print("\nNO VALID HEART RATE CANDIDATES FOUND")
                
                # Show sample data for top candidates
                if ts_candidates and hr_candidates:
                    print(f"\nSAMPLE DATA (first 5 entries):")
                    best_ts_pos = ts_candidates[0][0]
                    best_hr_pos = hr_candidates[0][0]
                    
                    for j, entry in enumerate(activity_metrics[:5]):
                        if 'metrics' in entry and len(entry['metrics']) > max(best_ts_pos, best_hr_pos):
                            metrics = entry['metrics']
                            ts_val = metrics[best_ts_pos] if best_ts_pos < len(metrics) else "N/A"
                            hr_val = metrics[best_hr_pos] if best_hr_pos < len(metrics) else "N/A"
                            
                            if ts_val != "N/A":
                                import datetime
                                ts_date = datetime.datetime.fromtimestamp(ts_val/1000)
                                print(f"  Entry {j}: TS={ts_date} ({ts_val}), HR={hr_val}")
                            else:
                                print(f"  Entry {j}: TS={ts_val}, HR={hr_val}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    conn.close()

def analyze_stored_activity_data():
    """Analyze the activity data already stored in the database."""
    print(f"\n=== Analyzing Stored Activity Data ===")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get activities for 2025-07-02
    cur.execute("""
        SELECT activity_id, activity_name, raw_activity_data, total_trimp, presentation_buckets
        FROM activities 
        WHERE date = '2025-07-02'
        ORDER BY start_time_local
    """)
    
    activities = cur.fetchall()
    
    if not activities:
        print("No activities found for 2025-07-02")
        return
    
    for activity in activities:
        print(f"\n{'='*80}")
        print(f"ACTIVITY: {activity['activity_name']} (ID: {activity['activity_id']})")
        print(f"{'='*80}")
        
        # Parse the raw activity data
        try:
            activity_details = json.loads(activity['raw_activity_data'])
            
            if 'activityDetailMetrics' in activity_details:
                activity_metrics = activity_details['activityDetailMetrics']
                
                if not activity_metrics:
                    print("No activityDetailMetrics found")
                    continue
                
                print(f"Found {len(activity_metrics)} metric entries")
                
                # Collect all values for each position
                position_data = {}
                for entry in activity_metrics:
                    if 'metrics' in entry:
                        metrics = entry['metrics']
                        for pos, value in enumerate(metrics):
                            if pos not in position_data:
                                position_data[pos] = []
                            if value is not None:
                                position_data[pos].append(value)
                
                # Analyze each position
                print(f"\n{'Position':<8} {'Count':<8} {'Min':<15} {'Max':<15} {'Type':<20} {'Constraints':<30}")
                print("-" * 100)
                
                for pos in sorted(position_data.keys()):
                    values = position_data[pos]
                    if values:
                        count = len(values)
                        min_val = min(values)
                        max_val = max(values)
                        
                        # Determine data type and check constraints
                        data_type = "Unknown"
                        constraints = []
                        
                        # Check if this looks like timestamp data
                        if min_val > 1000000000000:  # Timestamps are in milliseconds since epoch
                            data_type = "Timestamp"
                            if 1751410800000 <= min_val <= 1751497080000 and 1751410800000 <= max_val <= 1751497080000:
                                constraints.append("✓ Timestamp range OK")
                            else:
                                constraints.append("✗ Timestamp range OUTSIDE")
                        
                        # Check if this looks like heart rate data
                        elif min_val >= 50 and max_val <= 120:
                            data_type = "Heart Rate"
                            constraints.append("✓ HR range OK")
                        elif min_val >= 40 and max_val <= 200:
                            data_type = "Heart Rate (extended)"
                            constraints.append("⚠ HR range extended")
                        
                        # Check if this looks like seconds/counter data
                        elif all(isinstance(v, (int, float)) and 0 <= v <= 10000 for v in values):
                            data_type = "Seconds/Counter"
                            constraints.append("Small integers")
                        
                        # Check if this looks like distance/speed data
                        elif all(isinstance(v, (int, float)) and 0 <= v <= 1000 for v in values):
                            data_type = "Distance/Speed"
                            constraints.append("Small floats")
                        
                        # Check if this looks like percentage data
                        elif all(isinstance(v, (int, float)) and 0 <= v <= 100 for v in values):
                            data_type = "Percentage"
                            constraints.append("0-100 range")
                        
                        # Check if this looks like boolean data
                        elif all(v in [0, 1, True, False] for v in values):
                            data_type = "Boolean"
                            constraints.append("0/1 values")
                        
                        # Check if this looks like null/zero data
                        elif all(v == 0 or v is None for v in values):
                            data_type = "Null/Zero"
                            constraints.append("All zeros")
                        
                        else:
                            data_type = "Other"
                            constraints.append(f"Range {min_val:.2f}-{max_val:.2f}")
                        
                        # Format output
                        min_str = f"{min_val:.2f}" if isinstance(min_val, float) else str(min_val)
                        max_str = f"{max_val:.2f}" if isinstance(max_val, float) else str(max_val)
                        constraints_str = ", ".join(constraints)
                        
                        print(f"{pos:<8} {count:<8} {min_str:<15} {max_str:<15} {data_type:<20} {constraints_str}")
                
                # Summary of findings
                print(f"\n{'='*80}")
                print(f"SUMMARY FOR {activity['activity_name']}")
                print(f"{'='*80}")
                
                # Find best timestamp candidates
                ts_candidates = []
                for pos, values in position_data.items():
                    if values and min(values) > 1000000000000:
                        if 1751410800000 <= min(values) <= 1751497080000 and 1751410800000 <= max(values) <= 1751497080000:
                            ts_candidates.append((pos, len(values), min(values), max(values)))
                
                if ts_candidates:
                    print(f"TIMESTAMP CANDIDATES ({len(ts_candidates)}):")
                    for pos, count, min_ts, max_ts in sorted(ts_candidates, key=lambda x: x[1], reverse=True):
                        import datetime
                        min_date = datetime.datetime.fromtimestamp(min_ts/1000)
                        max_date = datetime.datetime.fromtimestamp(max_ts/1000)
                        print(f"  Position {pos}: {count} values, {min_date} to {max_date}")
                else:
                    print("NO VALID TIMESTAMP CANDIDATES FOUND")
                
                # Find best heart rate candidates
                hr_candidates = []
                for pos, values in position_data.items():
                    if values and min(values) >= 50 and max(values) <= 120:
                        unique_count = len(set(values))
                        if unique_count > 5:  # Should have many different heart rate values
                            hr_candidates.append((pos, unique_count, min(values), max(values)))
                
                if hr_candidates:
                    print(f"\nHEART RATE CANDIDATES ({len(hr_candidates)}):")
                    for pos, unique_count, min_hr, max_hr in sorted(hr_candidates, key=lambda x: x[1], reverse=True):
                        print(f"  Position {pos}: {unique_count} unique values, range {min_hr}-{max_hr}")
                else:
                    print("\nNO VALID HEART RATE CANDIDATES FOUND")
                
                # Show current TRIMP results
                print(f"\nCURRENT TRIMP RESULTS:")
                print(f"  Total TRIMP: {activity['total_trimp']}")
                
                if activity['presentation_buckets']:
                    try:
                        buckets = json.loads(activity['presentation_buckets'])
                        print(f"  Presentation buckets:")
                        for bucket, data in buckets.items():
                            print(f"    {bucket}: TRIMP={data.get('trimp', 0):.2f}, Minutes={data.get('minutes', 0):.2f}")
                    except Exception as e:
                        print(f"  Error parsing presentation_buckets: {e}")
                
                # Show sample data for top candidates
                if ts_candidates and hr_candidates:
                    print(f"\nSAMPLE DATA (first 5 entries):")
                    best_ts_pos = ts_candidates[0][0]
                    best_hr_pos = hr_candidates[0][0]
                    
                    for j, entry in enumerate(activity_metrics[:5]):
                        if 'metrics' in entry and len(entry['metrics']) > max(best_ts_pos, best_hr_pos):
                            metrics = entry['metrics']
                            ts_val = metrics[best_ts_pos] if best_ts_pos < len(metrics) else "N/A"
                            hr_val = metrics[best_hr_pos] if best_hr_pos < len(metrics) else "N/A"
                            
                            if ts_val != "N/A":
                                import datetime
                                ts_date = datetime.datetime.fromtimestamp(ts_val/1000)
                                print(f"  Entry {j}: TS={ts_date} ({ts_val}), HR={hr_val}")
                            else:
                                print(f"  Entry {j}: TS={ts_val}, HR={hr_val}")
        
        except Exception as e:
            print(f"Error parsing activity data: {e}")
    
    conn.close()

def analyze_all_activities_by_type():
    """Analyze all activities in the database and compare structures by activity type."""
    print(f"\n=== Analyzing All Activities by Type ===")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get all activities
    cur.execute("""
        SELECT activity_id, activity_name, activity_type, raw_activity_data
        FROM activities 
        ORDER BY date, start_time_local
    """)
    
    activities = cur.fetchall()
    
    if not activities:
        print("No activities found in database")
        return
    
    # Group by activity type
    activities_by_type = {}
    for activity in activities:
        activity_type = activity['activity_type']
        if activity_type not in activities_by_type:
            activities_by_type[activity_type] = []
        activities_by_type[activity_type].append(activity)
    
    print(f"Found {len(activities)} activities across {len(activities_by_type)} activity types:")
    for activity_type, type_activities in activities_by_type.items():
        print(f"  {activity_type}: {len(type_activities)} activities")
    
    # Analyze each activity type
    for activity_type, type_activities in activities_by_type.items():
        print(f"\n{'='*80}")
        print(f"ACTIVITY TYPE: {activity_type} ({len(type_activities)} activities)")
        print(f"{'='*80}")
        
        for i, activity in enumerate(type_activities):
            print(f"\n--- Activity {i+1}: {activity['activity_name']} (ID: {activity['activity_id']}) ---")
            
            try:
                activity_details = json.loads(activity['raw_activity_data'])
                
                if 'activityDetailMetrics' in activity_details:
                    activity_metrics = activity_details['activityDetailMetrics']
                    
                    if not activity_metrics:
                        print("  No activityDetailMetrics found")
                        continue
                    
                    print(f"  Found {len(activity_metrics)} metric entries")
                    
                    # Analyze the first few entries to understand structure
                    sample_entries = activity_metrics[:3]
                    
                    for j, entry in enumerate(sample_entries):
                        if 'metrics' in entry:
                            metrics = entry['metrics']
                            print(f"    Entry {j}: {len(metrics)} values")
                            
                            # Show first 10 positions with their values
                            for pos in range(min(10, len(metrics))):
                                value = metrics[pos]
                                if value is not None:
                                    print(f"      Position {pos}: {value} (type: {type(value).__name__})")
                    
                    # Find HR and timestamp candidates
                    position_data = {}
                    for entry in activity_metrics:
                        if 'metrics' in entry:
                            metrics = entry['metrics']
                            for pos, value in enumerate(metrics):
                                if pos not in position_data:
                                    position_data[pos] = []
                                if value is not None:
                                    position_data[pos].append(value)
                    
                    # Find HR candidates
                    hr_candidates = []
                    for pos, values in position_data.items():
                        if values and min(values) >= 50 and max(values) <= 200:
                            unique_count = len(set(values))
                            if unique_count > 5:
                                hr_candidates.append((pos, unique_count, min(values), max(values)))
                    
                    # Find timestamp candidates
                    ts_candidates = []
                    for pos, values in position_data.items():
                        if values and min(values) > 1000000000000:
                            unique_count = len(set(values))
                            if unique_count > 100:
                                ts_candidates.append((pos, unique_count, min(values), max(values)))
                    
                    print(f"    HR candidates: {hr_candidates}")
                    print(f"    Timestamp candidates: {ts_candidates}")
                    
                else:
                    print("  No activityDetailMetrics found")
                    
            except Exception as e:
                print(f"  Error parsing activity data: {e}")
    
    conn.close()

if __name__ == "__main__":
    analyze_stored_activity_data() 