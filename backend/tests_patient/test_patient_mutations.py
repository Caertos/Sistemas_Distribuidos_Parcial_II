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

    # minimal execute/commit used by controllers when not patched
    def execute(self, *args, **kwargs):
        return None

    def commit(self):
        return None


def fake_get_db():
    # return a fake session with a predictable user (direct return, not a generator)
    u = FakeUser(id=str(UUID(int=1)))
    return FakeSession(u)


def make_token(subject: str = "11111111-1111-1111-1111-111111111111"):
    extras = {"role": "patient", "documento_id": "1"}
    return create_access_token(subject=subject, extras=extras)


def test_create_update_cancel_appointment(monkeypatch):
    """Testeamos endpoints POST, PATCH y DELETE de citas con dependencias parcheadas."""
    client = TestClient(app)

    # Override DB dependency to return fake session (callable returning session)
    from src.database import get_db

    app.dependency_overrides[get_db] = fake_get_db

    # Patch controller functions to avoid real DB operations
    from src.controllers import patient as patient_ctrl

    def fake_create(u, db, fecha_hora, duracion_minutos, motivo):
        return {"cita_id": 42, "fecha_hora": fecha_hora, "duracion_minutos": duracion_minutos, "estado": "programada", "motivo": motivo}

    def fake_update(u, db, cita_id, fecha_hora=None, duracion_minutos=None, motivo=None, estado=None):
        return {"cita_id": cita_id, "fecha_hora": fecha_hora or "2025-11-30T10:30:00", "duracion_minutos": duracion_minutos or 30, "estado": estado or "programada", "motivo": motivo or "modificado"}

    def fake_cancel(u, db, cita_id):
        return {"cita_id": cita_id, "fecha_hora": "2025-11-30T10:30:00", "duracion_minutos": 30, "estado": "cancelada", "motivo": "canceled"}

    monkeypatch.setattr(patient_ctrl, "create_patient_appointment", fake_create)
    monkeypatch.setattr(patient_ctrl, "update_patient_appointment", fake_update)
    monkeypatch.setattr(patient_ctrl, "cancel_patient_appointment", fake_cancel)
    # The route module imported the controller functions at import-time, so patch
    # them there as well to ensure the route calls our fakes.
    from src.routes import patient as patient_routes
    monkeypatch.setattr(patient_routes, "create_patient_appointment", fake_create)
    monkeypatch.setattr(patient_routes, "update_patient_appointment", fake_update)
    monkeypatch.setattr(patient_routes, "cancel_patient_appointment", fake_cancel)

    token = make_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # POST create
    body = {"fecha_hora": "2025-11-30T10:30:00", "duracion_minutos": 30, "motivo": "Prueba unit"}
    r = client.post("/api/patient/me/appointments", headers=headers, data=json.dumps(body))
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["cita_id"] == 42

    # PATCH update
    upd = {"fecha_hora": "2025-11-30T11:00:00", "motivo": "Cambio"}
    r2 = client.patch("/api/patient/me/appointments/42", headers=headers, data=json.dumps(upd))
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["cita_id"] == 42
    assert d2["motivo"] == "Cambio"

    # DELETE cancel
    r3 = client.delete("/api/patient/me/appointments/42", headers=headers)
    assert r3.status_code == 200, r3.text
    d3 = r3.json()
    assert d3["estado"] == "cancelada"

    # Clean overrides
    app.dependency_overrides.pop(get_db, None)
