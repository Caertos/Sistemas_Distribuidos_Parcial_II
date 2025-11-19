/**
 * Admin Users Management - JavaScript
 * Sistema FHIR - Gestión de Usuarios
 */

let currentUsers = [];
let filteredUsers = [];
let currentPage = 1;
const usersPerPage = 10;
let userToDelete = null;
let userToEditRole = null;

// =====================================================
// Token Synchronization
// =====================================================
(function() {
    function getCookieImmediate(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    const cookieToken = getCookieImmediate('authToken');
    if (cookieToken && !localStorage.getItem('authToken')) {
        const cleanToken = cookieToken.startsWith('FHIR-') ? cookieToken.substring(5) : cookieToken;
        localStorage.setItem('authToken', cleanToken);
    }
})();

// =====================================================
// Initialize
// =====================================================
document.addEventListener('DOMContentLoaded', function() {
    loadUsername();
    loadUsers();
    setupEventListeners();
});

// =====================================================
// Setup Event Listeners
// =====================================================
function setupEventListeners() {
    // Search input
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }
    
    // Role filter
    const filterRole = document.getElementById('filterRole');
    if (filterRole) {
        filterRole.addEventListener('change', applyFilters);
    }
    
    // Delete modal
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', confirmDelete);
    }
    
    // Role modal
    const confirmRoleBtn = document.getElementById('confirmRoleBtn');
    if (confirmRoleBtn) {
        confirmRoleBtn.addEventListener('click', confirmRoleChange);
    }
}

// =====================================================
// Load Users
// =====================================================
async function loadUsers() {
    const token = getAuthToken();
    
    if (!token) {
        window.location.href = '/login';
        return;
    }
    
    try {
        const response = await fetch('/api/admin/users?limit=1000', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                window.location.href = '/login';
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        currentUsers = await response.json();
        filteredUsers = [...currentUsers];
        displayUsers();
        
    } catch (error) {
        console.error('Error loading users:', error);
        showError('Error al cargar los usuarios');
        document.getElementById('usersTableBody').innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Error al cargar los usuarios
                </td>
            </tr>
        `;
    }
}

// =====================================================
// Display Users
// =====================================================
function displayUsers() {
    const tbody = document.getElementById('usersTableBody');
    
    if (filteredUsers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    <i class="bi bi-inbox me-2"></i>
                    No se encontraron usuarios
                </td>
            </tr>
        `;
        document.getElementById('paginationContainer').style.display = 'none';
        return;
    }
    
    // Calculate pagination
    const totalPages = Math.ceil(filteredUsers.length / usersPerPage);
    const startIndex = (currentPage - 1) * usersPerPage;
    const endIndex = startIndex + usersPerPage;
    const usersToShow = filteredUsers.slice(startIndex, endIndex);
    
    // Build table rows
    tbody.innerHTML = usersToShow.map(user => `
        <tr>
            <td>
                <i class="bi bi-person-circle me-2"></i>
                <strong>${escapeHtml(user.username)}</strong>
            </td>
            <td>${escapeHtml(user.email)}</td>
            <td>${escapeHtml(user.full_name)}</td>
            <td>
                <span class="badge bg-${getRoleBadgeColor(user.user_type)}">
                    ${getRoleLabel(user.user_type)}
                </span>
            </td>
            <td>
                ${user.is_superuser 
                    ? '<span class="badge bg-danger"><i class="bi bi-shield-fill-check me-1"></i>Sí</span>' 
                    : '<span class="badge bg-secondary">No</span>'}
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary" 
                            onclick="editUser('${user.id}')" title="Editar">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button type="button" class="btn btn-outline-info" 
                            onclick="openRoleModal('${user.id}', '${escapeHtml(user.username)}', '${user.user_type}', ${user.is_superuser})" 
                            title="Asignar Rol">
                        <i class="bi bi-shield-check"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger" 
                            onclick="openDeleteModal('${user.id}', '${escapeHtml(user.username)}')" 
                            title="Eliminar">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    // Show pagination if needed
    if (totalPages > 1) {
        displayPagination(totalPages);
    } else {
        document.getElementById('paginationContainer').style.display = 'none';
    }
}

// =====================================================
// Display Pagination
// =====================================================
function displayPagination(totalPages) {
    const pagination = document.getElementById('pagination');
    const container = document.getElementById('paginationContainer');
    
    container.style.display = 'block';
    
    let html = '';
    
    // Previous button
    html += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1}); return false;">
                <i class="bi bi-chevron-left"></i>
            </a>
        </li>
    `;
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="changePage(${i}); return false;">${i}</a>
                </li>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }
    
    // Next button
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1}); return false;">
                <i class="bi bi-chevron-right"></i>
            </a>
        </li>
    `;
    
    pagination.innerHTML = html;
}

// =====================================================
// Change Page
// =====================================================
function changePage(page) {
    const totalPages = Math.ceil(filteredUsers.length / usersPerPage);
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        displayUsers();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// =====================================================
// Apply Filters
// =====================================================
function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const roleFilter = document.getElementById('filterRole').value;
    
    filteredUsers = currentUsers.filter(user => {
        const matchesSearch = !searchTerm || 
            user.username.toLowerCase().includes(searchTerm) ||
            user.email.toLowerCase().includes(searchTerm) ||
            user.full_name.toLowerCase().includes(searchTerm);
        
        const matchesRole = !roleFilter || user.user_type === roleFilter;
        
        return matchesSearch && matchesRole;
    });
    
    currentPage = 1;
    displayUsers();
}

// =====================================================
// Clear Filters
// =====================================================
function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('filterRole').value = '';
    applyFilters();
}

// =====================================================
// Edit User
// =====================================================
function editUser(userId) {
    window.location.href = `/admin/users/${userId}/edit`;
}

// =====================================================
// Open Delete Modal
// =====================================================
function openDeleteModal(userId, username) {
    userToDelete = userId;
    document.getElementById('deleteUserName').textContent = username;
    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

// =====================================================
// Confirm Delete
// =====================================================
async function confirmDelete() {
    if (!userToDelete) return;
    
    const token = getAuthToken();
    const modal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
    
    try {
        const response = await fetch(`/api/admin/users/${userToDelete}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        showSuccess('Usuario eliminado exitosamente');
        modal.hide();
        userToDelete = null;
        
        // Reload users
        await loadUsers();
        
    } catch (error) {
        console.error('Error deleting user:', error);
        showError('Error al eliminar el usuario');
    }
}

