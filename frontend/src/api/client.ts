import type {
  MultiClusterOverview,
  ClusterRegion,
  FinOpsSummary,
  RemediationCostDelta,
  SelfHealingPolicy,
  ClosedLoopExecution,
  GuardrailStatus,
} from "../types/day5";
import type { Incident } from "../types/incident";
import type {
  TopologyGraph,
  BlastRadiusReport,
  ClusterPredictionSummary,
  IncidentCluster,
  NoiseReductionStats,
  OnCallRosterStatus,
  PageEvent,
} from "../types/day3";
import type {
  CanaryDeployment,
  CanaryAnalysisReport,
  ResilienceScorecard,
  ChaosExperiment,
  AuditEntry,
  ComplianceReport,
  IncidentReplayFrame,
} from "../types/day4";

const BASE = "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${path}: ${res.status} ${err}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  incidents: {
    list: (params?: { status?: string; severity?: string; service?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params?.status) qs.set("status", params.status);
      if (params?.severity) qs.set("severity", params.severity);
      if (params?.service) qs.set("service", params.service);
      if (params?.limit) qs.set("limit", String(params.limit));
      return request<Incident[]>(`/incidents${qs.toString() ? "?" + qs.toString() : ""}`);
    },
    get: (id: string) => request<Incident>(`/incidents/${id}`),
    stream: () => new EventSource(`${BASE}/incidents/stream`),
  },
  alerts: {
    sendWebhook: (payload: unknown) =>
      request<unknown>("/alerts/webhook", { method: "POST", body: JSON.stringify(payload) }),
  },
  remediation: {
    investigate: (incidentId: string) =>
      request<Incident>(`/incidents/${incidentId}/investigate`, { method: "POST" }),
    diff: (incidentId: string) =>
      request<{ incident_id: string; action: string; risk_tier: string; target_resource: string; diff: string }>(`/incidents/${incidentId}/diff`),
    approve: (incidentId: string, approver: string, comment?: string) =>
      request<Incident>(`/incidents/${incidentId}/approve`, {
        method: "POST",
        body: JSON.stringify({ approver, comment }),
      }),
    reject: (incidentId: string, rejector: string, reason: string) =>
      request<Incident>(`/incidents/${incidentId}/reject`, {
        method: "POST",
        body: JSON.stringify({ rejector, reason }),
      }),
    escalate: (incidentId: string, reason: string, channel: string = "all") =>
      request<Incident>(`/incidents/${incidentId}/escalate`, {
        method: "POST",
        body: JSON.stringify({ reason, channel }),
      }),
    updateStatus: (incidentId: string, status: string, reason?: string) =>
      request<Incident>(`/incidents/${incidentId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status, reason }),
      }),
  },
  runbooks: {
    catalog: () => request<{ count: number; runbooks: any[] }>("/runbooks/catalog"),
    get: (id: string) => request<any>(`/runbooks/catalog/${id}`),
    match: (incident: any, evidence?: any) =>
      request<any>("/runbooks/match", {
        method: "POST",
        body: JSON.stringify({ incident, evidence }),
      }),
    trigger: (runbookId: string, incident: any, evidence?: any) =>
      request<{ execution_id: string; runbook_id: string; runbook_name: string; incident_id: string; status: string; message: string }>(
        "/runbooks/trigger",
        {
          method: "POST",
          body: JSON.stringify({ runbook_id: runbookId, incident, evidence }),
        }
      ),
    status: (executionId: string) => request<any>(`/runbooks/status/${executionId}`),
    approve: (executionId: string, stepIndex: number, approved: boolean, approver = "operator", reason?: string) =>
      request<any>("/runbooks/approve", {
        method: "POST",
        body: JSON.stringify({ execution_id: executionId, step_index: stepIndex, approved, approver, reason }),
      }),
  },
  copilot: {
    createSession: (incidentId?: string, incidentContext?: any) =>
      request<{ session_id: string; incident_id?: string; message: string }>("/copilot/sessions", {
        method: "POST",
        body: JSON.stringify({ incident_id: incidentId, incident_context: incidentContext }),
      }),
    chat: (sessionId: string, message: string, incidentContext?: any) =>
      request<{ session_id: string; reply: string; suggestions: string[]; referenced_runbook_id?: string; confidence: number }>(
        "/copilot/chat",
        {
          method: "POST",
          body: JSON.stringify({ session_id: sessionId, message, incident_context: incidentContext }),
        }
      ),
    getSession: (sessionId: string) => request<any>(`/copilot/sessions/${sessionId}`),
  },
  postmortems: {
    generate: (data: any) =>
      request<{ incident_id: string; title: string; markdown: string; generated_at: string; word_count: number }>(
        "/postmortems/generate",
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      ),
    get: (incidentId: string) => request<any>(`/postmortems/${incidentId}`),
    list: () => request<{ count: number; postmortems: any[] }>("/postmortems/"),
  },
  telemetry: {
    getSeries: (service: string, metricName: string, limit = 60) =>
      request<{ service: string; metric_name: string; count: number; points: Array<{ timestamp: string; value: number }> }>(
        `/telemetry/series/${service}/${metricName}?limit=${limit}`
      ),
    getSLOs: (service?: string) =>
      request<{ count: number; slos: Array<{ slo_id: string; service: string; target_pct: number; current_pct: number; burn_rate: number; error_budget_remaining_pct: number; is_breached: boolean; status: string; evaluated_at: string }> }>(
        `/telemetry/slos${service ? "?service=" + service : ""}`
      ),
    getCorrelations: (service: string) =>
      request<{ service: string; primary_metric: string; correlations: Array<{ signal_name: string; service: string; correlation_coefficient: number; lag_seconds: number; p_value: number; description: string }> }>(
        `/telemetry/correlations/${service}`
      ),
    tick: (chaosScenario = "nominal") =>
      request<{ status: string; points_count: number; chaos_applied: string }>(
        `/telemetry/tick?chaos_scenario=${chaosScenario}`,
        { method: "POST" }
      ),
  },
  topology: {
    getGraph: () => request<TopologyGraph>("/topology/graph"),
    calculateBlastRadius: (serviceId: string) =>
      request<BlastRadiusReport>("/topology/blast-radius", {
        method: "POST",
        body: JSON.stringify({ service_id: serviceId }),
      }),
    updateHealth: (serviceId: string, health: string, incidentId?: string) =>
      request<{ status: string; service_id: string; new_health: string }>(
        `/topology/nodes/${serviceId}/health`,
        {
          method: "POST",
          body: JSON.stringify({ health, incident_id: incidentId }),
        }
      ),
  },
  prediction: {
    getForecasts: () => request<ClusterPredictionSummary>("/prediction/forecasts"),
  },
  grouping: {
    getClusters: () => request<{ clusters: IncidentCluster[] }>("/grouping/clusters"),
    getStats: () => request<NoiseReductionStats>("/grouping/stats"),
    ingest: (alertId: string, alertName: string, service: string, severity = "critical") =>
      request<IncidentCluster>("/grouping/ingest", {
        method: "POST",
        body: JSON.stringify({
          alert_id: alertId,
          alert_name: alertName,
          service,
          severity,
        }),
      }),
  },
  oncall: {
    getStatus: () => request<OnCallRosterStatus>("/oncall/status"),
    page: (incidentId: string, tier = 1, notes?: string) =>
      request<PageEvent>("/oncall/page", {
        method: "POST",
        body: JSON.stringify({ incident_id: incidentId, tier, notes }),
      }),
    acknowledge: (pageId: string) =>
      request<PageEvent>(`/oncall/page/${pageId}/ack`, { method: "POST" }),
    escalate: (pageId: string, reason?: string) =>
      request<PageEvent>(`/oncall/page/${pageId}/escalate`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
  },
  canary: {
    list: () => request<{ deployments: CanaryDeployment[] }>("/canary/deployments"),
    get: (id: string) => request<CanaryDeployment>(`/canary/deployments/${id}`),
    evaluate: (id: string) =>
      request<{ deployment: CanaryDeployment; report: CanaryAnalysisReport }>(
        `/canary/deployments/${id}/evaluate`,
        { method: "POST" }
      ),
    advance: (id: string) =>
      request<{ deployment: CanaryDeployment; report: CanaryAnalysisReport }>(
        `/canary/deployments/${id}/advance`,
        { method: "POST" }
      ),
    promote: (id: string) =>
      request<CanaryDeployment>(`/canary/deployments/${id}/promote`, { method: "POST" }),
    rollback: (id: string, reason?: string) =>
      request<CanaryDeployment>(`/canary/deployments/${id}/rollback`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
  },
  resilience: {
    getScorecard: () => request<ResilienceScorecard>("/resilience/scorecard"),
    listExperiments: () => request<{ experiments: ChaosExperiment[] }>("/resilience/experiments"),
    launch: (experimentId: string) =>
      request<ChaosExperiment>(`/resilience/experiments/${experimentId}/launch`, { method: "POST" }),
    stop: (experimentId: string) =>
      request<ChaosExperiment>(`/resilience/experiments/${experimentId}/stop`, { method: "POST" }),
  },
  audit: {
    getLedger: () =>
      request<{ integrity_verified: boolean; count: number; ledger: AuditEntry[] }>("/audit/ledger"),
    getCompliance: (incidentId: string) =>
      request<ComplianceReport>(`/audit/compliance/${incidentId}`),
    getReplay: (incidentId: string) =>
      request<{ incident_id: string; frames_count: number; frames: IncidentReplayFrame[] }>(
        `/audit/replay/${incidentId}`
      ),
  },
  multicluster: {
    getOverview: () => request<MultiClusterOverview>("/multicluster/overview"),
    listClusters: () => request<{ clusters: ClusterRegion[] }>("/multicluster/clusters"),
    drain: (clusterId: string, reason?: string) =>
      request<{ status: string; cluster: ClusterRegion; overview: MultiClusterOverview }>(
        `/multicluster/clusters/${clusterId}/drain`,
        { method: "POST", body: JSON.stringify({ reason }) }
      ),
    restore: (clusterId: string, targetWeightPct = 35) =>
      request<{ status: string; cluster: ClusterRegion; overview: MultiClusterOverview }>(
        `/multicluster/clusters/${clusterId}/restore`,
        { method: "POST", body: JSON.stringify({ target_weight_pct: targetWeightPct }) }
      ),
    shift: (sourceId: string, targetId: string, shiftPct: number) =>
      request<MultiClusterOverview>("/multicluster/shift", {
        method: "POST",
        body: JSON.stringify({ source_id: sourceId, target_id: targetId, shift_pct: shiftPct }),
      }),
  },
  finops: {
    listSummaries: () => request<{ summaries: FinOpsSummary[] }>("/finops/summaries"),
    getImpact: (incidentId: string) => request<FinOpsSummary>(`/finops/impact/${incidentId}`),
    calculate: (service: string, durationMinutes: number, errorRatePct: number, incidentId?: string) =>
      request<FinOpsSummary>("/finops/calculate", {
        method: "POST",
        body: JSON.stringify({
          service,
          duration_minutes: durationMinutes,
          error_rate_pct: errorRatePct,
          incident_id: incidentId,
        }),
      }),
    addRemediationCost: (incidentId: string, actionType: string, resources: string, hourlyUsd: number) =>
      request<RemediationCostDelta>("/finops/remediation-cost", {
        method: "POST",
        body: JSON.stringify({
          incident_id: incidentId,
          action_type: actionType,
          resources,
          hourly_usd: hourlyUsd,
        }),
      }),
  },
  selfhealing: {
    listPolicies: () => request<{ policies: SelfHealingPolicy[] }>("/selfhealing/policies"),
    togglePolicy: (policyId: string, enabled: boolean) =>
      request<SelfHealingPolicy>(`/selfhealing/policies/${policyId}/toggle`, {
        method: "POST",
        body: JSON.stringify({ enabled }),
      }),
    executePolicy: (policyId: string, incidentId: string, initialMetrics?: Record<string, number>) =>
      request<ClosedLoopExecution>(`/selfhealing/policies/${policyId}/execute`, {
        method: "POST",
        body: JSON.stringify({ incident_id: incidentId, initial_metrics: initialMetrics }),
      }),
    listExecutions: () => request<{ executions: ClosedLoopExecution[] }>("/selfhealing/executions"),
    getGuardrails: () => request<GuardrailStatus>("/selfhealing/guardrails"),
  },
};

