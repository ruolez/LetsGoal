#!/usr/bin/env python3
"""
LetsGoal Admin Application Entry Point
Separate Flask app for admin dashboard functionality
"""

import os
import sys
sys.path.append('/app')
from flask import Flask, send_from_directory, request
from flask_login import LoginManager, login_required
from flask_cors import CORS
from backend.models import db, User
from backend.auth import auth_bp, admin_required
from backend.admin import admin_bp
import logging

def create_admin_app():
    """Factory function to create the admin Flask application"""
    app = Flask(__name__, 
                static_folder='../frontend',
                template_folder='../frontend')
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///letsgoal.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True
    
    # CORS configuration for admin
    cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS(app, supports_credentials=True, origins=cors_origins)
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access the admin dashboard.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # Admin-specific routes
    @app.route('/')
    @app.route('/admin')
    @login_required
    @admin_required
    def admin_dashboard():
        """Serve the admin dashboard"""
        return send_from_directory('../frontend', 'admin.html')
    
    @app.route('/css/<path:filename>')
    def admin_css(filename):
        """Serve CSS files"""
        return send_from_directory('../frontend/css', filename)
    
    @app.route('/js/<path:filename>')
    def admin_js(filename):
        """Serve JS files"""
        return send_from_directory('../frontend/js', filename)
    
    @app.route('/assets/<path:filename>')
    def admin_assets(filename):
        """Serve asset files"""
        return send_from_directory('../frontend/assets', filename)
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return {'status': 'healthy', 'service': 'letsgoal-admin'}, 200
    
    # Create tables if they don't exist
    with app.app_context():
        try:
            db.create_all()
            
            # Create default admin user if it doesn't exist
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@letsgoal.com',
                    role='admin'
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                app.logger.info('Created default admin user (admin/admin123)')
        except Exception as e:
            app.logger.error(f'Database initialization error: {e}')
    
    return app

# Create the application instance
app = create_admin_app()

if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5000, debug=True)