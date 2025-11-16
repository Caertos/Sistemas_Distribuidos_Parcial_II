import json
from fastapi.testclient import TestClient
from uuid import UUID

from src.main import app
from src.auth.jwt import create_access_token


class FakeUser:
    def __init__(self, id, username="patient1", fhir_patient_id="1", is_active=True):
        self.id = id
        self.username = username
        self.fhir_patient_id = fhir_patient_id
        self.is_active = is_active


class FakeQuery:
    def __init__(self, user):
        self.user = user

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.user


class FakeSession:
    def __init__(self, user):
        self._user = user

    def query(self, model):
        return FakeQuery(self._user)

    def execute(self, *args, **kwargs):
        return None

    def commit(self):
        return None


def fake_get_db():
    u = FakeUser(id=str(UUID(int=1)))
    return FakeSession(u)


def make_token(subject: str = "11111111-1111-1111-1111-111111111111"):
    extras = {"role": "patient", "documento_id": "1"}
    return create_access_token(subject=subject, extras=extras)


def test_get_medications_and_allergies(monkeypatch):
    client = TestClient(app)

    from src.database import get_db
    app.dependency_overrides[get_db] = fake_get_db

    from src.controllers import patient as patient_ctrl
    # fakes
    def fake_meds(u, db):
        return [{"medicamento_id": 1, "nombre": "Paracetamol", "dosis": "500mg", "frecuencia": "8h"}]

    def fake_alrs(u, db):
        return [{"alergia_id": 2, "agente": "Polen", "severidad": "moderada", "nota": "Estacional"}]

    monkeypatch.setattr(patient_ctrl, "get_patient_medications_from_model", fake_meds)
    monkeypatch.setattr(patient_ctrl, "get_patient_allergies_from_model", fake_alrs)

    # also patch the route module references (import-time binding)
    from src.routes import patient as patient_routes
    monkeypatch.setattr(patient_routes, "get_patient_medications_from_model", fake_meds)
    monkeypatch.setattr(patient_routes, "get_patient_allergies_from_model", fake_alrs)

    token = make_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # medications
    r = client.get("/api/patient/me/medications", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["nombre"] == "Paracetamol"

    # allergies
    r2 = client.get("/api/patient/me/allergies", headers=headers)
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert isinstance(d2, list)
    assert d2[0]["agente"] == "Polen"

    # unauthorized
    r3 = client.get("/api/patient/me/medications")
    assert r3.status_code == 401

    # cleanup
    app.dependency_overrides.pop(get_db, None)
