#!/usr/bin/env python3
"""
Database migration to add admin system
- Add role, last_login_at, password_changed_at, login_count columns to users table
- Create user_sessions table for login tracking
- Create admin_settings table for configuration
- Create system_backups table for backup tracking
- Create default admin user (username='admin', password='admin', role='admin')
- Add database indexes for better performance
- Add default admin settings
"""

import os
import sys
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

def run_migration():
    """Run the migration to add admin system"""
    
    # Get database path
    db_path = os.environ.get('DATABASE_PATH', '/app/database/letsgoal.db')
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    print(f"Running admin system migration on database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Add new columns to users table
        print("1. Adding new columns to users table...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add role column
        if 'role' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
            print("   ✓ Added role column to users table")
        else:
            print("   ✓ Role column already exists")
        
        # Add last_login_at column
        if 'last_login_at' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN last_login_at DATETIME")
            print("   ✓ Added last_login_at column to users table")
        else:
            print("   ✓ Last_login_at column already exists")
        
        # Add password_changed_at column
        if 'password_changed_at' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_changed_at DATETIME")
            print("   ✓ Added password_changed_at column to users table")
        else:
            print("   ✓ Password_changed_at column already exists")
        
        # Add login_count column
        if 'login_count' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN login_count INTEGER NOT NULL DEFAULT 0")
            print("   ✓ Added login_count column to users table")
        else:
            print("   ✓ Login_count column already exists")
        
        # 2. Create user_sessions table
        print("2. Creating user_sessions table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_start DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                session_end DATETIME,
                ip_address VARCHAR(45),
                user_agent TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        print("   ✓ User_sessions table created or already exists")
        
        # 3. Create admin_settings table
        print("3. Creating admin_settings table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT,
                setting_type VARCHAR(20) NOT NULL DEFAULT 'string',
                description TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("   ✓ Admin_settings table created or already exists")
        
        # 4. Create system_backups table
        print("4. Creating system_backups table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_name VARCHAR(200) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                backup_size BIGINT,
                backup_type VARCHAR(20) NOT NULL DEFAULT 'manual',
                created_by_user_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) NOT NULL DEFAULT 'completed',
                error_message TEXT,
                metadata TEXT,
                FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        ''')
        print("   ✓ System_backups table created or already exists")
        
        # 5. Create database indexes for performance
        print("5. Creating database indexes...")
        
        # Indexes on users table
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_at)")
        
        # Indexes on user_sessions table
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_start ON user_sessions(session_start)")
        
        # Indexes on admin_settings table
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_settings_key ON admin_settings(setting_key)")
        
        # Indexes on system_backups table
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_backups_created_at ON system_backups(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_backups_type ON system_backups(backup_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_backups_status ON system_backups(status)")
        
        print("   ✓ Created database indexes")
        
        # 6. Create default admin user
        print("6. Creating default admin user...")
        
        # Check if admin user already exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_exists = cursor.fetchone()
        
        if not admin_exists:
            # Create admin user with default password 'admin'
            admin_password_hash = generate_password_hash('admin')
            current_time = datetime.utcnow().isoformat()
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, created_at, updated_at, login_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('admin', 'admin@letsgoal.local', admin_password_hash, 'admin', current_time, current_time, 0))
            
            admin_user_id = cursor.lastrowid
            print(f"   ✓ Created default admin user (ID: {admin_user_id})")
            print("   ⚠️  Default admin password is 'admin' - MUST be changed on first login")
        else:
            print("   ✓ Admin user already exists")
            
            # Ensure existing admin user has admin role
            cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
            print("   ✓ Ensured admin user has admin role")
        
        # 7. Add default admin settings
        print("7. Adding default admin settings...")
        
        default_settings = [
            ('system_name', 'LetsGoal Admin Portal', 'string', 'Name of the admin system'),
            ('backup_retention_days', '30', 'integer', 'Days to retain backup files'),
            ('session_timeout_minutes', '120', 'integer', 'Admin session timeout in minutes'),
            ('auto_backup_enabled', 'true', 'boolean', 'Enable automatic daily backups'),
            ('max_login_attempts', '5', 'integer', 'Maximum failed login attempts before lockout'),
            ('admin_email_notifications', 'true', 'boolean', 'Send admin email notifications'),
            ('system_maintenance_mode', 'false', 'boolean', 'System maintenance mode status'),
        ]
        
        settings_added = 0
        for key, value, setting_type, description in default_settings:
            try:
                cursor.execute('''
                    INSERT INTO admin_settings (setting_key, setting_value, setting_type, description)
                    VALUES (?, ?, ?, ?)
                ''', (key, value, setting_type, description))
                settings_added += 1
            except sqlite3.IntegrityError:
                # Setting already exists, skip
                pass
        
        print(f"   ✓ Added {settings_added} default admin settings")
        
        # Commit all changes
        conn.commit()
        print("\n✅ Admin system migration completed successfully!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM admin_settings")
        settings_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_sessions")
        sessions_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM system_backups")
        backups_count = cursor.fetchone()[0]
        
        print(f"\nSummary:")
        print(f"- Admin users: {admin_count}")
        print(f"- Admin settings: {settings_count}")
        print(f"- User sessions: {sessions_count}")
        print(f"- System backups: {backups_count}")
        
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
    
    print(f"Rolling back admin system migration on database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Drop new tables
        cursor.execute('DROP TABLE IF EXISTS system_backups')
        print("✓ Dropped system_backups table")
        
        cursor.execute('DROP TABLE IF EXISTS admin_settings')
        print("✓ Dropped admin_settings table")
        
        cursor.execute('DROP TABLE IF EXISTS user_sessions')
        print("✓ Dropped user_sessions table")
        
        # Note: We don't remove columns from users table as ALTER TABLE DROP COLUMN
        # is not supported in SQLite. In production, this would require recreating the table.
        print("✓ Note: New columns not removed from users table (SQLite limitation)")
        
        # Remove admin user
        cursor.execute("DELETE FROM users WHERE username = 'admin'")
        deleted_admin = cursor.rowcount
        print(f"✓ Removed {deleted_admin} admin user(s)")
        
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