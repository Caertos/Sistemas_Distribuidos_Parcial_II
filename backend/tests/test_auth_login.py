from fastapi.testclient import TestClient
from src.main import app
from src.auth.utils import hash_password
from src.auth.jwt import verify_token


class FakeUserObj:
    def __init__(self, uid, username, password_plain, user_type="patient", fhir_patient_id=None, fhir_practitioner_id=None):
        self.id = uid
        self.username = username
        self.hashed_password = hash_password(password_plain)
        self.user_type = user_type
        self.fhir_patient_id = fhir_patient_id
        self.fhir_practitioner_id = fhir_practitioner_id
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
    
    # Methods used by create_refresh_token: add, commit, refresh
    def add(self, obj):
        # no-op: simulate adding to session
        self._last_added = obj

    def commit(self):
        # no-op: simulate commit
        return True

    def refresh(self, obj):
        # no-op: simulate SQLAlchemy refresh
        return obj


def test_login_success(monkeypatch):
    from src.database import get_db

    client = TestClient(app)

    user = FakeUserObj(uid="u100", username="juan", password_plain="s3cret", user_type="practitioner", fhir_practitioner_id="pr-1")

    def fake_get_db():
        return FakeSession(user)

    app.dependency_overrides[get_db] = fake_get_db

    resp = client.post("/api/auth/login", json={"username": "juan", "password": "s3cret"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body and body.get("refresh_token")

    # verify token contains expected claims
    token = body["access_token"]
    payload = verify_token(token)
    assert payload.get("sub") == "u100"
    assert payload.get("role") == "practitioner"
    assert payload.get("username") == "juan"

    app.dependency_overrides.pop(get_db, None)


def test_login_invalid_credentials(monkeypatch):
    from src.database import get_db

    client = TestClient(app)

    # No user in DB
    def fake_get_db():
        return FakeSession(None)

    app.dependency_overrides[get_db] = fake_get_db

    resp = client.post("/api/auth/login", json={"username": "nobody", "password": "bad"})
    assert resp.status_code == 401

    app.dependency_overrides.pop(get_db, None)
