"""
Alert Deduplication & Incident Grouping Engine.
Groups incoming alerts by fingerprint, topology affinity, and temporal locality.
"""
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
from backend.grouping.models import (
    GroupedAlertItem,
    IncidentCluster,
    NoiseReductionStats,
    utc_now,
)

class AlertGroupingEngine:
    """Manages alert deduplication, fingerprinting, and semantic clustering."""

    def __init__(self):
        self.clusters: Dict[str, IncidentCluster] = {}
        self.raw_alert_count: int = 0
        self.duplicate_count: int = 0
        self._init_demo_clusters()

    def generate_fingerprint(self, service: str, alert_name: str, environment: str = "production") -> str:
        """Create deterministic 12-char fingerprint for alert deduplication."""
        raw = f"{environment}:{service}:{alert_name.lower().strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]

    def _init_demo_clusters(self):
        """Seed realistic clustered alert storms for immediate dashboard analysis."""
        c1_alerts = [
            GroupedAlertItem(
                alert_id="alt-101",
                alert_name="KubePodCrashLooping",
                service="checkout-api",
                severity="critical",
                fired_at="2026-09-25T19:10:00Z",
                fingerprint=self.generate_fingerprint("checkout-api", "KubePodCrashLooping"),
                is_duplicate=False,
            ),
            GroupedAlertItem(
                alert_id="alt-102",
                alert_name="ContainerMemoryOOMKilled",
                service="checkout-api",
                severity="critical",
                fired_at="2026-09-25T19:10:20Z",
                fingerprint=self.generate_fingerprint("checkout-api", "ContainerMemoryOOMKilled"),
                is_duplicate=False,
            ),
            GroupedAlertItem(
                alert_id="alt-103",
                alert_name="ContainerMemoryOOMKilled",
                service="checkout-api",
                severity="critical",
                fired_at="2026-09-25T19:11:05Z",
                fingerprint=self.generate_fingerprint("checkout-api", "ContainerMemoryOOMKilled"),
                is_duplicate=True,
            ),
            GroupedAlertItem(
                alert_id="alt-104",
                alert_name="HighHttp5xxRate",
                service="checkout-api",
                severity="critical",
                fired_at="2026-09-25T19:11:45Z",
                fingerprint=self.generate_fingerprint("checkout-api", "HighHttp5xxRate"),
                is_duplicate=False,
            ),
            GroupedAlertItem(
                alert_id="alt-105",
                alert_name="DownstreamServiceUnavailable",
                service="api-gateway",
                severity="warning",
                fired_at="2026-09-25T19:12:10Z",
                fingerprint=self.generate_fingerprint("api-gateway", "DownstreamServiceUnavailable"),
                is_duplicate=False,
            ),
            GroupedAlertItem(
                alert_id="alt-106",
                alert_name="HighHttp5xxRate",
                service="checkout-api",
                severity="critical",
                fired_at="2026-09-25T19:12:40Z",
                fingerprint=self.generate_fingerprint("checkout-api", "HighHttp5xxRate"),
                is_duplicate=True,
            ),
        ]

        c1 = IncidentCluster(
            cluster_id="cluster-checkout-oom-storm",
            title="Checkout API Memory Leak & Gateway Cascading 5xx",
            primary_service="checkout-api",
            root_cause_candidate="Pod OOMKilled leading to degraded pool",
            severity="critical",
            alerts_count=len(c1_alerts),
            duplicate_count=2,
            first_seen="2026-09-25T19:10:00Z",
            last_seen="2026-09-25T19:12:40Z",
            alerts=c1_alerts,
            similarity_score=0.96,
            noise_reduction_pct=round(((len(c1_alerts) - 1) / len(c1_alerts)) * 100, 1),
        )

        c2_alerts = [
            GroupedAlertItem(
                alert_id="alt-201",
                alert_name="RedisConnectionPoolExhausted",
                service="redis-cache",
                severity="warning",
                fired_at="2026-09-25T18:45:00Z",
                fingerprint=self.generate_fingerprint("redis-cache", "RedisConnectionPoolExhausted"),
                is_duplicate=False,
            ),
            GroupedAlertItem(
                alert_id="alt-202",
                alert_name="RedisLatencySpikeP99",
                service="redis-cache",
                severity="warning",
                fired_at="2026-09-25T18:46:15Z",
                fingerprint=self.generate_fingerprint("redis-cache", "RedisLatencySpikeP99"),
                is_duplicate=False,
            ),
            GroupedAlertItem(
                alert_id="alt-203",
                alert_name="RedisConnectionPoolExhausted",
                service="redis-cache",
                severity="warning",
                fired_at="2026-09-25T18:47:00Z",
                fingerprint=self.generate_fingerprint("redis-cache", "RedisConnectionPoolExhausted"),
                is_duplicate=True,
            ),
        ]

        c2 = IncidentCluster(
            cluster_id="cluster-redis-pool-exhaustion",
            title="Distributed Redis Cluster High Connection Contention",
            primary_service="redis-cache",
            root_cause_candidate="Connection pool limit reached under burst traffic",
            severity="warning",
            alerts_count=len(c2_alerts),
            duplicate_count=1,
            first_seen="2026-09-25T18:45:00Z",
            last_seen="2026-09-25T18:47:00Z",
            alerts=c2_alerts,
            similarity_score=0.88,
            noise_reduction_pct=round(((len(c2_alerts) - 1) / len(c2_alerts)) * 100, 1),
        )

        self.clusters[c1.cluster_id] = c1
        self.clusters[c2.cluster_id] = c2
        self.raw_alert_count = len(c1_alerts) + len(c2_alerts)
        self.duplicate_count = 3

    def ingest_alert(self, alert_id: str, alert_name: str, service: str, severity: str) -> IncidentCluster:
        """
        Deduplicate and cluster incoming alert into an existing or new cluster.
        """
        fp = self.generate_fingerprint(service, alert_name)
        self.raw_alert_count += 1

        # Check if matches any existing cluster's primary service or related service
        target_cluster: Optional[IncidentCluster] = None
        for c in self.clusters.values():
            if c.primary_service == service:
                target_cluster = c
                break

        now = utc_now()
        is_dup = False

        if target_cluster:
            # Check for duplicate fingerprint in this cluster
            if any(a.fingerprint == fp for a in target_cluster.alerts):
                is_dup = True
                self.duplicate_count += 1
                target_cluster.duplicate_count += 1

            new_alert = GroupedAlertItem(
                alert_id=alert_id,
                alert_name=alert_name,
                service=service,
                severity=severity,
                fired_at=now,
                fingerprint=fp,
                is_duplicate=is_dup,
            )
            target_cluster.alerts.append(new_alert)
            target_cluster.alerts_count = len(target_cluster.alerts)
            target_cluster.last_seen = now
            target_cluster.noise_reduction_pct = round(
                ((target_cluster.alerts_count - 1) / target_cluster.alerts_count) * 100, 1
            )
            return target_cluster

        # Otherwise create a new cluster
        new_cluster_id = f"cluster-{service}-{int(datetime.now().timestamp())}"
        new_alert = GroupedAlertItem(
            alert_id=alert_id,
            alert_name=alert_name,
            service=service,
            severity=severity,
            fired_at=now,
            fingerprint=fp,
            is_duplicate=False,
        )
        new_cluster = IncidentCluster(
            cluster_id=new_cluster_id,
            title=f"{service} - {alert_name} Outage Group",
            primary_service=service,
            root_cause_candidate=f"Unresolved anomaly detected in {service}",
            severity=severity,
            alerts_count=1,
            duplicate_count=0,
            first_seen=now,
            last_seen=now,
            alerts=[new_alert],
            similarity_score=1.0,
            noise_reduction_pct=0.0,
        )
        self.clusters[new_cluster_id] = new_cluster
        return new_cluster

    def get_clusters(self) -> List[IncidentCluster]:
        """Return all active incident clusters sorted by severity and recency."""
        return sorted(list(self.clusters.values()), key=lambda c: (c.severity == "critical", c.last_seen), reverse=True)

    def get_noise_reduction_stats(self) -> NoiseReductionStats:
        """Calculate overall cluster alert deduplication and noise reduction metrics."""
        raw = max(1, self.raw_alert_count)
        grouped = len(self.clusters)
        reduction = round(((raw - grouped) / raw) * 100, 1)

        return NoiseReductionStats(
            total_raw_alerts=self.raw_alert_count,
            grouped_incidents=grouped,
            duplicate_alerts_suppressed=self.duplicate_count,
            noise_reduction_pct=max(0.0, reduction),
            last_computed=utc_now(),
        )

# Global grouping engine singleton
grouping_engine = AlertGroupingEngine()
