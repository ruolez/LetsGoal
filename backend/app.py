import os
from flask import Flask, jsonify, request, send_from_directory
from flask_login import LoginManager, login_required, current_user
from flask_cors import CORS
from datetime import datetime, date
from models import db, User, Goal, Subgoal, ProgressEntry, Event
from auth import auth_bp
from event_tracker import EventTracker

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
            status='created'
        )
        
        try:
            db.session.add(goal)
            db.session.flush()  # Flush to get the goal ID
            
            # Log event
            EventTracker.log_goal_created(goal)
            
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
        
        # Track changes for event logging
        changes = {}
        old_status = goal.status
        
        if data.get('title') and data['title'] != goal.title:
            changes['title'] = {'old': goal.title, 'new': data['title']}
            goal.title = data['title']
            
        if data.get('description') is not None and data['description'] != goal.description:
            changes['description'] = {'old': goal.description, 'new': data['description']}
            goal.description = data['description']
            
        if data.get('target_date'):
            new_target_date = datetime.strptime(data['target_date'], '%Y-%m-%d').date()
            if new_target_date != goal.target_date:
                changes['target_date'] = {
                    'old': goal.target_date.isoformat() if goal.target_date else None,
                    'new': new_target_date.isoformat()
                }
                goal.target_date = new_target_date
                
        if data.get('status') and data['status'] != goal.status:
            changes['status'] = {'old': goal.status, 'new': data['status']}
            goal.status = data['status']
            if data['status'] == 'completed' and not goal.achieved_date:
                goal.achieved_date = date.today()
                changes['achieved_date'] = {'old': None, 'new': goal.achieved_date.isoformat()}
            elif data['status'] != 'completed' and goal.achieved_date:
                changes['achieved_date'] = {'old': goal.achieved_date.isoformat(), 'new': None}
                goal.achieved_date = None
        
        goal.updated_at = datetime.utcnow()
        
        try:
            # Log events for changes
            if changes:
                EventTracker.log_goal_updated(goal, changes)
                
                # Special event for status changes
                if 'status' in changes:
                    EventTracker.log_goal_status_changed(goal, old_status, goal.status)
                    
                    # Special event for completion
                    if goal.status == 'completed':
                        EventTracker.log_goal_completed(goal)
            
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
        
        # Store info for event logging before deletion
        goal_title = goal.title
        
        try:
            # Log deletion event
            EventTracker.log_goal_deleted(goal.id, goal_title)
            
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
            db.session.flush()  # Flush to get subgoal ID
            
            # Log subgoal creation event
            EventTracker.log_subgoal_created(subgoal)
            
            # Update parent goal's updated_at timestamp
            goal.updated_at = datetime.utcnow()
            
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
        
        # Track changes for event logging
        changes = {}
        old_status = subgoal.status
        goal = subgoal.goal
        old_goal_status = goal.status if goal else None
        
        if data.get('title') and data['title'] != subgoal.title:
            changes['title'] = {'old': subgoal.title, 'new': data['title']}
            subgoal.title = data['title']
            
        if data.get('description') is not None and data['description'] != subgoal.description:
            changes['description'] = {'old': subgoal.description, 'new': data['description']}
            subgoal.description = data['description']
            
        if data.get('target_date'):
            new_target_date = datetime.strptime(data['target_date'], '%Y-%m-%d').date()
            if new_target_date != subgoal.target_date:
                changes['target_date'] = {
                    'old': subgoal.target_date.isoformat() if subgoal.target_date else None,
                    'new': new_target_date.isoformat()
                }
                subgoal.target_date = new_target_date
                
        if data.get('status') and data['status'] != subgoal.status:
            changes['status'] = {'old': subgoal.status, 'new': data['status']}
            subgoal.status = data['status']
            
            # Handle achieved date
            if data['status'] == 'achieved' and not subgoal.achieved_date:
                subgoal.achieved_date = date.today()
                changes['achieved_date'] = {'old': None, 'new': subgoal.achieved_date.isoformat()}
            elif data['status'] == 'pending' and subgoal.achieved_date:
                changes['achieved_date'] = {'old': subgoal.achieved_date.isoformat(), 'new': None}
                subgoal.achieved_date = None
            
            # Update goal status based on subgoal progress
            if goal and old_status != data['status']:
                # Recalculate goal progress and update status
                achieved_count = sum(1 for sg in goal.subgoals if sg.status == 'achieved' or (sg.id == subgoal.id and data['status'] == 'achieved'))
                total_count = len(goal.subgoals)
                progress = int((achieved_count / total_count) * 100) if total_count > 0 else 0
                
                # Auto-update goal status based on new system: Created -> Started -> Working -> Completed
                if progress == 100 and goal.status != 'completed':
                    goal.status = 'completed'
                    goal.achieved_date = date.today()
                elif achieved_count == 1 and goal.status == 'created':
                    goal.status = 'started'
                elif achieved_count >= 2 and goal.status in ['created', 'started']:
                    goal.status = 'working'
                elif progress == 0:
                    goal.status = 'created'
                    if goal.achieved_date:
                        goal.achieved_date = None
                
                # Update goal timestamp for cascading updates
                goal.updated_at = datetime.utcnow()
        
        # Always update goal timestamp when any subgoal is modified
        if goal:
            goal.updated_at = datetime.utcnow()
        
        subgoal.updated_at = datetime.utcnow()
        
        try:
            # Log events for changes
            if changes:
                EventTracker.log_subgoal_updated(subgoal, changes)
                
                # Special event for status changes
                if 'status' in changes:
                    EventTracker.log_subgoal_status_changed(subgoal, old_status, subgoal.status)
                    
                    # Special event for completion
                    if subgoal.status == 'achieved':
                        EventTracker.log_subgoal_completed(subgoal)
            
            # Log goal status change if it occurred
            if goal and old_goal_status != goal.status:
                EventTracker.log_goal_status_changed(goal, old_goal_status, goal.status)
                if goal.status == 'completed':
                    EventTracker.log_goal_completed(goal)
            
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
        
        # Store info for event logging before deletion
        subgoal_title = subgoal.title
        goal_id = subgoal.goal_id
        goal_title = subgoal.goal.title if subgoal.goal else None
        goal = subgoal.goal
        
        try:
            # Log deletion event
            EventTracker.log_subgoal_deleted(subgoal.id, subgoal_title, goal_id, goal_title)
            
            db.session.delete(subgoal)
            
            # Update parent goal's timestamp for cascading updates
            if goal:
                goal.updated_at = datetime.utcnow()
            
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
        completed_goals = Goal.query.filter_by(user_id=current_user.id, status='completed').count()
        working_goals = Goal.query.filter_by(user_id=current_user.id, status='working').count()
        started_goals = Goal.query.filter_by(user_id=current_user.id, status='started').count()
        created_goals = Goal.query.filter_by(user_id=current_user.id, status='created').count()
        active_goals = working_goals + started_goals
        
        return jsonify({
            'total_goals': total_goals,
            'completed_goals': completed_goals,
            'active_goals': active_goals,
            'working_goals': working_goals,
            'started_goals': started_goals,
            'created_goals': created_goals,
            'achievement_rate': round((completed_goals / total_goals * 100) if total_goals > 0 else 0, 1)
        })
    
    # History and reporting endpoint
    @app.route('/api/reports/history', methods=['GET'])
    @login_required
    def get_history_report():
        completed_goals = Goal.query.filter_by(
            user_id=current_user.id, 
            status='completed'
        ).order_by(Goal.achieved_date.desc()).all()
        
        # Calculate timing analysis
        timing_analysis = []
        for goal in completed_goals:
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
        for goal in completed_goals:
            if goal.achieved_date:
                month_key = goal.achieved_date.strftime('%Y-%m')
                monthly_trends[month_key] = monthly_trends.get(month_key, 0) + 1
        
        return jsonify({
            'completed_goals': [goal.to_dict() for goal in completed_goals],
            'timing_analysis': timing_analysis,
            'monthly_trends': monthly_trends,
            'total_achievements': len(completed_goals)
        })
    
    # Event-based API endpoints for activity tracking
    @app.route('/api/events', methods=['GET'])
    @login_required
    def get_events():
        """Get recent events for the current user"""
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 events
        events = EventTracker.get_recent_events(current_user.id, limit)
        return jsonify([event.to_dict() for event in events])
    
    @app.route('/api/goals/<int:goal_id>/events', methods=['GET'])
    @login_required
    def get_goal_events(goal_id):
        """Get all events for a specific goal"""
        # Verify goal belongs to current user
        goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        events = EventTracker.get_goal_events(goal_id, current_user.id)
        return jsonify([event.to_dict() for event in events])
    
    @app.route('/api/dashboard/recent-activity', methods=['GET'])
    @login_required
    def get_recent_activity():
        """Get recent activity summary for dashboard"""
        limit = int(request.args.get('limit', 20))
        events = EventTracker.get_recent_events(current_user.id, limit)
        
        # Group events by date for better presentation
        activity_by_date = {}
        for event in events:
            date_key = event.created_at.date().isoformat()
            if date_key not in activity_by_date:
                activity_by_date[date_key] = []
            activity_by_date[date_key].append(event.to_dict())
        
        return jsonify({
            'events': [event.to_dict() for event in events],
            'activity_by_date': activity_by_date,
            'total_events': len(events)
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