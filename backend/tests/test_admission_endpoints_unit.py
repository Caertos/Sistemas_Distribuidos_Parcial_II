from fastapi.testclient import TestClient
from src.main import app
from src.auth.jwt import create_access_token


def token_for(role: str = "admission"):
    return {"authorization": f"Bearer {create_access_token(subject='user1', extras={'role': role})}"}


class FakeSession:
    def __init__(self, rows=None):
        self._rows = rows or []

    def execute(self, *args, **kwargs):
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

        return R(self._rows)


def test_list_pending_admissions_access_control(monkeypatch):
    import src.routes.patient as patient_routes
    from src.database import get_db

    sample = [{"admission_id": "ADM-1", "paciente_id": 1, "motivo_consulta": "Dolor"}]

    def fake_get_db():
        return FakeSession(rows=sample)

    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    # admission allowed
    r = client.get("/api/patient/admissions/pending", headers=token_for("admission"))
    assert r.status_code == 200
    # patient forbidden
    r2 = client.get("/api/patient/admissions/pending", headers=token_for("patient"))
    assert r2.status_code == 403
    # admin allowed
    r3 = client.get("/api/patient/admissions/pending", headers=token_for("admin"))
    assert r3.status_code == 200

    app.dependency_overrides.pop(get_db, None)


def test_mark_admitted_and_discharge_and_refer(monkeypatch):
    import src.routes.patient as patient_routes
    from src.database import get_db

    # Patch the route-level helpers to avoid DB logic
    def fake_mark_admitted(db, admission_id, author):
        return {"admission_id": admission_id, "estado_admision": "admitida"}

    def fake_mark_discharged(db, admission_id, author, notas=None):
        return {"admission_id": admission_id, "estado_admision": "egresada"}

    def fake_refer_patient(db, admission_id, author, payload):
        return {"tarea_id": 123, "estado": "creada"}

    monkeypatch.setattr(patient_routes, "mark_admitted", fake_mark_admitted)
    monkeypatch.setattr(patient_routes, "mark_discharged", fake_mark_discharged)
    monkeypatch.setattr(patient_routes, "refer_patient", fake_refer_patient)

    def fake_get_db():
        return FakeSession()

    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    # admission role can mark admitted
    r = client.post("/api/patient/admissions/ADM-1/admit", headers=token_for("admission"))
    assert r.status_code == 200
    assert r.json().get("estado_admision") == "admitida"

    # patient cannot
    r2 = client.post("/api/patient/admissions/ADM-1/admit", headers=token_for("patient"))
    assert r2.status_code == 403

    # admin can
    r3 = client.post("/api/patient/admissions/ADM-1/admit", headers=token_for("admin"))
    assert r3.status_code == 200

    # discharge
    r4 = client.post("/api/patient/admissions/ADM-1/discharge", headers=token_for("admission"))
    assert r4.status_code == 200
    assert r4.json().get("estado_admision") == "egresada"

    # refer
    payload = {"motivo": "Necesita estudio", "destino": "Especialista"}
    r5 = client.post("/api/patient/admissions/ADM-1/refer", json=payload, headers=token_for("admission"))
    assert r5.status_code == 200
    assert r5.json().get("tarea_id") == 123

    app.dependency_overrides.pop(get_db, None)


def test_nursing_notes_and_med_admin(monkeypatch):
    import src.routes.patient as patient_routes
    from src.database import get_db

    def fake_add_nursing_note(db, author, payload):
        return {"ok": True, "nota": payload.get("nota")}

    def fake_administer_medication(db, author, payload):
        return {"ok": True, "nombre_medicamento": payload.get("nombre_medicamento")}

    monkeypatch.setattr(patient_routes, "add_nursing_note", fake_add_nursing_note)
    monkeypatch.setattr(patient_routes, "administer_medication", fake_administer_medication)

    def fake_get_db():
        return FakeSession()

    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    payload_note = {"paciente_id": 1, "nota": "Paciente estable"}
    r = client.post("/api/patient/1/nursing-notes", json=payload_note, headers=token_for("admission"))
    assert r.status_code == 200
    assert r.json().get("ok") is True

    payload_med = {"nombre_medicamento": "Paracetamol", "dosis": "500mg"}
    r2 = client.post("/api/patient/1/med-admin", json=payload_med, headers=token_for("admission"))
    assert r2.status_code == 200
    assert r2.json().get("nombre_medicamento") == "Paracetamol"

    # patient cannot add nursing note
    r3 = client.post("/api/patient/1/nursing-notes", json=payload_note, headers=token_for("patient"))
    assert r3.status_code == 403

    app.dependency_overrides.pop(get_db, None)
