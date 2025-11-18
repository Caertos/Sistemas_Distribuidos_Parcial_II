(function(window){
  const Practitioners = {};
  const Api = () => (window.PatientComponents && window.PatientComponents.Api) ? window.PatientComponents.Api : null;

  async function loadPractitioners(){
    const api = Api(); if(!api) return;
    try{
      // endpoint correct: router is mounted under /api/patient
      const reps = await api.fetchAPI('/api/patient/practitioners');
      const sel = document.getElementById('practitioner-select'); if(!sel) return;
      sel.innerHTML = '<option value="">-- Seleccionar médico (opcional) --</option>';
      reps.forEach(p => { const opt = document.createElement('option'); opt.value = p.id || p.username || ''; opt.textContent = p.name || p.username || opt.value; sel.appendChild(opt); });
    }catch(e){ /* silencioso */ }
  }

  Practitioners.loadPractitioners = loadPractitioners;
  window.PatientComponents = window.PatientComponents || {};
  window.PatientComponents.Practitioners = Practitioners;
})(window);
