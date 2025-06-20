#!/usr/bin/env python3
"""
Database migration to add goal sharing system
- Add owner_id column to goals table
- Create goal_shares table for many-to-many sharing relationships
- Migrate existing goals to set owner_id = user_id
- Create "Shared" system tag for all users
- Create indexes for better performance
"""

import os
import sys
import sqlite3
from datetime import datetime

def run_migration():
    """Run the migration to add goal sharing system"""
    
    # Get database path
    db_path = os.environ.get('DATABASE_PATH', '/app/database/letsgoal.db')
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    print(f"Running goal sharing migration on database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Add owner_id column to goals table if it doesn't exist
        print("1. Adding owner_id column to goals table...")
        
        # Check if owner_id column already exists
        cursor.execute("PRAGMA table_info(goals)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'owner_id' not in columns:
            cursor.execute('''
                ALTER TABLE goals 
                ADD COLUMN owner_id INTEGER REFERENCES users(id)
            ''')
            print("   ✓ Added owner_id column to goals table")
            
            # Migrate existing goals: set owner_id = user_id for all existing goals
            print("   ✓ Migrating existing goals...")
            cursor.execute('''
                UPDATE goals 
                SET owner_id = user_id 
                WHERE owner_id IS NULL
            ''')
            updated_goals = cursor.rowcount
            print(f"   ✓ Updated {updated_goals} existing goals with owner_id")
        else:
            print("   ✓ owner_id column already exists")
        
        # 2. Create goal_shares table
        print("2. Creating goal_shares table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goal_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                shared_by_user_id INTEGER NOT NULL,
                shared_with_user_id INTEGER NOT NULL,
                permission_level VARCHAR(20) NOT NULL DEFAULT 'edit',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(goal_id) REFERENCES goals (id) ON DELETE CASCADE,
                FOREIGN KEY(shared_by_user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY(shared_with_user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(goal_id, shared_with_user_id)
            )
        ''')
        print("   ✓ Goal_shares table created or already exists")
        
        # 3. Create indexes for better performance
        print("3. Creating database indexes...")
        
        # Index on goals.owner_id for efficient owner lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_goals_owner_id 
            ON goals(owner_id)
        ''')
        
        # Index on goal_shares for efficient sharing lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_goal_shares_goal_id 
            ON goal_shares(goal_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_goal_shares_shared_with 
            ON goal_shares(shared_with_user_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_goal_shares_shared_by 
            ON goal_shares(shared_by_user_id)
        ''')
        print("   ✓ Created database indexes")
        
        # 4. Create "Shared" system tag for all existing users
        print("4. Creating 'Shared' system tag for all users...")
        cursor.execute('SELECT id FROM users')
        users = cursor.fetchall()
        
        shared_tags_created = 0
        current_time = datetime.utcnow().isoformat()
        
        for user in users:
            user_id = user[0]
            
            try:
                cursor.execute('''
                    INSERT INTO tags (user_id, name, color, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, 'Shared', '#9CA3AF', current_time, current_time))
                shared_tags_created += 1
            except sqlite3.IntegrityError:
                # "Shared" tag already exists for this user, skip
                pass
        
        print(f"   ✓ Created {shared_tags_created} 'Shared' system tags")
        
        # Commit all changes
        conn.commit()
        print("\n✅ Goal sharing migration completed successfully!")
        
        # Show summary
        cursor.execute('SELECT COUNT(*) FROM goal_shares')
        total_shares = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM goals WHERE owner_id IS NOT NULL')
        goals_with_owners = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tags WHERE name = 'Shared'")
        shared_tags = cursor.fetchone()[0]
        
        print(f"\nSummary:")
        print(f"- Goals with owners: {goals_with_owners}")
        print(f"- Total goal shares: {total_shares}")
        print(f"- 'Shared' system tags: {shared_tags}")
        
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
    
    print(f"Rolling back goal sharing migration on database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Drop goal_shares table
        cursor.execute('DROP TABLE IF EXISTS goal_shares')
        print("✓ Dropped goal_shares table")
        
        # Note: We don't remove owner_id column from goals as ALTER TABLE DROP COLUMN
        # is not supported in SQLite. In production, this would require recreating the table.
        print("✓ Note: owner_id column not removed (SQLite limitation)")
        
        # Remove "Shared" system tags
        cursor.execute("DELETE FROM tags WHERE name = 'Shared'")
        deleted_tags = cursor.rowcount
        print(f"✓ Removed {deleted_tags} 'Shared' system tags")
        
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