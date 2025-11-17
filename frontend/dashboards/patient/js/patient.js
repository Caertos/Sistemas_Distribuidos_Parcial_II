// JS específico para paciente - ver citas, medicamentos, alergias
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
      const appointments = await fetchAPI('/api/patient/me/appointments');
      
      const list = document.getElementById('appointments-list');
      if (!appointments || appointments.length === 0) {
        list.innerHTML = '<p>No tienes citas registradas.</p>';
        document.getElementById('next-appointment').textContent = '—';
        return;
      }

      // Mostrar próxima cita
      const next = appointments[0];
      if (next && next.fecha_hora) {
        document.getElementById('next-appointment').textContent = formatDate(next.fecha_hora);
      }
      
      let html = '<table style="width:100%; border-collapse:collapse;"><thead><tr>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Fecha/Hora</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Duración</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Motivo</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Estado</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Acciones</th>';
      html += '</tr></thead><tbody>';
      
      appointments.forEach(apt => {
        html += '<tr>';
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">${formatDate(apt.fecha_hora)}</td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">${apt.duracion_minutos || '—'} min</td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">${apt.motivo || '—'}</td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;"><span class="badge">${apt.estado || '—'}</span></td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">`;
        if (apt.estado !== 'cancelada' && apt.estado !== 'completada') {
          html += `<button onclick="PatientDashboard.cancelAppointment(${apt.cita_id})" style="padding:0.25rem 0.5rem; background:#dc3545; color:white; border:none; border-radius:4px; cursor:pointer;">Cancelar</button>`;
        }
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

  async function loadMedications() {
    try {
      const medications = await fetchAPI('/api/patient/me/medications');
      
      document.getElementById('medications-section').style.display = 'block';
      document.getElementById('medications-count').textContent = medications.length;
      
      const list = document.getElementById('medications-list');
      if (!medications || medications.length === 0) {
        list.innerHTML = '<p>No tienes medicamentos registrados.</p>';
        return;
      }
      
      let html = '<ul style="line-height:2;">';
      medications.forEach(med => {
        html += `<li><strong>${med.nombre || med.medicamento_nombre || '—'}</strong>`;
        if (med.dosis) html += ` - ${med.dosis}`;
        if (med.frecuencia) html += ` - ${med.frecuencia}`;
        if (med.via_administracion) html += ` (${med.via_administracion})`;
        html += '</li>';
      });
      html += '</ul>';
      list.innerHTML = html;
    } catch (error) {
      console.error('Error cargando medicamentos:', error);
      document.getElementById('medications-list').innerHTML = `<p style="color:red;">Error: ${error.message}</p>`;
    }
  }

  async function loadAllergies() {
    try {
      const allergies = await fetchAPI('/api/patient/me/allergies');
      
      document.getElementById('allergies-section').style.display = 'block';
      document.getElementById('allergies-count').textContent = allergies.length;
      
      const list = document.getElementById('allergies-list');
      if (!allergies || allergies.length === 0) {
        list.innerHTML = '<p>No tienes alergias registradas.</p>';
        return;
      }
      
      let html = '<ul style="line-height:2;">';
      allergies.forEach(allergy => {
        html += `<li><strong>${allergy.alergeno || allergy.sustancia || '—'}</strong>`;
        if (allergy.severidad) html += ` - Severidad: ${allergy.severidad}`;
        if (allergy.reaccion) html += ` - Reacción: ${allergy.reaccion}`;
        html += '</li>';
      });
      html += '</ul>';
      list.innerHTML = html;
    } catch (error) {
      console.error('Error cargando alergias:', error);
      document.getElementById('allergies-list').innerHTML = `<p style="color:red;">Error: ${error.message}</p>`;
    }
  }

  async function createAppointment(formData) {
    try {
      const payload = {
        fecha_hora: formData.get('fecha_hora'),
        duracion_minutos: parseInt(formData.get('duracion_minutos')) || 30,
        motivo: formData.get('motivo') || null
      };
      
      await fetchAPI('/api/patient/me/appointments', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      
      alert('Cita agendada exitosamente');
      hideCreateAppointmentForm();
      loadAppointments();
    } catch (error) {
      console.error('Error creando cita:', error);
      alert('Error agendando cita: ' + error.message);
    }
  }

  async function cancelAppointment(appointmentId) {
    if (!confirm('¿Estás seguro de cancelar esta cita?')) return;
    
    try {
      await fetchAPI(`/api/patient/me/appointments/${appointmentId}`, { method: 'DELETE' });
      alert('Cita cancelada');
      loadAppointments();
    } catch (error) {
      console.error('Error cancelando cita:', error);
      alert('Error cancelando cita: ' + error.message);
    }
  }

  function showCreateAppointmentForm() {
    document.getElementById('create-appointment-modal').style.display = 'block';
  }

  function hideCreateAppointmentForm() {
    document.getElementById('create-appointment-modal').style.display = 'none';
    document.getElementById('create-appointment-form').reset();
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
    console.log('Patient dashboard loaded');
    loadAppointments();
    
    // Form submit handler
    const form = document.getElementById('create-appointment-form');
    if (form) {
      form.addEventListener('submit', function(e) {
        e.preventDefault();
        createAppointment(new FormData(form));
      });
    }
  });

  window.PatientDashboard = {
    loadAppointments,
    loadMedications,
    loadAllergies,
    createAppointment,
    cancelAppointment,
    showCreateAppointmentForm,
    hideCreateAppointmentForm
  };

})(window);
