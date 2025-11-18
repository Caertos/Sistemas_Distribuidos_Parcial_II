/* =====================================================
   Sistema FHIR Distribuido - JavaScript Principal
   ===================================================== */

// Estado global de la aplicación 
window.FHIRApp = {
    currentUser: null,
    theme: 'light',
    notifications: [],
    isLoading: false
};

// =====================================================
// Inicialización de la aplicación
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    console.log('🚀 Inicializando Sistema FHIR...');
    
    // Cargar configuraciones
    loadUserPreferences();
    setupThemeToggle();
    setupNotifications();
    setupLoadingOverlay();
    setupFormValidation();
    setupTableEnhancements();
    setupTooltips();
    setupConfirmDialogs();
    
    console.log('✅ Sistema FHIR inicializado correctamente');
}

// =====================================================
// Gestión de temas
// =====================================================

function loadUserPreferences() {
    const savedTheme = localStorage.getItem('fhir-theme') || 'light';
    setTheme(savedTheme);
    
    // Cargar otras preferencias
    const sidebarCollapsed = localStorage.getItem('fhir-sidebar-collapsed') === 'true';
    if (sidebarCollapsed) {
        document.body.classList.add('sidebar-collapsed');
    }
}

function setupThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    
    if (themeToggle && themeIcon) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
        });
    }
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    localStorage.setItem('fhir-theme', theme);
    
    const themeIcon = document.getElementById('theme-icon');
    if (themeIcon) {
        themeIcon.className = theme === 'dark' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
    }
    
    window.FHIRApp.theme = theme;
}

// =====================================================
// Sistema de notificaciones
// =====================================================

function setupNotifications() {
    // Crear contenedor de toasts si no existe
    if (!document.querySelector('.toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1080';
        document.body.appendChild(toastContainer);
    }
    
    // Configurar notificaciones en tiempo real si hay WebSocket
    if (window.CURRENT_USER && typeof io !== 'undefined') {
        setupRealtimeNotifications();
    }
}

function showNotification(message, type = 'info', duration = 5000) {
    const toastContainer = document.querySelector('.toast-container');
    const toastId = 'toast-' + Date.now();
    
    const iconMap = {
        'success': 'bi-check-circle-fill',
        'error': 'bi-exclamation-triangle-fill',
        'warning': 'bi-exclamation-triangle-fill',
        'info': 'bi-info-circle-fill'
    };
    
    const colorMap = {
        'success': 'text-success',
        'error': 'text-danger', 
        'warning': 'text-warning',
        'info': 'text-info'
    };
    
    const toastHTML = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="bi ${iconMap[type]} ${colorMap[type]} me-2"></i>
                <strong class="me-auto">Sistema FHIR</strong>
                <small class="text-muted">ahora</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        delay: duration
    });
    
    toast.show();
    
    // Limpiar después de que se oculte
    toastElement.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

function updateNotificationCount() {
    const notificationCount = document.getElementById('notification-count');
    if (notificationCount && window.FHIRApp.notifications) {
        const unreadCount = window.FHIRApp.notifications.filter(n => !n.read).length;
        notificationCount.textContent = unreadCount;
        notificationCount.style.display = unreadCount > 0 ? 'inline' : 'none';
    }
}

// =====================================================
// Loading overlay
// =====================================================

function setupLoadingOverlay() {
    // Interceptar todas las peticiones fetch para mostrar loading
    const originalFetch = window.fetch;
    
    window.fetch = function(...args) {
        showLoading();
        
        return originalFetch.apply(this, args)
            .then(response => {
                hideLoading();
                return response;
            })
            .catch(error => {
                hideLoading();
                throw error;
            });
    };
}

function showLoading(message = 'Cargando...') {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.querySelector('p').textContent = message;
        overlay.classList.remove('d-none');
        window.FHIRApp.isLoading = true;
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('d-none');
        window.FHIRApp.isLoading = false;
    }
}

// =====================================================
// Validación de formularios
// =====================================================

function setupFormValidation() {
    // Validación de Bootstrap personalizada
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        });
    });
    
    // Validación en tiempo real para campos específicos
    document.querySelectorAll('input[type="email"]').forEach(input => {
        input.addEventListener('blur', validateEmail);
    });
    
    document.querySelectorAll('input[data-fhir-type]').forEach(input => {
        input.addEventListener('blur', validateFHIRField);
    });
}

function validateEmail(event) {
    const input = event.target;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (input.value && !emailRegex.test(input.value)) {
        input.setCustomValidity('Por favor ingrese un email válido');
        input.classList.add('is-invalid');
    } else {
        input.setCustomValidity('');
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    }
}

function validateFHIRField(event) {
    const input = event.target;
    const fhirType = input.dataset.fhirType;
    
    let isValid = true;
    let message = '';
    
    switch (fhirType) {
        case 'identifier':
            // Validar formato de identificador FHIR
            if (input.value && !/^[A-Za-z0-9\-\.]{1,64}$/.test(input.value)) {
                isValid = false;
                message = 'Identificador debe ser alfanumérico con máximo 64 caracteres';
            }
            break;
            
        case 'phone':
            // Validar formato de teléfono
            if (input.value && !/^\+?[\d\s\-\(\)]{7,15}$/.test(input.value)) {
                isValid = false;
                message = 'Formato de teléfono inválido';
            }
            break;
            
        case 'date':
            // Validar formato de fecha FHIR (YYYY-MM-DD)
            if (input.value && !/^\d{4}-\d{2}-\d{2}$/.test(input.value)) {
                isValid = false;
                message = 'Formato de fecha debe ser YYYY-MM-DD';
            }
            break;
    }
    
    if (!isValid) {
        input.setCustomValidity(message);
        input.classList.add('is-invalid');
    } else {
        input.setCustomValidity('');
        input.classList.remove('is-invalid');
        if (input.value) {
            input.classList.add('is-valid');
        }
    }
}

