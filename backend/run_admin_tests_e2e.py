#!/usr/bin/env python3
import json
import os
from datetime import datetime
import urllib.request
import urllib.parse


API_URL = os.environ.get("API_URL", "http://localhost:8000")


def post_form(path, data):
    url = API_URL + path
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r), r.getcode()


def post_json(path, payload, token=None):
    url = API_URL + path
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r), r.getcode()
    except urllib.error.HTTPError as e:
        try:
            return json.load(e), e.code
        except Exception:
            return {"error": e.reason}, e.code


def get(path, token=None):
    url = API_URL + path
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            content_type = r.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                return json.load(r), r.getcode()
            else:
                return r.read().decode(), r.getcode()
    except urllib.error.HTTPError as e:
        try:
            return json.load(e), e.code
        except Exception:
            return {"error": e.reason}, e.code


def run_e2e():
    results = []

    # 1. Authenticate as admin1
    try:
        token_resp, status = post_form("/api/auth/token", {"username": "admin1", "password": "secret"})
        admin_token = token_resp.get("access_token")
    except Exception as e:
        results.append({"name": "auth_admin1", "status": "error", "body": str(e)})
        return results

    results.append({"name": "auth_admin1", "status": status, "body": token_resp})

    # 2. metrics
    metrics_body, metrics_status = get("/api/admin/monitor/metrics", token=admin_token)
    results.append({"name": "metrics_admin", "status": metrics_status, "body": metrics_body})

    # 3. logs
    logs_body, logs_status = get("/api/admin/monitor/logs", token=admin_token)
    results.append({"name": "logs_admin", "status": logs_status, "body": logs_body})

    # 4. forbidden for non-admin (enfermera1)
    try:
        t2, s2 = post_form("/api/auth/token", {"username": "enfermera1", "password": "secret"})
        nurse_token = t2.get("access_token")
    except Exception as e:
        nurse_token = None
        results.append({"name": "auth_nurse", "status": "error", "body": str(e)})

    forb_body, forb_status = get("/api/admin/monitor/metrics", token=nurse_token)
    results.append({"name": "forbidden_non_admin", "status": forb_status, "body": forb_body})

    # 5. missing auth
    missing_body, missing_status = get("/api/admin/monitor/metrics", token=None)
    results.append({"name": "missing_auth", "status": missing_status, "body": missing_body})

    # 6. CRUD light: create -> get -> update -> delete
    new_user = {
        "username": "e2e-test-user",
        "email": "e2e@example.com",
        "full_name": "E2E Test User",
        "password": "testpass",
        "user_type": "user",
        "is_superuser": False,
    }
    created, created_status = post_json("/api/admin/users", new_user, token=admin_token)
    results.append({"name": "create_user", "status": created_status, "body": created})

    user_id = created.get("id") if isinstance(created, dict) else None
    if user_id:
        got, got_status = get(f"/api/admin/users/{user_id}", token=admin_token)
        results.append({"name": "get_user", "status": got_status, "body": got})

        # update
        upd_payload = {"full_name": "E2E Updated"}
        # PUT endpoint expects JSON
        url = API_URL + f"/api/admin/users/{user_id}"
        import urllib.request as _u, json as _j
        req = _u.Request(url, data=_j.dumps(upd_payload).encode(), method="PUT")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {admin_token}")
        try:
            with _u.urlopen(req, timeout=10) as r:
                updb = _j.load(r)
                upds = r.getcode()
        except _u.HTTPError as e:
            try:
                updb = _j.load(e)
            except Exception:
                updb = {"error": e.reason}
            upds = e.code
        results.append({"name": "update_user", "status": upds, "body": updb})

        # delete
        import urllib.error as _err
        del_req = urllib.request.Request(API_URL + f"/api/admin/users/{user_id}", data=b"", method="DELETE")
        del_req.add_header("Authorization", f"Bearer {admin_token}")
        try:
            with urllib.request.urlopen(del_req, timeout=10) as r:
                del_status = r.getcode()
                del_body = ""
        except urllib.error.HTTPError as e:
            del_status = e.code
            try:
                del_body = json.load(e)
            except Exception:
                del_body = {"error": e.reason}
        results.append({"name": "delete_user", "status": del_status, "body": del_body})

        # verify delete -> should be 404
        verify_body, verify_status = get(f"/api/admin/users/{user_id}", token=admin_token)
        results.append({"name": "verify_deleted_user", "status": verify_status, "body": verify_body})

    return results


def write_md(results, path):
    lines = []
    lines.append(f"# Informe E2E Admin - {datetime.utcnow().isoformat()}Z\n")
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

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write("\n".join(lines))


if __name__ == '__main__':
    res = run_e2e()
    out = "doc/resultados-tests/admin_tests_report.md"
    write_md(res, out)
    print(f"Results written to: {out}")
    for r in res:
        print(r['name'], r['status'])
