from fastapi.testclient import TestClient
import pytest

from src.main import app
from src.auth.jwt import create_access_token


client = TestClient(app)


def auth_header_for(role: str):
    token = create_access_token(subject="test-user", extras={"role": role})
    return {"authorization": f"Bearer {token}"}


def test_practitioner_sees_only_admitted_by_default():
    headers = auth_header_for("practitioner")
    resp = client.get("/api/practitioner/appointments", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "count" in body and "items" in body
    assert body["count"] == 1
    assert all(item["admitted"] is True for item in body["items"])


def test_admin_can_access_practitioner_endpoints():
    headers = auth_header_for("admin")
    resp = client.get("/api/practitioner/appointments", headers=headers)
    assert resp.status_code == 200


def test_patient_cannot_access_practitioner_endpoints():
    headers = auth_header_for("patient")
    resp = client.get("/api/practitioner/appointments", headers=headers)
    assert resp.status_code == 403


def test_unauthenticated_request_is_401():
    resp = client.get("/api/practitioner/appointments")
    assert resp.status_code == 401
