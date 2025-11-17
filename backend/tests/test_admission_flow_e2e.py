from fastapi.testclient import TestClient
from src.main import app
from src.auth.jwt import create_access_token
import pytest
import os

# E2E-style test: disabled by default to avoid polluting module state in full-suite runs.
# Opt-in by setting RUN_E2E=1 in the environment.


def token_for(role: str = "admission", subject: str = "user1"):
    return {"authorization": f"Bearer {create_access_token(subject=subject, extras={'role': role})}"}


class FakeSession:
    def __init__(self, store):
        self.store = store

    def execute(self, *args, **kwargs):
        # We'll not parse SQL; the tests that use this will expect mappings().all()
        class R:
            def __init__(self, rows):
                self._rows = rows

            def mappings(self):
                class M:
                    def __init__(self, rows):
                        self._rows = rows

                    def all(self):
                        return self._rows

                    def first(self):
                        return self._rows[0] if self._rows else None

                return M(self._rows)

        # Return admitted appointments
        rows = []
        for a in self.store.get("appointments", []):
            if a.get("estado_admision") == "admitida":
                rows.append(a)
        return R(rows)


@pytest.mark.skipif(os.environ.get("RUN_E2E") != "1", reason="E2E tests disabled by default; set RUN_E2E=1 to run")
def test_patient_admission_flow(monkeypatch):
    import src.routes.patient as patient_routes
    import src.routes.practitioner as practitioner_routes
    from src.database import get_db

    # shared in-memory state
    store = {
        "appointments": [
            {"cita_id": 1, "paciente_id": 1, "fecha_hora": "2025-11-20T10:00:00", "estado_admision": None}
        ],
        "admissions": [],
    }

    # Patch create_admission to add to store and return admission
    def fake_create_admission(db, admitted_by, payload):
        adm = {"admission_id": f"ADM-{len(store['admissions'])+1}", "paciente_id": payload.get('paciente_id'), "cita_id": payload.get('cita_id'), "estado_admision": "pendiente"}
        store["admissions"].append(adm)
        return adm

    def fake_mark_admitted(db, admission_id, author):
        # find admission, set estado, update related appointment
        for adm in store["admissions"]:
            if adm["admission_id"] == admission_id:
                adm["estado_admision"] = "admitida"
                # update appointment
                for a in store["appointments"]:
                    if a.get("cita_id") == adm.get("cita_id"):
                        a["estado_admision"] = "admitida"
                        return {"admission_id": admission_id, "estado_admision": "admitida"}
        return None

    monkeypatch.setattr(patient_routes, "create_admission", fake_create_admission)
    monkeypatch.setattr(patient_routes, "mark_admitted", fake_mark_admitted)

    # Override DB for practitioner listing to return from store
    def fake_get_db():
        return FakeSession(store)

    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    # 1) Admissioner creates admission for cita_id=1
    headers_adm = token_for("admission", subject="adm1")
    payload = {"paciente_id": 1, "cita_id": 1, "motivo_consulta": "Consulta"}
    r = client.post("/api/patient/1/admissions", json=payload, headers=headers_adm)
    assert r.status_code in (200, 201)
    adm_obj = r.json()
    adm_id = adm_obj.get("admission_id")
    assert adm_id is not None

    # 2) Admissioner marks admitted
    r2 = client.post(f"/api/patient/admissions/{adm_id}/admit", headers=headers_adm)
    assert r2.status_code == 200
    assert r2.json().get("estado_admision") == "admitida"

    # 3) Practitioner lists appointments and sees the admitted one
    headers_pr = token_for("practitioner", subject="pr1")
    r3 = client.get("/api/practitioner/appointments", headers=headers_pr)
    assert r3.status_code == 200
    body = r3.json()
    assert body.get("count", 0) >= 1
    items = body.get("items", [])
    assert any((it.get("estado_admision") == "admitida" or it.get("admitted") is True) for it in items)

    app.dependency_overrides.pop(get_db, None)
    client.close()
