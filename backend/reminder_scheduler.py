"""
Reminder Scheduler Service for LetsGoal Application

This module provides scheduled SMS reminder functionality using APScheduler.
It handles creating, scheduling, and sending various types of reminders based on
user goals, deadlines, and preferences.
"""

import os
import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from models import db, User, Goal, Subgoal, SmsReminder
from sms_service import sms_service

# Configure logging
logger = logging.getLogger(__name__)

class ReminderScheduler:
    """
    Scheduler service for managing SMS reminders
    """
    
    def __init__(self, database_url: str = None):
        """Initialize the reminder scheduler"""
        self.scheduler = None
        self.database_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///database/letsgoal.db')
        self.is_running = False
        
        # Message templates
        self.message_templates = {
            'deadline_24h': "⏰ Reminder: Your goal '{goal_title}' is due tomorrow! You're {progress}% complete. Keep going! 💪",
            'deadline_1h': "🚨 Your goal '{goal_title}' is due in 1 hour! Current progress: {progress}%. You've got this!",
            'daily_motivation': "🌟 Good morning! Remember to work on your goals today. You have {active_goals} active goals. Make today count! ✨",
            'progress_milestone': "🎉 Congratulations! You've reached {progress}% completion on '{goal_title}'. Keep up the excellent work!",
            'weekly_summary': "📊 Weekly Summary: You completed {completed_goals} goals and {completed_subgoals} tasks this week. Next week's focus: {upcoming_goals}",
            'subgoal_due': "📋 Task reminder: '{subgoal_title}' for goal '{goal_title}' is due {due_time}. Time to make progress!"
        }
        
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """Setup APScheduler with database persistence"""
        try:
            # Configure job store to use database
            jobstores = {
                'default': SQLAlchemyJobStore(url=self.database_url, tablename='apscheduler_jobs')
            }
            
            # Configure executors
            executors = {
                'default': ThreadPoolExecutor(max_workers=5)
            }
            
            # Job defaults
            job_defaults = {
                'coalesce': True,  # Combine multiple pending executions into one
                'max_instances': 1,  # Only one instance of each job at a time
                'misfire_grace_time': 30  # Grace period for missed jobs
            }
            
            # Create scheduler
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'
            )
            
            logger.info("Reminder scheduler configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup scheduler: {str(e)}")
            raise
    
    def start(self):
        """Start the scheduler"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                self.is_running = True
                logger.info("Reminder scheduler started")
                
                # Schedule daily cleanup job
                self._schedule_daily_cleanup()
                
                # Schedule weekly summary job
                self._schedule_weekly_summaries()
                
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            raise
    
    def stop(self):
        """Stop the scheduler"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                logger.info("Reminder scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}")
    
    def schedule_goal_deadline_reminders(self, goal_id: int):
        """
        Schedule deadline reminders for a goal
        
        Args:
            goal_id: ID of the goal to schedule reminders for
        """
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                goal = Goal.query.get(goal_id)
                if not goal or not goal.target_date:
                    return
                
                user = User.query.get(goal.user_id)
                if not user or not user.can_receive_sms():
                    return
                
                # Get user preferences
                preferences = user.get_sms_preferences()
                if not preferences.get('deadline_reminders', True):
                    return
                
                target_datetime = datetime.combine(goal.target_date, time(9, 0))  # 9 AM on target date
                now = datetime.utcnow()
                
                # Schedule 24-hour reminder
                reminder_24h = target_datetime - timedelta(hours=24)
                if reminder_24h > now:
                    self._create_and_schedule_reminder(
                        user_id=goal.user_id,
                        goal_id=goal.id,
                        reminder_type='deadline_24h',
                        scheduled_time=reminder_24h,
                        template_key='deadline_24h'
                    )
                
                # Schedule 1-hour reminder
                reminder_1h = target_datetime - timedelta(hours=1)
                if reminder_1h > now:
                    self._create_and_schedule_reminder(
                        user_id=goal.user_id,
                        goal_id=goal.id,
                        reminder_type='deadline_1h',
                        scheduled_time=reminder_1h,
                        template_key='deadline_1h'
                    )
                
                logger.info(f"Scheduled deadline reminders for goal {goal_id}")
                
        except Exception as e:
            logger.error(f"Error scheduling goal deadline reminders: {str(e)}")
    
    def schedule_subgoal_deadline_reminder(self, subgoal_id: int):
        """
        Schedule deadline reminder for a subgoal
        
        Args:
            subgoal_id: ID of the subgoal to schedule reminder for
        """
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                subgoal = Subgoal.query.get(subgoal_id)
                if not subgoal or not subgoal.target_date or subgoal.status == 'achieved':
                    return
                
                goal = Goal.query.get(subgoal.goal_id)
                user = User.query.get(goal.user_id)
                
                if not user or not user.can_receive_sms():
                    return
                
                # Get user preferences
                preferences = user.get_sms_preferences()
                if not preferences.get('deadline_reminders', True):
                    return
                
                target_datetime = datetime.combine(subgoal.target_date, time(9, 0))
                reminder_time = target_datetime - timedelta(hours=2)  # 2 hours before
                
                if reminder_time > datetime.utcnow():
                    self._create_and_schedule_reminder(
                        user_id=goal.user_id,
                        goal_id=goal.id,
                        subgoal_id=subgoal.id,
                        reminder_type='subgoal_due',
                        scheduled_time=reminder_time,
                        template_key='subgoal_due'
                    )
                    
                    logger.info(f"Scheduled subgoal deadline reminder for subgoal {subgoal_id}")
                
        except Exception as e:
            logger.error(f"Error scheduling subgoal deadline reminder: {str(e)}")
    
    def schedule_daily_motivation(self, user_id: int):
        """
        Schedule daily motivation messages for a user
        
        Args:
            user_id: ID of the user
        """
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                user = User.query.get(user_id)
                if not user or not user.can_receive_sms():
                    return
                
                preferences = user.get_sms_preferences()
                if not preferences.get('daily_motivation', False):
                    return
                
                # Get user's preferred time (default 9:00 AM)
                reminder_time_str = preferences.get('reminder_time', '09:00')
                hour, minute = map(int, reminder_time_str.split(':'))
                
                # Schedule daily job
                job_id = f"daily_motivation_{user_id}"
                
                # Remove existing job if it exists
                try:
                    self.scheduler.remove_job(job_id)
                except:
                    pass
                
                # Add new daily job
                self.scheduler.add_job(
                    func=self._send_daily_motivation,
                    args=[user_id],
                    trigger=CronTrigger(hour=hour, minute=minute),
                    id=job_id,
                    replace_existing=True
                )
                
                logger.info(f"Scheduled daily motivation for user {user_id} at {reminder_time_str}")
                
        except Exception as e:
            logger.error(f"Error scheduling daily motivation: {str(e)}")
    
    def schedule_progress_milestone_reminder(self, goal_id: int, milestone_percentage: int):
        """
        Schedule a progress milestone celebration reminder
        
        Args:
            goal_id: ID of the goal
            milestone_percentage: Progress percentage reached (25, 50, 75, 100)
        """
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                goal = Goal.query.get(goal_id)
                if not goal:
                    return
                
                user = User.query.get(goal.user_id)
                if not user or not user.can_receive_sms():
                    return
                
                preferences = user.get_sms_preferences()
                if not preferences.get('progress_updates', True):
                    return
                
                # Send immediately for milestone celebrations
                self._send_progress_milestone(goal_id, milestone_percentage)
                
        except Exception as e:
            logger.error(f"Error scheduling progress milestone reminder: {str(e)}")
    
    def _create_and_schedule_reminder(self, 
                                    user_id: int,
                                    reminder_type: str,
                                    scheduled_time: datetime,
                                    template_key: str,
                                    goal_id: Optional[int] = None,
                                    subgoal_id: Optional[int] = None):
        """
        Create a reminder record and schedule it
        
        Args:
            user_id: ID of the user
            reminder_type: Type of reminder
            scheduled_time: When to send the reminder
            template_key: Key for the message template
            goal_id: Optional goal ID
            subgoal_id: Optional subgoal ID
        """
        try:
            # Create reminder record
            reminder = SmsReminder(
                user_id=user_id,
                goal_id=goal_id,
                subgoal_id=subgoal_id,
                reminder_type=reminder_type,
                message_template=template_key,
                scheduled_time=scheduled_time
            )
            
            db.session.add(reminder)
            db.session.commit()
            
            # Schedule the job
            job_id = f"reminder_{reminder.id}"
            self.scheduler.add_job(
                func=self._send_scheduled_reminder,
                args=[reminder.id],
                trigger=DateTrigger(run_date=scheduled_time),
                id=job_id,
                replace_existing=True
            )
            
            logger.info(f"Created and scheduled reminder {reminder.id} for {scheduled_time}")
            
        except Exception as e:
            logger.error(f"Error creating reminder: {str(e)}")
    
    def _send_scheduled_reminder(self, reminder_id: int):
        """
        Send a scheduled reminder
        
        Args:
            reminder_id: ID of the reminder to send
        """
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                reminder = SmsReminder.query.get(reminder_id)
                if not reminder or reminder.status != 'pending':
                    return
                
                user = User.query.get(reminder.user_id)
                if not user or not user.can_receive_sms():
                    reminder.status = 'cancelled'
                    reminder.error_message = 'User cannot receive SMS'
                    db.session.commit()
                    return
                
                # Generate message content
                message_content = self._generate_message_content(reminder)
                
                # Send SMS
                success, result = sms_service.send_sms(
                    phone_number=user.phone_number,
                    message=message_content,
                    user_id=user.id,
                    message_type='reminder',
                    metadata={
                        'reminder_id': reminder.id,
                        'reminder_type': reminder.reminder_type,
                        'goal_id': reminder.goal_id,
                        'subgoal_id': reminder.subgoal_id
                    }
                )
                
                # Update reminder status
                if success:
                    reminder.status = 'sent'
                    reminder.sent_at = datetime.utcnow()
                else:
                    reminder.status = 'failed'
                    reminder.error_message = result
                
                db.session.commit()
                
                logger.info(f"Processed reminder {reminder_id}: {reminder.status}")
                
        except Exception as e:
            logger.error(f"Error sending scheduled reminder {reminder_id}: {str(e)}")
    
    def _send_daily_motivation(self, user_id: int):
        """
        Send daily motivation message
        
        Args:
            user_id: ID of the user
        """
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                user = User.query.get(user_id)
                if not user or not user.can_receive_sms():
                    return
                
                # Get user's active goals
                active_goals = Goal.query.filter(
                    Goal.user_id == user_id,
                    Goal.status.in_(['created', 'started', 'working']),
                    Goal.archived_date.is_(None)
                ).count()
                
                if active_goals == 0:
                    return  # Don't send motivation if no active goals
                
                # Generate motivation message
                template = self.message_templates['daily_motivation']
                message = template.format(active_goals=active_goals)
                
                # Send SMS
                sms_service.send_sms(
                    phone_number=user.phone_number,
                    message=message,
                    user_id=user.id,
                    message_type='reminder',
                    metadata={
                        'reminder_type': 'daily_motivation',
                        'active_goals': active_goals
                    }
                )
                
                logger.info(f"Sent daily motivation to user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending daily motivation to user {user_id}: {str(e)}")
    
    def _send_progress_milestone(self, goal_id: int, milestone_percentage: int):
        """
        Send progress milestone celebration message
        
        Args:
            goal_id: ID of the goal
            milestone_percentage: Progress percentage reached
        """
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                goal = Goal.query.get(goal_id)
                if not goal:
                    return
                
                user = User.query.get(goal.user_id)
                if not user or not user.can_receive_sms():
                    return
                
                # Generate milestone message
                template = self.message_templates['progress_milestone']
                message = template.format(
                    progress=milestone_percentage,
                    goal_title=goal.title[:50]  # Limit title length
                )
                
                # Send SMS
                sms_service.send_sms(
                    phone_number=user.phone_number,
                    message=message,
                    user_id=user.id,
                    message_type='reminder',
                    metadata={
                        'reminder_type': 'progress_milestone',
                        'goal_id': goal_id,
                        'milestone_percentage': milestone_percentage
                    }
                )
                
                logger.info(f"Sent progress milestone message for goal {goal_id} ({milestone_percentage}%)")
                
        except Exception as e:
            logger.error(f"Error sending progress milestone message: {str(e)}")
    
    def _generate_message_content(self, reminder: SmsReminder) -> str:
        """
        Generate message content for a reminder
        
        Args:
            reminder: SmsReminder object
            
        Returns:
            Generated message content
        """
        try:
            template_key = reminder.message_template
            template = self.message_templates.get(template_key, "Reminder: Don't forget about your goals!")
            
            # Get goal and subgoal if applicable
            goal = Goal.query.get(reminder.goal_id) if reminder.goal_id else None
            subgoal = Subgoal.query.get(reminder.subgoal_id) if reminder.subgoal_id else None
            
            # Prepare template variables
            variables = {}
            
            if goal:
                variables.update({
                    'goal_title': goal.title[:50],  # Limit length for SMS
                    'progress': goal.calculate_progress()
                })
            
            if subgoal:
                variables.update({
                    'subgoal_title': subgoal.title[:50],
                    'goal_title': goal.title[:30] if goal else '',
                    'due_time': 'soon' if subgoal.target_date else 'today'
                })
            
            # Format the message
            try:
                message = template.format(**variables)
            except KeyError:
                # Fallback if template variables don't match
                message = template
            
            return message
            
        except Exception as e:
            logger.error(f"Error generating message content: {str(e)}")
            return "Reminder: Don't forget about your goals! 🎯"
    
    def _schedule_daily_cleanup(self):
        """Schedule daily cleanup of old reminders and logs"""
        self.scheduler.add_job(
            func=self._cleanup_old_data,
            trigger=CronTrigger(hour=2, minute=0),  # 2 AM daily
            id='daily_cleanup',
            replace_existing=True
        )
    
    def _schedule_weekly_summaries(self):
        """Schedule weekly summary messages"""
        self.scheduler.add_job(
            func=self._send_weekly_summaries,
            trigger=CronTrigger(day_of_week='sun', hour=19, minute=0),  # Sunday 7 PM
            id='weekly_summaries',
            replace_existing=True
        )
    
    def _cleanup_old_data(self):
        """Clean up old reminder and log data"""
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                # Delete old completed/failed reminders (older than 30 days)
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                old_reminders = SmsReminder.query.filter(
                    SmsReminder.status.in_(['sent', 'failed', 'cancelled']),
                    SmsReminder.created_at < cutoff_date
                ).delete()
                
                db.session.commit()
                
                if old_reminders > 0:
                    logger.info(f"Cleaned up {old_reminders} old reminders")
                
        except Exception as e:
            logger.error(f"Error during daily cleanup: {str(e)}")
    
    def _send_weekly_summaries(self):
        """Send weekly summary messages to users who have enabled them"""
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                # Get users who want weekly summaries
                users = User.query.filter(
                    User.sms_enabled == True,
                    User.phone_verified == True
                ).all()
                
                for user in users:
                    preferences = user.get_sms_preferences()
                    if preferences.get('weekly_summary', False):
                        self._send_user_weekly_summary(user.id)
                
        except Exception as e:
            logger.error(f"Error sending weekly summaries: {str(e)}")
    
    def _send_user_weekly_summary(self, user_id: int):
        """
        Send weekly summary to a specific user
        
        Args:
            user_id: ID of the user
        """
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                user = User.query.get(user_id)
                if not user or not user.can_receive_sms():
                    return
                
                # Calculate weekly stats
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                completed_goals = Goal.query.filter(
                    Goal.user_id == user_id,
                    Goal.status == 'completed',
                    Goal.achieved_date >= week_ago.date()
                ).count()
                
                completed_subgoals = Subgoal.query.join(Goal).filter(
                    Goal.user_id == user_id,
                    Subgoal.status == 'achieved',
                    Subgoal.achieved_date >= week_ago.date()
                ).count()
                
                upcoming_goals = Goal.query.filter(
                    Goal.user_id == user_id,
                    Goal.target_date <= (datetime.utcnow() + timedelta(days=7)).date(),
                    Goal.status.in_(['created', 'started', 'working'])
                ).count()
                
                # Generate summary message
                template = self.message_templates['weekly_summary']
                message = template.format(
                    completed_goals=completed_goals,
                    completed_subgoals=completed_subgoals,
                    upcoming_goals=upcoming_goals
                )
                
                # Send SMS
                sms_service.send_sms(
                    phone_number=user.phone_number,
                    message=message,
                    user_id=user.id,
                    message_type='reminder',
                    metadata={
                        'reminder_type': 'weekly_summary',
                        'completed_goals': completed_goals,
                        'completed_subgoals': completed_subgoals,
                        'upcoming_goals': upcoming_goals
                    }
                )
                
                logger.info(f"Sent weekly summary to user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending weekly summary to user {user_id}: {str(e)}")
    
    def cancel_goal_reminders(self, goal_id: int):
        """
        Cancel all pending reminders for a goal
        
        Args:
            goal_id: ID of the goal
        """
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                # Cancel database records
                pending_reminders = SmsReminder.query.filter(
                    SmsReminder.goal_id == goal_id,
                    SmsReminder.status == 'pending'
                ).all()
                
                for reminder in pending_reminders:
                    reminder.status = 'cancelled'
                    
                    # Remove from scheduler
                    job_id = f"reminder_{reminder.id}"
                    try:
                        self.scheduler.remove_job(job_id)
                    except:
                        pass  # Job might not exist
                
                db.session.commit()
                
                logger.info(f"Cancelled {len(pending_reminders)} reminders for goal {goal_id}")
                
        except Exception as e:
            logger.error(f"Error cancelling goal reminders: {str(e)}")

# Global scheduler instance
reminder_scheduler = ReminderScheduler()