import sys
sys.path.append('/app')
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from backend.models import db, User, UserSession
from datetime import datetime
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    """Decorator to require admin role for access"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate input
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    username = data['username']
    email = data['email']
    password = data['password']
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    # Create new user
    user = User(username=username, email=email)
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # Log the user in
        login_user(user)
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400
    
    username = data['username']
    password = data['password']
    
    # Find user by username or email
    user = User.query.filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Update user login metadata
    user.last_login_at = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    
    # Create user session
    session = UserSession(
        user_id=user.id,
        session_start=datetime.utcnow(),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:500],  # Limit to 500 chars
        is_active=True
    )
    db.session.add(session)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Login failed'}), 500
    
    # Log the user in
    login_user(user, remember=data.get('remember', False))
    
    # Store session ID in Flask session for tracking
    from flask import session as flask_session
    flask_session['user_session_id'] = session.id
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    # End user session
    from flask import session as flask_session
    session_id = flask_session.get('user_session_id')
    
    if session_id:
        user_session = UserSession.query.get(session_id)
        if user_session and user_session.is_active:
            user_session.session_end = datetime.utcnow()
            user_session.is_active = False
            try:
                db.session.commit()
            except:
                db.session.rollback()
    
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({
        'user': current_user.to_dict()
    }), 200

@auth_bp.route('/check', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        }), 200
    else:
        return jsonify({
            'authenticated': False
        }), 200