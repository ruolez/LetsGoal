#!/bin/bash

# LetsGoal Complete Installation Script for Ubuntu Server
# Supports local network and web domain deployment with Docker
# Handles SSL, CORS configuration, backup/restore, and container management

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/letsgoal"
BACKUP_DIR="/opt/letsgoal/backups"
LOG_FILE="/var/log/letsgoal-install.log"
CONFIG_FILE="/opt/letsgoal/.env"
NGINX_CONF="/etc/nginx/sites-available/letsgoal"
NGINX_ENABLED="/etc/nginx/sites-enabled/letsgoal"

# Installation configuration
DEPLOYMENT_TYPE=""
DOMAIN_OR_IP=""
USE_SSL=""
INSTALL_MODE=""
EXISTING_DB_BACKUP=""

# Docker configuration
DOCKER_COMPOSE_FILE=""
CONTAINER_NAME="letsgoal-backend"
NGINX_CONTAINER_NAME="letsgoal-nginx"

#==============================================================================
# Utility Functions
#==============================================================================

log() {
    echo -e "${WHITE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${PURPLE}"
    echo "================================================================================"
    echo "                       LetsGoal Installation Script"
    echo "                    Goal Tracking & Productivity Application"
    echo "================================================================================"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${CYAN}▶ $1${NC}"
    echo "----------------------------------------"
}

confirm() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    
    if [[ "$default" == "y" ]]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi
    
    read -p "$prompt" response
    response=${response:-$default}
    
    [[ "$response" =~ ^[Yy]$ ]]
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_ubuntu() {
    if ! command -v apt-get &> /dev/null; then
        log_error "This script is designed for Ubuntu/Debian systems"
        exit 1
    fi
}

#==============================================================================
# System Preparation Functions
#==============================================================================

update_system() {
    print_section "Updating System Packages"
    log_info "Updating package lists..."
    apt-get update -y
    
    log_info "Installing essential packages..."
    apt-get install -y \
        curl \
        wget \
        git \
        ufw \
        nginx \
        certbot \
        python3-certbot-nginx \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        jq \
        sqlite3
    
    log_success "System packages updated successfully"
}

install_docker() {
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        log_info "Docker and Docker Compose already installed"
        return 0
    fi
    
    print_section "Installing Docker and Docker Compose"
    
    # Add Docker's official GPG key
    log_info "Adding Docker GPG key..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    log_info "Adding Docker repository..."
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    log_info "Installing Docker..."
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Install Docker Compose (standalone)
    log_info "Installing Docker Compose..."
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r .tag_name)
    curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    # Add current user to docker group if not root
    if [[ -n "${SUDO_USER:-}" ]]; then
        usermod -aG docker "$SUDO_USER"
        log_info "Added $SUDO_USER to docker group. Please log out and back in for changes to take effect."
    fi
    
    log_success "Docker and Docker Compose installed successfully"
}

setup_directories() {
    print_section "Setting Up Directories"
    
    log_info "Creating installation directories..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Set proper permissions
    chown -R root:root "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
    
    log_success "Directories created successfully"
}

#==============================================================================
# Configuration Functions
#==============================================================================

get_deployment_configuration() {
    print_section "Deployment Configuration"
    
    echo -e "${WHITE}Choose deployment type:${NC}"
    echo "1) Local Network (LAN access only)"
    echo "2) Web Domain (Internet access with domain name)"
    echo ""
    
    while true; do
        read -p "Enter your choice (1-2): " choice
        case $choice in
            1)
                DEPLOYMENT_TYPE="local"
                get_local_network_config
                break
                ;;
            2)
                DEPLOYMENT_TYPE="domain"
                get_domain_config
                break
                ;;
            *)
                log_error "Invalid choice. Please enter 1 or 2."
                ;;
        esac
    done
}

