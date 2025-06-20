import json
from datetime import datetime
from flask_login import current_user
from models import db, Event

class EventTracker:
    """Service class for tracking and logging all system events"""
    
    @staticmethod
    def log_event(entity_type, entity_id, action, field_name=None, old_value=None, new_value=None, metadata=None):
        """
        Log an event to the events table
        
        Args:
            entity_type (str): Type of entity ('goal', 'subgoal')
            entity_id (int): ID of the entity
            action (str): Action performed ('created', 'updated', 'deleted', 'status_changed', etc.)
            field_name (str, optional): Specific field that changed
            old_value (any, optional): Previous value
            new_value (any, optional): New value
            metadata (dict, optional): Additional context
        """
        try:
            # Get current user ID
            user_id = current_user.id if current_user and current_user.is_authenticated else None
            
            if not user_id:
                print(f"Warning: No authenticated user for event logging: {action} on {entity_type} {entity_id}")
                return None
            
            # Convert complex values to JSON strings
            old_value_str = json.dumps(old_value) if old_value is not None and not isinstance(old_value, str) else old_value
            new_value_str = json.dumps(new_value) if new_value is not None and not isinstance(new_value, str) else new_value
            metadata_str = json.dumps(metadata) if metadata else None
            
            event = Event(
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                field_name=field_name,
                old_value=old_value_str,
                new_value=new_value_str,
                event_metadata=metadata_str
            )
            
            db.session.add(event)
            # Don't commit here - let the calling function handle the transaction
            
            return event
            
        except Exception as e:
            print(f"Error logging event: {e}")
            return None
    
    @staticmethod
    def log_goal_created(goal):
        """Log goal creation event"""
        return EventTracker.log_event(
            entity_type='goal',
            entity_id=goal.id,
            action='created',
            metadata={
                'title': goal.title,
                'status': goal.status,
                'target_date': goal.target_date.isoformat() if goal.target_date else None
            }
        )
    
    @staticmethod
    def log_goal_updated(goal, changes):
        """
        Log goal update event
        
        Args:
            goal: Goal object
            changes (dict): Dictionary of field_name -> {'old': old_value, 'new': new_value}
        """
        events = []
        for field_name, change in changes.items():
            event = EventTracker.log_event(
                entity_type='goal',
                entity_id=goal.id,
                action='updated',
                field_name=field_name,
                old_value=change.get('old'),
                new_value=change.get('new')
            )
            if event:
                events.append(event)
        return events
    
    @staticmethod
    def log_goal_status_changed(goal, old_status, new_status):
        """Log goal status change event"""
        return EventTracker.log_event(
            entity_type='goal',
            entity_id=goal.id,
            action='status_changed',
            field_name='status',
            old_value=old_status,
            new_value=new_status,
            metadata={
                'title': goal.title,
                'progress': goal.calculate_progress()
            }
        )
    
    @staticmethod
    def log_goal_completed(goal):
        """Log goal completion event"""
        return EventTracker.log_event(
            entity_type='goal',
            entity_id=goal.id,
            action='completed',
            metadata={
                'title': goal.title,
                'achieved_date': goal.achieved_date.isoformat() if goal.achieved_date else None,
                'total_subgoals': len(goal.subgoals)
            }
        )
    
    @staticmethod
    def log_goal_deleted(goal_id, goal_title):
        """Log goal deletion event"""
        return EventTracker.log_event(
            entity_type='goal',
            entity_id=goal_id,
            action='deleted',
            metadata={
                'title': goal_title
            }
        )
    
    @staticmethod
    def log_subgoal_created(subgoal):
        """Log subgoal creation event"""
        return EventTracker.log_event(
            entity_type='subgoal',
            entity_id=subgoal.id,
            action='created',
            metadata={
                'title': subgoal.title,
                'goal_id': subgoal.goal_id,
                'goal_title': subgoal.goal.title if subgoal.goal else None,
                'status': subgoal.status
            }
        )
    
    @staticmethod
    def log_subgoal_updated(subgoal, changes):
        """
        Log subgoal update event
        
        Args:
            subgoal: Subgoal object
            changes (dict): Dictionary of field_name -> {'old': old_value, 'new': new_value}
        """
        events = []
        for field_name, change in changes.items():
            event = EventTracker.log_event(
                entity_type='subgoal',
                entity_id=subgoal.id,
                action='updated',
                field_name=field_name,
                old_value=change.get('old'),
                new_value=change.get('new'),
                metadata={
                    'title': subgoal.title,
                    'goal_id': subgoal.goal_id,
                    'goal_title': subgoal.goal.title if subgoal.goal else None
                }
            )
            if event:
                events.append(event)
        return events
    
    @staticmethod
    def log_subgoal_status_changed(subgoal, old_status, new_status):
        """Log subgoal status change event"""
        return EventTracker.log_event(
            entity_type='subgoal',
            entity_id=subgoal.id,
            action='status_changed',
            field_name='status',
            old_value=old_status,
            new_value=new_status,
            metadata={
                'title': subgoal.title,
                'goal_id': subgoal.goal_id,
                'goal_title': subgoal.goal.title if subgoal.goal else None,
                'goal_progress': subgoal.goal.calculate_progress() if subgoal.goal else None
            }
        )
    
    @staticmethod
    def log_subgoal_completed(subgoal):
        """Log subgoal completion event"""
        return EventTracker.log_event(
            entity_type='subgoal',
            entity_id=subgoal.id,
            action='completed',
            metadata={
                'title': subgoal.title,
                'goal_id': subgoal.goal_id,
                'goal_title': subgoal.goal.title if subgoal.goal else None,
                'achieved_date': subgoal.achieved_date.isoformat() if subgoal.achieved_date else None,
                'goal_progress': subgoal.goal.calculate_progress() if subgoal.goal else None
            }
        )
    
    @staticmethod
    def log_subgoal_deleted(subgoal_id, subgoal_title, goal_id, goal_title):
        """Log subgoal deletion event"""
        return EventTracker.log_event(
            entity_type='subgoal',
            entity_id=subgoal_id,
            action='deleted',
            metadata={
                'title': subgoal_title,
                'goal_id': goal_id,
                'goal_title': goal_title
            }
        )
    
    @staticmethod
    def get_recent_events(user_id, limit=50):
        """Get recent events for a user"""
        return Event.query.filter_by(user_id=user_id)\
            .order_by(Event.created_at.desc())\
            .limit(limit)\
            .all()
    
    @staticmethod
    def get_goal_events(goal_id, user_id):
        """Get all events for a specific goal"""
        return Event.query.filter_by(user_id=user_id)\
            .filter(
                ((Event.entity_type == 'goal') & (Event.entity_id == goal_id)) |
                ((Event.entity_type == 'subgoal') & (Event.event_metadata.like(f'%"goal_id": {goal_id}%')))
            )\
            .order_by(Event.created_at.desc())\
            .all()
    
    @staticmethod
    def log_goal_shared(goal, shared_with_user):
        """Log goal sharing event"""
        return EventTracker.log_event(
            entity_type='goal',
            entity_id=goal.id,
            action='shared',
            metadata={
                'title': goal.title,
                'shared_with_user_id': shared_with_user.id,
                'shared_with_username': shared_with_user.username,
                'shared_with_email': shared_with_user.email
            }
        )
    
    @staticmethod
    def log_goal_unshared(goal, unshared_user):
        """Log goal unsharing event"""
        return EventTracker.log_event(
            entity_type='goal',
            entity_id=goal.id,
            action='unshared',
            metadata={
                'title': goal.title,
                'unshared_user_id': unshared_user.id,
                'unshared_username': unshared_user.username,
                'unshared_email': unshared_user.email
            }
        )