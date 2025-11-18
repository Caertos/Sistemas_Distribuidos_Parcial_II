(function(window){
  // API utilities: fetch wrapper y notificaciones globales
  const Api = {};

  async function fetchAPI(endpoint, options = {}){
    const token = (window.Auth && typeof window.Auth.getToken === 'function') ? window.Auth.getToken() : null;
    const headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(endpoint, Object.assign({}, options, { headers, credentials: 'include' }));
    if (!resp.ok) {
      const err = await resp.json().catch(()=>({ detail: 'Error en la petición' }));
      throw new Error(err && err.detail ? err.detail : `Error ${resp.status}`);
    }
    return resp.json().catch(()=>null);
  }

  function setGlobalMessage(type, text, timeout = 4000){
    const el = document.getElementById('patient-global-message');
    if (!el) return; // en caso de no existir, no hacemos nada
    el.style.display = 'block';
    el.textContent = text;
    el.className = ''; el.classList.add('message');
    if (type === 'error') el.classList.add('error'); else el.classList.add('success');
    clearTimeout(el._hideTimer);
    if (timeout > 0) el._hideTimer = setTimeout(()=>{ try{ el.style.display='none'; el.textContent=''; el.className=''; }catch(e){} }, timeout);
  }

  function clearGlobalMessage(){ const el = document.getElementById('patient-global-message'); if(!el) return; el.style.display='none'; el.textContent=''; el.className=''; }

  Api.fetchAPI = fetchAPI;
  Api.setGlobalMessage = setGlobalMessage;
  Api.clearGlobalMessage = clearGlobalMessage;

  window.PatientComponents = window.PatientComponents || {};
  window.PatientComponents.Api = Api;
})(window);
