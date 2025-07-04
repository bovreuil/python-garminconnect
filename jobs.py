#!/usr/bin/env python3
"""
Background job functions for Garmin Heart Rate Analyzer
"""

import json
import logging
import garminconnect
from database import (
    get_db_connection, 
    decrypt_password, 
    get_user_hr_parameters, 
    update_job_status
)
from datetime import datetime, date, timedelta
from garminconnect import Garmin
from cryptography.fernet import Fernet
import os
from models import HeartRateAnalyzer
from typing import Dict, List, Optional, Tuple
import math
from config import TIME_CONFIG, API_CONFIG


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_hr_and_timestamp_positions(activity_details: Dict) -> Tuple[Optional[int], Optional[int]]:
    """
    Detect HR and timestamp positions using metricDescriptors from activity details.
    
    Args:
        activity_details: Activity details containing metricDescriptors and activityDetailMetrics
        
    Returns:
        Tuple of (heart_rate_position, timestamp_position) or (None, None) if not found
    """
    if not activity_details:
        return None, None
    
    # Get metricDescriptors from activity details
    metric_descriptors = activity_details.get('metricDescriptors', [])
    if not metric_descriptors:
        logger.warning("detect_hr_and_timestamp_positions: No metricDescriptors found in activity details")
        return None, None
    
    logger.info(f"detect_hr_and_timestamp_positions: Found {len(metric_descriptors)} metric descriptors")
    
    # Find HR and timestamp positions using the key
    hr_position = None
    ts_position = None
    
    for descriptor in metric_descriptors:
        metrics_index = descriptor.get('metricsIndex')
        key = descriptor.get('key')
        unit = descriptor.get('unit', {})
        unit_key = unit.get('key', 'unknown')
        factor = unit.get('factor', 1.0)
        
        logger.info(f"detect_hr_and_timestamp_positions: Index {metrics_index}: {key} ({unit_key}, factor={factor})")
        
        # Look for heart rate data
        if key == 'directHeartRate':
            hr_position = metrics_index
            logger.info(f"detect_hr_and_timestamp_positions: Found HR at position {hr_position} (unit: {unit_key}, factor: {factor})")
        
        # Look for timestamp data
        elif key == 'directTimestamp':
            ts_position = metrics_index
            logger.info(f"detect_hr_and_timestamp_positions: Found timestamp at position {ts_position} (unit: {unit_key}, factor: {factor})")
    
    if hr_position is None:
        logger.warning("detect_hr_and_timestamp_positions: No directHeartRate found in metricDescriptors")
    
    if ts_position is None:
        logger.warning("detect_hr_and_timestamp_positions: No directTimestamp found in metricDescriptors")
    
    return hr_position, ts_position

