#!/bin/bash

# LetsGoal SSL Setup Script
# Handles Let's Encrypt SSL certificate installation and management

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN=""
EMAIL=""
WEBROOT_PATH="/var/www/html"
NGINX_CONF="/etc/nginx/sites-available/letsgoal"
NGINX_ENABLED="/etc/nginx/sites-enabled/letsgoal"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_domain_dns() {
    local domain="$1"
    local server_ip
    local domain_ip
    
    # Get server's public IP
    server_ip=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "unknown")
    
    # Get domain's resolved IP
    domain_ip=$(dig +short "$domain" | tail -n1)
    
    log_info "Server IP: $server_ip"
    log_info "Domain IP: $domain_ip"
    
    if [[ "$server_ip" != "$domain_ip" ]]; then
        log_warning "Domain $domain does not resolve to this server ($server_ip)"
        log_warning "Current domain resolution: $domain_ip"
        return 1
    fi
    
    log_success "Domain DNS configuration verified"
    return 0
}

install_certbot() {
    log_info "Installing Certbot..."
    
    # Update package list
    apt-get update -y
    
    # Install certbot and nginx plugin
    apt-get install -y certbot python3-certbot-nginx
    
    log_success "Certbot installed successfully"
}

obtain_certificate() {
    local domain="$1"
    local email="$2"
    local method="${3:-standalone}"
    
    log_info "Obtaining SSL certificate for $domain using $method method..."
    
    if [[ "$method" == "standalone" ]]; then
        # Stop nginx temporarily for standalone authentication
        systemctl stop nginx 2>/dev/null || true
        
        # Obtain certificate using standalone method
        certbot certonly \
            --standalone \
            --non-interactive \
            --agree-tos \
            --email "$email" \
            --domains "$domain" \
            --rsa-key-size 4096 \
            --must-staple
            
        # Start nginx again
        systemctl start nginx
        
    elif [[ "$method" == "webroot" ]]; then
        # Create webroot directory if it doesn't exist
        mkdir -p "$WEBROOT_PATH"
        
        # Obtain certificate using webroot method
        certbot certonly \
            --webroot \
            --webroot-path="$WEBROOT_PATH" \
            --non-interactive \
            --agree-tos \
            --email "$email" \
            --domains "$domain" \
            --rsa-key-size 4096 \
            --must-staple
            
    elif [[ "$method" == "nginx" ]]; then
        # Use nginx plugin (requires existing nginx configuration)
        certbot --nginx \
            --non-interactive \
            --agree-tos \
            --email "$email" \
            --domains "$domain" \
            --rsa-key-size 4096 \
            --redirect
    else
        log_error "Unknown certificate method: $method"
        return 1
    fi
    
    if [[ $? -eq 0 ]]; then
        log_success "SSL certificate obtained successfully"
        return 0
    else
        log_error "Failed to obtain SSL certificate"
        return 1
    fi
}

