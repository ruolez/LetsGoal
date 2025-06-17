# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment

### Starting the Application
```bash
# Start the application with Docker
docker-compose up --build -d

# Access the application
open http://localhost:5001
```

### Development Commands
```bash
# Rebuild and restart after code changes
docker-compose down && docker-compose up --build -d

# View application logs
docker logs letsgoal-backend

# View recent logs
docker logs letsgoal-backend --tail 20

# Stop the application
docker-compose down
```

### Running Tests
```bash
# Run all tests
cd tests && python -m pytest

# Run specific test file
cd tests && python test_auth.py

# Run specific test class
cd tests && python -m pytest test_goals.py::GoalTestCase
```

### Database Migrations
```bash
# Apply all pending migrations
cd migrations && python migrate.py

# Run specific migration
cd migrations && python add_event_tracking.py

# Rollback migration (development only)
cd migrations && python rollback_event_tracking.py
```

## Architecture Overview

### Backend Structure
- **Flask application** with factory pattern (`backend/app.py`)
- **SQLAlchemy models**: User, Goal, Subgoal, ProgressEntry, Event, Tag (`backend/models.py`)
- **Authentication blueprint** with Flask-Login (`backend/auth.py`)
- **Event tracking system** with comprehensive activity logging (`backend/event_tracker.py`)
- **SQLite database** with automatic schema creation and migrations
- **RESTful API endpoints** for goal management, tagging, and dashboard stats (25+ endpoints)
- **Migration system** for database schema evolution (`migrations/` directory)

### Frontend Structure
- **Static file serving** through Flask (no separate frontend server)
- **Vanilla JavaScript** with modular structure:
  - `frontend/js/auth.js` - Authentication utilities and login/register
  - `frontend/js/dashboard.js` - Goal management, progress tracking, Chart.js integration
- **Tailwind CSS** for styling with custom CSS in `frontend/css/styles.css`
- **Two main pages**: `login.html` and `dashboard.html`

### Key Data Flow
1. **Goal-Subgoal Relationship**: Goals contain subgoals; goal progress auto-updates based on subgoal completion
2. **Automatic Status Updates**: Goal status changes from "created" → "started" → "working" → "completed" based on subgoal completion percentage
3. **Real-time Updates**: Frontend updates progress bars, charts, and stats immediately after subgoal changes
4. **Progress Chart**: Shows 7-day trends of completed subgoals and goals using Chart.js line chart

### Database Schema
- **Users**: Basic auth with password hashing
- **Goals**: Hierarchical structure with status tracking (created/started/working/completed)
- **Subgoals**: Belong to goals, track individual task completion with order_index
- **ProgressEntry**: Historical progress tracking for reporting features
- **Events**: Comprehensive activity logging with metadata (entity_type, action, field changes)
- **Tags**: User-specific categorization with color coding
- **Goal_Tags**: Many-to-many junction table for goal-tag associations

### Frontend-Backend Communication
- **Session-based authentication** with Flask-Login
- **CORS enabled** for credential-based requests
- **JSON API responses** with error handling
- **Optimistic UI updates** for better user experience

### Modal System
- **Two-panel edit modal**: Goal details on left, subgoals on right
- **Inline subgoal creation**: Avoids modal-in-modal conflicts
- **Form validation**: Client-side validation with server-side fallbacks

### Progress Tracking Logic
- Goal progress = (completed subgoals / total subgoals) × 100
- Goal status auto-updates: 0% = created, >0% = started, partial = working, 100% = completed
- Chart shows recent completion trends, not just status distribution
- Real-time chart updates when subgoals are checked/unchecked

