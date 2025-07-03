# Garmin Heart Rate Analyzer with TRIMP Calculations

A Flask web application that analyzes heart rate data from Garmin Connect using TRIMP (Training Impulse) calculations with an exponential model.

## Features

- **Google OAuth Authentication**: Secure login with user restrictions
- **TRIMP Calculations**: Exponential model based on heart rate reserve
- **Heart Rate Bucketing**: Individual 1 BPM buckets for calculations, 10 BPM buckets for presentation
- **Color-coded Zones**: Temperature scale visualization (blue to red)
- **Daily & Weekly Views**: Charts and analysis for different time periods
- **Personal HR Parameters**: Configurable resting and maximum heart rates
- **SQLite Database**: Simple file-based database for both local and production
- **Sample Data**: Built-in sample data for testing and development

## Quick Start

### Prerequisites

- Python 3.9+
- Google OAuth credentials
- Garmin Connect account

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd python-garminconnect
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google OAuth**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google+ API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URIs:
     - `http://localhost:5001/login/authorized` (for local development)
     - `https://your-app.herokuapp.com/login/authorized` (for production)

4. **Set up environment**:
   ```bash
   cp env.example env.local
   # Edit env.local with your configuration
   ```

5. **Generate encryption key**:
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
   ```
   Copy the output to your `env.local` file.

6. **Run the application**:
   ```bash
   python3 app.py
   ```

7. **Access the app**: Open http://localhost:5001 in your browser

### Production Deployment

For production deployment:

1. **Set up your hosting platform** (Heroku, Railway, etc.)
2. **Configure environment variables** with your Google OAuth credentials
3. **Deploy the application**

## Configuration

### Environment Variables

- `SECRET_KEY`: Flask secret key for sessions
- `GOOGLE_ID`: Google OAuth client ID
- `GOOGLE_SECRET`: Google OAuth client secret
- `ENCRYPTION_KEY`: Fernet key for password encryption

### User Access Control

Access is restricted to specific email addresses defined in the `ALLOWED_USERS` dictionary in `app.py`:

```python
ALLOWED_USERS = {
    'peter.buckney@gmail.com': 'Peter Buckney'
    # Add more users here as needed
}
```

### Heart Rate Parameters

Default values (configurable per user):
- **Resting HR**: 48 BPM
- **Max HR**: 167 BPM

## TRIMP Calculation

The app uses an exponential TRIMP model:

```
TRIMP = minutes × HR_reserve_ratio × 0.64 × e^(1.92 × HR_reserve_ratio)
```

Where:
- `HR_reserve_ratio = (HR - resting_HR) / (max_HR - resting_HR)`
- Only HR ≥ 80 BPM is counted (exercise threshold)

## Heart Rate Zones

### Individual Buckets (1 BPM each)
Used for precise TRIMP calculations: 90, 91, 92, ..., 160+

### Presentation Buckets (10 BPM each)
Used for charts and visualization:
- **80-89**: Midnight (very low intensity)
- **90-99**: Blue (low intensity)
- **100-109**: Light blue
- **110-119**: Cyan
- **120-129**: Green (moderate intensity)
- **130-139**: Orange
- **140-149**: Dark orange
- **150-159**: Red (high intensity)
- **160+**: Dark red (very high intensity)

## API Endpoints

- `GET /`: Main dashboard (requires authentication)
- `GET /login`: Google OAuth login
- `GET /logout`: Logout user
- `POST /collect-data`: Collect heart rate data for a date
- `GET /api/data/<date>`: Get data for specific date
- `GET /api/weekly-data/<start_date>`: Get weekly data
- `GET/POST /api/hr-parameters`: Get/update HR parameters
- `GET/POST /setup-garmin`: Setup Garmin credentials
- `GET/POST /setup-hr-parameters`: Setup HR parameters

## Database Schema

### Tables
- `users`: User information with Google OAuth IDs
- `garmin_credentials`: Encrypted Garmin login credentials
- `user_hr_parameters`: Personal HR settings
- `heart_rate_data`: Heart rate data with TRIMP calculations

### Key Fields
- `individual_hr_buckets`: JSON of 1 BPM buckets
- `presentation_buckets`: JSON of 10 BPM buckets with minutes and TRIMP
- `trimp_data`: JSON of TRIMP values per HR
- `total_trimp`: Daily TRIMP score
- `activity_type`: Classification (long_low_intensity, short_high_intensity, mixed)

## Development

### Testing TRIMP Calculations

Run the test script to verify calculations:
```bash
python3 test_trimp.py
```

### Adding Real Garmin Data

To integrate real Garmin Connect data collection:

1. **Setup Garmin credentials** in the web interface
2. **Modify the `collect_data` route** in `app.py` to fetch real data
3. **Handle 2FA authentication** if needed

### Adding New Users

To add new users to the application:

1. **Edit the `ALLOWED_USERS` dictionary** in `app.py`
2. **Add the user's email and display name**:
   ```python
   ALLOWED_USERS = {
       'peter.buckney@gmail.com': 'Peter Buckney',
       'newuser@example.com': 'New User Name'
   }
   ```

## Security Features

- **Google OAuth Authentication**: Secure login with Google accounts
- **User Access Control**: Only authorized email addresses can access the app
- **Encrypted Credentials**: Garmin passwords are encrypted using Fernet
- **Session Management**: Secure session handling with Flask

## License

MIT License - see LICENSE file for details.
