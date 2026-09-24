"""
Cluster Simulator Extension: Real-Time Telemetry Pipeline Generator.
Periodically feeds multi-service golden signals, rolling windows, and simulated chaos into TelemetryBuffer.
"""
from typing import Dict, Any, List
import random
from datetime import datetime, timezone
from backend.telemetry.models import TelemetryPoint, utc_now
from backend.telemetry.buffer import telemetry_buffer

class TelemetryGenerator:
    """
    Generates realistic live metric streams for monitored services and feeds the global TelemetryBuffer.
    """
    SERVICES = ["order-processor", "payment-api", "auth-service", "inventory-db", "frontend-gateway", "billing-service"]

    @classmethod
    def emit_tick(cls, chaos_scenario: str = "nominal") -> List[TelemetryPoint]:
        points: List[TelemetryPoint] = []
        now_ts = utc_now()

        for svc in cls.SERVICES:
            # Baseline healthy behavior
            req_rate = random.uniform(45.0, 120.0)
            err_rate = random.uniform(0.01, 0.45)
            p99_lat = random.uniform(45.0, 160.0)
            cpu_sat = random.uniform(25.0, 55.0)
            mem_sat = random.uniform(40.0, 65.0)

            # Apply chaos deviations
            if chaos_scenario == "OOMKilled" and svc in ["order-processor", "billing-service"]:
                mem_sat = random.uniform(96.0, 99.8)
                p99_lat = random.uniform(1200.0, 3400.0)
                err_rate = random.uniform(8.5, 24.0)
            elif chaos_scenario == "CrashLoopBackOff" and svc in ["auth-service", "order-processor"]:
                err_rate = random.uniform(35.0, 80.0)
                req_rate = random.uniform(10.0, 30.0)
                cpu_sat = random.uniform(10.0, 25.0)
            elif chaos_scenario == "UpstreamTimeout" and svc in ["payment-api", "order-processor"]:
                p99_lat = random.uniform(2800.0, 5200.0)
                err_rate = random.uniform(12.0, 30.0)
                cpu_sat = random.uniform(75.0, 92.0)

            pts = [
                TelemetryPoint(timestamp=now_ts, metric_name="request_rate_rps", service=svc, value=round(req_rate, 1)),
                TelemetryPoint(timestamp=now_ts, metric_name="error_rate_pct", service=svc, value=round(err_rate, 2)),
                TelemetryPoint(timestamp=now_ts, metric_name="latency_p99_ms", service=svc, value=round(p99_lat, 1)),
                TelemetryPoint(timestamp=now_ts, metric_name="cpu_saturation_pct", service=svc, value=round(cpu_sat, 1)),
                TelemetryPoint(timestamp=now_ts, metric_name="memory_saturation_pct", service=svc, value=round(mem_sat, 1)),
            ]
            points.extend(pts)

        telemetry_buffer.ingest_points(points)
        return points

    @classmethod
    def populate_initial_history(cls, points_per_metric: int = 30):
        """Populates rolling historical buffer for immediate chart rendering."""
        for _ in range(points_per_metric):
            cls.emit_tick()
