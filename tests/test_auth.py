import unittest
import json
import tempfile
import os
from datetime import datetime
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import create_app
from models import db, User, Goal

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.db_path}'
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        with self.app.app_context():
            db.create_all()
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up after each test method."""
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def register_user(self, username="testuser", email="test@example.com", password="testpass123"):
        """Helper method to register a user."""
        return self.client.post('/api/auth/register', 
                               data=json.dumps({
                                   'username': username,
                                   'email': email,
                                   'password': password
                               }),
                               content_type='application/json')

    def login_user(self, username="testuser", password="testpass123"):
        """Helper method to login a user."""
        return self.client.post('/api/auth/login',
                               data=json.dumps({
                                   'username': username,
                                   'password': password
                               }),
                               content_type='application/json')

    def test_user_registration_success(self):
        """Test successful user registration."""
        response = self.register_user()
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@example.com')

    def test_user_registration_duplicate_username(self):
        """Test registration with duplicate username."""
        # Register first user
        self.register_user()
        
        # Try to register with same username
        response = self.register_user(email="different@example.com")
        self.assertEqual(response.status_code, 409)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Username already exists', data['error'])

    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email."""
        # Register first user
        self.register_user()
        
        # Try to register with same email
        response = self.register_user(username="differentuser")
        self.assertEqual(response.status_code, 409)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Email already registered', data['error'])

    def test_user_registration_missing_fields(self):
        """Test registration with missing required fields."""
        response = self.client.post('/api/auth/register',
                                   data=json.dumps({
                                       'username': 'testuser'
                                       # Missing email and password
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Missing required fields', data['error'])

    def test_user_login_success(self):
        """Test successful user login."""
        # Register user first
        self.register_user()
        
        # Login
        response = self.login_user()
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        # Register user first
        self.register_user()
        
        # Try login with wrong password
        response = self.login_user(password="wrongpassword")
        self.assertEqual(response.status_code, 401)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Invalid credentials', data['error'])

    def test_user_login_nonexistent_user(self):
        """Test login with non-existent user."""
        response = self.login_user()
        self.assertEqual(response.status_code, 401)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Invalid credentials', data['error'])

    def test_user_login_missing_fields(self):
        """Test login with missing required fields."""
        response = self.client.post('/api/auth/login',
                                   data=json.dumps({
                                       'username': 'testuser'
                                       # Missing password
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Missing username or password', data['error'])

    def test_user_logout(self):
        """Test user logout."""
        # Register and login user first
        self.register_user()
        self.login_user()
        
        # Logout
        response = self.client.post('/api/auth/logout')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('Logout successful', data['message'])

    def test_auth_check_authenticated(self):
        """Test auth check for authenticated user."""
        # Register and login user first
        self.register_user()
        self.login_user()
        
        # Check auth status
        response = self.client.get('/api/auth/check')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['authenticated'])
        self.assertIn('user', data)

    def test_auth_check_unauthenticated(self):
        """Test auth check for unauthenticated user."""
        response = self.client.get('/api/auth/check')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertFalse(data['authenticated'])

    def test_get_current_user_authenticated(self):
        """Test getting current user when authenticated."""
        # Register and login user first
        self.register_user()
        self.login_user()
        
        # Get current user
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')

    def test_get_current_user_unauthenticated(self):
        """Test getting current user when not authenticated."""
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 401)

    def test_password_hashing(self):
        """Test that passwords are properly hashed."""
        with self.app.app_context():
            # Create user
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpassword')
            
            # Password should be hashed, not stored in plain text
            self.assertNotEqual(user.password_hash, 'testpassword')
            self.assertTrue(user.check_password('testpassword'))
            self.assertFalse(user.check_password('wrongpassword'))

if __name__ == '__main__':
    unittest.main()