/**
 * Admission Dashboard - JavaScript Functionality
 * Sistema FHIR - Gestión del Dashboard de Admisiones/Enfermería
 */

// =====================================================
// Sincronización de Token (debe ejecutarse PRIMERO)
// =====================================================

// Immediately sync token from cookie to localStorage if needed
(function() {
    console.log('[DEBUG] Starting token synchronization...');
    
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
    
    console.log('[DEBUG] Checking localStorage...');
    const lsToken = localStorage.getItem('authToken');
    console.log('[DEBUG] localStorage token:', lsToken ? 'EXISTS' : 'NOT FOUND');
    
    console.log('[DEBUG] Checking cookie...');
    const cookieToken = getCookieImmediate('authToken');
    console.log('[DEBUG] Cookie token:', cookieToken ? 'EXISTS (length: ' + cookieToken.length + ')' : 'NOT FOUND');
    
    if (cookieToken && !lsToken) {
        console.log('[DEBUG] Copying token from cookie to localStorage...');
        // Remover prefijo FHIR- si existe
        const cleanToken = cookieToken.startsWith('FHIR-') ? cookieToken.substring(5) : cookieToken;
        console.log('[DEBUG] Token limpio (length: ' + cleanToken.length + ')');
        localStorage.setItem('authToken', cleanToken);
        console.log('[SUCCESS] Token synchronized from cookie to localStorage');
    } else if (cookieToken && lsToken) {
        console.log('[INFO] Token already exists in both cookie and localStorage');
    } else if (!cookieToken && !lsToken) {
        console.warn('[WARNING] No token found in cookie or localStorage!');
    }
})();

// =====================================================
// Estado Global
// =====================================================

const AdmissionState = {
    pendingAppointments: [],
    activeAdmissions: [],
    selectedAppointment: null,
    selectedAdmission: null,
    refreshInterval: null,
    statistics: {}
};

// =====================================================
// Inicialización del Dashboard
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] DOMContentLoaded event fired');
    console.log('[DEBUG] Admission Dashboard initializing...');
    
    // Verificar autenticación
    const token = getAuthToken();
    console.log('[DEBUG] Getting auth token...');
    console.log('[DEBUG] Token retrieved:', token ? 'EXISTS (length: ' + token.length + ')' : 'NOT FOUND');
    
    if (!token) {
        console.error('[ERROR] No authentication token found - redirecting to login');
        window.location.href = '/login';
        return;
    }
    
    console.log('[SUCCESS] Token found - continuing with dashboard initialization');
    
    // Inicializar componentes
    initializeDashboard();
    setupEventListeners();
    
    // Cargar datos iniciales
    loadAllData();
    
    // Auto-refresh cada 30 segundos
    AdmissionState.refreshInterval = setInterval(loadAllData, 30000);
});

// =====================================================
// Inicialización del Dashboard
// =====================================================

function initializeDashboard() {
    // Inicializar tooltips de Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Inicializar pain scale slider si existe
    const painScaleSlider = document.getElementById('nivel_dolor');
    if (painScaleSlider) {
        painScaleSlider.addEventListener('input', updatePainScaleLabel);
    }
    
    // Inicializar cálculos automáticos
    setupVitalSignsCalculations();
}

// =====================================================
// Configurar Event Listeners
// =====================================================

function setupEventListeners() {
    // Botón de refrescar
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadAllData();
            showToast('Datos actualizados', 'success');
        });
    }
    
    // Formulario de admisión
    const admissionForm = document.getElementById('admission-form');
    if (admissionForm) {
        admissionForm.addEventListener('submit', handleAdmissionSubmit);
    }
    
    // Botones de acciones rápidas en citas pendientes
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('admit-appointment-btn')) {
            const citaId = e.target.dataset.citaId;
            openAdmissionModal(citaId);
        }
        
        if (e.target.classList.contains('view-admission-btn')) {
            const admissionId = e.target.dataset.admissionId;
            viewAdmissionDetails(admissionId);
        }
        
        if (e.target.classList.contains('update-triage-btn')) {
            const admissionId = e.target.dataset.admissionId;
            openTriageUpdateModal(admissionId);
        }
    });
}

