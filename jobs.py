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
    
    logger.debug(f"detect_hr_and_timestamp_positions_advanced: Found {len(ts_candidates)} timestamp candidates")
    
    # 3. For each timestamp candidate, find HR candidates and calculate correlation
    best_correlation = 0.0
    best_hr_pos = None
    best_ts_pos = None
    
    for ts_pos, unique_count, min_ts, max_ts in ts_candidates:
        logger.debug(f"detect_hr_and_timestamp_positions_advanced: Checking timestamp position {ts_pos}")
        
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
            logger.debug(f"detect_hr_and_timestamp_positions_advanced: No HR candidates for timestamp position {ts_pos}")
            continue
        
        logger.debug(f"detect_hr_and_timestamp_positions_advanced: Found {len(hr_candidates)} HR candidates for timestamp position {ts_pos}")
        
        # For each HR candidate, calculate correlation with daily HR pattern
        for hr_pos, unique_count, min_hr, max_hr in hr_candidates:
            correlation = calculate_hr_correlation(activity_metrics, ts_pos, hr_pos, 
                                                activity_start_time, activity_duration, daily_hr_data)
            
            logger.debug(f"detect_hr_and_timestamp_positions_advanced: HR pos {hr_pos}, TS pos {ts_pos}, correlation: {correlation:.3f}")
            
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
    
    logger.debug(f"detect_hr_and_timestamp_positions (fallback): Starting detection with {len(activity_metrics)} metric entries")
    
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
    
    logger.debug(f"detect_hr_and_timestamp_positions (fallback): Collected data for {len(position_data)} positions")
    
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
            
            # Delete existing data for this date
            cur.execute("DELETE FROM daily_data WHERE date = ?", (target_date,))
            
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
        
        # Delete existing activity data for this date
        cur.execute("DELETE FROM activity_data WHERE date = ?", (target_date,))
        
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
                    
                    # Use the same HR extraction logic as the app
                    position_data = {}
                    for entry in activity_metrics:
                        if 'metrics' in entry:
                            metrics = entry['metrics']
                            for pos, value in enumerate(metrics):
                                if pos not in position_data:
                                    position_data[pos] = []
                                if value is not None:
                                    position_data[pos].append(value)
                    
                    # Find HR and timestamp positions
                    hr_candidates = []
                    ts_candidates = []
                    
                    for pos, values in position_data.items():
                        if values and min(values) >= 48 and max(values) <= 167:
                            # Check if all values are integers
                            all_integers = all(isinstance(v, (int, float)) and v == int(v) for v in values)
                            if all_integers:
                                unique_count = len(set(values))
                                if unique_count > 5:
                                    hr_candidates.append((pos, unique_count, min(values), max(values)))
                                    logger.info(f"collect_activities_for_date: HR candidate at position {pos}: "
                                              f"{unique_count} unique values, range {min(values)}-{max(values)}")
                        
                        if values and min(values) > 1000000000000:
                            unique_count = len(set(values))
                            if unique_count > 100:
                                ts_candidates.append((pos, unique_count, min(values), max(values)))
                                logger.info(f"collect_activities_for_date: Timestamp candidate at position {pos}: "
                                          f"{unique_count} unique values")
                    
                    if hr_candidates and ts_candidates:
                        # Sort by unique count (descending) and take the first
                        hr_candidates.sort(key=lambda x: x[1], reverse=True)
                        ts_candidates.sort(key=lambda x: x[1], reverse=True)
                        
                        hr_pos = hr_candidates[0][0]
                        ts_pos = ts_candidates[0][0]
                        
                        logger.info(f"collect_activities_for_date: Selected HR position {hr_pos}, Timestamp position {ts_pos}")
                        
                        # Extract HR time series
                        for entry in activity_metrics:
                            if 'metrics' in entry and len(entry['metrics']) > max(hr_pos, ts_pos):
                                metrics = entry['metrics']
                                timestamp = metrics[ts_pos]
                                hr_value = metrics[hr_pos]
                                
                                if timestamp is not None and hr_value is not None:
                                    hr_series.append([timestamp, int(hr_value)])
                        
                        logger.info(f"collect_activities_for_date: Extracted {len(hr_series)} HR data points")
                        
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
        
        # Now merge activity HR data into daily HR data
        merge_activity_hr_into_daily(target_date, conn, cur)
        
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