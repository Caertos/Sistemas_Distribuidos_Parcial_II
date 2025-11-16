import os
import datetime
import pytest

try:
    import httpx
except Exception:
    httpx = None


E2E_BACKEND_URL = os.getenv("E2E_BACKEND_URL", "http://localhost:8000")
E2E_PATIENT_TOKEN = os.getenv("E2E_PATIENT_TOKEN")


@pytest.mark.skipif(httpx is None, reason="httpx not installed in environment")
@pytest.mark.skipif(E2E_PATIENT_TOKEN is None, reason="Set E2E_PATIENT_TOKEN to run E2E tests")
def test_e2e_create_list_cancel_appointment():
    """End-to-end flow against a running backend and DB seed:

    Preconditions:
    - A Postgres instance seeded with the SQL in `postgres-citus/init` is running (see docker-compose.e2e.yml)
    - The backend is running and connected to that DB (DATABASE_URL set appropriately)
    - E2E_PATIENT_TOKEN contains a valid Bearer token for a seeded patient
    """
    headers = {"Authorization": f"Bearer {E2E_PATIENT_TOKEN}"}
    client = httpx.Client(timeout=10.0)

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
