(function(window){
  const Appointments = {};
  const Api = () => (window.PatientComponents && window.PatientComponents.Api) ? window.PatientComponents.Api : null;
  const UI = () => (window.PatientComponents && window.PatientComponents.UI) ? window.PatientComponents.UI : null;

  async function loadAppointments(){
    const api = Api(); const ui = UI();
    if(!api) return;
    try{
      const appointments = await api.fetchAPI('/api/patient/me/appointments');
      const list = document.getElementById('appointments-list'); if(!list) return;
      if(!appointments || appointments.length === 0){ list.innerHTML = '<p>No tienes citas registradas.</p>'; const na = document.getElementById('next-appointment'); if(na) na.textContent = '—'; return; }
      const showAll = window.PatientDashboard && window.PatientDashboard._showAllAppointments;
      let filtered = appointments;
      if(!showAll){ const now = new Date(); filtered = appointments.filter(a=>{ const est = (a.estado||'').toLowerCase(); if(['cancelada','completada','cancelado','finalizada'].includes(est)) return false; try{ const d=new Date(a.fecha_hora); return isNaN(d.getTime())?true:d>=now }catch(e){ return true } }); }
      const next = (filtered && filtered.length>0) ? filtered[0] : appointments[0]; if(next && next.fecha_hora){ const na = document.getElementById('next-appointment'); if(na && ui) na.textContent = ui.formatDate(next.fecha_hora); }
      let html = '<table style="width:100%; border-collapse:collapse;"><thead><tr><th>Fecha/Hora</th><th>Duración</th><th>Motivo</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>';
      (filtered||[]).forEach(apt=>{
        const date = ui ? ui.formatDate(apt.fecha_hora) : apt.fecha_hora;
        const actions = (apt.estado||'').toLowerCase().includes('cancel') || (apt.estado||'').toLowerCase().includes('final') ? '' : `<button onclick="PatientDashboard.cancelAppointment(${apt.cita_id})">Cancelar</button>`;
        html += `<tr><td>${date}</td><td>${apt.duracion_minutos||'—'} min</td><td>${apt.motivo||'—'}</td><td>${apt.estado||'—'}</td><td>${actions}</td></tr>`;
      });
      html += '</tbody></table>';
      list.innerHTML = html;
    }catch(e){ const list = document.getElementById('appointments-list'); if(list) list.innerHTML = `<p style="color:red;">Error: ${e.message}</p>` }
  }

  async function createAppointment(formData){
    const api = Api(); const ui = UI(); if(!api) throw new Error('API no disponible');
    const msgEl = document.getElementById('create-appointment-message'); const submitBtn = document.querySelector('#create-appointment-form button[type="submit"]'); if(msgEl) ui && ui.clearFormMessage(msgEl); if(submitBtn) submitBtn.disabled = true;
    try{
      const fhRaw = formData.get('fecha_hora'); if(!fhRaw) throw new Error('Seleccione fecha y hora'); const fh = new Date(fhRaw);
      const now = new Date(); const min = new Date(); min.setDate(min.getDate()+2);
      if(isNaN(fh.getTime())) throw new Error('Fecha inválida'); if(fh < now) throw new Error('No se puede agendar en el pasado'); if(fh < min) throw new Error('Las citas deben solicitarse con al menos 2 días de anticipación');
      const payload = { fecha_hora: formData.get('fecha_hora'), duracion_minutos: parseInt(formData.get('duracion_minutos'))||30, motivo: formData.get('motivo')||null, profesional_id: formData.get('profesional_id')||null };
      await api.fetchAPI('/api/patient/me/appointments',{ method: 'POST', body: JSON.stringify(payload) });
      if(msgEl && ui) ui.setFormMessage(msgEl, 'success', 'Cita agendada exitosamente');
      api.setGlobalMessage('success', 'Cita agendada correctamente');
      setTimeout(()=>{ ui && ui.hideCreateAppointmentForm(); loadAppointments(); }, 900);
    }catch(e){ if(msgEl && ui) ui.setFormMessage(msgEl, 'error', 'Error agendando cita: '+(e && e.message? e.message : String(e))); else api && api.setGlobalMessage('error', 'Error agendando cita: '+(e && e.message? e.message : String(e))); }
    finally{ if(submitBtn) submitBtn.disabled = false }
  }

  async function cancelAppointment(id){
    const api = Api(); if(!api) return;
    if(!confirm('¿Estás seguro de cancelar esta cita?')) return;
    try{ await api.fetchAPI(`/api/patient/me/appointments/${id}`, { method: 'DELETE' }); api.setGlobalMessage('success','Cita cancelada'); loadAppointments(); }catch(e){ api.setGlobalMessage('error','Error cancelando cita: '+(e && e.message? e.message : String(e))); }
  }

  function toggleShowAllAppointments(checked){ window.PatientDashboard = window.PatientDashboard || {}; window.PatientDashboard._showAllAppointments = !!checked; const lbl = document.getElementById('appointments-filter-label'); if(lbl) lbl.textContent = checked? 'Todas':'Pendientes'; loadAppointments(); }

  Appointments.loadAppointments = loadAppointments;
  Appointments.createAppointment = createAppointment;
  Appointments.cancelAppointment = cancelAppointment;
  Appointments.toggleShowAllAppointments = toggleShowAllAppointments;

  window.PatientComponents = window.PatientComponents || {};
  window.PatientComponents.Appointments = Appointments;
})(window);
