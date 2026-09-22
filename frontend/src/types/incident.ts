// Core incident and diagnostic types shared across all components

export type IncidentStatus =
  | "NEW"
  | "INVESTIGATING"
  | "DIAGNOSED"
  | "ACTION_REQUIRED"
  | "REMEDIATING"
  | "RESOLVED"
  | "ESCALATED";

export type IncidentSeverity = "critical" | "warning" | "info";
export type RiskTier = "TIER_1_LOW" | "TIER_2_MEDIUM" | "TIER_3_HIGH";

export interface IncidentEvent {
  id: number;
  incident_id: string;
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface GoldenSignals {
  request_rate_rps: number;
  error_rate_pct: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  latency_p99_ms: number;
  cpu_saturation_pct: number;
  memory_saturation_pct: number;
}

export interface SignalTimeline {
  timestamps: string[];
  error_rate: number[];
  latency_p99: number[];
  memory_saturation: number[];
}

export interface DeploymentMarker {
  timestamp: string;
  revision: string;
  message: string;
}

export interface GoldenSignalsData {
  service: string;
  namespace: string;
  timestamp: string;
  signals: GoldenSignals;
  timeline: SignalTimeline;
  deployment_marker?: DeploymentMarker;
}

export interface PodInfo {
  name: string;
  service: string;
  namespace: string;
  status: string;
  ready: boolean;
  restart_count: number;
  exit_code: number;
  reason: string | null;
  node: string;
  started_at: string;
}

export interface ClusterEvent {
  type: string;
  reason: string;
  object: string;
  message: string;
  timestamp: string;
}

export interface LogEntry {
  pod: string;
  message: string;
}

export interface LogData {
  service: string;
  namespace: string;
  total_lines_scanned: number;
  error_count: number;
  errors: LogEntry[];
  raw_logs: LogEntry[];
}

export interface DeploymentInfo {
  name: string;
  namespace: string;
  replicas: number;
  ready_replicas: number;
  image: string;
  revision: number;
  history: Array<{ revision: number; image: string; updated_at: string }>;
}

export interface InvestigationEvidence {
  service: string;
  namespace: string;
  collected_at: string;
  golden_signals: GoldenSignalsData;
  pods: PodInfo[];
  events: ClusterEvent[];
  deployment: DeploymentInfo;
  logs: LogData;
  anomalies: string[];
  health_score: number;
}

export interface Diagnosis {
  root_cause: string;
  confidence: number;
  supporting_evidence: string[];
  recommended_action: string;
  action_type: string;
  risk_tier: RiskTier;
  requires_escalation: boolean;
  diagnosed_at: string;
}

export interface RemediationAction {
  action_type: string;
  name: string;
  description: string;
  risk_tier: RiskTier;
  target_resource: string;
  parameters: Record<string, unknown>;
  requires_human_approval: boolean;
  is_auto_executable: boolean;
  diff_preview: string;
}

export interface Incident {
  id: string;
  fingerprint: string;
  title: string;
  service: string;
  namespace: string;
  alert_name: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  summary: string;
  description: string;
  firing_count: number;
  first_seen_at: string;
  last_seen_at: string;
  resolved_at: string | null;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  evidence: InvestigationEvidence | Record<string, never>;
  diagnosis: Diagnosis | Record<string, never>;
  remediation: RemediationAction | Record<string, never>;
  events: IncidentEvent[];
}

export interface SSEMessage {
  event: string;
  data: Record<string, unknown>;
  timestamp: string;
}
