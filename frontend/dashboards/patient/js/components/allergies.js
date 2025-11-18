(function(window){
  const Allergies = {};
  const Api = () => (window.PatientComponents && window.PatientComponents.Api) ? window.PatientComponents.Api : null;
  const UI = () => (window.PatientComponents && window.PatientComponents.UI) ? window.PatientComponents.UI : null;

  async function loadAllergies(){
    const api = Api(); const ui = UI(); if(!api) return;
    try{
      const all = await api.fetchAPI('/api/patient/me/allergies');
      const list = document.getElementById('allergies-list'); if(!list) return;
      if(!all || all.length===0){ list.innerHTML = '<p>No tienes alergias registradas.</p>'; return; }
      let html = '<ul style="line-height:2;">';
      all.forEach(a=>{ html += `<li><strong>${a.alergeno || a.sustancia || '—'}</strong>`; if(a.severidad) html += ` - Severidad: ${a.severidad}`; if(a.reaccion) html += ` - Reacción: ${a.reaccion}`; html += '</li>'; });
      html += '</ul>'; list.innerHTML = html;
    }catch(e){ const list = document.getElementById('allergies-list'); if(list) list.innerHTML = `<p style="color:red;">Error: ${e.message}</p>` }
  }

  Allergies.loadAllergies = loadAllergies;
  window.PatientComponents = window.PatientComponents || {};
  window.PatientComponents.Allergies = Allergies;
})(window);
