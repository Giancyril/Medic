"""
Microservice Topology & Blast Radius Models.
Defines service graph nodes, dependencies, real-time health states, and blast radius impact assessment.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class NodeHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"

class ServiceTier(str, Enum):
    TIER_0_CRITICAL = "tier_0"  # Direct revenue / core gateway
    TIER_1_CORE = "tier_1"      # Core checkout/auth/billing
    TIER_2_SUPPORTING = "tier_2"# Notifications, telemetry, recommendation

class ProtocolType(str, Enum):
    GRPC = "grpc"
    HTTP = "http"
    REDIS = "redis"
    POSTGRES = "postgres"
    KAFKA = "kafka"

class ServiceNode(BaseModel):
    id: str = Field(..., description="Unique service ID, e.g., 'checkout-api'")
    name: str = Field(..., description="Human-readable service name")
    tier: ServiceTier = Field(default=ServiceTier.TIER_1_CORE)
    service_type: str = Field(default="service", description="service, database, cache, or queue")
    health: NodeHealth = Field(default=NodeHealth.HEALTHY)
    replicas_ready: int = Field(default=3)
    replicas_desired: int = Field(default=3)
    current_rps: float = Field(default=120.0)
    error_rate_pct: float = Field(default=0.02)
    p99_latency_ms: float = Field(default=45.0)
    active_incidents: List[str] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)

class ServiceEdge(BaseModel):
    source: str = Field(..., description="Caller service ID")
    target: str = Field(..., description="Target service ID")
    protocol: ProtocolType = Field(default=ProtocolType.HTTP)
    latency_p99_ms: float = Field(default=25.0)
    error_rate: float = Field(default=0.0)
    call_volume_rps: float = Field(default=150.0)

class BlastRadiusReport(BaseModel):
    origin_service: str
    direct_upstream: List[str] = Field(default_factory=list, description="Services that call this service directly")
    indirect_upstream: List[str] = Field(default_factory=list, description="Services indirectly affected higher up the stack")
    direct_downstream: List[str] = Field(default_factory=list, description="Services this service calls directly")
    indirect_downstream: List[str] = Field(default_factory=list, description="Transitive dependencies below this service")
    affected_tiers: List[ServiceTier] = Field(default_factory=list)
    critical_services_impacted: List[str] = Field(default_factory=list)
    total_blast_score: float = Field(default=0.0, description="Computed blast radius risk score (0-100)")
    mitigation_guidance: str = Field(default="")
    evaluated_at: str = Field(default_factory=utc_now)

class TopologyGraph(BaseModel):
    nodes: List[ServiceNode]
    edges: List[ServiceEdge]
    healthy_count: int = 0
    degraded_count: int = 0
    failing_count: int = 0
    last_updated: str = Field(default_factory=utc_now)
