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


def detect_breathing_rate_position(activity_details: Dict) -> Optional[int]:
    """
    Detect breathing rate position in activity metrics.
    
    Args:
        activity_details: Activity details from Garmin API
        
    Returns:
        Breathing rate position or None if not found
    """
    logger.info(f"detect_breathing_rate_position: Analyzing activity details for breathing rate")
    
    # Get metric descriptors
    metric_descriptors = activity_details.get('metricDescriptors', [])
    if not metric_descriptors:
        logger.warning(f"detect_breathing_rate_position: No metricDescriptors found")
        return None
    
    # Find breathing rate position
    breathing_pos = None
    
    for descriptor in metric_descriptors:
        metrics_index = descriptor.get('metricsIndex')
        key = descriptor.get('key', '')
        logger.info(f"detect_breathing_rate_position: Descriptor {metrics_index}: key='{key}'")
        
        if key == 'directRespirationRate':
            breathing_pos = metrics_index
            logger.info(f"detect_breathing_rate_position: Found breathing rate at position {breathing_pos}")
            break
    
    if breathing_pos is not None:
        logger.info(f"detect_breathing_rate_position: Successfully detected breathing rate at {breathing_pos}")
        return breathing_pos
    else:
        logger.info(f"detect_breathing_rate_position: No breathing rate data found")
        return None


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
        
        # Clean up any existing data for this date (user data is stored separately)
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
        
        # Build the final HR time series for the day
        logger.info(f"collect_garmin_data_job: Building final HR time series for {target_date}")
        final_hr_series = build_daily_hr_timeseries(target_date, conn, cur)
        
        if final_hr_series:
            logger.info(f"collect_garmin_data_job: Built HR time series with {len(final_hr_series)} points")
            
            # Calculate TRIMP from the final HR time series
            trimp_results = calculate_trimp_from_timeseries(final_hr_series)
            
            # Update or insert daily data
            cur.execute("DELETE FROM daily_data WHERE date = ?", (target_date,))
            cur.execute("""
                INSERT INTO daily_data 
                (date, heart_rate_series, trimp_data, total_trimp, daily_score, activity_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(target_date),
                json.dumps(final_hr_series),
                json.dumps({
                    'presentation_buckets': trimp_results['presentation_buckets'],
                    'total_trimp': trimp_results['total_trimp']
                }),
                float(trimp_results['total_trimp']),
                0.0,  # daily_score - could be calculated separately
                'mixed'  # activity_type - could be determined from activities
            ))
            
            conn.commit()
            logger.info(f"collect_garmin_data_job: Updated daily data with {len(final_hr_series)} HR points, TRIMP: {trimp_results['total_trimp']}")
        else:
            logger.info(f"collect_garmin_data_job: No HR time series could be built for {target_date}")
        
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
            
            # Extract HR and breathing rate data from activity
            hr_series = []
            breathing_series = []
            trimp_data = {'zones': {}, 'total_trimp': 0.0}
            total_trimp = 0.0
            
            if 'activityDetailMetrics' in activity_details:
                activity_metrics = activity_details['activityDetailMetrics']
                if activity_metrics:
                    logger.info(f"collect_activities_for_date: Found activityDetailMetrics with {len(activity_metrics)} entries")
                    
                    # Use the clean HR detection function with activity details
                    hr_pos, ts_pos = detect_hr_and_timestamp_positions(activity_details)
                    
                    # Detect breathing rate position
                    breathing_pos = detect_breathing_rate_position(activity_details)
                    
                    if hr_pos is not None and ts_pos is not None:
                        logger.info(f"collect_activities_for_date: Selected HR position {hr_pos}, Timestamp position {ts_pos}")
                        if breathing_pos is not None:
                            logger.info(f"collect_activities_for_date: Selected breathing rate position {breathing_pos}")
                        
                        # Get the factor for HR values from metricDescriptors
                        hr_factor = 1.0
                        for descriptor in activity_details.get('metricDescriptors', []):
                            if descriptor.get('key') == 'directHeartRate':
                                hr_factor = descriptor.get('unit', {}).get('factor', 1.0)
                                logger.info(f"collect_activities_for_date: Using HR factor: {hr_factor}")
                                break
                        
                        # Extract HR and breathing rate time series
                        hr_values_checked = 0
                        hr_values_filtered = 0
                        breathing_values_checked = 0
                        
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
                                
                                # Extract breathing rate if available
                                if breathing_pos is not None and len(metrics) > breathing_pos:
                                    breathing_value = metrics[breathing_pos]
                                    if timestamp is not None and breathing_value is not None:
                                        breathing_values_checked += 1
                                        
                                        # Log first few breathing values for debugging
                                        if breathing_values_checked <= 5:
                                            logger.info(f"collect_activities_for_date: Sample breathing value {breathing_values_checked}: {breathing_value}")
                                        
                                        breathing_series.append([timestamp, float(breathing_value)])
                        
                        logger.info(f"collect_activities_for_date: Checked {hr_values_checked} HR values, filtered {hr_values_filtered}, extracted {len(hr_series)}")
                        logger.info(f"collect_activities_for_date: Checked {breathing_values_checked} breathing values, extracted {len(breathing_series)}")
                        
                        # Calculate TRIMP for activity using the new function
                        if hr_series:
                            trimp_results = calculate_trimp_from_timeseries(hr_series)
                            trimp_data = {
                                'presentation_buckets': trimp_results['presentation_buckets'],
                                'total_trimp': trimp_results['total_trimp']
                            }
                            logger.info(f"collect_activities_for_date: Calculated TRIMP for activity {activity_id}: {trimp_results['total_trimp']}")
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
                 distance_meters, elevation_gain, average_hr, max_hr, heart_rate_series, breathing_rate_series, trimp_data, total_trimp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json.dumps(breathing_series), 
                json.dumps(trimp_data), 
                float(trimp_results['total_trimp']) if 'trimp_results' in locals() else 0.0
            ))
            
            logger.info(f"collect_activities_for_date: Stored activity {activity_id} in new schema")
        
        conn.commit()
        logger.info(f"collect_activities_for_date: Completed collection for {target_date}")
        
    except Exception as e:
        logger.error(f"collect_activities_for_date: Error collecting activities for {target_date}: {e}")
        raise 







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



def build_daily_hr_timeseries(target_date, conn, cur):
    """
    Build the daily HR time series by combining daily HR data and activity HR data.
    
    Args:
        target_date: Date to process
        conn: Database connection
        cur: Database cursor
        
    Returns:
        List of [timestamp, heart_rate] pairs for the day
    """
    logger.info(f"build_daily_hr_timeseries: Building HR time series for {target_date}")
    
    # Get daily HR data
    cur.execute("SELECT heart_rate_series FROM daily_data WHERE date = ?", (target_date,))
    daily_result = cur.fetchone()
    
    daily_hr_series = []
    if daily_result and daily_result['heart_rate_series']:
        daily_hr_series = json.loads(daily_result['heart_rate_series'])
        logger.info(f"build_daily_hr_timeseries: Found {len(daily_hr_series)} daily HR points")
    else:
        logger.info(f"build_daily_hr_timeseries: No daily HR data found for {target_date}")
    
    # Get all activities for this date
    cur.execute("""
        SELECT activity_id, heart_rate_series, start_time_local, duration_seconds
        FROM activity_data 
        WHERE date = ? AND heart_rate_series IS NOT NULL
        ORDER BY start_time_local
    """, (target_date,))
    
    activities = cur.fetchall()
    logger.info(f"build_daily_hr_timeseries: Found {len(activities)} activities with HR data")
    
    # If no daily HR data and no activities, return empty
    if not daily_hr_series and not activities:
        logger.info(f"build_daily_hr_timeseries: No HR data available for {target_date}")
        return []
    
    # If no daily HR data but we have activities, construct from activities only
    if not daily_hr_series and activities:
        logger.info(f"build_daily_hr_timeseries: Constructing from activities only")
        all_hr_series = []
        
        for activity in activities:
            activity_hr_series = json.loads(activity['heart_rate_series'])
            if activity_hr_series:
                # Find continuous segments in activity HR data
                segments = find_continuous_segments(activity_hr_series)
                logger.info(f"build_daily_hr_timeseries: Activity {activity['activity_id']} has {len(segments)} segments")
                
                # Add all segments to the daily HR series
                for segment in segments:
                    all_hr_series.extend(segment)
        
        if all_hr_series:
            all_hr_series.sort(key=lambda x: x[0])
            logger.info(f"build_daily_hr_timeseries: Constructed {len(all_hr_series)} HR points from activities")
            return all_hr_series
        else:
            logger.info(f"build_daily_hr_timeseries: No HR data collected from activities")
            return []
    
    # If we have daily HR data, merge with activity data
    if daily_hr_series:
        logger.info(f"build_daily_hr_timeseries: Merging daily HR data with activity data")
        
        # Process each activity
        for activity in activities:
            activity_id = activity['activity_id']
            activity_hr_series = json.loads(activity['heart_rate_series'])
            
            if not activity_hr_series:
                continue
            
            logger.info(f"build_daily_hr_timeseries: Processing activity {activity_id} with {len(activity_hr_series)} HR points")
            
            # Find continuous segments in activity HR data
            segments = find_continuous_segments(activity_hr_series)
            logger.info(f"build_daily_hr_timeseries: Found {len(segments)} continuous segments")
            
            # Replace daily HR data with activity HR data for each segment
            for segment in segments:
                segment_start = segment[0][0]  # First timestamp in segment
                segment_end = segment[-1][0]   # Last timestamp in segment
                
                # Remove daily HR points that fall within this segment
                daily_hr_series = [point for point in daily_hr_series 
                                 if point[0] < segment_start or point[0] > segment_end]
                
                # Add activity HR points for this segment
                daily_hr_series.extend(segment)
                
                logger.info(f"build_daily_hr_timeseries: Replaced daily HR data from {segment_start} to {segment_end}")
            
            # Sort daily HR series by timestamp
            daily_hr_series.sort(key=lambda x: x[0])
        
        logger.info(f"build_daily_hr_timeseries: Final HR time series has {len(daily_hr_series)} points")
        return daily_hr_series
    
    return []

def calculate_trimp_from_timeseries(hr_series):
    """
    Calculate TRIMP from heart rate series data.
    
    Args:
        hr_series: List of [timestamp, heart_rate] pairs
        
    Returns:
        Dict with presentation_buckets and total_trimp
    """
    if not hr_series or len(hr_series) < 2:
        return {
            'presentation_buckets': {},
            'total_trimp': 0.0
        }
    
    # Get HR parameters
    resting_hr, max_hr = get_user_hr_parameters()
    
    # Use the existing TRIMPCalculator which has the correct presentation bucket logic
    from models import TRIMPCalculator
    calculator = TRIMPCalculator(resting_hr, max_hr)
    
    # Convert to the format expected by TRIMPCalculator
    heart_rate_data = {
        'heartRateValues': hr_series
    }
    
    # Calculate TRIMP using the existing logic
    results = calculator.bucket_heart_rates(heart_rate_data)
    
    return {
        'presentation_buckets': results['presentation_buckets'],
        'total_trimp': results['total_trimp']
    } 