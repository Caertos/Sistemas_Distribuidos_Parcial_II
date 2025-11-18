(function(window){
  const Medications = {};
  const Api = () => (window.PatientComponents && window.PatientComponents.Api) ? window.PatientComponents.Api : null;
  const UI = () => (window.PatientComponents && window.PatientComponents.UI) ? window.PatientComponents.UI : null;

  async function loadMedications(){
    const api = Api(); const ui = UI(); if(!api) return;
    try{
      const meds = await api.fetchAPI('/api/patient/me/medications');
      const list = document.getElementById('medications-list'); if(!list) return;
      if(!meds || meds.length===0){ list.innerHTML = '<p>No tienes medicamentos registrados.</p>'; return; }
      let html = '<ul style="line-height:2;">';
      meds.forEach(m=>{ html += `<li><strong>${m.nombre || m.medicamento_nombre || '—'}</strong>`; if(m.dosis) html += ` - ${m.dosis}`; if(m.frecuencia) html += ` - ${m.frecuencia}`; if(m.via_administracion) html += ` (${m.via_administracion})`; html += '</li>'; });
      html += '</ul>'; list.innerHTML = html;
    }catch(e){ const list = document.getElementById('medications-list'); if(list) list.innerHTML = `<p style="color:red;">Error: ${e.message}</p>` }
  }

  Medications.loadMedications = loadMedications;
  window.PatientComponents = window.PatientComponents || {};
  window.PatientComponents.Medications = Medications;
})(window);
