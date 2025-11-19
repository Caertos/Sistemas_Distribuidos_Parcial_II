// login.js - lógica de envío del formulario de login y manejo de respuesta

function showElement(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('d-none');
}

function hideElement(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('d-none');
}

function showError(message) {
    hideElement('loading-alert');
    hideElement('success-alert');
    const el = document.getElementById('error-alert');
    const msg = document.getElementById('error-message');
    if (msg) msg.textContent = message;
    if (el) el.classList.remove('d-none');
}

function showSuccess(message) {
    hideElement('loading-alert');
    hideElement('error-alert');
    const el = document.getElementById('success-alert');
    const msg = document.getElementById('success-message');
    if (msg) msg.textContent = message;
    if (el) el.classList.remove('d-none');
}

function showLoading(message='Iniciando sesión...') {
    hideElement('error-alert');
    hideElement('success-alert');
    const el = document.getElementById('loading-alert');
    const msg = document.getElementById('loading-message');
    if (msg) msg.textContent = message;
    if (el) el.classList.remove('d-none');
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    const btn = document.querySelector('.btn-login');
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showError('Por favor ingrese usuario y contraseña');
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Iniciando sesión...';
    }

    showLoading();

    try {
        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password}),
            credentials: 'include'
        });

        if (!resp.ok) {
            const err = await resp.json().catch(()=>null);
            const msg = err?.detail || err?.message || 'Credenciales inválidas';
            throw new Error(msg);
        }

        const data = await resp.json();
        const accessToken = data.access_token;
        const refreshToken = data.refresh_token;
        const role = data.role || data.user_type;
        const uname = data.username || username;

        if (!accessToken) throw new Error('No se recibió token del servidor');

        // Guardar tokens/usuario
        try { localStorage.setItem('authToken', accessToken); } catch(e){}
        try { localStorage.setItem('role', role || ''); } catch(e){}
        try { localStorage.setItem('username', uname); } catch(e){}
        if (refreshToken) try { localStorage.setItem('refreshToken', refreshToken); } catch(e){}

        // Guardar wrapper FHIR- para compatibilidad
        try {
            const fhir = window.auth.wrapFHIR(accessToken);
            try { localStorage.setItem('auth_token', fhir); } catch(e){}
            document.cookie = 'auth_token=' + encodeURIComponent(fhir) + '; path=/; SameSite=Lax';
        } catch (e) {
            try { localStorage.setItem('auth_token', accessToken); } catch(e){}
            document.cookie = 'auth_token=' + encodeURIComponent(accessToken) + '; path=/; SameSite=Lax';
        }

        // Redirección según rol
        const roleLower = (role || '').toString().toLowerCase();
        let route = (roleLower === 'patient' || roleLower === 'paciente') ? '/patient'
                : (roleLower === 'practitioner' || roleLower === 'medic' || roleLower === 'medico' || roleLower === 'doctor') ? '/medic'
                : (roleLower === 'admin' || roleLower === 'administrador') ? '/admin'
                : (roleLower === 'auditor') ? '/admin'
                // Personal de Admisión / enfermería
                : (roleLower === 'admission' || roleLower === 'admisión' || roleLower === 'enfermera' || roleLower === 'enfermero' || roleLower === 'nurse') ? '/admission/'
                : '/dashboard';

        showSuccess('Inicio de sesión correcto. Redirigiendo...');

        // Si la ruta objetivo es /admission/ y el origen actual no sirve esa ruta,
        // intentar redirigir al puerto 30080 del mismo host (donde suele estar el nginx frontend).
        if (route === '/admission/') {
            try {
                // Algunos servidores no permiten HEAD y responden 405; usar GET y comprobar status.
                const respCheck = await fetch(route, { method: 'GET', credentials: 'include', redirect: 'manual' });
                // Si el recurso responde 2xx/3xx lo consideramos disponible
                if (respCheck && respCheck.status >= 200 && respCheck.status < 400) {
                    setTimeout(()=> window.location.href = route, 700);
                } else {
                    const alt = `${window.location.protocol}//${window.location.hostname}:30080/admission/`;
                    setTimeout(()=> window.location.href = alt, 700);
                }
            } catch (e) {
                const alt = `${window.location.protocol}//${window.location.hostname}:30080/admission/`;
                setTimeout(()=> window.location.href = alt, 700);
            }
        } else {
            setTimeout(()=> window.location.href = route, 700);
        }

    } catch (err) {
        console.error('Login error:', err);
        showError(err.message || 'Error al iniciar sesión');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>Iniciar Sesión';
        }
    }
}

function setupDemoUsers() {
    document.querySelectorAll('.user-card').forEach(card => {
        card.addEventListener('click', function() {
            const username = this.dataset.username;
            const password = this.dataset.password;
            if (username && password) {
                document.getElementById('username').value = username;
                document.getElementById('password').value = password;
                const btn = document.querySelector('.btn-login');
                if (btn) btn.focus();
            }
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('loginForm');
    if (form) form.addEventListener('submit', handleLoginSubmit);
    setupDemoUsers();
    const usernameField = document.getElementById('username');
    if (usernameField) usernameField.focus();
});
