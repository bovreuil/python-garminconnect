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
from datetime import datetime, date
from garminconnect import Garmin
from cryptography.fernet import Fernet
import os
from models import HeartRateAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        if not heart_rate_data or 'heartRateValues' not in heart_rate_data:
            error_msg = f"No heart rate data found for {target_date}"
            logger.warning(f"collect_garmin_data_job: {error_msg}")
            cur.execute("""
                UPDATE background_jobs 
                SET status = 'completed', result = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (json.dumps({'message': error_msg}), job_id))
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
        
        # Save to database
        cur.execute("""
            INSERT OR REPLACE INTO heart_rate_data 
            (date, individual_hr_buckets, presentation_buckets, trimp_data, 
             total_trimp, daily_score, activity_type, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            target_date,
            json.dumps(analysis_result['individual_hr_buckets']),
            json.dumps(analysis_result['presentation_buckets']),
            json.dumps(analysis_result['trimp_data']),
            analysis_result['total_trimp'],
            analysis_result['daily_score'],
            analysis_result['activity_type']
        ))
        
        conn.commit()
        logger.info(f"collect_garmin_data_job: Data saved to database successfully")
        
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