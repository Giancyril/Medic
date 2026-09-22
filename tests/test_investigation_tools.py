import pytest
from backend.tools.cluster_simulator import simulator
from backend.tools.prometheus import get_golden_signals
from backend.tools.kubernetes import inspect_pods, inspect_events, inspect_deployment
from backend.tools.log_tailer import tail_pod_logs
from backend.tools.investigator import collect_evidence

@pytest.mark.asyncio
async def test_golden_signals_healthy():
    signals = await get_golden_signals("order-processor", "production")
    assert signals["service"] == "order-processor"
    s = signals["signals"]
    assert "request_rate_rps" in s
    assert "error_rate_pct" in s
    assert "latency_p99_ms" in s
    assert "memory_saturation_pct" in s
    assert "cpu_saturation_pct" in s
    assert "timeline" in signals
    assert len(signals["timeline"]["timestamps"]) == 15

@pytest.mark.asyncio
async def test_kubernetes_inspection():
    pods = await inspect_pods("order-processor", "production")
    assert len(pods) >= 1
    deployment = await inspect_deployment("order-processor", "production")
    assert deployment["name"] == "order-processor"
    assert deployment["replicas"] >= 1
    assert "history" in deployment

@pytest.mark.asyncio
async def test_chaos_injection_oomkilled():
    simulator.inject_chaos_scenario("OOMKilled", service="order-processor", namespace="production")
    
    evidence = await collect_evidence("order-processor", "production")
    assert evidence["service"] == "order-processor"
    assert any("OOMKilled" in a for a in evidence["anomalies"])
    assert any(p.get("exit_code") == 137 for p in evidence["pods"])
    assert evidence["logs"]["error_count"] > 0
    assert any("OutOfMemory" in err["message"] for err in evidence["logs"]["errors"])

@pytest.mark.asyncio
async def test_chaos_injection_crashloop():
    simulator.inject_chaos_scenario("CrashLoopBackOff", service="payment-api", namespace="production")
    
    evidence = await collect_evidence("payment-api", "production")
    assert any("CrashLoopBackOff" in a for a in evidence["anomalies"])
    assert evidence["logs"]["error_count"] > 0
    assert any("KeyError" in err["message"] for err in evidence["logs"]["errors"])
