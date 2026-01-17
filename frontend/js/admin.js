// Admin Dashboard JavaScript
// Manages all admin panel functionality

let currentSection = 'overview';
let currentTheme = localStorage.getItem('theme') || 'light';
let charts = {}; // Store chart instances for proper cleanup

// Initialize admin dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    loadOverviewData();
    setActiveSection('overview');
    
    // Initialize form handlers only if elements exist
    initializeFormHandlers();
});

// Initialize form event handlers
function initializeFormHandlers() {
    // SMS form handler
    const smsForm = document.getElementById('sms-provider-form');
    if (smsForm) {
        smsForm.addEventListener('submit', handleSMSFormSubmit);
    }
}

// Theme Management
function initializeTheme() {
    document.documentElement.setAttribute('data-theme', currentTheme);
}

function toggleTheme() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', currentTheme);
    document.documentElement.setAttribute('data-theme', currentTheme);
}

// Navigation
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.add('hidden');
    });
    
    // Show selected section
    const targetSection = document.getElementById(sectionName + '-section');
    if (targetSection) {
        targetSection.classList.remove('hidden');
    }
    
    // Update active navigation
    setActiveSection(sectionName);
    currentSection = sectionName;
    
    // Load section data
    console.log('Loading section data for:', sectionName);
    switch(sectionName) {
        case 'overview':
            loadOverviewData();
            break;
        case 'users':
            loadUsersData();
            break;
        case 'subscriptions':
            loadSubscriptionsData();
            break;
        case 'plans':
            loadPlansData();
            break;
        case 'sms':
            loadSMSData();
            break;
        case 'backups':
            console.log('=== Calling loadBackupsData ===');
            loadBackupsData();
            break;
        case 'settings':
            loadSettingsData();
            break;
    }
}

function setActiveSection(sectionName) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Find and activate the clicked nav item
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        if (item.getAttribute('onclick')?.includes(sectionName)) {
            item.classList.add('active');
        }
    });
}

// API Helper Functions
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(`/api/admin${endpoint}`, options);
    
    if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/login?next=/admin';
            return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response.json();
}

function showLoading(show = true) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        if (show) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    }
}

function showNotification(message, type = 'info') {
    // Simple alert for now - could be enhanced with a proper notification system
    alert(message);
}

// Overview Data Loading
async function loadOverviewData() {
    try {
        showLoading(true);
        
        // Load system overview stats
        const overviewStats = await apiCall('/stats/overview');
        updateOverviewStats(overviewStats);
        
        // Load and create charts with error handling
        try {
            const revenueData = await apiCall('/subscriptions/stats/revenue');
            createRevenueChart(revenueData);
        } catch (error) {
            console.warn('Revenue chart data not available:', error);
            createRevenueChart({ daily_revenue: [], revenue_by_plan: {} });
        }
        
        try {
            const subscriptionStats = await apiCall('/subscriptions/stats/overview');
            createSubscriptionChart(subscriptionStats);
        } catch (error) {
            console.warn('Subscription chart data not available:', error);
            createSubscriptionChart({ plan_distribution: {} });
        }
        
    } catch (error) {
        console.error('Failed to load overview data:', error);
        // Set default values
        updateOverviewStats({
            users: { total: 0, active_sessions: 0 },
            goals: { total: 0, completed: 0 },
            timestamp: new Date().toISOString()
        });
    } finally {
        showLoading(false);
    }
}

function updateOverviewStats(stats) {
    // Update user stats
    const totalUsersEl = document.getElementById('total-users');
    if (totalUsersEl) {
        totalUsersEl.textContent = stats.users?.total || 0;
    }
    
    // Update subscription stats
    const activeSubsEl = document.getElementById('active-subscriptions');
    if (activeSubsEl) {
        activeSubsEl.textContent = stats.subscriptions?.active || 0;
    }
    
    // Update revenue stats
    const monthlyRevenueEl = document.getElementById('monthly-revenue');
    if (monthlyRevenueEl) {
        monthlyRevenueEl.textContent = '$' + (stats.revenue?.monthly || 0);
    }
    
    // Update SMS stats
    const smsSentEl = document.getElementById('sms-sent');
    if (smsSentEl) {
        smsSentEl.textContent = stats.sms?.sent_today || 0;
    }
}

function createRevenueChart(data) {
    const canvas = document.getElementById('revenue-chart');
    if (!canvas) {
        console.warn('Revenue chart canvas not found');
        return;
    }
    
    // Destroy existing chart if it exists
    if (charts.revenue) {
        charts.revenue.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    
    // Process the data
    const dailyRevenue = data.daily_revenue || [];
    const labels = dailyRevenue.map(item => item.date || 'N/A');
    const values = dailyRevenue.map(item => item.revenue || 0);
    
    charts.revenue = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels.length > 0 ? labels : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                label: 'Daily Revenue',
                data: values.length > 0 ? values : [0, 0, 0, 0, 0, 0],
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value;
                        }
                    }
                }
            }
        }
    });
}

