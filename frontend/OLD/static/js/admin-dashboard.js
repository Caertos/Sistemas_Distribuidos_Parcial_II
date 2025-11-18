/**
 * Admin Dashboard - JavaScript Functionality
 * Sistema FHIR - Gestión del Dashboard de Administrador
 */

// =====================================================
// Sincronización de Token (debe ejecutarse PRIMERO)
// =====================================================

// Immediately sync token from cookie to localStorage if needed
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
        // Remover prefijo FHIR- si existe
        const cleanToken = cookieToken.startsWith('FHIR-') ? cookieToken.substring(5) : cookieToken;
        console.log('[ADMIN DEBUG] Token limpio (primeros 50 chars):', cleanToken.substring(0, 50));
        localStorage.setItem('authToken', cleanToken);
        console.log('[ADMIN SUCCESS] Token synchronized from cookie to localStorage');
    }
})();

// =====================================================
// Inicialización del Dashboard
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[ADMIN DEBUG] DOMContentLoaded - Initializing dashboard...');
    
    // Inicializar componentes
    initializeDashboard();
    loadDashboardStats();
    setLastLoginTime();
    
    // Auto-refresh cada 30 segundos
    setInterval(loadDashboardStats, 30000);
});

// =====================================================
// Cargar Estadísticas del Dashboard
// =====================================================

async function loadDashboardStats() {
    const token = getAuthToken();
    
    if (!token) {
        console.error('No authentication token found');
        window.location.href = '/login';
        return;
    }
    
    try {
        const response = await fetch('/api/admin/dashboard-stats', {
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
        
        const data = await response.json();
        
        if (data.success && data.stats) {
            updateDashboardStats(data.stats);
        } else {
            console.error('Invalid response format:', data);
            showError('Error al cargar las estadísticas');
        }
        
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        showError('Error de conexión al cargar estadísticas');
        // Mostrar valores por defecto en caso de error
        updateDashboardStats({
            active_users: 0,
            total_patients: 0,
            active_practitioners: 0,
            medical_records: 0
        });
    }
}

// =====================================================
// Actualizar Estadísticas en el DOM
// =====================================================

function updateDashboardStats(stats) {
    // Actualizar usuarios activos
    animateCounter('active-users', stats.active_users || 0);
    
    // Actualizar pacientes
    animateCounter('total-patients', stats.total_patients || 0);
    
    // Actualizar médicos
    animateCounter('active-practitioners', stats.active_practitioners || 0);
    
    // Actualizar registros médicos
    animateCounter('medical-records', stats.medical_records || 0);
}

// =====================================================
// Animación de Contadores
// =====================================================

function animateCounter(elementId, targetValue) {
    const element = document.getElementById(elementId);
    
    if (!element) {
        console.warn(`Element with id '${elementId}' not found`);
        return;
    }
    
    const currentValue = parseInt(element.textContent) || 0;
    const duration = 1000; // 1 segundo
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
// Obtener Token de Autenticación
// =====================================================

function getAuthToken() {
    // Intentar obtener de localStorage primero
    let token = localStorage.getItem('authToken');
    
    // Si no está en localStorage, intentar obtener de cookie
    if (!token) {
        token = getCookie('authToken');
    }
    
    // Si el token tiene prefijo "FHIR-", quitarlo
    if (token && token.startsWith('FHIR-')) {
        token = token.substring(5);
    }
    
    return token;
}

// =====================================================
// Obtener Cookie por Nombre
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
// Establecer Hora del Último Acceso
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
// Inicializar Dashboard
// =====================================================

function initializeDashboard() {
    console.log('Admin Dashboard initialized');
    
    // Verificar autenticación
    const token = getAuthToken();
    if (!token) {
        console.warn('No authentication token found, redirecting to login...');
        window.location.href = '/login';
        return;
    }
    
    // Agregar listeners a los botones de acciones rápidas
    setupQuickActions();
}

// =====================================================
// Configurar Acciones Rápidas
// =====================================================

function setupQuickActions() {
    // Los enlaces ya están configurados en el HTML
    // Aquí se pueden agregar handlers adicionales si es necesario
    
    const quickActionLinks = document.querySelectorAll('.admin-dashboard a[href^="/admin/"]');
    
    quickActionLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Si la ruta no existe, mostrar mensaje
            const href = this.getAttribute('href');
            if (href.includes('/new') || href.includes('/backup') || href.includes('/logs') || href.includes('/settings')) {
                // Estas rutas aún no están implementadas
                console.log(`Navigating to: ${href}`);
            }
        });
    });
}

// =====================================================
// Mostrar Mensajes de Error
// =====================================================

function showError(message) {
    // Crear o actualizar elemento de error
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
    
    // Auto-ocultar después de 5 segundos
    setTimeout(() => {
        if (errorElement) {
            errorElement.classList.remove('show');
        }
    }, 5000);
}

// =====================================================
// Mostrar Mensajes de Éxito
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
    
    // Auto-eliminar después de 5 segundos
    setTimeout(() => {
        successElement.remove();
    }, 5000);
}

// =====================================================
// Actualizar Estado del Sistema (si se implementa)
// =====================================================

async function updateSystemStatus() {
    // Placeholder para futuras actualizaciones de estado del sistema
    const statusElements = {
        database: document.querySelector('.admin-dashboard .badge:contains("Base de Datos")'),
        backend: document.querySelector('.admin-dashboard .badge:contains("API Backend")'),
        web: document.querySelector('.admin-dashboard .badge:contains("Servicios Web")'),
        monitoring: document.querySelector('.admin-dashboard .badge:contains("Monitoreo")')
    };
    
    // Esta función se puede expandir para obtener estado real de los servicios
}

// =====================================================
// Utilidades para Manejo de Datos
// =====================================================

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toLocaleString('es-ES');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return date.toLocaleString('es-ES', options);
}

// =====================================================
// Export para uso en otros módulos (si es necesario)
// =====================================================

window.adminDashboard = {
    loadStats: loadDashboardStats,
    showError: showError,
    showSuccess: showSuccess,
    getAuthToken: getAuthToken
};
