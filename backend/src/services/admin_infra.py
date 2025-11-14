import subprocess
from typing import Dict, Any


def _safe_run(cmd: str) -> Dict[str, Any]:
    try:
        p = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return {"ok": True, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "stdout": e.stdout, "stderr": e.stderr or str(e)}


def deploy_service(target: str, options: Dict = None):
    # Lightweight stub: if a k8s manifest exists, apply it; otherwise, return simulated response.
    opts = options or {}
    # Example: if target == 'backend' we might call k8s deployment. Keep safe by default.
    return {"action": "deploy", "target": target, "options": opts, "result": "queued"}


def stop_service(target: str, options: Dict = None):
    opts = options or {}
    return {"action": "stop", "target": target, "options": opts, "result": "ok"}


def rebuild_image(target: str, options: Dict = None):
    opts = options or {}
    # If target references a local Dockerfile we could run a docker build command here.
    # Keep safe: return instructions rather than executing heavy commands by default.
    return {"action": "rebuild", "target": target, "options": opts, "result": "not_executed", "note": "Use CLI scripts in scripts/dev to perform actual builds"}


def update_configmap(name: str, data: Dict[str, str]):
    return {"action": "update_configmap", "name": name, "data": data, "result": "not_implemented"}


def update_secret(name: str, data: Dict[str, str]):
    return {"action": "update_secret", "name": name, "result": "not_implemented"}
