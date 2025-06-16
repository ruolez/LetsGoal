#!/usr/bin/env python3
"""
Database migration to add event tracking system
- Add updated_at field to subgoals table
- Create events table
- Backfill existing data with approximate timestamps
"""

import os
import sys
import sqlite3
from datetime import datetime

def run_migration():
    """Run the migration to add event tracking"""
    
    # Get database path
    db_path = os.environ.get('DATABASE_PATH', '/app/database/letsgoal.db')
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    print(f"Running migration on database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Add updated_at column to subgoals table if it doesn't exist
        print("1. Adding updated_at column to subgoals table...")
        try:
            cursor.execute("ALTER TABLE subgoals ADD COLUMN updated_at DATETIME")
            print("   ✓ Added updated_at column to subgoals")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("   ✓ updated_at column already exists in subgoals")
            else:
                raise e
        
        # 2. Create events table if it doesn't exist
        print("2. Creating events table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                entity_type VARCHAR(20) NOT NULL,
                entity_id INTEGER NOT NULL,
                action VARCHAR(50) NOT NULL,
                field_name VARCHAR(50),
                old_value TEXT,
                new_value TEXT,
                event_metadata TEXT,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users (id)
            )
        ''')
        print("   ✓ Events table created or already exists")
        
        # 3. Backfill subgoals.updated_at with created_at where updated_at is NULL
        print("3. Backfilling subgoals.updated_at timestamps...")
        cursor.execute('''
            UPDATE subgoals 
            SET updated_at = created_at 
            WHERE updated_at IS NULL
        ''')
        affected_rows = cursor.rowcount
        print(f"   ✓ Updated {affected_rows} subgoal records")
        
        # 4. Create initial events for existing goals and subgoals
        print("4. Creating initial events for existing data...")
        
        # Get all goals
        cursor.execute('SELECT id, user_id, title, status, created_at FROM goals')
        goals = cursor.fetchall()
        
        events_created = 0
        current_time = datetime.utcnow().isoformat()
        
        for goal in goals:
            goal_id, user_id, title, status, created_at = goal
            
            # Create 'created' event for each goal
            cursor.execute('''
                INSERT INTO events (user_id, entity_type, entity_id, action, event_metadata, created_at)
                VALUES (?, 'goal', ?, 'created', ?, ?)
            ''', (
                user_id,
                goal_id,
                f'{{"title": "{title}", "status": "{status}"}}',
                created_at or current_time
            ))
            events_created += 1
        
        # Get all subgoals
        cursor.execute('''
            SELECT s.id, g.user_id, s.title, s.status, s.goal_id, g.title as goal_title, s.created_at
            FROM subgoals s
            JOIN goals g ON s.goal_id = g.id
        ''')
        subgoals = cursor.fetchall()
        
        for subgoal in subgoals:
            subgoal_id, user_id, title, status, goal_id, goal_title, created_at = subgoal
            
            # Create 'created' event for each subgoal
            cursor.execute('''
                INSERT INTO events (user_id, entity_type, entity_id, action, event_metadata, created_at)
                VALUES (?, 'subgoal', ?, 'created', ?, ?)
            ''', (
                user_id,
                subgoal_id,
                f'{{"title": "{title}", "status": "{status}", "goal_id": {goal_id}, "goal_title": "{goal_title}"}}',
                created_at or current_time
            ))
            events_created += 1
            
            # If subgoal is achieved, create a 'completed' event
            if status == 'achieved':
                cursor.execute('''
                    INSERT INTO events (user_id, entity_type, entity_id, action, event_metadata, created_at)
                    VALUES (?, 'subgoal', ?, 'completed', ?, ?)
                ''', (
                    user_id,
                    subgoal_id,
                    f'{{"title": "{title}", "goal_id": {goal_id}, "goal_title": "{goal_title}"}}',
                    created_at or current_time
                ))
                events_created += 1
        
        print(f"   ✓ Created {events_created} initial events")
        
        # 5. Create index on events table for better performance
        print("5. Creating database indexes...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_user_created 
            ON events(user_id, created_at DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_entity 
            ON events(entity_type, entity_id, created_at DESC)
        ''')
        print("   ✓ Created database indexes")
        
        # Commit all changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        # Show summary
        cursor.execute('SELECT COUNT(*) FROM events')
        total_events = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM subgoals WHERE updated_at IS NOT NULL')
        subgoals_with_timestamps = cursor.fetchone()[0]
        
        print(f"\nSummary:")
        print(f"- Total events in database: {total_events}")
        print(f"- Subgoals with updated_at timestamps: {subgoals_with_timestamps}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def rollback_migration():
    """Rollback the migration (for development/testing)"""
    db_path = os.environ.get('DATABASE_PATH', '/app/database/letsgoal.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    print(f"Rolling back migration on database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Drop events table
        cursor.execute('DROP TABLE IF EXISTS events')
        print("✓ Dropped events table")
        
        # Remove updated_at column from subgoals (SQLite doesn't support DROP COLUMN easily)
        # So we'll just set the values to NULL
        cursor.execute('UPDATE subgoals SET updated_at = NULL')
        print("✓ Cleared updated_at values from subgoals")
        
        conn.commit()
        print("✅ Rollback completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        run_migration()