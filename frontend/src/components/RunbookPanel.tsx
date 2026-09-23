import React, { useState, useEffect } from 'react';
import { BookOpen, Play, CheckCircle, XCircle, AlertCircle, Clock, ShieldCheck, ChevronRight } from 'lucide-react';
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
    <div className="bg-[#121316] border border-[#23272f] rounded-lg overflow-hidden flex flex-col h-full text-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#23272f] bg-[#16181d]">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-sm tracking-wide">Runbook Automation Engine</span>
        </div>
        <div className="flex gap-1 bg-[#0d0e11] p-0.5 rounded border border-[#23272f] text-xs">
          <button
            onClick={() => setActiveTab('match')}
            className={`px-2.5 py-1 rounded transition-colors ${activeTab === 'match' ? 'bg-[#23272f] text-white font-medium' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Recommended
          </button>
          <button
            onClick={() => setActiveTab('catalog')}
            className={`px-2.5 py-1 rounded transition-colors ${activeTab === 'catalog' ? 'bg-[#23272f] text-white font-medium' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Catalog ({catalog.length})
          </button>
          {execution && (
            <button
              onClick={() => setActiveTab('execution')}
              className={`px-2.5 py-1 rounded transition-colors flex items-center gap-1 ${activeTab === 'execution' ? 'bg-[#23272f] text-white font-medium' : 'text-slate-400 hover:text-slate-200'}`}
            >
              <span>Execution</span>
              {execution.is_completed ? (
                execution.success ? <CheckCircle className="w-3 h-3 text-emerald-400" /> : <XCircle className="w-3 h-3 text-rose-400" />
              ) : (
                <Clock className="w-3 h-3 text-amber-400 animate-spin" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 flex-1 overflow-y-auto space-y-4">
        {activeTab === 'match' && (
          <div>
            {matching ? (
              <div className="text-center py-8 text-slate-400 text-xs">
                Analyzing incident telemetry & symptoms for optimal runbook match...
              </div>
            ) : matched ? (
              <div className="border border-emerald-500/30 bg-emerald-950/10 rounded-lg p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-emerald-400 text-sm">{matched.runbook_name}</span>
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-500/30">
                        {Math.round(matched.confidence_score * 100)}% Match
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">{matched.runbook_description}</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-300 py-1 border-y border-[#23272f]/60">
                  <div>Severity: <span className="uppercase text-amber-400 font-mono">{matched.severity}</span></div>
                  <div>Steps: <span className="font-mono">{matched.automated_step_count}/{matched.step_count} automated</span></div>
                  <div>Est. Time: <span className="font-mono">{matched.estimated_duration_minutes}m</span></div>
                </div>

                <div className="flex justify-end pt-1">
                  <button
                    disabled={executing}
                    onClick={() => handleTrigger(matched.runbook_id)}
                    className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded text-xs font-medium transition-all shadow-sm active:scale-95 disabled:opacity-50"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>{executing ? 'Executing Runbook...' : 'Execute Runbook'}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-slate-500 text-xs">
                No automatic runbook recommendation matched with high confidence. Explore the catalog below.
              </div>
            )}
          </div>
        )}

        {activeTab === 'catalog' && (
          <div className="space-y-2">
            {catalog.map((rb) => (
              <div key={rb.id} className="border border-[#23272f] hover:border-slate-700 bg-[#16181d] rounded p-3 text-xs transition-colors">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-200">{rb.name}</span>
                  <button
                    onClick={() => handleTrigger(rb.id)}
                    className="text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-0.5"
                  >
                    Run <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
                <p className="text-slate-400 text-[11px] mt-1">{rb.description}</p>
                <div className="flex items-center gap-2 mt-2 text-[10px] text-slate-500">
                  <span>{rb.step_count} steps</span>
                  <span>•</span>
                  <span>{rb.estimated_duration_minutes}m duration</span>
                  <div className="flex gap-1 ml-auto">
                    {rb.tags?.map((t: string) => (
                      <span key={t} className="bg-[#23272f] text-slate-400 px-1 rounded">{t}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'execution' && execution && (
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[#23272f]">
              <div>
                <h4 className="font-medium text-xs text-slate-200">{execution.runbook_name}</h4>
                <span className="text-[10px] text-slate-500">Target incident: {execution.incident_id}</span>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded border uppercase font-mono ${
                execution.is_completed 
                  ? (execution.success ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border-rose-500/30 text-rose-400')
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-400 animate-pulse'
              }`}>
                {execution.is_completed ? (execution.success ? 'Success' : 'Failed') : 'In Progress'}
              </span>
            </div>

            {/* Steps Timeline */}
            <div className="space-y-2">
              {execution.steps?.map((step: any, idx: number) => {
                const isPassed = step.status === 'passed';
                const isFailed = step.status === 'failed';
                const isPending = step.status === 'pending';
                const isRunning = step.status === 'running';

                return (
                  <div key={idx} className="border border-[#23272f] bg-[#16181d] rounded p-2.5 text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        {isPassed && <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
                        {isFailed && <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />}
                        {isRunning && <Clock className="w-3.5 h-3.5 text-amber-400 animate-spin shrink-0" />}
                        {isPending && <Clock className="w-3.5 h-3.5 text-slate-500 shrink-0" />}
                        <span className="font-medium text-slate-200">{step.title}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 uppercase">{step.action_type}</span>
                    </div>

                    {step.output && (
                      <div className="bg-[#0e0f12] p-1.5 rounded font-mono text-[11px] text-slate-300 border border-[#23272f]">
                        {step.output}
                      </div>
                    )}

                    {step.action_type === 'human_confirmation' && isPending && (
                      <div className="flex items-center gap-2 pt-1 border-t border-[#23272f]">
                        <span className="text-[11px] text-amber-400 flex items-center gap-1">
                          <ShieldCheck className="w-3 h-3" /> Safety Gate: Approval Required
                        </span>
                        <div className="ml-auto flex gap-1">
                          <button
                            disabled={approvingStep === idx}
                            onClick={() => handleApproveStep(idx, false)}
                            className="bg-rose-900/40 hover:bg-rose-900/60 text-rose-300 px-2 py-0.5 rounded text-[10px] border border-rose-800"
                          >
                            Reject
                          </button>
                          <button
                            disabled={approvingStep === idx}
                            onClick={() => handleApproveStep(idx, true)}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-0.5 rounded text-[10px]"
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
