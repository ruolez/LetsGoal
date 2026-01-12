#!/usr/bin/env python3
"""
Migration to fix metadata column naming issue
"""

import os
import sqlite3

def run_migration():
    """Fix metadata column name in system_backups table"""
    db_path = os.environ.get('DATABASE_PATH', '/app/database/letsgoal.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    print(f"Fixing metadata column in database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if backup_metadata column exists
        cursor.execute("PRAGMA table_info(system_backups)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'backup_metadata' not in columns:
            if 'metadata' in columns:
                # Rename metadata to backup_metadata
                print("Renaming metadata column to backup_metadata...")
                cursor.execute("ALTER TABLE system_backups RENAME COLUMN metadata TO backup_metadata")
                print("✓ Column renamed successfully")
            else:
                # Add backup_metadata column
                print("Adding backup_metadata column...")
                cursor.execute("ALTER TABLE system_backups ADD COLUMN backup_metadata TEXT")
                print("✓ Column added successfully")
        else:
            print("✓ backup_metadata column already exists")
        
        conn.commit()
        print("✅ Metadata column fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()