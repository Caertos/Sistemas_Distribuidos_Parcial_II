import os
import datetime
import pytest

try:
    import httpx
except Exception:
    httpx = None

try:
    from sqlalchemy import create_engine, text
except Exception:
    create_engine = None

from uuid import uuid4


E2E_BACKEND_URL = os.getenv("E2E_BACKEND_URL", "http://localhost:8000")
E2E_PATIENT_TOKEN = os.getenv("E2E_PATIENT_TOKEN")
E2E_DB_URL = os.getenv("E2E_DB_URL", "postgresql://test:test@localhost:5432/testdb")


@pytest.mark.skipif(httpx is None, reason="httpx not installed in environment")
def test_e2e_create_list_cancel_appointment():
    """End-to-end flow against a running backend and DB seed.

    This test will try to obtain a bearer token automatically by inserting a test
    user and a linked `paciente` row into the DB (if they don't already exist),
    then request a token via the normal `/api/auth/token` endpoint.

    Preconditions:
    - A Postgres/Citus instance seeded with the SQL in `postgres-citus/init` is running (see docker-compose.e2e.yml)
    - The backend is running and connected to that DB (DATABASE_URL set appropriately)
    """

    client = httpx.Client(timeout=10.0)

    # If a token was provided externally, prefer it. Otherwise try to create user+patient in DB.
    token = E2E_PATIENT_TOKEN

    if not token:
        if create_engine is None:
            pytest.skip("SQLAlchemy not available to prepare DB user; set E2E_PATIENT_TOKEN to run this test")

        # Prepare DB user and paciente record
        engine = create_engine(E2E_DB_URL)
        test_username = f"e2e_user_{uuid4().hex[:8]}"
        test_password = "secret"
        test_email = f"{test_username}@example.test"
        test_fullname = "E2E Test User"

        # Use project's password hashing utility if available
        try:
            from src.auth.utils import hash_password
            hashed = hash_password(test_password)
        except Exception:
            # fallback: store plaintext (only for local e2e use; verify_password has fallbacks)
            hashed = test_password

        # Create a paciente and a user linked to it
        pid = 100000 + int(datetime.datetime.now().timestamp()) % 10000
        documento_id = 999999
        user_id = str(uuid4())

        with engine.begin() as conn:
            # Insert paciente if not exists
            conn.execute(text("INSERT INTO paciente (paciente_id, documento_id, nombre, apellido) VALUES (:pid, :doc, :n, :a) ON CONFLICT (documento_id, paciente_id) DO NOTHING"), {"pid": pid, "doc": documento_id, "n": "E2E", "a": "Patient"})

            # Insert user if not exists
            conn.execute(
                text(
                    "INSERT INTO users (id, username, email, full_name, hashed_password, user_type, is_active, fhir_patient_id) VALUES (:id, :username, :email, :full_name, :hpw, :utype, true, :fhir) ON CONFLICT (username) DO NOTHING"
                ),
                {"id": user_id, "username": test_username, "email": test_email, "full_name": test_fullname, "hpw": hashed, "utype": "patient", "fhir": str(pid)},
            )

        # Request token via OAuth2 password flow
        data = {"username": test_username, "password": test_password}
        r = client.post(f"{E2E_BACKEND_URL}/api/auth/token", data=data)
        assert r.status_code == 200, f"Token endpoint failed: {r.status_code} {r.text}"
        resp = r.json()
        token = resp.get("access_token")
        assert token, "No access_token returned"

    headers = {"Authorization": f"Bearer {token}"}

    # 1) Check auth + profile
    r = client.get(f"{E2E_BACKEND_URL}/api/patient/me", headers=headers)
    assert r.status_code == 200, f"GET /api/patient/me failed: {r.status_code} {r.text}"

    # 2) Create appointment in the future (48h ahead)
    fecha = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=48)).isoformat()
    payload = {"fecha_hora": fecha, "duracion_minutos": 30, "motivo": "E2E test"}
    r = client.post(f"{E2E_BACKEND_URL}/api/patient/me/appointments", json=payload, headers=headers)
    assert r.status_code == 201, f"Create appointment failed: {r.status_code} {r.text}"
    appt = r.json()
    appt_id = appt.get("cita_id")
    assert appt_id is not None

    # 3) List appointments and check presence
    r = client.get(f"{E2E_BACKEND_URL}/api/patient/me/appointments", headers=headers)
    assert r.status_code == 200
    appts = r.json()
    assert any(a.get("cita_id") == appt_id for a in appts)

    # 4) Cancel appointment
    r = client.delete(f"{E2E_BACKEND_URL}/api/patient/me/appointments/{appt_id}", headers=headers)
    assert r.status_code == 200, f"Cancel failed: {r.status_code} {r.text}"
    canceled = r.json()
    assert canceled.get("estado") == "cancelada"
