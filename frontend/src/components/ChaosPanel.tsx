import { useState } from "react";
import { api } from "../api/client";

interface Props {
  onFired?: () => void;
}

export function ChaosPanel({ onFired }: Props) {
  const [loading, setLoading] = useState<string | null>(null);

  const scenarios = [
    {
      id: "oom",
      name: "🔥 OOMKilled Spike",
      desc: "Simulates checkout-service memory exhaustion and OOM termination",
      payload: {
        status: "firing",
        receiver: "alert-agent-webhook",
        alerts: [
          {
            status: "firing",
            labels: {
              alertname: "KubePodOOMKilled",
              severity: "critical",
              service: "checkout-service",
              namespace: "prod",
              pod: "checkout-service-7848bc95c6-q2x89",
            },
            annotations: {
              summary: "Pod checkout-service-7848bc95c6-q2x89 was OOMKilled",
              description: "Container in pod checkout-service-7848bc95c6-q2x89 has been terminated with OOMKilled status (exit code 137). Memory usage exceeded limits.",
            },
            startsAt: new Date().toISOString(),
          },
        ],
      },
    },
    {
      id: "crashloop",
      name: "💥 CrashLoopBackOff",
      desc: "Simulates payment-service restart loop after bad release",
      payload: {
        status: "firing",
        receiver: "alert-agent-webhook",
        alerts: [
          {
            status: "firing",
            labels: {
              alertname: "KubePodCrashLooping",
              severity: "critical",
              service: "payment-service",
              namespace: "prod",
              pod: "payment-service-5f8846b49-b8s2m",
            },
            annotations: {
              summary: "Pod payment-service is crash looping with repeated failures",
              description: "Pod has restarted 5 times in the last 10 minutes. Exit code 1 indicates fatal application startup exception.",
            },
            startsAt: new Date().toISOString(),
          },
        ],
      },
    },
    {
      id: "errors",
      name: "⚡ High Error Rate (5xx)",
      desc: "Spikes API gateway error rate to 18.5% with upstream timeouts",
      payload: {
        status: "firing",
        receiver: "alert-agent-webhook",
        alerts: [
          {
            status: "firing",
            labels: {
              alertname: "HighHttpErrorRate",
              severity: "warning",
              service: "api-gateway",
              namespace: "prod",
            },
            annotations: {
              summary: "HTTP 5xx error rate exceeded 5% threshold on api-gateway",
              description: "HTTP 5xx rate currently at 18.5%. Downstream dependency timeouts detected on database and payment connections.",
            },
            startsAt: new Date().toISOString(),
          },
        ],
      },
    },
    {
      id: "latency",
      name: "⏱️ Latency Degraded (P99)",
      desc: "Simulates upstream timeout and degraded P99 latency",
      payload: {
        status: "firing",
        receiver: "alert-agent-webhook",
        alerts: [
          {
            status: "firing",
            labels: {
              alertname: "ServiceLatencyHigh",
              severity: "warning",
              service: "auth-service",
              namespace: "prod",
            },
            annotations: {
              summary: "P99 latency elevated above 1200ms on auth-service",
              description: "Authentication service P99 latency is 1450ms, causing cascading queue saturation.",
            },
            startsAt: new Date().toISOString(),
          },
        ],
      },
    },
  ];

  async function fireChaos(s: typeof scenarios[0]) {
    setLoading(s.id);
    try {
      await api.alerts.sendWebhook(s.payload);
      onFired?.();
    } catch (e) {
      alert("Failed to fire chaos alert: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="chaos-panel">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", fontWeight: 700, color: "var(--accent-purple)", letterSpacing: "0.5px" }}>
          <span>🧪</span> CHAOS INJECTION SIMULATOR
        </div>
        <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>Simulate Prometheus Alerts</span>
      </div>
      <div className="chaos-buttons">
        {scenarios.map((s) => (
          <button
            key={s.id}
            className="btn-chaos"
            disabled={loading !== null}
            onClick={() => fireChaos(s)}
            title={s.desc}
            id={`btn-chaos-${s.id}`}
          >
            {loading === s.id ? "Firing…" : s.name}
          </button>
        ))}
      </div>
    </div>
  );
}
