import os
import shutil
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.middleware.audit import AuditMiddleware


LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))


def make_app(require_header: bool = False):
    app = FastAPI()

    @app.get("/api/patient/test/{patient_id}")
    def get_test(patient_id: int):
        return {"patient_id": patient_id}

    app.add_middleware(AuditMiddleware, require_header=require_header)
    return app


def clean_logs():
    logs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    if os.path.exists(logs_path):
        # remove files but keep folder
        for fname in os.listdir(logs_path):
            fpath = os.path.join(logs_path, fname)
            try:
                if os.path.isfile(fpath):
                    os.remove(fpath)
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath)
            except Exception:
                pass


def test_header_required_returns_428():
    app = make_app(require_header=True)
    client = TestClient(app)

    resp = client.get("/api/patient/test/123")
    assert resp.status_code == 428
    assert "X-Documento-Id" in resp.json().get("detail", "") or "required" in resp.json().get("detail", "").lower()


def test_with_header_writes_fallback_csv(tmp_path):
    # ensure logs dir clean
    clean_logs()

    app = make_app(require_header=True)
    client = TestClient(app)

    headers = {"X-Documento-Id": "123"}
    resp = client.get("/api/patient/test/123", headers=headers)
    assert resp.status_code == 200

    # fallback file should exist
    audit_file = os.path.join(os.path.dirname(__file__), "..", "logs", "audit_access.csv")
    assert os.path.exists(audit_file), f"Expected fallback audit file at {audit_file}"

    content = open(audit_file, "r").read()
    assert "123" in content or "patient" in content
