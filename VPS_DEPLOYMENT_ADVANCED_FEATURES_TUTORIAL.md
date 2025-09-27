
# Depanku VPS Deployment & Advanced Features Tutorial

## Overview
This tutorial covers deploying the Depanku Flask application to a VPS and explains the advanced features implemented, including AI integration, Firebase authentication, and real-time capabilities.

## Project Structure
```
depanku/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── firebase_config.json        # Firebase configuration
├── openrouter_config.py        # OpenRouter AI configuration
├── ai_analysis_service.py      # AI analysis service
├── moderation_service.py       # Content moderation service
├── static/                     # Static assets (CSS, JS, images)
├── templates/                  # HTML templates
└── LANDING_PAGE_REDESIGN_TUTORIAL.md  # Previous tutorial
```

## Part 1: VPS Deployment

### 1.1 Choosing a VPS Provider
Recommended providers:
- **DigitalOcean**: Simple and developer-friendly
- **AWS EC2**: Scalable and feature-rich
- **Linode**: Competitive pricing and performance
- **Vultr**: High-performance SSD servers

### 1.2 Server Setup (Ubuntu 20.04/22.04)

#### Step 1: Server Initialization
```bash
# Connect to your VPS via SSH
ssh root@your-server-ip

# Update system packages
apt update && apt upgrade -y

# Install essential packages
apt install -y nginx python3-pip python3-venv certbot python3-certbot-nginx git
```

#### Step 2: Create Deployment User
```bash
# Create a new user for deployment
adduser deploy
usermod -aG sudo deploy

# Switch to deploy user
su - deploy
```

#### Step 3: Clone Repository
```bash
# Clone your Depanku repository
git clone https://github.com/your-username/depanku.git
cd depanku
```

#### Step 4: Python Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 1.3 Nginx Configuration

#### Create Nginx Config
```bash
sudo nano /etc/nginx/sites-available/depanku
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/deploy/depanku/static;
    }
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/depanku /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 1.4 Gunicorn Setup

#### Create Gunicorn Service
```bash
sudo nano /etc/systemd/system/depanku.service
```

```ini
[Unit]
Description=Depanku Gunicorn Service
After=network.target

[Service]
User=deploy
Group=www-data
WorkingDirectory=/home/deploy/depanku
Environment="PATH=/home/deploy/depanku/venv/bin"
ExecStart=/home/deploy/depanku/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 app:app

[Install]
WantedBy=multi-user.target
```

```bash
# Start and enable service
sudo systemctl start depanku
sudo systemctl enable depanku
sudo systemctl status depanku
```

### 1.5 SSL Certificate with Let's Encrypt
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 1.6 Environment Configuration
```bash
# Create environment file
nano .env
```

```ini
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
FIREBASE_API_KEY=your-firebase-api-key
OPENROUTER_API_KEY=your-openrouter-api-key
ALGOLIA_APP_ID=your-algolia-app-id
ALGOLIA_API_KEY=your-algolia-api-key
```

### 1.7 Deployment Script
Create a deployment script for easy updates:

```bash
nano deploy.sh
```

```bash
#!/bin/bash
echo "Deploying Depanku..."

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Collect static files (if needed)
python -m flask collectstatic

# Restart service
sudo systemctl restart depanku

echo "Deployment complete!"
```

```bash
chmod +x deploy.sh
```

## Part 2: Advanced Features Explained

### 2.1 AI Integration with OpenRouter

#### Configuration
```python
# openrouter_config.py
import os
from openai import OpenAI

class OpenRouterClient:
    def __init__(self):
