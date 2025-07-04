"""
Configuration settings for the Garmin HR Analysis application.
"""

# Note: HR values (resting_hr, max_hr) are stored in the database and retrieved dynamically
# This config only contains system constants that don't change

# Time Constants (in seconds)
TIME_CONFIG = {
    'GAP_THRESHOLD_SECONDS': 300,  # 5 minutes - gap threshold for TRIMP calculation
    'ACTIVITY_MATCH_THRESHOLD_MS': 30000,  # 30 seconds - activity timestamp matching
    'TIMESTAMP_MULTIPLIER': 1000,  # Convert seconds to milliseconds
}

# API and Database Limits
API_CONFIG = {
    'MAX_DATE_RANGE_DAYS': 30,
    'MAX_ACTIVITIES_LIMIT': 9999,
    'UNIQUE_TIMESTAMP_THRESHOLD': 100,
}

# Server Configuration
SERVER_CONFIG = {
    'DEFAULT_PORT': 5001,
    'TEST_PORT': 5000,
    'HOST': '0.0.0.0',
    'DEBUG': True,
}

# Frontend Configuration
FRONTEND_CONFIG = {
    'DEFAULT_CHART_HEIGHT': '300px',
    'GAP_VISUALIZATION_OFFSET_MS': 1000,  # 1 minute offset for gap visualization
    'CHART_STEP_SIZE_THRESHOLD': 500,
} 