import { useState, useEffect } from "react";
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
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <span>SRE Ops // Incident Agent</span>
        </div>

        <div className="navbar-divider" />

        <div className="navbar-pill live">
          <div className="pulse" />
          <span>Real-time Telemetry (SSE)</span>
        </div>

        <div className="navbar-pill">
          <span>Mode:</span>
          <strong style={{ color: "var(--accent-cyan)", marginLeft: 3 }}>Simulator Cluster</strong>
        </div>

        <div className="navbar-right">
          <button className="btn btn-ghost btn-sm" onClick={refetch} title="Force Refresh">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="23 4 23 10 17 10" />
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
            </svg>
            Refresh
          </button>
        </div>
      </header>

      {/* Main Grid */}
      <main className="main-layout">
        {/* Left Pane: Incidents List */}
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

        {/* Right Pane: Incident Details */}
        <section className="incident-detail-pane">
          {error && <ErrorBanner message={error} onRetry={refetch} />}
          {selectedIncident ? (
            <IncidentDetail incident={selectedIncident} onUpdate={refetch} />
          ) : (
            <div className="empty-state" style={{ height: "100%" }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
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
