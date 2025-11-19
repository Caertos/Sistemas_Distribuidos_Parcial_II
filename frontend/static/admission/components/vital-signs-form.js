/* vital-signs-form.js (static copy) */
(function(){
    class VitalSignsForm {
        constructor(rootId){
            this.root = document.getElementById(rootId);
            this.token = window.auth && window.auth.getStoredToken && window.auth.unwrapFHIR ? window.auth.unwrapFHIR(window.auth.getStoredToken()) : null;
            this.history = [];
            this.render();
        }

        render(){
            this.root.innerHTML = `
            <div class="card">
                <div class="card-header"><h5>Registrar Signos Vitales</h5></div>
                <div class="card-body">
                    <form id="vitalsForm">
                        <div class="row">
                            <div class="col-md-3 mb-3"><label class="form-label">Temperatura (°C)</label><input id="v_temp" class="form-control" type="number" step="0.1"></div>
                            <div class="col-md-3 mb-3"><label class="form-label">FC</label><input id="v_fc" class="form-control" type="number"></div>
                            <div class="col-md-3 mb-3"><label class="form-label">FR</label><input id="v_fr" class="form-control" type="number"></div>
                            <div class="col-md-3 mb-3"><label class="form-label">Sat O2</label><input id="v_sat" class="form-control" type="number"></div>
                        </div>
                        <div class="row">
                            <div class="col-md-4 mb-3"><label class="form-label">PAS</label><input id="v_pas" class="form-control" type="number"></div>
                            <div class="col-md-4 mb-3"><label class="form-label">PAD</label><input id="v_pad" class="form-control" type="number"></div>
                            <div class="col-md-4 mb-3"><label class="form-label">Peso (kg)</label><input id="v_peso" class="form-control" type="number" step="0.1"></div>
                        </div>
                        <div class="d-flex justify-content-end"><button class="btn btn-primary" type="submit">Guardar</button></div>
                    </form>
                    <hr>
                    <div id="vitals-history"><h6>Historial reciente</h6><div id="vitals-list" class="small text-muted">(sin datos)</div></div>
                </div>
            </div>`;
            this.root.querySelector('#vitalsForm').addEventListener('submit', (e)=>this.submit(e));
        }

        async submit(e){
            e.preventDefault();
            const payload = {
                fecha: new Date().toISOString(),
                presion_sistolica: parseInt(this.root.querySelector('#v_pas').value)||null,
                presion_diastolica: parseInt(this.root.querySelector('#v_pad').value)||null,
                frecuencia_cardiaca: parseInt(this.root.querySelector('#v_fc').value)||null,
                frecuencia_respiratoria: parseInt(this.root.querySelector('#v_fr').value)||null,
                temperatura: parseFloat(this.root.querySelector('#v_temp').value)||null,
                saturacion_oxigeno: parseInt(this.root.querySelector('#v_sat').value)||null,
                peso: parseFloat(this.root.querySelector('#v_peso').value)||null,
            };
            const t = this.token; if(!t) return window.location.href='/login';
            try{
                const r = await fetch('/api/patient/me/vitals',{method:'POST',headers:{'Authorization':`Bearer ${t}`,'Content-Type':'application/json'},body:JSON.stringify(payload),credentials:'include'});
                if(r.status===201){ const out = await r.json(); this.history.unshift({payload,out}); this.renderHistory(); this.showAlert('Signo guardado','success'); }
                else { const txt = await r.text(); this.showAlert('Error: '+r.status+' '+txt,'danger'); if(r.status===401) window.location.href='/login'; }
            }catch(e){ console.error(e); }
        }

        renderHistory(){
            const container = this.root.querySelector('#vitals-list');
            if(!this.history.length) { container.innerHTML='(sin datos)'; return; }
            container.innerHTML = this.history.slice(0,10).map(h=>{
                const p=h.payload; return `<div class="mb-1">${new Date(p.fecha).toLocaleString()} — T:${p.temperatura||'—'}°C FC:${p.frecuencia_cardiaca||'—'} FR:${p.frecuencia_respiratoria||'—'} PAS/PAD:${p.presion_sistolica||'—'}/${p.presion_diastolica||'—'} Sat:${p.saturacion_oxigeno||'—'}</div>`;
            }).join('');
        }

        showAlert(msg,type){ const el = document.createElement('div'); el.className=`alert alert-${type}`; el.textContent=msg; this.root.prepend(el); setTimeout(()=>el.remove(),3000); }
    }

    window.AdmissionComponents = window.AdmissionComponents || {};
    window.AdmissionComponents.VitalSignsForm = VitalSignsForm;
})();
