import { useState } from "react";
import { Flame, AlertTriangle, Zap, TrendingDown, Activity } from "lucide-react";
import { api } from "../api/client";

interface Props {
  onFired?: () => void;
}

export function ChaosPanel({ onFired }: Props) {
  const [loading, setLoading] = useState<string | null>(null);

  const scenarios = [
    {
      id: "oom",
      name: "OOMKilled Spike",
      desc: "Simulates checkout-service memory exhaustion and OOM termination",
      icon: Flame,
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
      name: "CrashLoopBackOff",
      desc: "Simulates payment-service restart loop after bad release",
      icon: AlertTriangle,
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
      name: "High Error Rate",
      desc: "Spikes API gateway error rate to 18.5% with upstream timeouts",
      icon: Zap,
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
      name: "Latency Degraded",
      desc: "Simulates upstream timeout and degraded P99 latency",
      icon: TrendingDown,
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
      <div className="chaos-panel-header">
        <div className="chaos-panel-title">
          <Activity size={13} style={{ color: "var(--accent-primary)" }} />
          <span>Chaos Simulator</span>
        </div>
        <span style={{ fontSize: "10px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          Simulate Alerts
        </span>
      </div>
      <div className="chaos-buttons-grid">
        {scenarios.map((s) => {
          const Icon = s.icon;
          return (
            <button
              key={s.id}
              className="chaos-btn"
              disabled={loading !== null}
              onClick={() => fireChaos(s)}
              title={s.desc}
              id={`btn-chaos-${s.id}`}
            >
              <Icon size={14} className="chaos-icon" />
              <span>{loading === s.id ? "Firing…" : s.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
