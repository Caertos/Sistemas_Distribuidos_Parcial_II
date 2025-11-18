// Orquestador del dashboard paciente: carga dinámica de componentes y exposición de API pública
(function(window){
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

  function loadScript(src){
    return new Promise((resolve,reject)=>{
      const s = document.createElement('script'); s.src = src; s.async = false; s.onload = ()=>resolve(); s.onerror = (e)=>reject(e); document.head.appendChild(s);
    });
  }

  async function loadAll(){
    const base = scriptBase();
    for(const p of SCRIPTS){ await loadScript(base + p); }
  }

  function composeDashboard(){
    const C = window.PatientComponents || {};
    const App = {};
    App.loadAppointments = C.Appointments && C.Appointments.loadAppointments ? C.Appointments.loadAppointments : ()=>{};
    App.loadMedications = C.Medications && C.Medications.loadMedications ? C.Medications.loadMedications : ()=>{};
    App.loadAllergies = C.Allergies && C.Allergies.loadAllergies ? C.Allergies.loadAllergies : ()=>{};
    App.createAppointment = C.Appointments && C.Appointments.createAppointment ? C.Appointments.createAppointment : ()=>{};
    App.cancelAppointment = C.Appointments && C.Appointments.cancelAppointment ? C.Appointments.cancelAppointment : ()=>{};
    App.exportSummary = C.Api && C.Api.fetchAPI ? async (format)=>{ const token = (window.Auth && typeof window.Auth.getToken==='function') ? window.Auth.getToken() : null; const url = `/api/patient/me/summary/export?format=${encodeURIComponent(format)}`; const headers = Object.assign({}, token? {'Authorization': `Bearer ${token}`} : {}); const resp = await fetch(url,{ method:'GET', headers }); if(!resp.ok){ const err = await resp.json().catch(()=>({detail:'Error'})); throw new Error(err.detail||`Error ${resp.status}`); } const blob = await resp.blob(); const contentType = resp.headers.get('Content-Type')||''; let ext='bin'; if(format==='pdf' || contentType.includes('pdf')) ext='pdf'; else if(format==='fhir' || contentType.includes('json')) ext='json'; const filename = `resumen_paciente.${ext}`; const urlBlob = window.URL.createObjectURL(blob); const a=document.createElement('a'); a.href=urlBlob; a.download=filename; document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(urlBlob); } : ()=>{};
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

    window.PatientDashboard = Object.assign(window.PatientDashboard || {}, App);
  }

  (function init(){
    document.addEventListener('DOMContentLoaded', async function(){
      try{ await loadAll(); }catch(e){}
      composeDashboard();
      try{ if(window.PatientComponents && window.PatientComponents.Profile) await window.PatientComponents.Profile.loadProfile(); }catch(e){}
      try{ if(window.PatientComponents && window.PatientComponents.Practitioners) await window.PatientComponents.Practitioners.loadPractitioners(); }catch(e){}
      try{ const input=document.getElementById('create-appointment-fecha'); if(input){ const now=new Date(); now.setDate(now.getDate()+2); const pad=n=>String(n).padStart(2,'0'); const minStr=`${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`; input.min = minStr; } }catch(e){}
      const hash = (window.location.hash || '#dashboard').replace('#',''); if(window.PatientDashboard && window.PatientDashboard.navigateTo) window.PatientDashboard.navigateTo(hash || 'dashboard');
      const form = document.getElementById('create-appointment-form'); if(form) form.addEventListener('submit', function(e){ e.preventDefault(); const fd = new FormData(form); if(window.PatientDashboard && window.PatientDashboard.createAppointment) window.PatientDashboard.createAppointment(fd); });
    });
  })();

})();
