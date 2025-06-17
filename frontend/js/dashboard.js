// Dashboard JavaScript

console.log('🚀 Dashboard.js is loading...'); // Debug log

// Utility function to parse date strings as local dates (fixes timezone issues)
function parseLocalDate(dateString) {
    if (!dateString) return null;
    
    // Handle ISO datetime strings (YYYY-MM-DDTHH:mm:ss) - preserve time for sorting
    if (typeof dateString === 'string' && dateString.includes('T')) {
        // For full datetime strings, use standard Date parsing to preserve time
        return new Date(dateString);
    }
    
    // Handle ISO date strings (YYYY-MM-DD only) 
    if (typeof dateString === 'string' && dateString.includes('-')) {
        const parts = dateString.split('-');
        if (parts.length === 3) {
            const year = parseInt(parts[0]);
            const month = parseInt(parts[1]) - 1; // Month is 0-indexed in JavaScript
            const day = parseInt(parts[2]);
            
            // Validate the date parts
            if (!isNaN(year) && !isNaN(month) && !isNaN(day)) {
                return new Date(year, month, day);
            }
        }
    }
    
    // Fallback to standard Date parsing
    return new Date(dateString);
}

let currentUser = null;
let goals = [];
let tags = [];
let progressChart = null;
let filteredGoals = [];
let currentViewMode = 'grid';
let currentFilter = 'all';
let currentSort = 'recent';
let currentTagFilter = null; // null means show all tags
let selectedTagIds = [];
let currentPage = 0;
const goalsPerPage = 9;

// Track which goal cards should maintain sticky hover state
let stickyHoverStates = new Map();

// ========================
// SETTINGS PERSISTENCE
// ========================

// Default user preferences
const DEFAULT_SETTINGS = {
    viewMode: 'grid',
    filter: 'all',
    sort: 'recent',
    tagFilter: null,
    page: 0,
    searchTerm: ''
};

// Save user settings to localStorage
function saveUserSettings() {
    try {
        const searchInput = document.getElementById('goal-search');
        const searchTerm = searchInput ? searchInput.value : '';
        
        const settings = {
            viewMode: currentViewMode,
            filter: currentFilter,
            sort: currentSort,
            tagFilter: currentTagFilter,
            page: currentPage,
            searchTerm: searchTerm
        };
        
        localStorage.setItem('letsgoal_user_settings', JSON.stringify(settings));
        console.log('💾 User settings saved:', settings);
    } catch (error) {
        console.error('❌ Failed to save user settings:', error);
    }
}

// Load user settings from localStorage
function loadUserSettings() {
    try {
        const saved = localStorage.getItem('letsgoal_user_settings');
        if (saved) {
            const settings = JSON.parse(saved);
            console.log('📂 Loading saved user settings:', settings);
            
            // Apply saved settings
            currentViewMode = settings.viewMode || DEFAULT_SETTINGS.viewMode;
            currentFilter = settings.filter || DEFAULT_SETTINGS.filter;
            currentSort = settings.sort || DEFAULT_SETTINGS.sort;
            currentTagFilter = settings.tagFilter || DEFAULT_SETTINGS.tagFilter;
            currentPage = settings.page || DEFAULT_SETTINGS.page;
            
            // Apply search term
            const searchInput = document.getElementById('goal-search');
            if (searchInput && settings.searchTerm) {
                searchInput.value = settings.searchTerm;
            }
            
            console.log('✅ User settings applied');
            return true;
        } else {
            console.log('📝 No saved settings found, using defaults');
            return false;
        }
    } catch (error) {
        console.error('❌ Failed to load user settings:', error);
        // Reset to defaults on error
        currentViewMode = DEFAULT_SETTINGS.viewMode;
        currentFilter = DEFAULT_SETTINGS.filter;
        currentSort = DEFAULT_SETTINGS.sort;
        currentTagFilter = DEFAULT_SETTINGS.tagFilter;
        currentPage = DEFAULT_SETTINGS.page;
        return false;
    }
}

// Clear user settings (useful for reset)
function clearUserSettings() {
    try {
        localStorage.removeItem('letsgoal_user_settings');
        console.log('🗑️ User settings cleared');
    } catch (error) {
        console.error('❌ Failed to clear user settings:', error);
    }
}

// Apply saved settings to UI elements
function applySettingsToUI() {
    console.log('🎨 Applying settings to UI...');
    
    // Apply view mode
    const viewToggle = document.getElementById('view-toggle');
    if (viewToggle) {
        const isGrid = currentViewMode === 'grid';
        viewToggle.querySelector('.fa-th-large').style.opacity = isGrid ? '1' : '0.5';
        viewToggle.querySelector('.fa-list').style.opacity = isGrid ? '0.5' : '1';
    }
    
    // Apply filter
    const filterLabel = document.getElementById('filter-label');
    if (filterLabel) {
        const filterText = {
            'all': 'All Goals',
            'created': 'Created',
            'started': 'Started',
            'working': 'Working',
            'completed': 'Completed'
        };
        filterLabel.textContent = filterText[currentFilter];
    }
    
    // Apply sort
    const sortLabel = document.getElementById('sort-label');
    if (sortLabel) {
        const sortText = {
            'recent': 'Recently Updated',
            'target': 'Target Date',
            'progress': 'Progress',
            'name': 'Name',
            'urgent_subgoals': 'Due Date'
        };
        sortLabel.textContent = sortText[currentSort];
    }
    
    // Apply tag filter
    const tagFilterLabel = document.getElementById('tag-filter-label');
    if (tagFilterLabel) {
        if (currentTagFilter) {
            const selectedTag = tags.find(tag => tag.id === currentTagFilter);
            if (selectedTag) {
                tagFilterLabel.textContent = selectedTag.name;
            }
        } else {
            tagFilterLabel.textContent = 'All Tags';
        }
    }
    
    console.log('✅ Settings applied to UI');
}

// Dashboard functionality confirmed working

// Professional motivational quotes
const motivationalQuotes = [
    "The successful person has the habit of doing the things failures don't like to do.",
    "Success is the progressive realization of a worthy goal or ideal.",
    "Goals are dreams with deadlines and action plans.",
    "Excellence is never an accident. It is always the result of high intention.",
    "The difference between ordinary and extraordinary is that little extra.",
    "Success is where preparation and opportunity meet.",
    "A goal properly set is halfway reached.",
    "The future belongs to those who prepare for it today."
];

// Predefined color palette for tags
const tagColors = [
    { name: 'Blue', value: '#3B82F6' },
    { name: 'Green', value: '#10B981' },
    { name: 'Purple', value: '#8B5CF6' },
    { name: 'Orange', value: '#F59E0B' },
    { name: 'Red', value: '#EF4444' },
    { name: 'Pink', value: '#EC4899' },
    { name: 'Indigo', value: '#6366F1' },
    { name: 'Teal', value: '#14B8A6' }
];

// Initialize dashboard
window.addEventListener('load', async function() {
    // Check authentication
    currentUser = await authUtils.checkAuthStatus();
    if (!currentUser) {
        window.location.href = '/login';
        return;
    }
    
    // Load saved user settings BEFORE loading data
    loadUserSettings();
    
    // Update welcome message
    document.getElementById('user-welcome').innerHTML = `
        Welcome, ${currentUser.username}
    `;
    
    // Load dashboard data
    await loadDashboardData();
    
    // Load user tags
    await loadUserTags();
    
    // Set daily motivational quote
    setDailyQuote();
    
    // Apply saved settings to UI elements (after everything is loaded)
    setTimeout(() => {
        applySettingsToUI();
    }, 100);
    
    // Setup event listeners
    setupEventListeners();
    
    // Setup filtering and sorting
    setupFiltersAndSorting();
});

// Load dashboard data
async function loadDashboardData() {
    try {
        authUtils.showLoadingSpinner();
        
        // Load goals and stats in parallel
        const [goalsResponse, statsResponse] = await Promise.all([
            fetch('/api/goals', { credentials: 'include' }),
            fetch('/api/dashboard/stats', { credentials: 'include' })
        ]);
        
        if (goalsResponse.ok) {
            goals = await goalsResponse.json();
            renderGoals();
        }
        
        if (statsResponse.ok) {
            const stats = await statsResponse.json();
            updateStatsDisplay(stats);
            updateProgressChart(stats);
        }
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        authUtils.showErrorMessage('Failed to load dashboard data');
    } finally {
        authUtils.hideLoadingSpinner();
    }
}

// Load user tags
async function loadUserTags() {
    try {
        const response = await fetch('/api/tags', { credentials: 'include' });
        
        if (response.ok) {
            tags = await response.json();
            console.log('📊 Loaded user tags:', tags.length);
            
            // Populate tag filter dropdown
            populateTagFilterDropdown();
        } else {
            console.error('Failed to load tags');
        }
    } catch (error) {
        console.error('Error loading user tags:', error);
    }
}

// Update stats display
function updateStatsDisplay(stats) {
    // Stats display has been removed from the UI
    // Stats are now available via the Progress modal
    console.log('Dashboard stats:', stats);
}

