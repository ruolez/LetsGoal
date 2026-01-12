#!/usr/bin/env python3
import sys
import os
sys.path.append('/app')
sys.path.append('/app/backend')

# Set environment variables for Flask
os.environ['FLASK_APP'] = 'backend/app.py'
os.environ['DATABASE_URL'] = 'sqlite:////app/database/letsgoal.db'

from backend.models import db, User
from backend.app import create_app

def create_admin_user():
    app = create_app()
    
    with app.app_context():
        try:
            # Check if admin user exists
            admin = User.query.filter_by(role='admin').first()
            if admin:
                print(f'Admin user already exists: {admin.username} ({admin.email})')
                return
            
            # Create admin user
            admin_user = User(username='admin', email='admin@letsgoal.com', role='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            
            print('✅ Admin user created successfully!')
            print('')
            print('Login credentials:')
            print('Username: admin')
            print('Email: admin@letsgoal.com')
            print('Password: admin123')
            print('')
            print('Access the admin dashboard at: http://localhost:8080/admin')
            
        except Exception as e:
            print(f'Error creating admin user: {e}')

if __name__ == '__main__':
    create_admin_user()