// =====================================================
// Cargar Todos los Datos
// =====================================================

async function loadAllData() {
    try {
        await Promise.all([
            loadStatistics(),
            loadPendingAppointments(),
            loadActiveAdmissions()
        ]);
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showToast('Error al cargar los datos del dashboard', 'error');
    }
}

// =====================================================
// Cargar Estadísticas
// =====================================================

async function loadStatistics() {
    try {
        const response = await apiRequest('/api/admission/statistics/dashboard', 'GET');
        
        if (response) {
            AdmissionState.statistics = response;
            updateStatisticsDisplay(response);
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
        // Mostrar valores por defecto
        updateStatisticsDisplay({
            citas_pendientes_admision: 0,
            admisiones_activas: 0,
            admisiones_urgentes: 0,
            admisiones_atendidas: 0
        });
    }
}

// =====================================================
// Actualizar Display de Estadísticas
// =====================================================

function updateStatisticsDisplay(stats) {
    animateCounter('pending-count', stats.citas_pendientes_admision || 0);
    animateCounter('active-count', stats.admisiones_activas || 0);
    animateCounter('urgent-count', stats.admisiones_urgentes || 0);
    animateCounter('completed-count', stats.admisiones_atendidas || 0);
}

// =====================================================
// Cargar Citas Pendientes
// =====================================================

async function loadPendingAppointments() {
    try {
        const appointments = await apiRequest('/api/admission/pending-appointments', 'GET');
        
        AdmissionState.pendingAppointments = appointments || [];
        renderPendingAppointments(appointments || []);
    } catch (error) {
        console.error('Error loading pending appointments:', error);
        renderPendingAppointments([]);
    }
}

// =====================================================
// Renderizar Citas Pendientes
// =====================================================

function renderPendingAppointments(appointments) {
    const container = document.getElementById('pending-appointments-list');
    
    if (!container) return;
    
    if (appointments.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-calendar-check"></i>
                <h4>No hay citas pendientes</h4>
                <p>Todas las citas han sido admitidas</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = appointments.map(apt => `
        <div class="appointment-card fade-in" data-cita-id="${apt.cita_id}">
            <div class="appointment-header">
                <div class="patient-info">
                    <h4>${apt.paciente_nombre}</h4>
                    <div class="patient-details">
                        <span><i class="bi bi-person-badge"></i> ID: ${apt.documento_id}</span>
                        <span><i class="bi bi-gender-${apt.paciente_genero === 'M' ? 'male' : 'female'}"></i> ${apt.paciente_genero === 'M' ? 'Masculino' : 'Femenino'}</span>
                        <span><i class="bi bi-calendar"></i> ${formatDate(apt.fecha_cita)}</span>
                        ${apt.prioridad ? `<span class="priority-badge priority-${apt.prioridad.toLowerCase()}">${apt.prioridad.toUpperCase()}</span>` : ''}
                    </div>
                </div>
                <div class="appointment-actions">
                    <button class="btn btn-primary btn-sm admit-appointment-btn" data-cita-id="${apt.cita_id}">
                        <i class="bi bi-plus-circle"></i> Admitir
                    </button>
                </div>
            </div>
            ${apt.motivo ? `<p class="text-muted mb-0"><strong>Motivo:</strong> ${apt.motivo}</p>` : ''}
        </div>
    `).join('');
}

// =====================================================
// Cargar Admisiones Activas
// =====================================================

async function loadActiveAdmissions() {
    try {
        const admissions = await apiRequest('/api/admission/active?limit=50', 'GET');
        
        AdmissionState.activeAdmissions = admissions || [];
        renderActiveAdmissions(admissions || []);
    } catch (error) {
        console.error('Error loading active admissions:', error);
        renderActiveAdmissions([]);
    }
}

// =====================================================
// Renderizar Admisiones Activas
// =====================================================

function renderActiveAdmissions(admissions) {
    const tbody = document.querySelector('#active-admissions-table tbody');
    
    if (!tbody) return;
    
    if (admissions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-5">
                    <div class="empty-state">
                        <i class="bi bi-inbox"></i>
                        <h4>No hay admisiones activas</h4>
                        <p>Las admisiones aparecerán aquí</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = admissions.map(adm => `
        <tr class="fade-in">
            <td><span class="admission-code">${adm.codigo_admision}</span></td>
            <td>
                <div class="patient-name">${adm.paciente_nombre || 'N/A'}</div>
                <small class="text-muted">ID: ${adm.paciente_documento_id}</small>
            </td>
            <td><span class="admission-time">${formatTime(adm.fecha_admision)}</span></td>
            <td>
                <div class="vital-signs-summary">
                    <div class="vital-indicator" title="Presión Arterial">
                        <span class="vital-indicator-label">PA</span>
                        <span class="vital-indicator-value">${adm.presion_arterial_sistolica}/${adm.presion_arterial_diastolica}</span>
                    </div>
                    <div class="vital-indicator" title="Frecuencia Cardíaca">
                        <span class="vital-indicator-label">FC</span>
                        <span class="vital-indicator-value">${adm.frecuencia_cardiaca}</span>
                    </div>
                    <div class="vital-indicator" title="Temperatura">
                        <span class="vital-indicator-label">T°</span>
                        <span class="vital-indicator-value">${adm.temperatura}</span>
                    </div>
                    <div class="vital-indicator" title="Saturación O2">
                        <span class="vital-indicator-label">SpO2</span>
                        <span class="vital-indicator-value">${adm.saturacion_oxigeno}%</span>
                    </div>
                </div>
            </td>
            <td>
                ${adm.requiere_atencion_inmediata ? 
                    '<span class="badge bg-danger"><i class="bi bi-exclamation-triangle"></i> Urgente</span>' : 
                    '<span class="badge bg-success">Normal</span>'}
            </td>
            <td>
                <span class="status-badge ${adm.estado}">${adm.estado.charAt(0).toUpperCase() + adm.estado.slice(1)}</span>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary view-admission-btn" data-admission-id="${adm.admission_id}" title="Ver detalles">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-outline-secondary update-triage-btn" data-admission-id="${adm.admission_id}" title="Actualizar triage">
                        <i class="bi bi-pencil"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// =====================================================
// Abrir Modal de Admisión
// =====================================================

function openAdmissionModal(citaId) {
    const appointment = AdmissionState.pendingAppointments.find(apt => apt.cita_id == citaId);
    
    if (!appointment) {
        showToast('Cita no encontrada', 'error');
        return;
    }
    
    AdmissionState.selectedAppointment = appointment;
    
    // Llenar información del paciente en el modal
    document.getElementById('modal-patient-name').textContent = appointment.paciente_nombre;
    document.getElementById('modal-patient-id').textContent = appointment.documento_id;
    document.getElementById('modal-appointment-date').textContent = formatDate(appointment.fecha_cita);
    
    // Establecer cita_id en el formulario
    document.getElementById('cita_id').value = citaId;
    
    // Resetear formulario
    document.getElementById('admission-form').reset();
    document.getElementById('cita_id').value = citaId;
    
    // Abrir modal
    const modal = new bootstrap.Modal(document.getElementById('admissionModal'));
    modal.show();
}

// =====================================================
// Manejar Envío de Formulario de Admisión
// =====================================================

async function handleAdmissionSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    
    // Convertir FormData a objeto
    const data = {};
    formData.forEach((value, key) => {
        // Convertir strings vacíos a null
        if (value === '') {
            data[key] = null;
        } else if (key === 'cita_id' || key.includes('presion') || key.includes('frecuencia') || 
                   key === 'saturacion_oxigeno' || key === 'nivel_dolor') {
            data[key] = parseInt(value);
        } else if (key === 'temperatura' || key === 'peso' || key === 'altura') {
            data[key] = parseFloat(value);
        } else if (key === 'requiere_atencion_inmediata') {
            data[key] = value === 'true' || value === '1';
        } else {
            data[key] = value;
        }
    });
    
    // Validar campos requeridos
    if (!validateAdmissionData(data)) {
        return;
    }
    
    // Deshabilitar botón de envío
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Admitiendo...';
    
    try {
        const response = await apiRequest('/api/admission/', 'POST', data);
        
        if (response) {
            showToast('Paciente admitido exitosamente', 'success');
            
            // Cerrar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('admissionModal'));
            modal.hide();
            
            // Recargar datos
            await loadAllData();
            
            // Resetear formulario
            form.reset();
        }
    } catch (error) {
        console.error('Error creating admission:', error);
        showToast(error.message || 'Error al crear la admisión', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// =====================================================
// Validar Datos de Admisión
// =====================================================

function validateAdmissionData(data) {
    // Validar presión arterial
    if (data.presion_arterial_diastolica >= data.presion_arterial_sistolica) {
        showToast('La presión diastólica debe ser menor que la sistólica', 'error');
        return false;
    }
    
    // Validar rangos de signos vitales
    if (data.temperatura < 35 || data.temperatura > 42) {
        showToast('Temperatura fuera de rango (35-42°C)', 'error');
        return false;
    }
    
    if (data.saturacion_oxigeno < 70 || data.saturacion_oxigeno > 100) {
        showToast('Saturación de oxígeno fuera de rango (70-100%)', 'error');
        return false;
    }
    
    return true;
}

// =====================================================
// Ver Detalles de Admisión
// =====================================================

async function viewAdmissionDetails(admissionId) {
    try {
        const admission = await apiRequest(`/api/admission/${admissionId}`, 'GET');
        
        if (!admission) {
            showToast('Admisión no encontrada', 'error');
            return;
        }
        
        AdmissionState.selectedAdmission = admission;
        
        // Llenar modal con detalles
        renderAdmissionDetails(admission);
        
        // Abrir modal
        const modal = new bootstrap.Modal(document.getElementById('admissionDetailsModal'));
        modal.show();
    } catch (error) {
        console.error('Error loading admission details:', error);
        showToast('Error al cargar los detalles', 'error');
    }
}

// =====================================================
// Renderizar Detalles de Admisión
// =====================================================

function renderAdmissionDetails(admission) {
    const container = document.getElementById('admission-details-content');
    
    if (!container) return;
    
    const imc = admission.imc ? admission.imc.toFixed(1) : 'N/A';
    const pam = admission.pam ? admission.pam.toFixed(1) : 'N/A';
    
    container.innerHTML = `
        <div class="admission-summary">
            <h5><i class="bi bi-clipboard-pulse"></i> Información General</h5>
            <div class="summary-grid">
                <div class="summary-item">
                    <span class="summary-label">Código de Admisión</span>
                    <span class="summary-value admission-code">${admission.codigo_admision}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Paciente</span>
                    <span class="summary-value">${admission.paciente_nombre || 'N/A'}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Fecha y Hora</span>
                    <span class="summary-value">${formatDateTime(admission.fecha_admision)}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Estado</span>
                    <span class="summary-value">
                        <span class="status-badge ${admission.estado}">${admission.estado.charAt(0).toUpperCase() + admission.estado.slice(1)}</span>
                    </span>
                </div>
            </div>
        </div>
        
        <div class="admission-summary mt-3">
            <h5><i class="bi bi-heart-pulse"></i> Signos Vitales</h5>
            <div class="vital-signs-list">
                <div class="vital-sign-item ${getVitalSignStatus('pa', admission.presion_arterial_sistolica, admission.presion_arterial_diastolica)}">
                    <span class="vital-sign-icon">🩺</span>
                    <span class="vital-sign-value">${admission.presion_arterial_sistolica}/${admission.presion_arterial_diastolica}</span>
                    <span class="vital-sign-label">Presión Arterial</span>
                    <span class="vital-sign-unit">mmHg</span>
                    <small class="d-block mt-1">PAM: ${pam} mmHg</small>
                </div>
                <div class="vital-sign-item ${getVitalSignStatus('fc', admission.frecuencia_cardiaca)}">
                    <span class="vital-sign-icon">💓</span>
                    <span class="vital-sign-value">${admission.frecuencia_cardiaca}</span>
                    <span class="vital-sign-label">Frecuencia Cardíaca</span>
                    <span class="vital-sign-unit">bpm</span>
                </div>
                <div class="vital-sign-item ${getVitalSignStatus('fr', admission.frecuencia_respiratoria)}">
                    <span class="vital-sign-icon">🫁</span>
                    <span class="vital-sign-value">${admission.frecuencia_respiratoria}</span>
                    <span class="vital-sign-label">Frecuencia Respiratoria</span>
                    <span class="vital-sign-unit">/min</span>
                </div>
                <div class="vital-sign-item ${getVitalSignStatus('temp', admission.temperatura)}">
                    <span class="vital-sign-icon">🌡️</span>
                    <span class="vital-sign-value">${admission.temperatura}</span>
                    <span class="vital-sign-label">Temperatura</span>
                    <span class="vital-sign-unit">°C</span>
                </div>
                <div class="vital-sign-item ${getVitalSignStatus('spo2', admission.saturacion_oxigeno)}">
                    <span class="vital-sign-icon">🫀</span>
                    <span class="vital-sign-value">${admission.saturacion_oxigeno}</span>
                    <span class="vital-sign-label">Saturación O₂</span>
                    <span class="vital-sign-unit">%</span>
                </div>
                ${admission.peso && admission.altura ? `
                <div class="vital-sign-item">
                    <span class="vital-sign-icon">⚖️</span>
                    <span class="vital-sign-value">${admission.peso}</span>
                    <span class="vital-sign-label">Peso</span>
                    <span class="vital-sign-unit">kg</span>
                    <small class="d-block mt-1">Altura: ${admission.altura} m</small>
                    <small class="d-block">IMC: ${imc}</small>
                </div>
                ` : ''}
            </div>
        </div>
        
        <div class="admission-summary mt-3">
            <h5><i class="bi bi-file-medical"></i> Evaluación Clínica</h5>
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Nivel de Conciencia:</strong> ${admission.nivel_conciencia.charAt(0).toUpperCase() + admission.nivel_conciencia.slice(1)}</p>
                    ${admission.nivel_dolor !== null ? `<p><strong>Nivel de Dolor:</strong> ${admission.nivel_dolor}/10</p>` : ''}
                    <p><strong>Requiere Atención Inmediata:</strong> 
                        ${admission.requiere_atencion_inmediata ? 
                            '<span class="badge bg-danger">Sí</span>' : 
                            '<span class="badge bg-success">No</span>'}
                    </p>
                </div>
                <div class="col-md-6">
                    ${admission.alergias ? `<p><strong>Alergias:</strong> ${admission.alergias}</p>` : ''}
                    ${admission.medicamentos_actuales ? `<p><strong>Medicamentos:</strong> ${admission.medicamentos_actuales}</p>` : ''}
                </div>
            </div>
            <p><strong>Motivo de Consulta:</strong></p>
            <p class="border p-2 rounded bg-light">${admission.motivo_consulta}</p>
            ${admission.observaciones_enfermeria ? `
                <p><strong>Observaciones de Enfermería:</strong></p>
                <p class="border p-2 rounded bg-light">${admission.observaciones_enfermeria}</p>
            ` : ''}
        </div>
    `;
}

// =====================================================
// Determinar Estado de Signo Vital
// =====================================================

function getVitalSignStatus(type, value, value2 = null) {
    switch(type) {
        case 'pa':
            if (value < 90 || value > 140 || value2 < 60 || value2 > 90) return 'warning';
            if (value < 80 || value > 160 || value2 < 50 || value2 > 100) return 'danger';
            return 'normal';
        case 'fc':
            if (value < 60 || value > 100) return 'warning';
            if (value < 50 || value > 120) return 'danger';
            return 'normal';
        case 'fr':
            if (value < 12 || value > 20) return 'warning';
            if (value < 10 || value > 25) return 'danger';
            return 'normal';
        case 'temp':
            if (value < 36 || value > 37.5) return 'warning';
            if (value < 35.5 || value > 38.5) return 'danger';
            return 'normal';
        case 'spo2':
            if (value < 95) return 'warning';
            if (value < 90) return 'danger';
            return 'normal';
        default:
            return 'normal';
    }
}

// =====================================================
// Configurar Cálculos Automáticos de Signos Vitales
// =====================================================

function setupVitalSignsCalculations() {
    // Calcular PAM automáticamente
    const sistolica = document.getElementById('presion_arterial_sistolica');
    const diastolica = document.getElementById('presion_arterial_diastolica');
    
    if (sistolica && diastolica) {
        [sistolica, diastolica].forEach(input => {
            input.addEventListener('input', calculatePAM);
        });
    }
    
    // Calcular IMC automáticamente
    const peso = document.getElementById('peso');
    const altura = document.getElementById('altura');
    
    if (peso && altura) {
        [peso, altura].forEach(input => {
            input.addEventListener('input', calculateIMC);
        });
    }
    
    // Validar signos vitales en tiempo real
    setupVitalSignsValidation();
}

// =====================================================
// Calcular Presión Arterial Media (PAM)
// =====================================================

function calculatePAM() {
    const sistolica = parseFloat(document.getElementById('presion_arterial_sistolica')?.value);
    const diastolica = parseFloat(document.getElementById('presion_arterial_diastolica')?.value);
    
    if (sistolica && diastolica) {
        const pam = (sistolica + 2 * diastolica) / 3;
        const pamDisplay = document.getElementById('pam-display');
        if (pamDisplay) {
            pamDisplay.textContent = `PAM: ${pam.toFixed(1)} mmHg`;
            pamDisplay.className = 'text-muted small';
            
            // Colorear según valor
            if (pam < 65 || pam > 110) {
                pamDisplay.classList.add('text-warning');
            }
        }
    }
}

// =====================================================
// Calcular Índice de Masa Corporal (IMC)
// =====================================================

function calculateIMC() {
    const peso = parseFloat(document.getElementById('peso')?.value);
    const altura = parseFloat(document.getElementById('altura')?.value);
    
    if (peso && altura && altura > 0) {
        const imc = peso / (altura * altura);
        const imcDisplay = document.getElementById('imc-display');
        if (imcDisplay) {
            let categoria = '';
            if (imc < 18.5) categoria = 'Bajo peso';
            else if (imc < 25) categoria = 'Normal';
            else if (imc < 30) categoria = 'Sobrepeso';
            else categoria = 'Obesidad';
            
            imcDisplay.textContent = `IMC: ${imc.toFixed(1)} (${categoria})`;
            imcDisplay.className = 'text-muted small';
        }
    }
}

// =====================================================
// Configurar Validación de Signos Vitales
// =====================================================

function setupVitalSignsValidation() {
    const vitalInputs = {
        'presion_arterial_sistolica': { min: 60, max: 250, unit: 'mmHg' },
        'presion_arterial_diastolica': { min: 40, max: 150, unit: 'mmHg' },
        'frecuencia_cardiaca': { min: 30, max: 220, unit: 'bpm' },
        'frecuencia_respiratoria': { min: 8, max: 50, unit: '/min' },
        'temperatura': { min: 35.0, max: 42.0, unit: '°C' },
        'saturacion_oxigeno': { min: 70, max: 100, unit: '%' }
    };
    
    Object.keys(vitalInputs).forEach(inputId => {
        const input = document.getElementById(inputId);
        if (input) {
            input.addEventListener('input', function() {
                validateVitalSign(this, vitalInputs[inputId]);
            });
        }
    });
}

// =====================================================
// Validar Signo Vital Individual
// =====================================================

function validateVitalSign(input, config) {
    const value = parseFloat(input.value);
    const feedback = input.parentElement.querySelector('.vital-status') || 
                     createFeedbackElement(input);
    
    if (!value || isNaN(value)) {
        feedback.textContent = '';
        feedback.className = 'vital-status';
        input.classList.remove('is-valid', 'is-invalid');
        return;
    }
    
    if (value < config.min || value > config.max) {
        feedback.textContent = `⚠️ Fuera de rango (${config.min}-${config.max} ${config.unit})`;
        feedback.className = 'vital-status danger';
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
    } else {
        feedback.textContent = `✓ Normal`;
        feedback.className = 'vital-status normal';
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    }
}

// =====================================================
// Crear Elemento de Feedback
// =====================================================

function createFeedbackElement(input) {
    const feedback = document.createElement('div');
    feedback.className = 'vital-status';
    input.parentElement.appendChild(feedback);
    return feedback;
}

// =====================================================
// Actualizar Label de Escala de Dolor
// =====================================================

function updatePainScaleLabel() {
    const slider = document.getElementById('nivel_dolor');
    const label = document.getElementById('pain-scale-value');
    
    if (slider && label) {
        const value = slider.value;
        let description = '';
        
        if (value == 0) description = 'Sin dolor';
        else if (value <= 3) description = 'Leve';
        else if (value <= 6) description = 'Moderado';
        else description = 'Severo';
        
        label.textContent = `${value}/10 - ${description}`;
    }
}

// =====================================================
// Request API Genérico
// =====================================================

async function apiRequest(url, method = 'GET', data = null) {
    const token = getAuthToken();
    
    if (!token) {
        throw new Error('No authentication token found');
    }
    
    const options = {
        method: method,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    };
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(url, options);
    
    if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/login';
            throw new Error('Unauthorized');
        }
        
        const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }
    
    return response.json();
}

// =====================================================
// Obtener Token de Autenticación
// =====================================================

function getAuthToken() {
    console.log('[DEBUG] getAuthToken() called');
    
    let token = localStorage.getItem('authToken');
    console.log('[DEBUG] localStorage.getItem("authToken"):', token ? 'EXISTS' : 'NOT FOUND');
    
    if (!token) {
        console.log('[DEBUG] Token not in localStorage, checking cookie...');
        token = getCookie('authToken');
        console.log('[DEBUG] getCookie("authToken"):', token ? 'EXISTS' : 'NOT FOUND');
    }
    
    if (token && token.startsWith('FHIR-')) {
        console.log('[DEBUG] Token has FHIR- prefix, removing it');
        token = token.substring(5);
    }
    
    console.log('[DEBUG] Final token:', token ? 'EXISTS (length: ' + token.length + ')' : 'NULL');
    return token;
}

// =====================================================
// Obtener Cookie
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
// Animación de Contadores
// =====================================================

function animateCounter(elementId, targetValue) {
    const element = document.getElementById(elementId);
    
    if (!element) return;
    
    const currentValue = parseInt(element.textContent) || 0;
    const duration = 1000;
    const steps = 50;
    const increment = (targetValue - currentValue) / steps;
    const stepDuration = duration / steps;
    
    let current = currentValue;
    let step = 0;
    
    const timer = setInterval(() => {
        step++;
        current += increment;
        
        if (step >= steps) {
            element.textContent = targetValue;
            clearInterval(timer);
        } else {
            element.textContent = Math.round(current);
        }
    }, stepDuration);
}

// =====================================================
// Mostrar Toast/Notificación
// =====================================================

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toastId = 'toast-' + Date.now();
    const iconMap = {
        success: 'check-circle',
        error: 'x-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    
    const bgMap = {
        success: 'success',
        error: 'danger',
        warning: 'warning',
        info: 'primary'
    };
    
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-white bg-${bgMap[type]} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi bi-${iconMap[type]} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// =====================================================
// Crear Contenedor de Toasts
// =====================================================

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

// =====================================================
// Formatear Fecha
// =====================================================

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// =====================================================
// Formatear Fecha y Hora
// =====================================================

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('es-ES', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// =====================================================
// Formatear Hora
// =====================================================

function formatTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 60) {
        return `Hace ${diffMins} min`;
    } else if (diffMins < 1440) {
        return `Hace ${Math.floor(diffMins / 60)} h`;
    } else {
        return date.toLocaleString('es-ES', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// =====================================================
// Limpiar al Cerrar
// =====================================================

window.addEventListener('beforeunload', function() {
    if (AdmissionState.refreshInterval) {
        clearInterval(AdmissionState.refreshInterval);
    }
});

// =====================================================
// Export para uso en otros módulos
// =====================================================

window.admissionDashboard = {
    loadAllData: loadAllData,
    showToast: showToast,
    getAuthToken: getAuthToken,
    state: AdmissionState
};
