#!/bin/bash
# LetsGoal Admin Dashboard Troubleshooting Script

echo "🔍 LetsGoal Admin Dashboard Troubleshooting"
echo "============================================"

# Check container status
echo "📦 Container Status:"
echo "--------------------"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep letsgoal

echo ""
echo "🏥 Health Checks:"
echo "------------------"

# Main app health
if curl -s http://localhost:5001/health | grep -q "healthy"; then
    echo "✅ Main application: Healthy"
else
    echo "❌ Main application: Unhealthy"
fi

# Admin health  
if curl -s http://localhost:5002/health | grep -q "healthy"; then
    echo "✅ Admin dashboard: Healthy"
else
    echo "❌ Admin dashboard: Unhealthy"
fi

# Redis health
if docker exec letsgoal-redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo "✅ Redis: Healthy"
else
    echo "❌ Redis: Unhealthy"
fi

echo ""
echo "🌐 Network Tests:"
echo "------------------"

# Test nginx routing (if in production)
if curl -s http://localhost/admin 2>/dev/null | head -n1 | grep -q "HTTP"; then
    echo "✅ Nginx admin routing: Working"
else
    echo "ℹ️  Nginx admin routing: Not tested (dev mode or not configured)"
fi

echo ""
echo "📋 Recent Logs (Last 20 lines):"
echo "--------------------------------"
echo "Backend:"
docker logs letsgoal-backend --tail 5 2>/dev/null | head -5

echo ""
echo "Admin:"
docker logs letsgoal-admin --tail 5 2>/dev/null | head -5

echo ""
echo "Redis:"
docker logs letsgoal-redis --tail 5 2>/dev/null | head -5

echo ""
echo "💡 Quick Fixes:"
echo "---------------"
echo "1. Restart all containers:     docker-compose restart"
echo "2. Restart admin only:         docker-compose restart admin"  
echo "3. View admin logs:            docker logs letsgoal-admin -f"
echo "4. Reset admin container:      docker-compose down && docker-compose up -d"
echo "5. Check admin database:       docker exec letsgoal-admin python -c \"from models import User; print(User.query.all())\""

echo ""
echo "🚨 Common Issues:"
echo "----------------"
echo "- Admin container not starting: Check if port 5002 is available"
echo "- Can't access /admin: Verify nginx configuration or use direct port 5002"
echo "- Database errors: Ensure admin_system migration has run"
echo "- Redis connection issues: Check if Redis container is running"