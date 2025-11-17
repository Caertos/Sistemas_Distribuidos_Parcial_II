from fastapi.testclient import TestClient
from src.main import app
from src.auth.jwt import create_access_token
from src.controllers import admission as admission_ctrl

client = TestClient(app)


def token_for(role: str = "admission"):
    return {"authorization": f"Bearer {create_access_token(subject='adm1', extras={'role': role})}"}


class FakeSession:
    def execute(self, *args, **kwargs):
        return None


def test_admission_role_allows_create(monkeypatch):
    # patch route-local create_admission to avoid DB ops (routes imported it at module import time)
    import src.routes.patient as patient_routes

    def fake_create(db, admitted_by, p):
        return {"admission_id": "ADM-1", "paciente_id": p.get('paciente_id'), "fecha_admision": None, "estado_admision": "activa", "prioridad": p.get('prioridad')}

    monkeypatch.setattr(patient_routes, "create_admission", fake_create)

    from src.database import get_db

    def fake_get_db():
        return FakeSession()

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("admission")
    payload = {"paciente_id": 1, "motivo_consulta": "Dolor"}
    r = client.post("/api/patient/1/admissions", json=payload, headers=headers)
    assert r.status_code in (201, 200)

    app.dependency_overrides.pop(get_db, None)


def test_patient_cannot_create_admission(monkeypatch):
    from src.database import get_db

    def fake_get_db():
        return FakeSession()

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("patient")
    payload = {"paciente_id": 1, "motivo_consulta": "Dolor"}
    r = client.post("/api/patient/1/admissions", json=payload, headers=headers)
    assert r.status_code == 403

    app.dependency_overrides.pop(get_db, None)


def test_admin_can_create_admission(monkeypatch):
    import src.routes.patient as patient_routes

    def fake_create(db, admitted_by, p):
        return {"admission_id": "ADM-1", "paciente_id": p.get('paciente_id')}

    monkeypatch.setattr(patient_routes, "create_admission", fake_create)

    from src.database import get_db

    def fake_get_db():
        return FakeSession()

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("admin")
    payload = {"paciente_id": 1, "motivo_consulta": "Dolor"}
    r = client.post("/api/patient/1/admissions", json=payload, headers=headers)
    assert r.status_code in (201, 200)

    app.dependency_overrides.pop(get_db, None)
