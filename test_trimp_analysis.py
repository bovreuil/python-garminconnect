#!/usr/bin/env python3
"""
Test script to analyze TRIMP calculations by comparing activity HR data with daily HR data.
"""

import json
import sqlite3
from datetime import datetime
from models import HeartRateAnalyzer

def get_db_connection():
    """Get database connection."""
    return sqlite3.connect('garmin_hr.db')

def analyze_activity_trimp(activity_id, target_date):
    """Analyze TRIMP for a specific activity and compare with daily HR data."""
    print(f"\n=== Analyzing Activity {activity_id} for {target_date} ===")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get activity data
    cur.execute("""
        SELECT activity_name, start_time_local, duration_seconds, raw_activity_data, total_trimp
        FROM activities 
        WHERE activity_id = ? AND date = ?
    """, (activity_id, target_date))
    
    activity_result = cur.fetchone()
    if not activity_result:
        print(f"Activity {activity_id} not found for {target_date}")
        return
    
    activity_name, start_time_local, duration_seconds, raw_activity_data, stored_trimp = activity_result
    print(f"Activity: {activity_name}")
    print(f"Start time: {start_time_local}")
    print(f"Duration: {duration_seconds} seconds ({duration_seconds/60:.1f} minutes)")
    print(f"Stored TRIMP: {stored_trimp}")
    
    # Parse activity data
    activity_details = json.loads(raw_activity_data)
    
    # Get daily HR data
    cur.execute("SELECT raw_hr_data FROM heart_rate_data WHERE date = ?", (target_date,))
    daily_hr_result = cur.fetchone()
    if not daily_hr_result:
        print(f"No daily HR data found for {target_date}")
        return
    
    daily_hr_data = json.loads(daily_hr_result[0])
    
    # Extract activity HR time series
    activity_hr_series = []
    if 'activityDetailMetrics' in activity_details:
        activity_metrics = activity_details['activityDetailMetrics']
        if activity_metrics:
            # Find HR and timestamp positions (using fallback method)
            position_data = {}
            for entry in activity_metrics:
                if 'metrics' in entry:
                    metrics = entry['metrics']
                    for pos, value in enumerate(metrics):
                        if pos not in position_data:
                            position_data[pos] = []
                        if value is not None:
                            position_data[pos].append(value)
            
            # Find HR position (values in 48-167 range, excluding GPS)
            hr_candidates = []
            for pos, values in position_data.items():
                if values and min(values) >= 48 and max(values) <= 167:
                    if not (min(values) >= 51.4 and max(values) <= 51.5):  # Exclude GPS
                        unique_count = len(set(values))
                        if unique_count > 5:
                            hr_candidates.append((pos, unique_count, min(values), max(values)))
            
            # Find timestamp position
            ts_candidates = []
            for pos, values in position_data.items():
                if values and min(values) > 1000000000000:
                    unique_count = len(set(values))
                    if unique_count > 100:
                        ts_candidates.append((pos, unique_count, min(values), max(values)))
            
            if hr_candidates and ts_candidates:
                hr_pos = hr_candidates[0][0]
                ts_pos = ts_candidates[0][0]
                
                print(f"HR position: {hr_pos}, Timestamp position: {ts_pos}")
                
                # Extract HR time series
                for entry in activity_metrics:
                    if 'metrics' in entry and len(entry['metrics']) > max(hr_pos, ts_pos):
                        metrics = entry['metrics']
                        timestamp = metrics[ts_pos]
                        hr_value = metrics[hr_pos]
                        
                        if timestamp is not None and hr_value is not None:
                            activity_hr_series.append([timestamp, int(hr_value)])
    
    if not activity_hr_series:
        print("No activity HR data found")
        return
    
    print(f"Activity HR data points: {len(activity_hr_series)}")
    
    # Calculate activity TRIMP
    analyzer = HeartRateAnalyzer(48, 167)  # Your HR parameters
    activity_hr_data = {'heartRateValues': activity_hr_series}
    activity_analysis = analyzer.analyze_heart_rate_data(activity_hr_data)
    activity_trimp = activity_analysis['total_trimp']
    
    print(f"Calculated activity TRIMP: {activity_trimp:.2f}")
    
    # Get activity time window
    if activity_hr_series:
        activity_start_ts = min(point[0] for point in activity_hr_series)
        activity_end_ts = max(point[0] for point in activity_hr_series)
        
        print(f"Activity time window: {activity_start_ts} to {activity_end_ts}")
        
        # Extract daily HR data for activity time window
        daily_hr_window = []
        for timestamp, hr_value in daily_hr_data:
            if activity_start_ts <= timestamp <= activity_end_ts:
                daily_hr_window.append([timestamp, hr_value])
        
        print(f"Daily HR data points in activity window: {len(daily_hr_window)}")
        
        if daily_hr_window:
            # Calculate daily HR TRIMP for the same time window
            daily_hr_data_window = {'heartRateValues': daily_hr_window}
            daily_analysis = analyzer.analyze_heart_rate_data(daily_hr_data_window)
            daily_trimp = daily_analysis['total_trimp']
            
            print(f"Daily HR TRIMP for activity window: {daily_trimp:.2f}")
            
            # Compare
            print(f"\nComparison:")
            print(f"Activity HR TRIMP: {activity_trimp:.2f}")
            print(f"Daily HR TRIMP: {daily_trimp:.2f}")
            print(f"Ratio (Activity/Daily): {activity_trimp/daily_trimp:.2f}")
            
            # Check sampling rates
            if len(activity_hr_series) > 1:
                activity_interval = (activity_hr_series[1][0] - activity_hr_series[0][0]) / 1000
                print(f"Activity HR sampling interval: {activity_interval:.1f} seconds")
            
            if len(daily_hr_window) > 1:
                daily_interval = (daily_hr_window[1][0] - daily_hr_window[0][0]) / 1000
                print(f"Daily HR sampling interval: {daily_interval:.1f} seconds")
    
    conn.close()