def collect_garmin_data_job(target_date: str, job_id: str):
    """
    Background job to collect heart rate data from Garmin Connect.
    
    Args:
        target_date: Date to collect data for (YYYY-MM-DD)
        job_id: Unique job identifier
    """
    logger.info(f"collect_garmin_data_job: Starting job {job_id} for date {target_date}")
    
    try:
        # Update job status to running
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE background_jobs 
            SET status = 'running', updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ?
        """, (job_id,))
        conn.commit()
        
        # Get Garmin credentials
        cur.execute("SELECT email, password_encrypted FROM garmin_credentials LIMIT 1")
        creds = cur.fetchone()
        
        if not creds:
            error_msg = "No Garmin credentials found"
            logger.error(f"collect_garmin_data_job: {error_msg}")
            cur.execute("""
                UPDATE background_jobs 
                SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (error_msg, job_id))
            conn.commit()
            cur.close()
            conn.close()
            return
        
        # Decrypt password
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            error_msg = "Encryption key not found"
            logger.error(f"collect_garmin_data_job: {error_msg}")
            cur.execute("""
                UPDATE background_jobs 
                SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (error_msg, job_id))
            conn.commit()
            cur.close()
            conn.close()
            return
        
        fernet = Fernet(key.encode())
        password = fernet.decrypt(creds['password_encrypted'].encode()).decode()
        
        logger.info(f"collect_garmin_data_job: Connecting to Garmin with email {creds['email']}")
        
        # Clean up any existing data for this date
        logger.info(f"collect_garmin_data_job: Cleaning up existing data for {target_date}")
        cur.execute("DELETE FROM daily_data WHERE date = ?", (target_date,))
        cur.execute("DELETE FROM activity_data WHERE date = ?", (target_date,))
        conn.commit()
        
        # Connect to Garmin
        api = Garmin(creds['email'], password)
        api.login()
        
        # Get heart rate data
        logger.info(f"collect_garmin_data_job: Fetching heart rate data for {target_date}")
        heart_rate_data = api.get_heart_rates(target_date)
        
        logger.info(f"collect_garmin_data_job: Raw heart rate data received")
        
        # Check if we got valid data
        if not heart_rate_data:
            error_msg = f"No heart rate data returned from Garmin for {target_date}"
            logger.warning(f"collect_garmin_data_job: {error_msg}")
            cur.execute("""
                UPDATE background_jobs 
                SET status = 'completed', result = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (json.dumps({'message': error_msg, 'data_found': False}), job_id))
            conn.commit()
            cur.close()
            conn.close()
            return
        
        # Check if heartRateValues exists and has data
        if 'heartRateValues' not in heart_rate_data:
            error_msg = f"Heart rate data missing 'heartRateValues' for {target_date}"
            logger.warning(f"collect_garmin_data_job: {error_msg}")
            cur.execute("""
                UPDATE background_jobs 
                SET status = 'completed', result = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (json.dumps({'message': error_msg, 'data_found': False}), job_id))
            conn.commit()
            cur.close()
            conn.close()
            return
        
        heart_rate_values = heart_rate_data['heartRateValues']
        logger.info(f"collect_garmin_data_job: Heart rate values: {len(heart_rate_values) if heart_rate_values else 0} points")
        
        # Check if we have daily HR data
        has_daily_hr_data = heart_rate_values and len(heart_rate_values) > 0
        
        if not has_daily_hr_data:
            logger.info(f"collect_garmin_data_job: No daily HR data found for {target_date}, will try to construct from activities")
            # Don't exit early - continue to collect activities
        else:
            # Check for None values in heart rate data
            if any(value is None for value in heart_rate_values):
                error_msg = f"Heart rate data contains None values for {target_date} - no valid data"
                logger.warning(f"collect_garmin_data_job: {error_msg}")
                cur.execute("""
                    UPDATE background_jobs 
                    SET status = 'completed', result = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                """, (json.dumps({'message': error_msg, 'data_found': False}), job_id))
                conn.commit()
                cur.close()
                conn.close()
                return
            
            # Get HR parameters for analysis
            resting_hr, max_hr = get_user_hr_parameters()
            analyzer = HeartRateAnalyzer(resting_hr, max_hr)
            
            # Analyze the data
            logger.info(f"collect_garmin_data_job: Analyzing heart rate data")
            analysis_results = analyzer.analyze_heart_rate_data(heart_rate_data)
            
            # Debug raw heart rate data
            raw_hr_data = heart_rate_data['heartRateValues']
            logger.info(f"collect_garmin_data_job: Raw HR data type: {type(raw_hr_data)}")
            logger.info(f"collect_garmin_data_job: Raw HR data length: {len(raw_hr_data) if raw_hr_data else 0}")
            if raw_hr_data and len(raw_hr_data) > 0:
                logger.info(f"collect_garmin_data_job: First few HR data points: {raw_hr_data[:3]}")
            
            # Serialize raw data to JSON
            raw_hr_json = json.dumps(raw_hr_data)
            logger.info(f"collect_garmin_data_job: Raw HR JSON length: {len(raw_hr_json)}")
            
            # Store heart rate data in database
            logger.info(f"collect_garmin_data_job: Storing heart rate data for {target_date}")
            
            # Calculate TRIMP and other metrics
            total_trimp = analysis_results['total_trimp']
            daily_score = analysis_results['daily_score']
            activity_type = analysis_results['activity_type']
            
            # Store in new daily_data table
            cur.execute("""
                INSERT INTO daily_data 
                (date, heart_rate_series, trimp_data, total_trimp, daily_score, activity_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(target_date),
                json.dumps(heart_rate_values),
                json.dumps(analysis_results['trimp_data']),
                float(total_trimp),
                float(daily_score),
                str(activity_type)
            ))
            
            conn.commit()
            logger.info(f"collect_garmin_data_job: Data saved to database successfully")
        
        # Collect activities for the same date
        activity_collection_success = True
        try:
            collect_activities_for_date(api, target_date, conn, cur)
        except Exception as activity_error:
            logger.warning(f"collect_garmin_data_job: Failed to collect activities: {activity_error}")
            activity_collection_success = False
        
        # If no daily HR data was found but we have activities, try to construct daily data from activities
        if not has_daily_hr_data and activity_collection_success:
            logger.info(f"collect_garmin_data_job: No daily HR data found, attempting to construct from activities")
            try:
                construct_daily_data_from_activities(target_date, conn, cur)
            except Exception as construction_error:
                logger.warning(f"collect_garmin_data_job: Failed to construct daily data from activities: {construction_error}")
        elif has_daily_hr_data and activity_collection_success:
            # If we have daily HR data and activities, merge activity HR into daily data
            logger.info(f"collect_garmin_data_job: Daily HR data found, merging activity HR data")
            try:
                merge_activity_hr_into_daily(target_date, conn, cur)
            except Exception as merge_error:
                logger.warning(f"collect_garmin_data_job: Failed to merge activity HR into daily data: {merge_error}")
        
        # Update job status based on whether activity collection succeeded
        if activity_collection_success:
            if has_daily_hr_data:
                result_data = {
                    'message': 'Data collection completed successfully',
                    'total_trimp': total_trimp,
                    'daily_score': daily_score,
                    'activity_type': activity_type
                }
            else:
                result_data = {
                    'message': 'Activity collection completed successfully (no daily HR data)',
                    'data_found': False
                }
            
            cur.execute("""
                UPDATE background_jobs 
                SET status = 'completed', result = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (json.dumps(result_data), job_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"collect_garmin_data_job: Job {job_id} completed successfully")
        else:
            # Mark as failed if activity collection failed
            error_msg = f"Failed to collect activities for {target_date}"
            cur.execute("""
                UPDATE background_jobs 
                SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (error_msg, job_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"collect_garmin_data_job: Job {job_id} failed due to activity collection error")
        
    except Exception as e:
        error_msg = f"Error collecting data: {str(e)}"
        logger.error(f"collect_garmin_data_job: {error_msg}")
        
        # Check if this is a rate limit error
        if "429" in str(e) or "Too Many Requests" in str(e):
            error_msg = f"Rate limited by Garmin API for {target_date}. Please try again later."
            logger.warning(f"collect_garmin_data_job: {error_msg}")
            # Mark as failed but with a specific message
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE background_jobs 
                    SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                """, (error_msg, job_id))
                conn.commit()
                cur.close()
                conn.close()
            except Exception as db_error:
                logger.error(f"collect_garmin_data_job: Failed to update job status: {str(db_error)}")
        else:
            # Regular error handling
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE background_jobs 
                    SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                """, (error_msg, job_id))
                conn.commit()
                cur.close()
                conn.close()
            except Exception as db_error:
                logger.error(f"collect_garmin_data_job: Failed to update job status: {str(db_error)}") 

