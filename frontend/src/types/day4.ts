// Day 4 Advanced Features: Canary Analysis, Resilience Studio & Audit Replay

export type CanaryPhase =
  | "pending"
  | "running"
  | "evaluating"
  | "promoting"
  | "promoted"
  | "rolling_back"
  | "rolled_back"
  | "aborted";

export type MetricComparisonStatus = "pass" | "warn" | "fail";

export interface CanaryMetricComparison {
  metric_name: string;
  unit: string;
  baseline_value: number;
  canary_value: number;
  delta_pct: number;
  weight: number;
  status: MetricComparisonStatus;
  threshold_warn_pct: number;
  threshold_fail_pct: number;
  description: string;
}

export interface CanaryAnalysisReport {
  deployment_id: string;
  service: string;
  baseline_version: string;
  canary_version: string;
  traffic_split_pct: number;
  overall_score: number;
  verdict: MetricComparisonStatus;
  auto_rollback_recommended: boolean;
  metrics: CanaryMetricComparison[];
  evaluated_at: string;
  message: string;
}

export interface CanaryDeployment {
  deployment_id: string;
  service: string;
  baseline_version: string;
  canary_version: string;
  phase: CanaryPhase;
  current_weight_pct: number;
  steps: number[];
  current_step_index: number;
  minimum_score: number;
  auto_rollback_enabled: boolean;
  created_at: string;
  last_evaluated_at?: string | null;
  last_report?: CanaryAnalysisReport | null;
}

export type FaultType = "latency_spike" | "packet_drop" | "pod_crash" | "cpu_hog" | "db_deadlock";
export type ExperimentState = "idle" | "running" | "recovering" | "completed" | "aborted";

export interface ChaosExperiment {
  experiment_id: string;
  name: string;
  target_service: string;
  fault_type: FaultType;
  duration_seconds: number;
  hypothesis: string;
  state: ExperimentState;
  started_at?: string | null;
  completed_at?: string | null;
  hypothesis_passed?: boolean | null;
  steady_state_metrics?: Record<string, number>;
  fault_state_metrics?: Record<string, number>;
  resilience_score: number;
  remediation_latency_seconds: number;
  summary: string;
}

export interface ResilienceScorecard {
  evaluated_at: string;
  cluster_resilience_grade: string;
  resilience_index: number;
  experiments_run: number;
  hypotheses_validated: number;
  hypotheses_failed: number;
  mttr_seconds_avg: number;
  experiments: ChaosExperiment[];
}

export type ActorType = "ai_agent" | "human_operator" | "kubernetes_controller" | "system";
export type ActionCategory =
  | "diagnosis"
  | "approval_request"
  | "approval_decision"
  | "remediation_execution"
  | "rollback"
  | "escalation"
  | "canary_progression";

export interface AuditEntry {
  entry_id: string;
  timestamp: string;
  incident_id: string;
  actor_type: ActorType;
  actor_name: string;
  category: ActionCategory;
  action_summary: string;
  details?: Record<string, any>;
  tamper_hash: string;
}

export interface IncidentReplayFrame {
  frame_index: number;
  relative_time_seconds: number;
  timestamp: string;
  event_title: string;
  description: string;
  cluster_health: string;
  service_state: Record<string, any>;
  action_taken?: string | null;
}

export interface ComplianceReport {
  incident_id: string;
  generated_at: string;
  total_actions: number;
  autonomous_actions_count: number;
  human_approved_actions_count: number;
  soc2_compliant: boolean;
  sox_safety_gates_passed: boolean;
  audit_trail_verified: boolean;
  summary: string;
}

