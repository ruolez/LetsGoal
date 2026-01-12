import unittest
import json
import tempfile
import os
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import create_app
from models import db, User, Goal, Subgoal, SmsDeliveryLog, SmsReminder
from sms_service import SmsService
from message_templates import MessageTemplateEngine
from reminder_scheduler import ReminderScheduler

class SmsTestCase(unittest.TestCase):
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
        
        # Create test user
        self.test_user = User(username='testuser', email='test@example.com')
        self.test_user.set_password('testpass123')
        db.session.add(self.test_user)
        db.session.commit()
        
        # Login test user
        self.login_user()

    def tearDown(self):
        """Clean up after each test method."""
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def login_user(self):
        """Helper method to login the test user."""
        return self.client.post('/api/auth/login',
                               data=json.dumps({
                                   'username': 'testuser',
                                   'password': 'testpass123'
                               }),
                               content_type='application/json')

class SmsServiceTestCase(SmsTestCase):
    """Test cases for SMS service functionality."""
    
    def setUp(self):
        super().setUp()
        self.sms_service = SmsService()
    
    def test_phone_number_validation_valid_us(self):
        """Test phone number validation with valid US number."""
        is_valid, formatted = self.sms_service.validate_phone_number('+1-555-123-4567', 'US')
        self.assertTrue(is_valid)
        self.assertEqual(formatted, '+15551234567')
    
    def test_phone_number_validation_valid_us_no_country_code(self):
        """Test phone number validation with US number without country code."""
        is_valid, formatted = self.sms_service.validate_phone_number('555-123-4567', 'US')
        self.assertTrue(is_valid)
        self.assertEqual(formatted, '+15551234567')
    
    def test_phone_number_validation_invalid(self):
        """Test phone number validation with invalid number."""
        is_valid, error_msg = self.sms_service.validate_phone_number('123', 'US')
        self.assertFalse(is_valid)
        self.assertIn('Invalid phone number', error_msg)
    
    def test_verification_code_generation(self):
        """Test verification code generation."""
        code = self.sms_service.generate_verification_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        self.assertTrue(100000 <= int(code) <= 999999)
    
    @patch('boto3.client')
    def test_send_sms_success(self, mock_boto_client):
        """Test successful SMS sending."""
        # Mock AWS SNS client
        mock_sns = MagicMock()
        mock_sns.publish.return_value = {'MessageId': 'test-message-id-123'}
        mock_boto_client.return_value = mock_sns
        
        # Reinitialize SMS service with mocked client
        self.sms_service._initialize_sns_client()
        self.sms_service.sns_client = mock_sns
        
        success, result = self.sms_service.send_sms(
            phone_number='+15551234567',
            message='Test message',
            user_id=self.test_user.id,
            message_type='test'
        )
        
        self.assertTrue(success)
        self.assertEqual(result, 'test-message-id-123')
        mock_sns.publish.assert_called_once()
        
        # Check delivery log was created
        log = SmsDeliveryLog.query.filter_by(user_id=self.test_user.id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'sent')
        self.assertEqual(log.aws_message_id, 'test-message-id-123')
    
    @patch('boto3.client')
    def test_send_sms_invalid_phone(self, mock_boto_client):
        """Test SMS sending with invalid phone number."""
        mock_sns = MagicMock()
        mock_boto_client.return_value = mock_sns
        self.sms_service.sns_client = mock_sns
        
        success, result = self.sms_service.send_sms(
            phone_number='invalid',
            message='Test message',
            user_id=self.test_user.id,
            message_type='test'
        )
        
        self.assertFalse(success)
        self.assertIn('Invalid phone number', result)
        mock_sns.publish.assert_not_called()
    
    @patch('boto3.client')
    def test_send_verification_sms(self, mock_boto_client):
        """Test sending verification SMS."""
        mock_sns = MagicMock()
        mock_sns.publish.return_value = {'MessageId': 'verify-message-id'}
        mock_boto_client.return_value = mock_sns
        self.sms_service.sns_client = mock_sns
        
        success, verification_code = self.sms_service.send_verification_sms(
            user_id=self.test_user.id,
            phone_number='+15551234567'
        )
        
        self.assertTrue(success)
        self.assertEqual(len(verification_code), 6)
        
        # Check user was updated with verification code
        user = User.query.get(self.test_user.id)
        self.assertEqual(user.verification_code, verification_code)
        self.assertIsNotNone(user.verification_expires_at)
    
    def test_verify_phone_number_success(self):
        """Test successful phone number verification."""
        # Set up verification code
        self.test_user.verification_code = '123456'
        self.test_user.verification_expires_at = datetime.utcnow() + timedelta(minutes=5)
        db.session.commit()
        
        success, message = self.sms_service.verify_phone_number(
            user_id=self.test_user.id,
            verification_code='123456'
        )
        
        self.assertTrue(success)
        self.assertIn('verified successfully', message)
        
        # Check user was updated
        user = User.query.get(self.test_user.id)
        self.assertTrue(user.phone_verified)
        self.assertIsNone(user.verification_code)
    
    def test_verify_phone_number_invalid_code(self):
        """Test phone verification with invalid code."""
        self.test_user.verification_code = '123456'
        self.test_user.verification_expires_at = datetime.utcnow() + timedelta(minutes=5)
        db.session.commit()
        
        success, message = self.sms_service.verify_phone_number(
            user_id=self.test_user.id,
            verification_code='wrong123'
        )
        
        self.assertFalse(success)
        self.assertIn('Invalid verification code', message)
    
    def test_verify_phone_number_expired_code(self):
        """Test phone verification with expired code."""
        self.test_user.verification_code = '123456'
        self.test_user.verification_expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()
        
        success, message = self.sms_service.verify_phone_number(
            user_id=self.test_user.id,
            verification_code='123456'
        )
        
        self.assertFalse(success)
        self.assertIn('expired', message)
    
    def test_opt_out_detection(self):
        """Test opt-out keyword detection."""
        test_cases = [
            ('STOP', True),
            ('stop', True),
            ('UNSUBSCRIBE', True),
            ('quit', True),
            ('CANCEL', True),
            ('Please stop sending messages', True),
            ('Hello world', False),
            ('Thanks for the reminder', False)
        ]
        
        for message, expected in test_cases:
            result = self.sms_service.check_opt_out('+15551234567', message)
            self.assertEqual(result, expected, f"Failed for message: {message}")
    
    @patch('boto3.client')
    def test_handle_opt_out(self, mock_boto_client):
        """Test handling opt-out request."""
        mock_sns = MagicMock()
        mock_sns.publish.return_value = {'MessageId': 'optout-message-id'}
        mock_boto_client.return_value = mock_sns
        self.sms_service.sns_client = mock_sns
        
        # Set user's phone number
        self.test_user.phone_number = '+15551234567'
        self.test_user.sms_enabled = True
        db.session.commit()
        
        success = self.sms_service.handle_opt_out('+15551234567')
        
        self.assertTrue(success)
        
        # Check user SMS was disabled
        user = User.query.get(self.test_user.id)
        self.assertFalse(user.sms_enabled)
        
        # Check confirmation SMS was sent
        mock_sns.publish.assert_called_once()


