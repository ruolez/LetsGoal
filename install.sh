#!/bin/bash

#==============================================================================
#                    LetsGoal Installation Manager v2.0.0
#                 Goal Tracking & Productivity Application
#
# One-line installation:
#   curl -fsSL https://raw.githubusercontent.com/ruolez/letsgoal/main/install.sh | sudo bash
#
# Features:
#   - Interactive menu-based installation
#   - Fresh install, update, and uninstall support
#   - SSL certificate management with Let's Encrypt
#   - Database backup and restore
#   - System status and logs viewing
#   - Docker cleanup and optimization
#==============================================================================

set -uo pipefail

#==============================================================================
# CONSTANTS
#==============================================================================
readonly VERSION="2.0.0"
readonly INSTALL_DIR="/opt/letsgoal"
readonly BACKUP_DIR="/opt/letsgoal/backups"
readonly LOG_FILE="/var/log/letsgoal-install.log"
readonly CONFIG_FILE="/opt/letsgoal/.env"
readonly GITHUB_REPO="https://github.com/ruolez/letsgoal.git"
readonly NGINX_CONF="/etc/nginx/sites-available/letsgoal"
readonly NGINX_ENABLED="/etc/nginx/sites-enabled/letsgoal"

# Container names
readonly CONTAINER_BACKEND="letsgoal-backend"
readonly CONTAINER_ADMIN="letsgoal-admin"
readonly CONTAINER_REDIS="letsgoal-redis"
readonly CONTAINER_NGINX="letsgoal-nginx"

#==============================================================================
# COLORS
#==============================================================================
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly GRAY='\033[0;90m'
readonly NC='\033[0m'
readonly BOLD='\033[1m'

#==============================================================================
# GLOBAL STATE
#==============================================================================
DEPLOYMENT_TYPE=""
DOMAIN_OR_IP=""
USE_SSL=""
INSTALL_STATUS="Not installed"
CURRENT_DOMAIN=""
SSL_STATUS="None"
CONTAINERS_RUNNING=0
CONTAINERS_TOTAL=4

#==============================================================================
# UTILITY FUNCTIONS
#==============================================================================

log() {
    local msg="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $msg" >> "$LOG_FILE" 2>/dev/null || true
}

print_colored() {
    echo -e "$1$2${NC}"
}

print_header() {
    clear
    echo -e "${PURPLE}"
    echo "================================================================================"
    echo "                    LetsGoal Installation Manager v${VERSION}"
    echo "                 Goal Tracking & Productivity Application"
    echo "================================================================================"
    echo -e "${NC}"
}

print_divider() {
    echo -e "${GRAY}--------------------------------------------------------------------------------${NC}"
}

print_step() {
    local step="$1"
    local total="$2"
    local msg="$3"
    echo -e "${CYAN}[$step/$total]${NC} $msg"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

print_info() {
    echo -e "${BLUE}→${NC} $1"
}

wait_for_key() {
    echo ""
    read -p "Press Enter to continue..."
}

confirm() {
    local prompt="$1"
    local default="${2:-n}"
    local response

    if [[ "$default" == "y" || "$default" == "Y" ]]; then
        read -p "$prompt [Y/n]: " response
        response=${response:-Y}
    else
        read -p "$prompt [y/N]: " response
        response=${response:-N}
    fi

    [[ "$response" =~ ^[Yy]$ ]]
}

#==============================================================================
# DETECTION FUNCTIONS
#==============================================================================

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_ubuntu() {
    if [[ ! -f /etc/os-release ]]; then
        print_warning "Could not detect OS version"
        return
    fi

    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        print_warning "This script is optimized for Ubuntu. Current OS: $ID"
    fi
}

get_ubuntu_version() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        echo "$PRETTY_NAME"
    else
        echo "Unknown"
    fi
}

detect_local_ip() {
    ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}' || hostname -I | awk '{print $1}'
}

detect_public_ip() {
    curl -s --connect-timeout 5 ifconfig.me 2>/dev/null || \
    curl -s --connect-timeout 5 icanhazip.com 2>/dev/null || \
    curl -s --connect-timeout 5 api.ipify.org 2>/dev/null || \
    echo "Unknown"
}

