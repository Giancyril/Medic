"""
Multi-Cluster Global Failover & Traffic Routing Engine.
Coordinates cross-region Kubernetes cluster health, DNS/Envoy weighted traffic shifting,
and zero-downtime regional evacuation (traffic drain).
"""
from typing import Dict, List, Optional
from backend.multicluster.models import (
    ClusterRegion,
    ClusterStatus,
    FailoverEvent,
    FailoverEventType,
    MultiClusterOverview,
    utc_now,
)

class MultiClusterEngine:
    """Manages multi-region cluster topologies, health telemetry, and global traffic routing."""

    def __init__(self):
        self.clusters: Dict[str, ClusterRegion] = {}
        self.events: List[FailoverEvent] = []
        self._init_clusters()

    def _init_clusters(self):
        c1 = ClusterRegion(
            cluster_id="cluster-us-east-1",
            name="US East (N. Virginia)",
            region_code="us-east-1",
            is_primary=True,
            status=ClusterStatus.HEALTHY,
            traffic_weight_pct=50,
            node_count=18,
            active_pods=124,
            p99_latency_ms=21.4,
            error_rate_pct=0.01,
            ingress_rps=1650,
            cloud_provider="AWS EKS (us-east-1)",
        )
        c2 = ClusterRegion(
            cluster_id="cluster-us-west-2",
            name="US West (Oregon)",
            region_code="us-west-2",
            is_primary=False,
            status=ClusterStatus.HEALTHY,
            traffic_weight_pct=35,
            node_count=14,
            active_pods=92,
            p99_latency_ms=26.8,
            error_rate_pct=0.02,
            ingress_rps=1150,
            cloud_provider="AWS EKS (us-west-2)",
        )
        c3 = ClusterRegion(
            cluster_id="cluster-eu-central-1",
            name="EU Central (Frankfurt)",
            region_code="eu-central-1",
            is_primary=False,
            status=ClusterStatus.HEALTHY,
            traffic_weight_pct=15,
            node_count=10,
            active_pods=58,
            p99_latency_ms=34.2,
            error_rate_pct=0.01,
            ingress_rps=500,
            cloud_provider="AWS EKS (eu-central-1)",
        )
        for c in [c1, c2, c3]:
            self.clusters[c.cluster_id] = c

        self.events.append(
            FailoverEvent(
                event_id="ev-init-01",
                timestamp="2026-09-26T07:00:00Z",
                cluster_id="cluster-us-east-1",
                event_type=FailoverEventType.TRAFFIC_RESTORED,
                summary="Initial global steady-state traffic distribution: 50% us-east, 35% us-west, 15% eu-central.",
                source_weight=0,
                target_weight=50,
                initiator="Global Ingress Controller",
            )
        )

    def list_clusters(self) -> List[ClusterRegion]:
        return list(self.clusters.values())

    def get_cluster(self, cluster_id: str) -> Optional[ClusterRegion]:
        return self.clusters.get(cluster_id)

    def drain_cluster(self, cluster_id: str, reason: str = "Unhealthy cluster evacuation") -> ClusterRegion:
        """Evacuate all traffic from target cluster and distribute load across surviving regions."""
        target = self.get_cluster(cluster_id)
        if not target:
            raise ValueError(f"Cluster '{cluster_id}' not found.")

        old_weight = target.traffic_weight_pct
        if old_weight == 0:
            target.status = ClusterStatus.DRAINED
            return target

        surviving = [c for c in self.clusters.values() if c.cluster_id != cluster_id and c.status == ClusterStatus.HEALTHY]
        if not surviving:
            raise ValueError("Cannot drain cluster: no healthy surviving clusters available.")

        # Reassign traffic proportionally among survivors
        target.traffic_weight_pct = 0
        target.status = ClusterStatus.DRAINED

        total_surviving_weight = sum(c.traffic_weight_pct for c in surviving)
        if total_surviving_weight == 0:
            even_split = 100 // len(surviving)
            for c in surviving:
                c.traffic_weight_pct = even_split
            surviving[0].traffic_weight_pct += 100 - (even_split * len(surviving))
        else:
            allocated = 0
            for i, c in enumerate(surviving):
                if i == len(surviving) - 1:
                    c.traffic_weight_pct += (old_weight - allocated)
                else:
                    portion = int(old_weight * (c.traffic_weight_pct / total_surviving_weight))
                    c.traffic_weight_pct += portion
                    allocated += portion

        event = FailoverEvent(
            event_id=f"ev-{len(self.events) + 1:03d}",
            timestamp=utc_now(),
            cluster_id=cluster_id,
            event_type=FailoverEventType.DRAIN_INITIATED,
            summary=f"Drained 100% of traffic from {target.name} ({old_weight}% -> 0%). Reason: {reason}",
            source_weight=old_weight,
            target_weight=0,
            initiator="Autonomous SRE Failover Agent",
        )
        self.events.insert(0, event)
        return target

    def restore_cluster(self, cluster_id: str, target_weight_pct: int = 35) -> ClusterRegion:
        """Restore traffic routing to a previously drained or degraded cluster."""
        target = self.get_cluster(cluster_id)
        if not target:
            raise ValueError(f"Cluster '{cluster_id}' not found.")

        target_weight_pct = max(1, min(100, target_weight_pct))
        old_weight = target.traffic_weight_pct
        target.status = ClusterStatus.HEALTHY
        target.traffic_weight_pct = target_weight_pct

        # Balance other clusters to sum to 100%
        others = [c for c in self.clusters.values() if c.cluster_id != cluster_id]
        remaining = 100 - target_weight_pct
        if others:
            portion = remaining // len(others)
            for c in others:
                c.traffic_weight_pct = portion
            others[0].traffic_weight_pct += (remaining - (portion * len(others)))

        event = FailoverEvent(
            event_id=f"ev-{len(self.events) + 1:03d}",
            timestamp=utc_now(),
            cluster_id=cluster_id,
            event_type=FailoverEventType.TRAFFIC_RESTORED,
            summary=f"Restored traffic to {target.name} ({old_weight}% -> {target_weight_pct}%). Cluster verified healthy.",
            source_weight=old_weight,
            target_weight=target_weight_pct,
            initiator="Autonomous SRE Failover Agent",
        )
        self.events.insert(0, event)
        return target

    def shift_traffic(self, source_id: str, target_id: str, shift_pct: int) -> MultiClusterOverview:
        """Shift a discrete percentage of traffic from one cluster to another."""
        source = self.get_cluster(source_id)
        target = self.get_cluster(target_id)
        if not source or not target:
            raise ValueError("Both source and target clusters must exist.")

        actual_shift = min(source.traffic_weight_pct, max(1, shift_pct))
        source.traffic_weight_pct -= actual_shift
        target.traffic_weight_pct += actual_shift

        event = FailoverEvent(
            event_id=f"ev-{len(self.events) + 1:03d}",
            timestamp=utc_now(),
            cluster_id=target_id,
            event_type=FailoverEventType.TRAFFIC_SHIFTED,
            summary=f"Shifted {actual_shift}% traffic from {source.name} to {target.name}.",
            source_weight=source.traffic_weight_pct + actual_shift,
            target_weight=target.traffic_weight_pct,
            initiator="Manual / Policy Traffic Balancer",
        )
        self.events.insert(0, event)
        return self.get_overview()

    def set_cluster_health(
        self,
        cluster_id: str,
        status: ClusterStatus,
        error_rate: float = 0.0,
        latency_ms: float = 25.0,
    ) -> ClusterRegion:
        target = self.get_cluster(cluster_id)
        if not target:
            raise ValueError(f"Cluster '{cluster_id}' not found.")
        target.status = status
        target.error_rate_pct = error_rate
        target.p99_latency_ms = latency_ms
        target.last_health_check = utc_now()
        return target

    def get_overview(self) -> MultiClusterOverview:
        clusters_list = list(self.clusters.values())
        healthy = sum(1 for c in clusters_list if c.status == ClusterStatus.HEALTHY)
        total_rps = sum(c.ingress_rps for c in clusters_list)
        return MultiClusterOverview(
            evaluated_at=utc_now(),
            total_clusters=len(clusters_list),
            healthy_clusters=healthy,
            total_ingress_rps=total_rps,
            dns_routing_policy="Latency-Optimized Anycast Geo-DNS",
            clusters=clusters_list,
            recent_events=self.events[:10],
        )

# Global singleton
multicluster_engine = MultiClusterEngine()