// Update progress chart to show recent progress trends
function updateProgressChart(stats) {
    const ctx = document.getElementById('progress-chart');
    if (!ctx) {
        console.log('Progress chart canvas not found - will be initialized when modal opens');
        return;
    }
    
    const context = ctx.getContext('2d');
    
    if (progressChart) {
        progressChart.destroy();
    }
    
    // Generate recent progress data (last 7 days)
    const recentProgressData = generateRecentProgressData();
    
    // Handle case when there are no goals
    if (stats.total_goals === 0) {
        progressChart = new Chart(context, {
            type: 'line',
            data: {
                labels: ['No Data'],
                datasets: [{
                    label: 'Progress',
                    data: [0],
                    backgroundColor: 'rgba(229, 231, 235, 0.1)',
                    borderColor: '#E5E7EB',
                    borderWidth: 2,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
        // Store the chart instance globally for modal access
        window.progressChart = progressChart;
        return;
    }
    
    progressChart = new Chart(context, {
        type: 'line',
        data: {
            labels: recentProgressData.labels,
            datasets: [{
                label: 'Subgoals Completed',
                data: recentProgressData.subgoalData,
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderColor: '#3B82F6',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#3B82F6',
                pointBorderColor: '#FFFFFF',
                pointBorderWidth: 2,
                pointRadius: 2,
                pointHoverRadius: 4
            }, {
                label: 'Goals Completed',
                data: recentProgressData.goalData,
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderColor: '#10B981',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#10B981',
                pointBorderColor: '#FFFFFF',
                pointBorderWidth: 2,
                pointRadius: 2,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#6B7280',
                        font: {
                            size: 8
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(229, 231, 235, 0.5)'
                    },
                    ticks: {
                        color: '#6B7280',
                        font: {
                            size: 8
                        }
                    }
                }
            }
        }
    });
    
    // Store the chart instance globally for modal access
    window.progressChart = progressChart;
}

// Generate recent progress data for the last 7 days
function generateRecentProgressData() {
    const days = [];
    const subgoalData = [];
    const goalData = [];
    
    // Get last 7 days (using local dates for consistency)
    for (let i = 6; i >= 0; i--) {
        const today = new Date();
        const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() - i);
        
        // Format day label (e.g., "Mon", "Tue")
        const dayLabel = date.toLocaleDateString('en-US', { weekday: 'short' });
        days.push(dayLabel);
        
        // Calculate completed items for this day
        // For now, we'll use simulated data based on current progress
        // In a real app, you'd track this in the database
        const subgoalsCompleted = calculateDayProgress(date, 'subgoals');
        const goalsCompleted = calculateDayProgress(date, 'goals');
        
        subgoalData.push(subgoalsCompleted);
        goalData.push(goalsCompleted);
    }
    
    return {
        labels: days,
        subgoalData: subgoalData,
        goalData: goalData
    };
}

// Calculate progress for a specific day (simulated for now)
function calculateDayProgress(date, type) {
    // This is a simplified simulation based on current data
    // In a production app, you'd store completion timestamps in the database
    
    const today = new Date();
    const todayLocal = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const isToday = date.toDateString() === todayLocal.toDateString();
    const dayOfWeek = date.getDay();
    
    if (type === 'subgoals') {
        // Count recently completed subgoals
        let completedCount = 0;
        goals.forEach(goal => {
            if (goal.subgoals) {
                goal.subgoals.forEach(subgoal => {
                    if (subgoal.status === 'achieved') {
                        // Simulate that some were completed on different days
                        if (isToday || (dayOfWeek > 0 && Math.random() > 0.7)) {
                            completedCount++;
                        }
                    }
                });
            }
        });
        return completedCount;
    } else {
        // Count recently completed goals
        let completedCount = 0;
        goals.forEach(goal => {
            if (goal.status === 'completed') {
                // Simulate that some goals were completed on different days
                if (isToday || (dayOfWeek > 0 && Math.random() > 0.8)) {
                    completedCount++;
                }
            }
        });
        return completedCount;
    }
}

// Enhanced goal rendering with filtering and sorting
function renderGoals() {
    const container = document.getElementById('goals-container');
    
    // Filter and sort goals
    applyFiltersAndSort();
    
    // Check if no goals exist at all
    if (goals.length === 0) {
        container.innerHTML = `
            <div class="col-span-full flex flex-col items-center justify-center py-16 px-4">
                <div class="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-6">
                    <i class="fas fa-target text-3xl text-gray-400"></i>
                </div>
                <h3 class="text-xl font-semibold text-gray-700 mb-2">No goals yet</h3>
                <p class="text-gray-500 mb-6 text-center max-w-md">Start your journey by creating your first goal. Break it down into manageable steps and track your progress.</p>
                <button onclick="showCreateGoalModal()" class="btn-primary px-6 py-3">
                    <i class="fas fa-plus mr-2"></i>
                    Create Your First Goal
                </button>
            </div>
        `;
        return;
    }
    
    // Check if filtered goals is empty
    if (filteredGoals.length === 0) {
        container.innerHTML = `
            <div class="col-span-full flex flex-col items-center justify-center py-12 px-4">
                <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                    <i class="fas fa-search text-2xl text-gray-400"></i>
                </div>
                <h3 class="text-lg font-medium text-gray-700 mb-2">No goals found</h3>
                <p class="text-gray-500 text-center">Try adjusting your filters or search terms.</p>
            </div>
        `;
        return;
    }
    
    // Apply view mode classes
    container.className = currentViewMode === 'grid' ? 'goals-grid' : 'goals-list';
    
    // Get goals for current page
    const startIndex = currentPage * goalsPerPage;
    const endIndex = startIndex + goalsPerPage;
    const goalsToShow = filteredGoals.slice(0, endIndex);
    
    // Render goals
    container.innerHTML = goalsToShow.map(goal => 
        currentViewMode === 'grid' ? renderGoalCardGrid(goal) : renderGoalCardList(goal)
    ).join('');
    
    // Add sticky hover functionality for grid view
    if (currentViewMode === 'grid') {
        setupStickyHover();
    }
    
    // Update load more button
    updateLoadMoreButton();
}

// Setup sticky hover functionality for goal cards
function setupStickyHover() {
    const goalCards = document.querySelectorAll('.goal-card-grid');
    
    goalCards.forEach(card => {
        const goalId = card.getAttribute('data-goal-id');
        let hoverTimeout = null;
        
        // Restore sticky state if it was active before re-render
        if (stickyHoverStates.get(goalId)) {
            card.classList.add('sticky-hover');
        }
        
        // Mouse enter - immediately add sticky hover
        card.addEventListener('mouseenter', function() {
            clearTimeout(hoverTimeout);
            this.classList.add('sticky-hover');
            stickyHoverStates.set(goalId, true);
        });
        
        // Mouse leave - delay removal to allow for potential re-entry
        card.addEventListener('mouseleave', function() {
            const self = this;
            clearTimeout(hoverTimeout);
            
            // Small delay to prevent flickering if user quickly moves mouse back
            hoverTimeout = setTimeout(() => {
                self.classList.remove('sticky-hover');
                stickyHoverStates.set(goalId, false);
            }, 100);
        });
        
        // When interacting with checkboxes, ensure sticky hover stays active
        const checkboxes = card.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                // Keep the card expanded while interacting
                clearTimeout(hoverTimeout);
                card.classList.add('sticky-hover');
                stickyHoverStates.set(goalId, true);
                
                // Remove sticky hover after a longer delay to allow multiple interactions
                hoverTimeout = setTimeout(() => {
                    // Only remove if mouse is not over the card
                    if (!card.matches(':hover')) {
                        card.classList.remove('sticky-hover');
                        stickyHoverStates.set(goalId, false);
                    }
                }, 800); // Increased timeout for better UX
            });
        });
        
        // Also handle clicking on subgoal text (which toggles checkboxes)
        const subgoalTexts = card.querySelectorAll('.subgoal-item span.cursor-pointer');
        subgoalTexts.forEach(text => {
            text.addEventListener('click', function() {
                // Keep the card expanded while interacting
                clearTimeout(hoverTimeout);
                card.classList.add('sticky-hover');
                stickyHoverStates.set(goalId, true);
                
                // Remove sticky hover after a longer delay
                hoverTimeout = setTimeout(() => {
                    if (!card.matches(':hover')) {
                        card.classList.remove('sticky-hover');
                        stickyHoverStates.set(goalId, false);
                    }
                }, 800); // Increased timeout for better UX
            });
        });
        
        // Handle quick subgoal input interactions
        const quickInput = card.querySelector('.quick-subgoal-input');
        if (quickInput) {
            quickInput.addEventListener('focus', function() {
                clearTimeout(hoverTimeout);
                card.classList.add('sticky-hover');
                stickyHoverStates.set(goalId, true);
            });
            
            quickInput.addEventListener('blur', function() {
                // Delay removal to allow for re-focus or other interactions
                hoverTimeout = setTimeout(() => {
                    if (!card.matches(':hover') && document.activeElement !== quickInput) {
                        card.classList.remove('sticky-hover');
                        stickyHoverStates.set(goalId, false);
                    }
                }, 1000); // Longer delay for input interactions
            });
            
            quickInput.addEventListener('keydown', function() {
                // Keep expanded while typing
                clearTimeout(hoverTimeout);
                card.classList.add('sticky-hover');
                stickyHoverStates.set(goalId, true);
            });
        }
    });
}