get_local_network_config() {
    echo -e "\n${WHITE}Local Network Configuration${NC}"
    
    # Auto-detect local IP
    LOCAL_IP=$(ip route get 1.1.1.1 | awk '{print $7; exit}')
    
    echo "Detected local IP: $LOCAL_IP"
    if confirm "Use detected IP address ($LOCAL_IP)?" "y"; then
        DOMAIN_OR_IP="$LOCAL_IP"
    else
        while true; do
            read -p "Enter your server's local IP address: " custom_ip
            if [[ "$custom_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
                DOMAIN_OR_IP="$custom_ip"
                break
            else
                log_error "Invalid IP address format. Please try again."
            fi
        done
    fi
    
    USE_SSL="n"
    log_info "Local network deployment will use HTTP (SSL not available for IP addresses)"
}

get_domain_config() {
    echo -e "\n${WHITE}Web Domain Configuration${NC}"
    
    while true; do
        read -p "Enter your domain name (e.g., letsgoal.yourdomain.com): " domain
        if [[ "$domain" =~ ^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$ ]]; then
            DOMAIN_OR_IP="$domain"
            break
        else
            log_error "Invalid domain format. Please enter a valid domain name."
        fi
    done
    
    if confirm "Enable SSL with Let's Encrypt certificate?" "y"; then
        USE_SSL="y"
        echo -e "${YELLOW}Note: Make sure your domain points to this server before continuing!${NC}"
        if ! confirm "Is your domain already pointing to this server?" "n"; then
            log_warning "Please configure your DNS first and run this script again"
            exit 1
        fi
    else
        USE_SSL="n"
    fi
}

get_installation_mode() {
    print_section "Installation Mode"
    
    echo -e "${WHITE}Choose installation mode:${NC}"
    echo "1) Clean Install (Fresh installation)"
    echo "2) Update (Update existing installation)"
    echo "3) Uninstall (Remove LetsGoal completely)"
    echo ""
    
    while true; do
        read -p "Enter your choice (1-3): " choice
        case $choice in
            1)
                INSTALL_MODE="clean"
                break
                ;;
            2)
                INSTALL_MODE="update"
                break
                ;;
            3)
                INSTALL_MODE="uninstall"
                uninstall_letsgoal
                exit 0
                ;;
            *)
                log_error "Invalid choice. Please enter 1-3."
                ;;
        esac
    done
}

#==============================================================================
# Backup and Database Functions
#==============================================================================

backup_database() {
    local backup_file="$BACKUP_DIR/letsgoal_backup_$(date +%Y%m%d_%H%M%S).db"
    local db_path="$INSTALL_DIR/database/letsgoal.db"
    
    if [[ -f "$db_path" ]]; then
        print_section "Creating Database Backup"
        log_info "Backing up database to: $backup_file"
        
        # Create backup directory if it doesn't exist
        mkdir -p "$BACKUP_DIR"
        
        # Copy database file
        cp "$db_path" "$backup_file"
        
        # Verify backup
        if sqlite3 "$backup_file" "SELECT COUNT(*) FROM sqlite_master;" &> /dev/null; then
            log_success "Database backup created successfully"
            EXISTING_DB_BACKUP="$backup_file"
        else
            log_error "Database backup verification failed"
            return 1
        fi
    else
        log_info "No existing database found to backup"
    fi
}

restore_database() {
    if [[ -n "$EXISTING_DB_BACKUP" && -f "$EXISTING_DB_BACKUP" ]]; then
        print_section "Restoring Database"
        log_info "Restoring database from: $EXISTING_DB_BACKUP"
        
        local db_path="$INSTALL_DIR/database/letsgoal.db"
        mkdir -p "$(dirname "$db_path")"
        
        cp "$EXISTING_DB_BACKUP" "$db_path"
        chown root:root "$db_path"
        chmod 644 "$db_path"
        
        log_success "Database restored successfully"
    fi
}

