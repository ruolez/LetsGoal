"""
SMS Service Module
Handles SMS notifications and reminders for LetsGoal
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from models import db, User, Goal, Subgoal, AdminSettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SMSService:
    """Service for sending SMS notifications"""
    
    def __init__(self):
        self.enabled = self._is_sms_enabled()
        self.provider = self._get_sms_provider()
        
    def _is_sms_enabled(self) -> bool:
        """Check if SMS service is enabled in admin settings"""
        return AdminSettings.get_setting('sms_enabled', False)
    
    def _get_sms_provider(self) -> str:
        """Get configured SMS provider"""
        return AdminSettings.get_setting('sms_provider', 'twilio')
    
    def send_reminder(self, user_id: int, message: str) -> Dict:
        """
        Send SMS reminder to a user
        
        Args:
            user_id: ID of the user to send SMS to
            message: Message content
            
        Returns:
            dict: Result with success status and message ID or error
        """
        try:
            if not self.enabled:
                return {
                    'success': False,
                    'error': 'SMS service is disabled'
                }
            
            user = User.query.get(user_id)
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            # Get user's phone number from settings or profile
            phone_number = self._get_user_phone(user)
            if not phone_number:
                return {
                    'success': False,
                    'error': 'User has no phone number configured'
                }
            
            # Send SMS based on provider
            if self.provider == 'twilio':
                return self._send_twilio_sms(phone_number, message)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported SMS provider: {self.provider}'
                }
                
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_user_phone(self, user: User) -> Optional[str]:
        """Get user's phone number from profile or settings"""
        # TODO: Add phone number field to User model
        # For now, return None
        return None
    
    def _send_twilio_sms(self, phone_number: str, message: str) -> Dict:
        """Send SMS using Twilio"""
        try:
            # Get Twilio credentials from admin settings
            account_sid = AdminSettings.get_setting('twilio_account_sid')
            auth_token = AdminSettings.get_setting('twilio_auth_token')
            from_number = AdminSettings.get_setting('twilio_from_number')
            
            if not all([account_sid, auth_token, from_number]):
                return {
                    'success': False,
                    'error': 'Twilio credentials not configured'
                }
            
            # Import Twilio client (optional dependency)
            try:
                from twilio.rest import Client
            except ImportError:
                return {
                    'success': False,
                    'error': 'Twilio library not installed'
                }
            
            # Create Twilio client and send message
            client = Client(account_sid, auth_token)
            
            message = client.messages.create(
                body=message,
                from_=from_number,
                to=phone_number
            )
            
            logger.info(f"SMS sent successfully: {message.sid}")
            
            return {
                'success': True,
                'message_id': message.sid,
                'status': message.status
            }
            
        except Exception as e:
            logger.error(f"Twilio SMS failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_goal_reminder(self, goal_id: int) -> Dict:
        """Send reminder for a specific goal"""
        try:
            goal = Goal.query.get(goal_id)
            if not goal:
                return {
                    'success': False,
                    'error': 'Goal not found'
                }
            
            # Get message template
            from message_templates import get_goal_reminder_message
            message = get_goal_reminder_message(goal)
            
            # Send to goal owner
            return self.send_reminder(goal.owner_id or goal.user_id, message)
            
        except Exception as e:
            logger.error(f"Failed to send goal reminder: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_bulk_reminders(self) -> Dict:
        """Send bulk reminders for goals due soon"""
        try:
            # Get all users with pending goals
            from sqlalchemy import and_
            from datetime import timedelta
            
            tomorrow = datetime.utcnow().date() + timedelta(days=1)
            
            # Find goals due tomorrow
            due_goals = Goal.query.filter(
                and_(
                    Goal.target_date == tomorrow,
                    Goal.status.in_(['created', 'started', 'working'])
                )
            ).all()
            
            sent_count = 0
            failed_count = 0
            
            for goal in due_goals:
                result = self.send_goal_reminder(goal.id)
                if result['success']:
                    sent_count += 1
                else:
                    failed_count += 1
            
            return {
                'success': True,
                'sent': sent_count,
                'failed': failed_count,
                'total': len(due_goals)
            }
            
        except Exception as e:
            logger.error(f"Failed to send bulk reminders: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_sms_status(self) -> Dict:
        """Get SMS service status and configuration"""
        return {
            'enabled': self.enabled,
            'provider': self.provider,
            'configured': self._is_provider_configured(),
            'test_mode': AdminSettings.get_setting('sms_test_mode', False),
            'daily_limit': AdminSettings.get_setting('sms_daily_limit', 100),
            'sent_today': self._get_sent_count_today()
        }
    
    def _is_provider_configured(self) -> bool:
        """Check if the SMS provider is properly configured"""
        if self.provider == 'twilio':
            return all([
                AdminSettings.get_setting('twilio_account_sid'),
                AdminSettings.get_setting('twilio_auth_token'),
                AdminSettings.get_setting('twilio_from_number')
            ])
        return False
    
    def _get_sent_count_today(self) -> int:
        """Get count of SMS sent today"""
        # TODO: Implement SMS tracking in database
        return 0
    
    def test_sms(self, phone_number: str) -> Dict:
        """Send a test SMS"""
        test_message = "This is a test message from LetsGoal. Your SMS notifications are working!"
        
        if self.provider == 'twilio':
            return self._send_twilio_sms(phone_number, test_message)
        else:
            return {
                'success': False,
                'error': f'Unsupported SMS provider: {self.provider}'
            }

# Global SMS service instance
sms_service = SMSService()