(function(window){
  const Profile = {};
  const Api = () => (window.PatientComponents && window.PatientComponents.Api) ? window.PatientComponents.Api : null;
  const UI = () => (window.PatientComponents && window.PatientComponents.UI) ? window.PatientComponents.UI : null;

  async function loadProfile(){
    const api = Api(); const ui = UI(); if(!api) return;
    try{
      const data = await api.fetchAPI('/api/patient/me');
      const el = document.getElementById('profile-content'); if(!el) return;
      let html = '<dl style="line-height:1.8">'; html += `<dt>Nombre</dt><dd>${data.nombre||data.full_name||data.username||'—'}</dd>`;
      if(data.documento) html += `<dt>Documento</dt><dd>${data.documento}</dd>`;
      if(data.email) html += `<dt>Email</dt><dd>${data.email}</dd>`;
      if(data.telefono) html += `<dt>Teléfono</dt><dd>${data.telefono}</dd>`;
      html += '</dl>'; el.innerHTML = html;
      const su = document.getElementById('sidebar-username'); if(su) su.textContent = data.nombre||data.username||'Paciente';

      const changeForm = document.createElement('div');
      changeForm.innerHTML = `\n        <h3 style="margin-top:1rem;">Cambiar contraseña</h3>\n        <form id="change-password-form">\n          <div style="margin-bottom:0.5rem;"><label>Contraseña actual</label><input type="password" name="old_password" required style="width:100%; padding:0.4rem; border:1px solid #ccc; border-radius:4px;"></div>\n          <div style="margin-bottom:0.5rem;"><label>Nueva contraseña</label><input type="password" name="new_password" required minlength="6" style="width:100%; padding:0.4rem; border:1px solid #ccc; border-radius:4px;"></div>\n          <div><button class="btn-primary" type="submit">Cambiar contraseña</button></div>\n        </form>\n      `;
      el.appendChild(changeForm);
      const cpf = document.getElementById('change-password-form');
      if(cpf){ cpf.addEventListener('submit', async function(e){ e.preventDefault(); const fd = new FormData(cpf); try{ const token = (window.Auth && typeof window.Auth.getToken === 'function')? window.Auth.getToken() : null; const resp = await fetch('/api/auth/change-password',{ method:'POST', headers: Object.assign({'Content-Type':'application/json'}, token ? {'Authorization': `Bearer ${token}`} : {}), body: JSON.stringify({ old_password: fd.get('old_password'), new_password: fd.get('new_password') }) }); if(!resp.ok){ const err = await resp.json().catch(()=>({detail:'Error cambiando contraseña'})); throw new Error(err.detail || 'Error'); } api.setGlobalMessage('success','Contraseña cambiada correctamente'); cpf.reset(); }catch(err){ api.setGlobalMessage('error','Error: '+(err && err.message? err.message : String(err))); } }); }
    }catch(e){ const el = document.getElementById('profile-content'); if(el) el.innerHTML = `<p style="color:red;">Error: ${e.message}</p>` }
  }

  Profile.loadProfile = loadProfile;
  window.PatientComponents = window.PatientComponents || {};
  window.PatientComponents.Profile = Profile;
})(window);
