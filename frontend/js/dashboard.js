/* Lógica común de dashboards
   - Verifica role esperado y realiza fetch a endpoints por role
   - Rellena elementos con data-bind (data-field) en la página
   - En modo preview (sin backend) coloca datos de ejemplo
*/
(function(window){
  const SAMPLE = {
    metrics: { users: 5, servers: 2, assigned: 24, appointments_today: 8 },
    next_appointment: '2025-11-20',
    status: 'Estable',
  };

  function getDataEndpointForRole(role){
    // Mapear role a endpoint REST que provea datos para el dashboard
    role = (role||'').toLowerCase();
    if(role.includes('admin')) return '/api/admin/monitor/metrics';
    if(role.includes('practitioner')||role.includes('medic')||role.includes('médico')) return '/api/practitioner/appointments';
    if(role.includes('patient')||role.includes('paciente')) return '/api/patient/me/summary';
    return '/api/dashboard/overview';
  }

  async function fetchOverview(role){
    const ep = getDataEndpointForRole(role);
    try{
      const token = window.Auth && Auth.getToken && Auth.getToken();
      const headers = token ? { 'Authorization': 'Bearer ' + token } : {};
      const res = await fetch(ep, { headers, credentials: 'include' });
      if(!res.ok) throw new Error('no-data');
      return await res.json();
    }catch(e){
      // no backend o error: devolver sample
      console.info('Usando datos de preview por falta de backend o error:', e);
      return SAMPLE;
    }
  }

  function fillFields(payload){
    // buscar elementos con data-field y asignar valores
    document.querySelectorAll('[data-field]').forEach(el=>{
      const key = el.getAttribute('data-field');
      // soporta keys anidados con punto
      const val = key.split('.').reduce((acc,k)=> acc && acc[k]!==undefined ? acc[k] : null, payload);
      el.textContent = (val===null || val===undefined) ? '—' : val;
    });
  }

  async function init(){
    // window.EXPECTED_ROLE debe ser establecido por la plantilla antes de incluir este script
    const expected = window.EXPECTED_ROLE || null;
    const auth = window.Auth;
    if(!auth){ console.error('Auth no cargado'); return; }

    // intenta requerir el role; si preview:true permitimos continuar
    const res = await auth.requireRole(expected, { preview: true });
    if(!res) return; // redirigido o error
    const role = res.role || expected || auth.getRole();

    const data = await fetchOverview(role);
    // rellenar campos comunes
    fillFields({ metrics: data.metrics || data, next_appointment: data.next_appointment || data.nextAppointment, status: data.status || '' });

    // opcional: mostrar banner de preview
    if(res.preview){
      const b = document.createElement('div');
      b.className = 'preview-banner';
      b.textContent = 'Vista previa local (sin backend). Algunas funciones pueden no estar disponibles.';
      document.body.insertBefore(b, document.body.firstChild);
    }
  }

  document.addEventListener('DOMContentLoaded', init);

  window.Dashboard = { init, fetchOverview, fillFields };

})(window);
