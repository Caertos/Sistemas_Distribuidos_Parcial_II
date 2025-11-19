/* emergency-admission.js (static copy) */
(function(){
    class EmergencyAdmission {
        constructor(rootId, workflow){
            this.root = document.getElementById(rootId);
            this.workflow = workflow;
            this.token = window.auth && window.auth.getStoredToken && window.auth.unwrapFHIR ? window.auth.unwrapFHIR(window.auth.getStoredToken()) : null;
            this.render();
        }

        render(){
            this.root.innerHTML = `
            <div class="card emergency-panel">
                <div class="card-header"><h5>Admisión Urgente (sin cita)</h5></div>
                <div class="card-body">
                    <form id="emergForm">
                        <div class="row">
                            <div class="col-md-4 mb-3"><label class="form-label">Paciente ID</label><input id="em-pid" class="form-control"></div>
                            <div class="col-md-4 mb-3"><label class="form-label">Prioridad</label><select id="em-priority" class="form-select"><option value="alta">Alta</option><option value="normal" selected>Normal</option><option value="baja">Baja</option></select></div>
                            <div class="col-md-4 mb-3"><label class="form-label">Nivel de dolor (0-10)</label><input id="em-dolor" type="number" min="0" max="10" class="form-control"></div>
                        </div>
                        <div class="mb-3"><label class="form-label">Motivo</label><input id="em-motivo" class="form-control"></div>
                        <div class="d-flex justify-content-end"><button class="btn btn-danger" type="submit">Crear Admisión Urgente</button></div>
                    </form>
                    <div id="em-result" class="mt-3 small text-muted"></div>
                </div>
            </div>`;
            this.root.querySelector('#emergForm').addEventListener('submit',(e)=>this.submit(e));
        }

        async submit(e){
            e.preventDefault();
            const pid = this.root.querySelector('#em-pid').value.trim();
            const motivo = this.root.querySelector('#em-motivo').value.trim();
            const prioridad = this.root.querySelector('#em-priority').value;
            const nivel_dolor = parseInt(this.root.querySelector('#em-dolor').value)||0;
            if(!pid || !motivo){ alert('Paciente ID y motivo son obligatorios'); return; }
            const payload = { paciente_id: parseInt(pid), motivo_consulta: motivo, prioridad: prioridad, nivel_dolor };
            const t = this.token; if(!t) return window.location.href='/login';
            try{
                const r = await fetch(`/api/patient/${encodeURIComponent(pid)}/admissions`,{method:'POST',headers:{'Authorization':`Bearer ${t}`,'Content-Type':'application/json'},body:JSON.stringify(payload),credentials:'include'});
                const outEl = this.root.querySelector('#em-result');
                if(r.status===201){ const out = await r.json(); outEl.innerHTML = `<div class='alert alert-success'>Admisión creada: <strong>${out.admission_id}</strong></div>`; if(this.workflow && this.workflow.loadPending) this.workflow.loadPending(); }
                else { const txt = await r.text(); outEl.innerHTML = `<div class='alert alert-danger'>Error ${r.status}: ${txt}</div>`; }
            }catch(e){ console.error(e); }
        }
    }

    window.AdmissionComponents = window.AdmissionComponents || {};
    window.AdmissionComponents.EmergencyAdmission = EmergencyAdmission;
})();
