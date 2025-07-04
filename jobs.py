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


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_hr_and_timestamp_positions_advanced(activity_metrics: List[Dict], target_date: str, 
                                              activity_start_time: str, activity_duration: float, 
                                              daily_hr_data: List[List]) -> Tuple[Optional[int], Optional[int], float]:
    """
    Advanced detection using timestamp range validation, HR range validation, and correlation with daily HR data.
    
    Args:
        activity_metrics: List of metric entries from activityDetailMetrics
        target_date: Date being processed (YYYY-MM-DD)
        activity_start_time: Activity start time (ISO format)
        activity_duration: Activity duration in seconds
        daily_hr_data: Daily HR data as [[timestamp, hr_value], ...]
        
    Returns:
        Tuple of (heart_rate_position, timestamp_position, correlation_score) or (None, None, 0.0)
    """
    if not activity_metrics or not daily_hr_data:
        logger.info("detect_hr_and_timestamp_positions_advanced: No activity metrics or daily HR data")
        return None, None, 0.0
    
    # 1. Calculate timestamp range (3-day window centered on target date)
    target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
    start_range = target_datetime - timedelta(days=1)  # 2025-07-01 00:00:00
    end_range = target_datetime + timedelta(days=2)    # 2025-07-04 00:00:00
    
    start_timestamp = int(start_range.timestamp() * 1000)
    end_timestamp = int(end_range.timestamp() * 1000)
    
    logger.info(f"detect_hr_and_timestamp_positions_advanced: Looking for timestamps in range {start_timestamp} to {end_timestamp}")
    
    # 2. Find timestamp candidates within range
    ts_candidates = []
    position_data = {}
    
    # Collect all values for each position
    for entry in activity_metrics:
        if 'metrics' in entry:
            metrics = entry['metrics']
            for pos, value in enumerate(metrics):
                if pos not in position_data:
                    position_data[pos] = []
                if value is not None:
                    position_data[pos].append(value)
    
    # Find timestamp candidates (large numbers in our range with many unique values)
    for pos, values in position_data.items():
        if values and min(values) > 1000000000000:  # Timestamps are in milliseconds
            if start_timestamp <= min(values) <= end_timestamp and start_timestamp <= max(values) <= end_timestamp:
                unique_count = len(set(values))
                if unique_count > 100:  # Should have many unique timestamps
                    ts_candidates.append((pos, unique_count, min(values), max(values)))
    
    if not ts_candidates:
        logger.warning("detect_hr_and_timestamp_positions_advanced: No valid timestamp candidates found")
        return None, None, 0.0
    
    logger.info(f"detect_hr_and_timestamp_positions_advanced: Found {len(ts_candidates)} timestamp candidates")
    
    # 3. For each timestamp candidate, find HR candidates and calculate correlation
    best_correlation = 0.0
    best_hr_pos = None
    best_ts_pos = None
    
    for ts_pos, unique_count, min_ts, max_ts in ts_candidates:
        logger.info(f"detect_hr_and_timestamp_positions_advanced: Checking timestamp position {ts_pos}")
        
        # Find HR candidates in 48-167 range
        hr_candidates = []
        for pos, values in position_data.items():
            if values and min(values) >= 48 and max(values) <= 167:
                # Exclude GPS coordinates (values around 51.4-51.5 are likely London latitude)
                if not (min(values) >= 51.4 and max(values) <= 51.5):
                    unique_count = len(set(values))
                    if unique_count > 5:  # Should have many different HR values
                        hr_candidates.append((pos, unique_count, min(values), max(values)))
        
        if not hr_candidates:
            logger.info(f"detect_hr_and_timestamp_positions_advanced: No HR candidates for timestamp position {ts_pos}")
            continue
        
        logger.info(f"detect_hr_and_timestamp_positions_advanced: Found {len(hr_candidates)} HR candidates for timestamp position {ts_pos}")
        
        # For each HR candidate, calculate correlation with daily HR pattern
        for hr_pos, unique_count, min_hr, max_hr in hr_candidates:
            correlation = calculate_hr_correlation(activity_metrics, ts_pos, hr_pos, 
                                                activity_start_time, activity_duration, daily_hr_data)
            
            logger.info(f"detect_hr_and_timestamp_positions_advanced: HR pos {hr_pos}, TS pos {ts_pos}, correlation: {correlation:.3f}")
            
            if correlation > best_correlation:
                best_correlation = correlation
                best_hr_pos = hr_pos
                best_ts_pos = ts_pos
    
    # 4. Check if we found a good match
    if best_correlation > 0.7:  # Adjustable threshold
        logger.info(f"detect_hr_and_timestamp_positions_advanced: Found good match - HR pos {best_hr_pos}, TS pos {best_ts_pos}, correlation: {best_correlation:.3f}")
        return best_hr_pos, best_ts_pos, best_correlation
    else:
        logger.warning(f"detect_hr_and_timestamp_positions_advanced: No good correlation found. Best: {best_correlation:.3f}")
        return None, None, 0.0

