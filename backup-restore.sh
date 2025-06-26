#!/bin/bash

# LetsGoal Database Backup and Restore Utilities
# Handles SQLite database backup, restore, and maintenance operations

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Default configuration
INSTALL_DIR="/opt/letsgoal"
DATABASE_PATH="$INSTALL_DIR/database/letsgoal.db"
BACKUP_DIR="$INSTALL_DIR/backups"
CONTAINER_NAME="letsgoal-backend"
RETENTION_DAYS=30

# Remote backup configuration
REMOTE_BACKUP_ENABLED=false
REMOTE_BACKUP_TYPE=""
REMOTE_BACKUP_BUCKET=""
REMOTE_BACKUP_PREFIX="letsgoal-backups/"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}"
    echo "================================================================================"
    echo "                    LetsGoal Database Backup & Restore"
    echo "================================================================================"
    echo -e "${NC}"
}

load_config() {
    local config_file="$INSTALL_DIR/.env"
    
    if [[ -f "$config_file" ]]; then
        log_info "Loading configuration from $config_file..."
        
        # Source the environment file
        set -a
        source "$config_file"
        set +a
        
        # Update paths from environment
        DATABASE_PATH="${DATABASE_URL#sqlite://}"
        BACKUP_DIR="${BACKUP_LOCATION:-$BACKUP_DIR}"
        RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-$RETENTION_DAYS}"
        
        # Remote backup settings
        REMOTE_BACKUP_ENABLED="${REMOTE_BACKUP_ENABLED:-false}"
        REMOTE_BACKUP_TYPE="${REMOTE_BACKUP_TYPE:-}"
        REMOTE_BACKUP_BUCKET="${REMOTE_BACKUP_BUCKET:-}"
        REMOTE_BACKUP_PREFIX="${REMOTE_BACKUP_PREFIX:-letsgoal-backups/}"
    else
        log_warning "Configuration file not found, using defaults"
    fi
}

check_dependencies() {
    # Check if SQLite is available
    if ! command -v sqlite3 &> /dev/null; then
        log_error "SQLite3 is not installed"
        exit 1
    fi
    
    # Check if Docker is available and container exists
    if command -v docker &> /dev/null; then
        if docker ps -a --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
            log_info "Docker container found: $CONTAINER_NAME"
        else
            log_warning "Docker container not found: $CONTAINER_NAME"
        fi
    fi
    
    # Check for remote backup dependencies
    if [[ "$REMOTE_BACKUP_ENABLED" == "true" ]]; then
        case "$REMOTE_BACKUP_TYPE" in
            "s3")
                if ! command -v aws &> /dev/null; then
                    log_error "AWS CLI is required for S3 backups but not installed"
                    exit 1
                fi
                ;;
            "gcs")
                if ! command -v gsutil &> /dev/null; then
                    log_error "Google Cloud SDK is required for GCS backups but not installed"
                    exit 1
                fi
                ;;
        esac
    fi
}

create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_info "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
        chmod 755 "$BACKUP_DIR"
    fi
}

stop_application() {
    local should_stop="${1:-true}"
    
    if [[ "$should_stop" == "true" ]] && command -v docker &> /dev/null; then
        if docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
            log_info "Stopping application container..."
            docker stop "$CONTAINER_NAME" || log_warning "Failed to stop container"
        fi
    fi
}

start_application() {
    local should_start="${1:-true}"
    
    if [[ "$should_start" == "true" ]] && command -v docker &> /dev/null; then
        if docker ps -a --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
            log_info "Starting application container..."
            docker start "$CONTAINER_NAME" || log_warning "Failed to start container"
        fi
    fi
}

create_backup() {
    local backup_name="${1:-}"
    local stop_app="${2:-true}"
    local timestamp
    local backup_file
    local temp_backup
    
    timestamp=$(date +%Y%m%d_%H%M%S)
    
    if [[ -n "$backup_name" ]]; then
        backup_file="$BACKUP_DIR/${backup_name}_${timestamp}.db"
    else
        backup_file="$BACKUP_DIR/letsgoal_backup_${timestamp}.db"
    fi
    
    temp_backup="${backup_file}.tmp"
    
    log_info "Creating database backup..."
    log_info "Source: $DATABASE_PATH"
    log_info "Destination: $backup_file"
    
    # Ensure database exists
    if [[ ! -f "$DATABASE_PATH" ]]; then
        log_error "Database file not found: $DATABASE_PATH"
        return 1
    fi
    
    # Create backup directory
    create_backup_dir
    
    # Stop application for consistent backup
    stop_application "$stop_app"
    
    # Create backup using SQLite backup command for consistency
    log_info "Creating SQLite backup..."
    if sqlite3 "$DATABASE_PATH" ".backup '$temp_backup'"; then
        # Move temp backup to final location
        mv "$temp_backup" "$backup_file"
        
        # Verify backup integrity
        if sqlite3 "$backup_file" "PRAGMA integrity_check;" | grep -q "ok"; then
            log_success "Database backup created successfully: $backup_file"
            
            # Get backup file size
            local size
            size=$(du -h "$backup_file" | cut -f1)
            log_info "Backup size: $size"
            
            # Create metadata file
            create_backup_metadata "$backup_file"
            
            # Upload to remote storage if enabled
            if [[ "$REMOTE_BACKUP_ENABLED" == "true" ]]; then
                upload_remote_backup "$backup_file"
            fi
            
            echo "$backup_file"
        else
            log_error "Backup integrity check failed"
            rm -f "$backup_file"
            start_application "$stop_app"
            return 1
        fi
    else
        log_error "Failed to create database backup"
        rm -f "$temp_backup"
        start_application "$stop_app"
        return 1
    fi
    
    # Start application
    start_application "$stop_app"
}