function createSubscriptionChart(data) {
    const canvas = document.getElementById('subscription-chart');
    if (!canvas) {
        console.warn('Subscription chart canvas not found');
        return;
    }
    
    // Destroy existing chart if it exists
    if (charts.subscription) {
        charts.subscription.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    
    // Process the data
    const planDistribution = data.plan_distribution || {};
    const labels = Object.keys(planDistribution);
    const values = Object.values(planDistribution);
    
    charts.subscription = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.length > 0 ? labels : ['Free', 'Pro', 'Business'],
            datasets: [{
                data: values.length > 0 ? values : [50, 30, 20],
                backgroundColor: [
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(34, 197, 94, 0.8)',
                    'rgba(168, 85, 247, 0.8)',
                    'rgba(245, 158, 11, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Users Data Loading
async function loadUsersData() {
    try {
        showLoading(true);
        const users = await apiCall('/users');
        renderUsersTable(users);
    } catch (error) {
        console.error('Failed to load users data:', error);
        renderUsersTable({ users: [], total: 0 });
    } finally {
        showLoading(false);
    }
}

function renderUsersTable(data) {
    const tableBody = document.getElementById('users-table');
    if (!tableBody) return;
    
    if (!data.users || data.users.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="px-6 py-4 text-center text-gray-500">No users found</td></tr>';
        return;
    }
    
    tableBody.innerHTML = data.users.map(user => `
        <tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                        <div class="h-10 w-10 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">${user.username.charAt(0).toUpperCase()}</span>
                        </div>
                    </div>
                    <div class="ml-4">
                        <div class="text-sm font-medium text-gray-900 dark:text-white">${user.username}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">${user.email}</div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${user.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'}">
                    ${user.role || 'user'}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                ${user.subscription_plan || 'Free'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                ${user.stats?.total_goals || 0} / ${user.stats?.completed_goals || 0}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button onclick="editUser(${user.id})" class="text-blue-600 hover:text-blue-900 mr-3">Edit</button>
                <button onclick="deleteUser(${user.id})" class="text-red-600 hover:text-red-900">Delete</button>
            </td>
        </tr>
    `).join('');
}

// SMS Data Loading
async function loadSMSData() {
    try {
        showLoading(true);
        
        // Load SMS statistics
        const smsStats = await apiCall('/sms/stats');
        updateSMSStats(smsStats);
        
        // Load SMS settings
        const smsSettings = await apiCall('/sms/settings');
        updateSMSSettings(smsSettings);
        
    } catch (error) {
        console.error('Failed to load SMS data:', error);
        // Set default values
        updateSMSStats({
            today: 0,
            week: 0,
            month: 0,
            total_cost: 0
        });
    } finally {
        showLoading(false);
    }
}

function updateSMSStats(stats) {
    const elements = {
        'sms-today': stats.today || 0,
        'sms-week': stats.week || 0,
        'sms-month': stats.month || 0,
        'sms-cost': '$' + (stats.total_cost || 0).toFixed(2)
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

function updateSMSSettings(settings) {
    const elements = {
        'sms-provider': settings.provider || 'twilio',
        'sms-account-sid': settings.account_sid || '',
        'sms-from-number': settings.from_number || ''
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.value = value;
        }
    });
}

async function handleSMSFormSubmit(e) {
    e.preventDefault();
    
    const formData = {
        provider: document.getElementById('sms-provider').value,
        account_sid: document.getElementById('sms-account-sid').value,
        auth_token: document.getElementById('sms-auth-token').value,
        from_number: document.getElementById('sms-from-number').value
    };
    
    try {
        await apiCall('/sms/settings', 'PUT', formData);
        showNotification('SMS settings saved successfully', 'success');
    } catch (error) {
        console.error('Failed to save SMS settings:', error);
        showNotification('Failed to save SMS settings', 'error');
    }
}

// Placeholder functions for other sections
async function loadSubscriptionsData() {
    console.log('Loading subscriptions data...');
}

async function loadPlansData() {
    console.log('Loading plans data...');
}

// Backup Management Functions
async function loadBackupsData() {
    console.log('=== loadBackupsData called ===');
    try {
        showLoading(true);
        
        // Load backup list
        console.log('Making API call to /backup/list');
        const backupsData = await apiCall('/backup/list');
        console.log('Received backup data:', backupsData);
        
        renderBackupsTable(backupsData);
        updateBackupStats(backupsData);
        
    } catch (error) {
        console.error('Failed to load backups data:', error);
        renderBackupsTable({ backups: [], pagination: { total: 0 } });
        updateBackupStats({ backups: [], pagination: { total: 0 } });
    } finally {
        showLoading(false);
    }
}

function updateBackupStats(data) {
    const backups = data.backups || [];
    
    // Update backup count
    const countEl = document.getElementById('backup-count');
    if (countEl) {
        countEl.textContent = backups.length;
    }
    
    // Calculate total size
    const totalSize = backups.reduce((sum, backup) => sum + (backup.backup_size || 0), 0);
    const sizeEl = document.getElementById('backup-size');
    if (sizeEl) {
        sizeEl.textContent = formatBytes(totalSize);
    }
    
    // Find last backup
    const lastBackup = backups.length > 0 ? backups[0] : null;
    const lastBackupEl = document.getElementById('last-backup');
    if (lastBackupEl) {
        lastBackupEl.textContent = lastBackup ? 
            formatDateTime(lastBackup.created_at) : 'Never';
    }
}

function renderBackupsTable(data) {
    console.log('renderBackupsTable called with data:', data);
    const tableBody = document.getElementById('backups-table');
    console.log('backups-table element:', tableBody);
    if (!tableBody) {
        console.error('backups-table element not found!');
        return;
    }
    
    const backups = data.backups || [];
    console.log('Number of backups:', backups.length);
    
    if (backups.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="px-6 py-4 text-center text-gray-500">No backups found</td></tr>';
        return;
    }
    
    tableBody.innerHTML = backups.map(backup => {
        const statusColor = backup.status === 'completed' ? 'green' : 
                          backup.status === 'failed' ? 'red' : 'yellow';
        
        return `
            <tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900 dark:text-white">${backup.backup_name}</div>
                    <div class="text-sm text-gray-500 dark:text-gray-400">${backup.file_exists ? 'File exists' : 'File missing'}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getTypeColor(backup.backup_type)}">
                        ${backup.backup_type}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    ${formatBytes(backup.backup_size)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    ${formatDateTime(backup.created_at)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-${statusColor}-100 text-${statusColor}-800">
                        ${backup.status}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div class="flex space-x-2">
                        <button onclick="downloadBackup(${backup.id})" class="text-blue-600 hover:text-blue-900" title="Download">
                            📥
                        </button>
                        <button onclick="restoreBackup(${backup.id}, '${backup.backup_name}')" class="text-green-600 hover:text-green-900" title="Restore">
                            🔄
                        </button>
                        <button onclick="deleteBackup(${backup.id}, '${backup.backup_name}')" class="text-red-600 hover:text-red-900" title="Delete">
                            🗑️
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function getTypeColor(type) {
    switch (type) {
        case 'manual': return 'bg-blue-100 text-blue-800';
        case 'scheduled': return 'bg-green-100 text-green-800';
        case 'pre_update': return 'bg-yellow-100 text-yellow-800';
        default: return 'bg-gray-100 text-gray-800';
    }
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

async function createBackup() {
    const backupName = prompt('Enter backup name (optional):');
    if (backupName === null) return; // User cancelled
    
    try {
        showLoading(true);
        
        const data = {
            backup_name: backupName || undefined,
            backup_type: 'manual'
        };
        
        const result = await apiCall('/backup/create', 'POST', data);
        showNotification('Backup created successfully!', 'success');
        
        // Refresh the backup list
        loadBackupsData();
        
    } catch (error) {
        console.error('Failed to create backup:', error);
        showNotification('Failed to create backup: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function restoreBackup(backupId, backupName) {
    const confirmed = confirm(
        `Are you sure you want to restore from backup "${backupName}"?\n\n` +
        `This will replace all current data with the backup data. This action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    try {
        showLoading(true);
        
        const result = await apiCall(`/backup/${backupId}/restore`, 'POST');
        showNotification('Database restored successfully!', 'success');
        
        // Refresh the backup list
        loadBackupsData();
        
    } catch (error) {
        console.error('Failed to restore backup:', error);
        showNotification('Failed to restore backup: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function downloadBackup(backupId) {
    try {
        // Create a download link
        const downloadUrl = `/api/admin/backup/${backupId}/download`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = '';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showNotification('Backup download started', 'success');
        
    } catch (error) {
        console.error('Failed to download backup:', error);
        showNotification('Failed to download backup: ' + error.message, 'error');
    }
}

async function deleteBackup(backupId, backupName) {
    const confirmed = confirm(
        `Are you sure you want to delete backup "${backupName}"?\n\n` +
        `This will permanently remove the backup file and cannot be undone.`
    );
    
    if (!confirmed) return;
    
    try {
        showLoading(true);
        
        const result = await apiCall(`/backup/${backupId}`, 'DELETE');
        showNotification('Backup deleted successfully!', 'success');
        
        // Refresh the backup list
        loadBackupsData();
        
    } catch (error) {
        console.error('Failed to delete backup:', error);
        showNotification('Failed to delete backup: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function cleanupOldBackups() {
    const retentionDays = prompt('Enter retention days (backups older than this will be deleted):', '30');
    if (retentionDays === null) return;
    
    const days = parseInt(retentionDays);
    if (isNaN(days) || days < 1) {
        showNotification('Please enter a valid number of days (1 or greater)', 'error');
        return;
    }
    
    const confirmed = confirm(
        `Are you sure you want to delete all backups older than ${days} days?\n\n` +
        `This action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    try {
        showLoading(true);
        
        const result = await apiCall('/backup/cleanup', 'POST', { retention_days: days });
        showNotification(`Cleanup completed: ${result.deleted_count} backups deleted`, 'success');
        
        // Refresh the backup list
        loadBackupsData();
        
    } catch (error) {
        console.error('Failed to cleanup backups:', error);
        showNotification('Failed to cleanup backups: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function cleanupOrphanedBackups() {
    const confirmed = confirm(
        `Are you sure you want to cleanup orphaned backup records?\n\n` +
        `This will remove database records for backups whose files no longer exist.`
    );
    
    if (!confirmed) return;
    
    try {
        showLoading(true);
        
        const result = await apiCall('/backup/cleanup-orphaned', 'POST');
        showNotification(`Cleanup completed: ${result.deleted_count} orphaned records removed`, 'success');
        
        // Refresh the backup list
        loadBackupsData();
        
    } catch (error) {
        console.error('Failed to cleanup orphaned backups:', error);
        showNotification('Failed to cleanup orphaned backups: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function refreshBackups() {
    loadBackupsData();
}

function triggerUploadRestore() {
    const fileInput = document.getElementById('backup-upload-input');
    if (fileInput) {
        fileInput.click();
    }
}

async function handleBackupUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file extension
    if (!file.name.endsWith('.db')) {
        showNotification('Invalid file type. Please select a .db file.', 'error');
        event.target.value = '';
        return;
    }

    // Confirm with user
    const confirmed = confirm(
        `⚠️ WARNING: Upload & Restore\n\n` +
        `You are about to restore the database from:\n"${file.name}"\n\n` +
        `This will:\n` +
        `• Create a backup of your current database\n` +
        `• Replace ALL current data with the uploaded file\n` +
        `• You will be logged out after restore\n\n` +
        `Are you absolutely sure you want to proceed?`
    );

    if (!confirmed) {
        event.target.value = '';
        return;
    }

    try {
        showLoading(true);

        // Create form data
        const formData = new FormData();
        formData.append('backup_file', file);

        // Upload and restore
        const response = await fetch('/api/admin/backup/upload-restore', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Upload failed');
        }

        showNotification(
            `Database restored successfully from "${file.name}"!\n` +
            `Pre-restore backup saved. Reloading page...`,
            'success'
        );

        // Reset file input
        event.target.value = '';

        // Reload page after short delay to apply changes
        setTimeout(() => {
            window.location.reload();
        }, 2000);

    } catch (error) {
        console.error('Failed to upload and restore backup:', error);
        showNotification('Failed to restore: ' + error.message, 'error');
        event.target.value = '';
    } finally {
        showLoading(false);
    }
}

async function loadSettingsData() {
    console.log('Loading settings data...');
}

// User management functions
function editUser(userId) {
    console.log('Editing user:', userId);
    showNotification('User editing functionality coming soon');
}

function deleteUser(userId) {
    if (confirm('Are you sure you want to delete this user?')) {
        console.log('Deleting user:', userId);
        showNotification('User deletion functionality coming soon');
    }
}

function refreshUsers() {
    loadUsersData();
}

// Global functions for HTML onclick handlers
window.showSection = showSection;
window.toggleTheme = toggleTheme;
window.editUser = editUser;
window.deleteUser = deleteUser;
window.refreshUsers = refreshUsers;

// Backup management functions
window.createBackup = createBackup;
window.restoreBackup = restoreBackup;
window.downloadBackup = downloadBackup;
window.deleteBackup = deleteBackup;
window.cleanupOldBackups = cleanupOldBackups;
window.cleanupOrphanedBackups = cleanupOrphanedBackups;
window.triggerUploadRestore = triggerUploadRestore;
window.handleBackupUpload = handleBackupUpload;
window.refreshBackups = refreshBackups;