def calculate_hr_correlation(activity_metrics: List[Dict], ts_pos: int, hr_pos: int,
                           activity_start_time: str, activity_duration: float, 
                           daily_hr_data: List[List]) -> float:
    """
    Calculate correlation between activity HR series and daily HR pattern.
    
    Args:
        activity_metrics: Activity metrics data
        ts_pos: Timestamp position in metrics array
        hr_pos: Heart rate position in metrics array
        activity_start_time: Activity start time
        activity_duration: Activity duration in seconds
        daily_hr_data: Daily HR data as [[timestamp, hr_value], ...]
        
    Returns:
        Correlation coefficient (0.0 to 1.0)
    """
    try:
        # 1. Extract activity HR time series
        activity_hr_series = []
        for entry in activity_metrics:
            if 'metrics' in entry and len(entry['metrics']) > max(ts_pos, hr_pos):
                metrics = entry['metrics']
                timestamp = metrics[ts_pos]
                hr_value = metrics[hr_pos]
                
                if timestamp and hr_value and 48 <= hr_value <= 167:
                    activity_hr_series.append([timestamp, hr_value])
        
        if len(activity_hr_series) < 10:  # Need minimum data points
            return 0.0
        
        # 2. Get activity time window
        activity_start = datetime.fromisoformat(activity_start_time.replace('Z', '+00:00'))
        activity_start_ts = int(activity_start.timestamp() * 1000)
        activity_end_ts = activity_start_ts + int(activity_duration * 1000)
        
        # 3. Extract daily HR data for activity time window
        daily_hr_window = []
        for timestamp, hr_value in daily_hr_data:
            if activity_start_ts <= timestamp <= activity_end_ts:
                daily_hr_window.append([timestamp, hr_value])
        
        if len(daily_hr_window) < 5:  # Need minimum daily data points
            return 0.0
        
        # 4. Align the two series for correlation calculation
        # We'll resample both to the same time points
        aligned_data = align_hr_series(activity_hr_series, daily_hr_window)
        
        if len(aligned_data) < 5:  # Need minimum aligned points
            return 0.0
        
        # 5. Calculate correlation
        activity_values = [point[0] for point in aligned_data]
        daily_values = [point[1] for point in aligned_data]
        
        # Calculate correlation coefficient manually (Pearson correlation)
        correlation = calculate_pearson_correlation(activity_values, daily_values)
        
        return abs(correlation)  # Use absolute value since we care about magnitude, not direction
        
    except Exception as e:
        logger.error(f"calculate_hr_correlation: Error calculating correlation: {e}")
        return 0.0

def align_hr_series(activity_hr_series: List[List], daily_hr_window: List[List]) -> List[List]:
    """
    Align activity HR series with daily HR window for correlation calculation.
    
    Args:
        activity_hr_series: Activity HR data as [[timestamp, hr_value], ...]
        daily_hr_window: Daily HR data for activity time window
        
    Returns:
        Aligned data as [[activity_hr, daily_hr], ...]
    """
    if not activity_hr_series or not daily_hr_window:
        return []
    
    # Sort both series by timestamp
    activity_hr_series.sort(key=lambda x: x[0])
    daily_hr_window.sort(key=lambda x: x[0])
    
    # Create a mapping of daily HR data by timestamp
    daily_hr_map = {}
    for timestamp, hr_value in daily_hr_window:
        daily_hr_map[timestamp] = hr_value
    
    # Align activity HR with nearest daily HR values
    aligned_data = []
    for activity_ts, activity_hr in activity_hr_series:
        # Find the closest daily HR timestamp
        closest_ts = min(daily_hr_map.keys(), key=lambda x: abs(x - activity_ts))
        
        # Only include if timestamps are within 30 seconds (30000ms)
        if abs(closest_ts - activity_ts) <= 30000:
            daily_hr = daily_hr_map[closest_ts]
            aligned_data.append([activity_hr, daily_hr])
    
    return aligned_data

