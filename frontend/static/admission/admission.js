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
                    this.showError('No autorizado. Redirigiendo al login...');
                    setTimeout(()=>window.location.href='/login',1200);
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
            // Montar solo los componentes requeridos: badge, lista de pendientes y admisión urgente
            this.components.notification = new window.AdmissionComponents.NotificationBadge('pending-badge-placeholder');
            this.components.appointments = new window.AdmissionComponents.AppointmentList('appointment-root', this.components.notification);
            this.components.emergency = new window.AdmissionComponents.EmergencyAdmission('emergency-root', this.components.appointments);

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
