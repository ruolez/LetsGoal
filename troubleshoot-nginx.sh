#!/bin/bash

# LetsGoal Nginx Troubleshooting Script

echo "=== LetsGoal Nginx Troubleshooting ==="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "Please run this script with sudo: sudo ./troubleshoot-nginx.sh"
   exit 1
fi

echo "1. Checking Docker containers..."
docker ps -a | grep letsgoal
echo ""

echo "2. Checking container logs..."
docker logs letsgoal-backend --tail 20
echo ""

echo "3. Checking nginx configuration..."
ls -la /etc/nginx/sites-available/letsgoal
ls -la /etc/nginx/sites-enabled/letsgoal
echo ""

echo "4. Checking if application is responding..."
curl -s http://127.0.0.1:5001/health || echo "Application not responding on port 5001"
echo ""

echo "5. Checking nginx sites enabled..."
ls -la /etc/nginx/sites-enabled/
echo ""

echo "6. Testing nginx configuration..."
nginx -t
echo ""

echo "7. Checking application environment..."
if [[ -f /opt/letsgoal/.env ]]; then
    echo "Environment file exists"
    grep -E "DEPLOYMENT_TYPE|DOMAIN_OR_IP|USE_SSL" /opt/letsgoal/.env
else
    echo "Environment file missing!"
fi
echo ""

echo "8. Checking current working directory..."
cd /opt/letsgoal
pwd
docker-compose -f docker-compose.prod.yml ps
echo ""

echo "9. Port usage check..."
netstat -tlnp | grep -E ":(80|443|5001)\s" || ss -tlnp | grep -E ":(80|443|5001)\s"