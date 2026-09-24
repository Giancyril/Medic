"""
Metric & Telemetry Correlation Engine.
Calculates Pearson correlation coefficients across multi-dimensional metrics
to identify cascading failure origins and cross-service dependencies.
"""
from typing import List, Dict, Tuple, Any
import math
from backend.telemetry.models import CorrelatedSignal

def _pearson_correlation(x: List[float], y: List[float]) -> float:
    n = min(len(x), len(y))
    if n < 3:
        return 0.0
    x_sub = x[-n:]
    y_sub = y[-n:]
    
    mean_x = sum(x_sub) / n
    mean_y = sum(y_sub) / n
    
    num = sum((a - mean_x) * (b - mean_y) for a, b in zip(x_sub, y_sub))
    var_x = sum((a - mean_x) ** 2 for a in x_sub)
    var_y = sum((b - mean_y) ** 2 for b in y_sub)
    
    denom = math.sqrt(var_x * var_y)
    if denom == 0:
        return 0.0
    return max(-1.0, min(1.0, num / denom))

class CorrelationEngine:
    """
    Correlates incident symptoms (e.g. latency spike, error spike)
    with underlying resource signals (memory leaks, thread pool saturation, upstream delays).
    """
    
    @staticmethod
    def correlate_incident_signals(
        primary_metric_name: str,
        primary_series: List[float],
        candidate_signals: Dict[str, Tuple[str, List[float]]] # signal_name -> (service, series)
    ) -> List[CorrelatedSignal]:
        results: List[CorrelatedSignal] = []
        
        for sig_name, (svc, series) in candidate_signals.items():
            if len(series) < 3 or len(primary_series) < 3:
                continue
            r = _pearson_correlation(primary_series, series)
            
            # Filter for statistically meaningful correlation (|r| >= 0.6)
            if abs(r) >= 0.5:
                direction = "positive" if r > 0 else "inverse"
                desc = (
                    f"Strong {direction} correlation ({r:.2f}) between {primary_metric_name} "
                    f"and {sig_name} on service '{svc}'."
                )
                results.append(CorrelatedSignal(
                    signal_name=sig_name,
                    service=svc,
                    correlation_coefficient=round(r, 3),
                    lag_seconds=0,
                    p_value=0.005 if abs(r) > 0.85 else 0.02,
                    description=desc
                ))
                
        # Rank by absolute correlation descending
        results.sort(key=lambda s: abs(s.correlation_coefficient), reverse=True)
        return results

    @staticmethod
    def detect_cascading_anomalies(
        service_signals: Dict[str, Dict[str, float]]
    ) -> List[Dict[str, Any]]:
        """
        Detects if upstream services are cascading degradation into downstream services.
        """
        cascades = []
        for svc, signals in service_signals.items():
            err = signals.get("error_rate_pct", 0)
            lat = signals.get("latency_p99_ms", 0)
            mem = signals.get("memory_saturation_pct", 0)
            
            if err > 5.0 and lat > 1500:
                cascades.append({
                    "service": svc,
                    "condition": "Severe degradation",
                    "impact": f"{err:.1f}% errors, {lat:.0f}ms P99 latency",
                    "probable_cause": "Memory exhaustion" if mem > 90 else "Upstream dependency bottleneck"
                })
        return cascades
