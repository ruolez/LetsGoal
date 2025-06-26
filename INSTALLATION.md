# LetsGoal Complete Installation Guide

This guide provides comprehensive instructions for installing LetsGoal on Ubuntu servers using the automated installation scripts.

## Quick Start

For the fastest installation, run the main installation script as root:

```bash
sudo ./install-letsgoal.sh
```

The script will guide you through an interactive setup process.

## Prerequisites

- Ubuntu 18.04 LTS or newer
- Root access (sudo)
- Internet connection
- At least 2GB RAM and 10GB disk space

For domain installations:
- Domain name pointing to your server
- Valid email address for SSL certificates

## Installation Files

| File | Purpose |
|------|---------|
| `install-letsgoal.sh` | Main interactive installation script |
| `docker-compose.prod.yml` | Production Docker configuration |
| `nginx.conf.template` | Nginx reverse proxy template |
| `.env.template` | Environment variables template |
| `ssl-setup.sh` | SSL certificate management |
| `backup-restore.sh` | Database backup/restore utilities |
| `firewall-setup.sh` | Firewall configuration |

## Installation Modes

### 1. Clean Installation

Fresh installation with complete environment setup:

```bash
sudo ./install-letsgoal.sh
# Choose: Clean Install
```

### 2. Update Installation

Update existing installation while preserving data:

```bash
sudo ./install-letsgoal.sh
# Choose: Update
```

This will:
- Backup the current database
- Pull latest code updates
- Rebuild Docker containers
- Restore the database
- Apply any new migrations

### 3. Uninstallation

Complete removal of LetsGoal:

```bash
sudo ./install-letsgoal.sh
# Choose: Uninstall
```

## Deployment Types

### Local Network Deployment

For LAN-only access (recommended for development):

- **Features**: Direct access via IP:5001
- **Security**: Firewall configured for local access
- **SSL**: Not available (IP addresses)
- **CORS**: Configured for local network IPs

**Access**: `http://YOUR_IP:5001`

### Web Domain Deployment

For internet access with domain name:

- **Features**: Professional domain access
- **Security**: Full SSL with Let's Encrypt
- **Firewall**: Hardened for internet exposure
- **CORS**: Configured for your domain

**Access**: `https://yourdomain.com` or `http://yourdomain.com`

## Configuration Options

### Environment Variables

The installation creates a `.env` file with configuration:

```bash
# Core settings
SECRET_KEY=auto-generated-secure-key
CORS_ORIGINS=configured-based-on-deployment
DEPLOYMENT_TYPE=local|domain
DOMAIN_OR_IP=your-domain-or-ip
USE_SSL=y|n

# Security
SESSION_COOKIE_SECURE=true|false
RATELIMIT_DEFAULT=100

# Optional features
AWS_ACCESS_KEY_ID=for-sms-notifications
SMTP_SERVER=for-email-notifications
```

### SSL Certificate Management

For domain deployments with SSL:

```bash
# Manual SSL operations
sudo ./ssl-setup.sh --domain yourdomain.com --email admin@yourdomain.com

# Check certificate status
sudo ./ssl-setup.sh --status --domain yourdomain.com

# Renew certificate
sudo ./ssl-setup.sh --renew --domain yourdomain.com

# Remove certificate
sudo ./ssl-setup.sh --remove --domain yourdomain.com
```

### Database Management

```bash
# Create backup
sudo ./backup-restore.sh backup

# Create named backup
sudo ./backup-restore.sh backup before_update

# List backups
sudo ./backup-restore.sh list

# Restore from backup
sudo ./backup-restore.sh restore /path/to/backup.db

# Verify database
sudo ./backup-restore.sh verify

# Cleanup old backups
sudo ./backup-restore.sh cleanup 7
```

### Firewall Configuration

```bash
# Interactive firewall setup
sudo ./firewall-setup.sh setup

# Apply configuration for local network
sudo ./firewall-setup.sh apply --deployment local

# Apply configuration for domain with rate limiting
sudo ./firewall-setup.sh apply --deployment domain --rate-limit

# Show firewall status
sudo ./firewall-setup.sh status
```

## Manual Installation Steps

If you prefer manual installation:

### 1. System Preparation

