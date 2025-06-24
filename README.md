# LetsGoal - Goal Tracking & Productivity Application

A comprehensive goal tracking and productivity application featuring subgoal management, progress tracking, motivational quotes, and collaborative goal sharing.

## Features

- **Goal Management**: Create, edit, and track goals with hierarchical subgoals
- **Progress Tracking**: Visual progress indicators and 7-day trend charts
- **Tagging System**: Organize goals with color-coded tags
- **Goal Sharing**: Collaborate by sharing goals with other users
- **Archive System**: Archive completed goals for historical reference
- **Dark/Light Theme**: Automatic theme switching with system preference detection
- **Event Tracking**: Comprehensive activity logging and audit trails
- **Motivational Elements**: Daily rotating motivational quotes with animated lotus logo

## Technology Stack

- **Backend**: Python Flask with SQLAlchemy ORM
- **Frontend**: Vanilla JavaScript with Tailwind CSS
- **Database**: SQLite with automatic migrations
- **Authentication**: Flask-Login with session management
- **Charts**: Chart.js for progress visualization
- **Containerization**: Docker and Docker Compose

## Environment Setup Instructions

### 1. Windows with Docker

#### Prerequisites
- [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- [Git for Windows](https://git-scm.com/download/win)

#### Installation Steps

1. **Clone the repository**
   ```powershell
   git clone https://github.com/ruolez/LetsGoal.git
   cd LetsGoal
   ```

2. **Start the application**
   ```powershell
   docker-compose up --build -d
   ```

3. **Access the application**
   ```
   http://localhost:5001
   ```

#### Production Setup with SSL (Windows)

1. **Install SSL certificates**
   ```powershell
   # Create SSL directory
   mkdir ssl
   
   # Generate self-signed certificate (for testing)
   # For production, use certificates from a trusted CA
   openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
   ```

2. **Update docker-compose.yml for SSL**
   ```yaml
   # Add to docker-compose.yml
   version: '3.8'
   services:
     app:
       # ... existing configuration
       ports:
         - "5001:5000"
         - "5443:5443"  # HTTPS port
       volumes:
         - ./ssl:/app/ssl:ro
       environment:
         - SSL_CERT_PATH=/app/ssl/cert.pem
         - SSL_KEY_PATH=/app/ssl/key.pem
   ```

3. **Access via HTTPS**
   ```
   https://localhost:5443
   ```

### 2. Linux with Docker

#### Prerequisites
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose git

# CentOS/RHEL/Fedora
sudo dnf install docker docker-compose git

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER
```

#### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/ruolez/LetsGoal.git
   cd LetsGoal
   ```

2. **Start the application**
   ```bash
   docker-compose up --build -d
   ```

3. **Access the application**
   ```
   http://localhost:5001
   ```

#### Production Setup with SSL (Linux)

1. **Install Certbot for Let's Encrypt SSL**
   ```bash
   # Ubuntu/Debian
   sudo apt install certbot
   
   # CentOS/RHEL/Fedora
   sudo dnf install certbot
   ```

2. **Obtain SSL certificate**
   ```bash
   # Replace yourdomain.com with your actual domain
   sudo certbot certonly --standalone -d yourdomain.com
   
   # Certificates will be saved to:
   # /etc/letsencrypt/live/yourdomain.com/fullchain.pem
   # /etc/letsencrypt/live/yourdomain.com/privkey.pem
   ```

3. **Create production docker-compose.prod.yml**
   ```yaml
   version: '3.8'
   services:
     app:
       build: .
       ports:
         - "80:5000"
         - "443:5443"
       volumes:
         - ./database:/app/database
         - /etc/letsencrypt/live/yourdomain.com:/app/ssl:ro
       environment:
         - FLASK_ENV=production
         - SSL_CERT_PATH=/app/ssl/fullchain.pem
         - SSL_KEY_PATH=/app/ssl/privkey.pem
       restart: unless-stopped
   ```

4. **Start production environment**
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```

5. **Setup SSL renewal cron job**
   ```bash
   sudo crontab -e
   # Add this line for automatic renewal:
   0 12 * * * /usr/bin/certbot renew --quiet && docker-compose -f /path/to/LetsGoal/docker-compose.prod.yml restart
   ```

### 3. Linux Native Installation

#### Prerequisites
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv sqlite3 git nginx

# CentOS/RHEL/Fedora
sudo dnf install python3 python3-pip sqlite git nginx
```

#### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/ruolez/LetsGoal.git
   cd LetsGoal
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   mkdir -p database
   python backend/app.py
   # Stop with Ctrl+C after database is created
   ```

5. **Create systemd service**
   ```bash
   sudo tee /etc/systemd/system/letsgoal.service > /dev/null <<EOF
   [Unit]
   Description=LetsGoal Application
   After=network.target
   
   [Service]
   Type=simple
   User=$USER
   WorkingDirectory=/path/to/LetsGoal
   Environment=PATH=/path/to/LetsGoal/venv/bin
   ExecStart=/path/to/LetsGoal/venv/bin/python backend/app.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   EOF
   
   # Update paths in the service file
   sudo sed -i "s|/path/to/LetsGoal|$(pwd)|g" /etc/systemd/system/letsgoal.service
   sudo sed -i "s|User=.*|User=$(whoami)|g" /etc/systemd/system/letsgoal.service
   
   # Start the service
   sudo systemctl daemon-reload
   sudo systemctl enable letsgoal
   sudo systemctl start letsgoal
   ```

#### Production Setup with Nginx and SSL (Linux Native)

1. **Install and configure Nginx**
   ```bash
   # Create Nginx configuration
   sudo tee /etc/nginx/sites-available/letsgoal > /dev/null <<EOF
   server {
       listen 80;
       server_name yourdomain.com www.yourdomain.com;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host \$host;
           proxy_set_header X-Real-IP \$remote_addr;
           proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto \$scheme;
       }
   }
   EOF
   
   # Enable the site
   sudo ln -s /etc/nginx/sites-available/letsgoal /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

2. **Install SSL certificate**
   ```bash
   # Install Certbot Nginx plugin
   sudo apt install python3-certbot-nginx  # Ubuntu/Debian
   # OR
   sudo dnf install python3-certbot-nginx  # CentOS/RHEL/Fedora
   
   # Obtain and install SSL certificate
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

3. **Configure firewall**
   ```bash
   # Ubuntu/Debian (ufw)
   sudo ufw allow 'Nginx Full'
   sudo ufw enable
   
   # CentOS/RHEL/Fedora (firewalld)
   sudo firewall-cmd --permanent --add-service=http
   sudo firewall-cmd --permanent --add-service=https
   sudo firewall-cmd --reload
   ```

## Application Management

### Docker Commands
```bash
# View logs
docker logs letsgoal-backend

# Restart application
docker-compose restart

# Update application
git pull
docker-compose down
docker-compose up --build -d

# Backup database
docker cp letsgoal-backend:/app/database/letsgoal.db ./backup-$(date +%Y%m%d).db
```

### Native Installation Commands
```bash
# Check service status
sudo systemctl status letsgoal

# View logs
sudo journalctl -u letsgoal -f

# Restart service
sudo systemctl restart letsgoal

# Update application
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart letsgoal

# Backup database
cp database/letsgoal.db backup-$(date +%Y%m%d).db
```

### Database Operations
```bash
# Docker environment
docker exec letsgoal-backend python backend/migrations/add_event_tracking.py
docker exec letsgoal-backend python backend/migrations/add_tagging_system.py
docker exec letsgoal-backend python backend/migrations/add_archived_date.py
docker exec letsgoal-backend python backend/migrations/add_goal_sharing.py

# Native environment
source venv/bin/activate
python backend/migrations/add_event_tracking.py
python backend/migrations/add_tagging_system.py
python backend/migrations/add_archived_date.py
python backend/migrations/add_goal_sharing.py
```

### Testing
```bash
# Docker environment
docker exec letsgoal-backend python -m pytest tests/

# Native environment
source venv/bin/activate
python -m pytest tests/
```

## Security Considerations

### Production Recommendations
1. **Use HTTPS in production** with valid SSL certificates
2. **Set secure Flask configuration**:
   ```python
   app.config['SESSION_COOKIE_SECURE'] = True
   app.config['SESSION_COOKIE_HTTPONLY'] = True
   app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
   ```
3. **Use environment variables** for sensitive configuration
4. **Regular database backups**
5. **Keep dependencies updated**
6. **Use a reverse proxy** (Nginx) for better security and performance
7. **Configure firewall** to allow only necessary ports

### Environment Variables
```bash
# Optional environment variables
export FLASK_SECRET_KEY="your-secret-key-here"
export DATABASE_URL="sqlite:///database/letsgoal.db"
export FLASK_ENV="production"
export SSL_CERT_PATH="/path/to/cert.pem"
export SSL_KEY_PATH="/path/to/key.pem"
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Find process using port 5001
   sudo lsof -i :5001
   # Kill the process or change port in docker-compose.yml
   ```

2. **Database permission issues**
   ```bash
   # Fix database permissions
   sudo chown -R $USER:$USER database/
   chmod 644 database/letsgoal.db
   ```

3. **SSL certificate issues**
   ```bash
   # Check certificate validity
   openssl x509 -in ssl/cert.pem -text -noout
   
   # Verify certificate chain
   openssl verify -CAfile ssl/cert.pem ssl/cert.pem
   ```

4. **Docker issues**
   ```bash
   # Clean Docker cache
   docker system prune -a
   
   # Rebuild without cache
   docker-compose build --no-cache
   ```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section above
- Review the CLAUDE.md file for development guidance