def calculate_pearson_correlation(x_values: List[float], y_values: List[float]) -> float:
    """
    Calculate Pearson correlation coefficient between two lists of values.
    
    Args:
        x_values: List of x values
        y_values: List of y values
        
    Returns:
        Correlation coefficient (-1.0 to 1.0)
    """
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return 0.0
    
    try:
        # Calculate means
        x_mean = sum(x_values) / len(x_values)
        y_mean = sum(y_values) / len(y_values)
        
        # Calculate numerator (sum of products of deviations)
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        
        # Calculate denominators (sum of squared deviations)
        x_denominator = sum((x - x_mean) ** 2 for x in x_values)
        y_denominator = sum((y - y_mean) ** 2 for y in y_values)
        
        # Calculate correlation coefficient
        if x_denominator == 0 or y_denominator == 0:
            return 0.0
        
        correlation = numerator / (x_denominator * y_denominator) ** 0.5
        
        # Handle any NaN or infinite values
        if not (correlation >= -1.0 and correlation <= 1.0):
            return 0.0
        
        return correlation
        
    except Exception as e:
        logger.error(f"calculate_pearson_correlation: Error calculating correlation: {e}")
        return 0.0

def detect_hr_and_timestamp_positions(activity_metrics: List[Dict]) -> Tuple[Optional[int], Optional[int]]:
    """
    Fallback detection using simple range-based approach.
    
    Args:
        activity_metrics: List of metric entries from activityDetailMetrics
        
    Returns:
        Tuple of (heart_rate_position, timestamp_position) or (None, None) if not found
    """
    if not activity_metrics:
        return None, None
    
    logger.info(f"detect_hr_and_timestamp_positions (fallback): Starting detection with {len(activity_metrics)} metric entries")
    
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
    
    logger.info(f"detect_hr_and_timestamp_positions (fallback): Collected data for {len(position_data)} positions")
    
    # Find heart rate position (values in 48-167 range, should be integers)
    hr_candidates = []
    for pos, values in position_data.items():
        if values and min(values) >= 48 and max(values) <= 167:
            # Check if all values are integers (HR data should be discrete)
            all_integers = all(isinstance(v, (int, float)) and v == int(v) for v in values)
            if all_integers:
                unique_count = len(set(values))
                if unique_count > 5:  # Should have some different heart rate values
                    hr_candidates.append((pos, unique_count, min(values), max(values)))
                    logger.info(f"detect_hr_and_timestamp_positions (fallback): HR candidate at position {pos}: "
                              f"{unique_count} unique values, range {min(values)}-{max(values)}, all integers: {all_integers}")
            else:
                logger.info(f"detect_hr_and_timestamp_positions (fallback): Excluded position {pos} as non-integer data: "
                          f"range {min(values)}-{max(values)}, all integers: {all_integers}")
    
    # Find timestamp position (large numbers > 1000000000000, many unique values)
    ts_candidates = []
    for pos, values in position_data.items():
        if values and min(values) > 1000000000000:  # Timestamps are in milliseconds since epoch
            unique_count = len(set(values))
            if unique_count > 100:  # Should have many unique timestamps
                ts_candidates.append((pos, unique_count, min(values), max(values)))
                logger.info(f"detect_hr_and_timestamp_positions (fallback): Timestamp candidate at position {pos}: "
                          f"{unique_count} unique values, range {min(values)}-{max(values)}")
    
    # Select best candidates
    hr_position = None
    if hr_candidates:
        # Sort by number of unique values (descending) and take the first
        hr_candidates.sort(key=lambda x: x[1], reverse=True)
        hr_position = hr_candidates[0][0]
        logger.info(f"detect_hr_and_timestamp_positions (fallback): Selected HR position {hr_position} "
                   f"({hr_candidates[0][1]} unique values, range {hr_candidates[0][2]}-{hr_candidates[0][3]})")
        
        # Log all HR candidates for debugging
        logger.info(f"detect_hr_and_timestamp_positions (fallback): All HR candidates:")
        for pos, unique_count, min_val, max_val in hr_candidates:
            logger.info(f"  Position {pos}: {unique_count} unique values, range {min_val}-{max_val}")
    else:
        logger.warning(f"detect_hr_and_timestamp_positions (fallback): No HR candidates found!")
        # Log all positions that were in 48-167 range but excluded
        for pos, values in position_data.items():
            if values and min(values) >= 48 and max(values) <= 167:
                logger.info(f"detect_hr_and_timestamp_positions (fallback): Position {pos} in HR range but excluded: "
                          f"range {min(values)}-{max(values)}, unique count {len(set(values))}")
    
    ts_position = None
    if ts_candidates:
        # Sort by number of unique values (descending) and take the first
        ts_candidates.sort(key=lambda x: x[1], reverse=True)
        ts_position = ts_candidates[0][0]
        logger.info(f"detect_hr_and_timestamp_positions (fallback): Selected timestamp position {ts_position} "
                   f"({ts_candidates[0][1]} unique values)")
        
        # Log all timestamp candidates for debugging
        logger.info(f"detect_hr_and_timestamp_positions (fallback): All timestamp candidates:")
        for pos, unique_count, min_val, max_val in ts_candidates:
            logger.info(f"  Position {pos}: {unique_count} unique values, range {min_val}-{max_val}")
    else:
        logger.warning(f"detect_hr_and_timestamp_positions (fallback): No timestamp candidates found!")
    
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
        
        # Connect to Garmin
        api = Garmin(creds['email'], password)
        api.login()
        
        # Get heart rate data
        logger.info(f"collect_garmin_data_job: Fetching heart rate data for {target_date}")
        heart_rate_data = api.get_heart_rates(target_date)
        
        logger.info(f"collect_garmin_data_job: Raw heart rate data: {heart_rate_data}")
        
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
        logger.info(f"collect_garmin_data_job: Heart rate values: {heart_rate_values}")
        
        if not heart_rate_values or len(heart_rate_values) == 0:
            error_msg = f"No heart rate values found for {target_date}"
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
        analysis_result = analyzer.analyze_heart_rate_data(heart_rate_data)
        
        # Debug raw heart rate data
        raw_hr_data = heart_rate_data['heartRateValues']
        logger.info(f"collect_garmin_data_job: Raw HR data type: {type(raw_hr_data)}")
        logger.info(f"collect_garmin_data_job: Raw HR data length: {len(raw_hr_data) if raw_hr_data else 0}")
        if raw_hr_data and len(raw_hr_data) > 0:
            logger.info(f"collect_garmin_data_job: First few HR data points: {raw_hr_data[:3]}")
        
        # Serialize raw data to JSON
        raw_hr_json = json.dumps(raw_hr_data)
        logger.info(f"collect_garmin_data_job: Raw HR JSON length: {len(raw_hr_json)}")
        logger.info(f"collect_garmin_data_job: Raw HR JSON first 100 chars: {raw_hr_json[:100]}")
        
        # Save to database
        # First, try to delete any existing record for this date
        cur.execute("DELETE FROM heart_rate_data WHERE date = ?", (target_date,))
        
        # Then insert the new record
        cur.execute("""
            INSERT INTO heart_rate_data 
            (date, individual_hr_buckets, presentation_buckets, trimp_data, 
             total_trimp, daily_score, activity_type, raw_hr_data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            target_date,
            json.dumps(analysis_result['individual_hr_buckets']),
            json.dumps(analysis_result['presentation_buckets']),
            json.dumps(analysis_result['trimp_data']),
            analysis_result['total_trimp'],
            analysis_result['daily_score'],
            analysis_result['activity_type'],
            raw_hr_json
        ))
        
        conn.commit()
        logger.info(f"collect_garmin_data_job: Data saved to database successfully")
        
        # Collect activities for the same date
        try:
            collect_activities_for_date(api, target_date, conn, cur)
        except Exception as activity_error:
            logger.warning(f"collect_garmin_data_job: Failed to collect activities: {activity_error}")
            # Continue with the job even if activity collection fails
        
        # Update job status to completed
        result_data = {
            'message': 'Data collection completed successfully',
            'total_trimp': analysis_result['total_trimp'],
            'daily_score': analysis_result['daily_score'],
            'activity_type': analysis_result['activity_type']
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
    Collect activities for a specific date and store them in the database.
    
    Args:
        api: Garmin API instance
        target_date: Date to collect activities for (YYYY-MM-DD)
        conn: Database connection
        cur: Database cursor
    """
    logger.info(f"collect_activities_for_date: Collecting activities for {target_date}")
    
    try:
        # Delete existing activities for this date first (like we do for heart rate data)
        cur.execute("DELETE FROM activities WHERE date = ?", (target_date,))
        logger.info(f"collect_activities_for_date: Deleted existing activities for {target_date}")
        
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
        
        # Get HR parameters for TRIMP calculation
        resting_hr, max_hr = get_user_hr_parameters()
        analyzer = HeartRateAnalyzer(resting_hr, max_hr)
        
        # Debug the activities structure
        logger.info(f"collect_activities_for_date: Activities type: {type(activities)}")
        logger.info(f"collect_activities_for_date: Activities length: {len(activities) if activities else 0}")
        logger.info(f"collect_activities_for_date: Activities keys: {list(activities.keys()) if isinstance(activities, dict) else 'Not a dict'}")
        logger.info(f"collect_activities_for_date: First activity: {activities[0] if activities and hasattr(activities, '__getitem__') and len(activities) > 0 else 'None'}")
        
        # If activities is a dict, it might have a different structure
        if isinstance(activities, dict):
            logger.info(f"collect_activities_for_date: Activities dict structure: {activities}")
            # Check if it has an 'ActivitiesForDay' key (which contains the actual activities)
            if 'ActivitiesForDay' in activities:
                activities = activities['ActivitiesForDay']
                logger.info(f"collect_activities_for_date: Found 'ActivitiesForDay' key, new length: {len(activities) if activities else 0}")
            elif 'activities' in activities:
                activities = activities['activities']
                logger.info(f"collect_activities_for_date: Found 'activities' key, new length: {len(activities)}")
            else:
                logger.error(f"collect_activities_for_date: Activities is dict but no 'ActivitiesForDay' or 'activities' key found")
                return
        
        # Process each activity
        for i, activity in enumerate(activities):
            logger.info(f"collect_activities_for_date: Processing activity {i}: {type(activity)}")
            
            # Handle different possible activity formats
            if isinstance(activity, str):
                # If activity is a string, it might be the activity ID
                activity_id = str(activity)
                logger.info(f"collect_activities_for_date: Activity is string, using as ID: {activity_id}")
            elif isinstance(activity, dict):
                activity_id = str(activity.get('activityId'))
                logger.info(f"collect_activities_for_date: Activity is dict, ID: {activity_id}")
            else:
                logger.warning(f"collect_activities_for_date: Unknown activity format: {type(activity)}, skipping")
                continue
            
            if not activity_id:
                logger.warning(f"collect_activities_for_date: Activity missing ID, skipping")
                continue
            
            # Get detailed activity data
            try:
                # Get detailed activity data which includes heart rate time series
                activity_details = api.get_activity_details(activity_id)
                logger.info(f"collect_activities_for_date: Got details for activity {activity_id}")
                
                                # Extract heart rate time series from activityDetailMetrics
                hr_data = None
                if activity_details and 'activityDetailMetrics' in activity_details:
                    activity_metrics = activity_details['activityDetailMetrics']
                    if activity_metrics and len(activity_metrics) > 0:
                        # Get daily HR data for correlation
                        cur.execute("SELECT raw_hr_data FROM heart_rate_data WHERE date = ?", (target_date,))
                        daily_hr_result = cur.fetchone()
                        daily_hr_data = []
                        if daily_hr_result and daily_hr_result['raw_hr_data']:
                            daily_hr_data = json.loads(daily_hr_result['raw_hr_data'])
                        
                        # Try advanced detection first
                        start_time = activity_details.get('startTimeLocal', '')
                        duration = activity_details.get('duration', 0)
                        
                        if start_time and duration > 0:
                            hr_position, ts_position, correlation = detect_hr_and_timestamp_positions_advanced(
                                activity_metrics, target_date, start_time, duration, daily_hr_data
                            )
                            
                            if hr_position is not None and ts_position is not None:
                                logger.info(f"collect_activities_for_date: Advanced detection successful for activity {activity_id}")
                                logger.info(f"collect_activities_for_date: HR position: {hr_position}, TS position: {ts_position}, correlation: {correlation}")
                            else:
                                logger.warning(f"collect_activities_for_date: Missing start time or duration for activity {activity_id}, skipping advanced detection")
                                logger.warning(f"collect_activities_for_date: Advanced detection failed for activity {activity_id}, trying fallback")
                                
                                # Log the activity_metrics structure for debugging
                                logger.info(f"collect_activities_for_date: activity_metrics has {len(activity_metrics)} entries")
                                logger.info(f"collect_activities_for_date: First few activity_metrics entries:")
                                for i, entry in enumerate(activity_metrics[:3]):
                                    logger.info(f"  Entry {i}: {entry}")
                                
                                hr_position, ts_position = detect_hr_and_timestamp_positions(activity_metrics)
                        else:
                            logger.warning(f"collect_activities_for_date: Missing start time or duration for activity {activity_id}, skipping advanced detection")
                            logger.warning(f"collect_activities_for_date: Advanced detection failed for activity {activity_id}, trying fallback")
                            
                            # Log the activity_metrics structure for debugging
                            logger.info(f"collect_activities_for_date: activity_metrics has {len(activity_metrics)} entries")
                            logger.info(f"collect_activities_for_date: First few activity_metrics entries:")
                            for i, entry in enumerate(activity_metrics[:3]):
                                logger.info(f"  Entry {i}: {entry}")
                            
                            hr_position, ts_position = detect_hr_and_timestamp_positions(activity_metrics)
                        
                        if hr_position is not None and ts_position is not None:
                            logger.info(f"collect_activities_for_date: Advanced detection successful for activity {activity_id}")
                            hr_time_series = []
                            for metric_entry in activity_metrics:
                                if 'metrics' in metric_entry and len(metric_entry['metrics']) > max(hr_position, ts_position):
                                    metrics = metric_entry['metrics']
                                    heart_rate = metrics[hr_position]
                                    timestamp = metrics[ts_position]
                                    
                                    # Include all heart rate data from the identified series (do not filter by value)
                                    if timestamp is not None and heart_rate is not None:
                                        hr_time_series.append([timestamp, int(heart_rate)])
                                        
                            if hr_time_series:
                                # Calculate actual time intervals to determine sampling rate
                                if len(hr_time_series) > 1:
                                    time_diff = hr_time_series[1][0] - hr_time_series[0][0]
                                    sampling_interval_seconds = time_diff / 1000  # Convert from milliseconds
                                    logger.info(f"collect_activities_for_date: Activity {activity_id} HR sampling interval: {sampling_interval_seconds:.1f} seconds")
                                
                                hr_data = {'heartRateValues': hr_time_series}
                                logger.info(f"collect_activities_for_date: Extracted {len(hr_time_series)} HR data points for activity {activity_id}")
                            else:
                                logger.info(f"collect_activities_for_date: No valid HR data points found for activity {activity_id}")
                        else:
                            logger.warning(f"collect_activities_for_date: Both advanced and fallback detection failed for activity {activity_id}")
                    else:
                        logger.info(f"collect_activities_for_date: No activityDetailMetrics data for activity {activity_id}")
                else:
                    logger.info(f"collect_activities_for_date: No activity details or activityDetailMetrics for activity {activity_id}")
                    
            except Exception as e:
                logger.warning(f"collect_activities_for_date: Could not get HR data for activity {activity_id}: {e}")
                hr_data = None
            
            # Calculate TRIMP if we have HR data
            trimp_results = None
            if hr_data and 'heartRateValues' in hr_data and hr_data['heartRateValues']:
                logger.info(f"collect_activities_for_date: About to calculate TRIMP for activity {activity_id}")
                logger.info(f"collect_activities_for_date: HR data points: {len(hr_data['heartRateValues'])}")
                
                # Log sample of HR data being used for TRIMP calculation
                if hr_data['heartRateValues']:
                    logger.info(f"collect_activities_for_date: Sample HR data for TRIMP calculation (first 5 points):")
                    for i, (ts, hr) in enumerate(hr_data['heartRateValues'][:5]):
                        logger.info(f"  Point {i}: timestamp={ts}, HR={hr}")
                
                trimp_results = analyzer.analyze_heart_rate_data(hr_data)
                logger.info(f"collect_activities_for_date: Calculated TRIMP for activity {activity_id}: {trimp_results['total_trimp']:.2f}")
                
                # Log TRIMP breakdown
                if trimp_results['presentation_buckets']:
                    logger.info(f"collect_activities_for_date: TRIMP breakdown for activity {activity_id}:")
                    for bucket, data in trimp_results['presentation_buckets'].items():
                        if data['minutes'] > 0 or data['trimp'] > 0:
                            logger.info(f"  {bucket}: {data['minutes']:.1f} minutes, {data['trimp']:.2f} TRIMP")
            else:
                logger.warning(f"collect_activities_for_date: No HR data available for TRIMP calculation for activity {activity_id}")
                if hr_data:
                    logger.info(f"collect_activities_for_date: HR data keys: {list(hr_data.keys()) if isinstance(hr_data, dict) else 'Not a dict'}")
                    if 'heartRateValues' in hr_data:
                        logger.info(f"collect_activities_for_date: heartRateValues length: {len(hr_data['heartRateValues']) if hr_data['heartRateValues'] else 'Empty'}")
                else:
                    logger.info(f"collect_activities_for_date: hr_data is None")
            
            # Extract activity data - handle both string and dict formats
            if isinstance(activity, dict):
                activity_name = activity.get('activityName', 'Unknown Activity')
                activity_type = activity.get('activityType', {}).get('typeKey', 'unknown')
                start_time_local = activity.get('startTimeLocal')
                duration_seconds = activity.get('duration', 0)
                distance_meters = activity.get('distance', 0)
                elevation_gain = activity.get('elevationGain', 0)
                average_hr = activity.get('averageHR')
                max_hr = activity.get('maxHR')
            else:
                # If activity is a string (just an ID), we'll get details from the API
                activity_name = 'Unknown Activity'
                activity_type = 'unknown'
                start_time_local = None
                duration_seconds = 0
                distance_meters = 0
                elevation_gain = 0
                average_hr = None
                max_hr = None
            
            # Store activity in database
            cur.execute("""
                INSERT INTO activities 
                (activity_id, date, activity_name, activity_type, start_time_local,
                 duration_seconds, distance_meters, elevation_gain, average_hr, max_hr,
                 individual_hr_buckets, presentation_buckets, trimp_data, total_trimp,
                 raw_activity_data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                activity_id,
                target_date,
                activity_name,
                activity_type,
                start_time_local,
                duration_seconds,
                distance_meters,
                elevation_gain,
                average_hr,
                max_hr,
                json.dumps(trimp_results['individual_hr_buckets']) if trimp_results else None,
                json.dumps(trimp_results['presentation_buckets']) if trimp_results else None,
                json.dumps(trimp_results['trimp_data']) if trimp_results else None,
                trimp_results['total_trimp'] if trimp_results else 0.0,
                json.dumps(activity_details)
            ))
            
            logger.info(f"collect_activities_for_date: Stored activity {activity_id} in database")
        
        conn.commit()
        logger.info(f"collect_activities_for_date: Successfully processed {len(activities)} activities for {target_date}")
        
    except Exception as e:
        logger.error(f"collect_activities_for_date: Error collecting activities for {target_date}: {e}")
        logger.error(f"collect_activities_for_date: Error type: {type(e)}")
        logger.error(f"collect_activities_for_date: Error details: {str(e)}")
        import traceback
        logger.error(f"collect_activities_for_date: Full traceback: {traceback.format_exc()}")
        raise 