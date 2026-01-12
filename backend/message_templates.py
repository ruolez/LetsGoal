"""
Message Templates and Dynamic Content Generation for SMS Reminders

This module provides dynamic message generation for SMS reminders, integrating
with the existing motivational quotes system and personalizing messages based
on user goals and progress.
"""

import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from models import db, User, Goal, Subgoal

# Configure logging
logger = logging.getLogger(__name__)

class MessageTemplateEngine:
    """
    Engine for generating dynamic SMS messages with personalization
    """
    
    def __init__(self):
        """Initialize the message template engine"""
        self.motivational_quotes = self._load_motivational_quotes()
        self.templates = self._initialize_templates()
        self.emojis = {
            'goal': ['🎯', '🏆', '⭐', '🌟', '💫'],
            'deadline': ['⏰', '🚨', '⏳', '🕐', '📅'],
            'celebration': ['🎉', '🎊', '🥳', '👏', '🔥'],
            'motivation': ['💪', '🚀', '⚡', '🌈', '✨'],
            'progress': ['📈', '📊', '⬆️', '🔥', '💯'],
            'daily': ['☀️', '🌅', '🌞', '🌸', '🌺'],
            'weekly': ['📅', '📋', '📊', '🗓️', '📆']
        }
    
    def _load_motivational_quotes(self) -> List[str]:
        """Load motivational quotes for SMS integration"""
        return [
            "Success is not final, failure is not fatal: it is the courage to continue that counts.",
            "The way to get started is to quit talking and begin doing.",
            "Don't be afraid to give up the good to go for the great.",
            "Innovation distinguishes between a leader and a follower.",
            "Your limitation—it's only your imagination.",
            "Push yourself, because no one else is going to do it for you.",
            "Great things never come from comfort zones.",
            "Dream it. Wish it. Do it.",
            "Success doesn't just find you. You have to go out and get it.",
            "The harder you work for something, the greater you'll feel when you achieve it.",
            "Dream bigger. Do bigger.",
            "Don't stop when you're tired. Stop when you're done.",
            "Wake up with determination. Go to bed with satisfaction.",
            "Do something today that your future self will thank you for.",
            "Little progress is still progress.",
            "Great things happen to those who don't stop believing, trying, working and learning.",
            "If you still look good at the end of your workout, you didn't train hard enough.",
            "Some people want it to happen, some wish it would happen, others make it happen.",
            "Don't wait for opportunity. Create it.",
            "Sometimes we're tested not to show our weaknesses, but to discover our strengths.",
            "The key to success is to focus on goals, not obstacles.",
            "Dream it. Believe it. Build it.",
            "Your only limit is your mind.",
            "Excellence is not a skill, it's an attitude.",
            "Stay focused and never give up.",
            "What seems impossible today will one day become your warm-up.",
            "Turn your wounds into wisdom.",
            "The comeback is always stronger than the setback.",
            "Believe you can and you're halfway there.",
            "Champions keep playing until they get it right."
        ]
    
    def _initialize_templates(self) -> Dict[str, Dict]:
        """Initialize message templates with variations"""
        return {
            'deadline_24h': {
                'templates': [
                    "{emoji} Your goal '{goal_title}' is due tomorrow! You're {progress}% complete. {motivation_text}",
                    "{emoji} 24-hour reminder: '{goal_title}' deadline approaching! Current progress: {progress}%. You've got this!",
                    "{emoji} Almost there! '{goal_title}' is due tomorrow. You're {progress}% done. Keep pushing forward!",
                    "{emoji} Final stretch! '{goal_title}' deadline tomorrow. {progress}% complete. Finish strong!"
                ],
                'emoji_category': 'deadline'
            },
            'deadline_1h': {
                'templates': [
                    "{emoji} URGENT: '{goal_title}' is due in 1 hour! Current progress: {progress}%. Sprint to the finish!",
                    "{emoji} Last call! '{goal_title}' deadline in 60 minutes. You're {progress}% there. You can do this!",
                    "{emoji} Final hour for '{goal_title}'! {progress}% complete. Make every minute count!",
                    "{emoji} One hour left! '{goal_title}' needs your attention. Current: {progress}%. Let's finish this!"
                ],
                'emoji_category': 'deadline'
            },
            'daily_motivation': {
                'templates': [
                    "{emoji} Good morning! You have {active_goals} active goal{s}. Today is your day to make progress! {quote}",
                    "{emoji} Rise and shine! {active_goals} goal{s} await{s_verb} your attention. Make today count! {quote}",
                    "{emoji} New day, new opportunities! Focus on your {active_goals} goal{s} today. {quote}",
                    "{emoji} Morning champion! Time to work on your {active_goals} goal{s}. Success starts now! {quote}",
                    "{emoji} Today's agenda: Crush your {active_goals} goal{s}! {quote}"
                ],
                'emoji_category': 'daily'
            },
            'progress_milestone': {
                'templates': [
                    "{emoji} Milestone achieved! You've reached {progress}% on '{goal_title}'. Incredible progress!",
                    "{emoji} Way to go! {progress}% completion on '{goal_title}'. You're crushing it!",
                    "{emoji} Amazing work! '{goal_title}' is {progress}% complete. Keep up the momentum!",
                    "{emoji} Celebration time! You've hit {progress}% on '{goal_title}'. Outstanding effort!",
                    "{emoji} Progress alert! '{goal_title}' is now {progress}% done. You're on fire!"
                ],
                'emoji_category': 'celebration'
            },
            'weekly_summary': {
                'templates': [
                    "{emoji} Week recap: {completed_goals} goal{goal_s} completed, {completed_subgoals} task{task_s} done! {upcoming_text}",
                    "{emoji} Weekly wins: {completed_goals} goal{goal_s} ✓, {completed_subgoals} task{task_s} ✓! {upcoming_text}",
                    "{emoji} This week's victories: {completed_goals} goal{goal_s} and {completed_subgoals} task{task_s} completed! {upcoming_text}",
                    "{emoji} Week summary: {completed_goals} goal{goal_s} achieved, {completed_subgoals} task{task_s} finished! {upcoming_text}"
                ],
                'emoji_category': 'weekly'
            },
            'subgoal_due': {
                'templates': [
                    "{emoji} Task reminder: '{subgoal_title}' for '{goal_title}' is due {due_time}. Time to tackle it!",
                    "{emoji} Don't forget: '{subgoal_title}' needs completion {due_time}. You've got this!",
                    "{emoji} Heads up! '{subgoal_title}' for '{goal_title}' is due {due_time}. Let's do this!",
                    "{emoji} Task alert: '{subgoal_title}' deadline {due_time}. Time to make progress!"
                ],
                'emoji_category': 'goal'
            },
            'goal_completed': {
                'templates': [
                    "{emoji} GOAL COMPLETED! '{goal_title}' is officially done! Time to celebrate your success!",
                    "{emoji} Victory! You've completed '{goal_title}'! Amazing work, champion!",
                    "{emoji} Goal achieved! '{goal_title}' is finished! You should be proud of this accomplishment!",
                    "{emoji} Success! '{goal_title}' is complete! Your dedication has paid off!"
                ],
                'emoji_category': 'celebration'
            },
            'goal_overdue': {
                'templates': [
                    "{emoji} '{goal_title}' is overdue. No worries - let's get back on track! Progress over perfection.",
                    "{emoji} Gentle reminder: '{goal_title}' passed its deadline. Ready for a fresh start?",
                    "{emoji} '{goal_title}' needs attention. Every expert was once a beginner. Keep going!",
                    "{emoji} Time to revisit '{goal_title}'. Success is a journey, not a destination."
                ],
                'emoji_category': 'motivation'
            },
            'streak_reminder': {
                'templates': [
                    "{emoji} You're on a {streak_days}-day streak! Keep the momentum going with your goals!",
                    "{emoji} {streak_days} days in a row! Your consistency is paying off. Stay strong!",
                    "{emoji} Streak alert: {streak_days} consecutive days! You're building great habits!",
                    "{emoji} {streak_days}-day streak continues! Your future self thanks you!"
                ],
                'emoji_category': 'progress'
            }
        }
    
    def generate_message(self, 
                        message_type: str,
                        user_id: int,
                        goal_id: Optional[int] = None,
                        subgoal_id: Optional[int] = None,
                        custom_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a personalized SMS message
        
        Args:
            message_type: Type of message to generate
            user_id: ID of the user
            goal_id: Optional goal ID
            subgoal_id: Optional subgoal ID
            custom_data: Additional data for message generation
            
        Returns:
            Generated message string
        """
        try:
            # Get template configuration
            template_config = self.templates.get(message_type)
            if not template_config:
                return self._fallback_message(message_type)
            
            # Select random template
            templates = template_config['templates']
            template = random.choice(templates)
            
            # Get emoji
            emoji_category = template_config['emoji_category']
            emoji = random.choice(self.emojis[emoji_category])
            
            # Prepare message variables
            variables = self._prepare_variables(
                user_id=user_id,
                goal_id=goal_id,
                subgoal_id=subgoal_id,
                message_type=message_type,
                custom_data=custom_data or {}
            )
            
            # Add emoji to variables
            variables['emoji'] = emoji
            
            # Format the message
            message = template.format(**variables)
            
            # Ensure message fits SMS constraints (160 characters recommended)
            if len(message) > 160:
                message = self._truncate_message(message, template, variables)
            
            logger.info(f"Generated {message_type} message for user {user_id}: {len(message)} chars")
            return message
        
        except Exception as e:
            logger.error(f"Error generating message: {str(e)}")
            return self._fallback_message(message_type)
    
    def _prepare_variables(self,
                          user_id: int,
                          goal_id: Optional[int],
                          subgoal_id: Optional[int],
                          message_type: str,
                          custom_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare variables for message template formatting
        
        Args:
            user_id: ID of the user
            goal_id: Optional goal ID
            subgoal_id: Optional subgoal ID
            message_type: Type of message
            custom_data: Additional custom data
            
        Returns:
            Dictionary of template variables
        """
        variables = custom_data.copy()
        
        try:
            # Get user data
            user = User.query.get(user_id)
            if user:
                variables['user_name'] = user.username
            
            # Get goal data
            if goal_id:
                goal = Goal.query.get(goal_id)
                if goal:
                    variables.update({
                        'goal_title': self._truncate_text(goal.title, 40),
                        'progress': goal.calculate_progress(),
                        'goal_status': goal.status
                    })
            
            # Get subgoal data
            if subgoal_id:
                subgoal = Subgoal.query.get(subgoal_id)
                if subgoal:
                    variables.update({
                        'subgoal_title': self._truncate_text(subgoal.title, 30),
                        'subgoal_status': subgoal.status
                    })
                    
                    # Determine due time text
                    if subgoal.target_date:
                        days_until = (subgoal.target_date - datetime.utcnow().date()).days
                        if days_until == 0:
                            variables['due_time'] = 'today'
                        elif days_until == 1:
                            variables['due_time'] = 'tomorrow'
                        elif days_until > 1:
                            variables['due_time'] = f'in {days_until} days'
                        else:
                            variables['due_time'] = f'{abs(days_until)} days ago'
                    else:
                        variables['due_time'] = 'soon'
            
            # Add message-specific variables
            self._add_message_specific_variables(variables, message_type, user_id)
            
            # Add grammatical helpers
            self._add_grammatical_helpers(variables)
            
        except Exception as e:
            logger.error(f"Error preparing variables: {str(e)}")
        
        return variables
    
    def _add_message_specific_variables(self, variables: Dict[str, Any], message_type: str, user_id: int):
        """Add variables specific to message type"""
        try:
            if message_type == 'daily_motivation':
                # Add motivational quote
                variables['quote'] = random.choice(self.motivational_quotes)
                
                # Get active goals count
                if 'active_goals' not in variables:
                    active_goals = Goal.query.filter(
                        Goal.user_id == user_id,
                        Goal.status.in_(['created', 'started', 'working']),
                        Goal.archived_date.is_(None)
                    ).count()
                    variables['active_goals'] = active_goals
            
            elif message_type == 'weekly_summary':
                # Calculate weekly stats if not provided
                if 'completed_goals' not in variables:
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
                    
                    variables.update({
                        'completed_goals': completed_goals,
                        'completed_subgoals': completed_subgoals,
                        'upcoming_goals': upcoming_goals
                    })
                
                # Add upcoming text
                upcoming = variables.get('upcoming_goals', 0)
                if upcoming > 0:
                    variables['upcoming_text'] = f"Next week: {upcoming} goal{'s' if upcoming != 1 else ''} due."
                else:
                    variables['upcoming_text'] = "Great work this week!"
            
            elif message_type in ['deadline_24h', 'deadline_1h', 'progress_milestone']:
                # Add motivational text for deadline reminders
                if 'motivation_text' not in variables:
                    motivational_phrases = [
                        "You've got this!",
                        "Almost there!",
                        "Keep pushing!",
                        "You're so close!",
                        "Finish strong!",
                        "Make it happen!",
                        "Success awaits!",
                        "You can do it!"
                    ]
                    variables['motivation_text'] = random.choice(motivational_phrases)
            
        except Exception as e:
            logger.error(f"Error adding message-specific variables: {str(e)}")
    
    def _add_grammatical_helpers(self, variables: Dict[str, Any]):
        """Add grammatical helper variables for proper pluralization"""
        # Goal pluralization
        goal_count = variables.get('active_goals', variables.get('completed_goals', 1))
        variables['s'] = 's' if goal_count != 1 else ''
        variables['s_verb'] = '' if goal_count != 1 else 's'
        variables['goal_s'] = 's' if variables.get('completed_goals', 1) != 1 else ''
        
        # Task pluralization
        task_count = variables.get('completed_subgoals', 1)
        variables['task_s'] = 's' if task_count != 1 else ''
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to fit within specified length"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def _truncate_message(self, message: str, template: str, variables: Dict[str, Any]) -> str:
        """Truncate message to fit SMS constraints while preserving key information"""
        if len(message) <= 160:
            return message
        
        # Try shorter versions of dynamic content
        shortened_variables = variables.copy()
        
        # Shorten goal title if present
        if 'goal_title' in variables:
            shortened_variables['goal_title'] = self._truncate_text(variables['goal_title'], 25)
        
        # Shorten subgoal title if present
        if 'subgoal_title' in variables:
            shortened_variables['subgoal_title'] = self._truncate_text(variables['subgoal_title'], 20)
        
        # Remove quote for length if present
        if 'quote' in variables:
            shortened_variables['quote'] = ""
        
        # Remove motivation text if present
        if 'motivation_text' in variables:
            shortened_variables['motivation_text'] = ""
        
        try:
            shortened_message = template.format(**shortened_variables)
            if len(shortened_message) <= 160:
                return shortened_message
        except:
            pass
        
        # Final fallback: hard truncate
        return message[:157] + "..."
    
    def _fallback_message(self, message_type: str) -> str:
        """Provide fallback message if generation fails"""
        fallbacks = {
            'deadline_24h': "⏰ Goal deadline reminder: Don't forget to work on your goals today!",
            'deadline_1h': "🚨 Goal deadline in 1 hour! Time to focus and finish strong!",
            'daily_motivation': "🌟 Good morning! Today is a great day to make progress on your goals!",
            'progress_milestone': "🎉 Great progress on your goal! Keep up the excellent work!",
            'weekly_summary': "📊 Weekly check-in: How did your goals go this week?",
            'subgoal_due': "📋 Task reminder: Don't forget about your pending tasks!",
            'goal_completed': "🏆 Congratulations on completing your goal!",
            'goal_overdue': "💪 Your goal needs attention. Ready to get back on track?",
            'streak_reminder': "🔥 Keep your momentum going with your goals!"
        }
        
        return fallbacks.get(message_type, "🎯 LetsGoal reminder: Don't forget about your goals!")
    
    def get_available_message_types(self) -> List[str]:
        """Get list of available message types"""
        return list(self.templates.keys())
    
    def preview_message(self, 
                       message_type: str,
                       sample_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a preview of a message type with sample data
        
        Args:
            message_type: Type of message to preview
            sample_data: Sample data for preview
            
        Returns:
            Dictionary with preview information
        """
        try:
            template_config = self.templates.get(message_type)
            if not template_config:
                return {'error': f'Unknown message type: {message_type}'}
            
            # Use sample data or defaults
            if sample_data is None:
                sample_data = {
                    'goal_title': 'Complete Project X',
                    'progress': 75,
                    'active_goals': 3,
                    'completed_goals': 2,
                    'completed_subgoals': 5,
                    'upcoming_goals': 1,
                    'subgoal_title': 'Review documentation',
                    'due_time': 'today',
                    'streak_days': 7
                }
            
            # Add required variables
            sample_data.update({
                'emoji': random.choice(self.emojis[template_config['emoji_category']]),
                's': 's',
                's_verb': '',
                'goal_s': 's',
                'task_s': 's',
                'motivation_text': 'You can do it!',
                'quote': random.choice(self.motivational_quotes[:5]),
                'upcoming_text': 'Next week: 1 goal due.'
            })
            
            # Generate all template variations
            previews = []
            for template in template_config['templates']:
                try:
                    message = template.format(**sample_data)
                    previews.append({
                        'template': template,
                        'message': message,
                        'length': len(message),
                        'fits_sms': len(message) <= 160
                    })
                except KeyError as e:
                    previews.append({
                        'template': template,
                        'error': f'Missing variable: {str(e)}',
                        'length': 0,
                        'fits_sms': False
                    })
            
            return {
                'message_type': message_type,
                'emoji_category': template_config['emoji_category'],
                'template_count': len(template_config['templates']),
                'previews': previews
            }
        
        except Exception as e:
            logger.error(f"Error generating preview: {str(e)}")
            return {'error': f'Preview generation failed: {str(e)}'}

# Global message template engine instance
message_engine = MessageTemplateEngine()