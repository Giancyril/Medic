from typing import Dict, Any, List, Optional
import re
from backend.app.core.config import settings
from backend.tools.cluster_simulator import simulator

ERROR_PATTERNS = [
    re.compile(r"error", re.IGNORECASE),
    re.compile(r"fatal", re.IGNORECASE),
    re.compile(r"critical", re.IGNORECASE),
    re.compile(r"exception", re.IGNORECASE),
    re.compile(r"timeout", re.IGNORECASE),
    re.compile(r"outofmemory", re.IGNORECASE),
    re.compile(r"panic", re.IGNORECASE),
    re.compile(r"sigkill", re.IGNORECASE),
    re.compile(r"crash", re.IGNORECASE),
    re.compile(r"504 gateway timeout", re.IGNORECASE)
]

async def tail_pod_logs(service: str, namespace: str = "production", max_lines: int = 50) -> Dict[str, Any]:
    """
    Tails the most recent container logs from all pods in a service,
    extracting high-priority error signatures and stack traces.
    """
    all_lines: List[Dict[str, str]] = []
    error_lines: List[Dict[str, str]] = []

    if settings.SIMULATION_MODE:
        for pod_name, lines in simulator.logs.items():
            if service in pod_name:
                for line in lines[-max_lines:]:
                    entry = {"pod": pod_name, "message": line}
                    all_lines.append(entry)
                    if any(p.search(line) for p in ERROR_PATTERNS):
                        error_lines.append(entry)

        return {
            "service": service,
            "namespace": namespace,
            "total_lines_scanned": len(all_lines),
            "error_count": len(error_lines),
            "errors": error_lines,
            "raw_logs": all_lines[-max_lines:]
        }

    return {
        "service": service,
        "namespace": namespace,
        "total_lines_scanned": 0,
        "error_count": 0,
        "errors": [],
        "raw_logs": []
    }
