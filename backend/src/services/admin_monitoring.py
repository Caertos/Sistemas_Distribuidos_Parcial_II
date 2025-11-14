from typing import Optional, List, Dict, Any
import os


def get_metrics(since_minutes: int = 60, metrics: Optional[List[str]] = None) -> Dict[str, Any]:
    # Placeholder metrics response. Integrate with Prometheus or similar in production.
    return {
        "since_minutes": since_minutes,
        "metrics": metrics or ["cpu_usage", "memory_usage", "request_rate"],
        "data": {
            "cpu_usage": 12.3,
            "memory_usage": 256 * 1024 * 1024,
            "request_rate": 42,
        },
    }


def get_logs(service: Optional[str] = None, tail: int = 200) -> Dict[str, Any]:
    # Try to read a local log file in ./logs/<service>.log if exists, otherwise return simulated tail.
    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
    os.makedirs(logs_dir, exist_ok=True)
    if service:
        path = os.path.join(logs_dir, f"{service}.log")
        if os.path.exists(path):
            with open(path, "r") as fh:
                lines = fh.readlines()[-tail:]
            return {"service": service, "tail": tail, "lines": [l.rstrip("\n") for l in lines]}

    # simulated
    sample = [f"[{i}] sample log line for {service or 'system'}" for i in range(max(0, tail - 5), tail)]
    return {"service": service or "system", "tail": tail, "lines": sample}


def get_audit_reports() -> Dict[str, Any]:
    # Stubbed audit report
    return {"audits": [], "note": "No audit backend configured. Integrate with ELK/Graylog in production."}
