from src.main import app
from src.auth.jwt import create_access_token


class FakeResult:
    def __init__(self, rows):
        self._rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class FakeSessionAssigned:
    """Fake DB session that returns a practitioner id and a matching assignment."""

    def execute(self, sql, params=None):
        s = str(sql).lower()
        if "select fhir_practitioner_id from users" in s:
            return FakeResult([{"fhir_practitioner_id": "10"}])
        if "select 1 from (select profesional_id from cita" in s:
            return FakeResult([{"1": 1}])
        return FakeResult([])


class FakeSessionNotAssigned(FakeSessionAssigned):
    """Returns practitioner id but no assignment rows."""

    def execute(self, sql, params=None):
        s = str(sql).lower()
        if "select fhir_practitioner_id from users" in s:
            return FakeResult([{"fhir_practitioner_id": "10"}])
        # assignment query -> return empty
        if "select 1 from (select profesional_id from cita" in s:
            return FakeResult([])
        return FakeResult([])


class FakeSessionNoPractitioner(FakeSessionAssigned):
    def execute(self, sql, params=None):
        s = str(sql).lower()
        if "select fhir_practitioner_id from users" in s:
            return FakeResult([{"fhir_practitioner_id": None}])
        return super().execute(sql, params)


def token_for(role: str = "practitioner"):
    return {"authorization": f"Bearer {create_access_token(subject='u1', extras={'role': role})}"}


def test_practitioner_assigned_allowed(client, monkeypatch):
    # override DB dependency
    from src.database import get_db

    def fake_get_db():
        return FakeSessionAssigned()

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("practitioner")
    r = client.get("/api/practitioner/patients/123", headers=headers)
    assert r.status_code == 200

    app.dependency_overrides.pop(get_db, None)


def test_practitioner_not_assigned_denied(client, monkeypatch):
    from src.database import get_db

    def fake_get_db():
        return FakeSessionNotAssigned()

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("practitioner")
    r = client.get("/api/practitioner/patients/123", headers=headers)
    assert r.status_code == 403

    app.dependency_overrides.pop(get_db, None)


def test_practitioner_without_fhir_id_denied(client, monkeypatch):
    from src.database import get_db

    def fake_get_db():
        return FakeSessionNoPractitioner()

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("practitioner")
    r = client.get("/api/practitioner/patients/123", headers=headers)
    assert r.status_code == 403

    app.dependency_overrides.pop(get_db, None)


def test_admin_bypasses_assignment(client, monkeypatch):
    from src.database import get_db

    def fake_get_db():
        return FakeSessionNotAssigned()

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("admin")
    r = client.get("/api/practitioner/patients/123", headers=headers)
    assert r.status_code == 200

    app.dependency_overrides.pop(get_db, None)
