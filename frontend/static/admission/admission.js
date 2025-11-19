/* admission.js (static copy) */
(function(){
    class AdmissionApp {
        constructor(){
            this.components = {};
            document.addEventListener('DOMContentLoaded', ()=>this.init());
        }

        init(){
            if(!window.auth || !window.auth.getStoredToken){
                console.warn('auth helper missing');
            }
            this.setupNav();
            this.showLoading(true);
            this.loadUser()
                .then(()=>{
                    this.mountComponents();
                    this.showLoading(false);
                })
                .catch(err=>{
                    console.error(err);
                    // Mostrar aviso y ofrecer enlace al login en lugar de redirigir automáticamente.
                    // Esto evita bucles de redirección en entornos donde el token no está presente
                    // o el frontend y backend manejan el token de forma distinta.
                    const msg = document.createElement('div');
                    msg.className = 'alert alert-warning';
                    msg.innerHTML = `No autorizado. <a href="/login">Iniciar sesión</a> para acceder al módulo de Admisión.`;
                    const container = document.getElementById('admission-content');
                    if(container){
                        container.classList.remove('d-none');
                        container.innerHTML = '';
                        container.appendChild(msg);
                    } else {
                        this.showError('No autorizado. Por favor inicie sesión.');
                    }
                });
        }

        setupNav(){
            document.querySelectorAll('.sidebar-nav .nav-link').forEach(btn=>{
                btn.addEventListener('click', ()=>{
                    document.querySelectorAll('.sidebar-nav .nav-link').forEach(b=>b.classList.remove('active'));
                    btn.classList.add('active');
                    const section = btn.getAttribute('data-section');
                    this.showSection(section);
                });
            });
        }

        showSection(name){
            document.querySelectorAll('.content-section').forEach(s=>s.classList.add('d-none'));
            const target = document.getElementById(`section-${name}`);
            if(target) target.classList.remove('d-none');
        }

        async loadUser(){
            const token = window.auth.getStoredToken();
            if(!token) throw new Error('no token');
            const raw = window.auth.unwrapFHIR ? window.auth.unwrapFHIR(token) : token;
            const r = await fetch('/api/patient/me',{headers:{'Authorization':`Bearer ${raw}`},credentials:'include'});
            if(r.status===401) throw new Error('unauth');
            const data = await r.json();
            const patientName = data.full_name || data.username || 'Usuario';
            document.getElementById('user-name').textContent = patientName;
        }

        mountComponents(){
            // Montar solo los componentes requeridos: badge y lista de pendientes.
            this.components.notification = new window.AdmissionComponents.NotificationBadge('pending-badge-placeholder');
            this.components.appointments = new window.AdmissionComponents.AppointmentList('appointment-root', this.components.notification);

            document.getElementById('admission-content').classList.remove('d-none');
            this.showSection('appointments');
        }

        showLoading(on){
            const l = document.getElementById('loading-state');
            if(!l) return;
            if(on) { l.style.display='flex'; } else { l.style.display='none'; }
        }

        showError(msg){
            alert(msg);
        }
    }

    window.logout = function(){
        try{ localStorage.removeItem('auth_token'); localStorage.removeItem('authToken'); }catch(e){}
        document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        window.location.href = '/login';
    };

    window.admissionApp = new AdmissionApp();
})();
