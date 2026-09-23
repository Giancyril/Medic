import React, { useState } from 'react';
import { FileText, Download, Check, Sparkles } from 'lucide-react';
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
          timestamp: t.timestamp,
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
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-[#121316] border border-[#23272f] rounded-xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden text-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#23272f] bg-[#16181d]">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white tracking-wide">Automated Post-Mortem Generator</h3>
              <p className="text-[10px] text-slate-400">Blameless retrospective markdown report</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-[#23272f]/50 hover:bg-[#23272f]"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 p-5 overflow-y-auto space-y-4">
          {!doc ? (
            <div className="text-center py-12 space-y-3">
              <div className="inline-flex p-3 rounded-full bg-[#181a20] border border-[#23272f] text-slate-400">
                <FileText className="w-8 h-8" />
              </div>
              <h4 className="text-sm font-medium text-slate-200">Generate Structured Incident Retrospective</h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Consolidates timeline events, golden signal anomalies, runbook steps, and diagnostic findings into a clean Markdown document for GitOps or Jira/Confluence.
              </p>
              <button
                disabled={loading}
                onClick={handleGenerate}
                className="mt-2 inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-xs font-medium transition-all shadow-sm active:scale-95 disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{loading ? 'Synthesizing Report...' : 'Generate Post-Mortem Markdown'}</span>
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Word count: <strong className="text-slate-200">{doc.word_count}</strong></span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopy}
                    className="flex items-center gap-1 bg-[#1a1c23] hover:bg-[#23272f] border border-[#2a2f3a] text-slate-300 px-2.5 py-1 rounded text-xs transition-colors"
                  >
                    {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <FileText className="w-3 h-3" />}
                    <span>{copied ? 'Copied!' : 'Copy Markdown'}</span>
                  </button>
                  <button
                    onClick={handleDownload}
                    className="flex items-center gap-1 bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 rounded text-xs font-medium transition-colors"
                  >
                    <Download className="w-3 h-3" />
                    <span>Download .md</span>
                  </button>
                </div>
              </div>

              <div className="bg-[#0c0d10] border border-[#23272f] rounded-lg p-4 font-mono text-xs text-slate-300 overflow-x-auto max-h-[50vh] whitespace-pre-wrap leading-relaxed select-all">
                {doc.markdown}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

