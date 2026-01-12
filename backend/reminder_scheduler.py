"""
Reminder Scheduler Module
Handles scheduling and sending of automated reminders for goals and subgoals
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import and_, or_
from models import db, User, Goal, Subgoal, AdminSettings
from sms_service import sms_service
from message_templates import message_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReminderScheduler:
    """Scheduler for automated reminders"""
    
    def __init__(self):
        self.enabled = self._is_scheduler_enabled()
        
    def _is_scheduler_enabled(self) -> bool:
        """Check if reminder scheduler is enabled"""
        return AdminSettings.get_setting('reminder_scheduler_enabled', True)
    
    def run_scheduled_reminders(self) -> Dict:
        """
        Main method to run all scheduled reminders
        Called by cron job or scheduled task
        
        Returns:
            dict: Summary of reminders sent
        """
        if not self.enabled:
            logger.info("Reminder scheduler is disabled")
            return {'success': False, 'reason': 'Scheduler disabled'}
        
        logger.info("Starting scheduled reminder run")
        
        results = {
            'deadline_24h': self._send_24h_deadline_reminders(),
            'deadline_1h': self._send_1h_deadline_reminders(),
            'daily_motivation': self._send_daily_motivation(),
            'weekly_summary': self._send_weekly_summaries() if datetime.utcnow().weekday() == 0 else {'sent': 0},
            'overdue': self._send_overdue_reminders(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        total_sent = sum(r.get('sent', 0) for r in results.values() if isinstance(r, dict))
        logger.info(f"Scheduled reminder run complete. Total sent: {total_sent}")
        
        return {
            'success': True,
            'total_sent': total_sent,
            'details': results
        }
    
    def _send_24h_deadline_reminders(self) -> Dict:
        """Send reminders for goals due in 24 hours"""
        try:
            tomorrow = datetime.utcnow().date() + timedelta(days=1)
            
            # Find goals due tomorrow
            goals_due = Goal.query.filter(
                and_(
                    Goal.target_date == tomorrow,
                    Goal.status.in_(['created', 'started', 'working']),
                    Goal.archived_date.is_(None)
                )
            ).all()
            
            sent_count = 0
            failed_count = 0
            
            for goal in goals_due:
                user_id = goal.owner_id or goal.user_id
                
                # Check if user has reminders enabled
                if not self._user_has_reminders_enabled(user_id):
                    continue
                
                # Generate and send message
                message = message_engine.generate_message(
                    message_type='deadline_24h',
                    user_id=user_id,
                    goal_id=goal.id
                )
                
                result = sms_service.send_reminder(user_id, message)
                
                if result['success']:
                    sent_count += 1
                    self._log_reminder_sent(user_id, goal.id, 'deadline_24h')
                else:
                    failed_count += 1
                    logger.error(f"Failed to send 24h reminder for goal {goal.id}: {result['error']}")
            
            return {
                'sent': sent_count,
                'failed': failed_count,
                'total_due': len(goals_due)
            }
            
        except Exception as e:
            logger.error(f"Error in 24h deadline reminders: {str(e)}")
            return {'sent': 0, 'failed': 0, 'error': str(e)}
    
    def _send_1h_deadline_reminders(self) -> Dict:
        """Send urgent reminders for goals due in 1 hour"""
        try:
            # Only run during reasonable hours (8 AM - 9 PM)
            current_hour = datetime.utcnow().hour
            if current_hour < 8 or current_hour > 21:
                return {'sent': 0, 'skipped': 'Outside notification hours'}
            
            one_hour_later = datetime.utcnow() + timedelta(hours=1)
            
            # Find goals due within the next hour
            # Note: This requires time support in target_date field
            goals_urgent = Goal.query.filter(
                and_(
                    Goal.target_date == one_hour_later.date(),
                    Goal.status.in_(['created', 'started', 'working']),
                    Goal.archived_date.is_(None)
                )
            ).all()
            
            sent_count = 0
            failed_count = 0
            
            for goal in goals_urgent:
                user_id = goal.owner_id or goal.user_id
                
                # Check if user has urgent reminders enabled
                if not self._user_has_urgent_reminders_enabled(user_id):
                    continue
                
                # Check if we already sent a 1h reminder today
                if self._already_sent_today(user_id, goal.id, 'deadline_1h'):
                    continue
                
                # Generate and send message
                message = message_engine.generate_message(
                    message_type='deadline_1h',
                    user_id=user_id,
                    goal_id=goal.id
                )
                
                result = sms_service.send_reminder(user_id, message)
                
                if result['success']:
                    sent_count += 1
                    self._log_reminder_sent(user_id, goal.id, 'deadline_1h')
                else:
                    failed_count += 1
            
            return {
                'sent': sent_count,
                'failed': failed_count,
                'total_urgent': len(goals_urgent)
            }
            
        except Exception as e:
            logger.error(f"Error in 1h deadline reminders: {str(e)}")
            return {'sent': 0, 'failed': 0, 'error': str(e)}
    
    def _send_daily_motivation(self) -> Dict:
        """Send daily motivational messages to active users"""
        try:
            # Only send at configured hour (default 8 AM)
            motivation_hour = AdminSettings.get_setting('daily_motivation_hour', 8)
            current_hour = datetime.utcnow().hour
            
            if current_hour != motivation_hour:
                return {'sent': 0, 'skipped': f'Not motivation hour ({motivation_hour})'}
            
            # Find users with active goals who want daily motivation
            active_users = db.session.query(User).join(Goal).filter(
                and_(
                    Goal.status.in_(['created', 'started', 'working']),
                    Goal.archived_date.is_(None),
                    User.id == Goal.user_id
                )
            ).distinct().all()
            
            sent_count = 0
            failed_count = 0
            
            for user in active_users:
                if not self._user_has_daily_motivation_enabled(user.id):
                    continue
                
                # Check if already sent today
                if self._already_sent_today(user.id, None, 'daily_motivation'):
                    continue
                
                # Count active goals
                active_goals = Goal.query.filter(
                    and_(
                        Goal.user_id == user.id,
                        Goal.status.in_(['created', 'started', 'working']),
                        Goal.archived_date.is_(None)
                    )
                ).count()
                
                # Generate and send message
                message = message_engine.generate_message(
                    message_type='daily_motivation',
                    user_id=user.id,
                    custom_data={'active_goals': active_goals}
                )
                
                result = sms_service.send_reminder(user.id, message)
                
                if result['success']:
                    sent_count += 1
                    self._log_reminder_sent(user.id, None, 'daily_motivation')
                else:
                    failed_count += 1
            
            return {
                'sent': sent_count,
                'failed': failed_count,
                'total_active_users': len(active_users)
            }
            
        except Exception as e:
            logger.error(f"Error in daily motivation: {str(e)}")
            return {'sent': 0, 'failed': 0, 'error': str(e)}
    
    def _send_weekly_summaries(self) -> Dict:
        """Send weekly summary messages (runs on Mondays)"""
        try:
            # Get all users who want weekly summaries
            users = User.query.all()
            
            sent_count = 0
            failed_count = 0
            
            for user in users:
                if not self._user_has_weekly_summary_enabled(user.id):
                    continue
                
                # Calculate weekly stats
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                completed_goals = Goal.query.filter(
                    and_(
                        Goal.user_id == user.id,
                        Goal.status == 'completed',
                        Goal.achieved_date >= week_ago.date()
                    )
                ).count()
                
                completed_subgoals = Subgoal.query.join(Goal).filter(
                    and_(
                        Goal.user_id == user.id,
                        Subgoal.status == 'achieved',
                        Subgoal.achieved_date >= week_ago.date()
                    )
                ).count()
                
                # Skip if no activity
                if completed_goals == 0 and completed_subgoals == 0:
                    continue
                
                # Generate and send message
                message = message_engine.generate_message(
                    message_type='weekly_summary',
                    user_id=user.id,
                    custom_data={
                        'completed_goals': completed_goals,
                        'completed_subgoals': completed_subgoals
                    }
                )
                
                result = sms_service.send_reminder(user.id, message)
                
                if result['success']:
                    sent_count += 1
                    self._log_reminder_sent(user.id, None, 'weekly_summary')
                else:
                    failed_count += 1
            
            return {
                'sent': sent_count,
                'failed': failed_count,
                'total_users': len(users)
            }
            
        except Exception as e:
            logger.error(f"Error in weekly summaries: {str(e)}")
            return {'sent': 0, 'failed': 0, 'error': str(e)}
    
    def _send_overdue_reminders(self) -> Dict:
        """Send reminders for overdue goals"""
        try:
            # Find overdue goals
            overdue_goals = Goal.query.filter(
                and_(
                    Goal.target_date < datetime.utcnow().date(),
                    Goal.status.in_(['created', 'started', 'working']),
                    Goal.archived_date.is_(None)
                )
            ).all()
            
            sent_count = 0
            failed_count = 0
            
            for goal in overdue_goals:
                user_id = goal.owner_id or goal.user_id
                
                # Only send overdue reminders once per week per goal
                if self._sent_within_days(user_id, goal.id, 'goal_overdue', 7):
                    continue
                
                # Generate and send message
                message = message_engine.generate_message(
                    message_type='goal_overdue',
                    user_id=user_id,
                    goal_id=goal.id
                )
                
                result = sms_service.send_reminder(user_id, message)
                
                if result['success']:
                    sent_count += 1
                    self._log_reminder_sent(user_id, goal.id, 'goal_overdue')
                else:
                    failed_count += 1
            
            return {
                'sent': sent_count,
                'failed': failed_count,
                'total_overdue': len(overdue_goals)
            }
            
        except Exception as e:
            logger.error(f"Error in overdue reminders: {str(e)}")
            return {'sent': 0, 'failed': 0, 'error': str(e)}
    
    def _user_has_reminders_enabled(self, user_id: int) -> bool:
        """Check if user has reminders enabled"""
        # TODO: Add user preference tracking
        # For now, return True for all users
        return True
    
    def _user_has_urgent_reminders_enabled(self, user_id: int) -> bool:
        """Check if user has urgent reminders enabled"""
        # TODO: Add user preference tracking
        return True
    
    def _user_has_daily_motivation_enabled(self, user_id: int) -> bool:
        """Check if user has daily motivation enabled"""
        # TODO: Add user preference tracking
        return True
    
    def _user_has_weekly_summary_enabled(self, user_id: int) -> bool:
        """Check if user has weekly summary enabled"""
        # TODO: Add user preference tracking
        return True
    
    def _already_sent_today(self, user_id: int, goal_id: Optional[int], reminder_type: str) -> bool:
        """Check if reminder was already sent today"""
        # TODO: Implement reminder tracking in database
        # For now, return False to allow sending
        return False
    
    def _sent_within_days(self, user_id: int, goal_id: int, reminder_type: str, days: int) -> bool:
        """Check if reminder was sent within specified days"""
        # TODO: Implement reminder tracking in database
        return False
    
    def _log_reminder_sent(self, user_id: int, goal_id: Optional[int], reminder_type: str):
        """Log that a reminder was sent"""
        # TODO: Implement reminder tracking in database
        logger.info(f"Reminder sent: type={reminder_type}, user={user_id}, goal={goal_id}")
    
    def send_test_reminder(self, user_id: int, reminder_type: str) -> Dict:
        """Send a test reminder of specified type"""
        try:
            # Find a sample goal for the user
            sample_goal = Goal.query.filter_by(user_id=user_id).first()
            
            # Generate message
            message = message_engine.generate_message(
                message_type=reminder_type,
                user_id=user_id,
                goal_id=sample_goal.id if sample_goal else None,
                custom_data={
                    'active_goals': 3,
                    'completed_goals': 2,
                    'completed_subgoals': 5
                }
            )
            
            # Send reminder
            result = sms_service.send_reminder(user_id, message)
            
            return {
                'success': result['success'],
                'message': message,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error sending test reminder: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Global reminder scheduler instance
reminder_scheduler = ReminderScheduler()