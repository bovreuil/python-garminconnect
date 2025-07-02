#!/bin/bash

# Garmin Heart Rate Analyzer - Heroku Deployment Script

echo "🚀 Deploying Garmin Heart Rate Analyzer to Heroku..."

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI is not installed. Please install it first:"
    echo "   https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if git repository is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Please initialize git first:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    exit 1
fi

# Get app name from user
read -p "Enter your Heroku app name (or press Enter to auto-generate): " app_name

if [ -z "$app_name" ]; then
    echo "Creating Heroku app with auto-generated name..."
    heroku create
else
    echo "Creating Heroku app: $app_name"
    heroku create $app_name
fi

# Add PostgreSQL addon
echo "📦 Adding PostgreSQL addon..."
heroku addons:create heroku-postgresql:mini

# Get environment variables from user
echo "🔧 Setting up environment variables..."

read -p "Enter your SECRET_KEY (or press Enter to generate): " secret_key
if [ -z "$secret_key" ]; then
    secret_key=$(python -c "import secrets; print(secrets.token_hex(32))")
    echo "Generated SECRET_KEY: $secret_key"
fi

read -p "Enter your GOOGLE_ID: " google_id
read -p "Enter your GOOGLE_SECRET: " google_secret

read -p "Enter your ENCRYPTION_KEY (or press Enter to generate): " encryption_key
if [ -z "$encryption_key" ]; then
    encryption_key=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    echo "Generated ENCRYPTION_KEY: $encryption_key"
fi

# Set environment variables
echo "Setting environment variables..."
heroku config:set SECRET_KEY="$secret_key"
heroku config:set GOOGLE_ID="$google_id"
heroku config:set GOOGLE_SECRET="$google_secret"
heroku config:set ENCRYPTION_KEY="$encryption_key"

# Deploy the application
echo "🚀 Deploying application..."
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# Open the application
echo "🌐 Opening application..."
heroku open

echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Complete Google OAuth setup in Google Cloud Console"
echo "2. Add your app's URL to authorized redirect URIs"
echo "3. Test the application"
echo ""
echo "🔍 To check logs: heroku logs --tail"
echo "🔧 To update environment variables: heroku config:set VAR=value" 