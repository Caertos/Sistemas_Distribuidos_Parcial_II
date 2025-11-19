/* workflow-panel.js (static copy) */
(function(){
    class WorkflowPanel {
        constructor(rootId, appointmentComponent){
            this.root = document.getElementById(rootId);
            this.appointments = appointmentComponent;
            this.token = window.auth && window.auth.getStoredToken && window.auth.unwrapFHIR ? window.auth.unwrapFHIR(window.auth.getStoredToken()) : null;
            this.render();
            this.loadPending();
        }

        render(){
            this.root.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center"><h5>Panel de Workflows</h5><button id="wfRefresh" class="btn btn-sm btn-outline-primary"><i class="bi bi-arrow-clockwise"></i></button></div>
                <div class="card-body"><div id="wf-list"></div></div>
            </div>`;
            this.root.querySelector('#wfRefresh').addEventListener('click', ()=>this.loadPending());
        }

        async loadPending(){
            if(!this.appointments) return;
            try{
                const container = this.root.querySelector('#wf-list');
                container.innerHTML = '<div class="text-muted">Cargando...</div>';
                const t = this.token; if(!t) return window.location.href='/login';
                const r = await fetch('/api/patient/admissions/pending',{headers:{'Authorization':`Bearer ${t}`},credentials:'include'});
                if(r.status===401) return window.location.href='/login';
                const rows = await r.json();
                if(!rows || rows.length===0){ container.innerHTML = '<div class="text-muted">No hay elementos en la cola.</div>'; return; }
                container.innerHTML = rows.slice(0,50).map(r=>{
                    const id = r.admission_id || r.cita_id || '';
                    const nombre = (r.nombre || r.nombre_paciente || r.paciente || r.documento_id || 'Paciente').toString();
                    const apellido = (r.apellido || '').toString();
                    const pacienteNombre = (nombre + ' ' + apellido).trim();
                    return `<div class="timeline-item mb-2"><div class="d-flex justify-content-between"><div><strong>${id}</strong> — ${pacienteNombre}</div><div><button data-aid="${id}" data-cita="${r.cita_id||''}" class="btn btn-sm btn-success btn-advance">Avanzar</button></div></div><div class="small text-muted mt-1">${r.motivo_consulta||r.motivo||''}</div></div>`;
                }).join('');
                this.root.querySelectorAll('.btn-advance').forEach(b=>b.addEventListener('click', (e)=>this.advance(e)));
            }catch(e){ console.error(e); }
        }

        async advance(ev){
            const aid = ev.target.getAttribute('data-aid');
            if(!confirm('Marcar como admitida la admisión '+aid+'?')) return;
            const t = this.token; try{
                const r = await fetch(`/api/patient/admissions/${encodeURIComponent(aid)}/admit`,{method:'POST',headers:{'Authorization':`Bearer ${t}`},credentials:'include'});
                if(r.ok){ this.showAlert('Admisión admitida','success'); this.loadPending(); if(this.appointments && this.appointments.loadPending) this.appointments.loadPending(); }
                else { const txt = await r.text(); this.showAlert('Error: '+r.status+' '+txt,'danger'); }
            }catch(e){ console.error(e); }
        }

        showAlert(msg,type){ const el=document.createElement('div'); el.className=`alert alert-${type}`; el.textContent=msg; this.root.prepend(el); setTimeout(()=>el.remove(),3000); }
    }

    window.AdmissionComponents = window.AdmissionComponents || {};
    window.AdmissionComponents.WorkflowPanel = WorkflowPanel;
})();
