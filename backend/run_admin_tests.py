import json
from datetime import datetime
from src.main import app
from src.auth.jwt import create_access_token
from fastapi.testclient import TestClient


client = TestClient(app)


def make_admin_token():
    return create_access_token(subject="admin-test", extras={"role": "admin"})


def make_user_token():
    return create_access_token(subject="user-test", extras={"role": "user"})


def run_tests():
    results = []

    # Test 1: metrics admin
    h = {"Authorization": f"Bearer {make_admin_token()}"}
    r = client.get("/api/admin/monitor/metrics", headers=h)
    results.append({"name": "metrics_admin", "status": r.status_code, "body": r.json()})

    # Test 2: logs admin
    r = client.get("/api/admin/monitor/logs", headers=h)
    results.append({"name": "logs_admin", "status": r.status_code, "body": r.json()})

    # Test 3: forbidden for non-admin
    h2 = {"Authorization": f"Bearer {make_user_token()}"}
    r = client.get("/api/admin/monitor/metrics", headers=h2)
    results.append({"name": "forbidden_non_admin", "status": r.status_code, "body": r.json() if r.headers.get('content-type','').startswith('application/json') else r.text})

    # Test 4: missing auth
    r = client.get("/api/admin/monitor/metrics")
    results.append({"name": "missing_auth", "status": r.status_code, "body": r.json() if r.headers.get('content-type','').startswith('application/json') else r.text})

    return results


def write_md(results, path):
    lines = []
    lines.append(f"# Informe de pruebas Admin - {datetime.utcnow().isoformat()}Z\n")
    for r in results:
        lines.append(f"## {r['name']}")
        lines.append(f"- status: {r['status']}")
        body = r.get('body')
        snippet = json.dumps(body, indent=2, ensure_ascii=False)
        lines.append("- response:\n")
        lines.append("```json")
        lines.append(snippet)
        lines.append("```")
        lines.append("")

    with open(path, "w") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    results = run_tests()
    out = "doc/resultados-tests/admin_tests_report.md"
    write_md(results, out)
    print(f"Results written to: {out}")
    for r in results:
        print(r['name'], r['status'])