class MessageTemplateTestCase(SmsTestCase):
    """Test cases for message template engine."""
    
    def setUp(self):
        super().setUp()
        self.template_engine = MessageTemplateEngine()
        
        # Create test goal
        self.test_goal = Goal(
            user_id=self.test_user.id,
            owner_id=self.test_user.id,
            title='Test Goal',
            description='Test goal description',
            target_date=date.today() + timedelta(days=7),
            status='working'
        )
        db.session.add(self.test_goal)
        
        # Create test subgoal
        self.test_subgoal = Subgoal(
            goal_id=self.test_goal.id,
            title='Test Subgoal',
            description='Test subgoal description',
            target_date=date.today() + timedelta(days=3),
            status='pending'
        )
        db.session.add(self.test_subgoal)
        db.session.commit()
    
    def test_generate_deadline_24h_message(self):
        """Test generation of 24-hour deadline reminder."""
        message = self.template_engine.generate_message(
            message_type='deadline_24h',
            user_id=self.test_user.id,
            goal_id=self.test_goal.id
        )
        
        self.assertIsInstance(message, str)
        self.assertIn('Test Goal', message)
        self.assertIn('tomorrow', message)
        self.assertTrue(len(message) <= 160)  # SMS length limit
    
    def test_generate_daily_motivation_message(self):
        """Test generation of daily motivation message."""
        message = self.template_engine.generate_message(
            message_type='daily_motivation',
            user_id=self.test_user.id
        )
        
        self.assertIsInstance(message, str)
        self.assertIn('Good morning', message.lower())
        self.assertTrue(len(message) <= 160)
    
    def test_generate_progress_milestone_message(self):
        """Test generation of progress milestone message."""
        message = self.template_engine.generate_message(
            message_type='progress_milestone',
            user_id=self.test_user.id,
            goal_id=self.test_goal.id,
            custom_data={'progress': 50}
        )
        
        self.assertIsInstance(message, str)
        self.assertIn('50%', message)
        self.assertIn('Test Goal', message)
        self.assertTrue(len(message) <= 160)
    
    def test_generate_subgoal_due_message(self):
        """Test generation of subgoal due reminder."""
        message = self.template_engine.generate_message(
            message_type='subgoal_due',
            user_id=self.test_user.id,
            goal_id=self.test_goal.id,
            subgoal_id=self.test_subgoal.id
        )
        
        self.assertIsInstance(message, str)
        self.assertIn('Test Subgoal', message)
        self.assertIn('Test Goal', message)
        self.assertTrue(len(message) <= 160)
    
    def test_message_truncation(self):
        """Test message truncation for SMS limits."""
        # Create goal with very long title
        long_goal = Goal(
            user_id=self.test_user.id,
            owner_id=self.test_user.id,
            title='This is an extremely long goal title that should definitely be truncated when used in SMS messages to ensure compliance with SMS character limits',
            description='Long description',
            target_date=date.today() + timedelta(days=7),
            status='working'
        )
        db.session.add(long_goal)
        db.session.commit()
        
        message = self.template_engine.generate_message(
            message_type='deadline_24h',
            user_id=self.test_user.id,
            goal_id=long_goal.id
        )
        
        self.assertTrue(len(message) <= 160)
    
    def test_preview_message_types(self):
        """Test message preview functionality."""
        preview = self.template_engine.preview_message('deadline_24h')
        
        self.assertIn('message_type', preview)
        self.assertIn('template_count', preview)
        self.assertIn('previews', preview)
        self.assertTrue(len(preview['previews']) > 0)
        
        for preview_item in preview['previews']:
            self.assertIn('message', preview_item)
            self.assertIn('length', preview_item)
            self.assertIn('fits_sms', preview_item)
    
    def test_available_message_types(self):
        """Test getting available message types."""
        types = self.template_engine.get_available_message_types()
        
        expected_types = [
            'deadline_24h', 'deadline_1h', 'daily_motivation',
            'progress_milestone', 'weekly_summary', 'subgoal_due',
            'goal_completed', 'goal_overdue', 'streak_reminder'
        ]
        
        for expected_type in expected_types:
            self.assertIn(expected_type, types)