// Render goal card for grid view
function renderGoalCardGrid(goal) {
    // Enhanced progress colors with gradients
    const progressColor = goal.progress >= 100 ? '#10b981' : 
                         goal.progress >= 75 ? '#3b82f6' : 
                         goal.progress >= 25 ? '#f59e0b' : '#ef4444';
    
    // Improved circle calculations for cleaner appearance
    const radius = 26;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (goal.progress / 100) * circumference;
    
    const hasHiddenSubgoals = goal.subgoals.length > 3;
    
    return `
        <div class="goal-card-grid expandable-goal-card" 
             data-goal-id="${goal.id}">
            
            <!-- Modern Header with Integrated Status -->
            <div class="card-header-section">
                <div class="flex items-start justify-between gap-3 mb-2">
                    <div class="flex items-center gap-2 flex-1 min-w-0">
                        <div class="status-dot ${getStatusDotClass(goal.status)}" 
                             title="${goal.status.replace('_', ' ').toUpperCase()}"></div>
                        <h3 class="goal-title-modern">${goal.title}</h3>
                    </div>
                    <div class="card-menu-container">
                        <button class="card-menu-btn" onclick="toggleCardMenu(${goal.id}); event.stopPropagation();" title="More options">
                            <i class="fas fa-ellipsis-h"></i>
                        </button>
                        <div id="card-menu-${goal.id}" class="card-dropdown-menu hidden" style="border: 1px solid #cbd5e1 !important;">
                            <button onclick="editGoal(${goal.id}); closeCardMenu(${goal.id}); event.stopPropagation();" class="card-menu-item">
                                <i class="fas fa-edit"></i>
                                <span>Edit</span>
                            </button>
                            ${goal.status !== 'completed' ? `
                                <button onclick="updateGoalStatus(${goal.id}, 'completed'); closeCardMenu(${goal.id}); event.stopPropagation();" class="card-menu-item">
                                    <i class="fas fa-trophy"></i>
                                    <span>Complete</span>
                                </button>
                            ` : `
                                <button onclick="updateGoalStatus(${goal.id}, 'working'); closeCardMenu(${goal.id}); event.stopPropagation();" class="card-menu-item">
                                    <i class="fas fa-undo"></i>
                                    <span>Incomplete</span>
                                </button>
                            `}
                            <div class="card-menu-divider"></div>
                            <button onclick="deleteGoal(${goal.id}); closeCardMenu(${goal.id}); event.stopPropagation();" class="card-menu-item card-menu-danger">
                                <i class="fas fa-trash"></i>
                                <span>Delete</span>
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Tags Row -->
                ${goal.tags && goal.tags.length > 0 ? `
                    <div class="tags-container mb-3">
                        ${renderModernTagBadges(goal, 3)}
                    </div>
                ` : ''}
                
                <!-- Description with better spacing -->
                ${goal.description ? `
                    <p class="goal-description-modern">${goal.description}</p>
                ` : ''}
            </div>
            
            <!-- Flexible content area -->
            <div class="flex flex-col flex-1 mt-4">
                <!-- Quick Add Subgoal Input - now in consistent position -->
                ${goal.status !== 'completed' ? `
                    <div class="mb-4 px-1">
                        <input type="text" 
                               id="quick-subgoal-${goal.id}"
                               class="quick-subgoal-input w-full text-xs px-2 py-1.5 border border-gray-200 rounded-md focus:border-blue-400 focus:ring-1 focus:ring-blue-400 focus:outline-none transition-all duration-200"
                               placeholder="Add quick sub-goal..." 
                               onkeypress="handleQuickSubgoalKeypress(event, ${goal.id})"
                               onclick="event.stopPropagation();"
                               onfocus="event.stopPropagation(); maintainStickyHover(${goal.id})"
                               onblur="event.stopPropagation();">
                    </div>
                ` : ''}
                
                <!-- Subgoals Preview with Pure CSS Hover Expansion -->
                ${goal.subgoals.length > 0 ? `
                    <div class="border-t pt-1.5 mt-auto subgoals-section ${hasHiddenSubgoals ? 'has-hidden-subgoals' : ''}">
                        <div class="flex items-center justify-between mb-0.5">
                            <span class="text-sm text-gray-600">Sub-goals</span>
                            <span class="text-xs bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded-full">
                                ${goal.subgoals.filter(sg => sg.status === 'achieved').length}/${goal.subgoals.length}
                            </span>
                        </div>
                        
                        <!-- Single Unified Subgoals List -->
                        <div class="subgoals-list space-y-0">
                            ${goal.subgoals.map((subgoal, index) => `
                                <div class="subgoal-item ${subgoal.status === 'achieved' ? 'completed' : ''} ${index >= 3 ? 'hidden-subgoal' : 'visible-subgoal'}" 
                                     style="--animation-delay: ${index * 0.05}s">
                                    <div class="flex items-center w-full py-0.25">
                                        <input type="checkbox" 
                                               id="subgoal-${subgoal.id}"
                                               class="h-3 w-3 text-blue-600 rounded mr-2 flex-shrink-0" 
                                               ${subgoal.status === 'achieved' ? 'checked' : ''}
                                               onclick="event.stopPropagation();"
                                               onchange="quickUpdateSubgoal(${subgoal.id}, this.checked, ${goal.id}); event.stopPropagation();">
                                        <span class="truncate flex-1 cursor-pointer text-sm" 
                                              onclick="event.stopPropagation(); toggleSubgoalCheckbox(${subgoal.id}, ${goal.id});">${subgoal.title}</span>
                                        ${formatDaysLeft(subgoal.target_date, subgoal.status)}
                                    </div>
                                </div>
                            `).join('')}
                            
                            ${hasHiddenSubgoals ? `
                                <div class="hover-hint-item text-xs text-gray-400 mt-1">
                                    <i class="fas fa-chevron-down mr-1"></i>
                                    <span class="hint-text">+${goal.subgoals.length - 3} more (hover to expand)</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                ` : `
                    <div class="border-t pt-1.5 mt-auto text-center">
                        <span class="text-sm text-gray-500">No sub-goals yet</span>
                    </div>
                `}
            </div>
            
        </div>
    `;
}

// Render goal card for list view
function renderGoalCardList(goal) {
    return `
        <div class="bg-white border border-gray-200 rounded-lg p-6 hover:border-gray-300 transition-all">
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <div class="flex items-center space-x-3 mb-2">
                        <h3 class="text-xl font-semibold text-gray-900">${goal.title}</h3>
                        <span class="status-badge ${getStatusBadgeClass(goal.status)}" 
                              title="${goal.status.replace('_', ' ').toUpperCase()}">
                            <i class="fas ${getStatusIcon(goal.status)}"></i>
                        </span>
                    </div>
                    
                    <!-- Tags -->
                    ${goal.tags && goal.tags.length > 0 ? `
                        <div class="flex flex-wrap gap-1 mb-3">
                            ${renderTagBadges(goal, 5)}
                        </div>
                    ` : ''}
                    
                    ${goal.description ? `<p class="text-gray-600 mb-4">${goal.description}</p>` : ''}
                    
                    <div class="flex items-center space-x-6 text-sm text-gray-500 mb-4">
                        <span class="flex items-center">
                            <i class="fas fa-calendar-alt mr-2"></i>
                            ${goal.target_date ? parseLocalDate(goal.target_date).toLocaleDateString() : 'No target date'}
                        </span>
                        <span class="flex items-center">
                            <i class="fas fa-tasks mr-2"></i>
                            ${goal.subgoals.filter(sg => sg.status === 'achieved').length}/${goal.subgoals.length} sub-goals
                        </span>
                        <span class="flex items-center">
                            <i class="fas fa-chart-pie mr-2"></i>
                            ${goal.progress}% complete
                        </span>
                    </div>
                    
                    <!-- Progress Bar -->
                    <div class="w-full bg-gray-200 rounded-full h-2 mb-4">
                        <div class="progress-bar h-2 rounded-full transition-all duration-700" 
                             style="width: ${goal.progress}%"></div>
                    </div>
                    
                    <!-- Subgoals -->
                    ${goal.subgoals.length > 0 ? `
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                            ${goal.subgoals.map(subgoal => `
                                <div class="flex items-center p-2 rounded hover:bg-gray-50">
                                    <input type="checkbox" 
                                           id="subgoal-list-${subgoal.id}"
                                           class="h-4 w-4 text-blue-600 rounded mr-3" 
                                           ${subgoal.status === 'achieved' ? 'checked' : ''}
                                           onchange="quickUpdateSubgoal(${subgoal.id}, this.checked, ${goal.id})">
                                    <span class="text-sm cursor-pointer ${subgoal.status === 'achieved' ? 'line-through text-gray-500' : 'text-gray-700'}"
                                          onclick="toggleSubgoalCheckboxList(${subgoal.id}, ${goal.id})">${subgoal.title}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
                
                <div class="flex flex-col space-y-2 ml-6">
                    ${goal.status !== 'completed' ? `
                        <button onclick="updateGoalStatus(${goal.id}, 'completed')" class="btn-success text-sm px-4 py-2">
                            <i class="fas fa-trophy mr-1"></i>
                            Complete
                        </button>
                    ` : ''}
                    <button onclick="editGoal(${goal.id})" class="btn-secondary text-sm px-4 py-2">
                        <i class="fas fa-edit mr-1"></i>
                        Edit
                    </button>
                    <button onclick="deleteGoal(${goal.id})" class="text-red-500 hover:text-red-700 text-sm px-4 py-2 hover:bg-red-50 rounded-lg transition-colors">
                        <i class="fas fa-trash mr-1"></i>
                        Delete
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Helper function to calculate days until deadline
function getDaysUntilDeadline(targetDate) {
    if (!targetDate) return null;
    
    const target = parseLocalDate(targetDate);
    // Use local date for today to match parseLocalDate behavior
    const today = new Date();
    const todayLocal = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const diffTime = target - todayLocal;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    return diffDays;
}

// Helper function to format days left indicator
function formatDaysLeft(targetDate, status) {
    if (!targetDate || status === 'achieved') return '';
    
    const daysLeft = getDaysUntilDeadline(targetDate);
    
    if (daysLeft === null) return '';
    
    let colorClass = '';
    let text = '';
    
    if (daysLeft < 0) {
        colorClass = 'text-red-500 bg-red-50';
        text = `${Math.abs(daysLeft)}d overdue`;
    } else if (daysLeft === 0) {
        colorClass = 'text-orange-600 bg-orange-50';
        text = 'Due today';
    } else if (daysLeft === 1) {
        colorClass = 'text-orange-600 bg-orange-50';
        text = 'Due tomorrow';
    } else if (daysLeft <= 3) {
        colorClass = 'text-orange-600 bg-orange-50';
        text = `${daysLeft}d left`;
    } else if (daysLeft <= 7) {
        colorClass = 'text-yellow-600 bg-yellow-50';
        text = `${daysLeft}d left`;
    } else {
        colorClass = 'text-gray-500 bg-gray-50';
        text = `${daysLeft}d left`;
    }
    
    return `<span class="text-xs px-2 py-1 rounded-full ${colorClass} ml-auto flex-shrink-0">${text}</span>`;
}

// Helper functions for goal status
function getStatusColor(status) {
    switch (status) {
        case 'completed': return 'text-green-600';
        case 'working': return 'text-amber-600';
        case 'started': return 'text-blue-600';
        case 'created': return 'text-gray-600';
        default: return 'text-gray-600';
    }
}

function getStatusIcon(status) {
    switch (status) {
        case 'completed': return 'fa-trophy';
        case 'working': return 'fa-rocket';
        case 'started': return 'fa-play';
        case 'created': return 'fa-clock';
        default: return 'fa-circle';
    }
}

function getStatusBadgeClass(status) {
    switch (status) {
        case 'completed': return 'status-completed';
        case 'working': return 'status-working';
        case 'started': return 'status-started';
        case 'created': return 'status-created';
        default: return 'status-created';
    }
}

// Modern status dot classes for redesigned header
function getStatusDotClass(status) {
    switch (status) {
        case 'completed': return 'status-dot-completed';
        case 'working': return 'status-dot-working';
        case 'started': return 'status-dot-started';
        case 'created': return 'status-dot-created';
        default: return 'status-dot-created';
    }
}

// Calculate days remaining until target date
function calculateDaysRemaining(targetDate) {
    if (!targetDate) return '';
    
    const today = new Date();
    const target = parseLocalDate(targetDate);
    const diffTime = target - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
        return `<span class="days-overdue">${Math.abs(diffDays)} days overdue</span>`;
    } else if (diffDays === 0) {
        return `<span class="days-today">Due today</span>`;
    } else if (diffDays === 1) {
        return `<span class="days-upcoming">Due tomorrow</span>`;
    } else if (diffDays <= 7) {
        return `<span class="days-upcoming">${diffDays} days left</span>`;
    } else {
        return `<span class="days-future">${diffDays} days left</span>`;
    }
}

function calculateDaysRemainingCompact(targetDate) {
    if (!targetDate) return '';
    
    const today = new Date();
    const target = parseLocalDate(targetDate);
    const diffTime = target - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
        return `${Math.abs(diffDays)}d overdue`;
    } else if (diffDays === 0) {
        return `Due today`;
    } else if (diffDays === 1) {
        return `Due tomorrow`;
    } else if (diffDays <= 7) {
        return `${diffDays} days left`;
    } else {
        return `${diffDays} days left`;
    }
}

function getDaysRemainingClass(targetDate) {
    if (!targetDate) return '';
    
    const today = new Date();
    const target = parseLocalDate(targetDate);
    const diffTime = target - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
        return 'days-overdue';
    } else if (diffDays === 0) {
        return 'days-today';
    } else if (diffDays <= 7) {
        return 'days-upcoming';
    } else {
        return 'days-future';
    }
}

// Card dropdown menu functions
window.toggleCardMenu = function(goalId) {
    const menu = document.getElementById(`card-menu-${goalId}`);
    const isVisible = !menu.classList.contains('hidden');
    
    // Close all other card menus first
    document.querySelectorAll('.card-dropdown-menu').forEach(m => {
        if (m.id !== `card-menu-${goalId}`) {
            m.classList.add('hidden');
        }
    });
    
    if (isVisible) {
        menu.classList.add('hidden');
    } else {
        menu.classList.remove('hidden');
    }
}

window.closeCardMenu = function(goalId) {
    const menu = document.getElementById(`card-menu-${goalId}`);
    if (menu) {
        menu.classList.add('hidden');
    }
}

// Close all card menus when clicking outside
document.addEventListener('click', function(event) {
    if (!event.target.closest('.card-menu-container')) {
        document.querySelectorAll('.card-dropdown-menu').forEach(menu => {
            menu.classList.add('hidden');
        });
    }
});

// Set daily motivational quote
function setDailyQuote() {
    const today = new Date().getDate();
    const quote = motivationalQuotes[today % motivationalQuotes.length];
    document.getElementById('daily-quote').innerHTML = quote;
}

