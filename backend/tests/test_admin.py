import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.auth.jwt import create_access_token


client = TestClient(app)


def admin_token():
    return create_access_token(subject="admin-test", extras={"role": "admin"})


def user_token():
    return create_access_token(subject="user-test", extras={"role": "user"})


def test_metrics_admin_ok():
    headers = {"Authorization": f"Bearer {admin_token()}"}
    r = client.get("/api/admin/monitor/metrics", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "since_minutes" in data
    assert "data" in data


def test_logs_admin_ok():
    headers = {"Authorization": f"Bearer {admin_token()}"}
    r = client.get("/api/admin/monitor/logs", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "lines" in data


def test_admin_forbidden_for_non_admin():
    headers = {"Authorization": f"Bearer {user_token()}"}
    r = client.get("/api/admin/monitor/metrics", headers=headers)
    assert r.status_code == 403


def test_missing_auth_unauthorized():
    r = client.get("/api/admin/monitor/metrics")
    assert r.status_code == 401