### Tagging System
- **User-specific tags**: Each user maintains their own tag namespace
- **Color coding**: Hex color support for visual organization (#FF5733, #33A1FF, etc.)
- **Many-to-many relationships**: Goals can have multiple tags, tags can be applied to multiple goals
- **Default tag creation**: System creates common tags (Work, Personal, Health, Learning) for new users
- **Tag filtering**: Dashboard supports filtering goals by selected tags

### Event Tracking & Activity System
- **Comprehensive logging**: All CRUD operations on goals/subgoals are tracked
- **Rich metadata**: Events store old/new values, timestamps, and contextual information
- **Activity timeline**: Recent activity display for user engagement insights
- **Audit trail**: Complete history of changes for debugging and analytics

## Development Notes

### JavaScript Architecture
- Functions are globally accessible via `window` object for onclick handlers
- Error handling includes both `authUtils` checks and alert() fallbacks
- Chart.js instance is properly destroyed/recreated to prevent memory leaks
- Defensive programming with null checks for DOM elements
- **Settings persistence**: User preferences stored in localStorage (view mode, filters, etc.)
- **Debounced search**: Real-time filtering with 300ms debounce to prevent excessive API calls
- **Optimistic updates**: UI updates immediately before backend confirmation

### Docker Configuration
- **Volume mounts** enable live code reloading during development
- **Health checks** monitor application status
- **Environment variables** configure Flask and database paths
- **Port mapping**: Container port 5000 → Host port 5001

### UI Interaction Patterns
- **Clickable subgoal titles**: Clicking subgoal text toggles checkbox state
- **Dedicated Edit button**: Goal cards use dedicated Edit button instead of click-to-edit
- **Hover expansion**: Goal cards show hidden subgoals (4+) on hover without modal interference
- **Real-time progress**: Progress circles update immediately using conic-gradient backgrounds

### Critical Design Decisions
- **No competing stacking contexts**: Removed `translateZ(0)`, `isolation`, and `contain` properties from goal cards to prevent dropdown z-index issues
- **Subgoal status synchronization**: Backend automatically updates goal status and achieved_date when subgoals change
- **Progress calculation**: `goal.progress = (completed_subgoals / total_subgoals) × 100` with automatic status transitions
- **Optimistic UI updates**: Frontend updates immediately, then syncs with backend for consistency

### CSS Architecture
- **Grid layout**: 4-column responsive grid with `minmax(320px, 1fr)` for goal cards
- **CSS Grid with hover**: Pure CSS animations without DOM manipulation to prevent flickering
- **Z-index hierarchy**: Dropdowns (`z-index: 9999`) > hover cards (`z-index: 2`) > normal cards (`z-index: 1`)
- **Conic-gradient progress**: `conic-gradient(color deg, background deg)` for smooth progress circles

### API Integration Patterns
- **Authentication check**: Always use `authUtils.ensureAuthenticated()` before API calls
- **Error handling**: API responses include `success` boolean and `message` for user feedback
- **Endpoint naming**: RESTful conventions (`/api/goals`, `/api/goals/<id>/subgoals`, etc.)
- **Data validation**: Both frontend validation and backend validation with error response
- **Session management**: Automatic logout on 401 responses with redirect to login

### Performance Considerations
- **Lazy loading**: Goals loaded on-demand with pagination support for large datasets
- **Debounced operations**: Search and filter inputs use 300ms debounce
- **Memory management**: Chart.js instances destroyed/recreated to prevent memory leaks
- **Database indexing**: Strategic indexes on user_id, goal relationships, and timestamps
- **Optimized queries**: SQLAlchemy relationships configured for efficient loading

### Common Issues
- **Modal conflicts**: Inline forms used instead of nested modals
- **Form validation**: Hidden required fields can cause "invalid form control" errors
- **Progress updates**: Use `updateGoalProgressBar()` for individual updates vs `renderGoals()` for full refresh
- **Chart updates**: Always call `generateRecentProgressData()` for fresh trend data
- **Dropdown clipping**: Ensure parent containers have `overflow: visible` for dropdowns
- **Tag color validation**: Ensure hex color format (#RRGGBB) when creating/updating tags
- **Event tracking**: All model changes automatically trigger event logging - no manual event creation needed