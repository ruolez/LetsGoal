from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association table for many-to-many relationship between goals and tags
goal_tags = db.Table('goal_tags',
    db.Column('goal_id', db.Integer, db.ForeignKey('goals.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class GoalShare(db.Model):
    __tablename__ = 'goal_shares'
    
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=False)
    shared_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shared_with_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    permission_level = db.Column(db.String(20), default='edit', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    goal = db.relationship('Goal', backref='shares')
    shared_by = db.relationship('User', foreign_keys=[shared_by_user_id], backref='shared_goals')
    shared_with = db.relationship('User', foreign_keys=[shared_with_user_id], backref='received_shares')
    
    # Ensure unique sharing relationships
    __table_args__ = (db.UniqueConstraint('goal_id', 'shared_with_user_id', name='_goal_share_unique'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'shared_by_user_id': self.shared_by_user_id,
            'shared_with_user_id': self.shared_with_user_id,
            'permission_level': self.permission_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'shared_by': self.shared_by.to_dict() if self.shared_by else None,
            'shared_with': self.shared_with.to_dict() if self.shared_with else None
        }

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # SMS-related fields
    phone_number = db.Column(db.String(20))
    phone_verified = db.Column(db.Boolean, default=False, nullable=False)
    sms_enabled = db.Column(db.Boolean, default=False, nullable=False)
    sms_preferences = db.Column(db.Text)  # JSON string for SMS preferences
    verification_code = db.Column(db.String(10))
    verification_expires_at = db.Column(db.DateTime)
    
    # Relationships
    goals = db.relationship('Goal', foreign_keys='Goal.user_id', backref='user', lazy=True, cascade='all, delete-orphan')
    tags = db.relationship('Tag', backref='user', lazy=True, cascade='all, delete-orphan')
    sms_reminders = db.relationship('SmsReminder', backref='user', lazy=True, cascade='all, delete-orphan')
    sms_logs = db.relationship('SmsDeliveryLog', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_sms_preferences(self):
        """Get SMS preferences as a dictionary"""
        if self.sms_preferences:
            try:
                return json.loads(self.sms_preferences)
            except json.JSONDecodeError:
                return {}
        return {
            'deadline_reminders': True,
            'daily_motivation': False,
            'progress_updates': True,
            'weekly_summary': False,
            'reminder_time': '09:00',
            'timezone': 'UTC'
        }
    
    def set_sms_preferences(self, preferences_dict):
        """Set SMS preferences from a dictionary"""
        self.sms_preferences = json.dumps(preferences_dict)
    
    def can_receive_sms(self):
        """Check if user can receive SMS messages"""
        return (self.phone_number and 
                self.phone_verified and 
                self.sms_enabled)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone_number': self.phone_number,
            'phone_verified': self.phone_verified,
            'sms_enabled': self.sms_enabled,
            'sms_preferences': self.get_sms_preferences(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Tag(db.Model):
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), nullable=False)  # Hex color code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint to prevent duplicate tag names per user
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='_user_tag_name_uc'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'color': self.color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Goal(db.Model):
    __tablename__ = 'goals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    target_date = db.Column(db.Date)
    achieved_date = db.Column(db.Date)
    archived_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='created')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subgoals = db.relationship('Subgoal', backref='goal', lazy=True, cascade='all, delete-orphan')
    progress_entries = db.relationship('ProgressEntry', backref='goal', lazy=True, cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=goal_tags, lazy='subquery', backref=db.backref('goals', lazy=True))
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_goals')
    
    def to_dict(self, current_user_id=None):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'owner_id': self.owner_id,
            'title': self.title,
            'description': self.description,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'achieved_date': self.achieved_date.isoformat() if self.achieved_date else None,
            'archived_date': self.archived_date.isoformat() if self.archived_date else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_activity_at': self.get_last_activity_at().isoformat() if self.get_last_activity_at() else None,
            'subgoals': [sg.to_dict() for sg in self.subgoals],
            'tags': [tag.to_dict() for tag in self.tags],
            'progress': self.calculate_progress(),
            'is_shared': self.is_shared(),
            'is_owner': self.is_owner(current_user_id) if current_user_id else None,
            'owner': self.owner.to_dict() if self.owner else None,
            'shared_with': [share.shared_with.to_dict() for share in self.shares] if hasattr(self, 'shares') else []
        }
    
    def calculate_progress(self):
        if self.status == 'completed':
            return 100
        
        if self.subgoals:
            achieved_count = sum(1 for sg in self.subgoals if sg.status == 'achieved')
            return int((achieved_count / len(self.subgoals)) * 100)
        
        # Goals with no subgoals start at 0%
        return 0
    
    def get_last_activity_at(self):
        """Get the most recent activity timestamp for this goal"""
        timestamps = [self.updated_at]
        
        # Add subgoal timestamps
        for subgoal in self.subgoals:
            if subgoal.updated_at:
                timestamps.append(subgoal.updated_at)
        
        # Filter out None values and return the most recent
        valid_timestamps = [ts for ts in timestamps if ts is not None]
        return max(valid_timestamps) if valid_timestamps else self.created_at
    
    def is_shared(self):
        """Check if this goal is shared with any users"""
        return len(self.shares) > 0 if hasattr(self, 'shares') else False
    
    def is_owner(self, user_id):
        """Check if the given user is the owner of this goal"""
        if not user_id:
            return False
        return self.owner_id == user_id
    
    def can_access(self, user_id):
        """Check if the given user can access this goal (owner or shared with)"""
        if not user_id:
            return False
        
        # Owner can always access
        if self.is_owner(user_id):
            return True
        
        # Check if goal is shared with this user
        if hasattr(self, 'shares'):
            for share in self.shares:
                if share.shared_with_user_id == user_id:
                    return True
        
        return False
    
    def can_edit(self, user_id):
        """Check if the given user can edit this goal"""
        if not user_id:
            return False
        
        # Owner can always edit
        if self.is_owner(user_id):
            return True
        
        # Check if goal is shared with edit permission
        if hasattr(self, 'shares'):
            for share in self.shares:
                if share.shared_with_user_id == user_id and share.permission_level == 'edit':
                    return True
        
        return False

class Subgoal(db.Model):
    __tablename__ = 'subgoals'
    
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    target_date = db.Column(db.Date)
    achieved_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'title': self.title,
            'description': self.description,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'achieved_date': self.achieved_date.isoformat() if self.achieved_date else None,
            'status': self.status,
            'order_index': self.order_index,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ProgressEntry(db.Model):
    __tablename__ = 'progress_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=False)
    entry_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    progress_percentage = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'progress_percentage': self.progress_percentage,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False)  # 'goal', 'subgoal'
    entity_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'created', 'updated', 'deleted', 'status_changed', etc.
    field_name = db.Column(db.String(50))  # specific field that changed
    old_value = db.Column(db.Text)  # previous value (JSON if complex)
    new_value = db.Column(db.Text)  # new value (JSON if complex)
    event_metadata = db.Column(db.Text)  # additional context (JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to user
    user = db.relationship('User', backref='events')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'action': self.action,
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'metadata': self.event_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SmsReminder(db.Model):
    __tablename__ = 'sms_reminders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=True)
    subgoal_id = db.Column(db.Integer, db.ForeignKey('subgoals.id'), nullable=True)
    reminder_type = db.Column(db.String(50), nullable=False)  # 'deadline', 'motivation', 'progress', 'weekly'
    message_template = db.Column(db.String(500), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    sent_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'sent', 'failed', 'cancelled'
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    goal = db.relationship('Goal', backref='sms_reminders')
    subgoal = db.relationship('Subgoal', backref='sms_reminders')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'goal_id': self.goal_id,
            'subgoal_id': self.subgoal_id,
            'reminder_type': self.reminder_type,
            'message_template': self.message_template,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SmsDeliveryLog(db.Model):
    __tablename__ = 'sms_delivery_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    message_content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), nullable=False)  # 'verification', 'reminder', 'notification'
    aws_message_id = db.Column(db.String(100))  # AWS SNS message ID
    status = db.Column(db.String(20), default='sent', nullable=False)  # 'sent', 'delivered', 'failed'
    cost_usd = db.Column(db.Numeric(10, 6))  # Cost in USD
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    metadata = db.Column(db.Text)  # JSON string for additional data
    
    def get_metadata(self):
        """Get metadata as a dictionary"""
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_metadata(self, metadata_dict):
        """Set metadata from a dictionary"""
        self.metadata = json.dumps(metadata_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'phone_number': self.phone_number,
            'message_content': self.message_content,
            'message_type': self.message_type,
            'aws_message_id': self.aws_message_id,
            'status': self.status,
            'cost_usd': float(self.cost_usd) if self.cost_usd else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'error_message': self.error_message,
            'metadata': self.get_metadata(),
            'created_at': self.sent_at.isoformat() if self.sent_at else None
        }