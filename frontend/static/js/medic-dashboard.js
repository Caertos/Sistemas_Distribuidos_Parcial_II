/*
 * Medic Dashboard JavaScript
 * Sistema FHIR - Dashboard Médico
 * FastAPI + Jinja2 Integration
 */

class MedicDashboard {
    constructor() {
        this.authToken = null;
        this.doctorData = null;
        this.refreshInterval = null;
        this.init();
    }

    init() {
        // Inicializando Dashboard Médico...
        
        // Inicializar cuando el DOM esté listo
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeDashboard());
        } else {
            this.initializeDashboard();
        }
    }

    // Helper para resolver nombre completo del paciente a partir de distintas variantes
    getPatientName(obj) {
        if (!obj) return 'Paciente';
        const candidates = [
            // campos en español
            (obj.nombre && obj.apellido) ? `${obj.nombre} ${obj.apellido}` : null,
            obj.full_name,
            obj.patient_name,
            obj.paciente_nombre,
            obj.name,
            obj.username,
            obj.display_name,
            // campos sueltos
            obj.nombre,
            obj.apellido && obj.apellido ? obj.apellido : null,
            obj.paciente_id,
            obj.patient_id,
            obj.id
        ];

        for (const c of candidates) {
            if (c && typeof c === 'string' && c.trim()) return c.trim();
        }
        return 'Paciente';
    }

    initializeDashboard() {
        this.loadAuthToken();
        this.setupCurrentDate();
        this.loadDashboardData();
        this.setupAutoRefresh();
        this.setupEventListeners();
        
        // Dashboard Médico inicializado correctamente
    }

    // =====================================
    // AUTENTICACIÓN Y TOKEN
    // =====================================
    
    loadAuthToken() {
        // Leer posibles keys usadas por distintos scripts: 'authToken' y 'auth_token'
        this.authToken = localStorage.getItem('authToken') || localStorage.getItem('auth_token') || this.getCookie('authToken') || this.getCookie('auth_token');
        
        if (!this.authToken) {
            console.error('No hay token de autenticación disponible');
            this.redirectToLogin();
            return false;
        }
        
        try {
            let token = this.authToken;
            // Si es un wrapper FHIR-<base64json>
            if (token.startsWith('FHIR-')) {
                token = token.substring(5);
                const tokenData = JSON.parse(atob(token));
                this.doctorData = tokenData;
                return true;
            }

            // Si es un JWT (header.payload.signature), decodificamos la parte payload
            if (token.split && token.split('.').length === 3) {
                const parts = token.split('.');
                const payload = parts[1];
                // base64url -> base64
                const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
                // pad string length
                const pad = base64.length % 4;
                const padded = base64 + (pad ? '='.repeat(4 - pad) : '');
                const jsonPayload = decodeURIComponent(atob(padded).split('').map(function(c) {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                }).join(''));
                const tokenData = JSON.parse(jsonPayload);
                if (tokenData.exp && tokenData.exp < Math.floor(Date.now() / 1000)) {
                    console.error('Token JWT expirado');
                    this.redirectToLogin();
                    return false;
                }
                this.doctorData = tokenData;
                return true;
            }

            // Fallback: intentar decodificar como base64 JSON puro
            const tokenData = JSON.parse(atob(token));
            this.doctorData = tokenData;
            return true;
        } catch (error) {
            console.error('Error al procesar token:', error);
            this.redirectToLogin();
            return false;
        }
    }

    getCookie(name) {
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

    redirectToLogin() {
        window.location.href = '/login';
    }

    // =====================================
    // CONFIGURACIÓN INICIAL
    // =====================================
    
    setupCurrentDate() {
        const currentDateElement = document.getElementById('current-date');
        if (currentDateElement) {
            const now = new Date();
            currentDateElement.textContent = now.toLocaleDateString('es-ES', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    }

    setupAutoRefresh() {
        // Refrescar datos cada 2 minutos
        this.refreshInterval = setInterval(() => {
            this.loadDashboardStats();
            this.loadPendingQueue();
        }, 120000);
    }

    setupEventListeners() {
        // Cleanup al cerrar la página
        window.addEventListener('beforeunload', () => {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
        });
    }

    // =====================================
    // CARGA DE DATOS
    // =====================================
    
    async loadDashboardData() {
        await Promise.all([
            this.loadDashboardStats(),
            this.loadPendingQueue(),
            this.loadTodaysSchedule(),
            this.loadRecentActivity()
        ]);
    }

    async loadDashboardStats() {
        // No existe un endpoint /medic/api/dashboard-stats en el backend actual.
        // Derivamos métricas simples usando endpoints disponibles.
        try {
            const [pendingResp, apptsResp] = await Promise.all([
                // debug route que devuelve citas pendientes (sin auth en dev)
                this.apiCall('/api/debug/admissions/pending'),
                this.apiCall('/api/practitioner/appointments?admitted=true&limit=200')
            ]);

            const pendingCount = Array.isArray(pendingResp) ? pendingResp.length : (pendingResp.count || 0);
            const apptsCount = (apptsResp && apptsResp.count) ? apptsResp.count : (Array.isArray(apptsResp.items) ? apptsResp.items.length : 0);

            this.updateStatsCards({
                pending_patients: pendingCount,
                todays_appointments: apptsCount,
                upcoming_appointments: apptsCount,
                completed_consultations: 0,
                pending_prescriptions: 0
            });
        } catch (error) {
            console.error('Error cargando estadísticas derivadas:', error);
            this.showStatsError();
        }
    }

    async loadPendingQueue() {
        try {
            // Usamos la ruta debug que devuelve citas pendientes si no existe endpoint específico
            const response = await this.apiCall('/api/debug/admissions/pending');

            // El debug endpoint devuelve una lista de filas
            if (Array.isArray(response)) {
                // Mapear a estructura esperada por la UI
                const patients = response.map(r => ({
                    id: r.paciente_id || r.paciente_id || r.id || r.cita_id,
                    name: this.getPatientName(r),
                    priority: 'normal',
                    arrival_time: r.fecha_hora || r.time || ''
                }));
                this.updatePendingQueue(patients);
                return;
            }

            // Fallback: si response tiene estructura {items: [...]}
            if (response && Array.isArray(response.items)) {
                this.updatePendingQueue(response.items || []);
                return;
            }

            this.showQueueError();
        } catch (error) {
            console.error('Error cargando cola de pacientes:', error);
            this.showQueueError();
        }
    }

    async loadTodaysSchedule() {
        try {
            // Usar el endpoint disponible en backend
            const response = await this.apiCall('/api/practitioner/appointments?admitted=true&limit=50');

            if (response) {
                // Puede devolver {count, items} o lista
                const items = response.items || response || [];
                // Normalizar items si vienen en formato DB
                const appointments = (Array.isArray(items) ? items : []).map(a => ({
                    datetime: a.fecha_hora || a.time || a.datetime || a.fecha || null,
                    time: (a.fecha_hora || a.time || a.datetime || '').toString().split('T').pop() || '',
                    patient: { name: this.getPatientName(a) },
                    reason: a.motivo || a.reason || '',
                    status: a.estado || a.status || 'programada'
                }));

                this.updateTodaysSchedule(appointments || []);
                return;
            }

            this.showScheduleError();
        } catch (error) {
            console.error('Error cargando agenda:', error);
            this.showScheduleError();
        }
    }

    async loadRecentActivity() {
        // No hay un endpoint claro para actividad reciente; por ahora mostramos vacío.
        this.updateRecentActivity([]);
    }

    // =====================================
    // ACTUALIZACIÓN DE UI
    // =====================================
    
    updateStatsCards(stats) {
        const elements = {
            'pending-patients-count': stats.pending_patients || 0,
            'todays-appointments-count': stats.todays_appointments || 0,
            'upcoming-appointments-count': stats.upcoming_appointments || 0,
            'completed-consultations-count': stats.completed_consultations || 0,
            'pending-prescriptions-count': stats.pending_prescriptions || 0
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
                element.classList.add('updated');
                setTimeout(() => element.classList.remove('updated'), 500);
            }
        });
    }

    updatePendingQueue(patients) {
        const container = document.getElementById('pending-queue');
        if (!container) return;

        if (patients.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-check-circle text-success"></i>
                    <p>No hay pacientes pendientes</p>
                </div>
            `;
            return;
        }

        let html = '<div class="patient-list">';
        patients.forEach((patient, index) => {
            html += `
                <div class="patient-item" data-patient-id="${patient.id}">
                    <div class="patient-info">
                        <div class="queue-position">${index + 1}</div>
                        <div class="patient-details">
                            <h6 class="patient-name">${patient.name}</h6>
                            <p class="patient-meta">
                                <span class="badge bg-${this.getPriorityColor(patient.priority)}">
                                    ${patient.priority}
                                </span>
                                <small class="text-muted ms-2">
                                    Llegada: ${patient.arrival_time}
                                </small>
                            </p>
                        </div>
                    </div>
                    <div class="patient-actions">
                        <button class="btn btn-sm btn-primary" onclick="medicDashboard.startConsultation('${patient.id}')">
                            <i class="bi bi-play-circle"></i> Atender
                        </button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    }

    updateTodaysSchedule(appointments) {
        const container = document.getElementById('todays-schedule');
        if (!container) return;

        if (appointments.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-calendar-x text-muted"></i>
                    <p>No hay citas programadas próximamente</p>
                </div>
            `;
            return;
        }

        let html = '<div class="schedule-list">';
        appointments.forEach(appointment => {
            // Obtener fecha y hora del appointment
            const appointmentDate = new Date(appointment.datetime);
            const today = new Date();
            const isToday = appointmentDate.toDateString() === today.toDateString();
            const isTomorrow = appointmentDate.toDateString() === new Date(today.getTime() + 24*60*60*1000).toDateString();
            
            let dateLabel = appointmentDate.toLocaleDateString('es-ES', { 
                day: 'numeric', 
                month: 'short' 
            });
            
            if (isToday) {
                dateLabel = 'Hoy';
            } else if (isTomorrow) {
                dateLabel = 'Mañana';
            }
            
            const timeClass = this.getAppointmentTimeClass(appointment.time);
            html += `
                <div class="schedule-item ${timeClass}">
                    <div class="schedule-time">
                        <strong>${appointment.time}</strong>
                        <small>${dateLabel}</small>
                    </div>
                    <div class="schedule-details">
                        <h6>${appointment.patient.name}</h6>
                        <p class="mb-1">${appointment.reason}</p>
                        <span class="badge bg-${this.getStatusColor(appointment.status)}">
                            ${appointment.status}
                        </span>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    }

    updateRecentActivity(activities) {
        const container = document.getElementById('recent-activity');
        if (!container) return;

        if (activities.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-clock-history text-muted"></i>
                    <p>No hay actividad reciente</p>
                </div>
            `;
            return;
        }

        let html = '<div class="activity-timeline">';
        activities.forEach(activity => {
            html += `
                <div class="activity-item">
                    <div class="activity-icon">
                        <i class="bi ${this.getActivityIcon(activity.type)}"></i>
                    </div>
                    <div class="activity-content">
                        <p class="activity-description">${activity.description}</p>
                        <small class="activity-time text-muted">${activity.time}</small>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    }

    // =====================================
    // FUNCIONES DE CONSULTA
    // =====================================
    
    async startConsultation(patientId) {
        try {
            // Cargar datos del paciente
            const patientResponse = await this.apiCall(`/api/practitioner/patients/${patientId}`);
            // Si la respuesta es un objeto paciente (o fallback), prellenar
            if (patientResponse) {
                const sel = document.getElementById('patientSelect');
                if (sel) sel.value = patientId;
                const modal = new bootstrap.Modal(document.getElementById('newConsultationModal'));
                modal.show();
            }
        } catch (error) {
            console.error('Error iniciando consulta:', error);
            this.showAlert('Error al iniciar consulta', 'error');
        }
    }

    async saveConsultation() {
        const form = document.getElementById('newConsultationForm');
        const formData = new FormData(form);
        
        const consultationData = {
            patient_id: document.getElementById('patientSelect').value,
            consultation_type: document.getElementById('consultationType').value,
            reason: document.getElementById('consultationReason').value,
            clinical_findings: document.getElementById('clinicalFindings').value,
            diagnosis: document.getElementById('diagnosis').value,
            treatment_plan: document.getElementById('treatmentPlan').value
        };

        try {
            const response = await this.apiCall('/api/practitioner/encounters', {
                method: 'POST',
                body: JSON.stringify(consultationData)
            });

            if (response.success) {
                this.showAlert('Consulta guardada exitosamente', 'success');
                bootstrap.Modal.getInstance(document.getElementById('newConsultationModal')).hide();
                form.reset();
                this.loadDashboardData(); // Refrescar datos
            }
        } catch (error) {
            console.error('Error guardando consulta:', error);
            this.showAlert('Error al guardar la consulta', 'error');
        }
    }

    // =====================================
    // FUNCIONES DE PRESCRIPCIÓN
    // =====================================
    
    async savePrescription() {
        const prescriptionData = {
            patient_id: document.getElementById('prescriptionPatient').value,
            medication_name: document.getElementById('medicationName').value,
            dosage: document.getElementById('dosage').value,
            frequency: document.getElementById('frequency').value,
            duration: document.getElementById('duration').value,
            instructions: document.getElementById('prescriptionInstructions').value
        };

        try {
            const response = await this.apiCall('/api/practitioner/medications', {
                method: 'POST',
                body: JSON.stringify(prescriptionData)
            });

            if (response.success) {
                this.showAlert('Prescripción guardada exitosamente', 'success');
                bootstrap.Modal.getInstance(document.getElementById('prescriptionModal')).hide();
                document.getElementById('prescriptionForm').reset();
                this.loadDashboardData();
            }
        } catch (error) {
            console.error('Error guardando prescripción:', error);
            this.showAlert('Error al guardar la prescripción', 'error');
        }
    }

    // =====================================
    // FUNCIONES AUXILIARES
    // =====================================
    
    async apiCall(endpoint, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.authToken}`, // this.authToken ya incluye 'FHIR-'
                'Content-Type': 'application/json'
            }
        };

        const response = await fetch(endpoint, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        return await response.json();
    }

    getPriorityColor(priority) {
        const colors = {
            'urgente': 'danger',
            'alta': 'warning',
            'normal': 'primary',
            'baja': 'secondary'
        };
        return colors[priority] || 'secondary';
    }

    getStatusColor(status) {
        const colors = {
            'programada': 'primary',
            'en_curso': 'warning',
            'completada': 'success',
            'cancelada': 'danger'
        };
        return colors[status] || 'secondary';
    }

    getAppointmentTimeClass(time) {
        const now = new Date();
        const appointmentTime = new Date(`${now.toDateString()} ${time}`);
        const diffMinutes = (appointmentTime - now) / (1000 * 60);
        
        if (diffMinutes < 0) return 'past-appointment';
        if (diffMinutes < 30) return 'current-appointment';
        return 'future-appointment';
    }

    getActivityIcon(type) {
        const icons = {
            'consultation': 'bi-person-check',
            'prescription': 'bi-prescription2',
            'appointment': 'bi-calendar-event',
            'patient': 'bi-person-plus'
        };
        return icons[type] || 'bi-circle';
    }

    showAlert(message, type = 'info') {
        // Crear toast notification
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : type}" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        // Agregar al contenedor de toasts (crear si no existe)
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // Limpiar después de mostrar
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    showStatsError() {
        ['pending-patients-count', 'todays-appointments-count', 'completed-consultations-count', 'pending-prescriptions-count']
            .forEach(id => {
                const element = document.getElementById(id);
                if (element) element.textContent = 'Error';
            });
    }

    showQueueError() {
        const container = document.getElementById('pending-queue');
        if (container) {
            container.innerHTML = `
                <div class="error-state">
                    <i class="bi bi-exclamation-triangle text-warning"></i>
                    <p>Error al cargar la cola de pacientes</p>
                    <button class="btn btn-sm btn-outline-primary" onclick="medicDashboard.loadPendingQueue()">
                        Reintentar
                    </button>
                </div>
            `;
        }
    }

    showScheduleError() {
        const container = document.getElementById('todays-schedule');
        if (container) {
            container.innerHTML = `
                <div class="error-state">
                    <i class="bi bi-exclamation-triangle text-warning"></i>
                    <p>Error al cargar la agenda</p>
                </div>
            `;
        }
    }

    showActivityError() {
        const container = document.getElementById('recent-activity');
        if (container) {
            container.innerHTML = `
                <div class="error-state">
                    <i class="bi bi-exclamation-triangle text-warning"></i>
                    <p>Error al cargar actividad reciente</p>
                </div>
            `;
        }
    }
}

// =====================================
// FUNCIONES GLOBALES
// =====================================

// Instancia global del dashboard
let medicDashboard;

// Inicializar cuando se carga el script
if (typeof window !== 'undefined') {
    medicDashboard = new MedicDashboard();
}

// Funciones globales para eventos onclick
function openNewConsultation() {
    const modal = new bootstrap.Modal(document.getElementById('newConsultationModal'));
    modal.show();
}

function openPrescriptionForm() {
    const modal = new bootstrap.Modal(document.getElementById('prescriptionModal'));
    modal.show();
}

function viewMedicalRecords() {
    window.location.href = '/medic/medical-records';
}

function viewPendingResults() {
    window.location.href = '/medic/results';
}

function viewFullSchedule() {
    window.location.href = '/medic/appointments';
}

function refreshDashboard() {
    if (medicDashboard) {
        medicDashboard.loadDashboardData();
    }
}

function refreshPendingQueue() {
    if (medicDashboard) {
        medicDashboard.loadPendingQueue();
    }
}
