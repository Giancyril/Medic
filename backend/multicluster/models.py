"""
Multi-Cluster Global Failover & Traffic Routing Models.
Defines schemas for multi-region Kubernetes clusters, global ingress traffic weights,
regional health matrices, and automated failover/drain state transitions.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class ClusterStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DRAINING = "draining"
    DRAINED = "drained"
    OFFLINE = "offline"

class FailoverEventType(str, Enum):
    DRAIN_INITIATED = "drain_initiated"
    TRAFFIC_SHIFTED = "traffic_shifted"
    CLUSTER_ISOLATED = "cluster_isolated"
    TRAFFIC_RESTORED = "traffic_restored"

class ClusterRegion(BaseModel):
    cluster_id: str
    name: str
    region_code: str
    is_primary: bool = False
    status: ClusterStatus = ClusterStatus.HEALTHY
    traffic_weight_pct: int = Field(..., ge=0, le=100)
    node_count: int = 12
    active_pods: int = 84
    p99_latency_ms: float = 24.5
    error_rate_pct: float = 0.02
    ingress_rps: int = 1250
    cloud_provider: str = "AWS EKS"
    last_health_check: str = Field(default_factory=utc_now)

class FailoverEvent(BaseModel):
    event_id: str
    timestamp: str = Field(default_factory=utc_now)
    cluster_id: str
    event_type: FailoverEventType
    summary: str
    source_weight: int
    target_weight: int
    initiator: str = "Autonomous Failover Controller"

class MultiClusterOverview(BaseModel):
    evaluated_at: str = Field(default_factory=utc_now)
    total_clusters: int
    healthy_clusters: int
    total_ingress_rps: int
    dns_routing_policy: str = "Latency-Optimized Anycast Geo-DNS"
    clusters: List[ClusterRegion]
    recent_events: List[FailoverEvent]