// Modal functions - make globally accessible
window.showCreateGoalModal = function() {
    console.log('🎯 Opening create goal modal'); // Debug log
    document.getElementById('create-goal-modal').classList.remove('hidden');
    // Set default target date to 30 days from now (using local time to avoid timezone shifts)
    const defaultDate = new Date();
    defaultDate.setDate(defaultDate.getDate() + 30);
    // Format as YYYY-MM-DD without timezone conversion
    const year = defaultDate.getFullYear();
    const month = String(defaultDate.getMonth() + 1).padStart(2, '0');
    const day = String(defaultDate.getDate()).padStart(2, '0');
    document.getElementById('goal-target-date').value = `${year}-${month}-${day}`;
    
    // Initialize tag selector
    selectedTagIds = [];
    renderTagSelector('create-goal-tags-grid', selectedTagIds);
    
    // Auto-focus on the goal title input field
    setTimeout(() => {
        const goalTitleInput = document.getElementById('goal-title');
        if (goalTitleInput) {
            goalTitleInput.focus();
        }
    }, 100);
    
    // Add ESC key listener to close create modal
    const handleCreateModalEsc = function(e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            const createModal = document.getElementById('create-goal-modal');
            // Only close if the create modal is visible (not hidden)
            if (createModal && !createModal.classList.contains('hidden')) {
                console.log('🎯 ESC key pressed - closing create modal'); // Debug log
                closeCreateGoalModal();
            }
        }
    };
    
    // Remove any existing ESC listeners and add new one
    document.removeEventListener('keydown', window.createModalEscHandler);
    window.createModalEscHandler = handleCreateModalEsc;
    document.addEventListener('keydown', handleCreateModalEsc);
    
    console.log('⌨️ ESC key listener attached to create modal'); // Debug log
}

window.closeCreateGoalModal = function() {
    console.log('🎯 Closing create goal modal'); // Debug log
    
    // Remove ESC key listener when closing modal
    if (window.createModalEscHandler) {
        document.removeEventListener('keydown', window.createModalEscHandler);
        window.createModalEscHandler = null;
        console.log('⌨️ ESC key listener removed from create modal'); // Debug log
    }
    
    document.getElementById('create-goal-modal').classList.add('hidden');
    document.getElementById('create-goal-form').reset();
    
    // Clear tag selection
    selectedTagIds = [];
}

// Goal management functions
async function createGoal(goalData) {
    try {
        const response = await fetch('/api/goals', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(goalData),
            credentials: 'include'
        });
        
        if (response.ok) {
            const newGoal = await response.json();
            
            // Set tags if any are selected
            if (selectedTagIds.length > 0) {
                const tagResponse = await fetch(`/api/goals/${newGoal.id}/tags`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ tag_ids: selectedTagIds }),
                    credentials: 'include'
                });
                
                if (!tagResponse.ok) {
                    console.warn('Failed to set goal tags, but goal was created successfully');
                }
            }
            
            if (window.authUtils) {
                window.authUtils.showSuccessMessage(`Goal "${newGoal.title}" created successfully`);
            }
            await loadDashboardData();
            closeCreateGoalModal();
        } else {
            const error = await response.json();
            if (window.authUtils) {
                window.authUtils.showErrorMessage(error.error || 'Failed to create goal');
            }
        }
    } catch (error) {
        console.error('Error creating goal:', error);
        if (window.authUtils) {
            window.authUtils.showErrorMessage('Connection error. Please try again');
        }
    }
}

async function updateGoalStatus(goalId, status) {
    try {
        const response = await fetch(`/api/goals/${goalId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status }),
            credentials: 'include'
        });
        
        if (response.ok) {
            const updatedGoal = await response.json();
            if (status === 'completed') {
                authUtils.showSuccessMessage(`Congratulations! Goal "${updatedGoal.title}" completed!`);
                // Add celebration effect
                createCelebrationEffect();
            } else {
                authUtils.showSuccessMessage('Goal updated successfully');
            }
            await loadDashboardData();
        } else {
            const error = await response.json();
            authUtils.showErrorMessage(error.error || 'Failed to update goal');
        }
    } catch (error) {
        console.error('Error updating goal:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

async function deleteGoal(goalId) {
    if (!confirm('Are you sure you want to delete this goal? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/goals/${goalId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            authUtils.showSuccessMessage('Goal deleted successfully');
            await loadDashboardData();
        } else {
            const error = await response.json();
            authUtils.showErrorMessage(error.error || 'Failed to delete goal');
        }
    } catch (error) {
        console.error('Error deleting goal:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

// Subtle celebration effect
function createCelebrationEffect() {
    // Just add a subtle visual feedback instead of confetti
    const dashboard = document.querySelector('.container');
    if (dashboard) {
        dashboard.style.transform = 'scale(1.01)';
        dashboard.style.transition = 'transform 0.2s ease';
        
        setTimeout(() => {
            dashboard.style.transform = 'scale(1)';
            setTimeout(() => {
                dashboard.style.transform = '';
                dashboard.style.transition = '';
            }, 200);
        }, 200);
    }
}

// Quick action functions - make globally accessible
window.viewHistory = async function() {
    console.log('🎯 Opening history view'); // Debug log
    try {
        const response = await fetch('/api/reports/history', { credentials: 'include' });
        
        if (response.ok) {
            const historyData = await response.json();
            showHistoryModal(historyData);
        } else {
            authUtils.showErrorMessage('Failed to load history');
        }
    } catch (error) {
        console.error('Error loading history:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

window.generateReport = function() {
    const totalGoals = goals.length;
    const completedGoals = goals.filter(g => g.status === 'completed').length;
    const workingGoals = goals.filter(g => g.status === 'working').length;
    const startedGoals = goals.filter(g => g.status === 'started').length;
    const activeGoals = workingGoals + startedGoals;
    const avgProgress = totalGoals > 0 ? Math.round(goals.reduce((sum, g) => sum + g.progress, 0) / totalGoals) : 0;
    
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="modern-card p-8 rounded-xl shadow-2xl max-w-md w-full mx-4">
            <div class="flex justify-between items-center mb-6">
                <h3 class="heading-secondary text-xl">Progress Report</h3>
                <button onclick="this.closest('.fixed').remove()" class="text-gray-500 hover:text-gray-700">
                    <span class="text-2xl">&times;</span>
                </button>
            </div>
            
            <div class="space-y-4">
                <div class="bg-gray-50 p-4 rounded-lg">
                    <div class="grid grid-cols-2 gap-4 text-center">
                        <div>
                            <div class="text-2xl font-bold text-gray-800">${totalGoals}</div>
                            <div class="text-sm text-gray-600">Total Goals</div>
                        </div>
                        <div>
                            <div class="text-2xl font-bold text-green-600">${completedGoals}</div>
                            <div class="text-sm text-gray-600">Completed</div>
                        </div>
                        <div>
                            <div class="text-2xl font-bold text-blue-600">${activeGoals}</div>
                            <div class="text-sm text-gray-600">Active</div>
                        </div>
                        <div>
                            <div class="text-2xl font-bold text-indigo-600">${avgProgress}%</div>
                            <div class="text-sm text-gray-600">Avg Progress</div>
                        </div>
                    </div>
                </div>
                
                <div class="text-center">
                    <button onclick="viewHistory(); this.closest('.fixed').remove()" class="btn-primary px-6 py-2">
                        View Detailed History
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

function editGoal(goalId) {
    const goal = goals.find(g => g.id === goalId);
    if (!goal) {
        authUtils.showErrorMessage('Goal not found');
        return;
    }
    
    // Prevent background scrolling
    document.body.classList.add('modal-open');
    
    // Show modal first
    document.getElementById('edit-goal-modal').classList.remove('hidden');
    
    // Setup event listeners for this modal instance (this clones the form, so do it first)
    setupEditModalEventListeners();
    
    // Populate the edit form AFTER event listeners are set up
    document.getElementById('edit-goal-id').value = goal.id;
    document.getElementById('edit-goal-title').value = goal.title;
    document.getElementById('edit-goal-description').value = goal.description || '';
    document.getElementById('edit-goal-target-date').value = goal.target_date || '';
    document.getElementById('edit-goal-status').value = goal.status;
    
    // Load subgoals
    loadSubgoalsForEdit(goal.subgoals || []);
    
    // Initialize tag selector with current goal tags
    editSelectedTagIds = goal.tags ? goal.tags.map(tag => tag.id) : [];
    renderTagSelector('edit-goal-tags-grid', editSelectedTagIds);
}

// Setup event listeners specifically for the edit modal
function setupEditModalEventListeners() {
    console.log('🎯 Setting up edit modal event listeners...'); // Debug log
    
    // Remove any existing listeners to prevent duplicates
    const editForm = document.getElementById('edit-goal-form');
    const updateBtn = document.getElementById('update-goal-btn');
    
    if (editForm) {
        // Clone and replace to remove existing listeners
        const newEditForm = editForm.cloneNode(true);
        editForm.parentNode.replaceChild(newEditForm, editForm);
        
        // Add form submit listener
        newEditForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('✅ Edit goal form submitted via form event'); // Debug log
            await handleGoalUpdate();
        });
        
        console.log('📝 Form submit listener attached'); // Debug log
    } else {
        console.error('❌ Edit goal form not found!');
    }
    
    if (updateBtn) {
        // Clone and replace to remove existing listeners
        const newUpdateBtn = updateBtn.cloneNode(true);
        updateBtn.parentNode.replaceChild(newUpdateBtn, updateBtn);
        
        // Add button click listener
        newUpdateBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            console.log('✅ Update button clicked directly'); // Debug log
            await handleGoalUpdate();
        });
        
        console.log('🔘 Button click listener attached'); // Debug log
    } else {
        console.error('❌ Update goal button not found!');
    }
    
    // Add ESC key listener to close modal
    const handleEscKey = function(e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            const editModal = document.getElementById('edit-goal-modal');
            // Only close if the edit modal is visible (not hidden)
            if (editModal && !editModal.classList.contains('hidden')) {
                console.log('🎯 ESC key pressed - closing edit modal'); // Debug log
                closeEditGoalModal();
            }
        }
    };
    
    // Remove any existing ESC listeners and add new one
    document.removeEventListener('keydown', window.editModalEscHandler);
    window.editModalEscHandler = handleEscKey;
    document.addEventListener('keydown', handleEscKey);
    
    console.log('⌨️ ESC key listener attached to edit modal'); // Debug log
}

window.closeEditGoalModal = function() {
    const editModal = document.getElementById('edit-goal-modal');
    const subgoalModal = document.getElementById('subgoal-creator-modal');
    
    // Re-enable background scrolling
    document.body.classList.remove('modal-open');
    
    // Remove ESC key listener when closing modal
    if (window.editModalEscHandler) {
        document.removeEventListener('keydown', window.editModalEscHandler);
        window.editModalEscHandler = null;
        console.log('⌨️ ESC key listener removed'); // Debug log
    }
    
    // Close both modals
    editModal.classList.add('hidden');
    if (subgoalModal) {
        subgoalModal.classList.add('hidden');
    }
    
    // Reset visibility
    editModal.style.visibility = 'visible';
    
    // Reset forms
    document.getElementById('edit-goal-form').reset();
    document.getElementById('subgoals-container').innerHTML = '';
    
    // Reset inline form if it exists
    const inlineForm = document.getElementById('inline-subgoal-form');
    if (inlineForm) {
        inlineForm.classList.add('hidden');
        document.getElementById('inline-subgoal-title').value = '';
        document.getElementById('inline-subgoal-description').value = '';
        document.getElementById('inline-subgoal-target-date').value = '';
        
        // Reset button
        const btn = document.getElementById('add-subgoal-btn');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-plus mr-1"></i> Add Sub-goal';
            btn.onclick = toggleInlineSubgoalForm;
        }
    }
    
    // Clear subgoal creator form if it was open
    const newSubgoalTitle = document.getElementById('new-subgoal-title');
    if (newSubgoalTitle) {
        newSubgoalTitle.value = '';
        document.getElementById('new-subgoal-description').value = '';
        document.getElementById('new-subgoal-target-date').value = '';
    }
}

function loadSubgoalsForEdit(subgoals) {
    const container = document.getElementById('subgoals-container');
    const emptyState = document.getElementById('subgoals-empty-state');
    
    container.innerHTML = '';
    
    if (subgoals.length === 0) {
        emptyState.classList.remove('hidden');
    } else {
        emptyState.classList.add('hidden');
        subgoals.forEach(subgoal => {
            addSubgoalToList(subgoal);
        });
    }
}

window.addSubgoalToList = function(subgoal = null) {
    const container = document.getElementById('subgoals-container');
    const emptyState = document.getElementById('subgoals-empty-state');
    
    // Hide empty state
    emptyState.classList.add('hidden');
    
    const row = document.createElement('div');
    row.className = 'subgoal-item bg-white border border-gray-200 rounded-md p-2 hover:border-gray-300 transition-all';
    row.innerHTML = `
        <input type="hidden" class="subgoal-id" value="${subgoal?.id || ''}">
        <div class="flex items-start space-x-2">
            <input type="checkbox" 
                   class="form-checkbox subgoal-checkbox mt-0.5 w-3 h-3" 
                   ${subgoal?.status === 'achieved' ? 'checked' : ''}
                   onchange="toggleSubgoalStatus(this)"
                   ${!subgoal?.id ? 'disabled' : ''}>
            <div class="flex-1">
                <input type="text" 
                       class="subgoal-title input-field w-full mb-1 text-xs py-1 ${subgoal?.status === 'achieved' ? 'line-through text-gray-500' : ''}" 
                       value="${subgoal?.title || ''}" 
                       placeholder="Enter sub-goal title" 
                       required>
                <textarea class="subgoal-description input-field w-full text-xs py-1" 
                          rows="1" 
                          placeholder="Description (optional)">${subgoal?.description || ''}</textarea>
                ${subgoal?.target_date ? `
                    <input type="date" 
                           class="subgoal-target-date input-field w-full text-xs py-1 mt-1" 
                           value="${subgoal.target_date}">
                ` : `
                    <input type="date" 
                           class="subgoal-target-date input-field w-full text-xs py-1 mt-1" 
                           placeholder="Target date (optional)">
                `}
                <input type="hidden" class="subgoal-status" value="${subgoal?.status || 'pending'}">
            </div>
            <button type="button" onclick="removeSubgoalFromList(this)" class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors" title="Remove sub-goal">
                <i class="fas fa-trash text-xs"></i>
            </button>
        </div>
    `;
    
    container.appendChild(row);
    
    // Scroll to the new item within the subgoals container
    const scrollContainer = container.closest('.subgoals-scroll-area');
    if (scrollContainer) {
        // Scroll the container to show the new item
        setTimeout(() => {
            row.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest',
                inline: 'nearest'
            });
        }, 100);
    }
    
    // Focus on the title input after a brief delay
    setTimeout(() => {
        const titleInput = row.querySelector('.subgoal-title');
        if (titleInput) {
            titleInput.focus();
        }
    }, 200);
}

function toggleSubgoalStatus(checkbox) {
    const row = checkbox.closest('.subgoal-item');
    const titleInput = row.querySelector('.subgoal-title');
    const statusInput = row.querySelector('.subgoal-status');
    
    if (checkbox.checked) {
        titleInput.classList.add('line-through', 'text-gray-500');
        statusInput.value = 'achieved';
        row.style.background = '#f0fdf4';
        setTimeout(() => {
            row.style.background = '';
        }, 1000);
    } else {
        titleInput.classList.remove('line-through', 'text-gray-500');
        statusInput.value = 'pending';
    }
}

function removeSubgoalFromList(button) {
    const container = document.getElementById('subgoals-container');
    const emptyState = document.getElementById('subgoals-empty-state');
    
    button.closest('.subgoal-item').remove();
    
    // Show empty state if no subgoals left
    if (container.children.length === 0) {
        emptyState.classList.remove('hidden');
    }
}

// Update goal function
async function updateGoal(goalData) {
    try {
        console.log('🌐 Making API request to update goal:', goalData.id); // Debug log
        
        const response = await fetch(`/api/goals/${goalData.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(goalData),
            credentials: 'include'
        });
        
        console.log('📡 API response status:', response.status); // Debug log
        
        if (response.ok) {
            const updatedGoal = await response.json();
            console.log('✅ Goal updated successfully:', updatedGoal); // Debug log
            return updatedGoal;
        } else {
            const error = await response.json();
            console.error('❌ API error response:', error); // Debug log
            throw new Error(error.error || 'Failed to update goal');
        }
    } catch (error) {
        console.error('❌ Network error updating goal:', error);
        throw error;
    }
}

