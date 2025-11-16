from fastapi.testclient import TestClient
from uuid import UUID

from src.main import app
from src.auth.jwt import create_access_token


class FakeUser:
    def __init__(self, id, username="patient1", fhir_patient_id=None, is_active=True):
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


def make_token(subject: str = "11111111-1111-1111-1111-111111111111"):
    extras = {"role": "patient", "documento_id": "1"}
    return create_access_token(subject=subject, extras=extras)


def fake_get_db_with_none():
    # Fake session where query(User) returns None (simulate no DB user)
    return FakeSession(None)


def fake_get_db_with_user_with_fhir():
    # Fake session where query(User) returns a user with fhir_patient_id set
    u = FakeUser(id=str(UUID(int=1)), fhir_patient_id="1")
    return FakeSession(u)


def test_get_me_fallback(monkeypatch):
    client = TestClient(app)
    from src.database import get_db
    app.dependency_overrides[get_db] = fake_get_db_with_none

    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/patient/me", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == "11111111-1111-1111-1111-111111111111"

    app.dependency_overrides.pop(get_db, None)


def test_get_summary_and_lists(monkeypatch):
    client = TestClient(app)
    from src.database import get_db
    app.dependency_overrides[get_db] = fake_get_db_with_user_with_fhir

    # Patch controller to return predictable summary
    from src.controllers import patient as patient_ctrl

    def fake_summary(u, db):
        return {"patient": {"id": str(u.id), "username": getattr(u, 'username', 'patient1'), "email": ""}, "appointments": [{"cita_id": 1}], "encounters": [{"encuentro_id": 2}]}

    monkeypatch.setattr(patient_ctrl, "get_patient_summary_from_model", fake_summary)
    monkeypatch.setattr(patient_ctrl, "get_patient_appointments_from_model", lambda u, db, limit=100, offset=0, estado=None: [{"cita_id": 1}])
    monkeypatch.setattr(patient_ctrl, "get_patient_appointment_by_id", lambda u, db, cid: {"cita_id": cid})
    monkeypatch.setattr(patient_ctrl, "get_patient_encounter_by_id", lambda u, db, eid: {"encuentro_id": eid})

    # patch routes binding too
    from src.routes import patient as patient_routes
    monkeypatch.setattr(patient_routes, "get_patient_summary_from_model", fake_summary)
    monkeypatch.setattr(patient_routes, "get_patient_appointments_from_model", lambda u, db, limit=100, offset=0, estado=None: [{"cita_id": 1}])
    monkeypatch.setattr(patient_routes, "get_patient_appointment_by_id", lambda u, db, cid: {"cita_id": cid})
    monkeypatch.setattr(patient_routes, "get_patient_encounter_by_id", lambda u, db, eid: {"encuentro_id": eid})

    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/patient/me/summary", headers=headers)
    assert r.status_code == 200, r.text
    s = r.json()
    assert "appointments" in s and isinstance(s["appointments"], list)

    r2 = client.get("/api/patient/me/appointments", headers=headers)
    assert r2.status_code == 200, r2.text
    assert isinstance(r2.json(), list)

    r3 = client.get("/api/patient/me/appointments/1", headers=headers)
    assert r3.status_code == 200, r3.text
    assert r3.json()["cita_id"] == 1

    r4 = client.get("/api/patient/me/encounters/2", headers=headers)
    assert r4.status_code == 200, r4.text
    assert r4.json()["encuentro_id"] == 2

    app.dependency_overrides.pop(get_db, None)
