/* nursing-notes-form.js (static copy) */
(function(){
    class NursingNotesForm {
        constructor(rootId){
            this.root = document.getElementById(rootId);
            this.token = window.auth && window.auth.getStoredToken && window.auth.unwrapFHIR ? window.auth.unwrapFHIR(window.auth.getStoredToken()) : null;
            this.render();
        }

        render(){
            this.root.innerHTML = `
            <div class="card">
                <div class="card-header"><h5>Notas de Enfermería</h5></div>
                <div class="card-body">
                    <form id="noteForm">
                        <div class="row">
                            <div class="col-md-4 mb-3"><label class="form-label">Paciente ID</label><input id="note-pid" class="form-control" placeholder="ID numérico"></div>
                            <div class="col-md-8 mb-3"><label class="form-label">Admission ID (opcional)</label><input id="note-aid" class="form-control" placeholder="ADM-... o vacío"></div>
                        </div>
                        <div class="mb-3"><label class="form-label">Nota</label><textarea id="note-text" class="form-control" rows="4"></textarea></div>
                        <div class="d-flex justify-content-end"><button class="btn btn-primary" type="submit">Agregar Nota</button></div>
                    </form>
                    <hr>
                    <div id="notes-result" class="small text-muted"></div>
                </div>
            </div>`;
            this.root.querySelector('#noteForm').addEventListener('submit',(e)=>this.submit(e));
        }

        async submit(e){
            e.preventDefault();
            const pid = this.root.querySelector('#note-pid').value.trim();
            const aid = this.root.querySelector('#note-aid').value.trim() || null;
            const nota = this.root.querySelector('#note-text').value.trim();
            if(!pid || !nota){ alert('Paciente ID y nota son obligatorios'); return; }
            const payload = { nota };
            if(aid) payload.admission_id = aid;
            const t = this.token; if(!t) return window.location.href='/login';
            try{
                const r = await fetch(`/api/patient/${encodeURIComponent(pid)}/nursing-notes`,{method:'POST',headers:{'Authorization':`Bearer ${t}`,'Content-Type':'application/json'},body:JSON.stringify(payload),credentials:'include'});
                const resEl = this.root.querySelector('#notes-result');
                if(r.ok){ const out = await r.json(); resEl.innerHTML = `<div class='alert alert-success'>Nota registrada</div><pre class='small'>${JSON.stringify(out,null,2)}</pre>`; }
                else { const txt = await r.text(); resEl.innerHTML = `<div class='alert alert-danger'>Error ${r.status}: ${txt}</div>`; if(r.status===401) window.location.href='/login'; }
            }catch(e){ console.error(e); }
        }
    }

    window.AdmissionComponents = window.AdmissionComponents || {};
    window.AdmissionComponents.NursingNotesForm = NursingNotesForm;
})();
