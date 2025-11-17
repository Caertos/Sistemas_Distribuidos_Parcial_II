/* Helpers de autenticación para el frontend (cliente)
   - Almacena token en localStorage
   - Provee login(), logout(), getToken(), getUser(), requireRole()
   - Intenta consultar /api/auth/me cuando sea necesario
*/
(function(window){
  const STORAGE_KEY = 'app_auth';

  function save(data){
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data || {}));
  }

  function load(){
    try{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch(e){ return {}; }
  }

  function clear(){
    localStorage.removeItem(STORAGE_KEY);
  }

  function getToken(){
    return load().access_token || null;
  }

  function getRole(){
    return load().role || null;
  }

  function setUserData(obj){
    const prev = load();
    save(Object.assign({}, prev, obj));
  }

  async function login(endpoint, payload){
    // endpoint: '/api/auth/login' por defecto
    endpoint = endpoint || '/api/auth/login';
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'include'
    });

    if(!res.ok){
      const j = await res.json().catch(()=>({detail:'Error de autenticación'}));
      throw j;
    }

    const data = await res.json();
    // Esperamos: { access_token, token_type, role, refresh_token }
    // Extraer role del nivel superior o de user.role si viene anidado
    const role = data.role || (data.user && data.user.role) || null;
    setUserData({ 
      access_token: data.access_token, 
      token_type: data.token_type || 'bearer',
      refresh_token: data.refresh_token,
      role: role,
      user: data.user || {}
    });
    return data;
  }

  async function fetchMe(endpoint){
    endpoint = endpoint || '/api/auth/me';
    const token = getToken();
    try{
      const res = await fetch(endpoint, {
        headers: token ? { 'Authorization': 'Bearer ' + token } : {},
        credentials: 'include'
      });
      if(!res.ok) return null;
      const j = await res.json();
      setUserData(j);
      return j;
    }catch(e){
      return null;
    }
  }

  function logout(){
    clear();
    // opcional: si hay endpoint de logout llamarlo
    try{ window.location.href = '/login.html'; }catch(e){}
  }

  // Requiere que el usuario tenga el role esperado; si no, redirige al login.
  // Si no hay token intenta consultar /api/auth/me; en build estático puede fallar,
  // en cuyo caso hay una devolución 'preview' y no se forzará la salida (pero se avisa).
  async function requireRole(expectedRole, opts){
    opts = opts || {};
    const token = getToken();
    let userRole = getRole();
    if(!userRole){
      // intentar consultarlo al backend
      const me = await fetchMe();
      if(me && me.role) userRole = me.role;
    }

    if(!userRole){
      // No hay role conocido: redirigir al login (o mostrar preview si opts.preview)
      if(opts.preview){
        // permitir continuar en modo preview
        console.info('Preview mode: no hay sesión activa');
        return { preview: true };
      }
      window.location.href = '/login.html';
      return null;
    }

    if(expectedRole && expectedRole !== userRole){
      // rol no autorizado
      alert('No tienes permisos para ver esta página.');
      // redirigir al dashboard correspondiente a su role
      const redirect = roleToPage(userRole) || '/dashboard';
      window.location.href = redirect;
      return null;
    }

    return { role: userRole, preview: false };
  }

  function roleToPage(role){
    if(!role) return '/dashboard';
    role = role.toLowerCase();
    if(role.includes('admin')) return '/admin.html';
    if(role.includes('medic') || role.includes('médico') || role.includes('doctor')) return '/medic.html';
    if(role.includes('patient') || role.includes('paciente')) return '/patient.html';
    return '/dashboard.html';
  }

  window.Auth = Object.freeze({
    save, load, clear, getToken, getRole, setUserData, login, fetchMe, requireRole, logout, roleToPage
  });

})(window);
