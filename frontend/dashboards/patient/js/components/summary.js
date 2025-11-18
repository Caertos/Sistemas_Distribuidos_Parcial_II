(function(window){
  const Summary = {};
  const Api = () => (window.PatientComponents && window.PatientComponents.Api) ? window.PatientComponents.Api : null;
  const UI = () => (window.PatientComponents && window.PatientComponents.UI) ? window.PatientComponents.UI : null;

  async function loadSummary(){
    const api = Api(); const ui = UI(); if(!api) return;
    try{
      const data = await api.fetchAPI('/api/patient/me/summary');
      const el = document.getElementById('summary-content'); if(!el) return;
      // limpiar contenedor
      el.innerHTML = '';
      if(typeof data === 'string'){
        const p = document.createElement('p'); p.textContent = data; el.appendChild(p); return;
      }

      // Citas
      const appts = data.appointments || [];
      const encs = data.encounters || [];
      if(appts.length){
        const sec = document.createElement('section'); sec.className = 'summary-section';
        const h = document.createElement('h3'); h.textContent = 'Citas recientes'; sec.appendChild(h);
        appts.forEach(a => {
          const it = document.createElement('div'); it.className = 'appointment-item';
          const meta = document.createElement('div'); meta.className = 'meta';
          const fecha = ui? ui.formatDate(a.fecha_hora) : (a.fecha_hora||'');
          meta.textContent = `${fecha} — ${a.motivo || '—'}`;
          const state = document.createElement('span'); state.className = 'state'; state.textContent = a.estado || '';
          meta.appendChild(state);
          it.appendChild(meta);
          sec.appendChild(it);
        });
        el.appendChild(sec);
      }

      // Encuentros / notas
      if(encs.length){
        const sec = document.createElement('section'); sec.className = 'summary-section';
        const h = document.createElement('h3'); h.textContent = 'Encuentros / Notas'; sec.appendChild(h);
        encs.forEach(e => {
          const it = document.createElement('div'); it.className = 'encounter-item';
          const meta = document.createElement('div'); meta.className = 'meta';
          const fecha = ui? ui.formatDate(e.fecha_hora || e.fecha) : (e.fecha_hora || e.fecha || '');
          meta.textContent = `${fecha} — ${e.motivo || e.diagnostico || '—'}`;
          it.appendChild(meta);
          const note = document.createElement('div'); note.className = 'note';
          // si viene un campo resumen o diagnostico más largo, mostrarlo; evitar JSON crudo
          const texto = e.resumen || e.diagnostico || JSON.stringify(e, null, 2) || '';
          note.textContent = texto;
          it.appendChild(note);
          sec.appendChild(it);
        });
        el.appendChild(sec);
      }

      if(!appts.length && !encs.length){
        const p = document.createElement('p'); p.textContent = 'No hay registros clínicos disponibles.'; el.appendChild(p);
      }
    }catch(e){ const el = document.getElementById('summary-content'); if(el) { el.innerHTML = ''; const p = document.createElement('p'); p.style.color = 'red'; p.textContent = `Error: ${e.message}`; el.appendChild(p); } }
  }

  Summary.loadSummary = loadSummary;
  window.PatientComponents = window.PatientComponents || {};
  window.PatientComponents.Summary = Summary;
})(window);
