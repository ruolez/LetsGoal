import os
from flask import Flask, jsonify, request, send_from_directory
from flask_login import LoginManager, login_required, current_user
from flask_cors import CORS
from datetime import datetime, date
from models import db, User, Goal, Subgoal, ProgressEntry
from auth import auth_bp

def create_app():
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////app/database/letsgoal.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, supports_credentials=True)
    
    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({'status': 'healthy'}), 200
    
    # Static file serving
    @app.route('/')
    def index():
        return send_from_directory('../frontend', 'login.html')
    
    @app.route('/login')
    def login_page():
        return send_from_directory('../frontend', 'login.html')
    
    @app.route('/dashboard')
    def dashboard_page():
        return send_from_directory('../frontend', 'dashboard.html')
    
    # Goals API endpoints
    @app.route('/api/goals', methods=['GET'])
    @login_required
    def get_goals():
        goals = Goal.query.filter_by(user_id=current_user.id).all()
        return jsonify([goal.to_dict() for goal in goals])
    
    @app.route('/api/goals', methods=['POST'])
    @login_required
    def create_goal():
        data = request.get_json()
        
        if not data or not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        goal = Goal(
            user_id=current_user.id,
            title=data['title'],
            description=data.get('description', ''),
            target_date=datetime.strptime(data['target_date'], '%Y-%m-%d').date() if data.get('target_date') else None,
            status='pending'
        )
        
        try:
            db.session.add(goal)
            db.session.commit()
            return jsonify(goal.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to create goal'}), 500
    
    @app.route('/api/goals/<int:goal_id>', methods=['PUT'])
    @login_required
    def update_goal(goal_id):
        goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        data = request.get_json()
        
        if data.get('title'):
            goal.title = data['title']
        if data.get('description') is not None:
            goal.description = data['description']
        if data.get('target_date'):
            goal.target_date = datetime.strptime(data['target_date'], '%Y-%m-%d').date()
        if data.get('status'):
            goal.status = data['status']
            if data['status'] == 'achieved' and not goal.achieved_date:
                goal.achieved_date = date.today()
        
        goal.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return jsonify(goal.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update goal'}), 500
    
    @app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
    @login_required
    def delete_goal(goal_id):
        goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        try:
            db.session.delete(goal)
            db.session.commit()
            return jsonify({'message': 'Goal deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to delete goal'}), 500
    
    # Subgoals API endpoints
    @app.route('/api/goals/<int:goal_id>/subgoals', methods=['POST'])
    @login_required
    def create_subgoal(goal_id):
        goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        data = request.get_json()
        if not data or not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        subgoal = Subgoal(
            goal_id=goal_id,
            title=data['title'],
            description=data.get('description', ''),
            target_date=datetime.strptime(data['target_date'], '%Y-%m-%d').date() if data.get('target_date') else None,
            order_index=data.get('order_index', 0)
        )
        
        try:
            db.session.add(subgoal)
            db.session.commit()
            return jsonify(subgoal.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to create subgoal'}), 500
    
    @app.route('/api/subgoals/<int:subgoal_id>', methods=['PUT'])
    @login_required
    def update_subgoal(subgoal_id):
        subgoal = Subgoal.query.join(Goal).filter(
            Subgoal.id == subgoal_id,
            Goal.user_id == current_user.id
        ).first()
        
        if not subgoal:
            return jsonify({'error': 'Subgoal not found'}), 404
        
        data = request.get_json()
        
        if data.get('title'):
            subgoal.title = data['title']
        if data.get('description') is not None:
            subgoal.description = data['description']
        if data.get('target_date'):
            subgoal.target_date = datetime.strptime(data['target_date'], '%Y-%m-%d').date()
        if data.get('status'):
            subgoal.status = data['status']
            if data['status'] == 'achieved' and not subgoal.achieved_date:
                subgoal.achieved_date = date.today()
        
        subgoal.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return jsonify(subgoal.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update subgoal'}), 500
    
    @app.route('/api/subgoals/<int:subgoal_id>', methods=['DELETE'])
    @login_required
    def delete_subgoal(subgoal_id):
        subgoal = Subgoal.query.join(Goal).filter(
            Subgoal.id == subgoal_id,
            Goal.user_id == current_user.id
        ).first()
        
        if not subgoal:
            return jsonify({'error': 'Subgoal not found'}), 404
        
        try:
            db.session.delete(subgoal)
            db.session.commit()
            return jsonify({'message': 'Subgoal deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to delete subgoal'}), 500
    
    # Progress tracking endpoints
    @app.route('/api/goals/<int:goal_id>/progress', methods=['POST'])
    @login_required
    def add_progress(goal_id):
        goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        data = request.get_json()
        if not data or 'progress_percentage' not in data:
            return jsonify({'error': 'Progress percentage is required'}), 400
        
        progress = ProgressEntry(
            goal_id=goal_id,
            progress_percentage=data['progress_percentage'],
            notes=data.get('notes', ''),
            entry_date=datetime.strptime(data['entry_date'], '%Y-%m-%d').date() if data.get('entry_date') else date.today()
        )
        
        try:
            db.session.add(progress)
            db.session.commit()
            return jsonify(progress.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to add progress'}), 500
    
    # Dashboard stats endpoint
    @app.route('/api/dashboard/stats', methods=['GET'])
    @login_required
    def get_dashboard_stats():
        total_goals = Goal.query.filter_by(user_id=current_user.id).count()
        achieved_goals = Goal.query.filter_by(user_id=current_user.id, status='achieved').count()
        active_goals = Goal.query.filter_by(user_id=current_user.id, status='in_progress').count()
        pending_goals = Goal.query.filter_by(user_id=current_user.id, status='pending').count()
        
        return jsonify({
            'total_goals': total_goals,
            'achieved_goals': achieved_goals,
            'active_goals': active_goals,
            'pending_goals': pending_goals,
            'achievement_rate': round((achieved_goals / total_goals * 100) if total_goals > 0 else 0, 1)
        })
    
    # History and reporting endpoint
    @app.route('/api/reports/history', methods=['GET'])
    @login_required
    def get_history_report():
        achieved_goals = Goal.query.filter_by(
            user_id=current_user.id, 
            status='achieved'
        ).order_by(Goal.achieved_date.desc()).all()
        
        # Calculate timing analysis
        timing_analysis = []
        for goal in achieved_goals:
            if goal.target_date and goal.achieved_date:
                days_diff = (goal.achieved_date - goal.target_date).days
                timing_analysis.append({
                    'goal_id': goal.id,
                    'title': goal.title,
                    'target_date': goal.target_date.isoformat(),
                    'achieved_date': goal.achieved_date.isoformat(),
                    'days_difference': days_diff,
                    'status': 'early' if days_diff < 0 else 'on_time' if days_diff == 0 else 'late'
                })
        
        # Monthly achievement trends
        monthly_trends = {}
        for goal in achieved_goals:
            if goal.achieved_date:
                month_key = goal.achieved_date.strftime('%Y-%m')
                monthly_trends[month_key] = monthly_trends.get(month_key, 0) + 1
        
        return jsonify({
            'achieved_goals': [goal.to_dict() for goal in achieved_goals],
            'timing_analysis': timing_analysis,
            'monthly_trends': monthly_trends,
            'total_achievements': len(achieved_goals)
        })
    
    # Initialize database
    with app.app_context():
        db.create_all()
        
        # Execute schema if database is empty
        if User.query.count() == 0:
            try:
                with open('/app/database/schema.sql', 'r') as f:
                    schema = f.read()
                    # SQLAlchemy doesn't handle multiple statements well, so we'll rely on create_all()
            except FileNotFoundError:
                pass  # Schema file not found, but create_all() will handle table creation
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)