def output_hr_comparison_data(activity_id, target_date):
    """Output raw HR data for activity vs daily HR for the same time period."""
    print(f"\n=== HR Data Comparison for Activity {activity_id} on {target_date} ===")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get activity data
    cur.execute("""
        SELECT activity_name, raw_activity_data
        FROM activities 
        WHERE activity_id = ? AND date = ?
    """, (activity_id, target_date))
    
    activity_result = cur.fetchone()
    if not activity_result:
        print(f"Activity {activity_id} not found for {target_date}")
        return
    
    activity_name, raw_activity_data = activity_result
    print(f"Activity: {activity_name}")
    
    # Parse activity data
    activity_details = json.loads(raw_activity_data)
    
    # Get daily HR data
    cur.execute("SELECT raw_hr_data FROM heart_rate_data WHERE date = ?", (target_date,))
    daily_hr_result = cur.fetchone()
    if not daily_hr_result:
        print(f"No daily HR data found for {target_date}")
        return
    
    daily_hr_data = json.loads(daily_hr_result[0])
    
    # Extract activity HR time series
    activity_hr_series = []
    if 'activityDetailMetrics' in activity_details:
        activity_metrics = activity_details['activityDetailMetrics']
        if activity_metrics:
            # Find HR and timestamp positions (using fallback method)
            position_data = {}
            for entry in activity_metrics:
                if 'metrics' in entry:
                    metrics = entry['metrics']
                    for pos, value in enumerate(metrics):
                        if pos not in position_data:
                            position_data[pos] = []
                        if value is not None:
                            position_data[pos].append(value)
            
            # Find HR position (values in 48-167 range, excluding GPS)
            hr_candidates = []
            for pos, values in position_data.items():
                if values and min(values) >= 48 and max(values) <= 167:
                    if not (min(values) >= 51.4 and max(values) <= 51.5):  # Exclude GPS
                        unique_count = len(set(values))
                        if unique_count > 5:
                            hr_candidates.append((pos, unique_count, min(values), max(values)))
            
            # Find timestamp position
            ts_candidates = []
            for pos, values in position_data.items():
                if values and min(values) > 1000000000000:
                    unique_count = len(set(values))
                    if unique_count > 100:
                        ts_candidates.append((pos, unique_count, min(values), max(values)))
            
            if hr_candidates and ts_candidates:
                hr_pos = hr_candidates[0][0]
                ts_pos = ts_candidates[0][0]
                
                # Extract HR time series
                for entry in activity_metrics:
                    if 'metrics' in entry and len(entry['metrics']) > max(hr_pos, ts_pos):
                        metrics = entry['metrics']
                        timestamp = metrics[ts_pos]
                        hr_value = metrics[hr_pos]
                        
                        if timestamp is not None and hr_value is not None:
                            activity_hr_series.append([timestamp, int(hr_value)])
    
    if not activity_hr_series:
        print("No activity HR data found")
        return
    
    # Get activity time window
    activity_start_ts = min(point[0] for point in activity_hr_series)
    activity_end_ts = max(point[0] for point in activity_hr_series)
    
    # Extract daily HR data for activity time window
    daily_hr_window = []
    for timestamp, hr_value in daily_hr_data:
        if activity_start_ts <= timestamp <= activity_end_ts:
            daily_hr_window.append([timestamp, hr_value])
    
    # Convert timestamps to readable format
    def timestamp_to_readable(ts):
        return datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\nActivity HR Data ({len(activity_hr_series)} points):")
    print("Timestamp,HR")
    for ts, hr in activity_hr_series[:10]:  # First 10 points
        print(f"{timestamp_to_readable(ts)},{hr}")
    if len(activity_hr_series) > 10:
        print("...")
        for ts, hr in activity_hr_series[-10:]:  # Last 10 points
            print(f"{timestamp_to_readable(ts)},{hr}")
    
    print(f"\nDaily HR Data for Activity Window ({len(daily_hr_window)} points):")
    print("Timestamp,HR")
    for ts, hr in daily_hr_window[:10]:  # First 10 points
        print(f"{timestamp_to_readable(ts)},{hr}")
    if len(daily_hr_window) > 10:
        print("...")
        for ts, hr in daily_hr_window[-10:]:  # Last 10 points
            print(f"{timestamp_to_readable(ts)},{hr}")
    
    # Output full data to files for Excel import
    activity_filename = f"activity_{activity_id}_hr_data.csv"
    daily_filename = f"daily_{activity_id}_hr_data.csv"
    
    with open(activity_filename, 'w') as f:
        f.write("Timestamp,HR\n")
        for ts, hr in activity_hr_series:
            f.write(f"{timestamp_to_readable(ts)},{hr}\n")
    
    with open(daily_filename, 'w') as f:
        f.write("Timestamp,HR\n")
        for ts, hr in daily_hr_window:
            f.write(f"{timestamp_to_readable(ts)},{hr}\n")
    
    print(f"\nFull data exported to:")
    print(f"  Activity HR: {activity_filename}")
    print(f"  Daily HR: {daily_filename}")
    
    # Summary statistics
    activity_hr_values = [point[1] for point in activity_hr_series]
    daily_hr_values = [point[1] for point in daily_hr_window]
    
    print(f"\nSummary Statistics:")
    print(f"Activity HR: min={min(activity_hr_values)}, max={max(activity_hr_values)}, mean={sum(activity_hr_values)/len(activity_hr_values):.1f}")
    print(f"Daily HR: min={min(daily_hr_values)}, max={max(daily_hr_values)}, mean={sum(daily_hr_values)/len(daily_hr_values):.1f}")
    
    conn.close()

def main():
    """Main function to analyze multiple activities."""
    print("TRIMP Analysis - Comparing Activity vs Daily HR Data")
    
    # Analyze the three activities from the logs
    activities_to_analyze = [
        ("19611720955", "2025-07-02"),  # Morning mobility & first Rope Flow
        ("19614024984", "2025-07-02"),  # Walk up One Tree Hill
        ("19621118007", "2025-07-03"),  # Southwark Running
    ]
    
    for activity_id, target_date in activities_to_analyze:
        analyze_activity_trimp(activity_id, target_date)
        output_hr_comparison_data(activity_id, target_date)

if __name__ == "__main__":
    main() 