```bash
# Update system
sudo apt-get update -y && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y curl wget git ufw nginx certbot \
    python3-certbot-nginx software-properties-common \
    apt-transport-https ca-certificates gnupg lsb-release

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Install Docker Compose
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d '"' -f 4)
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Application Setup

```bash
# Create installation directory
sudo mkdir -p /opt/letsgoal
cd /opt/letsgoal

# Copy application files
sudo cp -r /path/to/letsgoal/* .

# Create environment file
sudo cp .env.template .env
sudo nano .env  # Edit configuration

# Build and start
sudo docker-compose -f docker-compose.prod.yml up --build -d
```

### 3. SSL Setup (for domain deployments)

```bash
# Stop nginx
sudo systemctl stop nginx

# Obtain certificate
sudo certbot certonly --standalone --non-interactive --agree-tos \
    --email admin@yourdomain.com -d yourdomain.com

# Configure nginx
sudo ./ssl-setup.sh --domain yourdomain.com --email admin@yourdomain.com

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 4. Firewall Setup

```bash
# Reset and configure firewall
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow necessary ports
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# For local deployments, also allow:
sudo ufw allow 5001/tcp

# Enable firewall
sudo ufw --force enable
```

## Post-Installation

### Verify Installation

1. **Check container status**:
   ```bash
   docker ps
   docker logs letsgoal-backend
   ```

2. **Test application access**:
   - Local: `http://YOUR_IP:5001`
   - Domain: `https://yourdomain.com`

3. **Verify SSL** (domain deployments):
   ```bash
   curl -I https://yourdomain.com
   ```

4. **Check firewall**:
   ```bash
   sudo ufw status verbose
   ```

### First Login

1. Access the application URL
2. Register the first user account
3. This account becomes the administrator

### Monitoring

- **Application logs**: `docker logs letsgoal-backend`
- **Nginx logs**: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **Firewall logs**: `/var/log/ufw.log`
- **SSL logs**: `/var/log/letsencrypt/letsencrypt.log`

## Troubleshooting

### Common Issues

1. **Container won't start**:
   ```bash
   docker logs letsgoal-backend
   # Check for port conflicts, permission issues
   ```

2. **SSL certificate errors**:
   ```bash
   sudo certbot certificates
   sudo nginx -t
   # Verify DNS pointing to server
   ```

3. **Database issues**:
   ```bash
   sudo ./backup-restore.sh verify
   # Check database permissions and integrity
   ```

4. **Firewall blocking access**:
   ```bash
   sudo ufw status
   sudo ./firewall-setup.sh status
   ```

### Getting Help

1. Check the application logs
2. Verify all services are running
3. Test network connectivity
4. Review configuration files

## Maintenance

### Regular Tasks

1. **Weekly**: Check application logs
2. **Monthly**: Verify backups and test restore
3. **Quarterly**: Update system packages
4. **SSL**: Certificates auto-renew (monitor logs)

### Updates

```bash
# Backup before updates
sudo ./backup-restore.sh backup before_update

# Pull latest code
git pull origin main

# Run update installation
sudo ./install-letsgoal.sh
# Choose: Update
```

### Security

1. Keep system packages updated
2. Monitor firewall logs for suspicious activity
3. Review SSL certificate status monthly
4. Regularly backup the database
5. Monitor disk space usage

## Performance Optimization

### For High Traffic

1. **Increase container resources**:
   Edit `docker-compose.prod.yml` to add resource limits

2. **Enable nginx caching**:
   Add caching directives to nginx configuration

3. **Database optimization**:
   Consider migrating to PostgreSQL for better performance

4. **Load balancing**:
   Set up multiple application containers behind nginx

### Monitoring

Consider adding monitoring tools:
- Prometheus + Grafana for metrics
- ELK stack for log analysis
- Uptime monitoring services

## Security Considerations

1. **Regular Updates**: Keep all components updated
2. **Strong Passwords**: Use strong passwords for admin accounts
3. **Firewall**: Keep firewall rules minimal and specific
4. **SSL**: Always use SSL for production deployments
5. **Backups**: Encrypt backups and store them securely
6. **Access Logs**: Monitor access logs for suspicious activity

## Support

For issues or questions:
1. Check this documentation
2. Review application logs
3. Test with minimal configuration
4. Report issues with detailed logs and configuration