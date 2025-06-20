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

### Database Operations
```bash
# Apply all pending migrations
cd backend/migrations && python add_event_tracking.py && python add_tagging_system.py

# Access SQLite database directly
sqlite3 database/letsgoal.db

# Common database queries
.tables  # List all tables
.schema goals  # Show schema for goals table
SELECT * FROM users;  # Query users
```

## Architecture Overview

### Backend Structure
- **Flask application** with factory pattern (`backend/app.py`)
- **SQLAlchemy models**: User, Goal, Subgoal, ProgressEntry, Event, Tag (`backend/models.py`)
- **Authentication blueprint** with Flask-Login (`backend/auth.py`)
- **Event tracking system** with comprehensive activity logging (`backend/event_tracker.py`)
- **SQLite database** with automatic schema creation and migrations
- **RESTful API endpoints** for goal management, tagging, and dashboard stats (25+ endpoints)
- **Migration system** for database schema evolution (`backend/migrations/` directory)

### Frontend Structure
- **Static file serving** through Flask (no separate frontend server)
- **Vanilla JavaScript** with modular structure:
  - `frontend/js/auth.js` - Authentication utilities and login/register
  - `frontend/js/dashboard.js` - Goal management, progress tracking, Chart.js integration (49K+ tokens)
- **Tailwind CSS** for styling with custom CSS in `frontend/css/styles.css`
- **Two main pages**: `login.html` and `dashboard.html`

### Key Data Flow
1. **Goal-Subgoal Relationship**: Goals contain subgoals; goal progress auto-updates based on subgoal completion
2. **Automatic Status Updates**: Goal status changes from "created" → "started" → "working" → "completed" based on subgoal completion percentage
3. **Real-time Updates**: Frontend updates progress bars, charts, and stats immediately after subgoal changes
4. **Progress Chart**: Shows 7-day trends of completed subgoals and goals using Chart.js line chart
5. **Daily Quote Rotation**: 350 unique motivational quotes displayed based on days since epoch

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
- **Visual tag filter bar**: Permanent filter interface with clickable colored badges replacing dropdown
- **Tag filtering**: Dashboard supports filtering goals by selected tags with visual feedback

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
- **Health checks** monitor application status with `/health` endpoint
- **Environment variables** configure Flask and database paths
- **Port mapping**: Container port 5000 → Host port 5001

### UI Interaction Patterns
- **Clickable subgoal titles**: Clicking subgoal text toggles checkbox state
- **Dedicated Edit button**: Goal cards use dedicated Edit button instead of click-to-edit
- **Position-based hover expansion**: Goal cards show hidden subgoals (4+) when mouse moves below quick add input
- **Real-time progress**: Progress circles update immediately using conic-gradient backgrounds

### Critical Design Decisions
- **No competing stacking contexts**: Removed `translateZ(0)`, `isolation`, and `contain` properties from goal cards to prevent dropdown z-index issues
- **Subgoal status synchronization**: Backend automatically updates goal status and achieved_date when subgoals change
- **Progress calculation**: `goal.progress = (completed_subgoals / total_subgoals) × 100` with automatic status transitions
- **Optimistic UI updates**: Frontend updates immediately, then syncs with backend for consistency

### CSS Architecture
- **Grid layout**: 4-column responsive grid with `minmax(320px, 1fr)` for goal cards
- **Controlled expansion**: JavaScript-driven `.sticky-hover` class controls card expansion, no CSS `:hover`
- **Z-index hierarchy**: Dropdowns (`z-index: 9999`) > expanded cards (`z-index: 2`) > normal cards (`z-index: 1`)
- **Conic-gradient progress**: `conic-gradient(color deg, background deg)` for smooth progress circles

### API Endpoints Pattern
- **Authentication**: `/api/auth/login`, `/api/auth/logout`, `/api/auth/register`
- **Goals**: `/api/goals` (GET/POST), `/api/goals/<id>` (PUT/DELETE)
- **Subgoals**: `/api/goals/<id>/subgoals` (POST), `/api/subgoals/<id>` (PUT/DELETE)
- **Tags**: `/api/tags` (GET/POST), `/api/tags/<id>` (PUT/DELETE)
- **Stats**: `/api/stats/dashboard`, `/api/stats/recent-activity`
- **Error handling**: API responses include `success` boolean and `message` for user feedback

### Performance Considerations
- **Lazy loading**: Goals loaded on-demand with pagination support for large datasets
- **Debounced operations**: Search and filter inputs use 300ms debounce
- **Memory management**: Chart.js instances destroyed/recreated to prevent memory leaks
- **Database indexing**: Strategic indexes on user_id, goal relationships, and timestamps
- **Optimized queries**: SQLAlchemy relationships configured for efficient loading

### Navbar Design System
- **Modern minimalist design** with Concept 1: floating elements and gradient backgrounds
- **Breathing lotus logo**: 72x72px animated SVG with complex breathing animations (8s cycles)
  - Multiple animation layers: breathing core, petal scaling, completion markers, energy rings
  - Built-in SVG animations with no hover effects for meditative stability
  - Gradient definitions: `breath1` (purple spectrum), `breath2` (cyan-blue), `breathCore` (radial white-gold-coral)
