#!/usr/bin/env python3
import json
from datetime import datetime
from src.main import app
from src.auth.jwt import create_access_token
from fastapi.testclient import TestClient


client = TestClient(app)


def run_local_crud():
    results = []
    token = create_access_token(subject="admin-local", extras={"role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    new_user = {
        "username": "local-e2e-user",
        "email": "local-e2e@example.com",
        "full_name": "Local E2E",
        "password": "testpass",
        "user_type": "user",
        "is_superuser": False,
    }

    r = client.post("/api/admin/users", json=new_user, headers=headers)
    results.append({"name": "create_user_local", "status": r.status_code, "body": r.json() if r.headers.get('content-type','').startswith('application/json') else r.text})

    if r.status_code == 201:
        uid = r.json().get('id')
        r2 = client.get(f"/api/admin/users/{uid}", headers=headers)
        results.append({"name": "get_user_local", "status": r2.status_code, "body": r2.json()})

        upd = {"full_name": "Local Updated"}
        r3 = client.put(f"/api/admin/users/{uid}", json=upd, headers=headers)
        results.append({"name": "update_user_local", "status": r3.status_code, "body": r3.json()})

        r4 = client.delete(f"/api/admin/users/{uid}", headers=headers)
        results.append({"name": "delete_user_local", "status": r4.status_code, "body": r4.text})

        r5 = client.get(f"/api/admin/users/{uid}", headers=headers)
        results.append({"name": "verify_deleted_local", "status": r5.status_code, "body": r5.json() if r5.headers.get('content-type','').startswith('application/json') else r5.text})

    return results


def append_md(results, path):
    lines = []
    lines.append(f"## CRUD_local - {datetime.utcnow().isoformat()}Z\n")
    for r in results:
        lines.append(f"### {r['name']}")
        lines.append(f"- status: {r['status']}")
        body = r.get('body')
        snippet = json.dumps(body, indent=2, ensure_ascii=False)
        lines.append("- response:\n")
        lines.append("```json")
        lines.append(snippet)
        lines.append("```")
        lines.append("")

    with open(path, "a") as fh:
        fh.write("\n".join(lines))


if __name__ == '__main__':
    res = run_local_crud()
    out = "doc/resultados-tests/admin_tests_report.md"
    append_md(res, out)
    print(f"Appended local CRUD results to: {out}")
