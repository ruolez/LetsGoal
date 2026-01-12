import os
import sys
sys.path.append('/app')
sys.path.append('/app/backend')
from flask import Flask, jsonify, request, send_from_directory
from flask_login import LoginManager, login_required, current_user
from flask_cors import CORS
from datetime import datetime, date
from backend.models import db, User, Goal, Subgoal, ProgressEntry, Event, Tag, GoalShare, UserSession, AdminSettings, SystemBackup
from backend.auth import auth_bp
from backend.admin import admin_bp
from backend.event_tracker import EventTracker

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
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
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
    
    @app.route('/admin')
    def admin_page():
        return send_from_directory('../frontend', 'admin.html')
    
    # Goals API endpoints
    @app.route('/api/goals', methods=['GET'])
    @login_required
    def get_goals():
        # Check if archived goals should be included
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        
        # Get goals owned by the user
        owned_goals_query = Goal.query.filter(Goal.owner_id == current_user.id)
        
        # Get goals shared with the user
        shared_goal_ids = db.session.query(GoalShare.goal_id).filter(
            GoalShare.shared_with_user_id == current_user.id
        ).subquery()
        shared_goals_query = Goal.query.filter(Goal.id.in_(shared_goal_ids))
        
        if include_archived:
            # Return only archived goals (owned or shared)
            owned_goals = owned_goals_query.filter(Goal.status == 'archived').all()
            shared_goals = shared_goals_query.filter(Goal.status == 'archived').all()
        else:
            # Return all goals except archived ones (owned or shared)
            owned_goals = owned_goals_query.filter(Goal.status != 'archived').all()
            shared_goals = shared_goals_query.filter(Goal.status != 'archived').all()
        
        # Combine and deduplicate goals
        all_goals = owned_goals + shared_goals
        unique_goals = {goal.id: goal for goal in all_goals}.values()
        
        return jsonify([goal.to_dict(current_user.id) for goal in unique_goals])
    
    @app.route('/api/goals', methods=['POST'])
    @login_required
    def create_goal():
        data = request.get_json()
        
        if not data or not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        goal = Goal(
            user_id=current_user.id,
            owner_id=current_user.id,
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
            return jsonify(goal.to_dict(current_user.id)), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to create goal'}), 500
    
    @app.route('/api/goals/<int:goal_id>', methods=['PUT'])
    @login_required
    def update_goal(goal_id):
        goal = Goal.query.get(goal_id)
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        # Check if user can edit this goal (owner or shared with edit permission)
        if not goal.can_edit(current_user.id):
            return jsonify({'error': 'Permission denied'}), 403
        
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
            return jsonify(goal.to_dict(current_user.id))
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update goal'}), 500
    
    @app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
    @login_required
    def delete_goal(goal_id):
        goal = Goal.query.get(goal_id)
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404

        goal_title = goal.title

        # Check if user is the owner
        if goal.is_owner(current_user.id):
            # Owner deletes: remove goal entirely (and all shares)
            try:
                EventTracker.log_goal_deleted(goal.id, goal_title)

                # Delete related shares first (no cascade in FK constraint)
                GoalShare.query.filter_by(goal_id=goal_id).delete()

                db.session.delete(goal)
                db.session.commit()
                return jsonify({'message': 'Goal deleted successfully'})
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': 'Failed to delete goal'}), 500
        else:
            # Non-owner: check if goal is shared with them, then remove the share
            share = GoalShare.query.filter_by(
                goal_id=goal_id,
                shared_with_user_id=current_user.id
            ).first()

            if not share:
                return jsonify({'error': 'Permission denied. You do not have access to this goal.'}), 403

            try:
                db.session.delete(share)
                db.session.commit()
                return jsonify({'message': 'Goal removed from your shared goals'})
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': 'Failed to remove shared goal'}), 500
    
    # Goal archive/unarchive endpoints
    @app.route('/api/goals/<int:goal_id>/archive', methods=['PUT'])
    @login_required
    def archive_goal(goal_id):
        goal = Goal.query.get(goal_id)
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        # Check if user can edit this goal (owner or shared with edit permission)
        if not goal.can_edit(current_user.id):
            return jsonify({'error': 'Permission denied'}), 403
        
        # Only allow archiving completed goals
        if goal.status != 'completed':
            return jsonify({'error': 'Only completed goals can be archived'}), 400
        
        # Check if already archived
        if goal.status == 'archived':
            return jsonify({'error': 'Goal is already archived'}), 400
        
        try:
            # Update status and set archived date
            old_status = goal.status
            goal.status = 'archived'
            goal.archived_date = date.today()
            goal.updated_at = datetime.utcnow()
            
            # Log archive event
            EventTracker.log_goal_status_changed(goal, old_status, 'archived')
            
            db.session.commit()
            return jsonify(goal.to_dict(current_user.id))
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to archive goal'}), 500
    
    @app.route('/api/goals/<int:goal_id>/unarchive', methods=['PUT'])
    @login_required
    def unarchive_goal(goal_id):
        goal = Goal.query.get(goal_id)
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        # Check if user can edit this goal (owner or shared with edit permission)
        if not goal.can_edit(current_user.id):
            return jsonify({'error': 'Permission denied'}), 403
        
        # Only allow unarchiving archived goals
        if goal.status != 'archived':
            return jsonify({'error': 'Goal is not archived'}), 400
        
        try:
            # Update status back to completed and clear archived date
            old_status = goal.status
            goal.status = 'completed'
            goal.archived_date = None
            goal.updated_at = datetime.utcnow()
            
            # Log unarchive event
            EventTracker.log_goal_status_changed(goal, old_status, 'completed')
            
            db.session.commit()
            return jsonify(goal.to_dict(current_user.id))
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to unarchive goal'}), 500
    
    # Subgoals API endpoints
    @app.route('/api/goals/<int:goal_id>/subgoals', methods=['POST'])
    @login_required
    def create_subgoal(goal_id):
        goal = Goal.query.get(goal_id)
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        # Check if user can edit this goal (owner or shared with edit permission)
        if not goal.can_edit(current_user.id):
            return jsonify({'error': 'Permission denied'}), 403
        
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
        subgoal = Subgoal.query.get(subgoal_id)
        
        if not subgoal:
            return jsonify({'error': 'Subgoal not found'}), 404
        
        # Check if user can edit this subgoal (owner or shared with edit permission)
        if not subgoal.goal.can_edit(current_user.id):
            return jsonify({'error': 'Permission denied'}), 403
        
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
        subgoal = Subgoal.query.get(subgoal_id)
        
        if not subgoal:
            return jsonify({'error': 'Subgoal not found'}), 404
        
        # Check if user can edit this subgoal (owner or shared with edit permission)
        if not subgoal.goal.can_edit(current_user.id):
            return jsonify({'error': 'Permission denied'}), 403
        
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
    
    # Goal Sharing API endpoints
    @app.route('/api/goals/<int:goal_id>/share', methods=['POST'])
    @login_required
    def share_goal(goal_id):
        goal = Goal.query.get(goal_id)
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        # Only owners can share goals
        if not goal.is_owner(current_user.id):
            return jsonify({'error': 'Permission denied. Only goal owners can share goals.'}), 403
        
        data = request.get_json()
        if not data or not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400
        
        # Find user by email
        user_to_share_with = User.query.filter_by(email=data['email'].strip().lower()).first()
        if not user_to_share_with:
            return jsonify({'error': 'User not found with that email address'}), 404
        
        # Prevent sharing with yourself
        if user_to_share_with.id == current_user.id:
            return jsonify({'error': 'You cannot share a goal with yourself'}), 400
        
        # Check if already shared
        existing_share = GoalShare.query.filter_by(
            goal_id=goal_id,
            shared_with_user_id=user_to_share_with.id
        ).first()
        if existing_share:
            return jsonify({'error': 'Goal is already shared with this user'}), 400
        
        # Create the share
        permission_level = data.get('permission_level', 'edit')
        if permission_level not in ['edit', 'view']:
            permission_level = 'edit'
        
        goal_share = GoalShare(
            goal_id=goal_id,
            shared_by_user_id=current_user.id,
            shared_with_user_id=user_to_share_with.id,
            permission_level=permission_level
        )
        
        try:
            db.session.add(goal_share)
            
            # Add "Shared" tag to goal if not already present
            shared_tag = Tag.query.filter_by(user_id=current_user.id, name='Shared').first()
            if shared_tag and shared_tag not in goal.tags:
                goal.tags.append(shared_tag)
            
            # Log sharing event
            EventTracker.log_goal_shared(goal, user_to_share_with)
            
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Goal shared with {user_to_share_with.username}',
                'share': goal_share.to_dict()
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to share goal'}), 500
    
    @app.route('/api/goals/<int:goal_id>/share/<int:user_id>', methods=['DELETE'])
    @login_required
    def unshare_goal(goal_id, user_id):
        goal = Goal.query.get(goal_id)
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        # Only owners can unshare goals
        if not goal.is_owner(current_user.id):
            return jsonify({'error': 'Permission denied. Only goal owners can unshare goals.'}), 403
        
        # Find the share
        goal_share = GoalShare.query.filter_by(
            goal_id=goal_id,
            shared_with_user_id=user_id
        ).first()
        if not goal_share:
            return jsonify({'error': 'Goal is not shared with this user'}), 404
        
        try:
            shared_with_user = goal_share.shared_with
            db.session.delete(goal_share)
            
            # Remove "Shared" tag if no other shares exist
            remaining_shares = GoalShare.query.filter_by(goal_id=goal_id).count()
            if remaining_shares == 1:  # Will be 0 after commit
                shared_tag = Tag.query.filter_by(user_id=current_user.id, name='Shared').first()
                if shared_tag and shared_tag in goal.tags:
                    goal.tags.remove(shared_tag)
            
            # Log unsharing event
            EventTracker.log_goal_unshared(goal, shared_with_user)
            
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Goal unshared from {shared_with_user.username}'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to unshare goal'}), 500
    
    @app.route('/api/goals/<int:goal_id>/shares', methods=['GET'])
    @login_required
    def get_goal_shares(goal_id):
        goal = Goal.query.get(goal_id)
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        # Only owners can view sharing details
        if not goal.is_owner(current_user.id):
            return jsonify({'error': 'Permission denied. Only goal owners can view sharing details.'}), 403
        
        shares = GoalShare.query.filter_by(goal_id=goal_id).all()
        return jsonify([share.to_dict() for share in shares])
    
    @app.route('/api/users/search', methods=['GET'])
    @login_required
    def search_users():
        email = request.args.get('email')
        if not email:
            return jsonify({'error': 'Email parameter is required'}), 400
        
        # Find users by email (exact match for security)
        user = User.query.filter_by(email=email.strip().lower()).first()
        if not user:
            return jsonify({'users': []})
        
        # Don't return the current user in search results
        if user.id == current_user.id:
            return jsonify({'users': []})
        
        return jsonify({
            'users': [{
                'id': user.id,
                'username': user.username,
                'email': user.email
            }]
        })
    
    # Tags API endpoints
    @app.route('/api/tags', methods=['GET'])
    @login_required
    def get_tags():
        tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()
        return jsonify([tag.to_dict() for tag in tags])
    
    @app.route('/api/tags', methods=['POST'])
    @login_required
    def create_tag():
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'error': 'Tag name is required'}), 400
        
        if not data.get('color'):
            return jsonify({'error': 'Tag color is required'}), 400
        
        # Validate color format (should be hex color)
        color = data['color']
        if not color.startswith('#') or len(color) != 7:
            return jsonify({'error': 'Color must be a valid hex color code (e.g., #3B82F6)'}), 400
        
        # Check if tag name already exists for this user
        existing_tag = Tag.query.filter_by(user_id=current_user.id, name=data['name']).first()
        if existing_tag:
            return jsonify({'error': 'A tag with this name already exists'}), 400
        
        tag = Tag(
            user_id=current_user.id,
            name=data['name'].strip(),
            color=color
        )
        
        try:
            db.session.add(tag)
            db.session.commit()
            return jsonify(tag.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to create tag'}), 500
    
    @app.route('/api/tags/<int:tag_id>', methods=['PUT'])
    @login_required
    def update_tag(tag_id):
        tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first()
        if not tag:
            return jsonify({'error': 'Tag not found'}), 404
        
        data = request.get_json()
        
        if data.get('name'):
            # Check if new name conflicts with existing tag
            existing_tag = Tag.query.filter_by(user_id=current_user.id, name=data['name']).first()
            if existing_tag and existing_tag.id != tag_id:
                return jsonify({'error': 'A tag with this name already exists'}), 400
            tag.name = data['name'].strip()
        
        if data.get('color'):
            # Validate color format
            color = data['color']
            if not color.startswith('#') or len(color) != 7:
                return jsonify({'error': 'Color must be a valid hex color code (e.g., #3B82F6)'}), 400
            tag.color = color
        
        tag.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return jsonify(tag.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update tag'}), 500
    
    @app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
    @login_required
    def delete_tag(tag_id):
        tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first()
        if not tag:
            return jsonify({'error': 'Tag not found'}), 404
        
        try:
            db.session.delete(tag)
            db.session.commit()
            return jsonify({'message': 'Tag deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to delete tag'}), 500
    
    @app.route('/api/goals/<int:goal_id>/tags', methods=['PUT'])
    @login_required
    def update_goal_tags(goal_id):
        goal = Goal.query.get(goal_id)
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404
        
        # Check if user can edit this goal (owner or shared with edit permission)
        if not goal.can_edit(current_user.id):
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        tag_ids = data.get('tag_ids', [])
        
        if not isinstance(tag_ids, list):
            return jsonify({'error': 'tag_ids must be a list'}), 400
        
        # Verify all tag IDs belong to the goal owner
        if tag_ids:
            owner_tags = Tag.query.filter(Tag.id.in_(tag_ids), Tag.user_id == goal.owner_id).all()
            if len(owner_tags) != len(tag_ids):
                return jsonify({'error': 'One or more tags not found or do not belong to the goal owner'}), 400
        
        try:
            # Clear existing tags and set new ones
            goal.tags.clear()
            if tag_ids:
                tags = Tag.query.filter(Tag.id.in_(tag_ids), Tag.user_id == goal.owner_id).all()
                goal.tags.extend(tags)
            
            goal.updated_at = datetime.utcnow()
            db.session.commit()
            return jsonify(goal.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update goal tags'}), 500

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

    @app.route('/api/stats/summary', methods=['GET'])
    @login_required
    def get_summary_stats():
        """Get progress summary dashboard stats"""
        from datetime import timedelta
        from sqlalchemy import func, and_, or_

        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Monday of current week

        # Get user's goals (owned and shared)
        shared_goal_ids = db.session.query(GoalShare.goal_id).filter(
            GoalShare.shared_with_user_id == current_user.id
        ).subquery()

        user_goals = Goal.query.filter(
            or_(Goal.owner_id == current_user.id, Goal.id.in_(shared_goal_ids)),
            Goal.status != 'archived'
        ).all()

        goal_ids = [g.id for g in user_goals]

        # TODAY'S FOCUS: Find most urgent goal/subgoal
        today_focus = None
        urgent_subgoal = None
        urgent_goal = None

        # Find subgoals due today or overdue that aren't completed
        if goal_ids:
            urgent_subgoal = Subgoal.query.filter(
                Subgoal.goal_id.in_(goal_ids),
                Subgoal.status != 'achieved',
                Subgoal.target_date != None,
                Subgoal.target_date <= today
            ).order_by(Subgoal.target_date.asc()).first()

            # If no urgent subgoal, find next upcoming subgoal
            if not urgent_subgoal:
                urgent_subgoal = Subgoal.query.filter(
                    Subgoal.goal_id.in_(goal_ids),
                    Subgoal.status != 'achieved',
                    Subgoal.target_date != None
                ).order_by(Subgoal.target_date.asc()).first()

            # Find most urgent goal if no subgoal focus
            if not urgent_subgoal:
                urgent_goal = Goal.query.filter(
                    Goal.id.in_(goal_ids),
                    Goal.status.in_(['created', 'started', 'working']),
                    Goal.target_date != None
                ).order_by(Goal.target_date.asc()).first()

        if urgent_subgoal:
            days_left = (urgent_subgoal.target_date - today).days if urgent_subgoal.target_date else None
            today_focus = {
                'type': 'subgoal',
                'id': urgent_subgoal.id,
                'title': urgent_subgoal.title,
                'goal_id': urgent_subgoal.goal_id,
                'goal_title': urgent_subgoal.goal.title if urgent_subgoal.goal else None,
                'target_date': urgent_subgoal.target_date.isoformat() if urgent_subgoal.target_date else None,
                'days_left': days_left,
                'is_overdue': days_left < 0 if days_left is not None else False
            }
        elif urgent_goal:
            days_left = (urgent_goal.target_date - today).days if urgent_goal.target_date else None
            today_focus = {
                'type': 'goal',
                'id': urgent_goal.id,
                'title': urgent_goal.title,
                'target_date': urgent_goal.target_date.isoformat() if urgent_goal.target_date else None,
                'days_left': days_left,
                'is_overdue': days_left < 0 if days_left is not None else False,
                'progress': urgent_goal.progress
            }

        # WEEKLY STATS
        # Goals completed this week
        goals_completed_this_week = Goal.query.filter(
            Goal.id.in_(goal_ids),
            Goal.status == 'completed',
            Goal.achieved_date >= week_start
        ).count() if goal_ids else 0

        # Subgoals completed this week
        subgoals_completed_this_week = 0
        if goal_ids:
            subgoals_completed_this_week = Subgoal.query.filter(
                Subgoal.goal_id.in_(goal_ids),
                Subgoal.status == 'achieved',
                Subgoal.updated_at >= datetime.combine(week_start, datetime.min.time())
            ).count()

        # Total active goals
        active_goals_count = len([g for g in user_goals if g.status in ['started', 'working']])
        total_goals_count = len(user_goals)
        completed_goals_count = len([g for g in user_goals if g.status == 'completed'])

        # Calculate overall progress (average of all non-archived goals)
        if user_goals:
            total_progress = sum(g.calculate_progress() for g in user_goals)
            overall_progress = round(total_progress / len(user_goals), 1)
        else:
            overall_progress = 0

        # STREAK CALCULATION
        # Count consecutive days with activity (subgoal completions)
        streak = 0
        check_date = today
        max_streak_check = 365  # Max days to check back

        for _ in range(max_streak_check):
            # Check if there was any activity on this date
            day_start = datetime.combine(check_date, datetime.min.time())
            day_end = datetime.combine(check_date, datetime.max.time())

            had_activity = False
            if goal_ids:
                # Check for subgoal completions
                subgoal_activity = Subgoal.query.filter(
                    Subgoal.goal_id.in_(goal_ids),
                    Subgoal.status == 'achieved',
                    Subgoal.updated_at >= day_start,
                    Subgoal.updated_at <= day_end
                ).first()

                if subgoal_activity:
                    had_activity = True
                else:
                    # Check for goal completions
                    goal_activity = Goal.query.filter(
                        Goal.id.in_(goal_ids),
                        Goal.achieved_date == check_date
                    ).first()
                    if goal_activity:
                        had_activity = True

            if had_activity:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                # Allow one grace day for today if no activity yet
                if check_date == today:
                    check_date -= timedelta(days=1)
                else:
                    break

        # RECENT WINS (last 10 completed items)
        recent_wins = []

        if goal_ids:
            # Get recent subgoal completions
            recent_subgoals = Subgoal.query.filter(
                Subgoal.goal_id.in_(goal_ids),
                Subgoal.status == 'achieved'
            ).order_by(Subgoal.updated_at.desc()).limit(8).all()

            for sg in recent_subgoals:
                recent_wins.append({
                    'type': 'subgoal',
                    'id': sg.id,
                    'goal_id': sg.goal_id,
                    'title': sg.title,
                    'completed_at': sg.updated_at.isoformat() if sg.updated_at else None,
                    'goal_title': sg.goal.title if sg.goal else None
                })

            # Get recent goal completions
            recent_goals = Goal.query.filter(
                Goal.id.in_(goal_ids),
                Goal.status == 'completed'
            ).order_by(Goal.achieved_date.desc()).limit(5).all()

            for g in recent_goals:
                recent_wins.append({
                    'type': 'goal',
                    'id': g.id,
                    'goal_id': g.id,
                    'title': g.title,
                    'completed_at': g.achieved_date.isoformat() if g.achieved_date else None
                })

        # Sort wins by completion date and limit to 10
        recent_wins.sort(key=lambda x: x.get('completed_at') or '', reverse=True)
        recent_wins = recent_wins[:10]

        return jsonify({
            'today_focus': today_focus,
            'weekly_stats': {
                'goals_completed': goals_completed_this_week,
                'subgoals_completed': subgoals_completed_this_week,
                'active_goals': active_goals_count,
                'total_goals': total_goals_count,
                'completed_goals': completed_goals_count,
                'overall_progress': overall_progress,
                'week_start': week_start.isoformat()
            },
            'streak': {
                'days': streak,
                'is_active_today': streak > 0 and check_date >= today - timedelta(days=1)
            },
            'recent_wins': recent_wins
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