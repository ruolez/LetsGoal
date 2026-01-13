from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import BigInteger

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
    role = db.Column(db.String(20), nullable=False, default='user')
    last_login_at = db.Column(db.DateTime)
    password_changed_at = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    goals = db.relationship('Goal', foreign_keys='Goal.user_id', backref='user', lazy=True, cascade='all, delete-orphan')
    tags = db.relationship('Tag', backref='user', lazy=True, cascade='all, delete-orphan')
    sessions = db.relationship('UserSession', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'login_count': self.login_count,
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
            'subgoals': [sg.to_dict() for sg in sorted(self.subgoals, key=lambda x: x.order_index or 0)],
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
            'event_metadata': self.event_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_start = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    session_end = db.Column(db.DateTime)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    def get_duration_minutes(self):
        """Get session duration in minutes"""
        if self.session_end:
            duration = self.session_end - self.session_start
            return int(duration.total_seconds() / 60)
        return 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_start': self.session_start.isoformat() if self.session_start else None,
            'session_end': self.session_end.isoformat() if self.session_end else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'is_active': self.is_active,
            'duration_minutes': self.get_duration_minutes()
        }

class AdminSettings(db.Model):
    __tablename__ = 'admin_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text)
    setting_type = db.Column(db.String(20), nullable=False, default='string')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_setting(cls, key, default=None):
        """Get a setting value by key"""
        setting = cls.query.filter_by(setting_key=key).first()
        if setting:
            # Convert value based on type
            if setting.setting_type == 'integer':
                return int(setting.setting_value)
            elif setting.setting_type == 'boolean':
                return setting.setting_value.lower() in ('true', '1', 'yes')
            elif setting.setting_type == 'float':
                return float(setting.setting_value)
            return setting.setting_value
        return default
    
    @classmethod
    def set_setting(cls, key, value, setting_type='string', description=None):
        """Set or update a setting"""
        setting = cls.query.filter_by(setting_key=key).first()
        if not setting:
            setting = cls(
                setting_key=key,
                setting_type=setting_type,
                description=description
            )
            db.session.add(setting)
        
        # Convert value to string for storage
        if isinstance(value, bool):
            setting.setting_value = 'true' if value else 'false'
        else:
            setting.setting_value = str(value)
        
        setting.updated_at = datetime.utcnow()
        return setting
    
    def to_dict(self):
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'setting_type': self.setting_type,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SystemBackup(db.Model):
    __tablename__ = 'system_backups'
    
    id = db.Column(db.Integer, primary_key=True)
    backup_name = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    backup_size = db.Column(BigInteger)
    backup_type = db.Column(db.String(20), nullable=False, default='manual')
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='completed')
    error_message = db.Column(db.Text)
    backup_metadata = db.Column(db.Text)
    
    # Relationships
    created_by = db.relationship('User', backref='created_backups')
    
    def get_backup_age_days(self):
        """Get age of backup in days"""
        if self.created_at:
            age = datetime.utcnow() - self.created_at
            return age.days
        return 0
    
    def set_metadata(self, metadata_dict):
        """Set metadata as JSON string"""
        import json
        self.backup_metadata = json.dumps(metadata_dict)
    
    def get_metadata(self):
        """Get metadata as dictionary"""
        import json
        if self.backup_metadata:
            try:
                return json.loads(self.backup_metadata)
            except:
                return {}
        return {}
    
    def to_dict(self):
        return {
            'id': self.id,
            'backup_name': self.backup_name,
            'file_path': self.file_path,
            'backup_size': self.backup_size,
            'backup_type': self.backup_type,
            'created_by_user_id': self.created_by_user_id,
            'created_by': self.created_by.username if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status,
            'error_message': self.error_message,
            'metadata': self.backup_metadata
        }

