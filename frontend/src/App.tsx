import { useState, useEffect } from "react";
import {
  ShieldAlert,
  RefreshCw,
  Radio,
  Network,
  TrendingUp,
  GitFork,
  Zap,
  Shield,
  Globe,
  DollarSign,
  Cpu,
} from "lucide-react";
import { useIncidents } from "./hooks/useIncidents";
import { IncidentList } from "./components/IncidentList";
import { IncidentDetail } from "./components/IncidentDetail";
import { ChaosPanel } from "./components/ChaosPanel";
import { LoadingOverlay, ErrorBanner } from "./components/Loading";
import { ServiceTopologyPanel } from "./components/ServiceTopologyPanel";
import { PredictiveHealthPanel } from "./components/PredictiveHealthPanel";
import { CanaryAnalysisPanel } from "./components/CanaryAnalysisPanel";
import { ResiliencePanel } from "./components/ResiliencePanel";
import { AuditTrailPanel } from "./components/AuditTrailPanel";
import { MultiClusterPanel } from "./components/MultiClusterPanel";
import { FinOpsPanel } from "./components/FinOpsPanel";
import { SelfHealingPanel } from "./components/SelfHealingPanel";

type ActiveTab =
  | "incidents"
  | "topology"
  | "predictive"
  | "canary"
  | "resilience"
  | "audit"
  | "multicluster"
  | "finops"
  | "selfhealing";

export function App() {
  const { incidents, loading, error, refetch } = useIncidents(5000);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("incidents");

  useEffect(() => {
    if (incidents.length > 0) {
      if (!selectedId || !incidents.some((i) => i.id === selectedId)) {
        setSelectedId(incidents[0].id);
      }
    } else {
      setSelectedId(null);
    }
  }, [incidents, selectedId]);

  const selectedIncident = incidents.find((i) => i.id === selectedId) ?? null;

  const tabs: { id: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { id: "incidents", label: "Incidents", icon: <Radio size={12} strokeWidth={2} /> },
    { id: "topology", label: "Topology", icon: <Network size={12} strokeWidth={2} /> },
    { id: "predictive", label: "Predictive", icon: <TrendingUp size={12} strokeWidth={2} /> },
    { id: "canary", label: "Canary", icon: <GitFork size={12} strokeWidth={2} /> },
    { id: "resilience", label: "Resilience", icon: <Zap size={12} strokeWidth={2} /> },
    { id: "audit", label: "Audit", icon: <Shield size={12} strokeWidth={2} /> },
    { id: "multicluster", label: "Multi-Cluster", icon: <Globe size={12} strokeWidth={2} /> },
    { id: "finops", label: "FinOps", icon: <DollarSign size={12} strokeWidth={2} /> },
    { id: "selfhealing", label: "Self-Healing", icon: <Cpu size={12} strokeWidth={2} /> },
  ];

  const renderPanel = () => {
    const wrapStyle: React.CSSProperties = {
      padding: "20px 24px",
      overflowY: "auto",
      height: "calc(100vh - 54px)",
    };
    switch (activeTab) {
      case "incidents":
        return (
          <main className="main-layout">
            <aside className="incident-list-pane">
              <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)" }}>
                <ChaosPanel onFired={refetch} />
              </div>
              {loading && incidents.length === 0 ? (
                <LoadingOverlay visible={true} message="Fetching incidents..." />
              ) : (
                <IncidentList incidents={incidents} selectedId={selectedId} onSelect={(id) => setSelectedId(id)} />
              )}
            </aside>
            <section className="incident-detail-pane">
              {error && <ErrorBanner message={error} onRetry={refetch} />}
              {selectedIncident ? (
                <IncidentDetail incident={selectedIncident} onUpdate={refetch} />
              ) : (
                <div className="empty-state" style={{ height: "100%" }}>
                  <Radio size={40} strokeWidth={1.5} style={{ opacity: 0.3 }} />
                  <h3>No Incident Selected</h3>
                  <p>Trigger a simulated Prometheus alert using the Chaos Simulator on the left.</p>
                </div>
              )}
            </section>
          </main>
        );
      case "topology":
        return <div style={wrapStyle}><ServiceTopologyPanel selectedServiceId={selectedIncident?.service} /></div>;
      case "predictive":
        return <div style={wrapStyle}><PredictiveHealthPanel incidentId={selectedIncident?.id} service={selectedIncident?.service} /></div>;
      case "canary":
        return <div style={wrapStyle}><CanaryAnalysisPanel service={selectedIncident?.service} /></div>;
      case "resilience":
        return <div style={wrapStyle}><ResiliencePanel /></div>;
      case "audit":
        return <div style={wrapStyle}><AuditTrailPanel incidentId={selectedIncident?.id} /></div>;
      case "multicluster":
        return <div style={wrapStyle}><MultiClusterPanel incidentService={selectedIncident?.service} /></div>;
      case "finops":
        return <div style={wrapStyle}><FinOpsPanel incidentId={selectedIncident?.id} service={selectedIncident?.service} /></div>;
      case "selfhealing":
        return <div style={wrapStyle}><SelfHealingPanel incidentId={selectedIncident?.id} service={selectedIncident?.service} /></div>;
    }
  };

  return (
    <div className="app-shell">
      <header className="navbar">
        <div className="navbar-brand">
          <div className="brand-icon">
            <ShieldAlert size={15} color="#ffffff" strokeWidth={2.2} />
          </div>
          <span>SRE Ops // Incident Agent</span>
        </div>

        <div className="navbar-divider" />

        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
          {tabs.map((t) => (
            <button
              key={t.id}
              id={`tab-${t.id}`}
              className={`btn btn-sm ${activeTab === t.id ? "btn-primary" : "btn-ghost"}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.icon}
              <span>{t.label}</span>
            </button>
          ))}
        </div>

        <div className="navbar-divider" />

        <div className="status-pill">
          <span className="status-dot dot-emerald" />
          <span>Real-time Telemetry (SSE)</span>
        </div>

        <div className="status-pill">
          <span className="status-dot dot-cyan" />
          <span>Mode: <strong style={{ color: "var(--text-primary)", fontWeight: 600 }}>Simulator Cluster</strong></span>
        </div>

        <div className="navbar-right">
          <button className="btn btn-ghost btn-sm" onClick={refetch} title="Force Refresh">
            <RefreshCw size={12} strokeWidth={2} />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {renderPanel()}
    </div>
  );
}

export default App;
