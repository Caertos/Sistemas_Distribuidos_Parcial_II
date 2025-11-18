// Orquestador del dashboard paciente: carga dinámica de componentes y exposición de API pública
(function(){
  const SCRIPTS = [
    'components/api.js',
    'components/ui.js',
    'components/appointments.js',
    'components/medications.js',
    'components/allergies.js',
    'components/profile.js',
    'components/summary.js',
    'components/practitioners.js'
  ];

  function scriptBase(){
    const cs = document.currentScript && document.currentScript.src ? document.currentScript.src : null;
    if (!cs) return './';
    return cs.replace(/\/[^\/]*$/, '/');
  }

  // Ruta absoluta segura para recursos estáticos del dashboard paciente.
  // Si `document.currentScript` no está disponible (carga atípica), usamos
  // la ruta montada por FastAPI: `/static/dashboards/patient/js/`.
  function safeBase(){
    try{
      const b = scriptBase();
      if(b && b.indexOf('/static/') !== -1) return b;
    }catch(e){}
    return '/static/dashboards/patient/js/';
  }

  // Asegurar que existe el objeto público antes de exponer métodos.
  window.PatientDashboard = window.PatientDashboard || {};

  function loadScript(src){
    return new Promise((resolve,reject)=>{
      const s = document.createElement('script'); s.src = src; s.async = false; s.onload = ()=>resolve(); s.onerror = (e)=>reject(e); document.head.appendChild(s);
    });
  }

  async function loadAll(){
    const base = safeBase();
    for(const p of SCRIPTS){
      try{
        await loadScript(base + p);
      }catch(err){
        // Intentar ruta alternativa sin `/static` (por si está sirviendo desde otra base)
        try{
          await loadScript(base.replace('/static','') + p);
        }catch(e){
          console.error('No se pudo cargar componente:', p, err, e);
        }
      }
    }
  }

  function composeDashboard(){
    const C = (typeof globalThis !== 'undefined' ? globalThis.PatientComponents : (typeof window !== 'undefined' ? window.PatientComponents : null)) || {};
    const App = {};
    App.loadAppointments = C.Appointments && C.Appointments.loadAppointments ? C.Appointments.loadAppointments : ()=>{};
    App.loadMedications = C.Medications && C.Medications.loadMedications ? C.Medications.loadMedications : ()=>{};
    App.loadAllergies = C.Allergies && C.Allergies.loadAllergies ? C.Allergies.loadAllergies : ()=>{};
    App.createAppointment = C.Appointments && C.Appointments.createAppointment ? C.Appointments.createAppointment : ()=>{};
    App.cancelAppointment = C.Appointments && C.Appointments.cancelAppointment ? C.Appointments.cancelAppointment : ()=>{};
    App.exportSummary = C.Api && C.Api.fetchAPI ? async (format) => {
      const G = (typeof globalThis !== 'undefined') ? globalThis : (typeof window !== 'undefined' ? window : this);
      const token = (G.Auth && typeof G.Auth.getToken === 'function') ? G.Auth.getToken() : null;
      const url = `/api/patient/me/summary/export?format=${encodeURIComponent(format)}`;
      const headers = Object.assign({}, token ? {'Authorization': `Bearer ${token}`} : {});
      const resp = await fetch(url, { method: 'GET', headers });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Error' }));
        throw new Error(err.detail || `Error ${resp.status}`);
      }
      const blob = await resp.blob();
      const contentType = resp.headers.get('Content-Type') || '';
      let ext = 'bin';
      if (format === 'pdf' || contentType.includes('pdf')) ext = 'pdf';
      else if (format === 'fhir' || contentType.includes('json')) ext = 'json';
      const filename = `resumen_paciente.${ext}`;
      const urlBlob = (typeof globalThis !== 'undefined' ? globalThis : window).URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = urlBlob; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
      (typeof globalThis !== 'undefined' ? globalThis : window).URL.revokeObjectURL(urlBlob);
    } : () => {};
    App.loadProfile = C.Profile && C.Profile.loadProfile ? C.Profile.loadProfile : ()=>{};
    App.loadSummary = C.Summary && C.Summary.loadSummary ? C.Summary.loadSummary : ()=>{};
    App.navigateTo = async function(section){
      const ids = ['panel-dashboard','appointments-section','medications-section','allergies-section','summary-section','profile-section'];
      ids.forEach(id=>{ const el=document.getElementById(id); if(el) el.style.display='none'; });
      const items = document.querySelectorAll('#patient-sidebar .nav-item'); items.forEach(it=>it.classList.toggle('active', it.dataset.section === section));
      if (section === 'dashboard'){ const p=document.getElementById('panel-dashboard'); if(p) p.style.display='block'; App.loadAppointments(); }
      else if(section === 'appointments'){ const p=document.getElementById('appointments-section'); if(p) p.style.display='block'; await App.loadAppointments(); }
      else if(section === 'medications'){ const p=document.getElementById('medications-section'); if(p) p.style.display='block'; await App.loadMedications(); }
      else if(section === 'allergies'){ const p=document.getElementById('allergies-section'); if(p) p.style.display='block'; await App.loadAllergies(); }
      else if(section === 'summary'){ const p=document.getElementById('summary-section'); if(p) p.style.display='block'; await App.loadSummary(); }
      else if(section === 'profile'){ const p=document.getElementById('profile-section'); if(p) p.style.display='block'; await App.loadProfile(); }
      try{ history.pushState({section},'',`#${section}`); }catch(e){}
    };

    // Exponer API pública en el objeto global
    const G = (typeof globalThis !== 'undefined') ? globalThis : (typeof window !== 'undefined' ? window : this);
    G.PatientDashboard = Object.assign(G.PatientDashboard || {}, App);
  }

  (function init(){
    document.addEventListener('DOMContentLoaded', async function(){
      try{ await loadAll(); }catch(e){}
      composeDashboard();
      try{ const G = (typeof globalThis !== 'undefined') ? globalThis : (typeof window !== 'undefined' ? window : this); if(G.PatientComponents && G.PatientComponents.Profile) await G.PatientComponents.Profile.loadProfile(); }catch(e){}
      try{ const G = (typeof globalThis !== 'undefined') ? globalThis : (typeof window !== 'undefined' ? window : this); if(G.PatientComponents && G.PatientComponents.Practitioners) await G.PatientComponents.Practitioners.loadPractitioners(); }catch(e){}
      try{ const input=document.getElementById('create-appointment-fecha'); if(input){ const now=new Date(); now.setDate(now.getDate()+2); const pad=n=>String(n).padStart(2,'0'); const minStr=`${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`; input.min = minStr; } }catch(e){}
      const G = (typeof globalThis !== 'undefined') ? globalThis : (typeof window !== 'undefined' ? window : this);
      const hash = (G.location && G.location.hash || '#dashboard').replace('#',''); if(G.PatientDashboard && G.PatientDashboard.navigateTo) G.PatientDashboard.navigateTo(hash || 'dashboard');
      const form = document.getElementById('create-appointment-form'); if(form) form.addEventListener('submit', function(e){ e.preventDefault(); const fd = new FormData(form); if(window.PatientDashboard && window.PatientDashboard.createAppointment) window.PatientDashboard.createAppointment(fd); });
    });
  })();

})();
