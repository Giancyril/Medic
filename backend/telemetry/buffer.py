"""
Telemetry Ingestion & Time-Series Buffer.
Maintains high-resolution metric windows, rolling aggregations, and anomaly spikes.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import math
from backend.telemetry.models import TelemetryPoint, SLODefinition, SLIStatus, SLIType, utc_now

class TelemetryBuffer:
    """
    In-memory circular telemetry stream buffer with downsampling and rolling statistics.
    """
    def __init__(self, max_points_per_metric: int = 1440):
        self.max_points = max_points_per_metric
        # Map: metric_key -> deque of TelemetryPoint
        self._buffer: Dict[str, deque[TelemetryPoint]] = defaultdict(lambda: deque(maxlen=self.max_points))
        self._slo_catalog: Dict[str, SLODefinition] = {}
        self._seed_default_slos()

    def _seed_default_slos(self):
        default_slos = [
            SLODefinition(
                id="slo-order-availability",
                service="order-processor",
                name="Order Processor High Availability",
                target_pct=99.9,
                sli_type=SLIType.AVAILABILITY,
                threshold_value=1.0, # max 1% error rate
                window_hours=24,
                description="99.9% of requests succeed with non-5xx status over 24h"
            ),
            SLODefinition(
                id="slo-order-latency",
                service="order-processor",
                name="Order Processor P99 Latency",
                target_pct=99.0,
                sli_type=SLIType.LATENCY_P99,
                threshold_value=800.0, # max 800ms
                window_hours=24,
                description="99% of order processing requests served under 800ms"
            ),
            SLODefinition(
                id="slo-payment-availability",
                service="payment-api",
                name="Payment API Availability",
                target_pct=99.95,
                sli_type=SLIType.AVAILABILITY,
                threshold_value=0.5,
                window_hours=24,
                description="99.95% of payment transactions succeed without error"
            ),
            SLODefinition(
                id="slo-billing-saturation",
                service="billing-service",
                name="Billing Memory Headroom",
                target_pct=99.5,
                sli_type=SLIType.SATURATION,
                threshold_value=85.0, # max 85% memory
                window_hours=24,
                description="Container memory saturation remains under 85% for 99.5% of samples"
            ),
        ]
        for slo in default_slos:
            self._slo_catalog[slo.id] = slo

    def ingest_point(self, point: TelemetryPoint):
        key = f"{point.namespace}/{point.service}/{point.metric_name}"
        self._buffer[key].append(point)

    def ingest_points(self, points: List[TelemetryPoint]):
        for p in points:
            self.ingest_point(p)

    def get_series(self, service: str, metric_name: str, namespace: str = "production", limit: int = 100) -> List[TelemetryPoint]:
        key = f"{namespace}/{service}/{metric_name}"
        pts = list(self._buffer.get(key, []))
        return pts[-limit:]

    def get_slos_for_service(self, service: str) -> List[SLODefinition]:
        return [s for s in self._slo_catalog.values() if s.service == service]

    def get_all_slos(self) -> List[SLODefinition]:
        return list(self._slo_catalog.values())

    def evaluate_slo(self, slo_id: str, current_metrics: Optional[Dict[str, float]] = None) -> SLIStatus:
        slo = self._slo_catalog.get(slo_id)
        if not slo:
            raise KeyError(f"SLO '{slo_id}' not found")

        # Evaluate based on active metrics or provided snapshot
        metrics = current_metrics or {}
        error_rate = metrics.get("error_rate_pct", 0.0)
        p99_latency = metrics.get("latency_p99_ms", 120.0)
        memory_pct = metrics.get("memory_saturation_pct", 50.0)

        current_sli_val = 100.0
        burn_rate = 0.0

        if slo.sli_type == SLIType.AVAILABILITY:
            # Current compliance: 100 - error_rate
            current_sli_val = max(0.0, 100.0 - error_rate)
            # Allowed error budget = (100 - target_pct) e.g. 0.1%
            allowed_error_pct = max(0.001, 100.0 - slo.target_pct)
            burn_rate = round(error_rate / allowed_error_pct, 2)
        elif slo.sli_type == SLIType.LATENCY_P99:
            if p99_latency > slo.threshold_value:
                excess_ratio = (p99_latency - slo.threshold_value) / slo.threshold_value
                current_sli_val = max(70.0, 100.0 - (excess_ratio * 15.0))
                burn_rate = round(max(1.0, excess_ratio * 10.0), 2)
            else:
                current_sli_val = 99.8
                burn_rate = 0.2
        elif slo.sli_type == SLIType.SATURATION:
            if memory_pct > slo.threshold_value:
                current_sli_val = max(60.0, 100.0 - ((memory_pct - slo.threshold_value) * 2.0))
                burn_rate = round((memory_pct - slo.threshold_value) / 2.0, 2)
            else:
                current_sli_val = 99.9
                burn_rate = 0.1

        is_breached = current_sli_val < slo.target_pct or burn_rate > 14.4
        budget_remaining = max(0.0, min(100.0, 100.0 - (burn_rate * 5.0)))
        
        status = "healthy"
        if burn_rate >= 14.4 or is_breached:
            status = "critical"
        elif burn_rate >= 3.0:
            status = "warning"

        return SLIStatus(
            slo_id=slo.id,
            service=slo.service,
            target_pct=slo.target_pct,
            current_pct=round(current_sli_val, 2),
            burn_rate=burn_rate,
            error_budget_remaining_pct=round(budget_remaining, 1),
            is_breached=is_breached,
            status=status,
        )

# Global singleton buffer
telemetry_buffer = TelemetryBuffer()
