/* demographic-form.js (static copy) */
(function(){
    function formatDateInput(val){ if(!val) return ''; try{ const d = new Date(val); return d.toISOString().split('T')[0]; }catch(e){return val;} }

    class DemographicForm {
        constructor(rootId){
            this.root = document.getElementById(rootId);
            this.token = window.auth && window.auth.getStoredToken && window.auth.unwrapFHIR ? window.auth.unwrapFHIR(window.auth.getStoredToken()) : null;
            this.render();
            this.loadProfile();
        }
        render(){
            this.root.innerHTML = `
            <div class="card">
                <div class="card-header"><h5>Registro Demográfico</h5></div>
                <div class="card-body">
                    <form id="demogForm">
                        <div class="row">
                            <div class="col-md-4 mb-3"><label class="form-label">Documento</label><input id="demog-documento" class="form-control" readonly></div>
                            <div class="col-md-4 mb-3"><label class="form-label">Nombre</label><input id="demog-nombre" class="form-control"></div>
                            <div class="col-md-4 mb-3"><label class="form-label">Apellido</label><input id="demog-apellido" class="form-control"></div>
                        </div>
                        <div class="row">
                            <div class="col-md-4 mb-3"><label class="form-label">Fecha Nacimiento</label><input id="demog-fn" type="date" class="form-control"></div>
                            <div class="col-md-4 mb-3"><label class="form-label">Contacto</label><input id="demog-contacto" class="form-control"></div>
                            <div class="col-md-4 mb-3"><label class="form-label">Ciudad</label><input id="demog-ciudad" class="form-control"></div>
                        </div>
                        <div class="d-flex justify-content-end"><button class="btn btn-primary" type="submit">Guardar</button></div>
                        <div id="demog-alert" class="mt-3"></div>
                    </form>
                </div>
            </div>`;
            const form = this.root.querySelector('#demogForm');
            form.addEventListener('submit', (e)=>this.submit(e));
        }

        async loadProfile(){
            const token = this.token;
            if(!token) return;
            try{
                const r = await fetch('/api/patient/me', {headers:{'Authorization':`Bearer ${token}`}, credentials:'include'});
                if(r.status===401){ window.location.href='/login'; return; }
                const data = await r.json();
                this.root.querySelector('#demog-documento').value = data.fhir_patient_id || data.id || '';
                this.root.querySelector('#demog-nombre').value = data.full_name || data.nombre || '';
                this.root.querySelector('#demog-apellido').value = data.apellido || '';
                this.root.querySelector('#demog-contacto').value = data.contacto || data.email || '';
                this.root.querySelector('#demog-ciudad').value = data.ciudad || '';
                this.root.querySelector('#demog-fn').value = formatDateInput(data.fecha_nacimiento || data.created_at);
            }catch(e){ console.error('loadProfile',e); }
        }

        async submit(e){
            e.preventDefault();
            const payload = {
                nombre: this.root.querySelector('#demog-nombre').value.trim() || null,
                apellido: this.root.querySelector('#demog-apellido').value.trim() || null,
                fecha_nacimiento: this.root.querySelector('#demog-fn').value || null,
                contacto: this.root.querySelector('#demog-contacto').value || null,
                ciudad: this.root.querySelector('#demog-ciudad').value || null,
            };
            const token = this.token;
            try{
                const r = await fetch('/api/patient/me/demographics',{method:'PUT',headers:{'Authorization':`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify(payload),credentials:'include'});
                const el = this.root.querySelector('#demog-alert');
                if(r.ok){ el.innerHTML = `<div class="alert alert-success">Datos actualizados correctamente</div>`; }
                else { const txt = await r.text(); el.innerHTML = `<div class="alert alert-danger">Error: ${r.status} ${txt}</div>`; if(r.status===401) window.location.href='/login'; }
            }catch(err){ console.error(err); }
        }
    }

    window.AdmissionComponents = window.AdmissionComponents || {};
    window.AdmissionComponents.DemographicForm = DemographicForm;
})();
