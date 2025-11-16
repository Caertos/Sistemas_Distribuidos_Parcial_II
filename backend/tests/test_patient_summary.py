from fastapi.testclient import TestClient
from src.main import app
from src.auth.jwt import create_access_token


client = TestClient(app)


def test_patient_summary_fallback_when_no_db_user():
    token = create_access_token(subject="patient-summary-test", extras={"role": "patient"})
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/patient/me/summary", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "patient" in data
    assert "appointments" in data and isinstance(data["appointments"], list)
    assert "encounters" in data and isinstance(data["encounters"], list)
