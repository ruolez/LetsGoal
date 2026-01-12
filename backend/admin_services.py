"""
Admin Services Module
Contains business logic for admin operations including backup/restore, 
file management, and system maintenance functions.
"""

import os
import sys
sys.path.append('/app')
import shutil
import sqlite3
from datetime import datetime, timedelta
from backend.models import db, SystemBackup, AdminSettings
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_path():
    """Get the current database file path"""
    db_url = os.environ.get('DATABASE_URL', 'sqlite:////app/database/letsgoal.db')
    if db_url.startswith('sqlite:///'):
        return db_url[10:]  # Remove 'sqlite:///' prefix
    return '/app/database/letsgoal.db'  # Fallback

def get_backup_directory():
    """Get or create the backup directory"""
    backup_dir = os.environ.get('BACKUP_DIR', '/app/backups')
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def create_database_backup(backup_name, backup_type='manual', created_by_user_id=None):
    """
    Create a backup of the SQLite database
    
    Args:
        backup_name (str): Name for the backup
        backup_type (str): Type of backup ('manual', 'scheduled', 'pre_update')
        created_by_user_id (int): ID of user creating the backup
    
    Returns:
        dict: Result with success status and backup info or error message
    """
    backup_record = None
    backup_path = None
    
    try:
        # Get database and backup paths
        db_path = get_database_path()
        backup_dir = get_backup_directory()
        
        # Verify source database exists and is readable
        if not os.path.exists(db_path):
            return {
                'success': False,
                'error': f'Source database not found: {db_path}'
            }
        
        if not os.access(db_path, os.R_OK):
            return {
                'success': False,
                'error': f'Source database is not readable: {db_path}'
            }
        
        # Verify backup directory exists and is writable
        os.makedirs(backup_dir, exist_ok=True)
        if not os.access(backup_dir, os.W_OK):
            return {
                'success': False,
                'error': f'Backup directory is not writable: {backup_dir}'
            }
        
        # Sanitize backup name
        import re
        sanitized_name = re.sub(r'[^a-zA-Z0-9_\-\s]', '_', backup_name)
        sanitized_name = sanitized_name.strip().replace(' ', '_')[:50]  # Limit length
        
        # Create backup filename with timestamp and random suffix for uniqueness
        import uuid
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_suffix = str(uuid.uuid4()).split('-')[0]  # Use first part of UUID
        backup_filename = f"{sanitized_name}_{timestamp}_{unique_suffix}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Ensure backup path doesn't already exist (very unlikely with UUID)
        counter = 1
        while os.path.exists(backup_path):
            backup_filename = f"{sanitized_name}_{timestamp}_{unique_suffix}_{counter}.db"
            backup_path = os.path.join(backup_dir, backup_filename)
            counter += 1
            if counter > 10:  # Safety limit (should never be needed with UUID)
                return {
                    'success': False,
                    'error': f'Unable to create unique filename after 10 attempts'
                }
        
        # Create backup record in database first (with in_progress status)
        backup_record = SystemBackup(
            backup_name=backup_name,
            file_path=backup_path,
            backup_type=backup_type,
            created_by_user_id=created_by_user_id,
            status='in_progress'
        )
        
        db.session.add(backup_record)
        db.session.commit()
        
        logger.info(f"Starting backup: {backup_name} -> {backup_path}")
        
        # Method 1: Using SQLite backup API (preferred for online backups)
        backup_method_used = None
        try:
            source_conn = sqlite3.connect(db_path, timeout=30.0)
            backup_conn = sqlite3.connect(backup_path)
            
            # Perform the backup with progress callback
            def backup_progress(status, remaining, total):
                if total > 0:
                    percent = ((total - remaining) / total) * 100
                    if percent % 25 == 0:  # Log every 25%
                        logger.info(f"Backup progress: {percent:.0f}%")
            
            # Use backup API with progress tracking
            source_conn.backup(backup_conn, pages=100, progress=backup_progress)
            
            source_conn.close()
            backup_conn.close()
            
            backup_method_used = 'sqlite_backup_api'
            logger.info(f"Backup completed using SQLite backup API")
            
        except Exception as sqlite_error:
            logger.warning(f"SQLite backup API failed: {sqlite_error}")
            
            # Clean up partial backup file
            if backup_path and os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except:
                    pass
            
            # Method 2: File copy fallback
            try:
                # Use secure copy with verification
                shutil.copy2(db_path, backup_path)
                
                # Verify the copied file
                if not os.path.exists(backup_path):
                    raise Exception("Backup file was not created")
                
                # Quick integrity check
                test_conn = sqlite3.connect(backup_path)
                test_conn.execute("SELECT COUNT(*) FROM sqlite_master")
                test_conn.close()
                
                backup_method_used = 'file_copy'
                logger.info(f"Backup completed using file copy")
                
            except Exception as copy_error:
                # Cleanup failed backup record and file
                if backup_path and os.path.exists(backup_path):
                    try:
                        os.remove(backup_path)
                    except:
                        pass
                
                if backup_record:
                    try:
                        db.session.delete(backup_record)
                        db.session.commit()
                    except:
                        pass
                
                return {
                    'success': False,
                    'error': f'Both backup methods failed. SQLite: {sqlite_error}, Copy: {copy_error}'
                }
        
        # Verify backup file was created and is valid
        if not os.path.exists(backup_path):
            if backup_record:
                try:
                    db.session.delete(backup_record)
                    db.session.commit()
                except:
                    pass
            return {
                'success': False,
                'error': 'Backup file was not created successfully'
            }
        
        # Get backup file size
        backup_size = os.path.getsize(backup_path)
        
        if backup_size == 0:
            # Remove empty backup file and record
            try:
                os.remove(backup_path)
                db.session.delete(backup_record)
                db.session.commit()
            except:
                pass
            return {
                'success': False,
                'error': 'Backup file is empty (0 bytes)'
            }
        
        # Update backup record with success status
        backup_record.backup_size = backup_size
        backup_record.status = 'completed'
        backup_record.set_metadata({
            'method': backup_method_used,
            'source_db_path': db_path,
            'source_db_size': os.path.getsize(db_path) if os.path.exists(db_path) else 0,
            'compression_ratio': round(backup_size / os.path.getsize(db_path), 4) if os.path.exists(db_path) else 0,
            'backup_filename': backup_filename,
            'timestamp': timestamp
        })
        
        db.session.commit()
        
        logger.info(f"Backup successful: {backup_size} bytes using {backup_method_used}")
        
        return {
            'success': True,
            'backup': backup_record.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        
        # Cleanup on failure
        if backup_path and os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except:
                pass
        
        # Update backup record with error status if it exists
        if backup_record:
            try:
                backup_record.status = 'failed'
                backup_record.error_message = str(e)
                db.session.commit()
            except Exception as db_error:
                logger.error(f"Failed to update backup record: {db_error}")
                # If we can't update the record, try to delete it
                try:
                    db.session.delete(backup_record)
                    db.session.commit()
                except:
                    pass
        
        return {
            'success': False,
            'error': f'Backup creation failed: {str(e)}'
        }

def restore_database_backup(backup_id, restored_by_user_id=None):
    """
    Restore database from a backup
    
    Args:
        backup_id (int): ID of the backup to restore from
        restored_by_user_id (int): ID of user performing the restore
    
    Returns:
        dict: Result with success status and restore info or error message
    """
    temp_db_path = None
    rollback_path = None
    
    try:
        # Get backup record
        backup = SystemBackup.query.get(backup_id)
        if not backup:
            return {
                'success': False,
                'error': 'Backup record not found'
            }
        
        # Verify backup file exists and is readable
        if not os.path.exists(backup.file_path):
            return {
                'success': False,
                'error': 'Backup file not found on disk'
            }
        
        if not os.access(backup.file_path, os.R_OK):
            return {
                'success': False,
                'error': 'Backup file is not readable'
            }
        
        # Get current database path
        db_path = get_database_path()
        
        # Verify current database exists
        if not os.path.exists(db_path):
            return {
                'success': False,
                'error': 'Current database not found'
            }
        
        # Verify backup file integrity thoroughly
        try:
            test_conn = sqlite3.connect(backup.file_path, timeout=10.0)
            
            # Run integrity check
            cursor = test_conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            
            if integrity_result != 'ok':
                test_conn.close()
                return {
                    'success': False,
                    'error': f'Backup file integrity check failed: {integrity_result}'
                }
            
            # Verify essential tables exist
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            if table_count == 0:
                test_conn.close()
                return {
                    'success': False,
                    'error': 'Backup file contains no tables'
                }
            
            # Check for essential tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users', 'goals')")
            essential_tables = cursor.fetchall()
            
            test_conn.close()
            
            if len(essential_tables) < 2:
                return {
                    'success': False,
                    'error': 'Backup file is missing essential tables (users, goals)'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Backup file validation failed: {str(e)}'
            }
        
        # Create a backup of current database before restore
        current_backup_name = f"pre_restore_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        pre_restore_result = create_database_backup(
            backup_name=current_backup_name,
            backup_type='pre_update',
            created_by_user_id=restored_by_user_id
        )
        
        if not pre_restore_result['success']:
            return {
                'success': False,
                'error': f'Failed to create pre-restore backup: {pre_restore_result["error"]}'
            }
        
        logger.info(f"Starting restore from backup: {backup.backup_name}")
        
        # Create temporary file for safe restore
        backup_dir = os.path.dirname(db_path)
        temp_db_path = os.path.join(backup_dir, f"temp_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db")
        
        try:
            # Copy backup to temporary location with verification
            shutil.copy2(backup.file_path, temp_db_path)
            
            # Verify the copied file
            if not os.path.exists(temp_db_path):
                raise Exception("Failed to create temporary restore file")
            
            temp_size = os.path.getsize(temp_db_path)
            original_size = os.path.getsize(backup.file_path)
            
            if temp_size != original_size:
                raise Exception(f"File size mismatch: original {original_size}, copy {temp_size}")
            
            # Test the temporary file
            test_conn = sqlite3.connect(temp_db_path)
            test_conn.execute("SELECT COUNT(*) FROM sqlite_master")
            test_conn.close()
            
            # Close all database connections before file operations
            db.session.close()
            db.engine.dispose()
            
            # Replace current database with backup
            if os.path.exists(db_path):
                # Move current db to a temporary location in case we need to rollback
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                rollback_path = f"{db_path}.rollback_{timestamp}"
                
                # Ensure rollback path doesn't exist
                counter = 1
                while os.path.exists(rollback_path):
                    rollback_path = f"{db_path}.rollback_{timestamp}_{counter}"
                    counter += 1
                
                try:
                    # Move current database to rollback location
                    shutil.move(db_path, rollback_path)
                    
                    # Move restored database to correct location
                    shutil.move(temp_db_path, db_path)
                    temp_db_path = None  # Prevent cleanup since file was moved
                    
                    # Verify the restore worked
                    test_conn = sqlite3.connect(db_path)
                    test_conn.execute("SELECT COUNT(*) FROM users")
                    test_conn.close()
                    
                    # Remove rollback file on success
                    os.remove(rollback_path)
                    rollback_path = None
                    
                    logger.info(f"Database restore completed successfully")
                    
                except Exception as e:
                    # Rollback on failure
                    if rollback_path and os.path.exists(rollback_path):
                        try:
                            # Remove failed restore file if it exists
                            if os.path.exists(db_path):
                                os.remove(db_path)
                            # Restore original database
                            shutil.move(rollback_path, db_path)
                            rollback_path = None
                        except Exception as rollback_error:
                            logger.error(f"Rollback failed: {rollback_error}")
                    raise Exception(f"Restore failed, database rollback attempted: {e}")
            else:
                # No current database, just move the temp file
                shutil.move(temp_db_path, db_path)
                temp_db_path = None
        
        except Exception as restore_error:
            logger.error(f"Restore operation failed: {restore_error}")
            raise restore_error
        
        finally:
            # Clean up temporary files
            if temp_db_path and os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except:
                    pass
            
            if rollback_path and os.path.exists(rollback_path):
                try:
                    os.remove(rollback_path)
                except:
                    pass
        
        # Record restore operation in metadata
        restore_info = {
            'restored_from_backup_id': backup_id,
            'restored_by_user_id': restored_by_user_id,
            'restored_at': datetime.utcnow().isoformat(),
            'pre_restore_backup_id': pre_restore_result['backup']['id'] if pre_restore_result['success'] else None,
            'backup_name': backup.backup_name,
            'backup_created_at': backup.created_at.isoformat() if backup.created_at else None,
            'backup_size_mb': round(backup.backup_size / (1024 * 1024), 2) if backup.backup_size else 0
        }
        
        return {
            'success': True,
            'info': restore_info
        }
        
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}")
        return {
            'success': False,
            'error': f'Database restore failed: {str(e)}'
        }

