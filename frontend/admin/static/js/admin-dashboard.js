/**
 * Admin Dashboard - JavaScript Functionality
 * Sistema FHIR - Gestión del Dashboard de Administrador
 */

// =====================================================
// Token Synchronization (must run FIRST)
// =====================================================
(function() {
    console.log('[ADMIN DEBUG] Starting token synchronization...');
    
    function getCookieImmediate(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    const cookieToken = getCookieImmediate('authToken');
    console.log('[ADMIN DEBUG] Cookie token:', cookieToken ? 'EXISTS' : 'NOT FOUND');
    
    if (cookieToken && !localStorage.getItem('authToken')) {
        const cleanToken = cookieToken.startsWith('FHIR-') ? cookieToken.substring(5) : cookieToken;
        localStorage.setItem('authToken', cleanToken);
        console.log('[ADMIN SUCCESS] Token synchronized from cookie to localStorage');
    }
})();

// =====================================================
// Dashboard Initialization
// =====================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('[ADMIN DEBUG] DOMContentLoaded - Initializing dashboard...');
    
    initializeDashboard();
    loadDashboardStats();
    setLastLoginTime();
    loadUsername();
    
    // Auto-refresh every 30 seconds
    setInterval(loadDashboardStats, 30000);
});

// =====================================================
// Load Dashboard Statistics
// =====================================================
async function loadDashboardStats() {
    const token = getAuthToken();
    
    if (!token) {
        console.error('No authentication token found');
        window.location.href = '/login';
        return;
    }
    
    try {
        // Load users list to calculate stats
        const response = await fetch('/api/admin/users?limit=1000', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                console.error('Unauthorized access');
                window.location.href = '/login';
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const users = await response.json();
        
        // Calculate statistics
        const stats = {
            active_users: users.length,
            total_patients: users.filter(u => u.user_type === 'patient').length,
            active_practitioners: users.filter(u => u.user_type === 'practitioner').length,
            total_admins: users.filter(u => u.user_type === 'admin' || u.is_superuser).length
        };
        
        updateDashboardStats(stats);
        
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        showError('Error al cargar las estadísticas');
        // Show default values on error
        updateDashboardStats({
            active_users: 0,
            total_patients: 0,
            active_practitioners: 0,
            total_admins: 0
        });
    }
}

// =====================================================
// Update Statistics in DOM
// =====================================================
function updateDashboardStats(stats) {
    animateCounter('active-users', stats.active_users || 0);
    animateCounter('total-patients', stats.total_patients || 0);
    animateCounter('active-practitioners', stats.active_practitioners || 0);
    animateCounter('total-admins', stats.total_admins || 0);
}

// =====================================================
// Counter Animation
// =====================================================
function animateCounter(elementId, targetValue) {
    const element = document.getElementById(elementId);
    
    if (!element) {
        console.warn(`Element with id '${elementId}' not found`);
        return;
    }
    
    const currentValue = parseInt(element.textContent) || 0;
    const duration = 1000; // 1 second
    const steps = 50;
    const increment = (targetValue - currentValue) / steps;
    const stepDuration = duration / steps;
    
    let current = currentValue;
    let step = 0;
    
    const timer = setInterval(() => {
        step++;
        current += increment;
        
        if (step >= steps) {
            element.textContent = targetValue.toLocaleString('es-ES');
            clearInterval(timer);
        } else {
            element.textContent = Math.round(current).toLocaleString('es-ES');
        }
    }, stepDuration);
}

// =====================================================
// Get Authentication Token
// =====================================================
function getAuthToken() {
    let token = localStorage.getItem('authToken');
    
    if (!token) {
        token = getCookie('authToken');
    }
    
    if (token && token.startsWith('FHIR-')) {
        token = token.substring(5);
    }
    
    return token;
}

// =====================================================
// Get Cookie by Name
// =====================================================
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// =====================================================
// Set Last Login Time
// =====================================================
function setLastLoginTime() {
    const lastLoginElement = document.getElementById('last-login');
    
    if (lastLoginElement) {
        const now = new Date();
        const options = {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        lastLoginElement.textContent = now.toLocaleString('es-ES', options);
    }
}

// =====================================================
// Load Username
// =====================================================
function loadUsername() {
    const token = getAuthToken();
    if (token) {
        try {
            const parts = token.split('.');
            if (parts.length === 3) {
                const payload = parts[1];
                const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
                const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                }).join(''));
                const tokenData = JSON.parse(jsonPayload);
                
                if (tokenData.username) {
                    document.getElementById('navbar-username').textContent = tokenData.username;
                }
            }
        } catch (e) {
            console.log('Could not parse user token:', e);
        }
    }
}

// =====================================================
// Initialize Dashboard
// =====================================================
function initializeDashboard() {
    console.log('Admin Dashboard initialized');
    
    const token = getAuthToken();
    if (!token) {
        console.warn('No authentication token found, redirecting to login...');
        window.location.href = '/login';
        return;
    }
}

// =====================================================
// Logout Function
// =====================================================
function logout() {
    localStorage.removeItem('authToken');
    document.cookie = 'authToken=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    window.location.href = '/login';
}

// =====================================================
// Show Error Messages
// =====================================================
function showError(message) {
    let errorElement = document.getElementById('dashboard-error');
    
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.id = 'dashboard-error';
        errorElement.className = 'alert alert-warning alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
        errorElement.style.zIndex = '9999';
        errorElement.style.maxWidth = '500px';
        errorElement.innerHTML = `
            <i class="bi bi-exclamation-triangle me-2"></i>
            <span id="error-message">${message}</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(errorElement);
    } else {
        document.getElementById('error-message').textContent = message;
        errorElement.classList.add('show');
    }
    
    setTimeout(() => {
        if (errorElement) {
            errorElement.classList.remove('show');
        }
    }, 5000);
}

// =====================================================
// Show Success Messages
// =====================================================
function showSuccess(message) {
    const successElement = document.createElement('div');
    successElement.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    successElement.style.zIndex = '9999';
    successElement.style.maxWidth = '500px';
    successElement.innerHTML = `
        <i class="bi bi-check-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(successElement);
    
    setTimeout(() => {
        successElement.remove();
    }, 5000);
}

// =====================================================
// Export for use in other modules
// =====================================================
window.adminDashboard = {
    loadStats: loadDashboardStats,
    showError: showError,
    showSuccess: showSuccess,
    getAuthToken: getAuthToken
};
