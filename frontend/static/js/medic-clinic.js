/* Medic clinic helpers: create observations, vitals and simple clinic CRUD wrappers.
   Uses medicDashboard.apiCall if available (shared API wrapper), otherwise falls
   back to fetch with bearer token from localStorage.
*/

function _getAuthHeaders() {
    const token = (window.medicDashboard && window.medicDashboard.authToken) || localStorage.getItem('authToken') || document.cookie.split('authToken=').pop();
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

async function _fetchApi(endpoint, options = {}) {
    if (window.medicDashboard && typeof window.medicDashboard.apiCall === 'function') {
        return window.medicDashboard.apiCall(endpoint, options);
    }

    const opts = { method: 'GET', headers: _getAuthHeaders(), ...options };
    const resp = await fetch(endpoint, opts);
    if (!resp.ok) {
        const text = await resp.text().catch(() => '');
        throw new Error(`API Error ${resp.status}: ${text}`);
    }
    try {
        return await resp.json();
    } catch (e) {
        return null;
    }
}

function _show(msg, type='info') {
    if (window.medicDashboard && typeof window.medicDashboard.showAlert === 'function') {
        window.medicDashboard.showAlert(msg, type === 'error' ? 'error' : type);
    } else {
        alert(msg);
    }
}

async function saveObservation() {
    try {
        const patientId = document.getElementById('observationPatient').value;
        const type = document.getElementById('observationType').value;
        const value = document.getElementById('observationValue').value;
        const notes = document.getElementById('observationNotes').value;

        if (!patientId || !type || !value) {
            _show('Complete los campos obligatorios', 'error');
            return;
        }

        const payload = {
            paciente_id: patientId,
            tipo: type,
            valor: value,
            notas: notes
        };

        const res = await _fetchApi('/api/practitioner/observations', { method: 'POST', body: JSON.stringify(payload) });
        _show('Observación registrada', 'success');
        bootstrap.Modal.getInstance(document.getElementById('observationModal')).hide();
        document.getElementById('observationForm').reset();
        // refrescar cola/estadísticas
        if (window.medicDashboard) medicDashboard.loadDashboardData();
        return res;
    } catch (err) {
        console.error('saveObservation error', err);
        if (err.message && err.message.includes('501')) {
            _show('Endpoint no implementado en backend (501).', 'error');
        } else {
            _show('Error registrando observación', 'error');
        }
    }
}

async function saveVital() {
    try {
        const patientId = document.getElementById('vitalPatient').value;
        const type = document.getElementById('vitalType').value;
        const value = document.getElementById('vitalValue').value;
        const notes = document.getElementById('vitalNotes').value;

        if (!patientId || !type || !value) {
            _show('Complete los campos obligatorios', 'error');
            return;
        }

        // En el backend el endpoint de signos vitales para practitioner puede no existir;
        // usamos /api/practitioner/observations como fallback con campo 'vital'.
        const payload = {
            paciente_id: patientId,
            tipo: type,
            valor: value,
            notas: notes,
            es_signo_vital: true
        };

        const res = await _fetchApi('/api/practitioner/observations', { method: 'POST', body: JSON.stringify(payload) });
        _show('Signo vital registrado', 'success');
        bootstrap.Modal.getInstance(document.getElementById('vitalModal')).hide();
        document.getElementById('vitalForm').reset();
        if (window.medicDashboard) medicDashboard.loadDashboardData();
        return res;
    } catch (err) {
        console.error('saveVital error', err);
        if (err.message && err.message.includes('501')) {
            _show('Endpoint no implementado en backend (501).', 'error');
        } else {
            _show('Error registrando signo vital', 'error');
        }
    }
}

// Rellenar select de pacientes con datos sencillos (intenta varios endpoints)
async function populatePatientSelects() {
    try {
        // Primero intentar listar pacientes asignados al practitioner
        let patients = [];
        try {
            const resp = await _fetchApi('/api/practitioner/appointments?admitted=true&limit=200');
            const items = resp.items || resp || [];
            patients = (Array.isArray(items) ? items : []).map(it => ({ id: it.paciente_id || it.patient_id || it.id || it.cita_id, name: (it.nombre ? `${it.nombre} ${it.apellido || ''}`.trim() : (it.patient_id || 'Paciente')) }));
        } catch (e) {
            // fallback: intentar endpoint debug
            const resp2 = await _fetchApi('/api/debug/admissions/pending');
            if (Array.isArray(resp2)) patients = resp2.map(r => ({ id: r.paciente_id || r.cita_id, name: `${r.nombre || ''} ${r.apellido || ''}`.trim() || (r.paciente_id || 'Paciente') }));
        }

        const selects = ['patientSelect','prescriptionPatient','observationPatient','vitalPatient'];
        selects.forEach(selId => {
            const sel = document.getElementById(selId);
            if (!sel) return;
            // limpiar
            while (sel.firstChild) sel.removeChild(sel.firstChild);
            const emptyOpt = document.createElement('option'); emptyOpt.value=''; emptyOpt.textContent = 'Seleccionar paciente...'; sel.appendChild(emptyOpt);
            patients.forEach(p => {
                const o = document.createElement('option'); o.value = p.id; o.textContent = p.name || p.id; sel.appendChild(o);
            });
        });

    } catch (err) {
        console.error('populatePatientSelects error', err);
    }
}

// Inicializar petición de pacientes cuando DOM listo
if (typeof window !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => populatePatientSelects());
    } else {
        populatePatientSelects();
    }
}
