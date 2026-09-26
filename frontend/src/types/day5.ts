export type ClusterStatus = "healthy" | "degraded" | "draining" | "drained" | "offline";

export interface ClusterRegion {
  cluster_id: string;
  name: string;
  region_code: string;
  is_primary: boolean;
  status: ClusterStatus;
  traffic_weight_pct: number;
  node_count: number;
  active_pods: number;
  p99_latency_ms: number;
  error_rate_pct: number;
  ingress_rps: number;
  cloud_provider: string;
  last_health_check: string;
}

export interface FailoverEvent {
  event_id: string;
  timestamp: string;
  cluster_id: string;
  event_type: string;
  summary: string;
  source_weight: number;
  target_weight: number;
  initiator: string;
}

export interface MultiClusterOverview {
  evaluated_at: string;
  total_clusters: number;
  healthy_clusters: number;
  total_ingress_rps: number;
  dns_routing_policy: string;
  clusters: ClusterRegion[];
  recent_events: FailoverEvent[];
}

export type ImpactTier = "tier_1_mission_critical" | "tier_2_core_business" | "tier_3_internal_support";

export interface BusinessImpactMetric {
  revenue_loss_per_minute_usd: number;
  cumulative_revenue_loss_usd: number;
  incident_duration_minutes: number;
  estimated_failed_transactions: number;
  sla_target_availability_pct: number;
  actual_availability_pct: number;
  sla_breach_penalty_usd: number;
}

export interface RemediationCostDelta {
  action_type: string;
  resources_added: string;
  hourly_cost_delta_usd: number;
  monthly_projected_cost_usd: number;
  cost_status: string;
  applied_at: string;
}

export interface FinOpsSummary {
  service: string;
  incident_id: string;
  impact_tier: ImpactTier;
  business_impact: BusinessImpactMetric;
  remediation_costs: RemediationCostDelta[];
  total_financial_loss_usd: number;
  total_infra_remediation_cost_usd: number;
  total_incident_cost_usd: number;
  roi_saved_usd: number;
  rightsizing_recommendation: string;
  evaluated_at: string;
}

export type VerificationStatus =
  | "pending"
  | "verifying"
  | "verified_resolved"
  | "verification_failed_reverted";

export interface SelfHealingPolicy {
  policy_id: string;
  name: string;
  target_service: string;
  trigger_condition: string;
  action_type: string;
  parameters: Record<string, any>;
  enabled: boolean;
  cooldown_minutes: number;
  last_triggered_at: string | null;
  execution_count: number;
  success_count: number;
  risk_level: string;
}

export interface ClosedLoopExecution {
  execution_id: string;
  policy_id: string;
  policy_name: string;
  incident_id: string;
  target_service: string;
  action_taken: string;
  started_at: string;
  completed_at: string | null;
  initial_metrics: Record<string, number>;
  post_mitigation_metrics: Record<string, number>;
  status: VerificationStatus;
  watchdog_verdict: string;
  revert_triggered: boolean;
}

export interface GuardrailStatus {
  velocity_limit_per_15m: number;
  actions_in_current_window: number;
  rate_limit_exceeded: boolean;
  blast_radius_cap: number;
  human_intervention_required: boolean;
  last_reset_at: string;
}