create_backup_metadata() {
    local backup_file="$1"
    local metadata_file="${backup_file}.meta"
    
    log_info "Creating backup metadata..."
    
    cat > "$metadata_file" << EOF
{
    "backup_file": "$(basename "$backup_file")",
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "database_path": "$DATABASE_PATH",
    "file_size": $(stat -c%s "$backup_file" 2>/dev/null || stat -f%z "$backup_file"),
    "md5_hash": "$(md5sum "$backup_file" 2>/dev/null | cut -d' ' -f1 || md5 -q "$backup_file")",
    "sqlite_version": "$(sqlite3 --version | cut -d' ' -f1)",
    "hostname": "$(hostname)",
    "backup_type": "full",
    "compression": "none"
}
EOF

    log_success "Backup metadata created: $metadata_file"
}

restore_backup() {
    local backup_file="$1"
    local stop_app="${2:-true}"
    local force="${3:-false}"
    
    log_info "Restoring database from backup..."
    log_info "Backup file: $backup_file"
    log_info "Target: $DATABASE_PATH"
    
    # Verify backup file exists
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Verify backup integrity
    log_info "Verifying backup integrity..."
    if ! sqlite3 "$backup_file" "PRAGMA integrity_check;" | grep -q "ok"; then
        log_error "Backup file is corrupted"
        return 1
    fi
    
    # Create backup of current database if it exists
    if [[ -f "$DATABASE_PATH" && "$force" != "true" ]]; then
        log_info "Creating backup of current database..."
        local current_backup
        current_backup=$(create_backup "pre_restore" false)
        log_info "Current database backed up to: $current_backup"
    fi
    
    # Stop application
    stop_application "$stop_app"
    
    # Ensure target directory exists
    mkdir -p "$(dirname "$DATABASE_PATH")"
    
    # Restore database
    log_info "Restoring database..."
    if cp "$backup_file" "$DATABASE_PATH"; then
        # Set proper permissions
        chmod 644 "$DATABASE_PATH"
        
        # Verify restored database
        if sqlite3 "$DATABASE_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
            log_success "Database restored successfully"
            
            # Show restoration info
            local tables_count
            tables_count=$(sqlite3 "$DATABASE_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
            log_info "Restored database contains $tables_count tables"
            
        else
            log_error "Restored database failed integrity check"
            start_application "$stop_app"
            return 1
        fi
    else
        log_error "Failed to copy backup file"
        start_application "$stop_app"
        return 1
    fi
    
    # Start application
    start_application "$stop_app"
}

list_backups() {
    local detailed="${1:-false}"
    
    log_info "Available backups in $BACKUP_DIR:"
    echo ""
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warning "Backup directory does not exist"
        return 0
    fi
    
    local backup_files
    backup_files=$(find "$BACKUP_DIR" -name "*.db" -type f | sort -r)
    
    if [[ -z "$backup_files" ]]; then
        log_warning "No backup files found"
        return 0
    fi
    
    local count=0
    while IFS= read -r backup_file; do
        if [[ -f "$backup_file" ]]; then
            count=$((count + 1))
            local filename
            local size
            local date_created
            local age
            
            filename=$(basename "$backup_file")
            size=$(du -h "$backup_file" | cut -f1)
            date_created=$(date -r "$backup_file" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c %y "$backup_file" | cut -d' ' -f1-2)
            age=$(find "$backup_file" -mtime +0 -exec echo "$(( ($(date +%s) - $(date -r {} +%s)) / 86400 )) days ago" \; 2>/dev/null || echo "unknown")
            
            if [[ "$detailed" == "true" ]]; then
                echo -e "${GREEN}$count.${NC} $filename"
                echo "   Size: $size"
                echo "   Created: $date_created ($age)"
                echo "   Path: $backup_file"
                
                # Show metadata if available
                local metadata_file="${backup_file}.meta"
                if [[ -f "$metadata_file" ]]; then
                    local md5_hash
                    md5_hash=$(jq -r '.md5_hash' "$metadata_file" 2>/dev/null || echo "unknown")
                    echo "   MD5: $md5_hash"
                fi
                echo ""
            else
                echo -e "${GREEN}$count.${NC} $filename ($size, $date_created)"
            fi
        fi
    done <<< "$backup_files"
    
    echo ""
    log_info "Total backups: $count"
}

cleanup_old_backups() {
    local days="${1:-$RETENTION_DAYS}"
    local dry_run="${2:-false}"
    
    log_info "Cleaning up backups older than $days days..."
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warning "Backup directory does not exist"
        return 0
    fi
    
    local old_files
    old_files=$(find "$BACKUP_DIR" -name "*.db" -type f -mtime +$days)
    
    if [[ -z "$old_files" ]]; then
        log_info "No old backup files found"
        return 0
    fi
    
    local count=0
    while IFS= read -r old_file; do
        if [[ -f "$old_file" ]]; then
            count=$((count + 1))
            local filename
            local age_days
            
            filename=$(basename "$old_file")
            age_days=$(( ($(date +%s) - $(date -r "$old_file" +%s)) / 86400 ))
            
            if [[ "$dry_run" == "true" ]]; then
                echo "Would delete: $filename (${age_days} days old)"
            else
                log_info "Deleting old backup: $filename (${age_days} days old)"
                rm -f "$old_file"
                rm -f "${old_file}.meta"  # Remove metadata file too
            fi
        fi
    done <<< "$old_files"
    
    if [[ "$dry_run" == "true" ]]; then
        log_info "Dry run: Would delete $count old backup files"
    else
        log_success "Deleted $count old backup files"
    fi
}

upload_remote_backup() {
    local backup_file="$1"
    local remote_path
    
    if [[ "$REMOTE_BACKUP_ENABLED" != "true" ]]; then
        return 0
    fi
    
    log_info "Uploading backup to remote storage..."
    
    case "$REMOTE_BACKUP_TYPE" in
        "s3")
            remote_path="s3://$REMOTE_BACKUP_BUCKET/$REMOTE_BACKUP_PREFIX$(basename "$backup_file")"
            if aws s3 cp "$backup_file" "$remote_path"; then
                log_success "Backup uploaded to S3: $remote_path"
                
                # Upload metadata file too
                local metadata_file="${backup_file}.meta"
                if [[ -f "$metadata_file" ]]; then
                    aws s3 cp "$metadata_file" "s3://$REMOTE_BACKUP_BUCKET/$REMOTE_BACKUP_PREFIX$(basename "$metadata_file")"
                fi
            else
                log_error "Failed to upload backup to S3"
            fi
            ;;
        "gcs")
            remote_path="gs://$REMOTE_BACKUP_BUCKET/$REMOTE_BACKUP_PREFIX$(basename "$backup_file")"
            if gsutil cp "$backup_file" "$remote_path"; then
                log_success "Backup uploaded to GCS: $remote_path"
                
                # Upload metadata file too
                local metadata_file="${backup_file}.meta"
                if [[ -f "$metadata_file" ]]; then
                    gsutil cp "$metadata_file" "gs://$REMOTE_BACKUP_BUCKET/$REMOTE_BACKUP_PREFIX$(basename "$metadata_file")"
                fi
            else
                log_error "Failed to upload backup to GCS"
            fi
            ;;
        *)
            log_warning "Unknown remote backup type: $REMOTE_BACKUP_TYPE"
            ;;
    esac
}

