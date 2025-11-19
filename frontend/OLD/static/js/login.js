// Login Page JavaScript Functions

document.addEventListener('DOMContentLoaded', function() {
    // Auto-focus en el campo de usuario
    const usernameField = document.getElementById('username');
    if (usernameField) {
        usernameField.focus();
    }
    
    // Configurar eventos de los usuarios demo
    setupDemoUsers();
    
    // Configurar el formulario de login
    setupLoginForm();
});

// Función para llenar credenciales automáticamente
function fillCredentials(username, password) {
    const usernameField = document.getElementById('username');
    const passwordField = document.getElementById('password');
    
    if (usernameField) usernameField.value = username;
    if (passwordField) passwordField.value = password;
    
    // Agregar efecto visual
    const submitButton = document.querySelector('.btn-login');
    if (submitButton) {
        submitButton.focus();
    }
}

// Configurar eventos de usuarios demo
function setupDemoUsers() {
    const userCards = document.querySelectorAll('.user-card');
    
    userCards.forEach(card => {
        card.addEventListener('click', function() {
            const username = this.dataset.username;
            const password = this.dataset.password;
            
            if (username && password) {
                fillCredentials(username, password);
                
                // Efecto visual de selección
                this.style.background = 'rgba(255, 255, 255, 0.3)';
                setTimeout(() => {
                    this.style.background = '';
                }, 300);
            }
        });
        
        // Agregar efecto hover mejorado
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

// Configurar el formulario de login
function setupLoginForm() {
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleLogin();
        });
    }
}

// Manejar el proceso de login
async function handleLogin() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
        showError('Por favor, ingrese usuario y contraseña');
        return;
    }
    
    // Mostrar estado de carga
    showLoading();
    
    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                username: username,
                password: password
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.success) {
                showSuccess('Login exitoso. Redirigiendo...');
                
                // Redirigir después de un breve delay
                setTimeout(() => {
                    window.location.href = data.redirect_url || '/dashboard';
                }, 1500);
            } else {
                throw new Error(data.message || 'Error de autenticación');
            }
        } else {
            // Si la respuesta no es JSON, intentar redirigir directamente
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            
            throw new Error('Credenciales inválidas');
        }
        
    } catch (error) {
        console.error('Error en login:', error);
        showError(error.message || 'Error al iniciar sesión');
    }
}

// Mostrar estado de carga
function showLoading() {
    hideAllAlerts();
    
    const loadingAlert = document.getElementById('loading-alert');
    if (loadingAlert) {
        loadingAlert.style.display = 'block';
    }
    
    // Deshabilitar botón de submit
    const submitButton = document.querySelector('.btn-login');
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Iniciando sesión...';
    }
}

// Mostrar error
function showError(message) {
    hideAllAlerts();
    
    const errorAlert = document.getElementById('error-alert');
    const errorMessage = document.getElementById('error-message');
    
    if (errorAlert && errorMessage) {
        errorMessage.textContent = message;
        errorAlert.style.display = 'block';
    }
    
    // Restaurar botón de submit
    resetSubmitButton();
}

// Mostrar éxito
function showSuccess(message) {
    hideAllAlerts();
    
    const successAlert = document.getElementById('success-alert');
    const successMessage = document.getElementById('success-message');
    
    if (successAlert) {
        successAlert.style.display = 'block';
        if (successMessage) {
            successMessage.textContent = message;
        }
    }
}

// Ocultar todas las alertas
function hideAllAlerts() {
    const alerts = ['loading-alert', 'error-alert', 'success-alert'];
    
    alerts.forEach(alertId => {
        const alert = document.getElementById(alertId);
        if (alert) {
            alert.style.display = 'none';
        }
    });
}

// Restaurar botón de submit
function resetSubmitButton() {
    const submitButton = document.querySelector('.btn-login');
    if (submitButton) {
        submitButton.disabled = false;
        submitButton.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>Iniciar Sesión';
    }
}

// Función para cambiar contraseña automáticamente basada en usuario
function autoFillPassword() {
    const usernameField = document.getElementById('username');
    const passwordField = document.getElementById('password');
    
    if (usernameField && passwordField) {
        usernameField.addEventListener('change', function() {
            const username = this.value.toLowerCase();
            
            // Mapeo de usuarios demo
            const demoCredentials = {
                'admin': 'secret',
                'medico': 'secret',
                'paciente': 'secret',
                'auditor': 'secret'
            };
            
            if (demoCredentials[username]) {
                passwordField.value = demoCredentials[username];
            } else {
                passwordField.value = '';
            }
        });
    }
}

// Inicializar auto-fill cuando se carga la página
document.addEventListener('DOMContentLoaded', autoFillPassword);