# Garmin Heart Rate Analyzer - Quick Start

This guide will get you up and running with the Garmin Heart Rate Analyzer demo in minutes.

## Prerequisites

- Python 3.9+
- Garmin Connect account with heart rate data
- Garmin device (Forerunner, Fenix, etc.) that syncs to Garmin Connect

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements_working.txt
```

### 2. Configure Credentials

Create a `test.env` file with your Garmin credentials:

```bash
# test.env
GARMIN_EMAIL=your.email@example.com
GARMIN_PASSWORD=your_password
```

### 3. Test the Connection

Run the demo script to verify everything works:

```bash
python3 demo.py
```

You should see:
- ✅ Authentication successful
- ✅ Heart rate data retrieved
- ✅ Zone analysis completed
- ✅ Daily score calculated

### 4. Start the Web App

```bash
python3 app_simple.py
```

Visit: http://localhost:5001/test-garmin

## What You'll See

### Demo Script Output
```
🎯 Garmin Connect Demo
============================================================
📧 Email: your.email@example.com
🔐 Attempting to authenticate...

📋 Authentication
----------------------------------------
✅ Authentication successful!

📋 Data Retrieval
----------------------------------------
📅 Fetching heart rate data for: 2025-07-01
✅ Heart rate data retrieved successfully!
📊 Total samples: 703
💓 Resting HR: 58 BPM
📈 Min HR: 45 BPM
📉 Max HR: 145 BPM

📋 Heart Rate Analysis
----------------------------------------
📊 Heart Rate Zones:
   90-100 BPM: 84 samples
   100-110 BPM: 45 samples
   110-120 BPM: 8 samples
   120-130 BPM: 2 samples

🎯 Daily Score: 124.1
🏃 Activity Type: long_low_intensity
💡 Extended periods in lower heart rate zones (good for endurance)
```

### Web App Response
```json
{
  "status": "success",
  "message": "Garmin connection and analysis working!",
  "data": {
    "date": "2025-07-01",
    "heart_rate_samples": 703,
    "zone_buckets": {
      "90-100": 84,
      "100-110": 45,
      "110-120": 8,
      "120-130": 2
    },
    "daily_score": 124.1,
    "activity_type": "long_low_intensity"
  }
}
```

## Understanding Your Data

### Heart Rate Zones
- **90-100 BPM**: Very light activity (walking, light chores)
- **100-110 BPM**: Light activity (easy jogging, cycling)
- **110-120 BPM**: Moderate activity (steady running, cycling)
- **120-130 BPM**: Moderate-high activity (tempo running)
- **130-140 BPM**: High activity (threshold training)
- **140-150 BPM**: Very high activity (interval training)
- **150+ BPM**: Maximum effort (sprint intervals)

### Daily Score
- **0-50**: Very light day
- **50-100**: Light activity day
- **100-150**: Moderate activity day
- **150-200**: High activity day
- **200+**: Very intense day

### Activity Types
- **long_low_intensity**: Extended periods in lower zones (endurance training)
- **short_high_intensity**: Brief periods in higher zones (interval training)
- **mixed**: Balanced distribution (general fitness)

## Troubleshooting

### Authentication Issues
- Verify your Garmin Connect credentials
- Check if 2FA is enabled (the app will prompt for the code)
- Ensure your device has synced recently

### No Data Available
- Make sure your Garmin device was worn on the test date
- Check that data has synced to Garmin Connect
- Try a different date (yesterday or earlier)

### Port Issues
- If port 5001 is busy, the app will tell you
- You can modify the port in `app_simple.py`

## Next Steps

Once the demo is working, you can:

1. **Set up the full application** with database and OAuth
2. **Customize heart rate zones** for your fitness level
3. **Deploy to Heroku** for web access
4. **Add more analysis features** like trends and comparisons

## Files Overview

- `demo.py` - Command-line demo script
- `app_simple.py` - Simple web app for testing
- `requirements_working.txt` - Minimal dependencies
- `test.env` - Your Garmin credentials (create this)
- `garminconnect/` - Local Garmin Connect library

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your Garmin device has synced data
3. Ensure your internet connection is stable
4. Check that your Garmin Connect account is active 