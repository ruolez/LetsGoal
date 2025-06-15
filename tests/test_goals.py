import unittest
import json
import tempfile
import os
from datetime import datetime, date
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import create_app
from models import db, User, Goal, Subgoal, ProgressEntry

class GoalsTestCase(unittest.TestCase):
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
        
        # Create and login a test user
        self.register_and_login_user()

    def tearDown(self):
        """Clean up after each test method."""
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def register_and_login_user(self):
        """Helper method to register and login a test user."""
        # Register user
        self.client.post('/api/auth/register', 
                        data=json.dumps({
                            'username': 'testuser',
                            'email': 'test@example.com',
                            'password': 'testpass123'
                        }),
                        content_type='application/json')
        
        # Login user
        self.client.post('/api/auth/login',
                        data=json.dumps({
                            'username': 'testuser',
                            'password': 'testpass123'
                        }),
                        content_type='application/json')

    def create_test_goal(self, title="Test Goal", description="Test Description"):
        """Helper method to create a test goal."""
        return self.client.post('/api/goals',
                               data=json.dumps({
                                   'title': title,
                                   'description': description,
                                   'target_date': '2024-12-31'
                               }),
                               content_type='application/json')

    def test_create_goal_success(self):
        """Test successful goal creation."""
        response = self.create_test_goal()
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Goal')
        self.assertEqual(data['description'], 'Test Description')
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(data['progress'], 0)

    def test_create_goal_missing_title(self):
        """Test goal creation with missing title."""
        response = self.client.post('/api/goals',
                                   data=json.dumps({
                                       'description': 'Test Description'
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Title is required', data['error'])

    def test_get_goals_empty(self):
        """Test getting goals when user has none."""
        response = self.client.get('/api/goals')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 0)

    def test_get_goals_with_data(self):
        """Test getting goals when user has goals."""
        # Create test goals
        self.create_test_goal("Goal 1", "Description 1")
        self.create_test_goal("Goal 2", "Description 2")
        
        response = self.client.get('/api/goals')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['title'], 'Goal 1')
        self.assertEqual(data[1]['title'], 'Goal 2')

    def test_update_goal_success(self):
        """Test successful goal update."""
        # Create a test goal
        create_response = self.create_test_goal()
        goal_data = json.loads(create_response.data)
        goal_id = goal_data['id']
        
        # Update the goal
        response = self.client.put(f'/api/goals/{goal_id}',
                                  data=json.dumps({
                                      'title': 'Updated Goal',
                                      'description': 'Updated Description',
                                      'status': 'in_progress'
                                  }),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Updated Goal')
        self.assertEqual(data['description'], 'Updated Description')
        self.assertEqual(data['status'], 'in_progress')

    def test_update_goal_to_achieved(self):
        """Test updating goal status to achieved."""
        # Create a test goal
        create_response = self.create_test_goal()
        goal_data = json.loads(create_response.data)
        goal_id = goal_data['id']
        
        # Update the goal to achieved
        response = self.client.put(f'/api/goals/{goal_id}',
                                  data=json.dumps({
                                      'status': 'achieved'
                                  }),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'achieved')
        self.assertIsNotNone(data['achieved_date'])

    def test_update_nonexistent_goal(self):
        """Test updating a goal that doesn't exist."""
        response = self.client.put('/api/goals/999',
                                  data=json.dumps({
                                      'title': 'Updated Goal'
                                  }),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Goal not found', data['error'])

    def test_delete_goal_success(self):
        """Test successful goal deletion."""
        # Create a test goal
        create_response = self.create_test_goal()
        goal_data = json.loads(create_response.data)
        goal_id = goal_data['id']
        
        # Delete the goal
        response = self.client.delete(f'/api/goals/{goal_id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('deleted successfully', data['message'])
        
        # Verify goal is deleted
        get_response = self.client.get('/api/goals')
        goals_data = json.loads(get_response.data)
        self.assertEqual(len(goals_data), 0)

    def test_delete_nonexistent_goal(self):
        """Test deleting a goal that doesn't exist."""
        response = self.client.delete('/api/goals/999')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Goal not found', data['error'])

    def test_create_subgoal_success(self):
        """Test successful subgoal creation."""
        # Create a test goal
        create_response = self.create_test_goal()
        goal_data = json.loads(create_response.data)
        goal_id = goal_data['id']
        
        # Create a subgoal
        response = self.client.post(f'/api/goals/{goal_id}/subgoals',
                                   data=json.dumps({
                                       'title': 'Test Subgoal',
                                       'description': 'Test Subgoal Description',
                                       'order_index': 1
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Subgoal')
        self.assertEqual(data['goal_id'], goal_id)
        self.assertEqual(data['order_index'], 1)

    def test_create_subgoal_nonexistent_goal(self):
        """Test creating subgoal for non-existent goal."""
        response = self.client.post('/api/goals/999/subgoals',
                                   data=json.dumps({
                                       'title': 'Test Subgoal'
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Goal not found', data['error'])

    def test_add_progress_success(self):
        """Test successful progress addition."""
        # Create a test goal
        create_response = self.create_test_goal()
        goal_data = json.loads(create_response.data)
        goal_id = goal_data['id']
        
        # Add progress
        response = self.client.post(f'/api/goals/{goal_id}/progress',
                                   data=json.dumps({
                                       'progress_percentage': 50,
                                       'notes': 'Halfway there!'
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertEqual(data['progress_percentage'], 50)
        self.assertEqual(data['notes'], 'Halfway there!')
        self.assertEqual(data['goal_id'], goal_id)

    def test_add_progress_nonexistent_goal(self):
        """Test adding progress to non-existent goal."""
        response = self.client.post('/api/goals/999/progress',
                                   data=json.dumps({
                                       'progress_percentage': 50
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Goal not found', data['error'])

    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint."""
        # Create test goals with different statuses
        goal1_response = self.create_test_goal("Goal 1")
        goal1_data = json.loads(goal1_response.data)
        
        goal2_response = self.create_test_goal("Goal 2")
        goal2_data = json.loads(goal2_response.data)
        
        # Update one goal to achieved
        self.client.put(f'/api/goals/{goal1_data["id"]}',
                       data=json.dumps({'status': 'achieved'}),
                       content_type='application/json')
        
        # Update another to in_progress
        self.client.put(f'/api/goals/{goal2_data["id"]}',
                       data=json.dumps({'status': 'in_progress'}),
                       content_type='application/json')
        
        # Get stats
        response = self.client.get('/api/dashboard/stats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['total_goals'], 2)
        self.assertEqual(data['achieved_goals'], 1)
        self.assertEqual(data['active_goals'], 1)
        self.assertEqual(data['pending_goals'], 0)
        self.assertEqual(data['achievement_rate'], 50.0)

    def test_goal_progress_calculation_with_subgoals(self):
        """Test goal progress calculation based on subgoals."""
        with self.app.app_context():
            # Create user and goal
            user = User.query.filter_by(username='testuser').first()
            goal = Goal(
                user_id=user.id,
                title='Test Goal',
                description='Test Description'
            )
            db.session.add(goal)
            db.session.commit()
            
            # Create subgoals
            subgoal1 = Subgoal(goal_id=goal.id, title='Subgoal 1', status='achieved')
            subgoal2 = Subgoal(goal_id=goal.id, title='Subgoal 2', status='pending')
            subgoal3 = Subgoal(goal_id=goal.id, title='Subgoal 3', status='pending')
            
            db.session.add_all([subgoal1, subgoal2, subgoal3])
            db.session.commit()
            
            # Calculate progress (should be 33% - 1 out of 3 achieved)
            progress = goal.calculate_progress()
            self.assertEqual(progress, 33)  # 1/3 * 100 = 33.33, rounded to 33

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access goal endpoints."""
        # Logout first
        self.client.post('/api/auth/logout')
        
        # Try to access goals endpoint
        response = self.client.get('/api/goals')
        self.assertEqual(response.status_code, 401)
        
        # Try to create a goal
        response = self.client.post('/api/goals',
                                   data=json.dumps({
                                       'title': 'Test Goal'
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()