// Handle subgoal updates
async function updateSubgoals(goalId, subgoalRows) {
    const promises = [];
    
    console.log(`🔍 Processing ${subgoalRows.length} subgoal rows for goal ${goalId}`); // Debug log
    
    subgoalRows.forEach((row, index) => {
        const subgoalIdElement = row.querySelector('.subgoal-id');
        const titleElement = row.querySelector('.subgoal-title');
        const descriptionElement = row.querySelector('.subgoal-description');
        const targetDateElement = row.querySelector('.subgoal-target-date');
        const statusElement = row.querySelector('.subgoal-status');
        
        if (!subgoalIdElement || !titleElement || !descriptionElement || !targetDateElement || !statusElement) {
            console.error(`❌ Missing subgoal form elements in row ${index + 1}`);
            console.log('Row HTML:', row.innerHTML);
            return; // Skip this row
        }
        
        const subgoalId = subgoalIdElement.value;
        const title = titleElement.value.trim();
        const description = descriptionElement.value.trim();
        const targetDate = targetDateElement.value;
        const status = statusElement.value;
        
        console.log(`📋 Subgoal ${index + 1}:`, { subgoalId, title, description, targetDate, status }); // Debug log
        
        if (!title) {
            console.log(`⚠️ Skipping subgoal ${index + 1} - no title`); // Debug log
            return; // Skip empty subgoals
        }
        
        const subgoalData = { title, description, status };
        if (targetDate) {
            subgoalData.target_date = targetDate;
        }
        
        if (subgoalId) {
            // Update existing subgoal
            console.log(`🔄 Updating existing subgoal ${subgoalId}`); // Debug log
            promises.push(
                fetch(`/api/subgoals/${subgoalId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(subgoalData),
                    credentials: 'include'
                }).then(response => {
                    console.log(`📡 Update subgoal ${subgoalId} response:`, response.status); // Debug log
                    return response;
                })
            );
        } else {
            // Create new subgoal
            console.log(`➕ Creating new subgoal for goal ${goalId}`); // Debug log
            promises.push(
                fetch(`/api/goals/${goalId}/subgoals`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(subgoalData),
                    credentials: 'include'
                }).then(response => {
                    console.log(`📡 Create subgoal response:`, response.status); // Debug log
                    return response;
                })
            );
        }
    });
    
    if (promises.length > 0) {
        console.log(`🚀 Executing ${promises.length} subgoal operations...`); // Debug log
        const results = await Promise.all(promises);
        console.log('✅ All subgoal operations completed:', results.map(r => r.status)); // Debug log
    } else {
        console.log('ℹ️ No subgoal operations to perform'); // Debug log
    }
}

// Quick update subgoal from main list
async function quickUpdateSubgoal(subgoalId, isChecked, goalId) {
    try {
        // Show loading feedback
        const checkbox = event.target;
        const subgoalItem = checkbox.closest('.subgoal-item');
        const originalText = subgoalItem.querySelector('span').textContent;
        
        // Add loading state
        subgoalItem.style.opacity = '0.6';
        subgoalItem.querySelector('span').textContent = 'Updating...';
        
        const status = isChecked ? 'achieved' : 'pending';
        const response = await fetch(`/api/subgoals/${subgoalId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status }),
            credentials: 'include'
        });
        
        if (response.ok) {
            // Update local state immediately for better UX
            const goal = goals.find(g => g.id === goalId);
            if (goal) {
                const subgoal = goal.subgoals.find(sg => sg.id === subgoalId);
                if (subgoal) {
                    subgoal.status = status;
                    // Recalculate goal progress
                    const completedSubgoals = goal.subgoals.filter(sg => sg.status === 'achieved').length;
                    goal.progress = goal.subgoals.length > 0 ? Math.round((completedSubgoals / goal.subgoals.length) * 100) : 0;
                    
                    // Auto-update goal status based on new system: Created -> Started -> Working -> Completed
                    const previousStatus = goal.status;
                    if (goal.progress === 100 && goal.status !== 'completed') {
                        goal.status = 'completed';
                    } else if (completedSubgoals === 1 && goal.status === 'created') {
                        goal.status = 'started';
                    } else if (completedSubgoals >= 2 && (goal.status === 'created' || goal.status === 'started')) {
                        goal.status = 'working';
                    } else if (goal.progress === 0) {
                        goal.status = 'created';
                    }
                    
                    // Update goal status on backend if it changed
                    if (goal.status !== previousStatus) {
                        fetch(`/api/goals/${goalId}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ status: goal.status }),
                            credentials: 'include'
                        }).catch(error => {
                            console.error('Failed to update goal status:', error);
                        });
                    }
                }
            }
            
            // Restore original state and apply new styling
            subgoalItem.style.opacity = '1';
            subgoalItem.querySelector('span').textContent = originalText;
            
            // Update visual state
            const span = subgoalItem.querySelector('span');
            if (isChecked) {
                span.classList.add('line-through', 'text-gray-500');
                span.classList.remove('text-gray-700', 'font-medium');
                authUtils.showSuccessMessage('Sub-goal completed!');
                
                // Add completion effect
                subgoalItem.style.background = '#f0fdf4';
                setTimeout(() => {
                    subgoalItem.style.background = '';
                }, 1000);
            } else {
                span.classList.remove('line-through', 'text-gray-500');
                span.classList.add('text-gray-700', 'font-medium');
            }
            
            // Update progress bar
            updateGoalProgressBar(goalId);
            
            // Update stats display
            const statsResponse = await fetch('/api/dashboard/stats', { credentials: 'include' });
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                updateStatsDisplay(stats);
                updateProgressChart(stats);
            }
            
            // Reload goals to get updated timestamps for proper sorting
            const goalsResponse = await fetch('/api/goals', { credentials: 'include' });
            if (goalsResponse.ok) {
                goals = await goalsResponse.json();
                renderGoals();
            }
            
        } else {
            // Restore original state on error
            subgoalItem.style.opacity = '1';
            subgoalItem.querySelector('span').textContent = originalText;
            checkbox.checked = !isChecked; // Revert checkbox
            authUtils.showErrorMessage('Failed to update sub-goal');
        }
    } catch (error) {
        console.error('Error updating subgoal:', error);
        // Restore original state on error
        const subgoalItem = checkbox.closest('.subgoal-item');
        subgoalItem.style.opacity = '1';
        checkbox.checked = !isChecked; // Revert checkbox
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

// Function to toggle subgoal checkbox when clicking on title (grid view)
window.toggleSubgoalCheckbox = function(subgoalId, goalId) {
    const checkbox = document.getElementById(`subgoal-${subgoalId}`);
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        quickUpdateSubgoal(subgoalId, checkbox.checked, goalId);
    }
}

// Function to toggle subgoal checkbox when clicking on title (list view)
window.toggleSubgoalCheckboxList = function(subgoalId, goalId) {
    const checkbox = document.getElementById(`subgoal-list-${subgoalId}`);
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        quickUpdateSubgoal(subgoalId, checkbox.checked, goalId);
    }
}

// Handle keypress in quick subgoal input
window.handleQuickSubgoalKeypress = function(event, goalId) {
    if (event.key === 'Enter') {
        event.preventDefault();
        quickAddSubgoal(goalId);
    }
}

// Maintain sticky hover when focusing on input
window.maintainStickyHover = function(goalId) {
    const card = document.querySelector(`[data-goal-id="${goalId}"]`);
    if (card) {
        card.classList.add('sticky-hover');
        stickyHoverStates.set(goalId.toString(), true);
    }
}

// Quick add subgoal function
async function quickAddSubgoal(goalId) {
    try {
        const input = document.getElementById(`quick-subgoal-${goalId}`);
        const title = input.value.trim();
        
        if (!title) {
            authUtils.showErrorMessage('Please enter a sub-goal title');
            input.focus();
            return;
        }
        
        // Find the goal to inherit target_date
        const goal = goals.find(g => g.id === goalId);
        if (!goal) {
            authUtils.showErrorMessage('Goal not found');
            return;
        }
        
        // Show loading state
        input.disabled = true;
        input.value = 'Adding...';
        
        // Prepare subgoal data
        const subgoalData = {
            title: title,
            description: '',
            target_date: goal.target_date || null,
            status: 'pending'
        };
        
        // Call API to create subgoal
        const response = await fetch(`/api/goals/${goalId}/subgoals`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(subgoalData),
            credentials: 'include'
        });
        
        if (response.ok) {
            const newSubgoal = await response.json();
            
            // Clear input and restore state
            input.value = '';
            input.disabled = false;
            input.placeholder = 'Add quick sub-goal...';
            
            // Show success message
            authUtils.showSuccessMessage(`Sub-goal "${title}" added successfully`);
            
            // Reload goals to get updated data and maintain sorting
            const goalsResponse = await fetch('/api/goals', { credentials: 'include' });
            if (goalsResponse.ok) {
                goals = await goalsResponse.json();
                renderGoals();
            }
            
            // Update stats
            const statsResponse = await fetch('/api/dashboard/stats', { credentials: 'include' });
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                updateStatsDisplay(stats);
                updateProgressChart(stats);
            }
            
        } else {
            const error = await response.json();
            
            // Restore input state
            input.value = title;
            input.disabled = false;
            input.focus();
            
            authUtils.showErrorMessage(error.error || 'Failed to add sub-goal');
        }
        
    } catch (error) {
        console.error('Error adding quick subgoal:', error);
        
        // Restore input state
        const input = document.getElementById(`quick-subgoal-${goalId}`);
        if (input) {
            input.disabled = false;
            input.focus();
        }
        
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

// Update goal progress after subgoal change
function updateGoalProgressBar(goalId) {
    const goal = goals.find(g => g.id === goalId);
    if (!goal) return;
    
    // Find the goal card by data attribute
    const goalCard = document.querySelector(`[data-goal-id="${goalId}"]`);
    if (!goalCard) return;
    
    // Update conic-gradient progress circle
    const progressCircle = goalCard.querySelector('.progress-circle > div');
    if (progressCircle) {
        const progressColor = goal.progress >= 100 ? '#10b981' : 
                             goal.progress >= 75 ? '#3b82f6' : 
                             goal.progress >= 25 ? '#f59e0b' : '#ef4444';
        
        progressCircle.style.background = `conic-gradient(${progressColor} ${goal.progress * 3.6}deg, #f3f4f6 ${goal.progress * 3.6}deg)`;
    }
    
    // Update progress text
    const progressText = goalCard.querySelector('.progress-text');
    if (progressText) {
        progressText.textContent = `${Math.round(goal.progress)}%`;
    }
    
    // Update subgoals completion badge
    const completionBadge = goalCard.querySelector('.text-xs.bg-blue-100');
    if (completionBadge) {
        const completed = goal.subgoals.filter(sg => sg.status === 'achieved').length;
        completionBadge.textContent = `${completed}/${goal.subgoals.length}`;
    }
    
    // Update status badge if goal status changed
    const statusBadge = goalCard.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.className = `status-badge ${getStatusBadgeClass(goal.status)} flex-shrink-0 ml-2`;
        statusBadge.setAttribute('title', goal.status.replace('_', ' ').toUpperCase());
        const icon = statusBadge.querySelector('i');
        if (icon) {
            icon.className = `fas ${getStatusIcon(goal.status)}`;
        }
    }
}

// History reporting function removed - now using window.viewHistory

function showHistoryModal(historyData) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="modern-card p-8 rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div class="flex justify-between items-center mb-6">
                <h3 class="heading-secondary text-xl">Achievement History</h3>
                <button onclick="this.closest('.fixed').remove()" class="text-gray-500 hover:text-gray-700">
                    <span class="text-2xl">&times;</span>
                </button>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h4 class="font-semibold text-gray-800 mb-2">Achievement Summary</h4>
                    <p class="text-gray-600">Total Achievements: ${historyData.total_achievements}</p>
                </div>
                
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h4 class="font-semibold text-gray-800 mb-2">Timing Analysis</h4>
                    <p class="text-gray-600">
                        Early: ${historyData.timing_analysis.filter(t => t.status === 'early').length} | 
                        On Time: ${historyData.timing_analysis.filter(t => t.status === 'on_time').length} | 
                        Late: ${historyData.timing_analysis.filter(t => t.status === 'late').length}
                    </p>
                </div>
            </div>
            
            <div class="space-y-4">
                ${historyData.completed_goals.map(goal => `
                    <div class="border border-gray-200 rounded-lg p-4">
                        <div class="flex justify-between items-start">
                            <div class="flex-1">
                                <h4 class="font-semibold text-gray-800">${goal.title}</h4>
                                <p class="text-gray-600 text-sm">${goal.description || 'No description'}</p>
                                <div class="flex space-x-4 text-sm text-gray-500 mt-2">
                                    <span>Target: ${goal.target_date ? parseLocalDate(goal.target_date).toLocaleDateString() : 'No date'}</span>
                                    <span>Achieved: ${goal.achieved_date ? parseLocalDate(goal.achieved_date).toLocaleDateString() : 'Unknown'}</span>
                                </div>
                            </div>
                            <div class="text-right">
                                <span class="inline-block px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                                    Completed
                                </span>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// Setup event listeners
function setupEventListeners() {
    // Create goal form submission
    document.getElementById('create-goal-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const goalData = {
            title: document.getElementById('goal-title').value,
            description: document.getElementById('goal-description').value,
            target_date: document.getElementById('goal-target-date').value
        };
        
        if (!goalData.title.trim()) {
            authUtils.showErrorMessage('Please enter a goal title');
            return;
        }
        
        await createGoal(goalData);
    });
    
    // Note: Edit goal form listeners are now set up when the modal opens
}

// Direct handler for onclick - make it globally accessible
window.handleGoalUpdateDirect = async function() {
    console.log('🎯 Direct onclick handler called!'); // Debug log
    await handleGoalUpdate();
}

// Centralized goal update handler
async function handleGoalUpdate() {
    console.log('🔄 Starting goal update process...'); // Debug log
    
    try {
        const goalIdElement = document.getElementById('edit-goal-id');
        const titleElement = document.getElementById('edit-goal-title');
        const descriptionElement = document.getElementById('edit-goal-description');
        const targetDateElement = document.getElementById('edit-goal-target-date');
        const statusElement = document.getElementById('edit-goal-status');
        
        if (!goalIdElement || !titleElement || !descriptionElement || !targetDateElement || !statusElement) {
            console.error('❌ Missing form elements');
            if (window.authUtils) {
                window.authUtils.showErrorMessage('Form elements not found. Please refresh the page.');
            } else {
                alert('Form elements not found. Please refresh the page.');
            }
            return;
        }
        
        const goalId = goalIdElement.value;
        const goalData = {
            id: goalId,
            title: titleElement.value,
            description: descriptionElement.value,
            target_date: targetDateElement.value,
            status: statusElement.value
        };
        
        console.log('📝 Goal data to update:', goalData); // Debug log
        
        if (!goalData.title.trim()) {
            if (window.authUtils) {
                window.authUtils.showErrorMessage('Please enter a goal title');
            } else {
                alert('Please enter a goal title');
            }
            return;
        }
        
        if (!goalId) {
            if (window.authUtils) {
                window.authUtils.showErrorMessage('Goal ID is missing. Please close and reopen the modal.');
            } else {
                alert('Goal ID is missing. Please close and reopen the modal.');
            }
            return;
        }
        
        // Show loading state
        let updateBtn = document.getElementById('update-goal-btn');
        if (updateBtn) {
            const originalText = updateBtn.innerHTML;
            updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Updating...';
            updateBtn.disabled = true;
        }
        
        // Update subgoals first - exclude the inline form
        const subgoalRows = document.querySelectorAll('.subgoal-item:not(#inline-subgoal-form)');
        console.log(`📋 Found ${subgoalRows.length} subgoal rows to process`); // Debug log
        
        if (subgoalRows.length > 0) {
            console.log('🔄 Updating subgoals...'); // Debug log
            await updateSubgoals(goalId, subgoalRows);
            console.log('✅ Subgoals updated successfully'); // Debug log
        }
        
        // Update goal
        console.log('🔄 Updating main goal...'); // Debug log
        await updateGoal(goalData);
        console.log('✅ Goal updated successfully'); // Debug log
        
        // Update goal tags
        console.log('🔄 Updating goal tags...'); // Debug log
        console.log('📌 Current editSelectedTagIds:', editSelectedTagIds);
        console.log('📌 Available tags:', tags);
        await updateGoalTags(goalId, editSelectedTagIds);
        console.log('✅ Goal tags updated successfully'); // Debug log
        
        // Reload dashboard data to show updated tags
        console.log('🔄 Reloading dashboard data with updated tags...'); // Debug log
        await loadDashboardData();
        console.log('✅ Dashboard data reloaded successfully'); // Debug log
        
        // Close modal and show success message
        closeEditGoalModal();
        if (window.authUtils) {
            window.authUtils.showSuccessMessage('Goal updated successfully');
        } else {
            alert('Goal updated successfully');
        }
        
        // Restore button state
        updateBtn = document.getElementById('update-goal-btn');
        if (updateBtn) {
            updateBtn.innerHTML = '<i class="fas fa-save mr-2"></i> Update Goal';
            updateBtn.disabled = false;
        }
        
    } catch (error) {
        console.error('❌ Error in goal update process:', error);
        if (window.authUtils) {
            window.authUtils.showErrorMessage(`Failed to update goal: ${error.message}`);
        } else {
            alert(`Failed to update goal: ${error.message}`);
        }
        
        // Restore button state
        updateBtn = document.getElementById('update-goal-btn');
        if (updateBtn) {
            updateBtn.innerHTML = '<i class="fas fa-save mr-2"></i> Update Goal';
            updateBtn.disabled = false;
        }
    }
}

// Enhanced filtering and sorting functionality
function setupFiltersAndSorting() {
    const searchInput = document.getElementById('goal-search');
    
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentPage = 0;
            renderGoals();
            saveUserSettings();
        });
    }
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('#filter-dropdown-btn') && !e.target.closest('#filter-dropdown')) {
            closeFilterDropdown();
        }
        if (!e.target.closest('#sort-dropdown-btn') && !e.target.closest('#sort-dropdown')) {
            closeSortDropdown();
        }
        if (!e.target.closest('#tag-filter-dropdown-btn') && !e.target.closest('#tag-filter-dropdown')) {
            closeTagFilterDropdown();
        }
    });
}

function applyFiltersAndSort() {
    let filtered = [...goals];
    
    // Apply search filter
    const searchTerm = document.getElementById('goal-search')?.value.toLowerCase() || '';
    if (searchTerm) {
        filtered = filtered.filter(goal => 
            goal.title.toLowerCase().includes(searchTerm) ||
            goal.description?.toLowerCase().includes(searchTerm) ||
            goal.subgoals.some(sg => sg.title.toLowerCase().includes(searchTerm))
        );
    }
    
    // Apply status filter
    if (currentFilter !== 'all') {
        filtered = filtered.filter(goal => goal.status === currentFilter);
    }
    
    // Apply tag filter
    if (currentTagFilter !== null) {
        filtered = filtered.filter(goal => 
            goal.tags && goal.tags.some(tag => tag.id === currentTagFilter)
        );
    }
    
    // Apply sorting
    filtered.sort((a, b) => {
        switch (currentSort) {
            case 'recent':
                // Use last_activity_at for more accurate "recently updated" sorting
                const aTimestamp = a.last_activity_at || a.updated_at || a.created_at;
                const bTimestamp = b.last_activity_at || b.updated_at || b.created_at;
                return parseLocalDate(bTimestamp) - parseLocalDate(aTimestamp);
            case 'target':
                if (!a.target_date && !b.target_date) return 0;
                if (!a.target_date) return 1;
                if (!b.target_date) return -1;
                return parseLocalDate(a.target_date) - parseLocalDate(b.target_date);
            case 'urgent_subgoals':
                // Helper function to find earliest subgoal date
                const getEarliestSubgoalDate = (goal) => {
                    if (!goal.subgoals || goal.subgoals.length === 0) return null;
                    
                    const dates = goal.subgoals
                        .filter(sg => sg.target_date && sg.status !== 'achieved')
                        .map(sg => parseLocalDate(sg.target_date));
                    
                    if (dates.length === 0) return null;
                    
                    return new Date(Math.min(...dates));
                };
                
                const aEarliest = getEarliestSubgoalDate(a);
                const bEarliest = getEarliestSubgoalDate(b);
                
                // Goals with no subgoal dates go to the bottom
                if (!aEarliest && !bEarliest) return 0;
                if (!aEarliest) return 1;
                if (!bEarliest) return -1;
                
                // Sort by earliest date (ascending - most urgent first)
                return aEarliest - bEarliest;
            case 'progress':
                return b.progress - a.progress;
            case 'name':
                return a.title.localeCompare(b.title);
            default:
                return 0;
        }
    });
    
    filteredGoals = filtered;
}

// Modern dropdown functionality
window.toggleFilterDropdown = function() {
    const dropdown = document.getElementById('filter-dropdown');
    const btn = document.getElementById('filter-dropdown-btn');
    const chevron = document.getElementById('filter-chevron');
    
    if (dropdown && dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        btn.classList.add('active');
        chevron.style.transform = 'rotate(180deg)';
        closeSortDropdown(); // Close other dropdown
    } else {
        closeFilterDropdown();
    }
}

window.toggleSortDropdown = function() {
    const dropdown = document.getElementById('sort-dropdown');
    const btn = document.getElementById('sort-dropdown-btn');
    const chevron = document.getElementById('sort-chevron');
    
    if (dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        btn.classList.add('active');
        chevron.style.transform = 'rotate(180deg)';
        closeFilterDropdown(); // Close other dropdown
    } else {
        closeSortDropdown();
    }
}

function closeFilterDropdown() {
    const dropdown = document.getElementById('filter-dropdown');
    const btn = document.getElementById('filter-dropdown-btn');
    const chevron = document.getElementById('filter-chevron');
    
    if (dropdown && !dropdown.classList.contains('hidden')) {
        dropdown.classList.add('hidden');
        btn.classList.remove('active');
        chevron.style.transform = 'rotate(0deg)';
    }
}

function closeSortDropdown() {
    const dropdown = document.getElementById('sort-dropdown');
    const btn = document.getElementById('sort-dropdown-btn');
    const chevron = document.getElementById('sort-chevron');
    
    if (dropdown && !dropdown.classList.contains('hidden')) {
        dropdown.classList.add('hidden');
        btn.classList.remove('active');
        chevron.style.transform = 'rotate(0deg)';
    }
}

window.setFilter = function(filterValue) {
    currentFilter = filterValue;
    currentPage = 0;
    
    // Update label
    const label = document.getElementById('filter-label');
    const filterLabels = {
        'all': 'All Goals',
        'created': 'Created',
        'started': 'Started',
        'working': 'Working',
        'completed': 'Completed'
    };
    
    if (label) {
        label.textContent = filterLabels[filterValue];
    }
    
    closeFilterDropdown();
    renderGoals();
    saveUserSettings();
}

window.setSort = function(sortValue) {
    currentSort = sortValue;
    currentPage = 0;
    
    // Update label
    const label = document.getElementById('sort-label');
    const sortLabels = {
        'recent': 'Recently Updated',
        'target': 'Target Date',
        'progress': 'Progress',
        'name': 'Name',
        'urgent_subgoals': 'Due Date'
    };
    label.textContent = sortLabels[sortValue];
    
    closeSortDropdown();
    renderGoals();
    saveUserSettings();
}

// Enhanced view mode management
window.setViewMode = function(mode) {
    currentViewMode = mode;
    
    // Update button states
    const gridBtn = document.getElementById('grid-view-btn');
    const listBtn = document.getElementById('list-view-btn');
    
    // Remove active class from both
    gridBtn.classList.remove('active', 'bg-white', 'text-gray-700', 'shadow-sm');
    listBtn.classList.remove('active', 'bg-white', 'text-gray-700', 'shadow-sm');
    gridBtn.classList.add('text-gray-500');
    listBtn.classList.add('text-gray-500');
    
    if (mode === 'grid') {
        gridBtn.classList.add('active', 'bg-white', 'text-gray-700', 'shadow-sm');
        gridBtn.classList.remove('text-gray-500');
    } else {
        listBtn.classList.add('active', 'bg-white', 'text-gray-700', 'shadow-sm');
        listBtn.classList.remove('text-gray-500');
    }
    
    renderGoals();
    saveUserSettings();
}

// Tag filter functions
window.toggleTagFilterDropdown = function() {
    const dropdown = document.getElementById('tag-filter-dropdown');
    const btn = document.getElementById('tag-filter-dropdown-btn');
    const chevron = document.getElementById('tag-filter-chevron');
    
    if (dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        btn.classList.add('active');
        chevron.style.transform = 'rotate(180deg)';
        closeFilterDropdown(); // Close other dropdowns
        closeSortDropdown();
    } else {
        closeTagFilterDropdown();
    }
}

function closeTagFilterDropdown() {
    const dropdown = document.getElementById('tag-filter-dropdown');
    const btn = document.getElementById('tag-filter-dropdown-btn');
    const chevron = document.getElementById('tag-filter-chevron');
    
    if (dropdown && !dropdown.classList.contains('hidden')) {
        dropdown.classList.add('hidden');
        btn.classList.remove('active');
        chevron.style.transform = 'rotate(0deg)';
    }
}

window.setTagFilter = function(tagId) {
    currentTagFilter = tagId;
    currentPage = 0;
    
    // Update label
    const label = document.getElementById('tag-filter-label');
    if (tagId === null) {
        label.textContent = 'All Tags';
    } else {
        const tag = tags.find(t => t.id === tagId);
        label.textContent = tag ? tag.name : 'Unknown Tag';
    }
    
    // Update selection state in dropdown
    document.querySelectorAll('.tag-filter-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    const selectedOption = tagId === null ? 
        document.querySelector('.tag-filter-option') : 
        document.querySelector(`[data-tag-id="${tagId}"]`);
    if (selectedOption) {
        selectedOption.classList.add('selected');
    }
    
    closeTagFilterDropdown();
    renderGoals();
    saveUserSettings();
}

window.clearTagFilter = function() {
    setTagFilter(null);
}

function populateTagFilterDropdown() {
    const container = document.getElementById('tag-filter-options');
    if (!container) return;
    
    if (tags.length === 0) {
        container.innerHTML = `
            <div class="px-4 py-2 text-sm text-gray-500 text-center">
                <p>No tags available</p>
                <button type="button" onclick="showTagManagementModal(); closeTagFilterDropdown();" class="text-blue-600 hover:text-blue-800 underline text-xs mt-1">
                    Create your first tag
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = tags.map(tag => `
        <button type="button" onclick="setTagFilter(${tag.id})" data-tag-id="${tag.id}" 
                class="tag-filter-option w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors ${currentTagFilter === tag.id ? 'selected' : ''}">
            <div class="tag-filter-badge" style="background-color: ${tag.color}"></div>
            ${tag.name}
        </button>
    `).join('');
}

// ========================
// TAG UTILITY FUNCTIONS
// ========================

// Render tag badges for a goal
function renderTagBadges(goal, maxVisible = 3) {
    if (!goal.tags || goal.tags.length === 0) {
        return '';
    }
    
    const visibleTags = goal.tags.slice(0, maxVisible);
    const remainingCount = Math.max(0, goal.tags.length - maxVisible);
    
    let badgesHtml = visibleTags.map(tag => `
        <span class="tag-badge" style="background-color: ${tag.color}">
            ${tag.name}
        </span>
    `).join('');
    
    if (remainingCount > 0) {
        badgesHtml += `
            <span class="tag-badge" style="background-color: #6b7280" title="${goal.tags.slice(maxVisible).map(t => t.name).join(', ')}">
                +${remainingCount}
            </span>
        `;
    }
    
    return badgesHtml;
}

// Render modern tag badges for redesigned header
function renderModernTagBadges(goal, maxVisible = 3) {
    if (!goal.tags || goal.tags.length === 0) {
        return '';
    }
    
    const visibleTags = goal.tags.slice(0, maxVisible);
    const remainingCount = Math.max(0, goal.tags.length - maxVisible);
    
    let badgesHtml = visibleTags.map(tag => `
        <span class="modern-tag-badge" style="background-color: ${tag.color}">
            ${tag.name}
        </span>
    `).join('');
    
    if (remainingCount > 0) {
        badgesHtml += `
            <span class="modern-tag-badge modern-tag-more" title="${goal.tags.slice(maxVisible).map(t => t.name).join(', ')}">
                +${remainingCount}
            </span>
        `;
    }
    
    return badgesHtml;
}

// ========================
// TAG SELECTION FUNCTIONS
// ========================

// Note: selectedTagIds is already declared at the top of the file
let editSelectedTagIds = [];

// Render tag selector for goal forms
function renderTagSelector(containerId, selectedIds = []) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (tags.length === 0) {
        container.innerHTML = `
            <p class="text-sm text-gray-500 text-center py-4">
                No tags available. 
                <button type="button" onclick="showTagManagementModal()" class="text-blue-600 hover:text-blue-800 underline">
                    Create your first tag
                </button>
            </p>
        `;
        return;
    }
    
    container.innerHTML = tags.map(tag => {
        const isSelected = selectedIds.includes(tag.id);
        return `
            <div class="tag-option ${isSelected ? 'selected' : ''}" 
                 onclick="toggleTagSelection(${tag.id}, '${containerId}')">
                <div class="tag-option-color" style="background-color: ${tag.color}"></div>
                <div class="tag-option-name">${tag.name}</div>
                ${isSelected ? '<i class="fas fa-check text-blue-600 ml-auto"></i>' : ''}
            </div>
        `;
    }).join('');
}

// Toggle tag selection
window.toggleTagSelection = function(tagId, containerId) {
    console.log('🏷️ Toggling tag selection:', tagId, 'in container:', containerId);
    let targetArray;
    
    if (containerId.includes('create')) {
        targetArray = selectedTagIds;
    } else if (containerId.includes('edit')) {
        targetArray = editSelectedTagIds;
    } else {
        console.warn('Unknown container ID:', containerId);
        return;
    }
    
    const index = targetArray.indexOf(tagId);
    if (index > -1) {
        targetArray.splice(index, 1);
        console.log('📤 Removed tag', tagId, 'from selection');
    } else {
        targetArray.push(tagId);
        console.log('📥 Added tag', tagId, 'to selection');
    }
    
    console.log('🏷️ Updated selection array:', targetArray);
    
    // Re-render to update selection state
    renderTagSelector(containerId, targetArray);
}

// Get selected tags data
function getSelectedTagsData(tagIds) {
    return tags.filter(tag => tagIds.includes(tag.id));
}

// Update goal tags
async function updateGoalTags(goalId, tagIds) {
    try {
        console.log('🚀 Making API call to update goal tags:', { goalId, tagIds });
        const response = await fetch(`/api/goals/${goalId}/tags`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ tag_ids: tagIds }),
            credentials: 'include'
        });
        
        console.log('📡 API response status:', response.status);
        
        if (!response.ok) {
            const error = await response.json();
            console.error('❌ API error:', error);
            throw new Error(error.error || 'Failed to update goal tags');
        }
        
        const result = await response.json();
        console.log('✅ API success:', result);
        
    } catch (error) {
        console.error('Error updating goal tags:', error);
        throw error;
    }
}

// ========================
// TAG MANAGEMENT FUNCTIONS
// ========================

let currentEditingTagId = null;

// Show tag management modal
window.showTagManagementModal = function() {
    const modal = document.getElementById('tag-management-modal');
    modal.classList.remove('hidden');
    
    // Initialize tag color picker
    initializeTagColorPicker();
    
    // Render existing tags
    renderTagsList();
    
    // Reset form state
    cancelTagForm();
}

// Close tag management modal
window.closeTagManagementModal = function() {
    const modal = document.getElementById('tag-management-modal');
    modal.classList.add('hidden');
    cancelTagForm();
}

// Initialize color picker
function initializeTagColorPicker() {
    const colorPicker = document.getElementById('tag-color-picker');
    if (!colorPicker) return;
    
    colorPicker.innerHTML = '';
    
    tagColors.forEach((color, index) => {
        const colorOption = document.createElement('div');
        colorOption.className = `color-option ${index === 0 ? 'selected' : ''}`;
        colorOption.style.backgroundColor = color.value;
        colorOption.title = color.name;
        colorOption.onclick = () => selectTagColor(color.value, colorOption);
        
        colorPicker.appendChild(colorOption);
    });
    
    // Set default color
    document.getElementById('selected-tag-color').value = tagColors[0].value;
    updateTagPreview();
}

// Select tag color
function selectTagColor(color, element) {
    // Remove selection from all color options
    document.querySelectorAll('.color-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    
    // Select this color
    element.classList.add('selected');
    document.getElementById('selected-tag-color').value = color;
    
    updateTagPreview();
}

// Update tag preview
function updateTagPreview() {
    const nameInput = document.getElementById('tag-name-input');
    const colorInput = document.getElementById('selected-tag-color');
    const preview = document.getElementById('tag-preview');
    
    if (nameInput && colorInput && preview) {
        const name = nameInput.value.trim() || 'Sample Tag';
        const color = colorInput.value;
        
        preview.textContent = name;
        preview.style.backgroundColor = color;
    }
}

// Show tag creation form
window.showTagCreationForm = function() {
    const form = document.getElementById('tag-creation-form');
    const createBtn = document.getElementById('create-tag-btn');
    const formTitle = document.getElementById('tag-form-title');
    const saveBtn = document.getElementById('save-tag-btn');
    
    // Reset form for new tag
    currentEditingTagId = null;
    document.getElementById('tag-name-input').value = '';
    
    // Update UI
    form.classList.remove('hidden');
    createBtn.style.display = 'none';
    formTitle.textContent = 'Create New Tag';
    saveBtn.innerHTML = '<i class="fas fa-check mr-2"></i>Create Tag';
    
    // Reset color selection
    initializeTagColorPicker();
    
    // Focus on name input
    setTimeout(() => {
        document.getElementById('tag-name-input').focus();
    }, 100);
}

// Edit existing tag
window.editTag = function(tagId) {
    const tag = tags.find(t => t.id === tagId);
    if (!tag) return;
    
    const form = document.getElementById('tag-creation-form');
    const createBtn = document.getElementById('create-tag-btn');
    const formTitle = document.getElementById('tag-form-title');
    const saveBtn = document.getElementById('save-tag-btn');
    const nameInput = document.getElementById('tag-name-input');
    const colorInput = document.getElementById('selected-tag-color');
    
    // Set editing mode
    currentEditingTagId = tagId;
    
    // Populate form
    nameInput.value = tag.name;
    colorInput.value = tag.color;
    
    // Update UI
    form.classList.remove('hidden');
    createBtn.style.display = 'none';
    formTitle.textContent = 'Edit Tag';
    saveBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Update Tag';
    
    // Initialize color picker and select current color
    initializeTagColorPicker();
    const colorOption = document.querySelector(`[style*="${tag.color}"]`);
    if (colorOption) {
        selectTagColor(tag.color, colorOption);
    }
    
    updateTagPreview();
    
    // Focus on name input
    setTimeout(() => {
        nameInput.focus();
        nameInput.select();
    }, 100);
}

// Cancel tag form
window.cancelTagForm = function() {
    const form = document.getElementById('tag-creation-form');
    const createBtn = document.getElementById('create-tag-btn');
    
    form.classList.add('hidden');
    createBtn.style.display = 'inline-flex';
    
    // Reset form
    currentEditingTagId = null;
    document.getElementById('tag-name-input').value = '';
    initializeTagColorPicker();
}

// Save tag (create or update)
window.saveTag = async function() {
    const nameInput = document.getElementById('tag-name-input');
    const colorInput = document.getElementById('selected-tag-color');
    const saveBtn = document.getElementById('save-tag-btn');
    
    const name = nameInput.value.trim();
    const color = colorInput.value;
    
    if (!name) {
        authUtils.showErrorMessage('Please enter a tag name');
        nameInput.focus();
        return;
    }
    
    // Check for duplicate names (excluding current tag when editing)
    const existingTag = tags.find(t => t.name.toLowerCase() === name.toLowerCase() && t.id !== currentEditingTagId);
    if (existingTag) {
        authUtils.showErrorMessage('A tag with this name already exists');
        nameInput.focus();
        nameInput.select();
        return;
    }
    
    // Show loading state
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
    saveBtn.disabled = true;
    
    try {
        let response;
        
        if (currentEditingTagId) {
            // Update existing tag
            response = await fetch(`/api/tags/${currentEditingTagId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, color }),
                credentials: 'include'
            });
        } else {
            // Create new tag
            response = await fetch('/api/tags', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, color }),
                credentials: 'include'
            });
        }
        
        if (response.ok) {
            const tagData = await response.json();
            
            if (currentEditingTagId) {
                // Update existing tag in array
                const tagIndex = tags.findIndex(t => t.id === currentEditingTagId);
                if (tagIndex !== -1) {
                    tags[tagIndex] = tagData;
                }
                authUtils.showSuccessMessage(`Tag "${name}" updated successfully`);
            } else {
                // Add new tag to array
                tags.push(tagData);
                authUtils.showSuccessMessage(`Tag "${name}" created successfully`);
            }
            
            // Refresh tags list
            renderTagsList();
            
            // Reset form
            cancelTagForm();
            
        } else {
            const error = await response.json();
            authUtils.showErrorMessage(error.error || 'Failed to save tag');
        }
        
    } catch (error) {
        console.error('Error saving tag:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
    } finally {
        // Restore button state
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    }
}

// Delete tag
window.deleteTag = async function(tagId) {
    const tag = tags.find(t => t.id === tagId);
    if (!tag) return;
    
    if (!confirm(`Are you sure you want to delete the tag "${tag.name}"?\n\nThis will remove it from all goals that use it.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/tags/${tagId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            // Remove from local array
            tags = tags.filter(t => t.id !== tagId);
            
            // Refresh tags list
            renderTagsList();
            
            // Refresh goals to update any that had this tag
            await loadDashboardData();
            
            authUtils.showSuccessMessage(`Tag "${tag.name}" deleted successfully`);
        } else {
            const error = await response.json();
            authUtils.showErrorMessage(error.error || 'Failed to delete tag');
        }
        
    } catch (error) {
        console.error('Error deleting tag:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

// Render tags list
function renderTagsList() {
    const tagsList = document.getElementById('tags-list');
    const emptyState = document.getElementById('tags-empty-state');
    
    if (!tagsList || !emptyState) return;
    
    if (tags.length === 0) {
        tagsList.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }
    
    emptyState.classList.add('hidden');
    
    tagsList.innerHTML = tags.map(tag => `
        <div class="tag-item">
            <div class="tag-item-color" style="background-color: ${tag.color}"></div>
            <div class="tag-item-name">${tag.name}</div>
            <div class="tag-item-actions">
                <button onclick="editTag(${tag.id})" class="tag-item-btn edit">
                    <i class="fas fa-edit"></i>
                    Edit
                </button>
                <button onclick="deleteTag(${tag.id})" class="tag-item-btn delete">
                    <i class="fas fa-trash"></i>
                    Delete
                </button>
            </div>
        </div>
    `).join('');
}

// Add event listeners for tag form
document.addEventListener('DOMContentLoaded', function() {
    // Tag name input listeners
    const tagNameInput = document.getElementById('tag-name-input');
    if (tagNameInput) {
        tagNameInput.addEventListener('input', updateTagPreview);
        tagNameInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                saveTag();
            }
        });
    }
    
    // Close tag modal when clicking outside
    const tagModal = document.getElementById('tag-management-modal');
    if (tagModal) {
        tagModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeTagManagementModal();
            }
        });
    }
});

// Load more functionality
window.loadMoreGoals = function() {
    currentPage++;
    renderGoals();
    saveUserSettings();
}

function updateLoadMoreButton() {
    const loadMoreContainer = document.getElementById('load-more-container');
    const totalShown = (currentPage + 1) * goalsPerPage;
    
    if (loadMoreContainer) {
        if (totalShown < filteredGoals.length) {
            loadMoreContainer.classList.remove('hidden');
        } else {
            loadMoreContainer.classList.add('hidden');
        }
    }
}

// Pure CSS hover animations - no JavaScript manipulation needed

// Additional event listeners - set up when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Close modals when clicking outside
    const createModal = document.getElementById('create-goal-modal');
    if (createModal) {
        createModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeCreateGoalModal();
            }
        });
    }
    
    const editModal = document.getElementById('edit-goal-modal');
    if (editModal) {
        editModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeEditGoalModal();
            }
        });
    }
});