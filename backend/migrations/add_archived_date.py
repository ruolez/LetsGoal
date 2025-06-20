#!/usr/bin/env python3

"""
Migration script to add archived_date field to goals table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db

app = create_app()

def add_archived_date_field():
    """Add archived_date field to goals table"""
    with app.app_context():
        try:
            # Check if column already exists
            with db.engine.connect() as conn:
                result = conn.execute(db.text("PRAGMA table_info(goals)"))
                columns = [row[1] for row in result]
                
                if 'archived_date' not in columns:
                    print("Adding archived_date column to goals table...")
                    conn.execute(db.text("ALTER TABLE goals ADD COLUMN archived_date DATE"))
                    conn.commit()
                    print("✅ Successfully added archived_date column")
                else:
                    print("✅ archived_date column already exists")
                
        except Exception as e:
            print(f"❌ Error adding archived_date column: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🗄️  Running migration: add_archived_date")
    success = add_archived_date_field()
    if success:
        print("✅ Migration completed successfully")
    else:
        print("❌ Migration failed")
        sys.exit(1)