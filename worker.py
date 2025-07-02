#!/usr/bin/env python3
"""
RQ Worker for Garmin Heart Rate Analyzer
Run this script to process background jobs
"""

import os
import sys
from dotenv import load_dotenv
from rq import Worker, Queue, Connection
from redis import Redis

# Load environment variables
load_dotenv('env.local')

# Import the job functions from jobs module
from jobs import collect_garmin_data_job

if __name__ == '__main__':
    # Connect to Redis
    redis_conn = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    
    # Create a queue
    queue = Queue(connection=redis_conn)
    
    # Create a worker
    worker = Worker([queue], connection=redis_conn)
    
    print("Starting RQ worker...")
    print("Press Ctrl+C to stop")
    
    try:
        worker.work()
    except KeyboardInterrupt:
        print("\nWorker stopped by user")
    except Exception as e:
        print(f"Worker error: {e}")
        sys.exit(1) 