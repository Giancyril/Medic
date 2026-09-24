"""
Backend telemetry and SLO evaluation pytest suite.
"""
import asyncio
import pytest
from backend.telemetry.models import TelemetryPoint, SLODefinition, SLIType
from backend.telemetry.buffer import TelemetryBuffer
from backend.telemetry.correlator import CorrelationEngine
from backend.telemetry.generator import TelemetryGenerator

@pytest.fixture
def buf():
    """Fresh buffer for each test."""
    return TelemetryBuffer(max_points_per_metric=100)

def test_telemetry_buffer_ingest_and_retrieve(buf):
    p = TelemetryPoint(metric_name="error_rate_pct", service="order-processor", value=12.5)
    buf.ingest_point(p)
    series = buf.get_series("order-processor", "error_rate_pct")
    assert len(series) == 1
    assert series[0].value == 12.5

def test_telemetry_buffer_multiple_points(buf):
    for i in range(50):
        buf.ingest_point(TelemetryPoint(metric_name="latency_p99_ms", service="payment-api", value=float(100 + i * 10)))
    series = buf.get_series("payment-api", "latency_p99_ms", limit=20)
    assert len(series) == 20
    assert series[-1].value == 590.0

def test_slo_evaluation_availability_healthy(buf):
    status = buf.evaluate_slo("slo-order-availability", {"error_rate_pct": 0.1})
    assert status.status == "healthy"
    assert status.burn_rate <= 1.0
    assert not status.is_breached

def test_slo_evaluation_availability_breached(buf):
    status = buf.evaluate_slo("slo-order-availability", {"error_rate_pct": 8.5})
    assert status.status == "critical"
    assert status.burn_rate > 1.0
    assert status.is_breached

def test_slo_evaluation_latency_breached(buf):
    status = buf.evaluate_slo("slo-order-latency", {"latency_p99_ms": 2400.0})
    assert status.burn_rate > 2.0
    assert status.is_breached

def test_slo_evaluation_unknown_id(buf):
    with pytest.raises(KeyError):
        buf.evaluate_slo("slo-nonexistent")

def test_correlation_engine_high_correlation():
    p_lat = [120.0, 180.0, 350.0, 850.0, 1800.0, 3400.0]
    mem    = [55.0,  65.0,  74.0,  87.0,  95.0,   99.0]
    rand   = [22.0,  45.0,  18.0,  77.0,  31.0,   50.0]
    res = CorrelationEngine.correlate_incident_signals(
        "latency_p99_ms", p_lat,
        {"memory_saturation_pct": ("order-processor", mem),
         "irrelevant_noise":      ("order-processor", rand)}
    )
    assert len(res) >= 1
    assert res[0].signal_name == "memory_saturation_pct"
    assert res[0].correlation_coefficient >= 0.85

def test_correlation_engine_no_correlation():
    flat = [100.0] * 6
    other = [50.0] * 6
    res = CorrelationEngine.correlate_incident_signals("x", flat, {"y": ("svc", other)})
    assert res == []

def test_cascading_anomaly_detection():
    signals = {
        "checkout": {"error_rate_pct": 18.0, "latency_p99_ms": 2800.0, "memory_saturation_pct": 45.0},
        "auth":     {"error_rate_pct": 0.2,  "latency_p99_ms": 90.0,   "memory_saturation_pct": 50.0},
    }
    cascades = CorrelationEngine.detect_cascading_anomalies(signals)
    assert len(cascades) == 1
    assert cascades[0]["service"] == "checkout"

def test_generator_nominal_tick():
    points = TelemetryGenerator.emit_tick("nominal")
    assert len(points) > 0
    services = {p.service for p in points}
    assert "order-processor" in services
    assert "payment-api" in services

def test_generator_oom_chaos_tick():
    points = TelemetryGenerator.emit_tick("OOMKilled")
    # At least one memory saturation point should be high for order-processor
    oom_mem = [p for p in points if p.service == "order-processor" and p.metric_name == "memory_saturation_pct"]
    assert any(p.value > 90.0 for p in oom_mem)