def cleanup_old_backup_files(retention_days=30):
    """
    Clean up old backup files and database records
    
    Args:
        retention_days (int): Number of days to retain backups
    
    Returns:
        dict: Cleanup statistics
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Get old backup records
        old_backups = SystemBackup.query.filter(
            SystemBackup.created_at < cutoff_date
        ).all()
        
        removed_files = 0
        freed_space_bytes = 0
        removed_records = 0
        orphaned_cleaned = 0
        
        # First, clean up old backups
        for backup in old_backups:
            # Remove file if it exists
            if os.path.exists(backup.file_path):
                try:
                    file_size = os.path.getsize(backup.file_path)
                    os.remove(backup.file_path)
                    freed_space_bytes += file_size
                    removed_files += 1
                    logger.info(f"Removed old backup file: {backup.file_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove backup file {backup.file_path}: {e}")
            
            # Remove database record
            try:
                db.session.delete(backup)
                removed_records += 1
            except Exception as e:
                logger.warning(f"Failed to remove backup record {backup.id}: {e}")
        
        # Second, clean up orphaned database records (records without files)
        all_backups = SystemBackup.query.all()
        for backup in all_backups:
            if not os.path.exists(backup.file_path):
                try:
                    logger.info(f"Removing orphaned backup record: {backup.backup_name} (file not found: {backup.file_path})")
                    db.session.delete(backup)
                    orphaned_cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to remove orphaned backup record {backup.id}: {e}")
        
        db.session.commit()
        
        freed_space_mb = round(freed_space_bytes / (1024 * 1024), 2)
        
        logger.info(f"Cleanup completed: {removed_files} files, {freed_space_mb} MB freed, {orphaned_cleaned} orphaned records removed")
        
        return {
            'removed_records': removed_records,
            'removed_files': removed_files,
            'freed_space_mb': freed_space_mb,
            'orphaned_cleaned': orphaned_cleaned
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Cleanup failed: {str(e)}")
        return {
            'removed_records': 0,
            'removed_files': 0,
            'freed_space_mb': 0,
            'orphaned_cleaned': 0,
            'error': str(e)
        }

def get_system_health_info():
    """
    Get system health information
    
    Returns:
        dict: System health data
    """
    try:
        db_path = get_database_path()
        backup_dir = get_backup_directory()
        
        health_info = {
            'database': {
                'path': db_path,
                'exists': os.path.exists(db_path),
                'size_mb': 0,
                'accessible': False
            },
            'backup_system': {
                'backup_dir': backup_dir,
                'backup_dir_exists': os.path.exists(backup_dir),
                'total_backups': 0,
                'total_backup_size_mb': 0,
                'oldest_backup': None,
                'newest_backup': None
            },
            'disk_space': {
                'available_mb': 0,
                'total_mb': 0,
                'used_percent': 0
            }
        }
        
        # Database info
        if os.path.exists(db_path):
            try:
                health_info['database']['size_mb'] = round(os.path.getsize(db_path) / (1024 * 1024), 2)
                
                # Test database accessibility
                test_conn = sqlite3.connect(db_path)
                test_conn.execute("SELECT 1")
                test_conn.close()
                health_info['database']['accessible'] = True
                
            except Exception as e:
                health_info['database']['error'] = str(e)
        
        # Backup system info
        if os.path.exists(backup_dir):
            backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
            health_info['backup_system']['total_backups'] = len(backup_files)
            
            total_size = 0
            file_times = []
            
            for backup_file in backup_files:
                file_path = os.path.join(backup_dir, backup_file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
                    file_times.append(os.path.getmtime(file_path))
            
            health_info['backup_system']['total_backup_size_mb'] = round(total_size / (1024 * 1024), 2)
            
            if file_times:
                health_info['backup_system']['oldest_backup'] = datetime.fromtimestamp(min(file_times)).isoformat()
                health_info['backup_system']['newest_backup'] = datetime.fromtimestamp(max(file_times)).isoformat()
        
        # Disk space info
        try:
            disk_usage = shutil.disk_usage(os.path.dirname(db_path))
            health_info['disk_space']['total_mb'] = round(disk_usage.total / (1024 * 1024), 2)
            health_info['disk_space']['available_mb'] = round(disk_usage.free / (1024 * 1024), 2)
            health_info['disk_space']['used_percent'] = round(
                ((disk_usage.total - disk_usage.free) / disk_usage.total) * 100, 2
            )
        except Exception as e:
            health_info['disk_space']['error'] = str(e)
        
        return health_info
        
    except Exception as e:
        logger.error(f"Failed to get system health info: {str(e)}")
        return {'error': str(e)}

def verify_backup_integrity(backup_id):
    """
    Verify the integrity of a backup file
    
    Args:
        backup_id (int): ID of backup to verify
    
    Returns:
        dict: Verification result
    """
    try:
        backup = SystemBackup.query.get(backup_id)
        if not backup:
            return {
                'valid': False,
                'error': 'Backup record not found'
            }
        
        if not os.path.exists(backup.file_path):
            return {
                'valid': False,
                'error': 'Backup file not found on disk'
            }
        
        # Test SQLite database integrity
        try:
            conn = sqlite3.connect(backup.file_path)
            
            # Run integrity check
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()
            
            # Count tables
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            # Get database info
            cursor.execute("PRAGMA user_version")
            user_version = cursor.fetchone()[0]
            
            conn.close()
            
            is_valid = integrity_result[0] == 'ok'
            
            return {
                'valid': is_valid,
                'integrity_check': integrity_result[0],
                'table_count': table_count,
                'user_version': user_version,
                'file_size_mb': round(os.path.getsize(backup.file_path) / (1024 * 1024), 2)
            }
            
        except Exception as db_error:
            return {
                'valid': False,
                'error': f'Database verification failed: {str(db_error)}'
            }
        
    except Exception as e:
        return {
            'valid': False,
            'error': f'Verification failed: {str(e)}'
        }

def export_admin_settings():
    """
    Export all admin settings to a dictionary
    
    Returns:
        dict: All admin settings
    """
    try:
        settings = AdminSettings.query.all()
        settings_dict = {}
        
        for setting in settings:
            settings_dict[setting.setting_key] = {
                'value': setting.get_typed_value(),
                'type': setting.setting_type,
                'description': setting.description,
                'updated_at': setting.updated_at.isoformat() if setting.updated_at else None
            }
        
        return {
            'success': True,
            'settings': settings_dict,
            'exported_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Settings export failed: {str(e)}'
        }

def import_admin_settings(settings_dict):
    """
    Import admin settings from a dictionary
    
    Args:
        settings_dict (dict): Settings to import
    
    Returns:
        dict: Import result
    """
    try:
        imported_count = 0
        updated_count = 0
        
        for key, setting_data in settings_dict.items():
            if not isinstance(setting_data, dict):
                continue
                
            value = setting_data.get('value')
            setting_type = setting_data.get('type', 'string')
            description = setting_data.get('description')
            
            # Check if setting exists
            existing_setting = AdminSettings.query.filter_by(setting_key=key).first()
            
            if existing_setting:
                existing_setting.set_typed_value(value)
                existing_setting.updated_at = datetime.utcnow()
                if description:
                    existing_setting.description = description
                updated_count += 1
            else:
                new_setting = AdminSettings(
                    setting_key=key,
                    setting_type=setting_type,
                    description=description
                )
                new_setting.set_typed_value(value)
                db.session.add(new_setting)
                imported_count += 1
        
        db.session.commit()
        
        return {
            'success': True,
            'imported_count': imported_count,
            'updated_count': updated_count,
            'total_processed': imported_count + updated_count
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': f'Settings import failed: {str(e)}'
        }

def cleanup_orphaned_backup_records():
    """
    Clean up database backup records that point to non-existent files
    
    Returns:
        dict: Cleanup statistics
    """
    try:
        orphaned_records = []
        all_backups = SystemBackup.query.all()
        
        for backup in all_backups:
            if not os.path.exists(backup.file_path):
                orphaned_records.append(backup)
        
        removed_count = 0
        for backup in orphaned_records:
            try:
                logger.info(f"Removing orphaned backup record: {backup.backup_name} (file: {backup.file_path})")
                db.session.delete(backup)
                removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove orphaned record {backup.id}: {e}")
        
        db.session.commit()
        
        logger.info(f"Orphaned backup cleanup completed: {removed_count} records removed")
        
        return {
            'success': True,
            'removed_count': removed_count,
            'total_checked': len(all_backups)
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Orphaned backup cleanup failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'removed_count': 0
        }

def clear_user_data_and_goals(preserve_admin=True):
    """
    Delete all user data including goals and settings, optionally preserving admin users
    
    Args:
        preserve_admin (bool): Whether to preserve admin users and their data
    
    Returns:
        dict: Result with success status and cleanup statistics
    """
    try:
        from backend.models import User, Goal, Subgoal, Tag, Event, UserSession, ProgressEntry
        
        stats = {
            'users_deleted': 0,
            'goals_deleted': 0,
            'subgoals_deleted': 0,
            'tags_deleted': 0,
            'events_deleted': 0,
            'sessions_deleted': 0,
            'progress_entries_deleted': 0
        }
        
        # Create backup before clearing data
        backup_name = f"pre_clear_full_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        backup_result = create_database_backup(
            backup_name=backup_name,
            backup_type='pre_update'
        )
        
        if not backup_result['success']:
            return {
                'success': False,
                'error': f'Failed to create pre-clear backup: {backup_result["error"]}'
            }
        
        logger.info(f"Starting full data clear (preserve_admin={preserve_admin})")
        
        if preserve_admin:
            # Get admin user IDs to preserve
            admin_user_ids = [user.id for user in User.query.filter_by(role='admin').all()]
            
            # Delete non-admin user data
            non_admin_users = User.query.filter(~User.id.in_(admin_user_ids)).all()
            for user in non_admin_users:
                # Delete user's goals (cascade will handle subgoals)
                user_goals = Goal.query.filter(
                    (Goal.user_id == user.id) | (Goal.owner_id == user.id)
                ).all()
                for goal in user_goals:
                    stats['subgoals_deleted'] += len(goal.subgoals)
                    db.session.delete(goal)
                    stats['goals_deleted'] += 1
                
                # Delete user's tags
                user_tags = Tag.query.filter_by(user_id=user.id).all()
                for tag in user_tags:
                    db.session.delete(tag)
                    stats['tags_deleted'] += 1
                
                # Delete user's events
                user_events = Event.query.filter_by(user_id=user.id).all()
                for event in user_events:
                    db.session.delete(event)
                    stats['events_deleted'] += 1
                
                # Delete user's sessions
                user_sessions = UserSession.query.filter_by(user_id=user.id).all()
                for session in user_sessions:
                    db.session.delete(session)
                    stats['sessions_deleted'] += 1
                
                # Delete user's progress entries
                user_progress = ProgressEntry.query.join(Goal).filter(Goal.user_id == user.id).all()
                for entry in user_progress:
                    db.session.delete(entry)
                    stats['progress_entries_deleted'] += 1
                
                # Delete the user
                db.session.delete(user)
                stats['users_deleted'] += 1
        else:
            # Delete all user data
            stats['progress_entries_deleted'] = ProgressEntry.query.count()
            ProgressEntry.query.delete()
            
            stats['events_deleted'] = Event.query.count()
            Event.query.delete()
            
            stats['sessions_deleted'] = UserSession.query.count()
            UserSession.query.delete()
            
            stats['tags_deleted'] = Tag.query.count()
            Tag.query.delete()
            
            stats['subgoals_deleted'] = Subgoal.query.count()
            Subgoal.query.delete()
            
            stats['goals_deleted'] = Goal.query.count()
            Goal.query.delete()
            
            stats['users_deleted'] = User.query.count()
            User.query.delete()
        
        db.session.commit()
        
        logger.info(f"Data clear completed: {stats}")
        
        return {
            'success': True,
            'statistics': stats,
            'backup_created': backup_result['backup'],
            'preserve_admin': preserve_admin
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Data clear failed: {str(e)}")
        return {
            'success': False,
            'error': f'Data clear failed: {str(e)}'
        }

def clear_goals_only(preserve_admin_goals=True):
    """
    Delete only goals and related data, keeping user accounts and settings
    
    Args:
        preserve_admin_goals (bool): Whether to preserve goals owned by admin users
    
    Returns:
        dict: Result with success status and cleanup statistics
    """
    try:
        from backend.models import User, Goal, Subgoal, Tag, Event, ProgressEntry
        
        stats = {
            'goals_deleted': 0,
            'subgoals_deleted': 0,
            'tags_deleted': 0,
            'goal_events_deleted': 0,
            'progress_entries_deleted': 0
        }
        
        # Create backup before clearing data
        backup_name = f"pre_clear_goals_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        backup_result = create_database_backup(
            backup_name=backup_name,
            backup_type='pre_update'
        )
        
        if not backup_result['success']:
            return {
                'success': False,
                'error': f'Failed to create pre-clear backup: {backup_result["error"]}'
            }
        
        logger.info(f"Starting goals-only clear (preserve_admin_goals={preserve_admin_goals})")
        
        if preserve_admin_goals:
            # Get admin user IDs
            admin_user_ids = [user.id for user in User.query.filter_by(role='admin').all()]
            
            # Delete goals not owned by admins
            non_admin_goals = Goal.query.filter(
                ~Goal.owner_id.in_(admin_user_ids) & ~Goal.user_id.in_(admin_user_ids)
            ).all()
            
            for goal in non_admin_goals:
                # Count and delete subgoals
                stats['subgoals_deleted'] += len(goal.subgoals)
                
                # Delete goal-related events
                goal_events = Event.query.filter_by(entity_type='goal', entity_id=goal.id).all()
                for event in goal_events:
                    db.session.delete(event)
                    stats['goal_events_deleted'] += 1
                
                # Delete subgoal-related events
                for subgoal in goal.subgoals:
                    subgoal_events = Event.query.filter_by(entity_type='subgoal', entity_id=subgoal.id).all()
                    for event in subgoal_events:
                        db.session.delete(event)
                        stats['goal_events_deleted'] += 1
                
                # Delete the goal (cascade will handle subgoals)
                db.session.delete(goal)
                stats['goals_deleted'] += 1
            
            # Delete tags not owned by admins
            non_admin_tags = Tag.query.filter(~Tag.user_id.in_(admin_user_ids)).all()
            for tag in non_admin_tags:
                db.session.delete(tag)
                stats['tags_deleted'] += 1
            
            # Delete progress entries not belonging to admin users
            non_admin_progress = ProgressEntry.query.join(Goal).filter(~Goal.user_id.in_(admin_user_ids)).all()
            for entry in non_admin_progress:
                db.session.delete(entry)
                stats['progress_entries_deleted'] += 1
        else:
            # Delete all goals and related data
            # Delete goal and subgoal events
            goal_events = Event.query.filter(Event.entity_type.in_(['goal', 'subgoal'])).all()
            for event in goal_events:
                db.session.delete(event)
                stats['goal_events_deleted'] += 1
            
            # Delete progress entries
            stats['progress_entries_deleted'] = ProgressEntry.query.count()
            ProgressEntry.query.delete()
            
            # Delete tags
            stats['tags_deleted'] = Tag.query.count()
            Tag.query.delete()
            
            # Count subgoals before deletion
            stats['subgoals_deleted'] = Subgoal.query.count()
            
            # Delete goals (cascade will handle subgoals)
            stats['goals_deleted'] = Goal.query.count()
            Goal.query.delete()
        
        db.session.commit()
        
        logger.info(f"Goals clear completed: {stats}")
        
        return {
            'success': True,
            'statistics': stats,
            'backup_created': backup_result['backup'],
            'preserve_admin_goals': preserve_admin_goals
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Goals clear failed: {str(e)}")
        return {
            'success': False,
            'error': f'Goals clear failed: {str(e)}'
        }

def clear_everything_except_admin():
    """
    Nuclear option: Delete everything except admin users and system settings
    
    Returns:
        dict: Result with success status and cleanup statistics
    """
    try:
        from backend.models import User, Goal, Subgoal, Tag, Event, UserSession, ProgressEntry
        
        stats = {
            'users_deleted': 0,
            'goals_deleted': 0,
            'subgoals_deleted': 0,
            'tags_deleted': 0,
            'events_deleted': 0,
            'sessions_deleted': 0,
            'progress_entries_deleted': 0
        }
        
        # Create backup before clearing data
        backup_name = f"pre_clear_nuclear_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        backup_result = create_database_backup(
            backup_name=backup_name,
            backup_type='pre_update'
        )
        
        if not backup_result['success']:
            return {
                'success': False,
                'error': f'Failed to create pre-clear backup: {backup_result["error"]}'
            }
        
        logger.info("Starting nuclear clear (preserve admin users and system settings only)")
        
        # Get admin user IDs to preserve
        admin_user_ids = [user.id for user in User.query.filter_by(role='admin').all()]
        
        if not admin_user_ids:
            return {
                'success': False,
                'error': 'No admin users found. Cannot proceed with nuclear clear to prevent lockout.'
            }
        
        # Delete ALL data for non-admin users
        non_admin_users = User.query.filter(~User.id.in_(admin_user_ids)).all()
        for user in non_admin_users:
            # Delete user's goals and subgoals
            user_goals = Goal.query.filter(
                (Goal.user_id == user.id) | (Goal.owner_id == user.id)
            ).all()
            for goal in user_goals:
                stats['subgoals_deleted'] += len(goal.subgoals)
                db.session.delete(goal)
                stats['goals_deleted'] += 1
            
            # Delete user's tags
            user_tags = Tag.query.filter_by(user_id=user.id).all()
            for tag in user_tags:
                db.session.delete(tag)
                stats['tags_deleted'] += 1
            
            # Delete user's events
            user_events = Event.query.filter_by(user_id=user.id).all()
            for event in user_events:
                db.session.delete(event)
                stats['events_deleted'] += 1
            
            # Delete user's sessions
            user_sessions = UserSession.query.filter_by(user_id=user.id).all()
            for session in user_sessions:
                db.session.delete(session)
                stats['sessions_deleted'] += 1
            
            # Delete user's progress entries
            user_progress = ProgressEntry.query.join(Goal).filter(Goal.user_id == user.id).all()
            for entry in user_progress:
                db.session.delete(entry)
                stats['progress_entries_deleted'] += 1
            
            # Delete the user
            db.session.delete(user)
            stats['users_deleted'] += 1
        
        # Also delete ALL goals, even admin goals (goals only clear)
        admin_goals = Goal.query.filter(
            (Goal.user_id.in_(admin_user_ids)) | (Goal.owner_id.in_(admin_user_ids))
        ).all()
        for goal in admin_goals:
            stats['subgoals_deleted'] += len(goal.subgoals)
            db.session.delete(goal)
            stats['goals_deleted'] += 1
        
        # Delete admin tags
        admin_tags = Tag.query.filter(Tag.user_id.in_(admin_user_ids)).all()
        for tag in admin_tags:
            db.session.delete(tag)
            stats['tags_deleted'] += 1
        
        # Delete admin progress entries  
        admin_progress = ProgressEntry.query.join(Goal).filter(Goal.user_id.in_(admin_user_ids)).all()
        for entry in admin_progress:
            db.session.delete(entry)
            stats['progress_entries_deleted'] += 1
        
        # Delete admin events (but preserve system events if any)
        admin_events = Event.query.filter(Event.user_id.in_(admin_user_ids)).all()
        for event in admin_events:
            db.session.delete(event)
            stats['events_deleted'] += 1
        
        # Delete admin sessions
        admin_sessions = UserSession.query.filter(UserSession.user_id.in_(admin_user_ids)).all()
        for session in admin_sessions:
            db.session.delete(session)
            stats['sessions_deleted'] += 1
        
        db.session.commit()
        
        logger.info(f"Nuclear clear completed: {stats}")
        
        return {
            'success': True,
            'statistics': stats,
            'backup_created': backup_result['backup'],
            'preserved_admin_count': len(admin_user_ids)
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Nuclear clear failed: {str(e)}")
        return {
            'success': False,
            'error': f'Nuclear clear failed: {str(e)}'
        }