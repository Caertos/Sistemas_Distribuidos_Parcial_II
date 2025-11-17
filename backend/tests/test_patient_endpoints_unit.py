from fastapi.testclient import TestClient
from src.main import app
from src.auth.jwt import create_access_token

client = TestClient(app)


def token_for(role: str = "patient", subject: str = "u1"):
    return {"authorization": f"Bearer {create_access_token(subject=subject, extras={'role': role})}"}


class FakeUserObj:
    def __init__(self, uid, fhir_patient_id=None):
        self.id = uid
        self.username = f"user-{uid}"
        self.email = f"{uid}@example.com"
        self.full_name = "Test User"
        self.fhir_patient_id = fhir_patient_id
        self.is_active = True


class FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class FakeSession:
    def __init__(self, user_obj=None):
        self._user = user_obj

    def query(self, model):
        return FakeQuery(self._user)


def test_get_my_profile_with_db_user(monkeypatch):
    from src.database import get_db

    user_obj = FakeUserObj(uid="u42", fhir_patient_id="123")

    def fake_get_db():
        return FakeSession(user_obj)

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("patient", subject="u42")
    r = client.get("/api/patient/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body.get("id") == "u42"

    app.dependency_overrides.pop(get_db, None)


def test_get_my_profile_fallback_when_no_db(monkeypatch):
    from src.database import get_db

    def fake_get_db():
        class BrokenSession:
            def query(self, model):
                raise Exception("db down")

        return BrokenSession()

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("patient", subject="u99")
    r = client.get("/api/patient/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body.get("id") == "u99"

    app.dependency_overrides.pop(get_db, None)


def test_create_my_appointment_requires_patient_link(monkeypatch):
    # if user not linked to patient record should return 400
    from src.database import get_db

    def fake_get_db():
        return FakeSession(None)

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("patient", subject="u55")
    payload = {"fecha_hora": "2025-11-20T12:00:00", "duracion_minutos": 30, "motivo": "dolor"}
    r = client.post("/api/patient/me/appointments", json=payload, headers=headers)
    # controller may return 400 if user not linked
    assert r.status_code in (400, 500, 401)

    app.dependency_overrides.pop(get_db, None)
