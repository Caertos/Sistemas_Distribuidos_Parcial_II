// JS específico para admin - gestión de usuarios, infraestructura y auditoría
(function(window){
  const Auth = window.Auth;

  async function fetchAPI(endpoint, options = {}) {
    const token = Auth && Auth.getToken ? Auth.getToken() : null;
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers
    };
    
    const response = await fetch(endpoint, { ...options, headers, credentials: 'include' });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Error en la petición' }));
      throw new Error(error.detail || `Error ${response.status}`);
    }
    return response.json();
  }

  async function loadUsers() {
    try {
      const users = await fetchAPI('/api/admin/users');
      document.getElementById('users-section').style.display = 'block';
      
      const table = document.getElementById('users-table');
      if (!users || users.length === 0) {
        table.innerHTML = '<p>No hay usuarios registrados.</p>';
        return;
      }
      
      let html = '<table style="width:100%; border-collapse:collapse;"><thead><tr>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Username</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Email</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Nombre</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Tipo</th>';
      html += '<th style="border-bottom:2px solid #ddd; padding:0.5rem; text-align:left;">Acciones</th>';
      html += '</tr></thead><tbody>';
      
      users.forEach(u => {
        html += '<tr>';
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">${u.username || '—'}</td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">${u.email || '—'}</td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">${u.full_name || '—'}</td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">${u.user_type || '—'}</td>`;
        html += `<td style="border-bottom:1px solid #eee; padding:0.5rem;">`;
        html += `<button onclick="AdminDashboard.deleteUser('${u.id}')" style="padding:0.25rem 0.5rem; background:#dc3545; color:white; border:none; border-radius:4px; cursor:pointer;">Eliminar</button>`;
        html += `</td>`;
        html += '</tr>';
      });
      
      html += '</tbody></table>';
      table.innerHTML = html;
    } catch (error) {
      console.error('Error cargando usuarios:', error);
      alert('Error cargando usuarios: ' + error.message);
    }
  }

  async function createUser(formData) {
    try {
      const payload = {
        username: formData.get('username'),
        email: formData.get('email'),
        full_name: formData.get('full_name') || null,
        password: formData.get('password'),
        user_type: formData.get('user_type'),
        is_superuser: formData.get('is_superuser') === 'on'
      };
      
      await fetchAPI('/api/admin/users', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      
      alert('Usuario creado exitosamente');
      hideCreateUserForm();
      loadUsers();
    } catch (error) {
      console.error('Error creando usuario:', error);
      alert('Error creando usuario: ' + error.message);
    }
  }

  async function deleteUser(userId) {
    if (!confirm('¿Estás seguro de eliminar este usuario?')) return;
    
    try {
      await fetchAPI(`/api/admin/users/${userId}`, { method: 'DELETE' });
      alert('Usuario eliminado');
      loadUsers();
    } catch (error) {
      console.error('Error eliminando usuario:', error);
      alert('Error eliminando usuario: ' + error.message);
    }
  }

  function showCreateUserForm() {
    document.getElementById('create-user-modal').style.display = 'block';
  }

  function hideCreateUserForm() {
    document.getElementById('create-user-modal').style.display = 'none';
    document.getElementById('create-user-form').reset();
  }

  function showInfraPanel() {
    alert('Panel de infraestructura (deploy/stop/rebuild) - próximamente implementado');
  }

  async function loadAuditLogs() {
    try {
      const logs = await fetchAPI('/api/admin/monitor/audit?limit=50');
      alert(`Se encontraron ${logs.count || 0} registros de auditoría (vista detallada próximamente)`);
    } catch (error) {
      console.error('Error cargando logs:', error);
      alert('Error cargando logs de auditoría: ' + error.message);
    }
  }

  // Event listeners
  document.addEventListener('DOMContentLoaded', function(){
    console.log('Admin dashboard loaded');
    
    // Form submit handler
    const form = document.getElementById('create-user-form');
    if (form) {
      form.addEventListener('submit', function(e) {
        e.preventDefault();
        createUser(new FormData(form));
      });
    }
  });

  // Exponer funciones globalmente
  window.AdminDashboard = {
    loadUsers,
    createUser,
    deleteUser,
    showCreateUserForm,
    hideCreateUserForm,
    showInfraPanel,
    loadAuditLogs
  };

})(window);
