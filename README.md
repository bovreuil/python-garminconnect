# Garmin Heart Rate Analyzer

A Flask web application that analyzes heart rate data from Garmin Connect devices (like Forerunner 955 with HRM Pro Plus) to provide insights into daily activity patterns and fitness scores.

## Features

- 🔐 **Google SSO Authentication** - Secure login using Google OAuth
- 📊 **Heart Rate Zone Analysis** - Bucket heart rate data into custom zones (90-100, 100-110, etc.)
- 🎯 **Daily Score Calculation** - Weighted scoring based on time spent in each zone
- 📈 **Activity Type Classification** - Determine if activity was long low-intensity or short high-intensity
- 🗄️ **PostgreSQL Storage** - Secure data storage with encrypted credentials
- 🔒 **2FA Support** - Full support for Garmin Connect two-factor authentication
- 📱 **Responsive Web Interface** - Modern, mobile-friendly dashboard with charts
- ☁️ **Heroku Ready** - Easy deployment to Heroku with PostgreSQL

## Screenshots

### Dashboard
- Heart rate zone histogram
- Daily activity score
- Activity type classification
- Interactive charts and visualizations

### Setup Process
- Google OAuth login
- Garmin Connect credential setup
- 2FA handling
- Secure credential storage

## Technology Stack

- **Backend**: Flask, Python 3.11
- **Database**: PostgreSQL
- **Authentication**: Google OAuth, Garmin Connect API
- **Frontend**: Bootstrap 5, Chart.js
- **Data Collection**: python-garminconnect library
- **Security**: Fernet encryption for credentials
- **Deployment**: Heroku

## Installation & Setup

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Google OAuth credentials
- Garmin Connect account

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd garmin-heart-rate-analyzer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Generate encryption key**
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   # Add the output to your .env file as ENCRYPTION_KEY
   ```

5. **Set up Google OAuth**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google+ API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URIs:
     - `http://localhost:5000/login/authorized` (for local development)
     - `https://your-app.herokuapp.com/login/authorized` (for production)
   - Copy Client ID and Client Secret to your `.env` file

6. **Set up PostgreSQL**
   ```bash
   # Create database
   createdb garmin_hr_db
   
   # Update DATABASE_URL in .env
   DATABASE_URL=postgresql://username:password@localhost:5432/garmin_hr_db
   ```

7. **Run the application**
   ```bash
   python3 app.py
   ```

8. **Access the application**
   - Open http://localhost:5000
   - Login with Google
   - Setup Garmin Connect credentials
   - Start analyzing your heart rate data!

### Heroku Deployment

1. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

2. **Add PostgreSQL addon**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

3. **Set environment variables**
   ```bash
   heroku config:set SECRET_KEY="your-secret-key"
   heroku config:set GOOGLE_ID="your-google-oauth-client-id"
   heroku config:set GOOGLE_SECRET="your-google-oauth-client-secret"
   heroku config:set ENCRYPTION_KEY="your-encryption-key"
   ```

4. **Deploy**
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push heroku main
   ```

5. **Open the app**
   ```bash
   heroku open
   ```

## Usage

### First Time Setup

1. **Login with Google** - Use your Google account to authenticate
2. **Setup Garmin Credentials** - Enter your Garmin Connect email and password
3. **Handle 2FA** - If you have 2FA enabled, enter your authentication code
4. **Start Collecting Data** - Select a date and collect heart rate data

### Daily Analysis

1. **Select Date** - Choose the date you want to analyze
2. **Collect Data** - Click "Collect Data" to fetch from Garmin Connect
3. **View Results** - See your heart rate zones, daily score, and activity type

### Understanding Your Data

#### Heart Rate Zones
- **90-100 BPM**: Very light activity
- **100-110 BPM**: Light activity
- **110-120 BPM**: Moderate activity
- **120-130 BPM**: Moderate-high activity
- **130-140 BPM**: High activity
- **140-150 BPM**: Very high activity
- **150+ BPM**: Maximum effort

#### Daily Score
The daily score is calculated using weighted averages:
- Higher heart rate zones have higher weights
- Score ranges from 0-400
- Based on time distribution across zones

#### Activity Types
- **Long Low-Intensity**: Extended periods in lower heart rate zones
- **Short High-Intensity**: Brief periods in higher heart rate zones
- **Mixed**: Balanced distribution across zones

## API Endpoints

### Authentication
- `GET /login` - Google OAuth login
- `GET /logout` - Logout user
- `GET /login/authorized` - OAuth callback

### Garmin Setup
- `GET /setup-garmin` - Setup Garmin credentials form
- `POST /setup-garmin` - Save Garmin credentials
- `POST /mfa` - Handle 2FA code

### Data Collection
- `POST /collect-data` - Collect heart rate data for a date
- `GET /api/data/<date>` - Get stored data for a date

## Security Features

- **Encrypted Credentials**: Garmin passwords are encrypted using Fernet
- **OAuth Authentication**: Secure Google SSO
- **Session Management**: Secure session handling
- **Database Security**: PostgreSQL with proper access controls
- **2FA Support**: Full support for Garmin Connect 2FA

## Data Privacy

- Your Garmin credentials are encrypted and stored securely
- Heart rate data is stored in your own database
- No data is shared with third parties
- You can delete your data at any time

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Google OAuth credentials
   - Check redirect URIs in Google Cloud Console
   - Ensure environment variables are set correctly

2. **Garmin Connect Issues**
   - Verify your Garmin Connect credentials
   - Check if 2FA is enabled and enter correct code
   - Ensure your device has synced data to Garmin Connect

3. **Database Connection Issues**
   - Verify DATABASE_URL is correct
   - Check PostgreSQL is running
   - Ensure database exists and is accessible

4. **Heroku Deployment Issues**
   - Check Heroku logs: `heroku logs --tail`
   - Verify all environment variables are set
   - Ensure PostgreSQL addon is provisioned

### Getting Help

- Check the logs for detailed error messages
- Verify all environment variables are set correctly
- Ensure your Garmin device has synced recent data
- Check that your Google OAuth credentials are properly configured

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) - Garmin Connect API wrapper
- [Garth](https://github.com/matin/garth) - Garmin authentication library
- Flask and the Python community for excellent tools and documentation