create_nginx_ssl_config() {
    local domain="$1"
    local app_port="${2:-5001}"
    
    log_info "Creating Nginx SSL configuration..."
    
    cat > "$NGINX_CONF" << EOF
# HTTP server - redirect to HTTPS
server {
    listen 80;
    server_name $domain;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Redirect all HTTP requests to HTTPS
    return 301 https://\$server_name\$request_uri;
}

# HTTPS server - main application
server {
    listen 443 ssl http2;
    server_name $domain;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/$domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$domain/privkey.pem;
    ssl_certificate_key /etc/letsencrypt/live/$domain/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/$domain/chain.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-RSA-AES128-SHA:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:HIGH:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4;
    ssl_prefer_server_ciphers off;
    ssl_dhparam /etc/ssl/certs/dhparam.pem;
    
    # SSL session settings
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Client upload size limit
    client_max_body_size 50M;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json;
    
    # Proxy to application
    location / {
        proxy_pass http://127.0.0.1:$app_port;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_redirect off;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    
    # Security.txt
    location /.well-known/security.txt {
        return 200 "Contact: admin@$domain\nExpires: 2025-12-31T23:59:59.000Z";
        add_header Content-Type text/plain;
    }
}
EOF

    # Generate DH parameters if they don't exist
    if [[ ! -f /etc/ssl/certs/dhparam.pem ]]; then
        log_info "Generating DH parameters (this may take a while)..."
        openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
    fi
    
    # Enable the site
    ln -sf "$NGINX_CONF" "$NGINX_ENABLED"
    
    # Test nginx configuration
    if nginx -t; then
        systemctl reload nginx
        log_success "Nginx SSL configuration created and activated"
    else
        log_error "Nginx configuration test failed"
        return 1
    fi
}

setup_auto_renewal() {
    log_info "Setting up automatic certificate renewal..."
    
    # Create renewal script
    cat > /etc/cron.daily/certbot-renewal << 'EOF'
#!/bin/bash
# Automatic SSL certificate renewal for LetsGoal

/usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"

# Log renewal attempts
echo "$(date): Certificate renewal check completed" >> /var/log/letsgoal-ssl.log
EOF
    
    chmod +x /etc/cron.daily/certbot-renewal
    
    # Also add to crontab as backup
    (crontab -l 2>/dev/null | grep -v certbot; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -
    
    log_success "Automatic renewal configured"
}

test_ssl_setup() {
    local domain="$1"
    
    log_info "Testing SSL certificate setup..."
    
    # Test HTTPS connection
    if curl -s --max-time 10 "https://$domain" > /dev/null; then
        log_success "HTTPS connection test passed"
    else
        log_warning "HTTPS connection test failed - certificate may still be propagating"
    fi
    
    # Test SSL certificate details
    log_info "SSL certificate information:"
    echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -dates
    
    # Test SSL grade (basic check)
    local ssl_grade
    ssl_grade=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -text | grep "Signature Algorithm" | head -1)
    log_info "Certificate signature: $ssl_grade"
}

show_ssl_status() {
    local domain="$1"
    
    echo -e "\n${GREEN}SSL Setup Complete!${NC}\n"
    
    echo -e "${BLUE}Certificate Information:${NC}"
    certbot certificates | grep -A5 "$domain" || log_warning "Certificate details not found"
    
    echo -e "\n${BLUE}Access URLs:${NC}"
    echo "• HTTPS: https://$domain"
    echo "• HTTP: http://$domain (redirects to HTTPS)"
    
    echo -e "\n${BLUE}Certificate Files:${NC}"
    echo "• Certificate: /etc/letsencrypt/live/$domain/fullchain.pem"
    echo "• Private Key: /etc/letsencrypt/live/$domain/privkey.pem"
    echo "• Chain: /etc/letsencrypt/live/$domain/chain.pem"
    
    echo -e "\n${BLUE}Management:${NC}"
    echo "• Renewal: Automatic (daily check via cron)"
    echo "• Manual renewal: certbot renew"
    echo "• Certificate status: certbot certificates"
    echo "• Nginx config: $NGINX_CONF"
    
    echo -e "\n${YELLOW}Important Notes:${NC}"
    echo "• Certificate auto-renews every 60 days"
    echo "• HTTP traffic automatically redirects to HTTPS"
    echo "• Strong SSL configuration with HSTS enabled"
    echo "• Certificate includes OCSP stapling for better performance"
}

usage() {
    echo "SSL Setup Script for LetsGoal"
    echo "Usage: $0 --domain DOMAIN --email EMAIL [OPTIONS]"
    echo ""
    echo "Required:"
    echo "  --domain DOMAIN    Domain name for SSL certificate"
    echo "  --email EMAIL      Email address for Let's Encrypt"
    echo ""
    echo "Options:"
    echo "  --method METHOD    Certificate method: standalone, webroot, nginx (default: standalone)"
    echo "  --port PORT        Application port (default: 5001)"
    echo "  --test-dns         Test DNS configuration before obtaining certificate"
    echo "  --renew           Renew existing certificate"
    echo "  --remove          Remove SSL certificate and configuration"
    echo "  --status          Show SSL certificate status"
    echo "  --help            Show this help message"
}

main() {
    local method="standalone"
    local app_port="5001"
    local test_dns=false
    local renew_cert=false
    local remove_cert=false
    local show_status=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --email)
                EMAIL="$2"
                shift 2
                ;;
            --method)
                method="$2"
                shift 2
                ;;
            --port)
                app_port="$2"
                shift 2
                ;;
            --test-dns)
                test_dns=true
                shift
                ;;
            --renew)
                renew_cert=true
                shift
                ;;
            --remove)
                remove_cert=true
                shift
                ;;
            --status)
                show_status=true
                shift
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Check if running as root
    check_root
    
    # Handle status request
    if [[ "$show_status" == true ]]; then
        if [[ -n "$DOMAIN" ]]; then
            show_ssl_status "$DOMAIN"
        else
            certbot certificates
        fi
        exit 0
    fi
    
    # Handle certificate removal
    if [[ "$remove_cert" == true ]]; then
        if [[ -z "$DOMAIN" ]]; then
            log_error "Domain must be specified for certificate removal"
            exit 1
        fi
        
        log_info "Removing SSL certificate for $DOMAIN..."
        certbot delete --cert-name "$DOMAIN" --non-interactive
        
        # Remove nginx configuration
        rm -f "$NGINX_ENABLED" "$NGINX_CONF"
        systemctl reload nginx
        
        log_success "SSL certificate and configuration removed"
        exit 0
    fi
    
    # Validate required parameters
    if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
        log_error "Domain and email are required"
        usage
        exit 1
    fi
    
    # Test DNS if requested
    if [[ "$test_dns" == true ]]; then
        if ! check_domain_dns "$DOMAIN"; then
            log_error "DNS test failed. Please configure your domain to point to this server."
            exit 1
        fi
    fi
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        install_certbot
    fi
    
    # Handle certificate renewal
    if [[ "$renew_cert" == true ]]; then
        log_info "Renewing SSL certificate for $DOMAIN..."
        certbot renew --cert-name "$DOMAIN"
        systemctl reload nginx
        log_success "Certificate renewal completed"
        exit 0
    fi
    
    # Obtain new certificate
    if obtain_certificate "$DOMAIN" "$EMAIL" "$method"; then
        create_nginx_ssl_config "$DOMAIN" "$app_port"
        setup_auto_renewal
        test_ssl_setup "$DOMAIN"
        show_ssl_status "$DOMAIN"
    else
        log_error "SSL setup failed"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"