def collect_activities_for_date(api, target_date: str, conn, cur):
    """
    Collect activities for a specific date and store in new schema.
    
    Args:
        api: Garmin API instance
        target_date: Date to collect activities for (YYYY-MM-DD)
        conn: Database connection
        cur: Database cursor
    """
    logger.info(f"collect_activities_for_date: Starting collection for {target_date}")
    
    try:
        # Get activities for the date
        activities = api.get_activities_fordate(target_date)
        
        # Handle new API structure: extract from ActivitiesForDay['payload'] if present
        if isinstance(activities, dict) and 'ActivitiesForDay' in activities:
            afd = activities['ActivitiesForDay']
            if isinstance(afd, dict) and 'payload' in afd:
                activities = afd['payload']
                logger.info(f"collect_activities_for_date: Extracted {len(activities) if activities else 0} activities from ActivitiesForDay['payload']")
            else:
                logger.error(f"collect_activities_for_date: 'ActivitiesForDay' present but no 'payload' key or not a dict")
                activities = []

        if not activities:
            logger.info(f"collect_activities_for_date: No activities found for {target_date}")
            return
        
        logger.info(f"collect_activities_for_date: Found {len(activities)} activities for {target_date}")
        
        # Debug: Check the structure of activities
        if activities:
            logger.info(f"collect_activities_for_date: First activity type: {type(activities[0])}")
            logger.info(f"collect_activities_for_date: First activity keys: {list(activities[0].keys()) if isinstance(activities[0], dict) else 'Not a dict'}")
        
        # Process each activity
        for activity in activities:
            activity_id = str(activity['activityId'])
            logger.info(f"collect_activities_for_date: Processing activity {activity_id}")
            
            # Extract basic activity info
            activity_name = activity.get('activityName', 'Unknown Activity')
            activity_type = activity.get('activityType', 'unknown')
            start_time_local = activity.get('startTimeLocal', '')
            duration_seconds = activity.get('duration', 0)
            distance_meters = activity.get('distance', 0)
            elevation_gain = activity.get('elevationGain', 0)
            average_hr = activity.get('averageHR', 0)
            max_hr = activity.get('maxHR', 0)
            
            # Get detailed activity data for HR extraction
            try:
                activity_details = api.get_activity_details(activity_id)
                logger.info(f"collect_activities_for_date: Got activity details for {activity_id}")
            except Exception as e:
                logger.error(f"collect_activities_for_date: Failed to get activity details for {activity_id}: {e}")
                continue
            
            # Extract HR data from activity
            hr_series = []
            trimp_data = {'zones': {}, 'total_trimp': 0.0}
            total_trimp = 0.0
            
            if 'activityDetailMetrics' in activity_details:
                activity_metrics = activity_details['activityDetailMetrics']
                if activity_metrics:
                    logger.info(f"collect_activities_for_date: Found activityDetailMetrics with {len(activity_metrics)} entries")
                    
                    # Use the clean HR detection function with activity details
                    hr_pos, ts_pos = detect_hr_and_timestamp_positions(activity_details)
                    
                    if hr_pos is not None and ts_pos is not None:
                        logger.info(f"collect_activities_for_date: Selected HR position {hr_pos}, Timestamp position {ts_pos}")
                        
                        # Get the factor for HR values from metricDescriptors
                        hr_factor = 1.0
                        for descriptor in activity_details.get('metricDescriptors', []):
                            if descriptor.get('key') == 'directHeartRate':
                                hr_factor = descriptor.get('unit', {}).get('factor', 1.0)
                                logger.info(f"collect_activities_for_date: Using HR factor: {hr_factor}")
                                break
                        
                        # Extract HR time series
                        hr_values_checked = 0
                        hr_values_filtered = 0
                        
                        # Get user's HR parameters for filtering
                        user_resting_hr, user_max_hr = get_user_hr_parameters()
                        logger.info(f"collect_activities_for_date: Using max HR {user_max_hr} for filtering")
                        
                        for entry in activity_metrics:
                            if 'metrics' in entry and len(entry['metrics']) > max(hr_pos, ts_pos):
                                metrics = entry['metrics']
                                timestamp = metrics[ts_pos]
                                hr_value = metrics[hr_pos]
                                
                                if timestamp is not None and hr_value is not None:
                                    hr_values_checked += 1
                                    
                                    # Apply the factor to get the actual HR value
                                    actual_hr_value = hr_value * hr_factor
                                    
                                    # Log first few HR values for debugging
                                    if hr_values_checked <= 5:
                                        logger.info(f"collect_activities_for_date: Sample HR value {hr_values_checked}: raw={hr_value}, actual={actual_hr_value} (factor={hr_factor})")
                                    
                                    # Skip HR readings above max HR (likely sensor artifacts)
                                    if actual_hr_value > user_max_hr:
                                        if hr_values_checked <= 10:  # Log first 10 filtered values
                                            logger.info(f"collect_activities_for_date: Filtering HR reading {actual_hr_value} above max HR {user_max_hr}")
                                        hr_values_filtered += 1
                                        continue
                                    
                                    hr_series.append([timestamp, int(actual_hr_value)])
                        
                        logger.info(f"collect_activities_for_date: Checked {hr_values_checked} HR values, filtered {hr_values_filtered}, extracted {len(hr_series)}")
                        
                        # Calculate TRIMP for activity
                        if hr_series:
                            total_trimp, trimp_breakdown = calculate_trimp(hr_series)
                            trimp_data = {
                                'presentation_buckets': trimp_breakdown,
                                'total_trimp': total_trimp
                            }
                            logger.info(f"collect_activities_for_date: Calculated TRIMP for activity {activity_id}: {total_trimp}")
                    else:
                        logger.warning(f"collect_activities_for_date: Could not find HR and timestamp positions for activity {activity_id}")
                else:
                    logger.warning(f"collect_activities_for_date: No activityDetailMetrics data for activity {activity_id}")
            else:
                logger.warning(f"collect_activities_for_date: No activityDetailMetrics in activity details for {activity_id}")
            
            # Store activity data in new schema
            cur.execute("""
                INSERT INTO activity_data 
                (activity_id, date, activity_name, activity_type, start_time_local, duration_seconds,
                 distance_meters, elevation_gain, average_hr, max_hr, heart_rate_series, trimp_data, total_trimp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(activity_id), 
                str(target_date), 
                str(activity_name), 
                str(activity_type), 
                str(start_time_local) if start_time_local else None, 
                int(duration_seconds) if duration_seconds else 0,
                float(distance_meters) if distance_meters else None, 
                float(elevation_gain) if elevation_gain else None, 
                int(average_hr) if average_hr else None, 
                int(max_hr) if max_hr else None, 
                json.dumps(hr_series), 
                json.dumps(trimp_data), 
                float(total_trimp)
            ))
            
            logger.info(f"collect_activities_for_date: Stored activity {activity_id} in new schema")
        
        conn.commit()
        logger.info(f"collect_activities_for_date: Completed collection for {target_date}")
        
    except Exception as e:
        logger.error(f"collect_activities_for_date: Error collecting activities for {target_date}: {e}")
        raise 

def calculate_trimp(hr_series):
    """
    Calculate TRIMP from heart rate series data.
    
    Args:
        hr_series: List of [timestamp, heart_rate] pairs
        
    Returns:
        Tuple of (total_trimp, trimp_breakdown)
    """
    if not hr_series or len(hr_series) < 2:
        return 0.0, {}
    
    # Get HR parameters
    resting_hr, max_hr = get_user_hr_parameters()
    
    # Calculate TRIMP using the same logic as before
    total_trimp = 0.0
    trimp_by_zone = {}
    
    # Skip the first reading since it has no previous timestamp
    for i in range(1, len(hr_series)):
        current_ts, current_hr = hr_series[i]
        prev_ts, prev_hr = hr_series[i-1]
        
        # Skip if any values are None
        if current_ts is None or current_hr is None or prev_ts is None or prev_hr is None:
            continue
        
        # Skip readings if the gap from the previous reading is greater than 300 seconds (5 minutes)
        time_diff = (current_ts - prev_ts) / 1000  # Convert from milliseconds to seconds
        if time_diff > 300:
            continue
        
        # Calculate time interval in minutes
        interval_minutes = time_diff / 60
        
        # Calculate TRIMP for this interval
        hr_reserve = (current_hr - resting_hr) / (max_hr - resting_hr)
        trimp_value = interval_minutes * hr_reserve * 0.64 * math.exp(1.92 * hr_reserve)
        
        total_trimp += trimp_value
        
        # Categorize by HR zone
        zone = categorize_hr_zone(current_hr, resting_hr, max_hr)
        if zone not in trimp_by_zone:
            trimp_by_zone[zone] = {'minutes': 0, 'trimp': 0}
        
        trimp_by_zone[zone]['minutes'] += interval_minutes
        trimp_by_zone[zone]['trimp'] += trimp_value
    
    return total_trimp, trimp_by_zone

def categorize_hr_zone(hr, resting_hr, max_hr):
    """Categorize heart rate into zones."""
    if hr < 80:
        return 'Below 80'
    elif hr < 90:
        return '80-89'
    elif hr < 100:
        return '90-99'
    elif hr < 110:
        return '100-109'
    elif hr < 120:
        return '110-119'
    elif hr < 130:
        return '120-129'
    elif hr < 140:
        return '130-139'
    elif hr < 150:
        return '140-149'
    elif hr < 160:
        return '150-159'
    else:
        return '160+'

def merge_activity_hr_into_daily(target_date, conn, cur):
    """
    Merge activity HR data into daily HR data.
    
    Args:
        target_date: Date to process
        conn: Database connection
        cur: Database cursor
    """
    logger.info(f"merge_activity_hr_into_daily: Starting merge for {target_date}")
    
    # Get daily HR data
    cur.execute("SELECT heart_rate_series FROM daily_data WHERE date = ?", (target_date,))
    daily_result = cur.fetchone()
    
    if not daily_result or not daily_result['heart_rate_series']:
        logger.info(f"merge_activity_hr_into_daily: No daily HR data found for {target_date}")
        return
    
    daily_hr_series = json.loads(daily_result['heart_rate_series'])
    logger.info(f"merge_activity_hr_into_daily: Found {len(daily_hr_series)} daily HR points")
    
    # Get all activities for this date
    cur.execute("""
        SELECT activity_id, heart_rate_series, start_time_local, duration_seconds
        FROM activity_data 
        WHERE date = ? AND heart_rate_series IS NOT NULL
        ORDER BY start_time_local
    """, (target_date,))
    
    activities = cur.fetchall()
    logger.info(f"merge_activity_hr_into_daily: Found {len(activities)} activities with HR data")
    
    # Process each activity
    for activity in activities:
        activity_id = activity['activity_id']
        activity_hr_series = json.loads(activity['heart_rate_series'])
        start_time = activity['start_time_local']
        duration = activity['duration_seconds']
        
        if not activity_hr_series:
            continue
        
        logger.info(f"merge_activity_hr_into_daily: Processing activity {activity_id} with {len(activity_hr_series)} HR points")
        
        # Find continuous segments in activity HR data
        segments = find_continuous_segments(activity_hr_series)
        logger.info(f"merge_activity_hr_into_daily: Found {len(segments)} continuous segments")
        
        # Replace daily HR data with activity HR data for each segment
        for segment in segments:
            segment_start = segment[0][0]  # First timestamp in segment
            segment_end = segment[-1][0]   # Last timestamp in segment
            
            # Remove daily HR points that fall within this segment
            daily_hr_series = [point for point in daily_hr_series 
                             if point[0] < segment_start or point[0] > segment_end]
            
            # Add activity HR points for this segment
            daily_hr_series.extend(segment)
            
            logger.info(f"merge_activity_hr_into_daily: Replaced daily HR data from {segment_start} to {segment_end}")
        
        # Sort daily HR series by timestamp
        daily_hr_series.sort(key=lambda x: x[0])
    
    # Calculate daily TRIMP from merged data
    total_trimp, trimp_breakdown = calculate_trimp(daily_hr_series)
    trimp_data = {
        'presentation_buckets': trimp_breakdown,
        'total_trimp': total_trimp
    }
    
    # Update daily data
    cur.execute("""
        UPDATE daily_data 
        SET heart_rate_series = ?, trimp_data = ?, total_trimp = ?, updated_at = CURRENT_TIMESTAMP
        WHERE date = ?
    """, (json.dumps(daily_hr_series), json.dumps(trimp_data), total_trimp, target_date))
    
    logger.info(f"merge_activity_hr_into_daily: Updated daily data with {len(daily_hr_series)} HR points, TRIMP: {total_trimp}")

def find_continuous_segments(hr_series):
    """
    Find continuous segments in HR series data.
    Segments are separated by gaps > 60 seconds.
    
    Args:
        hr_series: List of [timestamp, heart_rate] pairs
        
    Returns:
        List of segments, where each segment is a list of [timestamp, heart_rate] pairs
    """
    if not hr_series or len(hr_series) < 2:
        return [hr_series] if hr_series else []
    
    segments = []
    current_segment = [hr_series[0]]
    
    for i in range(1, len(hr_series)):
        current_ts, current_hr = hr_series[i]
        prev_ts, prev_hr = hr_series[i-1]
        
        # Check if gap is > 60 seconds
        time_diff = (current_ts - prev_ts) / 1000  # Convert from milliseconds to seconds
        
        if time_diff > 60:
            # Gap is too large, start new segment
            if current_segment:
                segments.append(current_segment)
            current_segment = [hr_series[i]]
        else:
            # Gap is small enough, continue current segment
            current_segment.append(hr_series[i])
    
    # Add the last segment
    if current_segment:
        segments.append(current_segment)
    
    return segments 

def construct_daily_data_from_activities(target_date, conn, cur):
    """
    Construct daily HR data from activities when no daily HR data exists.
    
    Args:
        target_date: Date to process
        conn: Database connection
        cur: Database cursor
    """
    logger.info(f"construct_daily_data_from_activities: Starting construction for {target_date}")
    
    # Get all activities for this date
    cur.execute("""
        SELECT activity_id, heart_rate_series, start_time_local, duration_seconds
        FROM activity_data 
        WHERE date = ? AND heart_rate_series IS NOT NULL
        ORDER BY start_time_local
    """, (target_date,))
    
    activities = cur.fetchall()
    logger.info(f"construct_daily_data_from_activities: Found {len(activities)} activities with HR data")
    
    if not activities:
        logger.info(f"construct_daily_data_from_activities: No activities with HR data found for {target_date}")
        return
    
    # Collect all HR data from activities
    all_hr_series = []
    total_duration_seconds = 0
    
    for activity in activities:
        activity_id = activity['activity_id']
        activity_hr_series = json.loads(activity['heart_rate_series'])
        duration_seconds = activity['duration_seconds']
        
        if not activity_hr_series:
            continue
        
        logger.info(f"construct_daily_data_from_activities: Processing activity {activity_id} with {len(activity_hr_series)} HR points")
        
        # Add activity duration to total
        if duration_seconds:
            total_duration_seconds += duration_seconds
        
        # Find continuous segments in activity HR data
        segments = find_continuous_segments(activity_hr_series)
        logger.info(f"construct_daily_data_from_activities: Found {len(segments)} continuous segments")
        
        # Add all segments to the daily HR series
        for segment in segments:
            all_hr_series.extend(segment)
    
    if not all_hr_series:
        logger.info(f"construct_daily_data_from_activities: No HR data collected from activities for {target_date}")
        return
    
    # Sort by timestamp
    all_hr_series.sort(key=lambda x: x[0])
    logger.info(f"construct_daily_data_from_activities: Collected {len(all_hr_series)} total HR points")
    
    # Get HR parameters for analysis
    resting_hr, max_hr = get_user_hr_parameters()
    analyzer = HeartRateAnalyzer(resting_hr, max_hr)
    
    # Create a heart_rate_data structure for analysis
    heart_rate_data = {
        'heartRateValues': all_hr_series
    }
    
    # Analyze the constructed data
    analysis_results = analyzer.analyze_heart_rate_data(heart_rate_data)
    
    # Store in daily_data table
    cur.execute("""
        INSERT INTO daily_data 
        (date, heart_rate_series, trimp_data, total_trimp, daily_score, activity_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        str(target_date),
        json.dumps(all_hr_series),
        json.dumps(analysis_results['trimp_data']),
        float(analysis_results['total_trimp']),
        float(analysis_results['daily_score']),
        str(analysis_results['activity_type'])
    ))
    
    conn.commit()
    logger.info(f"construct_daily_data_from_activities: Created daily data with {len(all_hr_series)} HR points, TRIMP: {analysis_results['total_trimp']}, Duration: {total_duration_seconds/60:.1f} minutes") 