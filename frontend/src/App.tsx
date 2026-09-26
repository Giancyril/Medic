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

type ActiveTab =
  | "incidents"
  | "topology"
  | "predictive"
  | "canary"
  | "resilience"
  | "audit";

export function App() {
  const { incidents, loading, error, refetch } = useIncidents(5000);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("incidents");

  // Auto-select first incident if none selected or if selected one disappears
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

  return (
    <div className="app-shell">
      {/* Top Navbar */}
      <header className="navbar">
        <div className="navbar-brand">
          <div className="brand-icon">
            <ShieldAlert size={15} color="#ffffff" strokeWidth={2.2} />
          </div>
          <span>SRE Ops // Incident Agent</span>
        </div>

        <div className="navbar-divider" />

        {/* Global Navigation Tabs */}
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          <button
            className={`btn btn-sm ${activeTab === "incidents" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setActiveTab("incidents")}
          >
            <Radio size={12} strokeWidth={2} />
            <span>Incidents</span>
          </button>
          <button
            className={`btn btn-sm ${activeTab === "topology" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setActiveTab("topology")}
          >
            <Network size={12} strokeWidth={2} />
            <span>Topology</span>
          </button>
          <button
            className={`btn btn-sm ${activeTab === "predictive" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setActiveTab("predictive")}
          >
            <TrendingUp size={12} strokeWidth={2} />
            <span>Predictive</span>
          </button>
          <button
            className={`btn btn-sm ${activeTab === "canary" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setActiveTab("canary")}
          >
            <GitFork size={12} strokeWidth={2} />
            <span>Canary</span>
          </button>
          <button
            className={`btn btn-sm ${activeTab === "resilience" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setActiveTab("resilience")}
          >
            <Zap size={12} strokeWidth={2} />
            <span>Resilience</span>
          </button>
          <button
            className={`btn btn-sm ${activeTab === "audit" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setActiveTab("audit")}
          >
            <Shield size={12} strokeWidth={2} />
            <span>Audit & Replay</span>
          </button>
        </div>

        <div className="navbar-divider" />

        {/* Standardized Status Pills */}
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

      {/* Main Layout Body */}
      {activeTab === "incidents" ? (
        <main className="main-layout">
          {/* Left Pane: Incidents List & Chaos Simulator */}
          <aside className="incident-list-pane">
            <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)" }}>
              <ChaosPanel onFired={refetch} />
            </div>
            {loading && incidents.length === 0 ? (
              <LoadingOverlay visible={true} message="Fetching incidents..." />
            ) : (
              <IncidentList
                incidents={incidents}
                selectedId={selectedId}
                onSelect={(id) => setSelectedId(id)}
              />
            )}
          </aside>

          {/* Right Pane: Incident Details & Timeline */}
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
      ) : activeTab === "topology" ? (
        <div style={{ padding: "20px 24px", overflowY: "auto", height: "calc(100vh - 54px)" }}>
          <ServiceTopologyPanel selectedServiceId={selectedIncident?.service} />
        </div>
      ) : activeTab === "predictive" ? (
        <div style={{ padding: "20px 24px", overflowY: "auto", height: "calc(100vh - 54px)" }}>
          <PredictiveHealthPanel incidentId={selectedIncident?.id} service={selectedIncident?.service} />
        </div>
      ) : activeTab === "canary" ? (
        <div style={{ padding: "20px 24px", overflowY: "auto", height: "calc(100vh - 54px)" }}>
          <CanaryAnalysisPanel service={selectedIncident?.service} />
        </div>
      ) : activeTab === "resilience" ? (
        <div style={{ padding: "20px 24px", overflowY: "auto", height: "calc(100vh - 54px)" }}>
          <ResiliencePanel />
        </div>
      ) : (
        <div style={{ padding: "20px 24px", overflowY: "auto", height: "calc(100vh - 54px)" }}>
          <AuditTrailPanel incidentId={selectedIncident?.id} />
        </div>
      )}
    </div>
  );
}

export default App;
