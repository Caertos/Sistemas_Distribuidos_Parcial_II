/**
 * Admin User Edit Form - JavaScript
 * Sistema FHIR - Editar Usuario
 */

let currentUserId = null;

// =====================================================
// Token Synchronization
// =====================================================
(function() {
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
    if (cookieToken && !localStorage.getItem('authToken')) {
        const cleanToken = cookieToken.startsWith('FHIR-') ? cookieToken.substring(5) : cookieToken;
        localStorage.setItem('authToken', cleanToken);
    }
})();

// =====================================================
// Initialize
// =====================================================
document.addEventListener('DOMContentLoaded', function() {
    loadUsername();
    loadUserData();
    setupPasswordToggle();
});

// =====================================================
// Load User Data
// =====================================================
async function loadUserData() {
    // Get user ID from URL
    const pathParts = window.location.pathname.split('/');
    const userIdIndex = pathParts.indexOf('users') + 1;
    currentUserId = pathParts[userIdIndex];
    
    if (!currentUserId) {
        showErrorState('ID de usuario no válido');
        return;
    }
    
    const token = getAuthToken();
    
    if (!token) {
        window.location.href = '/login';
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${currentUserId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('Usuario no encontrado');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const user = await response.json();
        populateForm(user);
        setupForm();
        
        // Show form, hide loading
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('editFormCard').style.display = 'block';
        
    } catch (error) {
        console.error('Error loading user:', error);
        showErrorState(error.message || 'Error al cargar los datos del usuario');
    }
}

// =====================================================
// Populate Form with User Data
// =====================================================
function populateForm(user) {
    document.getElementById('user_id').value = user.id;
    document.getElementById('username').value = user.username;
    document.getElementById('email').value = user.email || '';
    document.getElementById('full_name').value = user.full_name || '';
    document.getElementById('user_type').value = user.user_type || 'patient';
    document.getElementById('is_superuser').checked = user.is_superuser || false;
}

// =====================================================
// Setup Form
// =====================================================
function setupForm() {
    const form = document.getElementById('editUserForm');
    
    if (form) {
        form.addEventListener('submit', handleSubmit);
    }
    
    // Password validation on change
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirm_password');
    
    if (password && confirmPassword) {
        confirmPassword.addEventListener('input', function() {
            if (this.value && password.value !== this.value) {
                this.setCustomValidity('Las contraseñas no coinciden');
            } else {
                this.setCustomValidity('');
            }
        });
        
        password.addEventListener('input', function() {
            if (confirmPassword.value && this.value !== confirmPassword.value) {
                confirmPassword.setCustomValidity('Las contraseñas no coinciden');
            } else {
                confirmPassword.setCustomValidity('');
            }
        });
    }
}

// =====================================================
// Setup Password Toggle
// =====================================================
function setupPasswordToggle() {
    const toggleButton = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');
    
    if (toggleButton && passwordInput) {
        toggleButton.addEventListener('click', function() {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            const icon = this.querySelector('i');
            if (icon) {
                icon.classList.toggle('bi-eye');
                icon.classList.toggle('bi-eye-slash');
            }
        });
    }
}

// =====================================================
// Handle Form Submit
// =====================================================
async function handleSubmit(event) {
    event.preventDefault();
    
    const token = getAuthToken();
    
    if (!token) {
        window.location.href = '/login';
        return;
    }
    
    // Get form data (only include fields that are being changed)
    const formData = {};
    
    const email = document.getElementById('email').value.trim();
    const fullName = document.getElementById('full_name').value.trim();
    const password = document.getElementById('password').value;
    const userType = document.getElementById('user_type').value;
    const isSuperuser = document.getElementById('is_superuser').checked;
    
    if (email) formData.email = email;
    if (fullName) formData.full_name = fullName;
    if (password) formData.password = password;
    if (userType) formData.user_type = userType;
    formData.is_superuser = isSuperuser;
    
    // Validate passwords match if password is being changed
    if (password) {
        const confirmPassword = document.getElementById('confirm_password').value;
        if (password !== confirmPassword) {
            showError('Las contraseñas no coinciden');
            return;
        }
    }
    
    // Disable submit button
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
    
    try {
        const response = await fetch(`/api/admin/users/${currentUserId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const updatedUser = await response.json();
        
        showSuccess('Usuario actualizado exitosamente');
        
        // Redirect to users list after 1 second
        setTimeout(() => {
            window.location.href = '/admin/users';
        }, 1000);
        
    } catch (error) {
        console.error('Error updating user:', error);
        showError(error.message || 'Error al actualizar el usuario');
        
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    }
}

// =====================================================
// Show Error State
// =====================================================
function showErrorState(message) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('editFormCard').style.display = 'none';
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorState').style.display = 'block';
}

// =====================================================
// Helper Functions
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

function logout() {
    localStorage.removeItem('authToken');
    document.cookie = 'authToken=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    window.location.href = '/login';
}

function showError(message) {
    const errorElement = document.createElement('div');
    errorElement.className = 'alert alert-danger alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    errorElement.style.zIndex = '9999';
    errorElement.style.maxWidth = '500px';
    errorElement.innerHTML = `
        <i class="bi bi-exclamation-triangle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(errorElement);
    
    setTimeout(() => {
        errorElement.remove();
    }, 5000);
}

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