cleanup_old_backups() {
    print_section "Cleaning Up Old Backups"
    log_info "Removing backups older than 30 days..."
    
    find "$BACKUP_DIR" -name "letsgoal_backup_*.db" -mtime +30 -delete 2>/dev/null || true
    
    log_success "Old backups cleaned up"
}

#==============================================================================
# Docker Management Functions
#==============================================================================

cleanup_existing_installation() {
    print_section "Cleaning Up Existing Installation"
    
    # Stop and remove containers
    log_info "Stopping existing containers..."
    docker-compose -f "$INSTALL_DIR/docker-compose.yml" down 2>/dev/null || true
    docker-compose -f "$INSTALL_DIR/docker-compose.prod.yml" down 2>/dev/null || true
    
    # Remove containers by name
    for container in "$CONTAINER_NAME" "$NGINX_CONTAINER_NAME"; do
        if docker ps -a --format "table {{.Names}}" | grep -q "^$container$"; then
            log_info "Removing container: $container"
            docker rm -f "$container" 2>/dev/null || true
        fi
    done
    
    # Remove images
    if docker images --format "table {{.Repository}}" | grep -q "letsgoal"; then
        log_info "Removing LetsGoal Docker images..."
        docker images --format "table {{.Repository}}:{{.Tag}}" | grep "letsgoal" | xargs -r docker rmi -f 2>/dev/null || true
    fi
    
    # Clean up Docker system
    log_info "Cleaning up Docker system..."
    docker system prune -f 2>/dev/null || true
    
    log_success "Existing installation cleaned up"
}

copy_application_files() {
    print_section "Copying Application Files"
    
    log_info "Copying application files to $INSTALL_DIR..."
    
    # Copy all application files except hidden and backup files
    rsync -av --exclude='.*' --exclude='backups/' --exclude='install-letsgoal.sh' \
        "$SCRIPT_DIR/" "$INSTALL_DIR/"
    
    # Set proper permissions
    chown -R root:root "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
    
    log_success "Application files copied successfully"
}

create_production_configs() {
    print_section "Creating Production Configuration"
    
    # Create production docker-compose file
    create_docker_compose_prod
    
    # Create environment file
    create_env_file
    
    # Create nginx configuration for all deployment types
    create_nginx_config
    
    log_success "Production configuration created"
}

