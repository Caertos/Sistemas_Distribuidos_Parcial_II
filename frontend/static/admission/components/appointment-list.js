/* appointment-list.js (static copy) */
(function(){
    class AppointmentList {
        constructor(rootId, notifier){
            this.root = document.getElementById(rootId);
            this.notifier = notifier;
            this.token = window.auth && window.auth.getStoredToken && window.auth.unwrapFHIR ? window.auth.unwrapFHIR(window.auth.getStoredToken()) : null;
            this.render();
            this.loadPending();
        }

        render(){
            this.root.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center"><h5 class="mb-0">Solicitudes pendientes</h5><div><button id="refreshPending" class="btn btn-sm btn-outline-primary"><i class="bi bi-arrow-clockwise"></i> Actualizar</button></div></div>
                <div class="card-body"><div id="pending-table"></div></div>
            </div>`;
            this.root.querySelector('#refreshPending').addEventListener('click', ()=>this.loadPending());
        }

        async loadPending(){
            const t = this.token; if(!t) return window.location.href='/login';
            try{
                const r = await fetch('/api/patient/admissions/pending',{headers:{'Authorization':`Bearer ${t}`},credentials:'include'});
                if(r.status===401) return window.location.href='/login';
                const rows = await r.json();
                this.renderTable(rows||[]);
                if(this.notifier && this.notifier.updateCount) this.notifier.updateCount(rows.length);
            }catch(e){ console.error('loadPending',e); }
        }

        renderTable(rows){
            const container = this.root.querySelector('#pending-table');
            if(!Array.isArray(rows) || rows.length===0){ container.innerHTML = '<div class="text-muted">No hay solicitudes pendientes</div>'; return; }
            let html = `<div class="table-responsive"><table class="table"><thead><tr><th>Admission ID</th><th>Paciente</th><th>Fecha/Hora</th><th>Motivo</th><th></th></tr></thead><tbody>`;
            rows.forEach(r=>{
                const aid = r.admission_id || r.cita_id || '';
                const paciente = r.nombre_paciente || r.paciente || r.documento || (r.paciente_nombre || '—');
                const fecha = r.fecha_hora || r.fecha_admision || r.fecha || '';
                html += `<tr data-admission="${aid}"><td>${aid}</td><td>${paciente}</td><td>${fecha}</td><td>${r.motivo_consulta||r.motivo||'—'}</td><td><div class="btn-group"><button class="btn btn-sm btn-success btn-accept">Aceptar</button><button class="btn btn-sm btn-danger btn-reject">Rechazar</button></div></td></tr>`;
            });
            html += '</tbody></table></div>';
            container.innerHTML = html;
            container.querySelectorAll('.btn-accept').forEach(b=>b.addEventListener('click', (ev)=>this.accept(ev)));
            container.querySelectorAll('.btn-reject').forEach(b=>b.addEventListener('click', (ev)=>this.reject(ev)));
        }

        async accept(ev){
            const tr = ev.target.closest('tr'); const aid = tr.getAttribute('data-admission');
            if(!confirm('Confirmar aceptación de admisión '+aid+'?')) return;
            const t = this.token; try{
                const r = await fetch(`/api/patient/admissions/${encodeURIComponent(aid)}/admit`,{method:'POST',headers:{'Authorization':`Bearer ${t}`},credentials:'include'});
                if(r.ok){ this.showAlert('Admisión marcada como admitida','success'); this.loadPending(); }
                else { const txt = await r.text(); this.showAlert('Error: '+r.status+' '+txt,'danger'); if(r.status===401) window.location.href='/login'; }
            }catch(e){ console.error(e); }
        }

        async reject(ev){
            const tr = ev.target.closest('tr'); const aid = tr.getAttribute('data-admission');
            if(!confirm('Rechazar/editar admisión '+aid+'? (se usará discharge con nota)')) return;
            const reason = prompt('Motivo del rechazo (opcional):','Rechazado por admisión');
            const t = this.token; try{
                const url = `/api/patient/admissions/${encodeURIComponent(aid)}/discharge` + (reason?`?notas=${encodeURIComponent(reason)}`:'');
                const r = await fetch(url,{method:'POST',headers:{'Authorization':`Bearer ${t}`},credentials:'include'});
                if(r.ok){ this.showAlert('Admisión marcada como atendida/rechazada','warning'); this.loadPending(); }
                else { const txt = await r.text(); this.showAlert('Error: '+r.status+' '+txt,'danger'); if(r.status===401) window.location.href='/login'; }
            }catch(e){ console.error(e); }
        }

        showAlert(msg, type){ const el = document.createElement('div'); el.className = `alert alert-${type}`; el.textContent = msg; this.root.prepend(el); setTimeout(()=>el.remove(),4000); }
    }

    window.AdmissionComponents = window.AdmissionComponents || {};
    window.AdmissionComponents.AppointmentList = AppointmentList;
})();
