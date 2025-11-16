from fastapi.testclient import TestClient
from src.main import app
from src.auth.jwt import create_access_token
from src.database import SessionLocal
from src.models.user import User
from src.auth.utils import hash_password
from uuid import uuid4


client = TestClient(app)


def test_patient_me_fallback_when_no_db_user():
    # Crear token con subject no presente en DB -> endpoint debe devolver fallback
    token = create_access_token(subject="patient-test", extras={"role": "patient"})
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/patient/me", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "patient-test"
    assert "username" in data
    # No exponer campos sensibles
    assert "hashed_password" not in data
    assert "is_superuser" not in data


def test_patient_me_invalid_token_returns_401():
    headers = {"Authorization": "Bearer this.is.not.a.valid.token"}
    r = client.get("/api/patient/me", headers=headers)
    assert r.status_code == 401


def test_patient_me_inactive_user_returns_401():
    # Crear usuario temporal inactivo en la BD
    db = SessionLocal()
    try:
        u = User()
        u.id = str(uuid4())
        u.username = "tmp_inactive"
        u.email = "tmp_inactive@example.test"
        u.full_name = "Temp Inactive"
        u.hashed_password = hash_password("secret")
        u.user_type = "patient"
        u.is_superuser = False
        u.is_active = False
        db.add(u)
        db.commit()
        db.refresh(u)

        token = create_access_token(subject=u.id, extras={"role": "patient"})
        headers = {"Authorization": f"Bearer {token}"}
        r = client.get("/api/patient/me", headers=headers)
        assert r.status_code == 401
    finally:
        # limpiar
        try:
            db.delete(u)
            db.commit()
        except Exception:
            pass
        db.close()