verify_database() {
    local db_file="${1:-$DATABASE_PATH}"
    
    log_info "Verifying database integrity..."
    
    if [[ ! -f "$db_file" ]]; then
        log_error "Database file not found: $db_file"
        return 1
    fi
    
    # Check integrity
    if sqlite3 "$db_file" "PRAGMA integrity_check;" | grep -q "ok"; then
        log_success "Database integrity check passed"
    else
        log_error "Database integrity check failed"
        return 1
    fi
    
    # Check foreign key constraints
    if sqlite3 "$db_file" "PRAGMA foreign_key_check;" | grep -q "."; then
        log_warning "Foreign key constraint violations found"
    else
        log_success "Foreign key constraints are valid"
    fi
    
    # Show basic statistics
    local tables_count
    local total_size
    
    tables_count=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
    total_size=$(du -h "$db_file" | cut -f1)
    
    log_info "Database statistics:"
    echo "  Tables: $tables_count"
    echo "  Size: $total_size"
    echo "  File: $db_file"
}

usage() {
    echo "LetsGoal Database Backup & Restore Utilities"
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  backup [NAME]              Create a new backup (optional custom name)"
    echo "  restore BACKUP_FILE        Restore from backup file"
    echo "  list [--detailed]          List available backups"
    echo "  cleanup [DAYS]             Remove backups older than DAYS (default: $RETENTION_DAYS)"
    echo "  verify [DATABASE_FILE]     Verify database integrity"
    echo "  status                     Show backup system status"
    echo ""
    echo "Options:"
    echo "  --no-stop                  Don't stop/start the application"
    echo "  --force                    Force restore without creating current backup"
    echo "  --dry-run                  Show what would be done (cleanup only)"
    echo "  --config FILE              Use custom configuration file"
    echo "  --help                     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 backup                                    # Create automatic backup"
    echo "  $0 backup before_update                      # Create named backup"
    echo "  $0 restore /path/to/backup.db                # Restore from specific backup"
    echo "  $0 list --detailed                           # Show detailed backup list"
    echo "  $0 cleanup 7                                 # Delete backups older than 7 days"
    echo "  $0 verify                                    # Check current database"
}