// =====================================================
// Mejoras de tablas
// =====================================================

function setupTableEnhancements() {
    // Hacer tablas responsivas
    document.querySelectorAll('.table').forEach(table => {
        if (!table.closest('.table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
    
    // Configurar ordenamiento de tablas
    document.querySelectorAll('.table-sortable th[data-sort]').forEach(header => {
        header.style.cursor = 'pointer';
        header.innerHTML += ' <i class="bi bi-arrow-down-up ms-1"></i>';
        
        header.addEventListener('click', function() {
            sortTable(this);
        });
    });
    
    // Configurar filtros de tabla
    document.querySelectorAll('.table-filter').forEach(filter => {
        filter.addEventListener('input', function() {
            filterTable(this);
        });
    });
}

function sortTable(header) {
    const table = header.closest('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const columnIndex = Array.from(header.parentNode.children).indexOf(header);
    const sortKey = header.dataset.sort;
    const currentOrder = header.dataset.order || 'asc';
    const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
    
    // Limpiar iconos de otras columnas
    table.querySelectorAll('th[data-sort]').forEach(th => {
        th.querySelector('i').className = 'bi bi-arrow-down-up ms-1';
        th.removeAttribute('data-order');
    });
    
    // Actualizar icono de la columna actual
    const icon = header.querySelector('i');
    icon.className = newOrder === 'asc' ? 'bi bi-arrow-up ms-1' : 'bi bi-arrow-down ms-1';
    header.dataset.order = newOrder;
    
    // Ordenar filas
    rows.sort((a, b) => {
        const aValue = a.children[columnIndex].textContent.trim();
        const bValue = b.children[columnIndex].textContent.trim();
        
        let comparison = 0;
        
        if (sortKey === 'number') {
            comparison = parseFloat(aValue) - parseFloat(bValue);
        } else if (sortKey === 'date') {
            comparison = new Date(aValue) - new Date(bValue);
        } else {
            comparison = aValue.localeCompare(bValue);
        }
        
        return newOrder === 'asc' ? comparison : -comparison;
    });
    
    // Reordenar filas en la tabla
    rows.forEach(row => tbody.appendChild(row));
}

function filterTable(filterInput) {
    const table = filterInput.dataset.target;
    const tbody = document.querySelector(`${table} tbody`);
    const rows = tbody.querySelectorAll('tr');
    const filterValue = filterInput.value.toLowerCase();
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(filterValue) ? '' : 'none';
    });
}

// =====================================================
// Tooltips y confirmaciones
// =====================================================

function setupTooltips() {
    // Inicializar todos los tooltips de Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Inicializar todos los popovers de Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

function setupConfirmDialogs() {
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function(event) {
            event.preventDefault();
            
            const message = this.dataset.confirm;
            const action = this.href || this.dataset.action;
            
            showConfirmDialog(message, () => {
                if (this.href) {
                    window.location.href = action;
                } else if (this.dataset.action) {
                    // Ejecutar acción personalizada
                    eval(action);
                }
            });
        });
    });
}

function showConfirmDialog(message, onConfirm, onCancel = null) {
    const modalId = 'confirm-modal-' + Date.now();
    const modalHTML = `
        <div class="modal fade" id="${modalId}" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-question-circle text-warning me-2"></i>
                            Confirmar Acción
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            Cancelar
                        </button>
                        <button type="button" class="btn btn-danger" id="confirm-btn">
                            Confirmar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    const confirmBtn = document.getElementById('confirm-btn');
    
    confirmBtn.addEventListener('click', function() {
        onConfirm();
        modal.hide();
    });
    
    modal.show();
    
    // Limpiar modal después de ocultarlo
    document.getElementById(modalId).addEventListener('hidden.bs.modal', function() {
        this.remove();
        if (onCancel) onCancel();
    });
}

// =====================================================
// Utilidades FHIR
// =====================================================

function formatFHIRDate(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function formatFHIRDateTime(dateTimeString) {
    if (!dateTimeString) return '-';
    
    const date = new Date(dateTimeString);
    return date.toLocaleString('es-ES', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function generateFHIRId(prefix = 'ID') {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substr(2, 5);
    return `${prefix}-${timestamp}-${random}`.toUpperCase();
}

// =====================================================
// API Helpers
// =====================================================

async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    };
    
    // Agregar token CSRF si existe
    if (window.CSRF_TOKEN) {
        defaultOptions.headers['X-CSRFToken'] = window.CSRF_TOKEN;
    }
    
    // Combinar opciones
    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, finalOptions);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        } else {
            return await response.text();
        }
        
    } catch (error) {
        console.error('API Request Error:', error);
        showNotification(`Error en la solicitud: ${error.message}`, 'error');
        throw error;
    }
}

// =====================================================
// Exportar funciones globales
// =====================================================

window.FHIRApp.showNotification = showNotification;
window.FHIRApp.showLoading = showLoading;
window.FHIRApp.hideLoading = hideLoading;
window.FHIRApp.showConfirmDialog = showConfirmDialog;
window.FHIRApp.apiRequest = apiRequest;
window.FHIRApp.formatFHIRDate = formatFHIRDate;
window.FHIRApp.formatFHIRDateTime = formatFHIRDateTime;
window.FHIRApp.generateFHIRId = generateFHIRId;

console.log('📱 JavaScript del Sistema FHIR cargado correctamente');