/**
 * Authentication Manager for OrderGuard AI Pro
 * Handles login, registration, logout, and session management
 */
class AuthManager {
    constructor() {
        this.tokenRefreshInterval = null;
        this.initTokenRefresh();
        this.bindEventListeners();
    }
    
    /**
     * User login
     * @param {string} email - User's email
     * @param {string} password - User's password
     * @param {boolean} rememberMe - Whether to remember the user
     * @returns {Promise<void>}
     */
    async login(email, password, rememberMe = false) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    email, 
                    password, 
                    remember_me: rememberMe 
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Show success message
                this.showMessage('Login successful!', 'success');
                
                // Redirect after short delay
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 500);
            } else {
                throw new Error(data.error || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showMessage(error.message, 'error');
            throw error;
        }
    }
    
    /**
     * User registration
     * @param {Object} userData - User registration data
     * @returns {Promise<void>}
     */
    async register(userData) {
        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showMessage('Registration successful!', 'success');
                
                // Redirect after short delay
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 500);
            } else {
                throw new Error(data.error || 'Registration failed');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.showMessage(error.message, 'error');
            throw error;
        }
    }
    
    /**
     * User logout
     * @returns {Promise<void>}
     */
    async logout() {
        try {
            const response = await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showMessage('Logged out successfully!', 'success');
                
                // Clear token refresh interval
                if (this.tokenRefreshInterval) {
                    clearInterval(this.tokenRefreshInterval);
                    this.tokenRefreshInterval = null;
                }
                
                // Redirect after short delay
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 500);
            } else {
                // Even if logout fails on server, redirect to home
                window.location.href = '/';
            }
        } catch (error) {
            console.error('Logout error:', error);
            // Redirect anyway
            window.location.href = '/';
        }
    }
    
    /**
     * Get user profile
     * @returns {Promise<Object>}
     */
    async getProfile() {
        try {
            const response = await fetch('/api/auth/profile', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                return data.profile;
            } else {
                throw new Error(data.error || 'Failed to get profile');
            }
        } catch (error) {
            console.error('Get profile error:', error);
            throw error;
        }
    }
    
    /**
     * Update user profile
     * @param {Object} profileData - Profile data to update
     * @returns {Promise<Object>}
     */
    async updateProfile(profileData) {
        try {
            const response = await fetch('/api/auth/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(profileData)
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showMessage('Profile updated successfully!', 'success');
                return data.profile;
            } else {
                throw new Error(data.error || 'Failed to update profile');
            }
        } catch (error) {
            console.error('Update profile error:', error);
            this.showMessage(error.message, 'error');
            throw error;
        }
    }
    
    /**
     * Send password reset email
     * @param {string} email - User's email
     * @returns {Promise<void>}
     */
    async resetPassword(email) {
        try {
            const response = await fetch('/api/auth/reset-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showMessage('Password reset email sent!', 'success');
            } else {
                throw new Error(data.error || 'Failed to send reset email');
            }
        } catch (error) {
            console.error('Password reset error:', error);
            this.showMessage(error.message, 'error');
            throw error;
        }
    }
    
    /**
     * Check authentication status
     * @returns {Promise<Object>}
     */
    async checkAuthStatus() {
        try {
            const response = await fetch('/api/auth/status', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Auth status check error:', error);
            return { authenticated: false };
        }
    }
    
    /**
     * Initialize automatic token refresh
     */
    initTokenRefresh() {
        // Refresh token every 30 minutes
        this.tokenRefreshInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/auth/refresh', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                if (!response.ok) {
                    console.error('Token refresh failed');
                    // Redirect to login if refresh fails
                    this.showMessage('Session expired. Please log in again.', 'warning');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                }
            } catch (error) {
                console.error('Token refresh error:', error);
                // Redirect to login if refresh fails
                window.location.href = '/login';
            }
        }, 30 * 60 * 1000); // 30 minutes
    }
    
    /**
     * Bind event listeners for forms
     */
    bindEventListeners() {
        // Login form
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', this.handleLoginSubmit.bind(this));
        }
        
        // Registration form
        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            registerForm.addEventListener('submit', this.handleRegisterSubmit.bind(this));
        }
        
        // Logout buttons
        const logoutButtons = document.querySelectorAll('.logout-btn');
        logoutButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        });
        
        // Password reset form
        const resetForm = document.getElementById('resetPasswordForm');
        if (resetForm) {
            resetForm.addEventListener('submit', this.handleResetSubmit.bind(this));
        }
    }
    
    /**
     * Handle login form submission
     * @param {Event} event - Form submit event
     */
    async handleLoginSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        
        const email = formData.get('email');
        const password = formData.get('password');
        const rememberMe = formData.get('remember_me') === 'on';
        
        if (!email || !password) {
            this.showMessage('Please enter both email and password', 'error');
            return;
        }
        
        // Disable form during submission
        this.setFormLoading(form, true);
        
        try {
            await this.login(email, password, rememberMe);
        } catch (error) {
            // Error already handled in login method
        } finally {
            this.setFormLoading(form, false);
        }
    }
    
    /**
     * Handle registration form submission
     * @param {Event} event - Form submit event
     */
    async handleRegisterSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        
        const userData = {
            email: formData.get('email'),
            password: formData.get('password'),
            password_confirm: formData.get('password_confirm'),
            username: formData.get('username'),
            organization_name: formData.get('organization_name')
        };
        
        // Basic validation
        if (!userData.email || !userData.password || !userData.username || !userData.organization_name) {
            this.showMessage('Please fill in all required fields', 'error');
            return;
        }
        
        if (userData.password !== userData.password_confirm) {
            this.showMessage('Passwords do not match', 'error');
            return;
        }
        
        if (userData.password.length < 8) {
            this.showMessage('Password must be at least 8 characters long', 'error');
            return;
        }
        
        // Remove password confirmation from data sent to server
        delete userData.password_confirm;
        
        // Disable form during submission
        this.setFormLoading(form, true);
        
        try {
            await this.register(userData);
        } catch (error) {
            // Error already handled in register method
        } finally {
            this.setFormLoading(form, false);
        }
    }
    
    /**
     * Handle password reset form submission
     * @param {Event} event - Form submit event
     */
    async handleResetSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        
        const email = formData.get('email');
        
        if (!email) {
            this.showMessage('Please enter your email address', 'error');
            return;
        }
        
        // Disable form during submission
        this.setFormLoading(form, true);
        
        try {
            await this.resetPassword(email);
        } catch (error) {
            // Error already handled in resetPassword method
        } finally {
            this.setFormLoading(form, false);
        }
    }
    
    /**
     * Set form loading state
     * @param {HTMLFormElement} form - Form element
     * @param {boolean} loading - Loading state
     */
    setFormLoading(form, loading) {
        const submitButton = form.querySelector('button[type="submit"]');
        const inputs = form.querySelectorAll('input, select, textarea');
        
        if (loading) {
            submitButton.disabled = true;
            submitButton.textContent = 'Please wait...';
            inputs.forEach(input => input.disabled = true);
        } else {
            submitButton.disabled = false;
            submitButton.textContent = submitButton.dataset.originalText || 'Submit';
            inputs.forEach(input => input.disabled = false);
        }
    }
    
    /**
     * Show message to user
     * @param {string} message - Message text
     * @param {string} type - Message type (success, error, warning, info)
     */
    showMessage(message, type = 'info') {
        // Remove existing messages
        const existingMessages = document.querySelectorAll('.auth-message');
        existingMessages.forEach(msg => msg.remove());
        
        // Create message element
        const messageEl = document.createElement('div');
        messageEl.className = `auth-message alert alert-${type}`;
        messageEl.textContent = message;
        
        // Insert message at top of page or in designated container
        const container = document.querySelector('.auth-messages') || document.body;
        container.insertBefore(messageEl, container.firstChild);
        
        // Auto-remove message after 5 seconds
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.remove();
            }
        }, 5000);
    }
    
    /**
     * Cleanup when page unloads
     */
    cleanup() {
        if (this.tokenRefreshInterval) {
            clearInterval(this.tokenRefreshInterval);
            this.tokenRefreshInterval = null;
        }
    }
}

// Initialize auth manager when DOM is loaded
let authManager;

document.addEventListener('DOMContentLoaded', () => {
    authManager = new AuthManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (authManager) {
        authManager.cleanup();
    }
});

// Export for use in other scripts
window.AuthManager = AuthManager;
window.authManager = authManager; 