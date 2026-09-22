from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import random

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ClusterSimulator:
    """
    In-memory simulated Kubernetes cluster and Prometheus metrics engine.
    Allows realistic local development, deterministic chaos injection, and unit testing
    without requiring external Docker, Minikube, or Prometheus services.
    """
    def __init__(self):
        self.pods: Dict[str, Dict[str, Any]] = {}
        self.deployments: Dict[str, Dict[str, Any]] = {}
        self.events: List[Dict[str, Any]] = []
        self.logs: Dict[str, List[str]] = {}
        self.metrics_state: Dict[str, Dict[str, float]] = {}
        self._seed_default_state()

    def _seed_default_state(self):
        # Default healthy services
        services = ["order-processor", "payment-api", "auth-service", "inventory-db", "frontend-gateway"]
        for svc in services:
            dep_key = f"production/{svc}"
            self.deployments[dep_key] = {
                "name": svc,
                "namespace": "production",
                "replicas": 3,
                "ready_replicas": 3,
                "image": f"registry.internal/apps/{svc}:v1.4.2",
                "revision": 3,
                "history": [
                    {"revision": 1, "image": f"registry.internal/apps/{svc}:v1.4.0", "updated_at": (utc_now() - timedelta(days=7)).isoformat()},
                    {"revision": 2, "image": f"registry.internal/apps/{svc}:v1.4.1", "updated_at": (utc_now() - timedelta(days=2)).isoformat()},
                    {"revision": 3, "image": f"registry.internal/apps/{svc}:v1.4.2", "updated_at": (utc_now() - timedelta(hours=3)).isoformat()},
                ]
            }

            for i in range(3):
                pod_name = f"{svc}-{random.randint(100000, 999999)}-{chr(97+i)}"
                self.pods[pod_name] = {
                    "name": pod_name,
                    "service": svc,
                    "namespace": "production",
                    "status": "Running",
                    "ready": True,
                    "restart_count": 0,
                    "exit_code": 0,
                    "reason": None,
                    "node": f"node-worker-{i%2 + 1}",
                    "started_at": (utc_now() - timedelta(hours=4)).isoformat()
                }
                self.logs[pod_name] = [
                    f"[{utc_now().isoformat()}] INFO Service started listening on :8080",
                    f"[{utc_now().isoformat()}] INFO Health probe OK (200)",
                    f"[{utc_now().isoformat()}] INFO Processed batch request (status: 200, duration: 24ms)"
                ]

            self.metrics_state[svc] = {
                "request_rate": 240.0,
                "error_rate": 0.001,
                "latency_p50_ms": 22.0,
                "latency_p95_ms": 65.0,
                "latency_p99_ms": 110.0,
                "cpu_saturation_pct": 32.0,
                "memory_saturation_pct": 45.0
            }

    def inject_chaos_scenario(self, scenario: str, service: str = "order-processor", namespace: str = "production"):
        """Injects a real-world incident pattern for investigation verification."""
        now_str = utc_now().isoformat()

        if scenario == "OOMKilled":
            pod_name = f"{service}-oomkill-pod"
            self.pods[pod_name] = {
                "name": pod_name,
                "service": service,
                "namespace": namespace,
                "status": "Terminated",
                "ready": False,
                "restart_count": 4,
                "exit_code": 137,
                "reason": "OOMKilled",
                "node": "node-worker-1",
                "started_at": now_str
            }
            self.events.append({
                "type": "Warning",
                "reason": "OOMKilling",
                "object": f"Pod/{pod_name}",
                "message": "Memory cgroup out of memory: Kill process 28412 (python) score 987 or sacrifice child",
                "timestamp": now_str
            })
            self.logs[pod_name] = [
                f"[{now_str}] WARN Worker memory usage: 98.4% (limit: 512Mi)",
                f"[{now_str}] ERROR OutOfMemoryError: Container memory limit reached (exceeded 536870912 bytes)",
                f"[{now_str}] FATAL Command terminated by signal 9 (SIGKILL)"
            ]
            self.metrics_state[service] = {
                "request_rate": 80.0,
                "error_rate": 0.42,
                "latency_p50_ms": 120.0,
                "latency_p95_ms": 1800.0,
                "latency_p99_ms": 3200.0,
                "cpu_saturation_pct": 88.0,
                "memory_saturation_pct": 99.4
            }

        elif scenario == "CrashLoopBackOff":
            pod_name = f"{service}-crashloop-pod"
            self.pods[pod_name] = {
                "name": pod_name,
                "service": service,
                "namespace": namespace,
                "status": "CrashLoopBackOff",
                "ready": False,
                "restart_count": 7,
                "exit_code": 1,
                "reason": "CrashLoopBackOff",
                "node": "node-worker-2",
                "started_at": now_str
            }
            self.events.append({
                "type": "Warning",
                "reason": "BackOff",
                "object": f"Pod/{pod_name}",
                "message": "Back-off 5m0s restarting failed container=app pod=" + pod_name,
                "timestamp": now_str
            })
            self.logs[pod_name] = [
                f"[{now_str}] INFO Initializing application configuration...",
                f"[{now_str}] ERROR KeyError: Missing required environment variable 'DATABASE_MASTER_URL'",
                f"[{now_str}] CRITICAL Application startup failed. Exiting with status 1."
            ]
            self.metrics_state[service] = {
                "request_rate": 15.0,
                "error_rate": 0.85,
                "latency_p50_ms": 0.0,
                "latency_p95_ms": 0.0,
                "latency_p99_ms": 0.0,
                "cpu_saturation_pct": 5.0,
                "memory_saturation_pct": 12.0
            }

        elif scenario == "UpstreamTimeout":
            self.events.append({
                "type": "Warning",
                "reason": "HighErrorRate",
                "object": f"Deployment/{service}",
                "message": "Upstream service database-pool latency exceeded 5000ms threshold",
                "timestamp": now_str
            })
            for pod_name, pod in self.pods.items():
                if pod["service"] == service:
                    self.logs[pod_name] = [
                        f"[{now_str}] WARN Connection pool waiting for free connection (active: 50/50, queue: 142)",
                        f"[{now_str}] ERROR TimeoutError: Queue timeout waiting for connection from pool after 5000ms",
                        f"[{now_str}] ERROR HTTP 504 Gateway Timeout returned to caller"
                    ]
            self.metrics_state[service] = {
                "request_rate": 310.0,
                "error_rate": 0.38,
                "latency_p50_ms": 850.0,
                "latency_p95_ms": 3400.0,
                "latency_p99_ms": 5200.0,
                "cpu_saturation_pct": 65.0,
                "memory_saturation_pct": 58.0
            }

simulator = ClusterSimulator()
