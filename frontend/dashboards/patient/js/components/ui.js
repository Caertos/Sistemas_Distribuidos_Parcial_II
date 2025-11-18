(function(window){
  const UI = {};

  function formatDate(dateStr){
    if (!dateStr) return '—';
    try{ const d = new Date(dateStr); return d.toLocaleString('es-ES',{ year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' }); }catch(e){ return dateStr; }
  }

  function setFormMessage(el, type, text){
    if (!el) return;
    el.style.display = 'block';
    el.textContent = text;
    if (type === 'error'){
      el.style.background = '#fff1f0'; el.style.color = '#8a1f1f'; el.style.border = '1px solid #f5c2c7';
    } else {
      el.style.background = '#f0fff4'; el.style.color = '#0b6623'; el.style.border = '1px solid #b7f5c9';
    }
  }

  function clearFormMessage(el){ if (!el) return; el.style.display='none'; el.textContent=''; el.style.border='none'; }

  function showCreateAppointmentForm(){ const m = document.getElementById('create-appointment-modal'); if (m) m.style.display='block'; }
  function hideCreateAppointmentForm(){ const m = document.getElementById('create-appointment-modal'); if (m) m.style.display='none'; const form = document.getElementById('create-appointment-form'); if (form){ form.reset(); const msg = document.getElementById('create-appointment-message'); if (msg){ clearFormMessage(msg); } const btn = form.querySelector('button[type="submit"]'); if (btn) btn.disabled = false; } }

  UI.formatDate = formatDate;
  UI.setFormMessage = setFormMessage;
  UI.clearFormMessage = clearFormMessage;
  UI.showCreateAppointmentForm = showCreateAppointmentForm;
  UI.hideCreateAppointmentForm = hideCreateAppointmentForm;

  window.PatientComponents = window.PatientComponents || {};
  window.PatientComponents.UI = UI;
})(window);
