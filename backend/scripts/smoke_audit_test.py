import os
from pprint import pprint

# Asegurarse de que backend (cwd) está en PYTHONPATH cuando se ejecute desde workspace
from fastapi.testclient import TestClient

from src.main import app
from src.auth.jwt import create_access_token


def run():
    client = TestClient(app)

    print("GET /health")
    r = client.get("/health")
    print(r.status_code, r.json())

    print('\nGET /api/admin/monitor/logs without token (expected 401)')
    r = client.get("/api/admin/monitor/logs")
    print(r.status_code, r.text)

    print('\nGET /api/admin/auditor/logs with auditor token (expected 200)')
    token = create_access_token(subject="auditor1", extras={"role": "auditor"})
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/admin/auditor/logs", headers=headers)
    print(r.status_code)
    try:
        pprint(r.json())
    except Exception:
        print(r.text)


if __name__ == "__main__":
    run()