check_installation_status() {
    INSTALL_STATUS="Not installed"
    CURRENT_DOMAIN=""
    SSL_STATUS="None"
    CONTAINERS_RUNNING=0

    # Check if install directory exists
    if [[ -d "$INSTALL_DIR" ]]; then
        INSTALL_STATUS="INSTALLED at $INSTALL_DIR"

        # Check for domain/IP configuration
        if [[ -f "$CONFIG_FILE" ]]; then
            CURRENT_DOMAIN=$(grep "^DOMAIN_OR_IP=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
            USE_SSL=$(grep "^USE_SSL=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
        fi

        # Check SSL status
        if [[ -n "$CURRENT_DOMAIN" && -d "/etc/letsencrypt/live/$CURRENT_DOMAIN" ]]; then
            local expiry
            expiry=$(openssl x509 -enddate -noout -in "/etc/letsencrypt/live/$CURRENT_DOMAIN/fullchain.pem" 2>/dev/null | cut -d'=' -f2)
            if [[ -n "$expiry" ]]; then
                SSL_STATUS="Active (expires: $expiry)"
            else
                SSL_STATUS="Active"
            fi
        elif [[ "$USE_SSL" == "y" ]]; then
            SSL_STATUS="Configured but certificate missing"
        fi

        # Count running containers
        if command -v docker &>/dev/null; then
            for container in "$CONTAINER_BACKEND" "$CONTAINER_ADMIN" "$CONTAINER_REDIS" "$CONTAINER_NGINX"; do
                if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^${container}$"; then
                    ((CONTAINERS_RUNNING++))
                fi
            done
        fi
    fi
}

print_status_line() {
    local ubuntu_version
    ubuntu_version=$(get_ubuntu_version)

    echo -e "${WHITE}System:${NC} $ubuntu_version"

    if [[ "$INSTALL_STATUS" == "Not installed" ]]; then
        echo -e "${WHITE}Status:${NC} ${YELLOW}Not installed${NC}"
    else
        echo -e "${WHITE}Status:${NC} ${GREEN}$INSTALL_STATUS${NC}"

        if [[ -n "$CURRENT_DOMAIN" ]]; then
            echo -e "${WHITE}Domain:${NC} $CURRENT_DOMAIN (SSL: $SSL_STATUS)"
        fi

        if [[ $CONTAINERS_RUNNING -gt 0 ]]; then
            if [[ $CONTAINERS_RUNNING -eq $CONTAINERS_TOTAL ]]; then
                echo -e "${WHITE}Containers:${NC} ${GREEN}$CONTAINERS_RUNNING/$CONTAINERS_TOTAL running${NC}"
            else
                echo -e "${WHITE}Containers:${NC} ${YELLOW}$CONTAINERS_RUNNING/$CONTAINERS_TOTAL running${NC}"
            fi
        fi
    fi
    echo ""
}

#==============================================================================
# INSTALLATION FUNCTIONS
#==============================================================================

install_system_packages() {
    print_step "$1" "$2" "Updating system packages..."
    log "Installing system packages"

    apt-get update -y >> "$LOG_FILE" 2>&1

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
        sqlite3 >> "$LOG_FILE" 2>&1

    print_success "System packages updated"
}

install_docker() {
    print_step "$1" "$2" "Installing Docker..."
    log "Installing Docker"

    if command -v docker &>/dev/null && command -v docker-compose &>/dev/null; then
        print_success "Docker already installed"
        return 0
    fi

    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg 2>/dev/null || true

    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    apt-get update -y >> "$LOG_FILE" 2>&1
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin >> "$LOG_FILE" 2>&1

    # Install Docker Compose (standalone)
    if ! command -v docker-compose &>/dev/null; then
        local compose_version
        compose_version=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r .tag_name 2>/dev/null || echo "v2.24.0")
        curl -L "https://github.com/docker/compose/releases/download/${compose_version}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose 2>/dev/null
        chmod +x /usr/local/bin/docker-compose
    fi

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    print_success "Docker installed"
}

clone_repository() {
    print_step "$1" "$2" "Cloning repository from GitHub..."
    log "Cloning repository"

    mkdir -p "$INSTALL_DIR"

    if [[ -d "$INSTALL_DIR/.git" ]]; then
        # Already a git repo, pull latest
        cd "$INSTALL_DIR"
        git fetch origin >> "$LOG_FILE" 2>&1
        git reset --hard origin/main >> "$LOG_FILE" 2>&1
    else
        # Fresh clone
        rm -rf "${INSTALL_DIR:?}/*"
        git clone "$GITHUB_REPO" "$INSTALL_DIR" >> "$LOG_FILE" 2>&1
    fi

    # Set permissions
    chown -R root:root "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"

    print_success "Repository cloned"
}

generate_configuration() {
    print_step "$1" "$2" "Generating secure configuration..."
    log "Generating configuration"

    local secret_key
    secret_key=$(openssl rand -hex 32)

    local cors_origins
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        cors_origins="http://$DOMAIN_OR_IP"
    elif [[ "$USE_SSL" == "y" ]]; then
        cors_origins="https://$DOMAIN_OR_IP"
    else
        cors_origins="http://$DOMAIN_OR_IP"
    fi

    # Create .env file
    cat > "$CONFIG_FILE" << EOF
# LetsGoal Production Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

SECRET_KEY=$secret_key
CORS_ORIGINS=$cors_origins
FLASK_ENV=production
DATABASE_URL=sqlite:////app/database/letsgoal.db

# Deployment Configuration
DEPLOYMENT_TYPE=$DEPLOYMENT_TYPE
DOMAIN_OR_IP=$DOMAIN_OR_IP
USE_SSL=$USE_SSL

# Version
VERSION=$VERSION
EOF

    chmod 600 "$CONFIG_FILE"
    print_success "Configuration generated"
}

configure_cors() {
    print_step "$1" "$2" "Configuring CORS origins..."
    log "Configuring CORS"

    # Update CORS in .env
    local cors_origins
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        cors_origins="http://$DOMAIN_OR_IP"
    elif [[ "$USE_SSL" == "y" ]]; then
        cors_origins="https://$DOMAIN_OR_IP"
    else
        cors_origins="http://$DOMAIN_OR_IP"
    fi

    if [[ -f "$CONFIG_FILE" ]]; then
        sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$cors_origins|" "$CONFIG_FILE"
    fi

    print_success "CORS configured"
}

setup_ssl() {
    print_step "$1" "$2" "Setting up SSL certificate..."
    log "Setting up SSL"

    if [[ "$USE_SSL" != "y" ]]; then
        print_info "SSL not requested, skipping"
        return 0
    fi

    # Check if certificate already exists
    if [[ -d "/etc/letsencrypt/live/$DOMAIN_OR_IP" ]]; then
        print_success "SSL certificate already exists"
        return 0
    fi

    # Stop nginx temporarily for standalone certificate
    systemctl stop nginx 2>/dev/null || true

    # Obtain certificate
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email "admin@$DOMAIN_OR_IP" \
        -d "$DOMAIN_OR_IP" >> "$LOG_FILE" 2>&1

    if [[ $? -eq 0 ]]; then
        # Setup auto-renewal cron job
        if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
            (crontab -l 2>/dev/null; echo "0 3 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -
        fi
        print_success "SSL certificate obtained"
    else
        print_error "Failed to obtain SSL certificate"
        print_warning "You can try again later via menu option 4"
    fi
}

setup_firewall() {
    print_step "$1" "$2" "Configuring firewall..."
    log "Configuring firewall"

    # Enable UFW
    ufw --force enable >> "$LOG_FILE" 2>&1

    # Allow essential ports
    ufw allow OpenSSH >> "$LOG_FILE" 2>&1
    ufw allow 80/tcp >> "$LOG_FILE" 2>&1
    ufw allow 443/tcp >> "$LOG_FILE" 2>&1

    print_success "Firewall configured"
}

create_nginx_config() {
    log "Creating nginx configuration"

    # Create sites-available directory if it doesn't exist
    mkdir -p /etc/nginx/sites-available
    mkdir -p /etc/nginx/sites-enabled

    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        # Local network HTTP only
        cat > "$NGINX_CONF" << 'NGINX_LOCAL'
server {
    listen 80 default_server;
    server_name _;

    client_max_body_size 50M;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Admin dashboard routes
    location /admin {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /api/admin {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /auth {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Main application
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
NGINX_LOCAL

    elif [[ "$USE_SSL" == "y" ]]; then
        # Production with SSL
        cat > "$NGINX_CONF" << NGINX_SSL
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

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 50M;

    # Admin dashboard routes
    location /admin {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /api/admin {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /auth {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Main application
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
NGINX_SSL

    else
        # Production HTTP only
        cat > "$NGINX_CONF" << NGINX_HTTP
server {
    listen 80;
    server_name $DOMAIN_OR_IP;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    client_max_body_size 50M;

    # Admin dashboard routes
    location /admin {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /api/admin {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /auth {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Main application
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
NGINX_HTTP
    fi
}

configure_nginx() {
    log "Configuring nginx"

    # Create nginx configuration
    create_nginx_config

    # Disable default site
    rm -f /etc/nginx/sites-enabled/default

    # Enable LetsGoal site
    ln -sf "$NGINX_CONF" "$NGINX_ENABLED"

    # Test and reload nginx
    if nginx -t >> "$LOG_FILE" 2>&1; then
        systemctl start nginx 2>/dev/null || true
        systemctl enable nginx 2>/dev/null || true
        systemctl reload nginx
        return 0
    else
        print_error "Nginx configuration test failed"
        return 1
    fi
}

start_docker_containers() {
    print_step "$1" "$2" "Starting Docker containers..."
    log "Starting containers"

    cd "$INSTALL_DIR"

    # Use production compose file
    docker-compose -f docker-compose.prod.yml up -d --build >> "$LOG_FILE" 2>&1

    print_success "Containers started"
}

run_migrations() {
    print_step "$1" "$2" "Running database migrations..."
    log "Running migrations"

    cd "$INSTALL_DIR"

    # Wait for containers to be ready
    sleep 10

    # Run migrations
    for migration in backend/migrations/*.py; do
        if [[ -f "$migration" ]]; then
            docker exec "$CONTAINER_BACKEND" python "$migration" >> "$LOG_FILE" 2>&1 || true
        fi
    done

    # Setup default admin user
    docker exec "$CONTAINER_ADMIN" python -c "
import sys
sys.path.append('/app/backend')
try:
    from admin_app import app
    from models import db, User
    from werkzeug.security import generate_password_hash

    with app.app_context():
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@letsgoal.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True,
                is_active=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print('Default admin user created')
except Exception as e:
    print(f'Admin setup: {e}')
" >> "$LOG_FILE" 2>&1 || true

    print_success "Migrations completed"
}

verify_installation() {
    print_step "$1" "$2" "Verifying installation..."
    log "Verifying installation"

    local success=true
    local url_prefix="http"

    if [[ "$USE_SSL" == "y" ]]; then
        url_prefix="https"
    fi

    # Wait for services
    sleep 5

    # Check containers
    for container in "$CONTAINER_BACKEND" "$CONTAINER_ADMIN" "$CONTAINER_REDIS"; do
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            print_success "Container $container is running"
        else
            print_error "Container $container is not running"
            success=false
        fi
    done

    # Check health endpoints
    if curl -s "http://127.0.0.1:5001/health" 2>/dev/null | grep -q "healthy"; then
        print_success "Backend health check passed"
    else
        print_warning "Backend health check pending"
    fi

    if curl -s "http://127.0.0.1:5002/health" 2>/dev/null | grep -q "healthy"; then
        print_success "Admin health check passed"
    else
        print_warning "Admin health check pending"
    fi

    if [[ "$success" == "true" ]]; then
        print_success "Installation verified"
    fi
}

show_installation_complete() {
    local url_prefix="http"
    if [[ "$USE_SSL" == "y" ]]; then
        url_prefix="https"
    fi

    echo ""
    print_divider
    echo -e "${GREEN}${BOLD}Installation complete!${NC}"
    print_divider
    echo ""
    echo -e "${WHITE}Access your application:${NC}"
    echo -e "  Main App: ${CYAN}${url_prefix}://${DOMAIN_OR_IP}${NC}"
    echo -e "  Admin:    ${CYAN}${url_prefix}://${DOMAIN_OR_IP}/admin${NC}"
    echo ""
    echo -e "${WHITE}Default admin credentials:${NC}"
    echo -e "  Username: ${YELLOW}admin${NC}"
    echo -e "  Password: ${YELLOW}admin123${NC} ${RED}(CHANGE THIS IMMEDIATELY!)${NC}"
    echo ""

    wait_for_key
}

#==============================================================================
# UPDATE FUNCTIONS
#==============================================================================

backup_database() {
    log "Creating database backup"

    mkdir -p "$BACKUP_DIR"

    local db_path="$INSTALL_DIR/database/letsgoal.db"
    local backup_file="$BACKUP_DIR/letsgoal_$(date +%Y%m%d_%H%M%S).db"

    if [[ -f "$db_path" ]]; then
        cp "$db_path" "$backup_file"

        # Verify backup
        if sqlite3 "$backup_file" "SELECT COUNT(*) FROM sqlite_master;" &>/dev/null; then
            echo "$backup_file"
            return 0
        else
            rm -f "$backup_file"
            return 1
        fi
    fi

    return 1
}

pull_from_github() {
    log "Pulling from GitHub"

    cd "$INSTALL_DIR"

    # Stash any local changes
    git stash >> "$LOG_FILE" 2>&1 || true

    # Pull latest
    git fetch origin >> "$LOG_FILE" 2>&1
    git reset --hard origin/main >> "$LOG_FILE" 2>&1

    # Get commit hash
    git rev-parse --short HEAD 2>/dev/null || echo "unknown"
}

cleanup_docker() {
    log "Cleaning up Docker"

    # Remove unused images
    docker image prune -af >> "$LOG_FILE" 2>&1 || true

    # Get freed space
    docker system df 2>/dev/null | grep "Images" | awk '{print $4}' || echo "unknown"
}

perform_update() {
    print_header
    echo -e "${BOLD}Update LetsGoal${NC}"
    print_divider
    echo ""
    echo "This will:"
    echo "  - Backup your database"
    echo "  - Pull latest code from GitHub"
    echo "  - Clean up unused Docker images"
    echo "  - Rebuild containers"
    echo "  - Run new migrations"
    echo "  - SSL certificates will NOT be affected"
    echo ""

    if ! confirm "Proceed with update?" "Y"; then
        return
    fi

    echo ""
    local total_steps=6

    # Step 1: Backup
    print_step 1 $total_steps "Creating database backup..."
    local backup_file
    backup_file=$(backup_database)
    if [[ -n "$backup_file" ]]; then
        print_success "Saved: $backup_file"
    else
        print_warning "No database to backup"
    fi

    # Step 2: Pull from GitHub
    print_step 2 $total_steps "Pulling latest changes from GitHub..."
    local commit
    commit=$(pull_from_github)
    print_success "Updated to commit: $commit"

    # Step 3: Cleanup Docker
    print_step 3 $total_steps "Cleaning up unused Docker images..."
    local freed
    freed=$(cleanup_docker)
    print_success "Freed: $freed"

    # Step 4: Rebuild containers
    print_step 4 $total_steps "Rebuilding containers..."
    cd "$INSTALL_DIR"
    docker-compose -f docker-compose.prod.yml down >> "$LOG_FILE" 2>&1
    docker-compose -f docker-compose.prod.yml up -d --build >> "$LOG_FILE" 2>&1
    print_success "Containers rebuilt"

    # Step 5: Run migrations
    print_step 5 $total_steps "Running database migrations..."
    sleep 10
    for migration in backend/migrations/*.py; do
        if [[ -f "$migration" ]]; then
            docker exec "$CONTAINER_BACKEND" python "$migration" >> "$LOG_FILE" 2>&1 || true
        fi
    done
    print_success "Migrations completed"

    # Step 6: Verify
    print_step 6 $total_steps "Verifying services..."
    check_installation_status
    if [[ $CONTAINERS_RUNNING -eq $CONTAINERS_TOTAL ]]; then
        print_success "All $CONTAINERS_TOTAL containers healthy"
    else
        print_warning "$CONTAINERS_RUNNING/$CONTAINERS_TOTAL containers running"
    fi

    echo ""
    print_divider
    print_success "Update complete!"
    print_divider

    wait_for_key
}

#==============================================================================
# UNINSTALL FUNCTIONS
#==============================================================================

perform_uninstall() {
    print_header
    echo -e "${BOLD}Uninstall LetsGoal${NC}"
    print_divider
    echo ""
    echo -e "${YELLOW}WARNING: This will remove LetsGoal from your system.${NC}"
    echo ""
    echo "What would you like to remove?"
    echo "  1) Full removal (containers, images, app files)"
    echo "  2) Full removal + SSL certificates"
    echo "  3) Cancel"
    echo ""

    read -p "Enter your choice [1-3]: " choice

    case $choice in
        1) do_uninstall false ;;
        2) do_uninstall true ;;
        3) return ;;
        *) print_error "Invalid choice"; return ;;
    esac
}

do_uninstall() {
    local remove_ssl="$1"

    echo ""

    # Offer backup
    if confirm "Create final database backup?" "Y"; then
        local backup_file
        backup_file=$(backup_database)
        if [[ -n "$backup_file" ]]; then
            # Move backup to temp
            local temp_backup="/tmp/letsgoal_backups_$(date +%Y%m%d)"
            mkdir -p "$temp_backup"
            mv "$BACKUP_DIR"/* "$temp_backup/" 2>/dev/null || true
            print_success "Backups moved to: $temp_backup"
        fi
    fi

    echo ""
    print_info "Removing LetsGoal..."

    # Stop containers
    echo "  Stopping containers..."
    cd "$INSTALL_DIR" 2>/dev/null && docker-compose -f docker-compose.prod.yml down -v >> "$LOG_FILE" 2>&1 || true

    # Remove containers by name
    for container in "$CONTAINER_BACKEND" "$CONTAINER_ADMIN" "$CONTAINER_REDIS" "$CONTAINER_NGINX"; do
        docker rm -f "$container" 2>/dev/null || true
    done

    # Remove images
    echo "  Removing Docker images..."
    docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "letsgoal|<none>" | xargs -r docker rmi -f 2>/dev/null || true
    docker system prune -af >> "$LOG_FILE" 2>&1 || true

    # Remove nginx configuration
    echo "  Removing nginx configuration..."
    rm -f "$NGINX_ENABLED" "$NGINX_CONF"

    # Re-enable default site
    if [[ -f "/etc/nginx/sites-available/default" ]]; then
        ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default 2>/dev/null || true
    fi
    systemctl reload nginx 2>/dev/null || true

    # Remove SSL if requested
    if [[ "$remove_ssl" == "true" && -n "$CURRENT_DOMAIN" ]]; then
        echo "  Removing SSL certificates..."
        certbot delete --cert-name "$CURRENT_DOMAIN" --non-interactive >> "$LOG_FILE" 2>&1 || true
    fi

    # Remove application files
    echo "  Removing application files..."
    rm -rf "$INSTALL_DIR"

    echo ""
    print_divider
    print_success "LetsGoal has been uninstalled."
    if [[ -d "/tmp/letsgoal_backups_"* ]]; then
        echo -e "Your backups are saved at: ${CYAN}/tmp/letsgoal_backups_*${NC}"
    fi
    print_divider

    wait_for_key
}

#==============================================================================
# SSL MANAGEMENT FUNCTIONS
#==============================================================================

menu_ssl() {
    while true; do
        print_header
        echo -e "${BOLD}SSL Certificate Management${NC}"
        print_divider
        echo ""

        check_installation_status

        if [[ -n "$CURRENT_DOMAIN" ]]; then
            echo -e "${WHITE}Current Status:${NC} $SSL_STATUS"
            echo -e "${WHITE}Domain:${NC} $CURRENT_DOMAIN"
        else
            echo -e "${YELLOW}No domain configured${NC}"
        fi

        echo ""
        echo "  1) Test certificate renewal (dry run)"
        echo "  2) Force certificate renewal"
        echo "  3) View certificate details"
        echo "  4) Back to main menu"
        echo ""

        read -p "Enter your choice [1-4]: " choice

        case $choice in
            1) ssl_test_renewal ;;
            2) ssl_force_renewal ;;
            3) ssl_view_details ;;
            4) return ;;
            *) print_error "Invalid option" ;;
        esac
    done
}

ssl_test_renewal() {
    echo ""
    print_info "Testing certificate renewal..."
    certbot renew --dry-run 2>&1 | tail -20
    wait_for_key
}

ssl_force_renewal() {
    echo ""
    if confirm "Force renewal of SSL certificate?" "n"; then
        print_info "Forcing certificate renewal..."
        certbot renew --force-renewal
        systemctl reload nginx
        print_success "Certificate renewed"
    fi
    wait_for_key
}

ssl_view_details() {
    echo ""
    if [[ -n "$CURRENT_DOMAIN" && -f "/etc/letsencrypt/live/$CURRENT_DOMAIN/fullchain.pem" ]]; then
        openssl x509 -in "/etc/letsencrypt/live/$CURRENT_DOMAIN/fullchain.pem" -noout -text | head -30
    else
        print_warning "No certificate found"
    fi
    wait_for_key
}

#==============================================================================
# STATUS AND LOGS FUNCTIONS
#==============================================================================

menu_status() {
    print_header
    echo -e "${BOLD}System Status${NC}"
    print_divider
    echo ""

    check_installation_status

    # Container status
    echo -e "${WHITE}Containers:${NC}"
    for container in "$CONTAINER_BACKEND" "$CONTAINER_ADMIN" "$CONTAINER_REDIS" "$CONTAINER_NGINX"; do
        local status health uptime
        if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^${container}$"; then
            status="${GREEN}Running${NC}"
            health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
            uptime=$(docker ps --format "{{.Status}}" --filter "name=$container" 2>/dev/null | head -1)
            echo -e "  $container   ${status}  ($health)   $uptime"
        else
            echo -e "  $container   ${RED}Stopped${NC}"
        fi
    done

    echo ""

    # Database info
    local db_path="$INSTALL_DIR/database/letsgoal.db"
    if [[ -f "$db_path" ]]; then
        local db_size
        db_size=$(du -h "$db_path" 2>/dev/null | cut -f1)
        local user_count goal_count
        user_count=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "?")
        goal_count=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM goals;" 2>/dev/null || echo "?")
        echo -e "${WHITE}Database:${NC} $db_size (users: $user_count, goals: $goal_count)"
    fi

    # SSL status
    echo -e "${WHITE}SSL:${NC} $SSL_STATUS"

    echo ""
    echo -e "${WHITE}Recent Logs (last 20 lines):${NC}"
    print_divider

    docker logs "$CONTAINER_BACKEND" --tail 20 2>/dev/null || echo "No backend logs available"

    wait_for_key
}

#==============================================================================
# BACKUP FUNCTIONS
#==============================================================================

menu_backup() {
    print_header
    echo -e "${BOLD}Database Backup${NC}"
    print_divider
    echo ""

    print_info "Creating backup..."

    local backup_file
    backup_file=$(backup_database)

    if [[ -n "$backup_file" ]]; then
        local size
        size=$(du -h "$backup_file" 2>/dev/null | cut -f1)

        echo ""
        print_success "Backup created successfully!"
        echo ""
        echo -e "  Source:      $INSTALL_DIR/database/letsgoal.db"
        echo -e "  Destination: $backup_file"
        echo -e "  Size:        $size"
        echo ""

        # List existing backups
        echo -e "${WHITE}Existing backups (last 5):${NC}"
        ls -lht "$BACKUP_DIR"/*.db 2>/dev/null | head -5 | while read -r line; do
            echo "  $line"
        done

        # Cleanup old backups
        echo ""
        print_info "Removing backups older than 30 days..."
        find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete 2>/dev/null || true
    else
        print_error "Failed to create backup"
    fi

    wait_for_key
}

#==============================================================================
# INSTALLATION MENU
#==============================================================================

menu_install() {
    print_header
    echo -e "${BOLD}Install LetsGoal${NC}"
    print_divider
    echo ""
    echo "Deployment Type:"
    echo "  1) Local Network (LAN access via IP address)"
    echo "  2) Production Domain (Internet with SSL - Recommended)"
    echo "  3) Back to main menu"
    echo ""

    read -p "Enter your choice [1-3]: " choice

    case $choice in
        1) install_local ;;
        2) install_production ;;
        3) return ;;
        *) print_error "Invalid option" ;;
    esac
}

install_local() {
    DEPLOYMENT_TYPE="local"
    USE_SSL="n"

    echo ""
    local detected_ip
    detected_ip=$(detect_local_ip)

    echo -e "Detected server IP: ${CYAN}$detected_ip${NC}"

    if confirm "Use this IP address?" "Y"; then
        DOMAIN_OR_IP="$detected_ip"
    else
        while true; do
            read -p "Enter your server's IP address: " custom_ip
            if [[ "$custom_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
                DOMAIN_OR_IP="$custom_ip"
                break
            else
                print_error "Invalid IP address format"
            fi
        done
    fi

    run_installation
}

install_production() {
    DEPLOYMENT_TYPE="domain"

    echo ""
    while true; do
        read -p "Enter your domain name (e.g., goals.example.com): " domain
        if [[ "$domain" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$ ]]; then
            DOMAIN_OR_IP="$domain"
            break
        else
            print_error "Invalid domain format"
        fi
    done

    echo ""
    print_info "Verifying DNS configuration..."

    local server_ip domain_ip
    server_ip=$(detect_public_ip)
    domain_ip=$(dig +short "$DOMAIN_OR_IP" 2>/dev/null | head -1)

    echo -e "  Server IP:          ${CYAN}$server_ip${NC}"
    echo -e "  Domain resolves to: ${CYAN}${domain_ip:-Not found}${NC}"

    if [[ "$server_ip" == "$domain_ip" ]]; then
        echo -e "  DNS verification:   ${GREEN}OK${NC}"
    else
        echo -e "  DNS verification:   ${YELLOW}WARNING - IPs don't match${NC}"
        echo ""
        if ! confirm "Continue anyway?" "n"; then
            return
        fi
    fi

    echo ""
    USE_SSL="y"
    print_info "SSL will be automatically configured with Let's Encrypt"

    echo ""
    if confirm "Proceed with installation for: $DOMAIN_OR_IP?" "Y"; then
        run_installation
    fi
}

run_installation() {
    print_header
    echo -e "${BOLD}Installing LetsGoal${NC}"
    print_divider
    echo ""

    local total_steps=10

    install_system_packages 1 $total_steps
    install_docker 2 $total_steps
    clone_repository 3 $total_steps
    generate_configuration 4 $total_steps
    configure_cors 5 $total_steps
    setup_ssl 6 $total_steps

    print_step 7 $total_steps "Configuring nginx..."
    configure_nginx
    print_success "Nginx configured"

    setup_firewall 8 $total_steps
    start_docker_containers 9 $total_steps
    run_migrations 10 $total_steps

    # Final verification
    echo ""
    verify_installation 10 $total_steps

    show_installation_complete
}

#==============================================================================
# MAIN MENU
#==============================================================================

show_main_menu() {
    while true; do
        print_header
        check_installation_status
        print_status_line

        echo "Select an option:"
        echo ""
        echo "  1) Install LetsGoal (Fresh installation)"
        echo "  2) Update LetsGoal (Pull latest from GitHub)"
        echo "  3) Uninstall LetsGoal (Remove completely)"
        echo "  4) Manage SSL Certificate"
        echo "  5) View System Status & Logs"
        echo "  6) Create Database Backup"
        echo "  7) Exit"
        echo ""

        read -p "Enter your choice [1-7]: " choice

        case $choice in
            1) menu_install ;;
            2)
                if [[ "$INSTALL_STATUS" == "Not installed" ]]; then
                    print_error "LetsGoal is not installed. Choose option 1 to install."
                    wait_for_key
                else
                    perform_update
                fi
                ;;
            3)
                if [[ "$INSTALL_STATUS" == "Not installed" ]]; then
                    print_error "LetsGoal is not installed."
                    wait_for_key
                else
                    perform_uninstall
                fi
                ;;
            4) menu_ssl ;;
            5) menu_status ;;
            6)
                if [[ "$INSTALL_STATUS" == "Not installed" ]]; then
                    print_error "LetsGoal is not installed."
                    wait_for_key
                else
                    menu_backup
                fi
                ;;
            7)
                echo ""
                print_info "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option"
                sleep 1
                ;;
        esac
    done
}

#==============================================================================
# MAIN ENTRY POINT
#==============================================================================

main() {
    # Initialize logging
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE" 2>/dev/null || true

    log "LetsGoal Installation Manager v$VERSION started"

    # Check prerequisites
    check_root
    check_ubuntu

    # Show main menu
    show_main_menu
}

# Handle arguments
case "${1:-}" in
    --help|-h)
        echo "LetsGoal Installation Manager v$VERSION"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --version, -v  Show version"
        echo ""
        echo "One-line installation:"
        echo "  curl -fsSL https://raw.githubusercontent.com/ruolez/letsgoal/main/install.sh | sudo bash"
        exit 0
        ;;
    --version|-v)
        echo "LetsGoal Installation Manager v$VERSION"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