class Plan(db.Model):
    __tablename__ = 'plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stripe_plan_id = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    interval = db.Column(db.String(20), nullable=False)  # 'month', 'year'
    features = db.Column(db.Text)  # JSON string of features
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    subscriptions = db.relationship('Subscription', backref='plan', lazy=True)
    
    def get_features(self):
        """Get features as dictionary"""
        import json
        if self.features:
            try:
                return json.loads(self.features)
            except:
                return {}
        return {}
    
    def set_features(self, features_dict):
        """Set features as JSON string"""
        import json
        self.features = json.dumps(features_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'stripe_plan_id': self.stripe_plan_id,
            'price': float(self.price),
            'currency': self.currency,
            'interval': self.interval,
            'features': self.get_features(),
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class StripeCustomer(db.Model):
    __tablename__ = 'stripe_customers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    stripe_customer_id = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('stripe_customer', uselist=False))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'stripe_customer_id': self.stripe_customer_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    stripe_subscription_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'active', 'canceled', 'past_due', 'unpaid', 'trialing'
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    trial_start = db.Column(db.DateTime)
    trial_end = db.Column(db.DateTime)
    canceled_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    stripe_metadata = db.Column(db.Text)  # Additional Stripe metadata as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='subscriptions')
    history = db.relationship('SubscriptionHistory', backref='subscription', lazy=True, cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='subscription', lazy=True, cascade='all, delete-orphan')
    
    def is_active(self):
        """Check if subscription is currently active"""
        return self.status in ['active', 'trialing']
    
    def is_trial(self):
        """Check if subscription is in trial period"""
        now = datetime.utcnow()
        return (self.status == 'trialing' and 
                self.trial_start and self.trial_end and
                self.trial_start <= now <= self.trial_end)
    
    def days_until_renewal(self):
        """Get days until next renewal"""
        if self.current_period_end:
            delta = self.current_period_end - datetime.utcnow()
            return max(0, delta.days)
        return 0
    
    def get_metadata(self):
        """Get metadata as dictionary"""
        import json
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except:
                return {}
        return {}
    
    def set_metadata(self, metadata_dict):
        """Set metadata as JSON string"""
        import json
        self.stripe_metadata = json.dumps(metadata_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            'stripe_subscription_id': self.stripe_subscription_id,
            'status': self.status,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'trial_start': self.trial_start.isoformat() if self.trial_start else None,
            'trial_end': self.trial_end.isoformat() if self.trial_end else None,
            'canceled_at': self.canceled_at.isoformat() if self.canceled_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'metadata': self.get_metadata(),
            'is_active': self.is_active(),
            'is_trial': self.is_trial(),
            'days_until_renewal': self.days_until_renewal(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'plan': self.plan.to_dict() if self.plan else None,
            'user': self.user.to_dict() if self.user else None
        }

class SubscriptionHistory(db.Model):
    __tablename__ = 'subscription_history'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'created', 'updated', 'canceled', 'reactivated', 'plan_changed'
    old_plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'))
    new_plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'))
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20))
    change_reason = db.Column(db.String(200))
    stripe_event_id = db.Column(db.String(100))  # Stripe webhook event ID
    history_metadata = db.Column(db.Text)  # Additional context as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    old_plan = db.relationship('Plan', foreign_keys=[old_plan_id])
    new_plan = db.relationship('Plan', foreign_keys=[new_plan_id])
    
    def get_metadata(self):
        """Get metadata as dictionary"""
        import json
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except:
                return {}
        return {}
    
    def set_metadata(self, metadata_dict):
        """Set metadata as JSON string"""
        import json
        self.stripe_metadata = json.dumps(metadata_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'action': self.action,
            'old_plan_id': self.old_plan_id,
            'new_plan_id': self.new_plan_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'change_reason': self.change_reason,
            'stripe_event_id': self.stripe_event_id,
            'metadata': self.get_metadata(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'old_plan': self.old_plan.to_dict() if self.old_plan else None,
            'new_plan': self.new_plan.to_dict() if self.new_plan else None
        }

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=False)
    stripe_invoice_id = db.Column(db.String(100), unique=True, nullable=False)
    amount_due = db.Column(db.Numeric(10, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), default=0)
    amount_remaining = db.Column(db.Numeric(10, 2), default=0)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    status = db.Column(db.String(20), nullable=False)  # 'draft', 'open', 'paid', 'uncollectible', 'void'
    paid = db.Column(db.Boolean, nullable=False, default=False)
    payment_intent_id = db.Column(db.String(100))
    invoice_pdf = db.Column(db.String(500))  # URL to PDF
    hosted_invoice_url = db.Column(db.String(500))  # Stripe hosted invoice URL
    period_start = db.Column(db.DateTime)
    period_end = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)
    stripe_metadata = db.Column(db.Text)  # Additional Stripe metadata as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.paid or not self.due_date:
            return False
        return datetime.utcnow() > self.due_date
    
    def get_metadata(self):
        """Get metadata as dictionary"""
        import json
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except:
                return {}
        return {}
    
    def set_metadata(self, metadata_dict):
        """Set metadata as JSON string"""
        import json
        self.stripe_metadata = json.dumps(metadata_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'stripe_invoice_id': self.stripe_invoice_id,
            'amount_due': float(self.amount_due),
            'amount_paid': float(self.amount_paid),
            'amount_remaining': float(self.amount_remaining),
            'currency': self.currency,
            'status': self.status,
            'paid': self.paid,
            'payment_intent_id': self.payment_intent_id,
            'invoice_pdf': self.invoice_pdf,
            'hosted_invoice_url': self.hosted_invoice_url,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'is_overdue': self.is_overdue(),
            'metadata': self.get_metadata(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }