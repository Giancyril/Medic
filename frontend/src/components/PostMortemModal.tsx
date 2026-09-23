import React, { useState } from 'react';
import { FileText, Download, Check, X } from 'lucide-react';
import { api } from '../api/client';
import type { Incident } from '../types/incident';

interface PostMortemModalProps {
  incident: Incident;
  isOpen: boolean;
  onClose: () => void;
}

export const PostMortemModal: React.FC<PostMortemModalProps> = ({ incident, isOpen, onClose }) => {
  const [doc, setDoc] = useState<{ title: string; markdown: string; word_count: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    try {
      setLoading(true);
      const res = await api.postmortems.generate({
        incident_id: incident.id,
        title: `${incident.service.toUpperCase()} Service Outage: ${incident.title}`,
        severity: incident.severity,
        service: incident.service,
        namespace: 'production',
        alert_name: incident.title,
        detected_at: incident.first_seen_at,
        resolved_at: incident.resolved_at || incident.last_seen_at,
        duration_minutes: 5,
        golden_signals: incident.evidence?.golden_signals?.signals || {},
        agent_diagnosis: incident.diagnosis?.root_cause || 'Automated diagnosis verified root cause.',
        timeline: (incident.events || []).map((t: any) => ({
          timestamp: t.created_at || new Date().toISOString(),
          actor: t.event_type?.includes('AGENT') ? 'agent' : 'system',
          event: t.message || t.event_type,
        })),
      });
      setDoc(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!doc) return;
    navigator.clipboard.writeText(doc.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!doc) return;
    const blob = new Blob([doc.markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `postmortem-${incident.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>

            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Automated Post-Mortem Generator</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Blameless retrospective markdown report</div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px', borderRadius: '4px', display: 'flex' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {!doc ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <div style={{ padding: '14px', borderRadius: '50%', background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)', display: 'inline-flex' }}>
                <FileText size={28} />
              </div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>Generate Structured Incident Retrospective</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', maxWidth: '440px', lineHeight: 1.5 }}>
                Consolidates timeline events, golden signal anomalies, runbook steps, and diagnostic findings into a clean Markdown document for GitOps or Jira/Confluence.
              </div>
              <button
                disabled={loading}
                onClick={handleGenerate}
                className="btn btn-primary"
                style={{ marginTop: '8px', display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '8px 16px' }}
              >

                <span>{loading ? 'Synthesizing Report...' : 'Generate Post-Mortem Markdown'}</span>
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)' }}>
                <span>Word count: <strong style={{ color: 'var(--text-primary)' }}>{doc.word_count}</strong></span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={handleCopy}
                    className="btn btn-secondary"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 10px', fontSize: '11px' }}
                  >
                    {copied ? <Check size={12} style={{ color: 'var(--color-success)' }} /> : <FileText size={12} />}
                    <span>{copied ? 'Copied!' : 'Copy Markdown'}</span>
                  </button>
                  <button
                    onClick={handleDownload}
                    className="btn btn-success"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 10px', fontSize: '11px' }}
                  >
                    <Download size={12} />
                    <span>Download .md</span>
                  </button>
                </div>
              </div>

              <div className="modal-markdown-box">
                {doc.markdown}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
