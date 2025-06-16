// Dashboard JavaScript

console.log('🚀 Dashboard.js is loading...'); // Debug log

let currentUser = null;
let goals = [];
let progressChart = null;
let filteredGoals = [];
let currentViewMode = 'grid';
let currentFilter = 'all';
let currentSort = 'recent';
let currentPage = 0;
const goalsPerPage = 9;

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

// Initialize dashboard
window.addEventListener('load', async function() {
    // Check authentication
    currentUser = await authUtils.checkAuthStatus();
    if (!currentUser) {
        window.location.href = '/login';
        return;
    }
    
    // Update welcome message
    document.getElementById('user-welcome').innerHTML = `
        Welcome, ${currentUser.username}
    `;
    
    // Load dashboard data
    await loadDashboardData();
    
    // Set daily motivational quote
    setDailyQuote();
    
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

// Update stats display
function updateStatsDisplay(stats) {
    document.getElementById('total-goals').textContent = stats.total_goals;
    document.getElementById('achieved-goals').textContent = stats.completed_goals;
    document.getElementById('active-goals').textContent = stats.active_goals;
    document.getElementById('achievement-rate').textContent = `${stats.achievement_rate}%`;
}

// Update progress chart to show recent progress trends
function updateProgressChart(stats) {
    const ctx = document.getElementById('progress-chart');
    if (!ctx) {
        console.error('Progress chart canvas not found');
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
}

// Generate recent progress data for the last 7 days
function generateRecentProgressData() {
    const days = [];
    const subgoalData = [];
    const goalData = [];
    
    // Get last 7 days
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        
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
    const isToday = date.toDateString() === today.toDateString();
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
    
    // Update load more button
    updateLoadMoreButton();
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
            
            <!-- Header with title and status -->
            <div class="mb-3">
                <div class="flex items-start justify-between gap-2">
                    <h3 class="text-lg font-semibold text-gray-900 flex-1">${goal.title}</h3>
                    <span class="status-badge ${getStatusBadgeClass(goal.status)} flex-shrink-0 ml-2" 
                          title="${goal.status.replace('_', ' ').toUpperCase()}">
                        <i class="fas ${getStatusIcon(goal.status)}"></i>
                    </span>
                </div>
            </div>
            
            <!-- Description -->
            ${goal.description ? `<p class="text-gray-600 text-sm mb-4 line-clamp-2">${goal.description}</p>` : ''}
            
            <!-- Progress and Stats -->
            <div class="flex items-center justify-between mb-4">
                <div class="progress-circle">
                    <div class="w-16 h-16 rounded-full flex items-center justify-center" 
                         style="background: conic-gradient(${progressColor} ${goal.progress * 3.6}deg, #f3f4f6 ${goal.progress * 3.6}deg);">
                        <div class="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                            <span class="progress-text">${Math.round(goal.progress)}%</span>
                        </div>
                    </div>
                </div>
                <div class="text-right">
                    <div class="text-sm text-gray-500">Target Date</div>
                    <div class="text-sm font-medium">${goal.target_date ? new Date(goal.target_date).toLocaleDateString() : 'Not set'}</div>
                </div>
            </div>
            
            <!-- Subgoals Preview with Pure CSS Hover Expansion -->
            ${goal.subgoals.length > 0 ? `
                <div class="border-t pt-3 mt-auto subgoals-section ${hasHiddenSubgoals ? 'has-hidden-subgoals' : ''}">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-sm text-gray-600">Sub-goals</span>
                        <span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                            ${goal.subgoals.filter(sg => sg.status === 'achieved').length}/${goal.subgoals.length}
                        </span>
                    </div>
                    
                    <!-- Single Unified Subgoals List -->
                    <div class="subgoals-list space-y-1">
                        ${goal.subgoals.map((subgoal, index) => `
                            <div class="subgoal-item ${subgoal.status === 'achieved' ? 'completed' : ''} ${index >= 3 ? 'hidden-subgoal' : 'visible-subgoal'}" 
                                 style="--animation-delay: ${index * 0.05}s">
                                <div class="flex items-center w-full">
                                    <input type="checkbox" 
                                           id="subgoal-${subgoal.id}"
                                           class="h-3 w-3 text-blue-600 rounded mr-2 flex-shrink-0" 
                                           ${subgoal.status === 'achieved' ? 'checked' : ''}
                                           onclick="event.stopPropagation();"
                                           onchange="quickUpdateSubgoal(${subgoal.id}, this.checked, ${goal.id}); event.stopPropagation();">
                                    <span class="truncate flex-1 cursor-pointer" 
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
                <div class="border-t pt-3 mt-auto text-center">
                    <span class="text-sm text-gray-500">No sub-goals yet</span>
                </div>
            `}
            
            <!-- Quick Actions -->
            <div class="flex gap-2 mt-4 pt-3 border-t">
                <button onclick="editGoal(${goal.id}); event.stopPropagation();" 
                        class="flex-1 btn-secondary text-xs py-2">
                    <i class="fas fa-edit mr-1"></i>
                    Edit
                </button>
                ${goal.status !== 'completed' ? `
                    <button onclick="updateGoalStatus(${goal.id}, 'completed'); event.stopPropagation();" 
                            class="flex-1 btn-success text-xs py-2">
                        <i class="fas fa-trophy mr-1"></i>
                        Complete
                    </button>
                ` : ''}
                <button onclick="deleteGoal(${goal.id}); event.stopPropagation();" 
                        class="px-3 py-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors text-xs">
                    <i class="fas fa-trash"></i>
                </button>
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
                    
                    ${goal.description ? `<p class="text-gray-600 mb-4">${goal.description}</p>` : ''}
                    
                    <div class="flex items-center space-x-6 text-sm text-gray-500 mb-4">
                        <span class="flex items-center">
                            <i class="fas fa-calendar-alt mr-2"></i>
                            ${goal.target_date ? new Date(goal.target_date).toLocaleDateString() : 'No target date'}
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
    
    const target = new Date(targetDate);
    const today = new Date();
    const diffTime = target - today;
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
    // Set default target date to 30 days from now
    const defaultDate = new Date();
    defaultDate.setDate(defaultDate.getDate() + 30);
    document.getElementById('goal-target-date').value = defaultDate.toISOString().split('T')[0];
}

window.closeCreateGoalModal = function() {
    console.log('🎯 Closing create goal modal'); // Debug log
    document.getElementById('create-goal-modal').classList.add('hidden');
    document.getElementById('create-goal-form').reset();
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
    
    // Populate the edit form
    document.getElementById('edit-goal-id').value = goal.id;
    document.getElementById('edit-goal-title').value = goal.title;
    document.getElementById('edit-goal-description').value = goal.description || '';
    document.getElementById('edit-goal-target-date').value = goal.target_date || '';
    document.getElementById('edit-goal-status').value = goal.status;
    
    // Load subgoals
    loadSubgoalsForEdit(goal.subgoals || []);
    
    // Show modal
    document.getElementById('edit-goal-modal').classList.remove('hidden');
    
    // Setup event listeners for this modal instance
    setupEditModalEventListeners();
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
}

window.closeEditGoalModal = function() {
    const editModal = document.getElementById('edit-goal-modal');
    const subgoalModal = document.getElementById('subgoal-creator-modal');
    
    // Re-enable background scrolling
    document.body.classList.remove('modal-open');
    
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
    row.className = 'subgoal-item bg-white border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-all';
    row.innerHTML = `
        <input type="hidden" class="subgoal-id" value="${subgoal?.id || ''}">
        <div class="flex items-start space-x-3">
            <input type="checkbox" 
                   class="form-checkbox subgoal-checkbox mt-1" 
                   ${subgoal?.status === 'achieved' ? 'checked' : ''}
                   onchange="toggleSubgoalStatus(this)"
                   ${!subgoal?.id ? 'disabled' : ''}>
            <div class="flex-1">
                <input type="text" 
                       class="subgoal-title input-field w-full mb-2 ${subgoal?.status === 'achieved' ? 'line-through text-gray-500' : ''}" 
                       value="${subgoal?.title || ''}" 
                       placeholder="Enter sub-goal title" 
                       required>
                <textarea class="subgoal-description input-field w-full text-sm" 
                          rows="1" 
                          placeholder="Description (optional)">${subgoal?.description || ''}</textarea>
                ${subgoal?.target_date ? `
                    <input type="date" 
                           class="subgoal-target-date input-field w-full text-sm mt-2" 
                           value="${subgoal.target_date}">
                ` : `
                    <input type="date" 
                           class="subgoal-target-date input-field w-full text-sm mt-2" 
                           placeholder="Target date (optional)">
                `}
                <input type="hidden" class="subgoal-status" value="${subgoal?.status || 'pending'}">
            </div>
            <button type="button" onclick="removeSubgoalFromList(this)" class="text-red-500 hover:text-red-700 p-2 rounded hover:bg-red-50 transition-colors" title="Remove sub-goal">
                <i class="fas fa-trash text-sm"></i>
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
            
            authUtils.showSuccessMessage('Goal updated successfully');
            await loadDashboardData();
            closeEditGoalModal();
            
            // Restore button state
            const updateBtn = document.getElementById('update-goal-btn');
            if (updateBtn) {
                updateBtn.innerHTML = '<i class="fas fa-save mr-2"></i> Update Goal';
                updateBtn.disabled = false;
            }
        } else {
            const error = await response.json();
            console.error('❌ API error response:', error); // Debug log
            authUtils.showErrorMessage(error.error || 'Failed to update goal');
            
            // Restore button state
            const updateBtn = document.getElementById('update-goal-btn');
            if (updateBtn) {
                updateBtn.innerHTML = '<i class="fas fa-save mr-2"></i> Update Goal';
                updateBtn.disabled = false;
            }
        }
    } catch (error) {
        console.error('❌ Network error updating goal:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
        
        // Restore button state
        const updateBtn = document.getElementById('update-goal-btn');
        if (updateBtn) {
            updateBtn.innerHTML = '<i class="fas fa-save mr-2"></i> Update Goal';
            updateBtn.disabled = false;
        }
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
                                    <span>Target: ${goal.target_date ? new Date(goal.target_date).toLocaleDateString() : 'No date'}</span>
                                    <span>Achieved: ${goal.achieved_date ? new Date(goal.achieved_date).toLocaleDateString() : 'Unknown'}</span>
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
        const updateBtn = document.getElementById('update-goal-btn');
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
        
    } catch (error) {
        console.error('❌ Error in goal update process:', error);
        if (window.authUtils) {
            window.authUtils.showErrorMessage(`Failed to update goal: ${error.message}`);
        } else {
            alert(`Failed to update goal: ${error.message}`);
        }
        
        // Restore button state
        const updateBtn = document.getElementById('update-goal-btn');
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
    
    // Apply sorting
    filtered.sort((a, b) => {
        switch (currentSort) {
            case 'recent':
                return new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at);
            case 'target':
                if (!a.target_date && !b.target_date) return 0;
                if (!a.target_date) return 1;
                if (!b.target_date) return -1;
                return new Date(a.target_date) - new Date(b.target_date);
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
    
    if (dropdown.classList.contains('hidden')) {
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
    label.textContent = filterLabels[filterValue];
    
    closeFilterDropdown();
    renderGoals();
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
        'name': 'Name'
    };
    label.textContent = sortLabels[sortValue];
    
    closeSortDropdown();
    renderGoals();
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
}

// Load more functionality
window.loadMoreGoals = function() {
    currentPage++;
    renderGoals();
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