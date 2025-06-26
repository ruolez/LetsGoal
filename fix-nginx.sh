#!/bin/bash

# Quick fix for LetsGoal nginx configuration

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== LetsGoal Nginx Configuration Fix ===${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Please run this script with sudo: sudo ./fix-nginx.sh${NC}"
   exit 1
fi

# Load configuration
if [[ -f /opt/letsgoal/.env ]]; then
    source /opt/letsgoal/.env
else
    echo -e "${RED}Configuration file not found at /opt/letsgoal/.env${NC}"
    exit 1
fi

echo -e "${YELLOW}Configuration detected:${NC}"
echo "• Deployment Type: $DEPLOYMENT_TYPE"
echo "• Domain/IP: $DOMAIN_OR_IP"
echo "• SSL Enabled: $USE_SSL"
echo ""

# First, ensure the application is running
echo -e "${BLUE}1. Starting LetsGoal application...${NC}"
cd /opt/letsgoal
docker-compose -f docker-compose.prod.yml up -d

# Wait for application to start
echo "Waiting for application to start..."
sleep 10

# Check if application is responding
if curl -s http://127.0.0.1:5001/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ Application is running${NC}"
else
    echo -e "${RED}✗ Application is not responding. Checking logs...${NC}"
    docker logs letsgoal-backend --tail 20
    exit 1
fi

# Disable default nginx site
echo -e "${BLUE}2. Disabling default nginx site...${NC}"
rm -f /etc/nginx/sites-enabled/default

# Create proper nginx configuration based on deployment type
echo -e "${BLUE}3. Creating nginx configuration...${NC}"

if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
    # For local deployment, create simple proxy config
    cat > /etc/nginx/sites-available/letsgoal << EOF
server {
    listen 80 default_server;
    server_name _;
    
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
    echo -e "${GREEN}✓ Created local network configuration${NC}"
    
elif [[ "$DEPLOYMENT_TYPE" == "domain" ]]; then
    # For domain deployment
    if [[ "$USE_SSL" == "y" ]]; then
        # HTTPS configuration
        cat > /etc/nginx/sites-available/letsgoal << EOF
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
        echo -e "${GREEN}✓ Created HTTPS configuration${NC}"
    else
        # HTTP only configuration
        cat > /etc/nginx/sites-available/letsgoal << EOF
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
        echo -e "${GREEN}✓ Created HTTP configuration${NC}"
    fi
fi

# Enable the site
echo -e "${BLUE}4. Enabling LetsGoal site...${NC}"
ln -sf /etc/nginx/sites-available/letsgoal /etc/nginx/sites-enabled/letsgoal

# Test nginx configuration
echo -e "${BLUE}5. Testing nginx configuration...${NC}"
if nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration test failed${NC}"
    exit 1
fi

# Reload nginx
echo -e "${BLUE}6. Reloading nginx...${NC}"
systemctl reload nginx

# Final check
echo -e "${BLUE}7. Performing final checks...${NC}"
sleep 3

# Test the site
if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
    TEST_URL="http://$DOMAIN_OR_IP"
    if [[ "$DOMAIN_OR_IP" != *":"* ]]; then
        TEST_URL="http://$DOMAIN_OR_IP:80"
    fi
else
    if [[ "$USE_SSL" == "y" ]]; then
        TEST_URL="https://$DOMAIN_OR_IP"
    else
        TEST_URL="http://$DOMAIN_OR_IP"
    fi
fi

echo "Testing $TEST_URL ..."
if curl -s -I "$TEST_URL" | grep -q "200 OK"; then
    echo -e "${GREEN}✓ Site is accessible!${NC}"
else
    echo -e "${YELLOW}⚠ Site may still be starting up or DNS propagating${NC}"
fi

echo ""
echo -e "${GREEN}=== Fix Applied Successfully ===${NC}"
echo ""
echo "Access your site at:"
if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
    echo "• http://$DOMAIN_OR_IP (port 80)"
    echo "• http://$DOMAIN_OR_IP:5001 (direct access)"
else
    if [[ "$USE_SSL" == "y" ]]; then
        echo "• https://$DOMAIN_OR_IP"
    else
        echo "• http://$DOMAIN_OR_IP"
    fi
fi
echo ""
echo "If you still see the nginx welcome page:"
echo "1. Clear your browser cache (Ctrl+F5)"
echo "2. Try incognito/private mode"
echo "3. Check DNS propagation if using a domain"