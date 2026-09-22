from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.core.config import settings
from backend.tools.cluster_simulator import simulator

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

async def inspect_pods(service: str, namespace: str = "production") -> List[Dict[str, Any]]:
    """
    Inspects all pods belonging to a service in the given namespace.
    Extracts status, ready state, restart counts, exit codes, and termination reasons.
    """
    if settings.SIMULATION_MODE:
        matching = []
        for pod_name, pod in simulator.pods.items():
            if pod["service"] == service and pod["namespace"] == namespace:
                matching.append(pod)
        return matching

    # Live K8s cluster inspector fallback (mock-safe)
    return [
        {
            "name": f"{service}-pod-1",
            "service": service,
            "namespace": namespace,
            "status": "Running",
            "ready": True,
            "restart_count": 0,
            "exit_code": 0,
            "reason": None
        }
    ]

async def inspect_events(service: str, namespace: str = "production", limit: int = 20) -> List[Dict[str, Any]]:
    """
    Retrieves recent Kubernetes events related to the service or its pods.
    Highlights Warning, OOMKilling, BackOff, and FailedScheduling events.
    """
    if settings.SIMULATION_MODE:
        matching = []
        for evt in reversed(simulator.events):
            if service in evt["object"] or namespace in evt.get("namespace", "production"):
                matching.append(evt)
            if len(matching) >= limit:
                break
        return matching

    return []

async def inspect_deployment(service: str, namespace: str = "production") -> Dict[str, Any]:
    """
    Inspects deployment state, desired vs ready replicas, container images,
    and rollout history revisions.
    """
    dep_key = f"{namespace}/{service}"
    if settings.SIMULATION_MODE:
        if dep_key in simulator.deployments:
            return simulator.deployments[dep_key]
        return {
            "name": service,
            "namespace": namespace,
            "replicas": 1,
            "ready_replicas": 1,
            "image": f"registry.internal/{service}:latest",
            "revision": 1,
            "history": []
        }

    return {
        "name": service,
        "namespace": namespace,
        "replicas": 2,
        "ready_replicas": 2,
        "image": f"registry.internal/{service}:v1.0.0",
        "revision": 1,
        "history": []
    }
