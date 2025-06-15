// Authentication JavaScript

// Utility functions
function showSuccessMessage(message) {
    const successDiv = document.getElementById('success-message');
    const successText = document.getElementById('success-text');
    successText.textContent = message;
    successDiv.classList.remove('hidden');
    successDiv.classList.add('bounce-in');
    
    setTimeout(() => {
        successDiv.classList.add('hidden');
        successDiv.classList.remove('bounce-in');
    }, 4000);
}

function showErrorMessage(message) {
    const errorDiv = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    errorText.textContent = message;
    errorDiv.classList.remove('hidden');
    errorDiv.classList.add('bounce-in');
    
    setTimeout(() => {
        errorDiv.classList.add('hidden');
        errorDiv.classList.remove('bounce-in');
    }, 4000);
}

function showLoadingSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.classList.remove('hidden');
    }
}

function hideLoadingSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.classList.add('hidden');
    }
}

// Login functionality
document.getElementById('login-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const remember = document.getElementById('remember-me').checked;
    
    if (!username || !password) {
        showErrorMessage('Please fill in all fields!');
        return;
    }
    
    showLoadingSpinner();
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password,
                remember: remember
            }),
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccessMessage(`Welcome back, ${data.user.username}!`);
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            showErrorMessage(data.error || 'Login failed. Please try again!');
        }
    } catch (error) {
        console.error('Login error:', error);
        showErrorMessage('Connection error. Please check your internet!');
    } finally {
        hideLoadingSpinner();
    }
});

// Register functionality
document.getElementById('register-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;
    
    // Validation
    if (!username || !email || !password || !confirmPassword) {
        showErrorMessage('Please fill in all fields!');
        return;
    }
    
    if (password !== confirmPassword) {
        showErrorMessage('Passwords do not match!');
        return;
    }
    
    if (password.length < 6) {
        showErrorMessage('Password must be at least 6 characters long!');
        return;
    }
    
    if (username.length < 3) {
        showErrorMessage('Username must be at least 3 characters long!');
        return;
    }
    
    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showErrorMessage('Please enter a valid email address!');
        return;
    }
    
    showLoadingSpinner();
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                email: email,
                password: password
            }),
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccessMessage(`Welcome to LetsGoal, ${data.user.username}!`);
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            showErrorMessage(data.error || 'Registration failed. Please try again!');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showErrorMessage('Connection error. Please check your internet!');
    } finally {
        hideLoadingSpinner();
    }
});

// Logout functionality
async function logout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            showSuccessMessage('Logged out successfully! See you soon!');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1500);
        } else {
            showErrorMessage('Logout failed. Please try again!');
        }
    } catch (error) {
        console.error('Logout error:', error);
        showErrorMessage('Connection error. Please check your internet!');
    }
}

// Check authentication status
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/check', {
            credentials: 'include'
        });
        
        const data = await response.json();
        return data.authenticated ? data.user : null;
    } catch (error) {
        console.error('Auth check error:', error);
        return null;
    }
}

// Get current user
async function getCurrentUser() {
    try {
        const response = await fetch('/api/auth/me', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            return data.user;
        }
        return null;
    } catch (error) {
        console.error('Get user error:', error);
        return null;
    }
}

// Export functions for use in other files
window.authUtils = {
    showSuccessMessage,
    showErrorMessage,
    showLoadingSpinner,
    hideLoadingSpinner,
    logout,
    checkAuthStatus,
    getCurrentUser
};