- **Floating quote bubble**: Glassmorphism design with Inter font
  - 6-second gentle floating animation with 2px vertical movement
  - Backdrop blur (15px) with gradient background (15% to 5% white opacity)
  - Typography: Inter font, 0.875rem, slate-600 color, normal weight
  - Decorative quotation marks positioned with CSS pseudo-elements
  - Daily rotation through 350 unique motivational quotes
- **Gradient navbar background**: `bg-gradient-to-r from-blue-50 to-indigo-50`
- **Brand typography**: Gradient text effect `from-blue-600 to-purple-600`

### Animation Architecture
- **Lotus breathing cycle**: 8-second meditative rhythm with multiple synchronized layers
- **Quote floating**: 6-second gentle vertical movement for peaceful UI
- **No hover interactions**: Logo and quote maintain stable, non-reactive behavior
- **CSS keyframes**: `lotus-glow`, `float-gentle`, `quote-pulse` for smooth animations
- **Performance optimized**: Hardware-accelerated transforms and SVG animations

### Theme System Architecture
- **Data-attribute based**: Uses `data-theme="dark"` on HTML element for theme switching
- **CSS Custom Properties**: 60+ variables for comprehensive theming (--color-bg-primary, --color-text-primary, etc.)
- **Smart initialization**: User preference → System preference → Light default
- **Persistent storage**: `localStorage.getItem('theme')` for preference retention
- **System integration**: Automatically responds to OS theme changes when no manual preference exists
- **Smooth transitions**: Global 0.3s ease transitions for all theme-related properties
- **Tailwind overrides**: High-specificity CSS rules to force dark mode on stubborn Tailwind classes
- **Component theming**: Special handling for Chart.js, SVG gradients, and progress circles in dark mode

### Goal Card Layout System
- **Consistent heights**: Uses CSS Grid `minmax(350px, auto)` with spacer elements for uniform card appearance
- **Subgoal sorting**: `sortSubgoalsForDisplay()` function moves completed subgoals to bottom of lists
- **Position-based expansion**: Cards expand when mouse moves below quick add input without breaking grid layout
- **Dynamic subgoal rendering**: Only first 3 subgoals rendered initially; hidden subgoals created dynamically on expansion to prevent spacing issues
- **Progressive disclosure**: First 3 subgoals visible, remainder shown with "+N more (hover to expand)" hint

### Advanced Hover Animation System
- **3-frame expansion**: Hidden subgoals animate through 33% → 66% → 100% height with GPU-optimized transitions
- **Staggered timing**: 30ms delays between each subgoal start, 30ms between animation frames within each subgoal
- **Dynamic DOM management**: Hidden subgoals created from JSON data on expansion, removed from DOM during collapse
- **Performance optimized**: Uses `requestAnimationFrame`, CSS `will-change`, and `transform3d` for 60fps animations
- **Memory leak prevention**: All dynamically created elements cleaned up during collapse animation
- **Interaction handling**: Maintains expansion during checkbox clicks, input focus, and form interactions

### Tag Filter Bar System
- **Permanent visibility**: Tag filter bar is always visible as extension of search filter bar
- **Visual tag badges**: Colored clickable badges (`.tag-filter-bar-badge`) with hover and active states
- **Responsive grid**: Automatically adapts from 2-8 columns based on screen size
- **Selection animations**: Tags animate on click with `.selecting` class and scale effect
- **State management**: `currentTagFilter` variable tracks active filter, syncs with localStorage
- **Reset functionality**: Reset button always enabled for consistent UX
- **Integration**: Uses `selectTagFromBar(tagId)` for filtering, `populateTagFilterBar()` for rendering
- **No dropdown fallback**: Tag filter dropdown completely removed in favor of permanent bar

### Common Issues
- **Modal conflicts**: Inline forms used instead of nested modals
- **Form validation**: Hidden required fields can cause "invalid form control" errors
- **Progress updates**: Use `updateGoalProgressBar()` for individual updates vs `renderGoals()` for full refresh
- **Chart updates**: Always call `generateRecentProgressData()` for fresh trend data
- **Dropdown clipping**: Ensure parent containers have `overflow: visible` for dropdowns
- **Tag color validation**: Ensure hex color format (#RRGGBB) when creating/updating tags
- **Tag filter synchronization**: Always call `populateTagFilterBar()` after tag CRUD operations
- **Event tracking**: All model changes automatically trigger event logging - no manual event creation needed
- **SVG gradient IDs**: Ensure unique gradient IDs (breath1, breath2, breathCore) don't conflict with other SVGs
- **Animation performance**: Lotus uses transform and filter animations for optimal GPU acceleration
- **Subgoal ordering**: Always use `sortSubgoalsForDisplay()` when rendering subgoal lists to maintain completed-at-bottom behavior
- **Dark mode compatibility**: When updating progress circles or charts, use theme-aware background colors via `document.documentElement.getAttribute('data-theme')`
- **Position-based hover**: Use `isMouseBelowQuickInput()` helper function to check if expansion should trigger
- **Sticky hover state**: Track expansion state with `isExpanded` variable to prevent flickering during mouse movement
- **Spacing accumulation**: Hidden subgoals must have `margin: 0` in CSS to prevent accumulated spacing proportional to subgoal count
- **DOM cleanup timing**: Remove dynamically created subgoals immediately after collapse animation completes, not in batch cleanup
- **Quote duplicates**: Ensure all 350 quotes in `motivationalQuotes` array are unique to prevent repetition