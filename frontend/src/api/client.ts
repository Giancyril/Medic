import type { Incident } from "../types/incident";

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
};
