"""
Telemetry REST API.
Exposes endpoints for querying telemetry series, evaluating real-time SLO burn rates,
and retrieving cross-service anomaly correlations.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query, HTTPException
from backend.telemetry.models import TelemetryPoint, SLODefinition, SLIStatus, CorrelatedSignal
from backend.telemetry.buffer import telemetry_buffer
from backend.telemetry.generator import TelemetryGenerator
from backend.telemetry.correlator import CorrelationEngine

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

# Ensure some initial history exists
TelemetryGenerator.populate_initial_history(25)

@router.get("/series/{service}/{metric_name}", summary="Query time-series points for a service metric")
async def get_metric_series(
    service: str,
    metric_name: str,
    namespace: str = "production",
    limit: int = Query(60, ge=5, le=300)
):
    points = telemetry_buffer.get_series(service, metric_name, namespace, limit)
    return {
        "service": service,
        "metric_name": metric_name,
        "count": len(points),
        "points": [p.model_dump() for p in points]
    }

@router.get("/slos", summary="List all configured SLOs and current burn rates")
async def list_slos(service: Optional[str] = None):
    slos = telemetry_buffer.get_slos_for_service(service) if service else telemetry_buffer.get_all_slos()
    evaluations: List[SLIStatus] = []
    
    for slo in slos:
        # Retrieve latest metrics for evaluation
        err_pts = telemetry_buffer.get_series(slo.service, "error_rate_pct", limit=1)
        lat_pts = telemetry_buffer.get_series(slo.service, "latency_p99_ms", limit=1)
        mem_pts = telemetry_buffer.get_series(slo.service, "memory_saturation_pct", limit=1)
        
        snapshot = {
            "error_rate_pct": err_pts[-1].value if err_pts else 0.1,
            "latency_p99_ms": lat_pts[-1].value if lat_pts else 120.0,
            "memory_saturation_pct": mem_pts[-1].value if mem_pts else 50.0,
        }
        evaluations.append(telemetry_buffer.evaluate_slo(slo.id, snapshot))
        
    return {
        "count": len(evaluations),
        "slos": [e.model_dump() for e in evaluations]
    }

@router.get("/correlations/{service}", summary="Compute cross-signal correlations for incident diagnosis")
async def get_correlations(service: str):
    # Fetch primary signals
    lat_pts = telemetry_buffer.get_series(service, "latency_p99_ms", limit=30)
    primary_series = [p.value for p in lat_pts]
    
    if len(primary_series) < 3:
        return {"service": service, "correlations": []}
        
    candidates = {}
    for other_metric in ["memory_saturation_pct", "cpu_saturation_pct", "error_rate_pct", "request_rate_rps"]:
        pts = telemetry_buffer.get_series(service, other_metric, limit=30)
        if pts:
            candidates[other_metric] = (service, [p.value for p in pts])
            
    # Also check upstream service payment-api
    if service != "payment-api":
        up_pts = telemetry_buffer.get_series("payment-api", "latency_p99_ms", limit=30)
        if up_pts:
            candidates["upstream_payment_p99"] = ("payment-api", [p.value for p in up_pts])
            
    correlations = CorrelationEngine.correlate_incident_signals("latency_p99_ms", primary_series, candidates)
    return {
        "service": service,
        "primary_metric": "latency_p99_ms",
        "correlations": [c.model_dump() for c in correlations]
    }

@router.post("/tick", summary="Simulate next telemetry clock tick with optional chaos")
async def trigger_tick(chaos_scenario: str = "nominal"):
    points = TelemetryGenerator.emit_tick(chaos_scenario)
    return {
        "status": "emitted",
        "points_count": len(points),
        "chaos_applied": chaos_scenario
    }
