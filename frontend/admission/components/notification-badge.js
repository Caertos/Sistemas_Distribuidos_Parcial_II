/* notification-badge.js */
(function(){
    class NotificationBadge {
        constructor(rootId, pollInterval=30000){
            this.root = document.getElementById(rootId);
            this.interval = pollInterval;
            this.count = 0;
            this.token = window.auth && window.auth.getStoredToken && window.auth.unwrapFHIR ? window.auth.unwrapFHIR(window.auth.getStoredToken()) : null;
            this.render();
            this.start();
        }

        render(){
            if(!this.root) return;
            this.root.innerHTML = `<div class="pending-badge"><i class="bi bi-bell fs-4"></i> <span id="pending-count" class="badge bg-danger d-none">0</span></div>`;
        }

        updateCount(n){
            this.count = n||0;
            const el = document.getElementById('pending-count');
            if(!el) return;
            if(this.count>0){ el.classList.remove('d-none'); el.textContent = String(this.count); this.flash(); }
            else { el.classList.add('d-none'); }
        }

        async poll(){
            const t = this.token; if(!t) return;
            try{
                const r = await fetch('/api/patient/admissions/pending',{headers:{'Authorization':`Bearer ${t}`},credentials:'include'});
                if(r.status===401) return window.location.href='/login';
                const rows = await r.json();
                this.updateCount(Array.isArray(rows)?rows.length:0);
            }catch(e){ console.error('notif poll',e); }
        }

        start(){ this.poll(); this._timer = setInterval(()=>this.poll(), this.interval); }

        stop(){ clearInterval(this._timer); }

        flash(){
            try{ const a = new Audio(); /* silent by default; user agent may block */ }catch(e){}
        }
    }

    window.AdmissionComponents = window.AdmissionComponents || {};
    window.AdmissionComponents.NotificationBadge = NotificationBadge;
})();
