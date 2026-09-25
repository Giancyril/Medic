// Day 3 Advanced Features: Topology, Predictive Anomaly, Alert Grouping & On-Call

export type NodeHealth = "healthy" | "degraded" | "failing";
export type ServiceTier = "tier_0" | "tier_1" | "tier_2";
export type ProtocolType = "grpc" | "http" | "redis" | "postgres" | "kafka";

export interface ServiceNode {
  id: string;
  name: string;
  tier: ServiceTier;
  service_type: string;
  health: NodeHealth;
  replicas_ready: number;
  replicas_desired: number;
  current_rps: number;
  error_rate_pct: number;
  p99_latency_ms: number;
  active_incidents: string[];
  tags?: Record<string, string>;
}

export interface ServiceEdge {
  source: string;
  target: string;
  protocol: ProtocolType;
  latency_p99_ms: number;
  error_rate: number;
  call_volume_rps: number;
}

export interface TopologyGraph {
  nodes: ServiceNode[];
  edges: ServiceEdge[];
  healthy_count: number;
  degraded_count: number;
  failing_count: number;
  last_updated: string;
}

export interface BlastRadiusReport {
  origin_service: string;
  direct_upstream: string[];
  indirect_upstream: string[];
  direct_downstream: string[];
  indirect_downstream: string[];
  affected_tiers: ServiceTier[];
  critical_services_impacted: string[];
  total_blast_score: number;
  mitigation_guidance: string;
  evaluated_at: string;
}

export type TrendDirection = "upward" | "downward" | "flat" | "volatile";
export type UrgencyLevel = "nominal" | "watch" | "elevated" | "critical";

export interface MetricForecast {
  metric_name: string;
  service: string;
  current_value: number;
  unit: string;
  predicted_value_5m: number;
  predicted_value_15m: number;
  threshold_critical: number;
  trend: TrendDirection;
  slope_per_second: number;
  ttf_seconds?: number | null;
  ttf_human: string;
  urgency: UrgencyLevel;
  confidence_score: number;
  summary: string;
}

export interface ClusterPredictionSummary {
  evaluated_at: string;
  total_metrics_evaluated: number;
  at_risk_count: number;
  imminent_breach_count: number;
  forecasts: MetricForecast[];
  systemic_risk_index: number;
}

export interface GroupedAlertItem {
  alert_id: string;
  alert_name: string;
  service: string;
  severity: string;
  fired_at: string;
  fingerprint: string;
  is_duplicate: boolean;
}

export interface IncidentCluster {
  cluster_id: string;
  title: string;
  primary_service: string;
  root_cause_candidate: string;
  severity: string;
  alerts_count: number;
  duplicate_count: number;
  first_seen: string;
  last_seen: string;
  alerts: GroupedAlertItem[];
  similarity_score: number;
  noise_reduction_pct: number;
}

export interface NoiseReductionStats {
  total_raw_alerts: number;
  grouped_incidents: number;
  duplicate_alerts_suppressed: number;
  noise_reduction_pct: number;
  last_computed: string;
}

export type PageStatus = "pending" | "acknowledged" | "escalated" | "resolved";

export interface Responder {
  id: string;
  name: string;
  email: string;
  role: string;
  phone: string;
  avatar_initials: string;
}

export interface OnCallShift {
  shift_id: string;
  rotation_name: string;
  primary_responder: Responder;
  secondary_responder: Responder;
  escalation_lead: Responder;
  starts_at: string;
  ends_at: string;
  tz: string;
}

export interface PageEvent {
  page_id: string;
  incident_id: string;
  tier_level: number;
  responder: Responder;
  status: PageStatus;
  dispatched_at: string;
  acknowledged_at?: string | null;
  channel: string;
  notes: string;
}

export interface OnCallRosterStatus {
  current_shift: OnCallShift;
  active_pages: PageEvent[];
  recent_resolved_pages: PageEvent[];
  mtta_seconds_avg: number;
}