show_status() {
    print_header
    
    echo -e "${BLUE}Backup System Status${NC}"
    echo "----------------------------------------"
    echo "Database Path: $DATABASE_PATH"
    echo "Backup Directory: $BACKUP_DIR"
    echo "Container Name: $CONTAINER_NAME"
    echo "Retention Days: $RETENTION_DAYS"
    echo "Remote Backup: $REMOTE_BACKUP_ENABLED"
    if [[ "$REMOTE_BACKUP_ENABLED" == "true" ]]; then
        echo "Remote Type: $REMOTE_BACKUP_TYPE"
        echo "Remote Bucket: $REMOTE_BACKUP_BUCKET"
    fi
    echo ""
    
    # Check database status
    if [[ -f "$DATABASE_PATH" ]]; then
        echo -e "${GREEN}✓${NC} Database file exists"
        local db_size
        db_size=$(du -h "$DATABASE_PATH" | cut -f1)
        echo "  Size: $db_size"
        echo "  Modified: $(date -r "$DATABASE_PATH" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c %y "$DATABASE_PATH" | cut -d' ' -f1-2)"
    else
        echo -e "${RED}✗${NC} Database file not found"
    fi
    
    # Check backup directory
    if [[ -d "$BACKUP_DIR" ]]; then
        echo -e "${GREEN}✓${NC} Backup directory exists"
        local backup_count
        backup_count=$(find "$BACKUP_DIR" -name "*.db" -type f | wc -l)
        echo "  Backup count: $backup_count"
        if [[ $backup_count -gt 0 ]]; then
            local latest_backup
            latest_backup=$(find "$BACKUP_DIR" -name "*.db" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
            echo "  Latest backup: $(basename "$latest_backup")"
        fi
    else
        echo -e "${YELLOW}!${NC} Backup directory does not exist"
    fi
    
    # Check container status
    if command -v docker &> /dev/null; then
        if docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
            echo -e "${GREEN}✓${NC} Application container is running"
        elif docker ps -a --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
            echo -e "${YELLOW}!${NC} Application container exists but is stopped"
        else
            echo -e "${RED}✗${NC} Application container not found"
        fi
    else
        echo -e "${YELLOW}!${NC} Docker not available"
    fi
}

main() {
    local command=""
    local no_stop=false
    local force=false
    local dry_run=false
    local detailed=false
    local custom_config=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            backup|restore|list|cleanup|verify|status)
                command="$1"
                shift
                ;;
            --no-stop)
                no_stop=true
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --detailed)
                detailed=true
                shift
                ;;
            --config)
                custom_config="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                break
                ;;
        esac
    done
    
    # Load configuration
    if [[ -n "$custom_config" ]]; then
        INSTALL_DIR="$(dirname "$custom_config")"
    fi
    load_config
    
    # Check dependencies
    check_dependencies
    
    # Execute command
    case "$command" in
        backup)
            local backup_name="${1:-}"
            create_backup "$backup_name" "$([ "$no_stop" = "true" ] && echo false || echo true)"
            ;;
        restore)
            if [[ -z "${1:-}" ]]; then
                log_error "Backup file path required for restore"
                usage
                exit 1
            fi
            restore_backup "$1" "$([ "$no_stop" = "true" ] && echo false || echo true)" "$force"
            ;;
        list)
            list_backups "$detailed"
            ;;
        cleanup)
            local days="${1:-$RETENTION_DAYS}"
            cleanup_old_backups "$days" "$dry_run"
            ;;
        verify)
            local db_file="${1:-$DATABASE_PATH}"
            verify_database "$db_file"
            ;;
        status)
            show_status
            ;;
        "")
            log_error "Command required"
            usage
            exit 1
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"