import React, { useState, useEffect } from 'react';
import { Network, RefreshCw, Server, Database, Layers, Activity } from 'lucide-react';
import { api } from '../api/client';
import type {
  TopologyGraph,
  ServiceNode,
  BlastRadiusReport,
} from '../types/day3';

interface Props {
  selectedServiceId?: string;
  onSelectService?: (serviceId: string) => void;
}

export const ServiceTopologyPanel: React.FC<Props> = ({
  selectedServiceId,
  onSelectService,
}) => {
  const [graph, setGraph] = useState<TopologyGraph | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeNode, setActiveNode] = useState<ServiceNode | null>(null);
  const [blastRadius, setBlastRadius] = useState<BlastRadiusReport | null>(null);
  const [calculatingBlast, setCalculatingBlast] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.topology.getGraph();
      setGraph(data);
      if (selectedServiceId) {
        const found = data.nodes.find((n) => n.id === selectedServiceId);
        if (found) setActiveNode(found);
      } else if (data.nodes.length > 0 && !activeNode) {
        setActiveNode(data.nodes[0]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load service topology");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [selectedServiceId]);

  const handleNodeClick = (node: ServiceNode) => {
    setActiveNode(node);
    if (onSelectService) onSelectService(node.id);
  };

  const runBlastRadius = async (serviceId: string) => {
    setCalculatingBlast(true);
    try {
      const report = await api.topology.calculateBlastRadius(serviceId);
      setBlastRadius(report);
    } catch (err: any) {
      console.error("Blast radius calculation error:", err);
    } finally {
      setCalculatingBlast(false);
    }
  };

  const getNodeIcon = (type: string) => {
    switch (type) {
      case "database":
        return <Database size={14} />;
      case "cache":
      case "queue":
        return <Layers size={14} />;
      default:
        return <Server size={14} />;
    }
  };

  const getHealthBadge = (health: string) => {
    switch (health) {
      case "failing":
        return <span className="status-pill" style={{ color: "#ef4444", borderColor: "rgba(239, 68, 68, 0.4)" }}>FAILING</span>;
      case "degraded":
        return <span className="status-pill" style={{ color: "#f59e0b", borderColor: "rgba(245, 158, 11, 0.4)" }}>DEGRADED</span>;
      default:
        return <span className="status-pill" style={{ color: "#10b981", borderColor: "rgba(16, 185, 129, 0.4)" }}>HEALTHY</span>;
    }
  };

  // Group nodes by architectural layer for clean schematic grid
  const tierLayers = [
    { label: "Edge & Gateways", ids: ["edge-ingress", "api-gateway"] },
    { label: "Core Microservices", ids: ["auth-service", "checkout-api", "payment-svc"] },
    { label: "Data & Storage Mesh", ids: ["order-db", "redis-cache", "kafka-broker"] },
    { label: "Workers & Streams", ids: ["notification-svc", "analytics-pipeline"] },
  ];

  return (
    <div className="card" style={{ padding: "18px", marginTop: "16px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Network size={18} color="var(--accent-cyan)" />
          <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 600 }}>Multi-Service Dependency Topology & Blast Radius</h3>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {graph && (
            <div style={{ display: "flex", gap: "8px", fontSize: "12px" }}>
              <span style={{ color: "var(--accent-emerald)" }}>● {graph.healthy_count} Healthy</span>
              <span style={{ color: "var(--accent-amber)" }}>● {graph.degraded_count} Degraded</span>
              <span style={{ color: "var(--accent-red)" }}>● {graph.failing_count} Failing</span>
            </div>
          )}
          <button
            className="btn btn-ghost btn-sm"
            onClick={fetchGraph}
            disabled={loading}
            title="Refresh Topology"
          >
            <RefreshCw size={12} className={loading ? "spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "10px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid #ef4444", borderRadius: "6px", fontSize: "12px", color: "#fca5a5", marginBottom: "14px" }}>
          {error}
        </div>
      )}

      {/* Main Grid: Architecture Diagram (Left) & Inspector / Blast Radius (Right) */}
      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: "16px" }}>
        {/* Architecture Layout */}
        <div style={{ background: "rgba(0, 0, 0, 0.25)", borderRadius: "8px", padding: "14px", border: "1px solid var(--border)" }}>
          {tierLayers.map((layer, idx) => {
            const layerNodes = graph?.nodes.filter((n) => layer.ids.includes(n.id)) || [];
            return (
              <div key={idx} style={{ marginBottom: idx < tierLayers.length - 1 ? "16px" : "0" }}>
                <div style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.05em", marginBottom: "6px" }}>
                  {layer.label}
                </div>
                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                  {layerNodes.map((node) => {
                    const isSelected = activeNode?.id === node.id;
                    const isBlastOrigin = blastRadius?.origin_service === node.id;
                    const isUpstreamImpact = blastRadius?.direct_upstream.includes(node.id) || blastRadius?.indirect_upstream.includes(node.id);
                    const isDownstreamImpact = blastRadius?.direct_downstream.includes(node.id) || blastRadius?.indirect_downstream.includes(node.id);

                    let borderColor = "var(--border)";
                    let bg = "var(--bg-card)";
                    if (isSelected) borderColor = "var(--accent-cyan)";
                    if (isBlastOrigin) {
                      borderColor = "#ef4444";
                      bg = "rgba(239, 68, 68, 0.15)";
                    } else if (isUpstreamImpact) {
                      borderColor = "#f59e0b";
                      bg = "rgba(245, 158, 11, 0.12)";
                    } else if (isDownstreamImpact) {
                      borderColor = "rgba(16, 185, 129, 0.5)";
                    }

                    return (
                      <div
                        key={node.id}
                        onClick={() => handleNodeClick(node)}
                        style={{
                          padding: "10px 12px",
                          borderRadius: "6px",
                          border: `1px solid ${borderColor}`,
                          background: bg,
                          cursor: "pointer",
                          minWidth: "160px",
                          flex: "1 1 calc(33% - 10px)",
                          transition: "all 0.15s ease",
                          boxShadow: isSelected ? "0 0 8px rgba(6, 182, 212, 0.25)" : "none",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                          <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 600 }}>
                            {getNodeIcon(node.service_type)}
                            {node.id}
                          </span>
                          <span
                            style={{
                              width: "8px",
                              height: "8px",
                              borderRadius: "50%",
                              background: node.health === "healthy" ? "#10b981" : node.health === "degraded" ? "#f59e0b" : "#ef4444",
                            }}
                          />
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-muted)" }}>
                          <span>{node.current_rps} RPS</span>
                          <span style={{ color: node.error_rate_pct > 0.05 ? "#ef4444" : "inherit" }}>
                            {(node.error_rate_pct * 100).toFixed(1)}% err
                          </span>
                        </div>
                        {isUpstreamImpact && (
                          <div style={{ fontSize: "10px", color: "#f59e0b", marginTop: "4px", fontWeight: 600 }}>
                            ⚠ Upstream At-Risk
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Node Inspector & Blast Radius Details */}
        <div style={{ background: "rgba(0, 0, 0, 0.25)", borderRadius: "8px", padding: "14px", border: "1px solid var(--border)" }}>
          {activeNode ? (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                <div>
                  <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>{activeNode.name}</h4>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                    ID: <code>{activeNode.id}</code> · Tier: {activeNode.tier.toUpperCase()}
                  </div>
                </div>
                {getHealthBadge(activeNode.health)}
              </div>

              {/* Service Metrics Box */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "14px", fontSize: "12px" }}>
                <div style={{ padding: "8px", background: "var(--bg-card)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                  <div style={{ color: "var(--text-muted)", fontSize: "10px" }}>REPLICAS</div>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                    {activeNode.replicas_ready} / {activeNode.replicas_desired} Pods Ready
                  </div>
                </div>
                <div style={{ padding: "8px", background: "var(--bg-card)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                  <div style={{ color: "var(--text-muted)", fontSize: "10px" }}>P99 LATENCY</div>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                    {activeNode.p99_latency_ms} ms
                  </div>
                </div>
              </div>

              {/* Blast Radius Action */}
              <button
                className="btn btn-primary"
                style={{ width: "100%", justifyContent: "center", marginBottom: "14px", fontSize: "12px" }}
                onClick={() => runBlastRadius(activeNode.id)}
                disabled={calculatingBlast}
              >
                <Activity size={14} className={calculatingBlast ? "spin" : ""} />
                <span>{calculatingBlast ? "Calculating Cascade..." : `Analyze Blast Radius for ${activeNode.id}`}</span>
              </button>

              {/* Blast Radius Report Display */}
              {blastRadius && blastRadius.origin_service === activeNode.id && (
                <div style={{ borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>
                      Blast Impact Assessment
                    </span>
                    <span
                      style={{
                        fontSize: "12px",
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: "12px",
                        background: blastRadius.total_blast_score >= 70 ? "rgba(239, 68, 68, 0.2)" : "rgba(245, 158, 11, 0.2)",
                        color: blastRadius.total_blast_score >= 70 ? "#ef4444" : "#f59e0b",
                      }}
                    >
                      Risk Score: {blastRadius.total_blast_score}/100
                    </span>
                  </div>

                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                    <strong>Direct Callers Hit:</strong>{" "}
                    {blastRadius.direct_upstream.length > 0 ? blastRadius.direct_upstream.join(", ") : "None (Edge service)"}
                  </div>

                  {blastRadius.critical_services_impacted.length > 0 && (
                    <div style={{ fontSize: "11px", color: "#fca5a5", marginBottom: "8px" }}>
                      <strong>Critical T0 Services Threatened:</strong> {blastRadius.critical_services_impacted.join(", ")}
                    </div>
                  )}

                  <div style={{ padding: "8px", background: "rgba(6, 182, 212, 0.1)", borderRadius: "4px", border: "1px solid rgba(6, 182, 212, 0.3)", fontSize: "11px", color: "var(--text-secondary)" }}>
                    <strong style={{ color: "var(--accent-cyan)" }}>Autonomous Mitigation Strategy:</strong>
                    <div style={{ marginTop: "4px" }}>{blastRadius.mitigation_guidance}</div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "12px", textAlign: "center", padding: "30px 0" }}>
              Select a service node from the topology diagram to inspect health metrics and compute blast radius.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

