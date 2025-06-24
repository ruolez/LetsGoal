#!/usr/bin/env python3
"""
Migration script to add SMS functionality to the LetsGoal application.

This migration adds:
1. SMS-related fields to the User model
2. SMS reminders table for scheduled messages
3. SMS delivery log table for tracking sent messages

Run this script after updating the models.py file with SMS functionality.
"""

import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from app import create_app
from models import db

def run_migration():
    """Execute the SMS functionality migration."""
    app = create_app()
    
    with app.app_context():
        try:
            print("Starting SMS functionality migration...")
            
            # Add SMS-related columns to users table
            print("Adding SMS fields to users table...")
            db.engine.execute("""
                ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);
            """)
            
            db.engine.execute("""
                ALTER TABLE users ADD COLUMN phone_verified BOOLEAN DEFAULT FALSE;
            """)
            
            db.engine.execute("""
                ALTER TABLE users ADD COLUMN sms_enabled BOOLEAN DEFAULT FALSE;
            """)
            
            db.engine.execute("""
                ALTER TABLE users ADD COLUMN sms_preferences TEXT;
            """)
            
            db.engine.execute("""
                ALTER TABLE users ADD COLUMN verification_code VARCHAR(10);
            """)
            
            db.engine.execute("""
                ALTER TABLE users ADD COLUMN verification_expires_at DATETIME;
            """)
            
            # Create SMS reminders table
            print("Creating sms_reminders table...")
            db.engine.execute("""
                CREATE TABLE IF NOT EXISTS sms_reminders (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    goal_id INTEGER,
                    subgoal_id INTEGER,
                    reminder_type VARCHAR(50) NOT NULL,
                    message_template VARCHAR(500) NOT NULL,
                    scheduled_time DATETIME NOT NULL,
                    sent_at DATETIME,
                    status VARCHAR(20) DEFAULT 'pending',
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
                    FOREIGN KEY (subgoal_id) REFERENCES subgoals(id) ON DELETE CASCADE
                );
            """)
            
            # Create SMS delivery log table
            print("Creating sms_delivery_log table...")
            db.engine.execute("""
                CREATE TABLE IF NOT EXISTS sms_delivery_log (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    phone_number VARCHAR(20) NOT NULL,
                    message_content TEXT NOT NULL,
                    message_type VARCHAR(50) NOT NULL,
                    aws_message_id VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'sent',
                    cost_usd DECIMAL(10, 6),
                    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    delivered_at DATETIME,
                    error_message TEXT,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
            
            # Create indexes for better performance
            print("Creating indexes...")
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_sms_reminders_user_id ON sms_reminders(user_id);
            """)
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_sms_reminders_scheduled_time ON sms_reminders(scheduled_time);
            """)
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_sms_reminders_status ON sms_reminders(status);
            """)
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_sms_delivery_log_user_id ON sms_delivery_log(user_id);
            """)
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_sms_delivery_log_sent_at ON sms_delivery_log(sent_at);
            """)
            
            # Commit the changes
            db.session.commit()
            
            print("SMS functionality migration completed successfully!")
            print("Summary of changes:")
            print("- Added SMS fields to users table")
            print("- Created sms_reminders table")
            print("- Created sms_delivery_log table")
            print("- Added performance indexes")
            
        except Exception as e:
            print(f"Migration failed: {str(e)}")
            db.session.rollback()
            return False
    
    return True

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)