class SmsApiTestCase(SmsTestCase):
    """Test cases for SMS API endpoints."""
    
    def test_get_sms_settings_unauthenticated(self):
        """Test getting SMS settings without authentication."""
        # Logout first
        self.client.post('/api/auth/logout')
        
        response = self.client.get('/api/user/sms-settings')
        self.assertEqual(response.status_code, 401)
    
    def test_get_sms_settings_default(self):
        """Test getting default SMS settings for new user."""
        response = self.client.get('/api/user/sms-settings')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsNone(data['phone_number'])
        self.assertFalse(data['phone_verified'])
        self.assertFalse(data['sms_enabled'])
        self.assertIsInstance(data['sms_preferences'], dict)
    
    def test_update_sms_settings(self):
        """Test updating SMS settings."""
        settings_data = {
            'sms_enabled': True,
            'sms_preferences': {
                'deadline_reminders': True,
                'daily_motivation': False,
                'progress_updates': True,
                'weekly_summary': False,
                'reminder_time': '10:00'
            }
        }
        
        response = self.client.put('/api/user/sms-settings',
                                  data=json.dumps(settings_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        # Verify settings were saved
        user = User.query.get(self.test_user.id)
        self.assertTrue(user.sms_enabled)
        preferences = user.get_sms_preferences()
        self.assertTrue(preferences['deadline_reminders'])
        self.assertFalse(preferences['daily_motivation'])
        self.assertEqual(preferences['reminder_time'], '10:00')
    
    @patch('sms_service.sms_service.send_verification_sms')
    def test_send_verification_code(self, mock_send_verification):
        """Test sending verification code endpoint."""
        mock_send_verification.return_value = (True, '123456')
        
        response = self.client.post('/api/user/send-sms-verification',
                                   data=json.dumps({'phone_number': '+15551234567'}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('message', data)
        mock_send_verification.assert_called_once()
    
    def test_send_verification_code_missing_phone(self):
        """Test sending verification code without phone number."""
        response = self.client.post('/api/user/send-sms-verification',
                                   data=json.dumps({}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('required', data['error'])
    
    @patch('sms_service.sms_service.verify_phone_number')
    def test_verify_phone_number_endpoint(self, mock_verify):
        """Test phone verification endpoint."""
        mock_verify.return_value = (True, 'Phone number verified successfully')
        
        response = self.client.post('/api/user/verify-phone',
                                   data=json.dumps({'verification_code': '123456'}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('message', data)
        mock_verify.assert_called_once()
    
    def test_verify_phone_number_missing_code(self):
        """Test phone verification without code."""
        response = self.client.post('/api/user/verify-phone',
                                   data=json.dumps({}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('required', data['error'])
    
    @patch('sms_service.sms_service.get_user_sms_stats')
    def test_get_sms_stats(self, mock_get_stats):
        """Test getting SMS statistics."""
        mock_stats = {
            'total_sent': 10,
            'total_cost_usd': 0.0645,
            'status_breakdown': {'sent': 9, 'failed': 1},
            'type_breakdown': {'reminder': 8, 'verification': 2},
            'period_days': 30
        }
        mock_get_stats.return_value = mock_stats
        
        response = self.client.get('/api/user/sms-stats?days=30')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['total_sent'], 10)
        self.assertEqual(data['total_cost_usd'], 0.0645)
        mock_get_stats.assert_called_once_with(self.test_user.id, 30)


class SmsIntegrationTestCase(SmsTestCase):
    """Test cases for SMS integration with goal workflows."""
    
    @patch('reminder_scheduler.reminder_scheduler.schedule_goal_deadline_reminders')
    def test_goal_creation_schedules_sms(self, mock_schedule):
        """Test that creating a goal with target date schedules SMS reminders."""
        # Enable SMS for user
        self.test_user.sms_enabled = True
        self.test_user.phone_verified = True
        db.session.commit()
        
        goal_data = {
            'title': 'Test Goal with SMS',
            'description': 'Test description',
            'target_date': (date.today() + timedelta(days=7)).isoformat()
        }
        
        response = self.client.post('/api/goals',
                                   data=json.dumps(goal_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        # Verify reminder was scheduled
        mock_schedule.assert_called_once()
    
    @patch('reminder_scheduler.reminder_scheduler.schedule_subgoal_deadline_reminder')
    def test_subgoal_creation_schedules_sms(self, mock_schedule):
        """Test that creating a subgoal with target date schedules SMS reminders."""
        # Create goal first
        goal = Goal(
            user_id=self.test_user.id,
            owner_id=self.test_user.id,
            title='Parent Goal',
            status='created'
        )
        db.session.add(goal)
        db.session.commit()
        
        # Enable SMS for user
        self.test_user.sms_enabled = True
        self.test_user.phone_verified = True
        db.session.commit()
        
        subgoal_data = {
            'title': 'Test Subgoal with SMS',
            'description': 'Test description',
            'target_date': (date.today() + timedelta(days=3)).isoformat()
        }
        
        response = self.client.post(f'/api/goals/{goal.id}/subgoals',
                                   data=json.dumps(subgoal_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        # Verify reminder was scheduled
        mock_schedule.assert_called_once()
    
    @patch('reminder_scheduler.reminder_scheduler.schedule_progress_milestone_reminder')
    def test_goal_completion_sends_sms(self, mock_schedule_milestone):
        """Test that completing a goal sends milestone SMS."""
        # Create goal with subgoals
        goal = Goal(
            user_id=self.test_user.id,
            owner_id=self.test_user.id,
            title='Test Goal',
            status='working'
        )
        db.session.add(goal)
        db.session.flush()
        
        subgoal = Subgoal(
            goal_id=goal.id,
            title='Test Subgoal',
            status='pending'
        )
        db.session.add(subgoal)
        db.session.commit()
        
        # Enable SMS for user
        self.test_user.sms_enabled = True
        self.test_user.phone_verified = True
        db.session.commit()
        
        # Complete the subgoal (which should complete the goal)
        response = self.client.put(f'/api/subgoals/{subgoal.id}',
                                  data=json.dumps({'status': 'achieved'}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        # Verify milestone SMS was scheduled
        mock_schedule_milestone.assert_called()


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(SmsServiceTestCase))
    test_suite.addTest(unittest.makeSuite(MessageTemplateTestCase))
    test_suite.addTest(unittest.makeSuite(SmsApiTestCase))
    test_suite.addTest(unittest.makeSuite(SmsIntegrationTestCase))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)