// =====================================================
// Open Role Modal
// =====================================================
function openRoleModal(userId, username, currentRole, isSuperuser) {
    userToEditRole = userId;
    document.getElementById('roleUserName').textContent = username;
    document.getElementById('newRole').value = currentRole;
    document.getElementById('newSuperuser').checked = isSuperuser;
    
    const modal = new bootstrap.Modal(document.getElementById('roleModal'));
    modal.show();
}

// =====================================================
// Confirm Role Change
// =====================================================
async function confirmRoleChange() {
    if (!userToEditRole) return;
    
    const token = getAuthToken();
    const newRole = document.getElementById('newRole').value;
    const isSuperuser = document.getElementById('newSuperuser').checked;
    const modal = bootstrap.Modal.getInstance(document.getElementById('roleModal'));
    
    try {
        const response = await fetch(`/api/admin/users/${userToEditRole}/role`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                role: newRole,
                is_superuser: isSuperuser
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        showSuccess('Rol asignado exitosamente');
        modal.hide();
        userToEditRole = null;
        
        // Reload users
        await loadUsers();
        
    } catch (error) {
        console.error('Error assigning role:', error);
        showError('Error al asignar el rol');
    }
}

// =====================================================
// Helper Functions
// =====================================================
function getAuthToken() {
    let token = localStorage.getItem('authToken');
    if (!token) {
        token = getCookie('authToken');
    }
    if (token && token.startsWith('FHIR-')) {
        token = token.substring(5);
    }
    return token;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function loadUsername() {
    const token = getAuthToken();
    if (token) {
        try {
            const parts = token.split('.');
            if (parts.length === 3) {
                const payload = parts[1];
                const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
                const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                }).join(''));
                const tokenData = JSON.parse(jsonPayload);
                
                if (tokenData.username) {
                    document.getElementById('navbar-username').textContent = tokenData.username;
                }
            }
        } catch (e) {
            console.log('Could not parse user token:', e);
        }
    }
}

function logout() {
    localStorage.removeItem('authToken');
    document.cookie = 'authToken=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    window.location.href = '/login';
}

function getRoleBadgeColor(role) {
    const colors = {
        'admin': 'danger',
        'practitioner': 'primary',
        'patient': 'success',
        'auditor': 'warning',
        'admission': 'info'
    };
    return colors[role] || 'secondary';
}

function getRoleLabel(role) {
    const labels = {
        'admin': 'Administrador',
        'practitioner': 'Médico',
        'patient': 'Paciente',
        'auditor': 'Auditor',
        'admission': 'Admisión'
    };
    return labels[role] || role;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function showError(message) {
    const errorElement = document.createElement('div');
    errorElement.className = 'alert alert-danger alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    errorElement.style.zIndex = '9999';
    errorElement.style.maxWidth = '500px';
    errorElement.innerHTML = `
        <i class="bi bi-exclamation-triangle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(errorElement);
    
    setTimeout(() => {
        errorElement.remove();
    }, 5000);
}

function showSuccess(message) {
    const successElement = document.createElement('div');
    successElement.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    successElement.style.zIndex = '9999';
    successElement.style.maxWidth = '500px';
    successElement.innerHTML = `
        <i class="bi bi-check-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(successElement);
    
    setTimeout(() => {
        successElement.remove();
    }, 5000);
}
