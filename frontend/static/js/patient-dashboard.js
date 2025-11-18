/**
 * patient-dashboard.js - Adaptado para consumir backend existente
 * Usa `window.auth` (auth.js) para obtener/validar token
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

        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                const sidebar = document.getElementById('sidebar');
                const toggle = document.getElementById('sidebarToggle');
                if (sidebar && toggle && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
                    sidebar.classList.remove('show');
                    const main = document.getElementById('mainContent');
                    if (main) main.classList.add('expanded');
                }
            }
        });

        document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.getAttribute('data-section');
                if (section) this.showSection(section);
            });
        });

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

    getAuthTokenRaw() {
        // Obtener token crudo (JWT) a partir de las fuentes soportadas
        const t = window.auth.getStoredToken();
        if (!t) return null;
        // Si es wrapper FHIR-, extraer token interno
        const raw = window.auth.unwrapFHIR(t) || t;
        return raw;
    }

    async initializeDashboard() {
        const token = this.getAuthTokenRaw();
        if (!token) {
            this.showError('No se encontró token de autenticación. Redirigiendo al login...');
            setTimeout(() => window.location.href = '/login', 1500);
            return;
        }
        await this.loadDashboard();
    }

    async loadDashboard() {
        const token = this.getAuthTokenRaw();
        if (!token) return window.location.href = '/login';
        try {
            this.showLoading();
            const response = await fetch('/api/patient/me/summary', {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            if (!response.ok) {
                if (response.status === 401) { this.handleAuthError(); return; }
                const text = await response.text();
                throw new Error(`Error ${response.status}: ${response.statusText} ${text}`);
            }
            this.dashboardData = await response.json();
            if (this.dashboardData) {
                this.populateAllSections();
                this.showContent();
            } else {
                throw new Error('Respuesta inválida del servidor');
            }
        } catch (err) {
            console.error('Error cargando dashboard:', err);
            this.showError(err.message || 'Error al cargar datos');
        }
    }

    handleAuthError() {
        this.showError('Sesión expirada. Redirigiendo al login...');
        try { localStorage.removeItem('authToken'); localStorage.removeItem('auth_token'); } catch(e){}
        document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        setTimeout(() => window.location.href = '/login', 1200);
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
        const el = document.getElementById('error-message'); if (el) el.textContent = message;
    }

    showContent() {
        this.toggleElement('loading-state', false);
        this.toggleElement('error-state', false);
        this.toggleElement('dashboard-content', true);
    }

    toggleElement(id, show) {
        const el = document.getElementById(id);
        if (!el) return;
        if (show) { el.style.display = 'block'; el.classList.remove('d-none'); }
        else { el.style.display = 'none'; el.classList.add('d-none'); }
    }

    populateAllSections() {
        if (!this.dashboardData) return;
        const patientName = this.dashboardData.patient?.full_name || this.dashboardData.patient?.username || 'Usuario';
        this.updateText('user-name', patientName);
        this.updateText('welcome-name', patientName);
        this.populateHealthMetrics();
        this.populateProfileSection();
        this.populateAppointmentsSection();
        this.populateMedicationsSection();
        this.populateMedicalHistorySection();
        this.populateAllergiesSection();
        this.populateResultsSection();
    }

    updateText(id, text) { const el = document.getElementById(id); if (el) el.textContent = text; }

    populateHealthMetrics() {
        const metrics = this.dashboardData.health_metrics || {};
        const container = document.getElementById('health-metrics'); if (!container) return;
        container.innerHTML = `...`;
    }

    populateProfileSection() {
        const patient = this.dashboardData.patient || {};
        const profileInfo = document.getElementById('profile-info');
        if (profileInfo) {
            profileInfo.innerHTML = `...`;
        }
    }

    populateAppointmentsSection() {
        const appointments = this.dashboardData.appointments || [];
        this.populateUpcomingAppointments(appointments);
        this.populateAllAppointments(appointments);
        this.populateAppointmentsSummary(appointments);
    }

    populateUpcomingAppointments(appointments) {
        const container = document.getElementById('upcoming-appointments'); if (!container) return;
        if (appointments.length === 0) {
            container.innerHTML = `<div class="alert alert-info"><i class="bi bi-info-circle me-2"></i>No tienes citas programadas próximamente.</div>`;
        } else {
            let html = '';
            appointments.slice(0,3).forEach(a => {
                html += `<div class="appointment-item"><div class="appointment-date">${this.formatDateTime(a.fecha_hora)}</div><div class="appointment-doctor">${a.profesional_nombre || ''}</div><div class="appointment-specialty">${a.specialty || ''}</div></div>`;
            });
            container.innerHTML = html;
        }
    }

    populateAllAppointments(appointments) {
        const container = document.getElementById('all-appointments'); if (!container) return;
        if (appointments.length === 0) container.innerHTML = `<div class="alert alert-info"><i class="bi bi-info-circle me-2"></i>No tienes citas programadas próximamente.</div>`;
        else {
            let html = '<div class="row">';
            appointments.forEach(app => { html += `<div class="col-md-6 mb-3"><div class="card"><div class="card-body"><h6 class="card-title">${app.motivo || 'Consulta médica'}</h6><p class="card-text"><strong>Fecha:</strong> ${this.formatDateTime(app.fecha_hora)}<br><strong>Profesional:</strong> ${app.profesional_nombre || ''}</p></div></div></div>`; });
            html += '</div>'; container.innerHTML = html;
        }
    }

    populateAppointmentsSummary(appointments) {
        const container = document.getElementById('appointments-summary'); if (!container) return;
        container.innerHTML = `<div class="text-center"><h3 class="text-primary">${appointments.length}</h3><p class="text-muted mb-4">Citas Programadas</p><div class="d-grid"><button class="btn btn-primary mb-2" onclick="window.patientDashboard.showSection('agendar-cita')"><i class="bi bi-plus-circle me-2"></i>Solicitar Cita</button><small class="text-muted">Las solicitudes pasarán por admisión para su triaje</small></div></div>`;
    }

    populateMedicationsSection() { /* simplified for brevity */ }
    populateMedicalHistorySection() { /* simplified for brevity */ }
    populateResultsSection() { /* simplified for brevity */ }
    populateAllergiesSection() { /* simplified for brevity */ }

    showSection(sectionName) {
        document.querySelectorAll('.content-section').forEach(s => s.classList.add('d-none'));
        document.querySelectorAll('.sidebar-nav .nav-link').forEach(l => l.classList.remove('active'));
        const target = document.getElementById(`section-${sectionName}`);
        if (target) target.classList.remove('d-none');
        const active = document.querySelector(`[data-section="${sectionName}"]`);
        if (active) active.classList.add('active');
        this.currentSection = sectionName;
    }

    async downloadHealthRecord() {
        const token = this.getAuthTokenRaw(); if (!token) return this.handleAuthError();
        try {
            const resp = await fetch('/api/patient/me/summary/export', { method: 'GET', headers: { 'Authorization': `Bearer ${token}` } });
            if (!resp.ok) { if (resp.status === 401) { this.handleAuthError(); return; } throw new Error('Error al generar PDF'); }
            const blob = await resp.blob(); const url = window.URL.createObjectURL(blob); const a = document.createElement('a'); a.style.display='none'; a.href = url; a.download = `historia_clinica.pdf`; document.body.appendChild(a); a.click(); window.URL.revokeObjectURL(url); a.remove();
            this.showAlert('Historia clínica descargada exitosamente','success');
        } catch (err) { console.error(err); this.showAlert('Error al descargar la historia clínica','danger'); }
    }

    logout() {
        try { localStorage.removeItem('authToken'); localStorage.removeItem('auth_token'); sessionStorage.removeItem('authToken'); } catch(e){}
        document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        window.location.href = '/login';
    }

    setupAppointmentForm() {
        const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
        const minDate = tomorrow.toISOString().split('T')[0];
        const dateInput = document.getElementById('appointmentDate'); if (dateInput) { dateInput.setAttribute('min', minDate); const maxDate = new Date(); maxDate.setMonth(maxDate.getMonth()+3); dateInput.setAttribute('max', maxDate.toISOString().split('T')[0]); }
        this.loadAvailableDoctors();
        const form = document.getElementById('appointmentForm'); if (form) form.addEventListener('submit', (e)=>this.handleAppointmentSubmit(e));
    }

    async loadAvailableDoctors() {
        const token = this.getAuthTokenRaw(); const select = document.getElementById('doctorSelect'); if (!select || !token) return;
        try {
            select.innerHTML = '<option value="">Cargando especialistas...</option>';
            const resp = await fetch('/api/patient/practitioners', { method: 'GET', headers: { 'Authorization': `Bearer ${token}` } });
            if (!resp.ok) { if (resp.status === 401) { this.handleAuthError(); return; } throw new Error('Error cargando médicos'); }
            const data = await resp.json();
            if (Array.isArray(data) && data.length>0) {
                select.innerHTML = '<option value="">Seleccionar especialista</option>';
                data.forEach(d => {
                    const option = document.createElement('option'); option.value = d.id; option.textContent = d.name || d.username || ('Dr. '+(d.name||d.username)); select.appendChild(option);
                });
            } else { select.innerHTML = '<option value="">No hay médicos disponibles</option>'; }
        } catch (err) { console.error('Error cargando médicos:', err); select.innerHTML = '<option value="">Error al cargar médicos</option>'; }
    }

    async handleAppointmentSubmit(event) {
        event.preventDefault();
        const token = this.getAuthTokenRaw(); if (!token) { this.handleAuthError(); return; }
        const submitButton = event.target.querySelector('button[type="submit"]'); const originalText = submitButton?.innerHTML || 'Solicitar Cita';
        const profesional_id = document.getElementById('doctorSelect')?.value || null;
        const date = document.getElementById('appointmentDate')?.value;
        const time = document.getElementById('appointmentTime')?.value;
        const motivo = document.getElementById('appointmentReason')?.value;
        const dur = parseInt(document.getElementById('appointmentDuration')?.value || '30');
        if (!date || !time || !motivo) { this.showAppointmentAlert('Por favor completa todos los campos requeridos.', 'warning'); return; }
        const fecha_hora = `${date}T${time}:00`;
        try {
            if (submitButton) { submitButton.disabled = true; submitButton.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Enviando...'; }
            const resp = await fetch('/api/patient/me/appointments', { method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ fecha_hora, duracion_minutos: dur, motivo, profesional_id: profesional_id ? parseInt(profesional_id) : undefined }) });
            const result = await resp.json().catch(()=>null);
            if (resp.ok && result) {
                this.showAppointmentAlert('Solicitud enviada correctamente. Su solicitud pasará por admisión para triaje.', 'success');
                event.target.reset(); setTimeout(()=>{ this.loadDashboard(); this.showSection('citas'); }, 1200);
            } else {
                if (resp.status === 401) { this.handleAuthError(); return; }
                throw new Error(result?.detail || result?.message || 'Error al solicitar la cita');
            }
        } catch (err) {
            console.error('Error solicitando cita:', err); this.showAppointmentAlert(err.message || 'Error al solicitar la cita', 'danger');
        } finally {
            if (submitButton) { submitButton.disabled = false; submitButton.innerHTML = originalText; }
        }
    }

    showAppointmentAlert(message,type){ this.showAlert(message,type,{position:'fixed',top:'100px',right:'20px',zIndex:'9999',minWidth:'300px'}); }
    showAlert(message, type, customStyles={}){
        const existing = document.querySelector('.custom-alert'); if (existing) existing.remove();
        const alertDiv = document.createElement('div'); alertDiv.className = `alert alert-${type} alert-dismissible fade show custom-alert`;
        Object.assign(alertDiv.style, customStyles);
        alertDiv.innerHTML = `<i class="bi bi-${type==='success'?'check-circle':type==='warning'?'exclamation-triangle':'x-circle'} me-2"></i>${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        document.body.appendChild(alertDiv); setTimeout(()=>{ if (alertDiv.parentNode) alertDiv.remove(); },5000);
    }

    formatDate(dateString){ if(!dateString) return 'No especificada'; const d=new Date(dateString); return d.toLocaleDateString('es-ES',{year:'numeric',month:'long',day:'numeric'}); }
    formatDateTime(dateString){ if(!dateString) return 'No especificada'; const d=new Date(dateString); return d.toLocaleString('es-ES',{year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}); }
    formatTime(t){ if(!t) return 'No especificada'; const [h,m]=t.split(':'); const hn=parseInt(h); const period = hn>=12?'PM':'AM'; const hh = hn>12?hn-12:hn===0?12:hn; return `${hh}:${m} ${period}`; }
}

const patientDashboard = new PatientDashboard();
window.showSection = (s)=>patientDashboard.showSection(s);
window.downloadHealthRecord = ()=>patientDashboard.downloadHealthRecord();
window.logout = ()=>patientDashboard.logout();
window.loadDashboard = ()=>patientDashboard.loadDashboard();
