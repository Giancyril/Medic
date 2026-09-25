"""
Microservice Dependency Topology & Blast Radius Engine.
Maintains service mesh topology, dynamically correlates incident impact, and calculates blast radius.
"""
from typing import Dict, List, Set, Optional
from collections import deque
from backend.topology.models import (
    NodeHealth,
    ServiceTier,
    ProtocolType,
    ServiceNode,
    ServiceEdge,
    BlastRadiusReport,
    TopologyGraph,
    utc_now,
)

class TopologyEngine:
    """Manages the cluster service dependency graph and analyzes blast radius."""

    def __init__(self):
        self.nodes: Dict[str, ServiceNode] = {}
        self.edges: List[ServiceEdge] = []
        self._init_default_topology()

    def _init_default_topology(self):
        """Seed a representative modern Kubernetes microservices deployment."""
        default_nodes = [
            ServiceNode(
                id="edge-ingress",
                name="Edge Ingress Controller",
                tier=ServiceTier.TIER_0_CRITICAL,
                service_type="ingress",
                replicas_ready=4,
                replicas_desired=4,
                current_rps=1450.0,
                error_rate_pct=0.01,
                p99_latency_ms=12.0,
            ),
            ServiceNode(
                id="api-gateway",
                name="API Gateway",
                tier=ServiceTier.TIER_0_CRITICAL,
                service_type="gateway",
                replicas_ready=6,
                replicas_desired=6,
                current_rps=1380.0,
                error_rate_pct=0.03,
                p99_latency_ms=28.0,
            ),
            ServiceNode(
                id="auth-service",
                name="Auth & Session Service",
                tier=ServiceTier.TIER_1_CORE,
                service_type="service",
                replicas_ready=3,
                replicas_desired=3,
                current_rps=520.0,
                error_rate_pct=0.02,
                p99_latency_ms=18.0,
            ),
            ServiceNode(
                id="checkout-api",
                name="Checkout & Cart API",
                tier=ServiceTier.TIER_0_CRITICAL,
                service_type="service",
                replicas_ready=4,
                replicas_desired=4,
                current_rps=380.0,
                error_rate_pct=0.04,
                p99_latency_ms=65.0,
            ),
            ServiceNode(
                id="payment-svc",
                name="Payment Processing Engine",
                tier=ServiceTier.TIER_0_CRITICAL,
                service_type="service",
                replicas_ready=3,
                replicas_desired=3,
                current_rps=190.0,
                error_rate_pct=0.02,
                p99_latency_ms=110.0,
            ),
            ServiceNode(
                id="order-db",
                name="Order Primary PostgreSQL",
                tier=ServiceTier.TIER_1_CORE,
                service_type="database",
                replicas_ready=2,
                replicas_desired=2,
                current_rps=280.0,
                error_rate_pct=0.0,
                p99_latency_ms=8.5,
            ),
            ServiceNode(
                id="redis-cache",
                name="Distributed Redis Cluster",
                tier=ServiceTier.TIER_1_CORE,
                service_type="cache",
                replicas_ready=3,
                replicas_desired=3,
                current_rps=980.0,
                error_rate_pct=0.0,
                p99_latency_ms=2.1,
            ),
            ServiceNode(
                id="kafka-broker",
                name="Kafka Event Bus",
                tier=ServiceTier.TIER_1_CORE,
                service_type="queue",
                replicas_ready=3,
                replicas_desired=3,
                current_rps=640.0,
                error_rate_pct=0.0,
                p99_latency_ms=5.0,
            ),
            ServiceNode(
                id="notification-svc",
                name="Notification Worker",
                tier=ServiceTier.TIER_2_SUPPORTING,
                service_type="worker",
                replicas_ready=2,
                replicas_desired=2,
                current_rps=85.0,
                error_rate_pct=0.01,
                p99_latency_ms=45.0,
            ),
            ServiceNode(
                id="analytics-pipeline",
                name="Real-time Stream Analytics",
                tier=ServiceTier.TIER_2_SUPPORTING,
                service_type="worker",
                replicas_ready=2,
                replicas_desired=2,
                current_rps=140.0,
                error_rate_pct=0.02,
                p99_latency_ms=35.0,
            ),
        ]

        for n in default_nodes:
            self.nodes[n.id] = n

        self.edges = [
            ServiceEdge(source="edge-ingress", target="api-gateway", protocol=ProtocolType.HTTP, latency_p99_ms=10.0, call_volume_rps=1400.0),
            ServiceEdge(source="api-gateway", target="auth-service", protocol=ProtocolType.GRPC, latency_p99_ms=15.0, call_volume_rps=500.0),
            ServiceEdge(source="api-gateway", target="checkout-api", protocol=ProtocolType.HTTP, latency_p99_ms=45.0, call_volume_rps=380.0),
            ServiceEdge(source="checkout-api", target="payment-svc", protocol=ProtocolType.GRPC, latency_p99_ms=80.0, call_volume_rps=190.0),
            ServiceEdge(source="checkout-api", target="order-db", protocol=ProtocolType.POSTGRES, latency_p99_ms=12.0, call_volume_rps=280.0),
            ServiceEdge(source="checkout-api", target="redis-cache", protocol=ProtocolType.REDIS, latency_p99_ms=2.5, call_volume_rps=850.0),
            ServiceEdge(source="checkout-api", target="kafka-broker", protocol=ProtocolType.KAFKA, latency_p99_ms=6.0, call_volume_rps=220.0),
            ServiceEdge(source="kafka-broker", target="notification-svc", protocol=ProtocolType.KAFKA, latency_p99_ms=8.0, call_volume_rps=85.0),
            ServiceEdge(source="kafka-broker", target="analytics-pipeline", protocol=ProtocolType.KAFKA, latency_p99_ms=14.0, call_volume_rps=140.0),
        ]

    def get_graph(self) -> TopologyGraph:
        """Return the current topology graph snapshot with calculated status tallies."""
        healthy = sum(1 for n in self.nodes.values() if n.health == NodeHealth.HEALTHY)
        degraded = sum(1 for n in self.nodes.values() if n.health == NodeHealth.DEGRADED)
        failing = sum(1 for n in self.nodes.values() if n.health == NodeHealth.FAILING)

        return TopologyGraph(
            nodes=list(self.nodes.values()),
            edges=self.edges,
            healthy_count=healthy,
            degraded_count=degraded,
            failing_count=failing,
            last_updated=utc_now(),
        )

    def set_service_health(
        self,
        service_id: str,
        health: NodeHealth,
        incident_id: Optional[str] = None,
        error_rate_pct: Optional[float] = None,
        p99_latency_ms: Optional[float] = None,
    ):
        """Update a service node's operational state."""
        node = self.nodes.get(service_id)
        if not node:
            return
        node.health = health
        if incident_id and incident_id not in node.active_incidents:
            node.active_incidents.append(incident_id)
        if error_rate_pct is not None:
            node.error_rate_pct = error_rate_pct
        if p99_latency_ms is not None:
            node.p99_latency_ms = p99_latency_ms

    def clear_service_incidents(self, service_id: str):
        """Reset service node health back to healthy once incident is resolved."""
        node = self.nodes.get(service_id)
        if node:
            node.health = NodeHealth.HEALTHY
            node.active_incidents = []
            node.error_rate_pct = 0.01

    def calculate_blast_radius(self, service_id: str) -> BlastRadiusReport:
        """
        Analyze blast radius of a failure at `service_id`:
        Traverses upstream to find callers whose traffic will fail or cascade,
        and downstream to find root dependencies.
        """
        if service_id not in self.nodes:
            return BlastRadiusReport(
                origin_service=service_id,
                total_blast_score=0.0,
                mitigation_guidance=f"Service '{service_id}' not found in active topology graph.",
            )

        # Build adjacency maps: upstream (caller -> callee, so callee -> callers for upstream)
        callers_map: Dict[str, List[str]] = {n: [] for n in self.nodes}
        dependencies_map: Dict[str, List[str]] = {n: [] for n in self.nodes}

        for edge in self.edges:
            dependencies_map[edge.source].append(edge.target)
            callers_map[edge.target].append(edge.source)

        # Direct callers & upstream cascade (BFS)
        direct_upstream = list(callers_map.get(service_id, []))
        indirect_upstream: List[str] = []
        visited_upstream: Set[str] = set([service_id] + direct_upstream)
        queue: deque[str] = deque(direct_upstream)

        while queue:
            curr = queue.popleft()
            for parent in callers_map.get(curr, []):
                if parent not in visited_upstream:
                    visited_upstream.add(parent)
                    indirect_upstream.append(parent)
                    queue.append(parent)

        # Direct downstream & transitive dependencies (BFS)
        direct_downstream = list(dependencies_map.get(service_id, []))
        indirect_downstream: List[str] = []
        visited_downstream: Set[str] = set([service_id] + direct_downstream)
        queue_down: deque[str] = deque(direct_downstream)

        while queue_down:
            curr = queue_down.popleft()
            for child in dependencies_map.get(curr, []):
                if child not in visited_downstream:
                    visited_downstream.add(child)
                    indirect_downstream.append(child)
                    queue_down.append(child)

        # Calculate affected tiers and critical services
        all_affected = set([service_id] + direct_upstream + indirect_upstream)
        affected_tiers_set = set()
        critical_services: List[str] = []
        tier_weights = {
            ServiceTier.TIER_0_CRITICAL: 35.0,
            ServiceTier.TIER_1_CORE: 15.0,
            ServiceTier.TIER_2_SUPPORTING: 5.0,
        }
        score = 0.0

        for aff_id in all_affected:
            node = self.nodes.get(aff_id)
            if node:
                affected_tiers_set.add(node.tier)
                score += tier_weights.get(node.tier, 10.0)
                if node.tier == ServiceTier.TIER_0_CRITICAL:
                    critical_services.append(aff_id)

        # Cap score at 100.0
        final_score = min(100.0, round(score, 1))

        # Mitigation guidance
        guidance = []
        if "checkout-api" in all_affected or "payment-svc" in all_affected:
            guidance.append("Activate checkout circuit breaker and switch to offline order queue.")
        if "edge-ingress" in all_affected or "api-gateway" in all_affected:
            guidance.append("Engage Cloudflare rate-limiting and return cached 503 fallback pages.")
        if not guidance:
            guidance.append("Isolate target pod replicas and enable fallback response stubs.")

        return BlastRadiusReport(
            origin_service=service_id,
            direct_upstream=direct_upstream,
            indirect_upstream=indirect_upstream,
            direct_downstream=direct_downstream,
            indirect_downstream=indirect_downstream,
            affected_tiers=sorted(list(affected_tiers_set)),
            critical_services_impacted=critical_services,
            total_blast_score=final_score,
            mitigation_guidance=" ".join(guidance),
            evaluated_at=utc_now(),
        )

# Global singleton topology engine
topology_engine = TopologyEngine()
