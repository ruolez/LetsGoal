import sys
sys.path.append('/app')
from flask import Blueprint, request, jsonify
from flask_login import current_user
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from backend.models import db, User, Goal, Subgoal, Tag, Event, UserSession, AdminSettings, SystemBackup, Plan, StripeCustomer, Subscription, SubscriptionHistory, Invoice
from backend.auth import admin_required
from backend.stripe_service import stripe_service
import json

admin_bp = Blueprint('admin', __name__)

# User Management Endpoints
@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users with statistics"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)  # Max 100 per page
        
        # Get search parameter
        search = request.args.get('search', '')
        
        # Build query
        query = User.query
        
        if search:
            query = query.filter(
                (User.username.contains(search)) |
                (User.email.contains(search))
            )
        
        # Paginate users
        users_pagination = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        users_with_stats = []
        for user in users_pagination.items:
            # Get user statistics
            total_goals = Goal.query.filter(
                (Goal.user_id == user.id) | (Goal.owner_id == user.id)
            ).count()
            
            completed_goals = Goal.query.filter(
                and_(
                    (Goal.user_id == user.id) | (Goal.owner_id == user.id),
                    Goal.status == 'completed'
                )
            ).count()
            
            active_goals = Goal.query.filter(
                and_(
                    (Goal.user_id == user.id) | (Goal.owner_id == user.id),
                    Goal.status.in_(['created', 'started', 'working'])
                )
            ).count()
            
            archived_goals = Goal.query.filter(
                and_(
                    (Goal.user_id == user.id) | (Goal.owner_id == user.id),
                    Goal.status == 'archived'
                )
            ).count()
            
            # Get shared goals count (goals shared BY this user)
            shared_goals = db.session.query(func.count(Goal.id)).join(
                Goal.shares
            ).filter(Goal.owner_id == user.id).scalar() or 0
            
            # Get total subgoals
            total_subgoals = db.session.query(func.count(Subgoal.id)).join(
                Goal
            ).filter(
                (Goal.user_id == user.id) | (Goal.owner_id == user.id)
            ).scalar() or 0
            
            # Get last session info
            last_session = UserSession.query.filter_by(
                user_id=user.id
            ).order_by(desc(UserSession.session_start)).first()
            
            # Calculate days since last login
            days_since_login = None
            if user.last_login_at:
                days_since_login = (datetime.utcnow() - user.last_login_at).days
            
            user_data = user.to_dict()
            user_data.update({
                'stats': {
                    'total_goals': total_goals,
                    'completed_goals': completed_goals,
                    'active_goals': active_goals,
                    'archived_goals': archived_goals,
                    'shared_goals': shared_goals,
                    'total_subgoals': total_subgoals,
                    'days_since_login': days_since_login,
                    'last_session_duration': last_session.get_duration_minutes() if last_session else 0
                }
            })
            users_with_stats.append(user_data)
        
        return jsonify({
            'users': users_with_stats,
            'pagination': {
                'page': users_pagination.page,
                'pages': users_pagination.pages,
                'per_page': users_pagination.per_page,
                'total': users_pagination.total,
                'has_next': users_pagination.has_next,
                'has_prev': users_pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch users: {str(e)}'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_details(user_id):
    """Get detailed information about a specific user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Get detailed goal statistics
        goals = Goal.query.filter(
            (Goal.user_id == user_id) | (Goal.owner_id == user_id)
        ).all()
        
        goal_stats = {
            'total': len(goals),
            'by_status': {},
            'recent_activity': []
        }
        
        # Count goals by status
        for goal in goals:
            status = goal.status
            goal_stats['by_status'][status] = goal_stats['by_status'].get(status, 0) + 1
            
            # Add recent activity
            if goal.updated_at and goal.updated_at > datetime.utcnow() - timedelta(days=30):
                goal_stats['recent_activity'].append({
                    'goal_id': goal.id,
                    'goal_title': goal.title,
                    'updated_at': goal.updated_at.isoformat(),
                    'status': goal.status
                })
        
        # Sort recent activity by date
        goal_stats['recent_activity'].sort(key=lambda x: x['updated_at'], reverse=True)
        goal_stats['recent_activity'] = goal_stats['recent_activity'][:10]  # Limit to 10
        
        # Get user sessions
        sessions = UserSession.query.filter_by(
            user_id=user_id
        ).order_by(desc(UserSession.session_start)).limit(20).all()
        
        session_data = [session.to_dict() for session in sessions]
        
        # Get recent events
        recent_events = Event.query.filter_by(
            user_id=user_id
        ).order_by(desc(Event.created_at)).limit(50).all()
        
        events_data = [event.to_dict() for event in recent_events]
        
        return jsonify({
            'user': user.to_dict(),
            'goal_stats': goal_stats,
            'sessions': session_data,
            'recent_events': events_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch user details: {str(e)}'}), 500

@admin_bp.route('/users/<int:user_id>/activity', methods=['GET'])
@admin_required
def get_user_activity(user_id):
    """Get detailed activity history for a user"""
    try:
        # Get date range parameters
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get user sessions in date range
        sessions = UserSession.query.filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.session_start >= start_date
            )
        ).order_by(desc(UserSession.session_start)).all()
        
        # Get user events in date range
        events = Event.query.filter(
            and_(
                Event.user_id == user_id,
                Event.created_at >= start_date
            )
        ).order_by(desc(Event.created_at)).all()
        
        # Calculate activity summary
        activity_summary = {
            'total_sessions': len(sessions),
            'total_session_time': sum(s.get_duration_minutes() for s in sessions),
            'total_events': len(events),
            'events_by_type': {},
            'sessions_by_day': {},
            'events_by_day': {}
        }
        
        # Group events by type
        for event in events:
            event_type = f"{event.entity_type}_{event.action}"
            activity_summary['events_by_type'][event_type] = \
                activity_summary['events_by_type'].get(event_type, 0) + 1
        
        # Group sessions and events by day
        for session in sessions:
            day = session.session_start.date().isoformat()
            activity_summary['sessions_by_day'][day] = \
                activity_summary['sessions_by_day'].get(day, 0) + 1
        
        for event in events:
            day = event.created_at.date().isoformat()
            activity_summary['events_by_day'][day] = \
                activity_summary['events_by_day'].get(day, 0) + 1
        
        return jsonify({
            'user_id': user_id,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat(),
                'days': days
            },
            'sessions': [session.to_dict() for session in sessions],
            'events': [event.to_dict() for event in events],
            'summary': activity_summary
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch user activity: {str(e)}'}), 500

# System Statistics Endpoints
@admin_bp.route('/stats/overview', methods=['GET'])
@admin_required
def get_system_overview():
    """Get system overview statistics"""
    try:
        # Basic counts
        total_users = User.query.count()
        admin_users = User.query.filter_by(role='admin').count()
        
        total_goals = Goal.query.count()
        completed_goals = Goal.query.filter_by(status='completed').count()
        active_goals = Goal.query.filter(Goal.status.in_(['created', 'started', 'working'])).count()
        
        total_subgoals = Subgoal.query.count()
        completed_subgoals = Subgoal.query.filter_by(status='achieved').count()
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        new_users_week = User.query.filter(User.created_at >= week_ago).count()
        new_goals_week = Goal.query.filter(Goal.created_at >= week_ago).count()
        
        # Active sessions
        active_sessions = UserSession.query.filter_by(is_active=True).count()
        
        # Recent logins (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(days=1)
        recent_logins = User.query.filter(User.last_login_at >= day_ago).count()
        
        # Database size (approximate)
        total_events = Event.query.count()
        total_sessions = UserSession.query.count()
        
        return jsonify({
            'users': {
                'total': total_users,
                'admins': admin_users,
                'regular': total_users - admin_users,
                'new_this_week': new_users_week,
                'recent_logins_24h': recent_logins,
                'active_sessions': active_sessions
            },
            'goals': {
                'total': total_goals,
                'completed': completed_goals,
                'active': active_goals,
                'archived': total_goals - completed_goals - active_goals,
                'new_this_week': new_goals_week,
                'completion_rate': round((completed_goals / total_goals * 100), 2) if total_goals > 0 else 0
            },
            'subgoals': {
                'total': total_subgoals,
                'completed': completed_subgoals,
                'pending': total_subgoals - completed_subgoals,
                'completion_rate': round((completed_subgoals / total_subgoals * 100), 2) if total_subgoals > 0 else 0
            },
            'activity': {
                'total_events': total_events,
                'total_sessions': total_sessions,
                'events_per_user': round(total_events / total_users, 2) if total_users > 0 else 0
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch system overview: {str(e)}'}), 500

@admin_bp.route('/stats/activity', methods=['GET'])
@admin_required
def get_system_activity():
    """Get recent activity across all users"""
    try:
        # Get parameters
        limit = min(request.args.get('limit', 100, type=int), 500)  # Max 500
        days = request.args.get('days', 7, type=int)
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get recent events across all users
        recent_events = Event.query.filter(
            Event.created_at >= start_date
        ).order_by(desc(Event.created_at)).limit(limit).all()
        
        # Get recent sessions
        recent_sessions = UserSession.query.filter(
            UserSession.session_start >= start_date
        ).order_by(desc(UserSession.session_start)).limit(limit).all()
        
        # Activity statistics by day
        activity_by_day = {}
        event_types = {}
        
        for event in recent_events:
            day = event.created_at.date().isoformat()
            event_type = f"{event.entity_type}_{event.action}"
            
            if day not in activity_by_day:
                activity_by_day[day] = {'events': 0, 'sessions': 0}
            activity_by_day[day]['events'] += 1
            
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        for session in recent_sessions:
            day = session.session_start.date().isoformat()
            if day not in activity_by_day:
                activity_by_day[day] = {'events': 0, 'sessions': 0}
            activity_by_day[day]['sessions'] += 1
        
        return jsonify({
            'recent_events': [event.to_dict() for event in recent_events],
            'recent_sessions': [session.to_dict() for session in recent_sessions],
            'activity_by_day': activity_by_day,
            'event_types': event_types,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat(),
                'days': days
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch system activity: {str(e)}'}), 500

@admin_bp.route('/stats/usage', methods=['GET'])
@admin_required
def get_usage_statistics():
    """Get usage patterns and trends"""
    try:
        # Get parameters
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # User engagement metrics
        total_users = User.query.count()
        active_users = User.query.filter(User.last_login_at >= start_date).count()
        
        # Calculate user activity levels
        very_active_users = db.session.query(func.count(User.id)).filter(
            User.login_count >= 20
        ).scalar() or 0
        
        moderate_users = db.session.query(func.count(User.id)).filter(
            and_(User.login_count >= 5, User.login_count < 20)
        ).scalar() or 0
        
        # Average goals per user
        avg_goals_per_user = db.session.query(
            func.avg(
                db.session.query(func.count(Goal.id))
                .filter(Goal.user_id == User.id)
                .scalar_subquery()
            )
        ).scalar() or 0
        
        # Goal completion trends
        goals_created_period = Goal.query.filter(Goal.created_at >= start_date).count()
        goals_completed_period = Goal.query.filter(
            and_(
                Goal.achieved_date >= start_date,
                Goal.status == 'completed'
            )
        ).count()
        
        # Session duration statistics
        session_durations = db.session.query(
            func.avg(
                (func.julianday(UserSession.session_end) - func.julianday(UserSession.session_start)) * 24 * 60
            ).label('avg_duration')
        ).filter(
            and_(
                UserSession.session_start >= start_date,
                UserSession.session_end.isnot(None)
            )
        ).scalar() or 0
        
        return jsonify({
            'user_engagement': {
                'total_users': total_users,
                'active_users': active_users,
                'activity_rate': round((active_users / total_users * 100), 2) if total_users > 0 else 0,
                'very_active_users': very_active_users,
                'moderate_users': moderate_users,
                'low_activity_users': total_users - very_active_users - moderate_users
            },
            'goal_metrics': {
                'avg_goals_per_user': round(avg_goals_per_user, 2),
                'goals_created_period': goals_created_period,
                'goals_completed_period': goals_completed_period,
                'completion_efficiency': round(
                    (goals_completed_period / goals_created_period * 100), 2
                ) if goals_created_period > 0 else 0
            },
            'session_metrics': {
                'avg_session_duration_minutes': round(session_durations, 2),
                'total_sessions_period': UserSession.query.filter(
                    UserSession.session_start >= start_date
                ).count()
            },
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat(),
                'days': days
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch usage statistics: {str(e)}'}), 500

# Backup and Restore Endpoints
@admin_bp.route('/backup/create', methods=['POST'])
@admin_required
def create_backup():
    """Create a system backup"""
    try:
        data = request.get_json() or {}
        backup_name = data.get('backup_name')
        backup_type = data.get('backup_type', 'manual')
        
        # Generate backup name if not provided
        if not backup_name:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_name = f"letsgoal_backup_{timestamp}"
        
        # Import backup service functions
        from admin_services import create_database_backup
        
        # Create the backup
        backup_result = create_database_backup(
            backup_name=backup_name,
            backup_type=backup_type,
            created_by_user_id=current_user.id
        )
        
        if backup_result['success']:
            return jsonify({
                'message': 'Backup created successfully',
                'backup': backup_result['backup']
            }), 201
        else:
            return jsonify({
                'error': backup_result['error']
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to create backup: {str(e)}'}), 500

@admin_bp.route('/backup/list', methods=['GET'])
@admin_required
def list_backups():
    """List all available backups"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Get backups with pagination
        backups_pagination = SystemBackup.query.order_by(
            desc(SystemBackup.created_at)
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        # Add file existence check
        backups_with_status = []
        for backup in backups_pagination.items:
            backup_data = backup.to_dict()
            
            # Check if backup file still exists
            import os
            backup_data['file_exists'] = os.path.exists(backup.file_path)
            backup_data['age_days'] = backup.get_backup_age_days()
            
            backups_with_status.append(backup_data)
        
        return jsonify({
            'backups': backups_with_status,
            'pagination': {
                'page': backups_pagination.page,
                'pages': backups_pagination.pages,
                'per_page': backups_pagination.per_page,
                'total': backups_pagination.total,
                'has_next': backups_pagination.has_next,
                'has_prev': backups_pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to list backups: {str(e)}'}), 500

@admin_bp.route('/backup/<int:backup_id>/restore', methods=['POST'])
@admin_required
def restore_backup(backup_id):
    """Restore from a specific backup"""
    try:
        backup = SystemBackup.query.get_or_404(backup_id)
        
        # Verify backup file exists
        import os
        if not os.path.exists(backup.file_path):
            return jsonify({
                'error': 'Backup file not found on disk'
            }), 404
        
        # Import restore service function
        from admin_services import restore_database_backup
        
        # Perform the restore
        restore_result = restore_database_backup(
            backup_id=backup_id,
            restored_by_user_id=current_user.id
        )
        
        if restore_result['success']:
            return jsonify({
                'message': 'Database restored successfully',
                'restore_info': restore_result['info']
            }), 200
        else:
            return jsonify({
                'error': restore_result['error']
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to restore backup: {str(e)}'}), 500

@admin_bp.route('/backup/<int:backup_id>/download', methods=['GET'])
@admin_required
def download_backup(backup_id):
    """Download a backup file"""
    try:
        backup = SystemBackup.query.get_or_404(backup_id)
        
        # Verify backup file exists
        import os
        if not os.path.exists(backup.file_path):
            return jsonify({
                'error': 'Backup file not found on disk'
            }), 404
        
        from flask import send_file
        return send_file(
            backup.file_path,
            as_attachment=True,
            download_name=f"{backup.backup_name}.db"
        )
        
    except Exception as e:
        return jsonify({'error': f'Failed to download backup: {str(e)}'}), 500

@admin_bp.route('/backup/<int:backup_id>', methods=['DELETE'])
@admin_required
def delete_backup(backup_id):
    """Delete a backup"""
    try:
        backup = SystemBackup.query.get_or_404(backup_id)
        
        # Store file path before deleting the record
        file_path = backup.file_path
        backup_name = backup.backup_name
        
        # Delete database record first to avoid readonly issues
        try:
            db.session.delete(backup)
            db.session.commit()
        except Exception as db_error:
            db.session.rollback()
            # Try to close all connections and retry
            try:
                db.session.close()
                db.engine.dispose()
                
                # Retry the delete operation
                backup = SystemBackup.query.get(backup_id)
                if backup:
                    db.session.delete(backup)
                    db.session.commit()
                else:
                    return jsonify({'error': 'Backup record not found'}), 404
                    
            except Exception as retry_error:
                db.session.rollback()
                return jsonify({
                    'error': f'Failed to delete backup record: {str(retry_error)}'
                }), 500
        
        # Delete file from disk after database record is removed
        import os
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                # File deletion failed, but database record is already removed
                # This is not a critical error
                return jsonify({
                    'message': f'Backup record deleted, but file removal failed: {str(e)}',
                    'warning': 'Manual file cleanup may be required'
                }), 200
        
        return jsonify({
            'message': f'Backup "{backup_name}" deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete backup: {str(e)}'}), 500

@admin_bp.route('/backup/cleanup', methods=['POST'])
@admin_required
def cleanup_old_backups():
    """Clean up old backup files"""
    try:
        data = request.get_json() or {}
        retention_days = data.get('retention_days', 30)
        
        # Import cleanup service function
        from admin_services import cleanup_old_backup_files
        
        cleanup_result = cleanup_old_backup_files(retention_days)
        
        return jsonify({
            'message': f'Cleanup completed',
            'removed_records': cleanup_result['removed_records'],
            'removed_files': cleanup_result['removed_files'],
            'freed_space_mb': cleanup_result['freed_space_mb'],
            'orphaned_cleaned': cleanup_result.get('orphaned_cleaned', 0)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to cleanup backups: {str(e)}'}), 500

@admin_bp.route('/backup/cleanup-orphaned', methods=['POST'])
@admin_required
def cleanup_orphaned_records():
    """Clean up orphaned backup database records"""
    try:
        # Import cleanup service function
        from admin_services import cleanup_orphaned_backup_records
        
        cleanup_result = cleanup_orphaned_backup_records()
        
        if cleanup_result['success']:
            return jsonify({
                'message': f'Orphaned cleanup completed',
                'removed_count': cleanup_result['removed_count'],
                'total_checked': cleanup_result['total_checked']
            }), 200
        else:
            return jsonify({
                'error': cleanup_result['error']
            }), 500
        
    except Exception as e:
        return jsonify({'error': f'Failed to cleanup orphaned records: {str(e)}'}), 500

# Admin Settings Endpoints
@admin_bp.route('/settings', methods=['GET'])
@admin_required
def get_admin_settings():
    """Get all admin settings"""
    try:
        settings = AdminSettings.query.order_by(AdminSettings.setting_key).all()
        return jsonify({
            'settings': [setting.to_dict() for setting in settings]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch settings: {str(e)}'}), 500

@admin_bp.route('/settings', methods=['PUT'])
@admin_required
def update_admin_settings():
    """Update admin settings"""
    try:
        data = request.get_json()
        
        if not data or 'settings' not in data:
            return jsonify({'error': 'Settings data required'}), 400
        
        updated_settings = []
        
        for setting_data in data['settings']:
            setting_key = setting_data.get('setting_key')
            setting_value = setting_data.get('setting_value')
            
            if not setting_key:
                continue
            
            # Update or create setting
            setting = AdminSettings.set_setting(
                key=setting_key,
                value=setting_value,
                setting_type=setting_data.get('setting_type', 'string'),
                description=setting_data.get('description')
            )
            updated_settings.append(setting.to_dict())
        
        db.session.commit()
        
        return jsonify({
            'message': f'Updated {len(updated_settings)} settings',
            'settings': updated_settings
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update settings: {str(e)}'}), 500

@admin_bp.route('/settings/<setting_key>', methods=['GET'])
@admin_required
def get_admin_setting(setting_key):
    """Get a specific admin setting"""
    try:
        setting = AdminSettings.query.filter_by(setting_key=setting_key).first()
        
        if not setting:
            return jsonify({'error': 'Setting not found'}), 404
        
        return jsonify({
            'setting': setting.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch setting: {str(e)}'}), 500

@admin_bp.route('/settings/<setting_key>', methods=['PUT'])
@admin_required
def update_admin_setting(setting_key):
    """Update a specific admin setting"""
    try:
        data = request.get_json()
        
        if not data or 'setting_value' not in data:
            return jsonify({'error': 'Setting value required'}), 400
        
        setting = AdminSettings.set_setting(
            key=setting_key,
            value=data['setting_value'],
            setting_type=data.get('setting_type', 'string'),
            description=data.get('description')
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Setting updated successfully',
            'setting': setting.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update setting: {str(e)}'}), 500

# Data Clearing Endpoints
@admin_bp.route('/data/clear/user-data', methods=['POST'])
@admin_required
def clear_user_data():
    """Clear user data and goals, optionally preserving admin users"""
    try:
        data = request.get_json() or {}
        preserve_admin = data.get('preserve_admin', True)
        
        # Require explicit confirmation
        confirmation = data.get('confirmation')
        if confirmation != 'CLEAR_USER_DATA':
            return jsonify({
                'error': 'Invalid confirmation. Must provide "CLEAR_USER_DATA"'
            }), 400
        
        # Import clearing service function
        from admin_services import clear_user_data_and_goals
        
        # Perform the clear operation
        clear_result = clear_user_data_and_goals(preserve_admin=preserve_admin)
        
        if clear_result['success']:
            return jsonify({
                'message': 'User data cleared successfully',
                'statistics': clear_result['statistics'],
                'backup_created': clear_result['backup_created'],
                'preserve_admin': clear_result['preserve_admin']
            }), 200
        else:
            return jsonify({
                'error': clear_result['error']
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to clear user data: {str(e)}'}), 500

@admin_bp.route('/data/clear/goals-only', methods=['POST'])
@admin_required
def clear_goals_only():
    """Clear only goals and related data, keeping user accounts"""
    try:
        data = request.get_json() or {}
        preserve_admin_goals = data.get('preserve_admin_goals', True)
        
        # Require explicit confirmation
        confirmation = data.get('confirmation')
        if confirmation != 'CLEAR_GOALS_ONLY':
            return jsonify({
                'error': 'Invalid confirmation. Must provide "CLEAR_GOALS_ONLY"'
            }), 400
        
        # Import clearing service function
        from admin_services import clear_goals_only as clear_goals_service
        
        # Perform the clear operation
        clear_result = clear_goals_service(preserve_admin_goals=preserve_admin_goals)
        
        if clear_result['success']:
            return jsonify({
                'message': 'Goals cleared successfully',
                'statistics': clear_result['statistics'],
                'backup_created': clear_result['backup_created'],
                'preserve_admin_goals': clear_result['preserve_admin_goals']
            }), 200
        else:
            return jsonify({
                'error': clear_result['error']
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to clear goals: {str(e)}'}), 500

@admin_bp.route('/data/clear/nuclear', methods=['POST'])
@admin_required
def nuclear_clear():
    """Nuclear option: Clear everything except admin users and system settings"""
    try:
        data = request.get_json() or {}
        
        # Require explicit confirmation with nuclear phrase
        confirmation = data.get('confirmation')
        if confirmation != 'NUCLEAR_CLEAR_EVERYTHING':
            return jsonify({
                'error': 'Invalid confirmation. Must provide "NUCLEAR_CLEAR_EVERYTHING"'
            }), 400
        
        # Import clearing service function
        from admin_services import clear_everything_except_admin
        
        # Perform the nuclear clear operation
        clear_result = clear_everything_except_admin()
        
        if clear_result['success']:
            return jsonify({
                'message': 'Nuclear clear completed successfully',
                'statistics': clear_result['statistics'],
                'backup_created': clear_result['backup_created'],
                'preserved_admin_count': clear_result['preserved_admin_count']
            }), 200
        else:
            return jsonify({
                'error': clear_result['error']
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to perform nuclear clear: {str(e)}'}), 500

@admin_bp.route('/data/clear/preview', methods=['POST'])
@admin_required
def preview_data_clear():
    """Preview what would be deleted in a clear operation without actually deleting"""
    try:
        data = request.get_json() or {}
        clear_type = data.get('clear_type', 'user-data')
        preserve_admin = data.get('preserve_admin', True)
        preserve_admin_goals = data.get('preserve_admin_goals', True)
        
        # Get counts without deleting
        from models import User, Goal, Subgoal, Tag, Event, UserSession, ProgressEntry
        
        preview = {
            'clear_type': clear_type,
            'would_delete': {},
            'would_preserve': {}
        }
        
        admin_user_ids = [user.id for user in User.query.filter_by(role='admin').all()]
        
        if clear_type == 'user-data':
            if preserve_admin:
                # Count non-admin data
                non_admin_users = User.query.filter(~User.id.in_(admin_user_ids)).all()
                preview['would_delete'] = {
                    'users': len(non_admin_users),
                    'goals': Goal.query.filter(
                        ~Goal.user_id.in_(admin_user_ids) & ~Goal.owner_id.in_(admin_user_ids)
                    ).count(),
                    'tags': Tag.query.filter(~Tag.user_id.in_(admin_user_ids)).count(),
                    'events': Event.query.filter(~Event.user_id.in_(admin_user_ids)).count(),
                    'sessions': UserSession.query.filter(~UserSession.user_id.in_(admin_user_ids)).count(),
                    'progress_entries': ProgressEntry.query.join(Goal).filter(~Goal.user_id.in_(admin_user_ids)).count()
                }
                preview['would_preserve'] = {
                    'admin_users': len(admin_user_ids),
                    'admin_goals': Goal.query.filter(
                        (Goal.user_id.in_(admin_user_ids)) | (Goal.owner_id.in_(admin_user_ids))
                    ).count()
                }
            else:
                preview['would_delete'] = {
                    'users': User.query.count(),
                    'goals': Goal.query.count(),
                    'subgoals': Subgoal.query.count(),
                    'tags': Tag.query.count(),
                    'events': Event.query.count(),
                    'sessions': UserSession.query.count(),
                    'progress_entries': ProgressEntry.query.count()
                }
                preview['would_preserve'] = {'system_settings': 'preserved'}
                
        elif clear_type == 'goals-only':
            if preserve_admin_goals:
                preview['would_delete'] = {
                    'goals': Goal.query.filter(
                        ~Goal.user_id.in_(admin_user_ids) & ~Goal.owner_id.in_(admin_user_ids)
                    ).count(),
                    'tags': Tag.query.filter(~Tag.user_id.in_(admin_user_ids)).count()
                }
                preview['would_preserve'] = {
                    'users': User.query.count(),
                    'admin_goals': Goal.query.filter(
                        (Goal.user_id.in_(admin_user_ids)) | (Goal.owner_id.in_(admin_user_ids))
                    ).count()
                }
            else:
                preview['would_delete'] = {
                    'goals': Goal.query.count(),
                    'subgoals': Subgoal.query.count(),
                    'tags': Tag.query.count(),
                    'progress_entries': ProgressEntry.query.count()
                }
                preview['would_preserve'] = {
                    'users': User.query.count(),
                    'user_accounts': 'all preserved'
                }
                
        elif clear_type == 'nuclear':
            non_admin_users = User.query.filter(~User.id.in_(admin_user_ids)).all()
            preview['would_delete'] = {
                'users': len(non_admin_users),
                'goals': Goal.query.count(),  # ALL goals including admin
                'subgoals': Subgoal.query.count(),
                'tags': Tag.query.count(),
                'events': Event.query.count(),
                'sessions': UserSession.query.count(),
                'progress_entries': ProgressEntry.query.count()
            }
            preview['would_preserve'] = {
                'admin_users': len(admin_user_ids),
                'system_settings': 'preserved',
                'backups': 'preserved'
            }
        
        return jsonify(preview), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to preview clear operation: {str(e)}'}), 500

# Subscription Plan Management Endpoints
@admin_bp.route('/plans', methods=['GET'])
@admin_required
def get_all_plans():
    """Get all subscription plans"""
    try:
        plans = Plan.query.order_by(Plan.price.asc()).all()
        return jsonify({
            'plans': [plan.to_dict() for plan in plans]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch plans: {str(e)}'}), 500

@admin_bp.route('/plans', methods=['POST'])
@admin_required
def create_plan():
    """Create a new subscription plan"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        # Validate required fields
        required_fields = ['name', 'price', 'interval']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create plan via Stripe service
        result = stripe_service.create_plan(
            name=data['name'],
            price=float(data['price']),
            currency=data.get('currency', 'USD'),
            interval=data['interval'],
            features=data.get('features', {})
        )
        
        if result['success']:
            return jsonify({
                'message': 'Plan created successfully',
                'plan': result['plan'].to_dict()
            }), 201
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to create plan: {str(e)}'}), 500

@admin_bp.route('/plans/<int:plan_id>', methods=['PUT'])
@admin_required
def update_plan(plan_id):
    """Update a subscription plan"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        # Update plan via Stripe service
        result = stripe_service.update_plan(
            plan_id=plan_id,
            name=data.get('name'),
            features=data.get('features'),
            active=data.get('active')
        )
        
        if result['success']:
            return jsonify({
                'message': 'Plan updated successfully',
                'plan': result['plan'].to_dict()
            }), 200
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to update plan: {str(e)}'}), 500

@admin_bp.route('/plans/<int:plan_id>', methods=['DELETE'])
@admin_required
def delete_plan(plan_id):
    """Archive a subscription plan (mark as inactive)"""
    try:
        plan = Plan.query.get_or_404(plan_id)
        
        # Check if plan has active subscriptions
        active_subscriptions = Subscription.query.filter(
            and_(
                Subscription.plan_id == plan_id,
                Subscription.status.in_(['active', 'trialing'])
            )
        ).count()
        
        if active_subscriptions > 0:
            return jsonify({
                'error': f'Cannot archive plan with {active_subscriptions} active subscriptions'
            }), 400
        
        # Mark as inactive instead of deleting
        plan.active = False
        db.session.commit()
        
        return jsonify({
            'message': f'Plan "{plan.name}" archived successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to archive plan: {str(e)}'}), 500

# Subscription Management Endpoints
@admin_bp.route('/subscriptions', methods=['GET'])
@admin_required
def get_all_subscriptions():
    """Get all subscriptions with filtering and pagination"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        status_filter = request.args.get('status')
        plan_filter = request.args.get('plan_id', type=int)
        user_search = request.args.get('user_search')
        
        # Build query
        query = Subscription.query.join(User).join(Plan)
        
        if status_filter:
            query = query.filter(Subscription.status == status_filter)
        
        if plan_filter:
            query = query.filter(Subscription.plan_id == plan_filter)
        
        if user_search:
            query = query.filter(
                (User.username.contains(user_search)) |
                (User.email.contains(user_search))
            )
        
        # Paginate subscriptions
        subscriptions_pagination = query.order_by(
            Subscription.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        # Get subscription statistics
        total_subscriptions = Subscription.query.count()
        active_subscriptions = Subscription.query.filter(
            Subscription.status.in_(['active', 'trialing'])
        ).count()
        
        subscription_stats = {
            'total': total_subscriptions,
            'active': active_subscriptions,
            'inactive': total_subscriptions - active_subscriptions,
            'by_status': {}
        }
        
        # Count by status
        status_counts = db.session.query(
            Subscription.status,
            func.count(Subscription.id)
        ).group_by(Subscription.status).all()
        
        for status, count in status_counts:
            subscription_stats['by_status'][status] = count
        
        return jsonify({
            'subscriptions': [sub.to_dict() for sub in subscriptions_pagination.items],
            'pagination': {
                'page': subscriptions_pagination.page,
                'pages': subscriptions_pagination.pages,
                'per_page': subscriptions_pagination.per_page,
                'total': subscriptions_pagination.total,
                'has_next': subscriptions_pagination.has_next,
                'has_prev': subscriptions_pagination.has_prev
            },
            'statistics': subscription_stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch subscriptions: {str(e)}'}), 500

@admin_bp.route('/subscriptions', methods=['POST'])
@admin_required
def create_subscription():
    """Create a new subscription for a user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        # Validate required fields
        required_fields = ['user_id', 'plan_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if user already has an active subscription
        existing_subscription = Subscription.query.filter(
            and_(
                Subscription.user_id == data['user_id'],
                Subscription.status.in_(['active', 'trialing'])
            )
        ).first()
        
        if existing_subscription:
            return jsonify({
                'error': 'User already has an active subscription'
            }), 400
        
        # Create subscription via Stripe service
        result = stripe_service.create_subscription(
            user_id=data['user_id'],
            plan_id=data['plan_id'],
            payment_method_id=data.get('payment_method_id'),
            trial_days=data.get('trial_days')
        )
        
        if result['success']:
            return jsonify({
                'message': 'Subscription created successfully',
                'subscription': result['local_subscription'].to_dict()
            }), 201
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to create subscription: {str(e)}'}), 500

@admin_bp.route('/subscriptions/<int:subscription_id>', methods=['GET'])
@admin_required
def get_subscription_details(subscription_id):
    """Get detailed subscription information"""
    try:
        subscription = Subscription.query.get_or_404(subscription_id)
        
        # Get subscription history
        history = SubscriptionHistory.query.filter_by(
            subscription_id=subscription_id
        ).order_by(SubscriptionHistory.created_at.desc()).all()
        
        # Get invoices
        invoices = Invoice.query.filter_by(
            subscription_id=subscription_id
        ).order_by(Invoice.created_at.desc()).all()
        
        return jsonify({
            'subscription': subscription.to_dict(),
            'history': [h.to_dict() for h in history],
            'invoices': [i.to_dict() for i in invoices]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch subscription details: {str(e)}'}), 500

@admin_bp.route('/subscriptions/<int:subscription_id>', methods=['PUT'])
@admin_required
def update_subscription(subscription_id):
    """Update a subscription (change plan)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        # Update subscription via Stripe service
        result = stripe_service.update_subscription(
            subscription_id=subscription_id,
            new_plan_id=data.get('plan_id'),
            prorate=data.get('prorate', True)
        )
        
        if result['success']:
            return jsonify({
                'message': 'Subscription updated successfully',
                'subscription': result['local_subscription'].to_dict()
            }), 200
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to update subscription: {str(e)}'}), 500

@admin_bp.route('/subscriptions/<int:subscription_id>/cancel', methods=['POST'])
@admin_required
def cancel_subscription(subscription_id):
    """Cancel a subscription"""
    try:
        data = request.get_json() or {}
        
        # Cancel subscription via Stripe service
        result = stripe_service.cancel_subscription(
            subscription_id=subscription_id,
            at_period_end=data.get('at_period_end', True),
            reason=data.get('reason', 'Canceled by admin')
        )
        
        if result['success']:
            return jsonify({
                'message': 'Subscription canceled successfully',
                'subscription': result['local_subscription'].to_dict()
            }), 200
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to cancel subscription: {str(e)}'}), 500

@admin_bp.route('/subscriptions/<int:subscription_id>/reactivate', methods=['POST'])
@admin_required
def reactivate_subscription(subscription_id):
    """Reactivate a canceled subscription"""
    try:
        data = request.get_json()
        
        if not data or not data.get('plan_id'):
            return jsonify({'error': 'Plan ID is required for reactivation'}), 400
        
        # Reactivate subscription via Stripe service
        result = stripe_service.reactivate_subscription(
            subscription_id=subscription_id,
            plan_id=data['plan_id']
        )
        
        if result['success']:
            return jsonify({
                'message': 'Subscription reactivated successfully',
                'subscription': result['local_subscription'].to_dict()
            }), 200
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to reactivate subscription: {str(e)}'}), 500

# Invoice Management Endpoints
@admin_bp.route('/invoices', methods=['GET'])
@admin_required
def get_all_invoices():
    """Get all invoices with filtering and pagination"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        status_filter = request.args.get('status')
        user_search = request.args.get('user_search')
        
        # Build query
        query = Invoice.query.join(Subscription).join(User)
        
        if status_filter:
            query = query.filter(Invoice.status == status_filter)
        
        if user_search:
            query = query.filter(
                (User.username.contains(user_search)) |
                (User.email.contains(user_search))
            )
        
        # Paginate invoices
        invoices_pagination = query.order_by(
            Invoice.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        # Get invoice statistics
        total_invoices = Invoice.query.count()
        paid_invoices = Invoice.query.filter_by(paid=True).count()
        overdue_invoices = Invoice.query.filter(
            and_(
                Invoice.paid == False,
                Invoice.due_date < datetime.utcnow()
            )
        ).count()
        
        # Calculate revenue
        total_revenue = db.session.query(
            func.sum(Invoice.amount_paid)
        ).scalar() or 0
        
        invoice_stats = {
            'total': total_invoices,
            'paid': paid_invoices,
            'unpaid': total_invoices - paid_invoices,
            'overdue': overdue_invoices,
            'total_revenue': float(total_revenue)
        }
        
        return jsonify({
            'invoices': [invoice.to_dict() for invoice in invoices_pagination.items],
            'pagination': {
                'page': invoices_pagination.page,
                'pages': invoices_pagination.pages,
                'per_page': invoices_pagination.per_page,
                'total': invoices_pagination.total,
                'has_next': invoices_pagination.has_next,
                'has_prev': invoices_pagination.has_prev
            },
            'statistics': invoice_stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch invoices: {str(e)}'}), 500

@admin_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@admin_required
def get_invoice_details(invoice_id):
    """Get detailed invoice information"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        return jsonify({
            'invoice': invoice.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch invoice details: {str(e)}'}), 500

# Subscription Statistics Endpoints
@admin_bp.route('/subscriptions/stats/overview', methods=['GET'])
@admin_required
def get_subscription_overview():
    """Get subscription overview statistics"""
    try:
        # Basic subscription counts
        total_subscriptions = Subscription.query.count()
        active_subscriptions = Subscription.query.filter(
            Subscription.status.in_(['active', 'trialing'])
        ).count()
        
        # Revenue calculations
        total_revenue = db.session.query(
            func.sum(Invoice.amount_paid)
        ).scalar() or 0
        
        # Monthly recurring revenue (MRR)
        monthly_subscriptions = Subscription.query.join(Plan).filter(
            and_(
                Subscription.status.in_(['active', 'trialing']),
                Plan.interval == 'month'
            )
        ).all()
        
        mrr = sum(sub.plan.price for sub in monthly_subscriptions)
        
        # Annual recurring revenue (ARR)
        annual_subscriptions = Subscription.query.join(Plan).filter(
            and_(
                Subscription.status.in_(['active', 'trialing']),
                Plan.interval == 'year'
            )
        ).all()
        
        arr = sum(sub.plan.price for sub in annual_subscriptions) * 12
        arr += mrr * 12  # Add annualized MRR
        
        # Churn calculation (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        churned_subscriptions = Subscription.query.filter(
            and_(
                Subscription.status.in_(['canceled', 'unpaid']),
                Subscription.canceled_at >= thirty_days_ago
            )
        ).count()
        
        churn_rate = (churned_subscriptions / max(total_subscriptions, 1)) * 100
        
        # Plan distribution
        plan_distribution = db.session.query(
            Plan.name,
            func.count(Subscription.id)
        ).join(Subscription).filter(
            Subscription.status.in_(['active', 'trialing'])
        ).group_by(Plan.name).all()
        
        return jsonify({
            'subscriptions': {
                'total': total_subscriptions,
                'active': active_subscriptions,
                'inactive': total_subscriptions - active_subscriptions,
                'churn_rate': round(churn_rate, 2)
            },
            'revenue': {
                'total_revenue': float(total_revenue),
                'mrr': float(mrr),
                'arr': float(arr)
            },
            'plan_distribution': {
                plan_name: count for plan_name, count in plan_distribution
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch subscription overview: {str(e)}'}), 500

@admin_bp.route('/subscriptions/stats/revenue', methods=['GET'])
@admin_required
def get_revenue_statistics():
    """Get detailed revenue statistics"""
    try:
        # Get date range parameters
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Revenue by day
        daily_revenue = db.session.query(
            func.date(Invoice.paid_at).label('date'),
            func.sum(Invoice.amount_paid).label('revenue')
        ).filter(
            and_(
                Invoice.paid == True,
                Invoice.paid_at >= start_date
            )
        ).group_by(func.date(Invoice.paid_at)).all()
        
        # Revenue by plan
        revenue_by_plan = db.session.query(
            Plan.name,
            func.sum(Invoice.amount_paid).label('revenue')
        ).select_from(Plan).join(
            Subscription, Plan.id == Subscription.plan_id
        ).join(
            Invoice, Subscription.id == Invoice.subscription_id
        ).filter(
            and_(
                Invoice.paid == True,
                Invoice.paid_at >= start_date
            )
        ).group_by(Plan.name).all()
        
        return jsonify({
            'daily_revenue': [
                {
                    'date': date.isoformat() if date else None,
                    'revenue': float(revenue) if revenue else 0
                }
                for date, revenue in daily_revenue
            ],
            'revenue_by_plan': {
                plan_name: float(revenue) for plan_name, revenue in revenue_by_plan
            },
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat(),
                'days': days
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch revenue statistics: {str(e)}'}), 500

# Stripe Webhook Endpoint
@admin_bp.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    try:
        import os
        
        payload = request.get_data()
        signature = request.headers.get('Stripe-Signature')
        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        
        if not webhook_secret:
            return jsonify({'error': 'Webhook secret not configured'}), 500
        
        # Verify webhook signature
        if not stripe_service.verify_webhook_signature(payload, signature, webhook_secret):
            return jsonify({'error': 'Invalid signature'}), 400
        
        # Parse event
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Handle event
        result = stripe_service.handle_webhook_event(
            event['type'],
            event['data']
        )
        
        if result['success']:
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'error': f'Webhook processing failed: {str(e)}'}), 500

# SMS Management Endpoints
@admin_bp.route('/sms/stats', methods=['GET'])
@admin_required
def get_sms_stats():
    """Get SMS usage statistics"""
    try:
        # Mock data for now - replace with actual SMS service integration
        return jsonify({
            'today': 0,
            'week': 0,
            'month': 0,
            'cost': 0.00,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get SMS stats: {str(e)}'}), 500

@admin_bp.route('/sms/settings', methods=['GET'])
@admin_required
def get_sms_settings():
    """Get SMS provider settings"""
    try:
        # Get SMS settings from admin settings
        provider_setting = AdminSettings.query.filter_by(setting_key='sms_provider').first()
        sid_setting = AdminSettings.query.filter_by(setting_key='sms_account_sid').first()
        number_setting = AdminSettings.query.filter_by(setting_key='sms_from_number').first()
        
        return jsonify({
            'provider': provider_setting.setting_value if provider_setting else 'twilio',
            'account_sid': sid_setting.setting_value if sid_setting else '',
            'from_number': number_setting.setting_value if number_setting else '',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get SMS settings: {str(e)}'}), 500

@admin_bp.route('/sms/settings', methods=['PUT'])
@admin_required
def update_sms_settings():
    """Update SMS provider settings"""
    try:
        data = request.get_json()
        
        # Update or create SMS settings
        settings_map = {
            'sms_provider': data.get('provider', 'twilio'),
            'sms_account_sid': data.get('account_sid', ''),
            'sms_auth_token': data.get('auth_token', ''),
            'sms_from_number': data.get('from_number', '')
        }
        
        for key, value in settings_map.items():
            if value:  # Only update if value is provided
                setting = AdminSettings.query.filter_by(setting_key=key).first()
                if setting:
                    setting.setting_value = value
                    setting.updated_at = datetime.utcnow()
                else:
                    setting = AdminSettings(
                        setting_key=key,
                        setting_value=value
                    )
                    db.session.add(setting)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'SMS settings updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update SMS settings: {str(e)}'}), 500

@admin_bp.route('/sms/templates', methods=['GET'])
@admin_required
def get_sms_templates():
    """Get SMS message templates"""
    try:
        # Get templates from admin settings
        reminder_template = AdminSettings.query.filter_by(setting_key='sms_template_goal_reminder').first()
        completion_template = AdminSettings.query.filter_by(setting_key='sms_template_goal_completion').first()
        
        return jsonify({
            'goal_reminder': reminder_template.setting_value if reminder_template else 'Hi {username}! Don\'t forget to work on your goal: {goal_name}',
            'goal_completion': completion_template.setting_value if completion_template else 'Congratulations {username}! You completed your goal: {goal_name}',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get SMS templates: {str(e)}'}), 500

@admin_bp.route('/sms/templates', methods=['PUT'])
@admin_required
def update_sms_templates():
    """Update SMS message templates"""
    try:
        data = request.get_json()
        
        # Update or create SMS templates
        templates_map = {
            'sms_template_goal_reminder': data.get('goal_reminder', ''),
            'sms_template_goal_completion': data.get('goal_completion', '')
        }
        
        for key, value in templates_map.items():
            if value:  # Only update if value is provided
                template = AdminSettings.query.filter_by(setting_key=key).first()
                if template:
                    template.setting_value = value
                    template.updated_at = datetime.utcnow()
                else:
                    template = AdminSettings(
                        setting_key=key,
                        setting_value=value
                    )
                    db.session.add(template)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'SMS templates updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update SMS templates: {str(e)}'}), 500