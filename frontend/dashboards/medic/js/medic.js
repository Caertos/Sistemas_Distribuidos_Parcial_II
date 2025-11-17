// JS específico para médico/practitioner - ver citas admitidas y pacientes
(function(window){
  const Auth = window.Auth;

  async function fetchAPI(endpoint, options = {}) {
    const token = Auth && Auth.getToken ? Auth.getToken() : null;
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers
    };
    
    const response = await fetch(endpoint, { ...options, headers, credentials: 'include' });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Error en la petición' }));
      throw new Error(error.detail || `Error ${response.status}`);
    }
    return response.json();
  }

  async function loadAppointments() {
    try {
      const data = await fetchAPI('/api/practitioner/appointments?admitted=true&limit=50');
      const appointments = data.items || data || [];
      
      const list = document.getElementById('appointments-list');
      if (!appointments || appointments.length === 0) {
        list.innerHTML = '<p>No hay citas admitidas pendientes.</p>';
        return;
      }

      // Actualizar contador
      document.getElementById('appointments-count').textContent = appointments.length;
      
      let html = '<table style="width:100%; border-collapse:collapse;"><thead><tr>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Cita ID</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Paciente ID</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Fecha/Hora</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Estado</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Acciones</th>';
      html += '</tr></thead><tbody>';
      
      appointments.forEach(apt => {
        html += '<tr>';
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">${apt.cita_id || apt.id || '—'}</td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">${apt.paciente_id || apt.patient_id || '—'}</td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">${formatDate(apt.fecha_hora || apt.time)}</td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;"><span class="badge">${apt.estado || apt.estado_admision || 'admitida'}</span></td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">`;
        html += `<button onclick="MedicDashboard.viewPatient(${apt.paciente_id || apt.patient_id})" style="padding:0.25rem 0.5rem; background:#0d6efd; color:white; border:none; border-radius:4px; cursor:pointer;">Ver Paciente</button>`;
        html += `</td>`;
        html += '</tr>';
      });
      
      html += '</tbody></table>';
      list.innerHTML = html;
    } catch (error) {
      console.error('Error cargando citas:', error);
      document.getElementById('appointments-list').innerHTML = `<p style="color:red;">Error: ${error.message}</p>`;
    }
  }

  async function viewPatient(patientId) {
    try {
      const patient = await fetchAPI(`/api/practitioner/patients/${patientId}`);
      
      let html = '<dl style="line-height:1.8;">';
      html += `<dt style="font-weight:bold;">Nombre:</dt><dd>${patient.nombre || '—'} ${patient.apellido || ''}</dd>`;
      html += `<dt style="font-weight:bold;">Documento:</dt><dd>${patient.documento_id || '—'}</dd>`;
      html += `<dt style="font-weight:bold;">Sexo:</dt><dd>${patient.sexo || '—'}</dd>`;
      html += `<dt style="font-weight:bold;">Fecha Nacimiento:</dt><dd>${patient.fecha_nacimiento || '—'}</dd>`;
      html += `<dt style="font-weight:bold;">Contacto:</dt><dd>${patient.contacto || '—'}</dd>`;
      html += `<dt style="font-weight:bold;">Ciudad:</dt><dd>${patient.ciudad || '—'}</dd>`;
      html += '</dl>';
      
      document.getElementById('patient-detail-content').innerHTML = html;
      document.getElementById('patient-detail-modal').style.display = 'block';
    } catch (error) {
      console.error('Error cargando paciente:', error);
      alert('Error cargando información del paciente: ' + error.message);
    }
  }

  function hidePatientDetail() {
    document.getElementById('patient-detail-modal').style.display = 'none';
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString('es-ES', { 
        year: 'numeric', 
        month: '2-digit', 
        day: '2-digit', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } catch (e) {
      return dateStr;
    }
  }

  document.addEventListener('DOMContentLoaded', function(){
    console.log('Medic dashboard loaded');
    loadAppointments();
  });

  window.MedicDashboard = {
    loadAppointments,
    viewPatient,
    hidePatientDetail
  };

})(window);
