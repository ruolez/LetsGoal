#!/bin/bash
# LetsGoal Development Setup Script
# Quick setup for development with admin dashboard support

set -e

echo "🚀 Setting up LetsGoal Development Environment with Admin Dashboard"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "📦 Building containers..."
docker-compose build

echo "🗄️ Setting up database..."
docker-compose up -d redis
sleep 3

echo "🔧 Running migrations..."
docker-compose up -d backend
sleep 10

# Run migrations
docker exec letsgoal-backend python backend/migrations/add_admin_system.py 2>/dev/null || echo "Admin migration may already exist"
docker exec letsgoal-backend python backend/migrations/add_event_tracking.py 2>/dev/null || echo "Event tracking migration may already exist"
docker exec letsgoal-backend python backend/migrations/add_tagging_system.py 2>/dev/null || echo "Tagging migration may already exist"

echo "👤 Starting admin container..."
docker-compose up -d admin
sleep 10

echo "✅ Development environment ready!"
echo ""
echo "📍 Access Points:"
echo "   Main App:        http://localhost:5001"
echo "   Admin Dashboard: http://localhost:5002/admin"
echo "   Redis:           localhost:6379"
echo ""
echo "🔑 Default Admin Credentials:"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "📋 Useful Commands:"
echo "   View logs:     docker-compose logs -f [backend|admin|redis]"
echo "   Stop all:      docker-compose down"
echo "   Restart:       docker-compose restart [service]"
echo "   Shell access:  docker exec -it letsgoal-backend bash"
echo ""