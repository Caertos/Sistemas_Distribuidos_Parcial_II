import subprocess
from typing import Dict, Any


def _safe_run(cmd: str) -> Dict[str, Any]:
    try:
        p = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return {"ok": True, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "stdout": e.stdout, "stderr": e.stderr or str(e)}


def deploy_service(target: str, options: Dict = None):
    # Stub ligero: si existe un manifiesto k8s, aplicarlo; si no, devolver una respuesta simulada.
    opts = options or {}
    # Ejemplo: si target == 'backend' podríamos ejecutar el deployment en k8s. Mantener seguro por defecto.
    return {"action": "deploy", "target": target, "options": opts, "result": "queued"}


def stop_service(target: str, options: Dict = None):
    opts = options or {}
    return {"action": "stop", "target": target, "options": opts, "result": "ok"}


def rebuild_image(target: str, options: Dict = None):
    opts = options or {}
    # Si 'target' referencia un Dockerfile local podríamos ejecutar un 'docker build' aquí.
    # Mantener seguro: devolver instrucciones en lugar de ejecutar comandos pesados por defecto.
    return {"action": "rebuild", "target": target, "options": opts, "result": "not_executed", "note": "Usa los scripts en scripts/dev para realizar builds reales"}


def update_configmap(name: str, data: Dict[str, str]):
    return {"action": "update_configmap", "name": name, "data": data, "result": "not_implemented"}


def update_secret(name: str, data: Dict[str, str]):
    return {"action": "update_secret", "name": name, "result": "not_implemented"}