run_database_migrations() {
    print_section "Running Database Migrations"
    
    log_info "Starting container for migrations..."
    cd "$INSTALL_DIR"
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for container to be ready
    sleep 10
    
    # Run migrations
    log_info "Running database migrations..."
    for migration in backend/migrations/*.py; do
        if [[ -f "$migration" ]]; then
            log_info "Running migration: $(basename "$migration")"
            docker exec "$CONTAINER_NAME" python "$migration" || log_warning "Migration failed: $migration"
        fi
    done
    
    log_success "Database migrations completed"
}

#==============================================================================
# SSL and Security Functions
#==============================================================================

setup_firewall() {
    print_section "Configuring Firewall"
    
    log_info "Configuring UFW firewall..."
    
    # Enable UFW
    ufw --force enable
    
    # Allow SSH
    ufw allow OpenSSH
    
    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow application port for local access
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        ufw allow 5001/tcp
    fi
    
    log_success "Firewall configured successfully"
}

setup_ssl() {
    if [[ "$USE_SSL" == "y" && "$DEPLOYMENT_TYPE" == "domain" ]]; then
        print_section "Setting Up SSL Certificate"
        
        log_info "Obtaining SSL certificate for $DOMAIN_OR_IP..."
        
        # Stop nginx temporarily
        systemctl stop nginx 2>/dev/null || true
        
        # Obtain certificate
        certbot certonly --standalone \
            --non-interactive \
            --agree-tos \
            --email "admin@$DOMAIN_OR_IP" \
            -d "$DOMAIN_OR_IP"
        
        # Start nginx
        systemctl start nginx
        systemctl enable nginx
        
        # Setup auto-renewal
        (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
        
        log_success "SSL certificate setup completed"
    fi
}

configure_nginx() {
    print_section "Configuring Nginx Reverse Proxy"
    
    # Ensure nginx is started and enabled
    log_info "Starting and enabling nginx service..."
    systemctl start nginx || true
    systemctl enable nginx || true
    
    # Disable default nginx site to avoid conflicts
    log_info "Disabling default nginx site..."
    rm -f /etc/nginx/sites-enabled/default
    
    # Enable nginx site
    if [[ -f "$NGINX_CONF" ]]; then
        ln -sf "$NGINX_CONF" "$NGINX_ENABLED"
        
        # Test nginx configuration
        if nginx -t; then
            systemctl reload nginx
            log_success "Nginx configuration updated"
        else
            log_error "Nginx configuration test failed"
            return 1
        fi
    else
        log_error "Nginx configuration file not found: $NGINX_CONF"
        return 1
    fi
}

#==============================================================================
# Service Management Functions
#==============================================================================

start_application() {
    print_section "Starting LetsGoal Application"
    
    cd "$INSTALL_DIR"
    
    # Start the application
    log_info "Starting Docker containers..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for application to start
    log_info "Waiting for application to start..."
    sleep 15
    
    # Health check
    local health_url
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        health_url="http://$DOMAIN_OR_IP:5001/health"
    elif [[ "$USE_SSL" == "y" ]]; then
        health_url="https://$DOMAIN_OR_IP/health"
    else
        health_url="http://$DOMAIN_OR_IP/health"
    fi
    
    log_info "Performing health check..."
    for i in {1..30}; do
        if curl -s "$health_url" | grep -q "healthy" 2>/dev/null; then
            log_success "Application is running and healthy!"
            break
        fi
        sleep 2
        if [[ $i -eq 30 ]]; then
            log_warning "Health check timeout - application may still be starting"
        fi
    done
    
    log_success "LetsGoal application started successfully"
    
    # Additional verification for web access
    log_info "Verifying web access..."
    local web_url
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        web_url="http://$DOMAIN_OR_IP"
    elif [[ "$USE_SSL" == "y" ]]; then
        web_url="https://$DOMAIN_OR_IP"
    else
        web_url="http://$DOMAIN_OR_IP"
    fi
    
    sleep 3
    if curl -s -I "$web_url" | grep -q "200 OK\|302 Found"; then
        log_success "Web interface is accessible at $web_url"
    else
        log_warning "Web interface may not be accessible yet. If you see nginx welcome page:"
        log_warning "1. Clear browser cache (Ctrl+F5)"
        log_warning "2. Try incognito/private mode"
        log_warning "3. Wait a minute for services to fully start"
        log_warning "4. Run: sudo ./troubleshoot-nginx.sh"
    fi
}

#==============================================================================
# Uninstall Function
#==============================================================================

uninstall_letsgoal() {
    print_section "Uninstalling LetsGoal"
    
    if confirm "Are you sure you want to completely remove LetsGoal?" "n"; then
        
        # Backup database before removal
        if confirm "Create final database backup before removal?" "y"; then
            backup_database
        fi
        
        # Stop and remove containers
        cleanup_existing_installation
        
        # Remove nginx configuration
        if [[ -f "$NGINX_ENABLED" ]]; then
            rm -f "$NGINX_ENABLED"
            
            # Re-enable default site if no other sites exist
            if [[ -z "$(ls -A /etc/nginx/sites-enabled/)" ]]; then
                if [[ -f "/etc/nginx/sites-available/default" ]]; then
                    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
                fi
            fi
            
            systemctl reload nginx || true
        fi
        if [[ -f "$NGINX_CONF" ]]; then
            rm -f "$NGINX_CONF"
        fi
        
        # Remove SSL certificates
        if [[ -d "/etc/letsencrypt/live/$DOMAIN_OR_IP" ]]; then
            if confirm "Remove SSL certificates?" "n"; then
                certbot delete --cert-name "$DOMAIN_OR_IP" --non-interactive || true
            fi
        fi
        
        # Remove application files
        if [[ -d "$INSTALL_DIR" ]]; then
            if confirm "Remove application files (keeping backups)?" "y"; then
                # Keep backups but remove everything else
                mv "$BACKUP_DIR" /tmp/letsgoal_backups_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
                rm -rf "$INSTALL_DIR"
                if [[ -d "/tmp/letsgoal_backups_"* ]]; then
                    log_info "Database backups moved to /tmp/"
                fi
            fi
        fi
        
        log_success "LetsGoal uninstalled successfully"
    else
        log_info "Uninstallation cancelled"
    fi
}

#==============================================================================
# Configuration File Creation Functions
#==============================================================================

create_docker_compose_prod() {
    cat > "$INSTALL_DIR/docker-compose.prod.yml" << 'EOF'
version: '3.8'

services:
  backend:
    build: .
    container_name: letsgoal-backend
    restart: unless-stopped
    ports:
      - "127.0.0.1:5001:5000"
    volumes:
      - ./database:/app/database
      - ./logs:/app/logs
    environment:
      - FLASK_ENV=production
      - FLASK_APP=backend/app.py
      - DATABASE_URL=sqlite:////app/database/letsgoal.db
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  default:
    name: letsgoal-network
EOF

    DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
}

create_env_file() {
    local secret_key
    secret_key=$(openssl rand -hex 32)
    
    local cors_origins
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        cors_origins="http://$DOMAIN_OR_IP:5001,http://localhost:5001,http://127.0.0.1:5001"
    elif [[ "$USE_SSL" == "y" ]]; then
        cors_origins="https://$DOMAIN_OR_IP"
    else
        cors_origins="http://$DOMAIN_OR_IP"
    fi
    
    cat > "$CONFIG_FILE" << EOF
# LetsGoal Production Configuration
SECRET_KEY=$secret_key
CORS_ORIGINS=$cors_origins
FLASK_ENV=production
DATABASE_URL=sqlite:////app/database/letsgoal.db

# Deployment Configuration
DEPLOYMENT_TYPE=$DEPLOYMENT_TYPE
DOMAIN_OR_IP=$DOMAIN_OR_IP
USE_SSL=$USE_SSL

# Installation Information
INSTALL_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
INSTALL_VERSION=1.0.0
EOF
}

create_nginx_config() {
    log_info "Creating nginx configuration for $DEPLOYMENT_TYPE deployment..."
    
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        # Simple proxy configuration for local network
        cat > "$NGINX_CONF" << 'EOF'
server {
    listen 80 default_server;
    server_name _;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
    elif [[ "$DEPLOYMENT_TYPE" == "domain" ]]; then
        # Domain-based configuration
        if [[ "$USE_SSL" == "y" ]]; then
            # HTTPS configuration
            cat > "$NGINX_CONF" << EOF
server {
    listen 80;
    server_name $DOMAIN_OR_IP;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN_OR_IP;
    
    ssl_certificate /etc/letsencrypt/live/$DOMAIN_OR_IP/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_OR_IP/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
        else
            # HTTP only configuration
            cat > "$NGINX_CONF" << EOF
server {
    listen 80;
    server_name $DOMAIN_OR_IP;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
        fi
    fi
    
    log_success "Nginx configuration created"
}

#==============================================================================
# Status and Information Functions
#==============================================================================

show_installation_summary() {
    print_section "Installation Summary"
    
    echo -e "${GREEN}LetsGoal has been successfully installed!${NC}\n"
    
    echo -e "${WHITE}Installation Details:${NC}"
    echo "• Installation Directory: $INSTALL_DIR"
    echo "• Deployment Type: $DEPLOYMENT_TYPE"
    echo "• Domain/IP: $DOMAIN_OR_IP"
    echo "• SSL Enabled: $USE_SSL"
    echo "• Database Backup: ${EXISTING_DB_BACKUP:-None}"
    
    echo -e "\n${WHITE}Access Information:${NC}"
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        echo "• Web Interface: http://$DOMAIN_OR_IP (via nginx)"
        echo "• Direct Access: http://$DOMAIN_OR_IP:5001"
        echo "• Network Access: Local network only"
    elif [[ "$USE_SSL" == "y" ]]; then
        echo "• Application URL: https://$DOMAIN_OR_IP"
        echo "• Network Access: Internet (with SSL)"
    else
        echo "• Application URL: http://$DOMAIN_OR_IP"
        echo "• Network Access: Internet (no SSL)"
    fi
    
    echo -e "\n${WHITE}Management Commands:${NC}"
    echo "• View logs: docker logs $CONTAINER_NAME"
    echo "• Restart: cd $INSTALL_DIR && docker-compose -f $DOCKER_COMPOSE_FILE restart"
    echo "• Stop: cd $INSTALL_DIR && docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "• Update: sudo $0 (choose update mode)"
    
    echo -e "\n${WHITE}File Locations:${NC}"
    echo "• Configuration: $CONFIG_FILE"
    echo "• Database: $INSTALL_DIR/database/letsgoal.db"
    echo "• Backups: $BACKUP_DIR"
    echo "• Logs: $LOG_FILE"
    
    if [[ "$DEPLOYMENT_TYPE" == "domain" ]]; then
        echo "• Nginx Config: $NGINX_CONF"
        if [[ "$USE_SSL" == "y" ]]; then
            echo "• SSL Certificates: /etc/letsencrypt/live/$DOMAIN_OR_IP/"
        fi
    fi
    
    echo -e "\n${YELLOW}Important Notes:${NC}"
    echo "• Default login credentials will be created on first access"
    echo "• Database backups are automatically created during updates"
    echo "• SSL certificates (if enabled) will auto-renew via cron"
    echo "• Firewall has been configured to allow necessary ports"
    
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        echo "• For local network access, ensure other devices can reach $DOMAIN_OR_IP:5001"
    fi
    
    echo -e "\n${CYAN}Troubleshooting:${NC}"
    echo "• If you see nginx welcome page: Clear browser cache (Ctrl+F5)"
    echo "• Check status: sudo ./troubleshoot-nginx.sh"
    echo "• Quick fix: sudo ./fix-nginx.sh"
    echo "• View nginx error logs: sudo tail -f /var/log/nginx/error.log"
    
    echo -e "\n${GREEN}Installation completed successfully!${NC}"
}

#==============================================================================
# Main Installation Flow
#==============================================================================

main() {
    print_header
    
    # Check prerequisites
    check_root
    check_ubuntu
    
    # Get configuration from user
    get_deployment_configuration
    get_installation_mode
    
    # Start installation log
    log "Starting LetsGoal installation..."
    log "Configuration: $DEPLOYMENT_TYPE deployment for $DOMAIN_OR_IP (SSL: $USE_SSL)"
    
    # System preparation
    update_system
    install_docker
    setup_directories
    setup_firewall
    
    # Handle different installation modes
    case "$INSTALL_MODE" in
        "update")
            backup_database
            cleanup_existing_installation
            copy_application_files
            create_production_configs
            restore_database
            ;;
        "clean")
            cleanup_existing_installation
            copy_application_files
            create_production_configs
            ;;
    esac
    
    # SSL and security setup
    setup_ssl
    configure_nginx
    
    # Database and application startup
    run_database_migrations
    start_application
    
    # Cleanup and final steps
    cleanup_old_backups
    
    # Show results
    show_installation_summary
    
    log_success "LetsGoal installation completed successfully!"
}

#==============================================================================
# Script Entry Point
#==============================================================================

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "LetsGoal Installation Script"
        echo "Usage: $0 [--help]"
        echo ""
        echo "This script provides interactive installation of LetsGoal"
        echo "application with support for local and web deployment."
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac