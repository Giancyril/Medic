import React, { useState, useEffect } from 'react';
import { GitCommit, ArrowRight, Zap, RefreshCw } from 'lucide-react';
import { api } from '../api/client';

interface CorrelationProps {
  service: string;
}

export const CorrelationGraphPanel: React.FC<CorrelationProps> = ({ service }) => {
  const [correlations, setCorrelations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCorrelations = async () => {
    try {
      const res = await api.telemetry.getCorrelations(service);
      setCorrelations(res.correlations || []);
    } catch (e) {
      console.error("Failed to load correlations", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCorrelations();
  }, [service]);

  return (
    <div className="card" style={{ padding: "16px 20px", marginBottom: "20px" }}>
      <div className="card-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Zap size={16} style={{ color: "var(--color-warning)" }} />
          <span>Cross-Signal Anomaly Correlation (Root-Cause Discovery)</span>
        </div>
        <button
          onClick={fetchCorrelations}
          className="btn btn-secondary"
          style={{ padding: "3px 8px", fontSize: "11px", display: "flex", alignItems: "center", gap: "4px" }}
        >
          <RefreshCw size={11} /> Recalculate
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "16px", color: "var(--text-muted)", fontSize: "12px" }}>
          Computing Pearson signal correlation matrices...
        </div>
      ) : correlations.length === 0 ? (
        <div style={{ textAlign: "center", padding: "16px", color: "var(--text-muted)", fontSize: "12px" }}>
          No statistically significant anomaly correlations detected for service `{service}`.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {correlations.map((corr, idx) => {
            const isHigh = Math.abs(corr.correlation_coefficient) >= 0.8;
            return (
              <div
                key={idx}
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "6px",
                  padding: "10px 14px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: "12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <div
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: isHigh ? "var(--color-critical)" : "var(--color-warning)",
                    }}
                  />
                  <div>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{corr.signal_name}</span>
                    <span style={{ color: "var(--text-muted)", marginLeft: "6px" }}>({corr.service})</span>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
                      {corr.description}
                    </div>
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: isHigh ? "var(--color-critical)" : "var(--color-warning)" }}>
                    r = {corr.correlation_coefficient}
                  </div>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>p &lt; {corr.p_value}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
