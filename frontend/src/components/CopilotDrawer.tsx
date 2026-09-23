import React, { useState } from 'react';
import { Bot, Send, Sparkles, MessageSquare, Terminal } from 'lucide-react';
import { api } from '../api/client';
import type { Incident } from '../types/incident';

interface CopilotDrawerProps {
  incident: Incident;
  isOpen: boolean;
  onClose: () => void;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  suggestions?: string[];
  referenced_runbook_id?: string;
}

export const CopilotDrawer: React.FC<CopilotDrawerProps> = ({ incident, isOpen, onClose }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `Hello! I'm Medic Copilot. I'm actively analyzing **${incident.title}** on service \`${incident.service}\`. What can I help you investigate or resolve?`,
      suggestions: [
        'What is the root cause candidate?',
        'Suggest diagnostic kubectl commands',
        'Which runbook matches this failure?',
      ]
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(`sess-${incident.id}`);

  if (!isOpen) return null;

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg = text.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const res = await api.copilot.chat(sessionId, userMsg, {
        alert_name: incident.title,
        service: incident.service,
        namespace: 'production',
        severity: incident.severity,
        golden_signals: incident.evidence?.golden_signals,
      });

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: res.reply,
          suggestions: res.suggestions,
          referenced_runbook_id: res.referenced_runbook_id,
        }
      ]);
    } catch (e) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error communicating with the copilot service.',
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-[#121316] border-l border-[#23272f] shadow-2xl flex flex-col z-50 text-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#23272f] bg-[#16181d]">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-white tracking-wide flex items-center gap-1.5">
              Medic SRE Copilot
              <span className="text-[9px] bg-indigo-500/20 text-indigo-300 px-1 py-0.2 rounded border border-indigo-500/30">AI</span>
            </h3>
            <p className="text-[10px] text-slate-400">Contextual Incident Assistant</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-[#23272f]/50 hover:bg-[#23272f]"
        >
          ✕
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3.5 text-xs">
        {messages.map((m, idx) => (
          <div key={idx} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div
              className={`max-w-[85%] rounded-lg p-3 ${
                m.role === 'user'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-[#181a20] border border-[#23272f] text-slate-200'
              }`}
            >
              <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>
              
              {m.referenced_runbook_id && (
                <div className="mt-2 pt-2 border-t border-[#23272f] text-[10px] text-indigo-400 flex items-center gap-1">
                  <Terminal className="w-3 h-3" />
                  <span>Referenced Runbook: <strong>{m.referenced_runbook_id}</strong></span>
                </div>
              )}
            </div>

            {/* Quick Suggestions */}
            {m.suggestions && m.suggestions.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {m.suggestions.map((s, sIdx) => (
                  <button
                    key={sIdx}
                    onClick={() => handleSend(s)}
                    className="text-[10px] bg-[#1a1c23] hover:bg-[#23272f] text-slate-300 border border-[#2a2f3a] rounded px-2 py-1 flex items-center gap-1 transition-colors text-left"
                  >
                    <Sparkles className="w-2.5 h-2.5 text-indigo-400" />
                    <span>{s}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-slate-400 text-xs italic">
            <Bot className="w-3.5 h-3.5 animate-spin text-indigo-400" />
            <span>Copilot is formulating response...</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-[#23272f] bg-[#16181d]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend(input);
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Copilot for diagnostic queries..."
            className="flex-1 bg-[#0e0f12] border border-[#23272f] rounded px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white p-1.5 rounded transition-all active:scale-95"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};
