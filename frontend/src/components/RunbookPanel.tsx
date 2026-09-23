import React, { useState, useEffect } from 'react';
import { BookOpen, Play, CheckCircle, XCircle, Clock, ShieldCheck, ChevronRight } from 'lucide-react';
import { api } from '../api/client';
import type { Incident } from '../types/incident';

interface RunbookPanelProps {
  incident: Incident;
}

export const RunbookPanel: React.FC<RunbookPanelProps> = ({ incident }) => {
  const [catalog, setCatalog] = useState<any[]>([]);
  const [matched, setMatched] = useState<any | null>(null);
  const [matching, setMatching] = useState(false);
  const [execution, setExecution] = useState<any | null>(null);
  const [executing, setExecuting] = useState(false);
  const [activeTab, setActiveTab] = useState<'match' | 'catalog' | 'execution'>('match');
  const [approvingStep, setApprovingStep] = useState<number | null>(null);

  useEffect(() => {
    // Load catalog
    api.runbooks.catalog()
      .then(res => setCatalog(res.runbooks || []))
      .catch(console.error);

    // Auto-match for current incident
    if (incident) {
      setMatching(true);
      api.runbooks.match(incident, incident.evidence)
        .then(res => {
          setMatched(res);
          setMatching(false);
        })
        .catch(() => {
          setMatched(null);
          setMatching(false);
        });
    }
  }, [incident.id]);

  const handleTrigger = async (runbookId: string) => {
    try {
      setExecuting(true);
      const res = await api.runbooks.trigger(runbookId, incident, incident.evidence);
      setActiveTab('execution');
      // Poll execution status
      const pollInterval = setInterval(async () => {
        try {
          const status = await api.runbooks.status(res.execution_id);
          setExecution(status);
          if (status.is_completed) {
            clearInterval(pollInterval);
            setExecuting(false);
          }
        } catch {
          clearInterval(pollInterval);
          setExecuting(false);
        }
      }, 1000);
    } catch (e) {
      console.error(e);
      setExecuting(false);
    }
  };

  const handleApproveStep = async (stepIndex: number, approved: boolean) => {
    if (!execution) return;
    try {
      setApprovingStep(stepIndex);
      await api.runbooks.approve(execution.runbook_id, stepIndex, approved, 'SRE-Operator');
      const updated = await api.runbooks.status(execution.runbook_id);
      setExecution(updated);
    } catch (e) {
      console.error(e);
    } finally {
      setApprovingStep(null);
    }
  };

  return (
    <div className="runbook-container">
      {/* Header */}
      <div className="runbook-header">
        <div className="runbook-title-group">
          <BookOpen size={16} style={{ color: 'var(--color-success)' }} />
          <span>Runbook Automation Engine</span>
        </div>
        <div className="runbook-tab-group">
          <button
            onClick={() => setActiveTab('match')}
            className={`runbook-tab-btn ${activeTab === 'match' ? 'active' : ''}`}
          >
            Recommended
          </button>
          <button
            onClick={() => setActiveTab('catalog')}
            className={`runbook-tab-btn ${activeTab === 'catalog' ? 'active' : ''}`}
          >
            Catalog ({catalog.length})
          </button>
          {execution && (
            <button
              onClick={() => setActiveTab('execution')}
              className={`runbook-tab-btn ${activeTab === 'execution' ? 'active' : ''}`}
            >
              <span>Execution</span>
              {execution.is_completed ? (
                execution.success ? <CheckCircle size={12} style={{ color: 'var(--color-success)' }} /> : <XCircle size={12} style={{ color: 'var(--color-critical)' }} />
              ) : (
                <Clock size={12} className="spinner" style={{ color: 'var(--color-warning)' }} />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="runbook-body">
        {activeTab === 'match' && (
          <div>
            {matching ? (
              <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '12px' }}>
                Analyzing incident telemetry & symptoms for optimal runbook match...
              </div>
            ) : matched ? (
              <div className="runbook-card">
                <div className="runbook-card-header">
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '13px' }}>{matched.runbook_name}</span>
                      <span className="runbook-match-badge">
                        {Math.round(matched.confidence_score * 100)}% Match
                      </span>
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>{matched.runbook_description}</p>
                  </div>
                </div>

                <div className="runbook-meta-grid">
                  <div>Severity: <strong style={{ color: 'var(--color-warning)', textTransform: 'uppercase' }}>{matched.severity}</strong></div>
                  <div>Steps: <strong>{matched.automated_step_count}/{matched.step_count} automated</strong></div>
                  <div>Est. Time: <strong>{matched.estimated_duration_minutes}m</strong></div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '4px' }}>
                  <button
                    disabled={executing}
                    onClick={() => handleTrigger(matched.runbook_id)}
                    className="btn btn-success"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '6px 14px', fontSize: '12px' }}
                  >
                    <Play size={12} style={{ fill: 'currentColor' }} />
                    <span>{executing ? 'Executing Runbook...' : 'Execute Runbook'}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)', fontSize: '12px' }}>
                No automatic runbook recommendation matched with high confidence. Explore the catalog above.
              </div>
            )}
          </div>
        )}

        {activeTab === 'catalog' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {catalog.map((rb) => (
              <div key={rb.id} className="runbook-step-row">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{rb.name}</span>
                  <button
                    onClick={() => handleTrigger(rb.id)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--color-success)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '2px', fontWeight: 600, fontSize: '11px' }}
                  >
                    Run <ChevronRight size={12} />
                  </button>
                </div>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '2px 0' }}>{rb.description}</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10px', color: 'var(--text-muted)' }}>
                  <span>{rb.step_count} steps</span>
                  <span>•</span>
                  <span>{rb.estimated_duration_minutes}m duration</span>
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: '4px' }}>
                    {rb.tags?.map((t: string) => (
                      <span key={t} style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)', padding: '2px 6px', borderRadius: '3px' }}>{t}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'execution' && execution && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
              <div>
                <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{execution.runbook_name}</h4>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Target incident: {execution.incident_id}</span>
              </div>
              <span className={`badge ${execution.is_completed ? (execution.success ? 'badge-RESOLVED' : 'badge-CRITICAL') : 'badge-INVESTIGATING'}`}>
                {execution.is_completed ? (execution.success ? 'Success' : 'Failed') : 'In Progress'}
              </span>
            </div>

            {/* Steps Timeline */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {execution.steps?.map((step: any, idx: number) => {
                const isPassed = step.status === 'passed';
                const isFailed = step.status === 'failed';
                const isPending = step.status === 'pending';
                const isRunning = step.status === 'running';

                return (
                  <div key={idx} className="runbook-step-row">
                    <div className="runbook-step-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {isPassed && <CheckCircle size={14} style={{ color: 'var(--color-success)', flexShrink: 0 }} />}
                        {isFailed && <XCircle size={14} style={{ color: 'var(--color-critical)', flexShrink: 0 }} />}
                        {isRunning && <Clock size={14} className="spinner" style={{ color: 'var(--color-warning)', flexShrink: 0 }} />}
                        {isPending && <Clock size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{step.title}</span>
                      </div>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{step.action_type}</span>
                    </div>

                    {step.output && (
                      <div className="runbook-step-output">
                        {step.output}
                      </div>
                    )}

                    {step.action_type === 'human_confirmation' && isPending && (
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)' }}>
                        <span style={{ fontSize: '11px', color: 'var(--color-warning)', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          <ShieldCheck size={14} /> Safety Gate: Approval Required
                        </span>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button
                            disabled={approvingStep === idx}
                            onClick={() => handleApproveStep(idx, false)}
                            className="btn btn-danger"
                            style={{ padding: '3px 8px', fontSize: '11px' }}
                          >
                            Reject
                          </button>
                          <button
                            disabled={approvingStep === idx}
                            onClick={() => handleApproveStep(idx, true)}
                            className="btn btn-success"
                            style={{ padding: '3px 8px', fontSize: '11px' }}
                          >
                            Approve
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
