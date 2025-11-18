/**
 * Patient Dashboard JavaScript
 * Sistema FHIR - Portal del Paciente
 */

class PatientDashboard {
    constructor() {
        this.dashboardData = null;
        this.currentSection = 'dashboard';
        this.init();
    }

    init() {
        document.addEventListener('DOMContentLoaded', () => {
            this.setupEventListeners();
            this.setupAppointmentForm();
            this.initializeDashboard();
        });
    }

    setupEventListeners() {
        // Toggle sidebar en móvil
        const sidebarToggle = document.getElementById('sidebarToggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => {
                const sidebar = document.getElementById('sidebar');
                const mainContent = document.getElementById('mainContent');
                
                sidebar.classList.toggle('show');
                if (window.innerWidth <= 768) {
                    mainContent.classList.toggle('expanded');
                }
            });
        }

        // Cerrar sidebar al hacer click fuera en móvil
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                const sidebar = document.getElementById('sidebar');
                const toggle = document.getElementById('sidebarToggle');
                
                if (sidebar && toggle && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
                    sidebar.classList.remove('show');
                    document.getElementById('mainContent').classList.add('expanded');
                }
            }
        });

        // Configurar navegación del sidebar
        document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.getAttribute('data-section');
                if (section) {
                    this.showSection(section);
                }
            });
        });

        // Configurar navegación del dropdown
        document.querySelectorAll('.dropdown-menu .dropdown-item').forEach(link => {
            link.addEventListener('click', (e) => {
                const section = e.target.getAttribute('data-section');
                if (section) {
                    e.preventDefault();
                    this.showSection(section);
                }
            });
        });
    }

    getAuthToken() {
        let token = null;
        
        // Estrategia 1: localStorage primero
        try {
            token = localStorage.getItem('authToken');
            if (token && this.isTokenValid(token)) {
                return token;
            } else if (token) {
                localStorage.removeItem('authToken');
                token = null;
            }
        } catch (e) {
            // localStorage no disponible
        }
        
        // Estrategia 2: cookies como fallback
        if (!token) {
            const cookies = document.cookie.split(';');
            const authCookie = cookies.find(cookie => cookie.trim().startsWith('authToken='));
            
            if (authCookie) {
                // Extraer el valor completo del token
                token = authCookie.substring(authCookie.indexOf('=') + 1);
                
                // Limpiar comillas
                if (token) {
                    token = token.trim();
                    if ((token.startsWith('"') && token.endsWith('"')) || 
                        (token.startsWith("'") && token.endsWith("'"))) {
                        token = token.slice(1, -1);
                    }
                }
                
                // Validar y guardar en localStorage
                if (token && this.isTokenValid(token)) {
                    try {
                        localStorage.setItem('authToken', token);
                    } catch (e) {
                        // Error silencioso
                    }
                } else {
                    token = null;
                }
            }
        }
        
                // Asegurar prefijo FHIR- sin duplicar
        if (token && !token.startsWith('FHIR-')) {
            token = `FHIR-${token}`;
            try {
                localStorage.setItem('auth_token', token);
            } catch (e) {
                // Error silencioso
            }
        }
        
        return token;
    }

    isTokenValid(token) {
        if (!token || !token.startsWith('FHIR-')) {
            return false;
        }
        
        try {
            const base64Token = token.substring(5);
            const tokenData = JSON.parse(atob(base64Token));
            const now = Date.now() / 1000;
            const expires = tokenData.expires;
            
            return expires > now;
        } catch (e) {
            return false;
        }
    }

    async initializeDashboard() {
        const token = this.getAuthToken();
        
        if (!token) {
            this.showError('No se encontró token de autenticación. Redirigiendo al login...');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
            return;
        }

        await this.loadDashboard();
    }

    async loadDashboard() {
        const token = this.getAuthToken();
        
        if (!token) {
            window.location.href = '/login';
            return;
        }
        
        try {
            this.showLoading();

            const response = await fetch('/api/patient/dashboard', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                if (response.status === 401) {
                    console.warn('Token expirado o inválido');
                    this.handleAuthError();
                    return;
                } else if (response.status === 404) {
                    throw new Error('Servicio temporalmente no disponible. Por favor intenta más tarde.');
                } else {
                    const errorText = await response.text();
                    console.error('Error response:', errorText);
                    throw new Error(`Error ${response.status}: ${response.statusText}`);
                }
            }

            this.dashboardData = await response.json();
            
            if (this.dashboardData && this.dashboardData.success) {
                this.populateAllSections();
                this.showContent();
            } else {
                throw new Error(this.dashboardData?.detail || 'Error desconocido al cargar datos');
            }

        } catch (error) {
            console.error('Error cargando dashboard:', error);
            this.showError(error.message);
        }
    }

    handleAuthError() {
        this.showError('Sesión expirada. Redirigiendo al login...');
        localStorage.removeItem('authToken');
        sessionStorage.removeItem('authToken');
        // Limpiar cookie
        document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
    }

    showLoading() {
        this.toggleElement('loading-state', true);
        this.toggleElement('error-state', false);
        this.toggleElement('dashboard-content', false);
    }

    showError(message) {
        this.toggleElement('loading-state', false);
        this.toggleElement('error-state', true);
        this.toggleElement('dashboard-content', false);
        
        const errorMessage = document.getElementById('error-message');
        if (errorMessage) {
            errorMessage.textContent = message;
        }
    }

    showContent() {
        this.toggleElement('loading-state', false);
        this.toggleElement('error-state', false);
        this.toggleElement('dashboard-content', true);
    }

    toggleElement(elementId, show) {
        const element = document.getElementById(elementId);
        if (element) {
            if (show) {
                element.style.display = 'block';
                element.classList.remove('d-none');
            } else {
                element.style.display = 'none';
                element.classList.add('d-none');
            }
        }
    }

    populateAllSections() {
        if (!this.dashboardData) return;

        // Actualizar nombre de usuario
        const patientName = this.dashboardData.patient_info?.full_name || 'Usuario';
        this.updateText('user-name', patientName);
        this.updateText('welcome-name', patientName);

        // Poblar secciones
        this.populateHealthMetrics();
        this.populateProfileSection();
        this.populateAppointmentsSection();
        this.populateMedicationsSection();
        this.populateMedicalHistorySection();
        this.populateAllergiesSection();
        this.populateResultsSection();
    }

    updateText(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
        }
    }

    populateHealthMetrics() {
        const metrics = this.dashboardData.health_metrics || {};
        const container = document.getElementById('health-metrics');
        
        if (!container) return;
        
        container.innerHTML = `
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="metric-card">
                    <div class="metric-value">${metrics.next_appointment_days !== null ? metrics.next_appointment_days : 'N/A'}</div>
                    <div class="metric-label">Días próxima cita</div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="metric-card success">
                    <div class="metric-value">${metrics.active_medications || 0}</div>
                    <div class="metric-label">Medicamentos activos</div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="metric-card info">
                    <div class="metric-value">${metrics.health_score || 0}%</div>
                    <div class="metric-label">Puntuación salud</div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="metric-card warning">
                    <div class="metric-value">${metrics.total_appointments || 0}</div>
                    <div class="metric-label">Citas este año</div>
                </div>
            </div>
        `;
    }

    populateProfileSection() {
        const patient = this.dashboardData.patient_info || {};
        const metrics = this.dashboardData.health_metrics || {};
        
        const profileInfo = document.getElementById('profile-info');
        if (profileInfo) {
            profileInfo.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label fw-bold">Nombre Completo</label>
                            <p class="form-control-plaintext">${patient.full_name || 'No especificado'}</p>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">Email</label>
                            <p class="form-control-plaintext">${patient.email || 'No especificado'}</p>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">Teléfono</label>
                            <p class="form-control-plaintext">${patient.phone || 'No especificado'}</p>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label fw-bold">Fecha de Nacimiento</label>
                            <p class="form-control-plaintext">${this.formatDate(patient.birth_date) || 'No especificada'}</p>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">Género</label>
                            <p class="form-control-plaintext">${patient.gender || 'No especificado'}</p>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">Ciudad</label>
                            <p class="form-control-plaintext">${patient.city || 'No especificada'}</p>
                        </div>
                    </div>
                </div>
            `;
        }

        const profileStats = document.getElementById('profile-stats');
        if (profileStats) {
            profileStats.innerHTML = `
                <div class="text-center">
                    <div class="mb-3">
                        <h3 class="text-primary">${metrics.health_score || 0}%</h3>
                        <small class="text-muted">Puntuación de Salud</small>
                    </div>
                    <div class="mb-3">
                        <h4 class="text-success">${metrics.active_medications || 0}</h4>
                        <small class="text-muted">Medicamentos Activos</small>
                    </div>
                    <div class="mb-3">
                        <h4 class="text-info">${metrics.total_appointments || 0}</h4>
                        <small class="text-muted">Citas este Año</small>
                    </div>
                </div>
            `;
        }
    }

    populateAppointmentsSection() {
        const appointments = this.dashboardData.upcoming_appointments || [];
        
        // Citas próximas para el dashboard
        this.populateUpcomingAppointments(appointments);
        this.populateAllAppointments(appointments);
        this.populateAppointmentsSummary(appointments);
    }

    populateUpcomingAppointments(appointments) {
        const container = document.getElementById('upcoming-appointments');
        if (!container) return;

        if (appointments.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    No tienes citas programadas próximamente.
                </div>
            `;
        } else {
            let html = '';
            appointments.slice(0, 3).forEach(appointment => {
                html += `
                    <div class="appointment-item">
                        <div class="appointment-date">${this.formatDateTime(appointment.datetime)}</div>
                        <div class="appointment-doctor">${appointment.doctor_name}</div>
                        <div class="appointment-specialty">${appointment.specialty}</div>
                        <div class="mt-2">
                            <span class="badge bg-${appointment.status === 'confirmada' ? 'success' : 'warning'}">
                                ${appointment.status}
                            </span>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        }
    }

    populateAllAppointments(appointments) {
        const container = document.getElementById('all-appointments');
        if (!container) return;

        if (appointments.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    No tienes citas programadas próximamente.
                </div>
            `;
        } else {
            let html = '<div class="row">';
            appointments.forEach(appointment => {
                html += `
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">${appointment.reason || 'Consulta médica'}</h6>
                                <p class="card-text">
                                    <strong>Fecha:</strong> ${this.formatDateTime(appointment.datetime)}<br>
                                    <strong>Doctor:</strong> ${appointment.doctor_name}<br>
                                    <strong>Especialidad:</strong> ${appointment.specialty}<br>
                                    <strong>Ubicación:</strong> ${appointment.location || 'Por definir'}
                                </p>
                                <span class="badge bg-${appointment.status === 'confirmada' ? 'success' : 'warning'}">
                                    ${appointment.status}
                                </span>
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        }
    }

    populateAppointmentsSummary(appointments) {
        const container = document.getElementById('appointments-summary');
        if (!container) return;

        container.innerHTML = `
            <div class="text-center">
                <h3 class="text-primary">${appointments.length}</h3>
                <p class="text-muted mb-4">Citas Programadas</p>
                
                <div class="d-grid">
                    <button class="btn btn-primary mb-2" onclick="window.patientDashboard.showSection('agendar-cita')">
                        <i class="bi bi-plus-circle me-2"></i>
                        Agendar Nueva Cita
                    </button>
                    <small class="text-muted">Selecciona fecha, hora y especialista</small>
                </div>
            </div>
        `;
    }

    populateMedicationsSection() {
        const medications = this.dashboardData.medication_reminders || [];
        
        this.populateRecentMedications(medications);
        this.populateAllMedications(medications);
    }

    populateRecentMedications(medications) {
        const container = document.getElementById('recent-medications');
        if (!container) return;

        if (medications.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    No tienes medicamentos activos registrados.
                </div>
            `;
        } else {
            let html = '';
            medications.slice(0, 3).forEach(medication => {
                html += `
                    <div class="medication-item">
                        <div class="medication-name">${medication.medication_name}</div>
                        <div class="medication-details">
                            <strong>Dosis:</strong> ${medication.dosage}<br>
                            <strong>Frecuencia:</strong> ${medication.frequency}
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        }
    }

    populateAllMedications(medications) {
        const container = document.getElementById('all-medications');
        if (!container) return;

        if (medications.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    No tienes medicamentos activos registrados.
                </div>
            `;
        } else {
            let html = '';
            medications.forEach(medication => {
                html += `
                    <div class="medication-item">
                        <div class="row">
                            <div class="col-md-8">
                                <div class="medication-name">${medication.medication_name}</div>
                                <div class="medication-details">
                                    <strong>Dosis:</strong> ${medication.dosage}<br>
                                    <strong>Frecuencia:</strong> ${medication.frequency}<br>
                                    <strong>Vía:</strong> ${medication.route}<br>
                                    <strong>Prescriptor:</strong> ${medication.prescriptor}
                                </div>
                            </div>
                            <div class="col-md-4 text-end">
                                <span class="badge bg-success">Activo</span>
                                <div class="mt-2">
                                    <small class="text-muted">
                                        ${medication.start_date ? `Desde: ${this.formatDate(medication.start_date)}` : ''}
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        }
    }

    populateMedicalHistorySection() {
        const history = this.dashboardData.recent_medical_history || [];
        const container = document.getElementById('medical-history-timeline');
        
        if (!container) return;

        if (history.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    No hay registros médicos recientes disponibles.
                </div>
            `;
        } else {
            let html = '';
            history.forEach(record => {
                html += `
                    <div class="timeline-item">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6 class="mb-0">${record.title}</h6>
                            <small class="text-muted">${this.formatDate(record.date)}</small>
                        </div>
                        <p class="mb-2">${record.description}</p>
                        <div class="d-flex align-items-center text-muted">
                            <i class="bi bi-person-badge me-2"></i>
                            <span>Dr. ${record.doctor_name} - ${record.specialty}</span>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        }
    }

    populateResultsSection() {
        const results = this.dashboardData.recent_lab_results || [];
        const container = document.getElementById('all-results');
        
        if (!container) return;

        if (results.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    No hay resultados de laboratorio recientes disponibles.
                </div>
            `;
        } else {
            let html = '<div class="row">';
            results.forEach(result => {
                html += `
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">${result.test_name}</h6>
                                <p class="card-text">
                                    <strong>Fecha:</strong> ${this.formatDate(result.date)}<br>
                                    <strong>Resultado:</strong> ${result.value} ${result.unit}<br>
                                    <strong>Rango Normal:</strong> ${result.normal_range}
                                </p>
                                <span class="badge bg-${result.status === 'normal' ? 'success' : result.status === 'borderline' ? 'warning' : 'danger'}">
                                    ${result.status}
                                </span>
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        }
    }

    populateAllergiesSection() {
        const allergies = this.dashboardData.important_allergies || [];
        const container = document.getElementById('all-allergies');
        
        if (!container) return;

        if (allergies.length === 0) {
            container.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle me-2"></i>
                    No tienes alergias registradas en tu expediente médico.
                </div>
            `;
        } else {
            let html = '<div class="row">';
            allergies.forEach(allergy => {
                const severityClass = allergy.severity === 'severa' ? 'danger' : 'warning';
                html += `
                    <div class="col-md-6 mb-3">
                        <div class="alert alert-${severityClass}">
                            <div class="d-flex align-items-start">
                                <i class="bi bi-exclamation-triangle fs-4 me-3 mt-1"></i>
                                <div>
                                    <h6 class="alert-heading">${allergy.allergen}</h6>
                                    <p class="mb-1"><strong>Severidad:</strong> ${allergy.severity}</p>
                                    <p class="mb-0"><strong>Reacción:</strong> ${allergy.reaction}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;

            // Mostrar alertas importantes en el dashboard
            const alertsContainer = document.getElementById('important-alerts');
            const alertsContent = document.getElementById('alerts-content');
            if (alertsContainer && alertsContent) {
                alertsContainer.style.display = 'block';
                alertsContent.innerHTML = `
                    <div class="alert alert-warning">
                        <strong>Atención:</strong> Tienes ${allergies.length} alergia(s) registrada(s). 
                        Asegúrate de informar a tu médico antes de cualquier tratamiento.
                    </div>
                `;
            }
        }
    }

    showSection(sectionName) {
        // Ocultar todas las secciones
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.add('d-none');
        });
        
        // Remover clase active de todos los enlaces del sidebar
        document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Mostrar la sección seleccionada
        const targetSection = document.getElementById(`section-${sectionName}`);
        if (targetSection) {
            targetSection.classList.remove('d-none');
        }
        
        // Activar el enlace correspondiente
        const activeLink = document.querySelector(`[data-section="${sectionName}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
        
        this.currentSection = sectionName;
    }

    async downloadHealthRecord() {
        const token = this.getAuthToken();
        
        if (!token) {
            this.handleAuthError();
            return;
        }
        
        try {
            const response = await fetch('/api/patient/health-record/download', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    this.handleAuthError();
                    return;
                }
                throw new Error('Error al generar el PDF');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `historia_clinica_${this.dashboardData.patient_info?.username || 'paciente'}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            this.showAlert('Historia clínica descargada exitosamente', 'success');

        } catch (error) {
            console.error('Error descargando PDF:', error);
            this.showAlert('Error al descargar la historia clínica. Por favor intenta de nuevo.', 'danger');
        }
    }

    logout() {
        // Limpiar localStorage
        try {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('authToken'); // Por compatibilidad
            sessionStorage.removeItem('auth_token');
            sessionStorage.removeItem('authToken'); // Por compatibilidad
        } catch (e) {
            // Error silencioso
        }
        
        // Limpiar cookies
        document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        
        // Redirigir a login
        window.location.href = '/login';
    }

    setupAppointmentForm() {
        // Establecer fecha mínima (mañana)
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        const minDate = tomorrow.toISOString().split('T')[0];
        
        const dateInput = document.getElementById('appointmentDate');
        if (dateInput) {
            dateInput.setAttribute('min', minDate);
            
            // Establecer fecha máxima (3 meses adelante)
            const maxDate = new Date();
            maxDate.setMonth(maxDate.getMonth() + 3);
            dateInput.setAttribute('max', maxDate.toISOString().split('T')[0]);
        }
        
        // Cargar médicos disponibles
        this.loadAvailableDoctors();
        
        // Configurar evento de envío del formulario
        const form = document.getElementById('appointmentForm');
        if (form) {
            form.addEventListener('submit', (e) => this.handleAppointmentSubmit(e));
        }
    }

    async loadAvailableDoctors() {
        const token = this.getAuthToken();
        const select = document.getElementById('doctorSelect');
        
        if (!select || !token) return;
        
        try {
            select.innerHTML = '<option value="">Cargando especialistas...</option>';
            
            const response = await fetch('/api/patient/available-doctors', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    this.handleAuthError();
                    return;
                }
                throw new Error('Error al cargar médicos');
            }

            const data = await response.json();
            
            if (data.success && data.doctors && data.doctors.length > 0) {
                select.innerHTML = '<option value="">Seleccionar especialista</option>';
                
                // Agrupar por especialidad
                const groupedDoctors = {};
                data.doctors.forEach(doctor => {
                    const specialty = doctor.specialty || 'Medicina General';
                    if (!groupedDoctors[specialty]) {
                        groupedDoctors[specialty] = [];
                    }
                    groupedDoctors[specialty].push(doctor);
                });
                
                // Crear opciones agrupadas
                Object.keys(groupedDoctors).sort().forEach(specialty => {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = specialty;
                    
                    groupedDoctors[specialty].forEach(doctor => {
                        const option = document.createElement('option');
                        option.value = doctor.id;
                        option.textContent = `Dr. ${doctor.name}`;
                        option.setAttribute('data-specialty', doctor.specialty);
                        option.setAttribute('data-phone', doctor.phone || '');
                        optgroup.appendChild(option);
                    });
                    
                    select.appendChild(optgroup);
                });
            } else {
                select.innerHTML = '<option value="">No hay médicos disponibles</option>';
            }
            
        } catch (error) {
            console.error('Error cargando médicos:', error);
            select.innerHTML = '<option value="">Error al cargar médicos</option>';
        }
    }

    async handleAppointmentSubmit(event) {
        event.preventDefault();
        
        const token = this.getAuthToken();
        if (!token) {
            this.handleAuthError();
            return;
        }
        
        const submitButton = event.target.querySelector('button[type="submit"]');
        const originalText = submitButton?.innerHTML || 'Agendar Cita';
        
        // Obtener datos del formulario
        const formData = {
            doctor_id: document.getElementById('doctorSelect')?.value,
            appointment_date: document.getElementById('appointmentDate')?.value,
            appointment_time: document.getElementById('appointmentTime')?.value,
            reason: document.getElementById('appointmentReason')?.value,
            notes: document.getElementById('appointmentNotes')?.value
        };
        
        // Validaciones
        if (!formData.doctor_id || !formData.appointment_date || !formData.appointment_time || !formData.reason) {
            this.showAppointmentAlert('Por favor completa todos los campos requeridos.', 'warning');
            return;
        }
        
        try {
            // Mostrar estado de carga
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Agendando...';
            }
            
            const response = await fetch('/api/patient/schedule-appointment', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();
            
            if (response.ok && result.success) {
                // Éxito
                this.showAppointmentAlert(
                    `¡Cita agendada exitosamente! Te contactaremos pronto para confirmar tu cita del ${this.formatDate(formData.appointment_date)} a las ${this.formatTime(formData.appointment_time)}.`, 
                    'success'
                );
                
                // Limpiar formulario
                event.target.reset();
                
                // Recargar datos del dashboard para mostrar la nueva cita
                setTimeout(() => {
                    this.loadDashboard();
                    this.showSection('citas');
                }, 2000);
                
            } else {
                if (response.status === 401) {
                    this.handleAuthError();
                    return;
                }
                throw new Error(result.detail || 'Error al agendar la cita');
            }
            
        } catch (error) {
            console.error('Error agendando cita:', error);
            this.showAppointmentAlert(
                error.message || 'Ocurrió un error al agendar la cita. Por favor intenta de nuevo.', 
                'danger'
            );
        } finally {
            // Restaurar botón
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        }
    }

    showAppointmentAlert(message, type) {
        this.showAlert(message, type, {
            position: 'fixed',
            top: '100px',
            right: '20px',
            zIndex: '9999',
            minWidth: '300px'
        });
    }

    showAlert(message, type, customStyles = {}) {
        const existingAlert = document.querySelector('.custom-alert');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show custom-alert`;
        
        // Aplicar estilos personalizados
        Object.assign(alertDiv.style, customStyles);
        
        alertDiv.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'x-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    // Funciones auxiliares
    formatDate(dateString) {
        if (!dateString) return 'No especificada';
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    formatDateTime(dateString) {
        if (!dateString) return 'No especificada';
        const date = new Date(dateString);
        return date.toLocaleString('es-ES', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatTime(timeString) {
        if (!timeString) return 'No especificada';
        const [hour, minute] = timeString.split(':');
        const hourNum = parseInt(hour);
        const period = hourNum >= 12 ? 'PM' : 'AM';
        const hour12 = hourNum > 12 ? hourNum - 12 : hourNum === 0 ? 12 : hourNum;
        return `${hour12}:${minute} ${period}`;
    }
}

// Crear instancia global
const patientDashboard = new PatientDashboard();

// Funciones globales para compatibilidad con el HTML
window.showSection = (section) => patientDashboard.showSection(section);
window.downloadHealthRecord = () => patientDashboard.downloadHealthRecord();
window.logout = () => patientDashboard.logout();
window.loadDashboard = () => patientDashboard.loadDashboard();