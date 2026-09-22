import { useState, useEffect } from "react";
import { ShieldAlert, RefreshCw, Radio } from "lucide-react";
import { useIncidents } from "./hooks/useIncidents";
import { IncidentList } from "./components/IncidentList";
import { IncidentDetail } from "./components/IncidentDetail";
import { ChaosPanel } from "./components/ChaosPanel";
import { LoadingOverlay, ErrorBanner } from "./components/Loading";

export function App() {
  const { incidents, loading, error, refetch } = useIncidents(5000);
  const [selectedId, setSelectedId] = useState<string | null>(null);

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

      {/* Main Grid Layout */}
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
    </div>
  );
}

export default App;
