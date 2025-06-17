#!/usr/bin/env python3
"""
Database migration to add tagging system
- Create tags table for user-specific tags with colors
- Create goal_tags table for many-to-many relationship
- Create indexes for better performance
"""

import os
import sys
import sqlite3
from datetime import datetime

def run_migration():
    """Run the migration to add tagging system"""
    
    # Get database path
    db_path = os.environ.get('DATABASE_PATH', '/app/database/letsgoal.db')
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    print(f"Running tagging system migration on database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Create tags table
        print("1. Creating tags table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name VARCHAR(50) NOT NULL,
                color VARCHAR(7) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            )
        ''')
        print("   ✓ Tags table created or already exists")
        
        # 2. Create goal_tags junction table
        print("2. Creating goal_tags table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goal_tags (
                goal_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (goal_id, tag_id),
                FOREIGN KEY(goal_id) REFERENCES goals (id) ON DELETE CASCADE,
                FOREIGN KEY(tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')
        print("   ✓ Goal_tags table created or already exists")
        
        # 3. Create indexes for better performance
        print("3. Creating database indexes...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tags_user_id 
            ON tags(user_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tags_name 
            ON tags(user_id, name)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_goal_tags_goal 
            ON goal_tags(goal_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_goal_tags_tag 
            ON goal_tags(tag_id)
        ''')
        print("   ✓ Created database indexes")
        
        # 4. Insert some default tags for existing users (optional)
        print("4. Creating default tags for existing users...")
        cursor.execute('SELECT id FROM users')
        users = cursor.fetchall()
        
        default_tags = [
            ('Work', '#3B82F6'),      # Blue
            ('Personal', '#10B981'),   # Green
            ('Health', '#EC4899'),     # Pink
            ('Learning', '#8B5CF6'),   # Purple
            ('Finance', '#F59E0B'),    # Orange
        ]
        
        tags_created = 0
        current_time = datetime.utcnow().isoformat()
        
        for user in users:
            user_id = user[0]
            
            for tag_name, tag_color in default_tags:
                try:
                    cursor.execute('''
                        INSERT INTO tags (user_id, name, color, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, tag_name, tag_color, current_time, current_time))
                    tags_created += 1
                except sqlite3.IntegrityError:
                    # Tag already exists for this user, skip
                    pass
        
        print(f"   ✓ Created {tags_created} default tags")
        
        # Commit all changes
        conn.commit()
        print("\n✅ Tagging system migration completed successfully!")
        
        # Show summary
        cursor.execute('SELECT COUNT(*) FROM tags')
        total_tags = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM goal_tags')
        total_goal_tags = cursor.fetchone()[0]
        
        print(f"\nSummary:")
        print(f"- Total tags in database: {total_tags}")
        print(f"- Total goal-tag associations: {total_goal_tags}")
        
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
    
    print(f"Rolling back tagging system migration on database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Drop tables in reverse order due to foreign keys
        cursor.execute('DROP TABLE IF EXISTS goal_tags')
        print("✓ Dropped goal_tags table")
        
        cursor.execute('DROP TABLE IF EXISTS tags')
        print("✓ Dropped tags table")
        
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