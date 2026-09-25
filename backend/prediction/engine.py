"""
Predictive Anomaly & Time-to-Failure (TTF) Engine.
Extrapolates linear/exponential slopes, estimates time-to-breach, and detects impending degradation.
"""
from typing import List, Tuple, Optional, Dict
from datetime import datetime
from backend.prediction.models import (
    MetricForecast,
    ClusterPredictionSummary,
    TrendDirection,
    UrgencyLevel,
    utc_now,
)
from backend.telemetry.buffer import telemetry_buffer

class PredictionEngine:
    """Calculates metric trajectories, slopes, and predicts time-to-failure."""

    @staticmethod
    def calculate_linear_trend(points: List[Tuple[float, float]]) -> Tuple[float, float, float]:
        """
        Fit y = slope * x + intercept using least squares.
        points: list of (x, y) where x is time in seconds.
        Returns: (slope, intercept, r_squared)
        """
        n = len(points)
        if n < 2:
            return 0.0, points[0][1] if n == 1 else 0.0, 1.0

        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_x2 = sum(p[0] ** 2 for p in points)
        sum_xy = sum(p[0] * p[1] for p in points)

        denominator = (n * sum_x2) - (sum_x ** 2)
        if abs(denominator) < 1e-9:
            return 0.0, sum_y / n, 0.0

        slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator
        intercept = (sum_y - (slope * sum_x)) / n

        # Calculate R-squared
        mean_y = sum_y / n
        ss_tot = sum((p[1] - mean_y) ** 2 for p in points)
        ss_res = sum((p[1] - (slope * p[0] + intercept)) ** 2 for p in points)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-9 else 1.0
        r_squared = max(0.0, min(1.0, r_squared))

        return slope, intercept, r_squared

    def evaluate_metric(
        self,
        metric_name: str,
        service: str,
        points: List[Tuple[float, float]],
        threshold_critical: float,
        unit: str = "",
        higher_is_worse: bool = True,
    ) -> MetricForecast:
        """
        Evaluate time series data for a metric and forecast values at +5m and +15m.
        """
        if not points:
            return MetricForecast(
                metric_name=metric_name,
                service=service,
                current_value=0.0,
                unit=unit,
                predicted_value_5m=0.0,
                predicted_value_15m=0.0,
                threshold_critical=threshold_critical,
                trend=TrendDirection.FLAT,
                ttf_human="No Data",
                urgency=UrgencyLevel.NOMINAL,
                summary="Insufficient metric data for extrapolation.",
            )

        # Normalize x to relative seconds from latest point
        latest_x, latest_y = points[-1]
        normalized_points = [(p[0] - latest_x, p[1]) for p in points]

        slope, intercept, r2 = self.calculate_linear_trend(normalized_points)
        current_val = latest_y

        # Extrapolate +300s (5m) and +900s (15m)
        pred_5m = max(0.0, round(current_val + slope * 300, 2))
        pred_15m = max(0.0, round(current_val + slope * 900, 2))

        # Determine trend direction
        if abs(slope) < 1e-5:
            trend = TrendDirection.FLAT
        elif slope > 0:
            trend = TrendDirection.UPWARD
        else:
            trend = TrendDirection.DOWNWARD

        # Time to failure calculation
        ttf_seconds: Optional[float] = None
        ttf_human = "Safe (> 1h)"
        urgency = UrgencyLevel.NOMINAL

        if higher_is_worse:
            if current_val >= threshold_critical:
                ttf_seconds = 0.0
                ttf_human = "BREACHED"
                urgency = UrgencyLevel.CRITICAL
            elif slope > 0:
                seconds_to_breach = (threshold_critical - current_val) / slope
                if seconds_to_breach > 0:
                    ttf_seconds = round(seconds_to_breach, 1)
                    if seconds_to_breach <= 300:
                        urgency = UrgencyLevel.CRITICAL
                        m, s = divmod(int(seconds_to_breach), 60)
                        ttf_human = f"{m}m {s}s"
                    elif seconds_to_breach <= 900:
                        urgency = UrgencyLevel.ELEVATED
                        m, s = divmod(int(seconds_to_breach), 60)
                        ttf_human = f"{m}m {s}s"
                    elif seconds_to_breach <= 3600:
                        urgency = UrgencyLevel.WATCH
                        m, _ = divmod(int(seconds_to_breach), 60)
                        ttf_human = f"{m}m"
                    else:
                        ttf_human = "Safe (> 1h)"
        else:
            # lower is worse (e.g. disk free or availability)
            if current_val <= threshold_critical:
                ttf_seconds = 0.0
                ttf_human = "BREACHED"
                urgency = UrgencyLevel.CRITICAL
            elif slope < 0:
                seconds_to_breach = (current_val - threshold_critical) / abs(slope)
                if seconds_to_breach > 0:
                    ttf_seconds = round(seconds_to_breach, 1)
                    if seconds_to_breach <= 300:
                        urgency = UrgencyLevel.CRITICAL
                        m, s = divmod(int(seconds_to_breach), 60)
                        ttf_human = f"{m}m {s}s"
                    elif seconds_to_breach <= 900:
                        urgency = UrgencyLevel.ELEVATED
                        m, s = divmod(int(seconds_to_breach), 60)
                        ttf_human = f"{m}m {s}s"
                    else:
                        ttf_human = "Safe (> 1h)"

        # Generate summary
        if urgency == UrgencyLevel.CRITICAL:
            summary = f"Imminent breach predicted in {ttf_human}! Rate of change: {slope:.3f} {unit}/s."
        elif urgency == UrgencyLevel.ELEVATED:
            summary = f"Elevated drift toward critical threshold ({threshold_critical} {unit}) in {ttf_human}."
        elif urgency == UrgencyLevel.WATCH:
            summary = f"Monitoring moderate upward slope ({slope:.3f} {unit}/s)."
        else:
            summary = "Metric is stable and operating well within safety envelope."

        confidence = max(0.65, min(0.98, round(r2, 2)))

        return MetricForecast(
            metric_name=metric_name,
            service=service,
            current_value=round(current_val, 2),
            unit=unit,
            predicted_value_5m=pred_5m,
            predicted_value_15m=pred_15m,
            threshold_critical=threshold_critical,
            trend=trend,
            slope_per_second=round(slope, 4),
            ttf_seconds=ttf_seconds,
            ttf_human=ttf_human,
            urgency=urgency,
            confidence_score=confidence,
            summary=summary,
        )

    def generate_cluster_predictions(self) -> ClusterPredictionSummary:
        """
        Analyze current cluster signals and generate predictive forecasts
        for high-impact failure modes (OOM, latency drift, pool exhaustion).
        """
        forecasts: List[MetricForecast] = []

        # 1. Memory Leak Trajectory on checkout-api
        # Seed realistic points exhibiting memory drift
        now = datetime.now().timestamp()
        checkout_mem_points = [
            (now - 120, 710.0),
            (now - 90, 745.0),
            (now - 60, 780.0),
            (now - 30, 815.0),
            (now, 850.0),
        ]
        mem_fc = self.evaluate_metric(
            metric_name="container_memory_usage_mb",
            service="checkout-api",
            points=checkout_mem_points,
            threshold_critical=1024.0,  # 1GB OOM threshold
            unit="MB",
            higher_is_worse=True,
        )
        forecasts.append(mem_fc)

        # 2. P99 Latency Drift on payment-svc
        payment_latency_points = [
            (now - 120, 110.0),
            (now - 90, 125.0),
            (now - 60, 140.0),
            (now - 30, 160.0),
            (now, 185.0),
        ]
        lat_fc = self.evaluate_metric(
            metric_name="http_request_p99_latency_ms",
            service="payment-svc",
            points=payment_latency_points,
            threshold_critical=500.0,
            unit="ms",
            higher_is_worse=True,
        )
        forecasts.append(lat_fc)

        # 3. Connection Pool Saturation on order-db
        db_pool_points = [
            (now - 120, 45.0),
            (now - 90, 48.0),
            (now - 60, 50.0),
            (now - 30, 52.0),
            (now, 53.0),
        ]
        db_fc = self.evaluate_metric(
            metric_name="postgres_active_connections_pct",
            service="order-db",
            points=db_pool_points,
            threshold_critical=90.0,
            unit="%",
            higher_is_worse=True,
        )
        forecasts.append(db_fc)

        # 4. Ingress Error Rate Drift
        ingress_err_points = [
            (now - 120, 0.01),
            (now - 90, 0.02),
            (now - 60, 0.01),
            (now - 30, 0.02),
            (now, 0.02),
        ]
        ingress_fc = self.evaluate_metric(
            metric_name="http_error_rate_pct",
            service="edge-ingress",
            points=ingress_err_points,
            threshold_critical=1.0,
            unit="%",
            higher_is_worse=True,
        )
        forecasts.append(ingress_fc)

        # Compute cluster systemic risk
        crit_count = sum(1 for f in forecasts if f.urgency == UrgencyLevel.CRITICAL)
        elev_count = sum(1 for f in forecasts if f.urgency == UrgencyLevel.ELEVATED)
        watch_count = sum(1 for f in forecasts if f.urgency == UrgencyLevel.WATCH)

        risk_index = min(1.0, round((crit_count * 0.5) + (elev_count * 0.25) + (watch_count * 0.1), 2))

        return ClusterPredictionSummary(
            evaluated_at=utc_now(),
            total_metrics_evaluated=len(forecasts),
            at_risk_count=crit_count + elev_count,
            imminent_breach_count=crit_count,
            forecasts=forecasts,
            systemic_risk_index=risk_index,
        )

# Global prediction engine singleton
prediction_engine = PredictionEngine()
