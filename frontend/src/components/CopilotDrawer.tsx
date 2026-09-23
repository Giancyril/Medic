import React, { useState } from 'react';
import { Bot, Send, Terminal, X } from 'lucide-react';
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
  const sessionId = `sess-${incident.id}`;

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
    <>
      <div className="copilot-backdrop" onClick={onClose} />
      <div className="copilot-drawer">
        {/* Header */}
        <div className="copilot-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>

            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                Medic SRE Copilot
                <span style={{ fontSize: '9px', background: 'rgba(99, 102, 241, 0.2)', color: '#a5b4fc', padding: '1px 5px', borderRadius: '3px', fontWeight: 600 }}>AI</span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Contextual Incident Assistant</div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px', borderRadius: '4px', display: 'flex' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Messages */}
        <div className="copilot-messages">
          {messages.map((m, idx) => (
            <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div className={m.role === 'user' ? 'copilot-msg-user' : 'copilot-msg-assistant'}>
                <div>{m.content}</div>
                {m.referenced_runbook_id && (
                  <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)', fontSize: '11px', color: '#818cf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Terminal size={12} />
                    <span>Referenced Runbook: <strong>{m.referenced_runbook_id}</strong></span>
                  </div>
                )}
              </div>

              {m.suggestions && m.suggestions.length > 0 && (
                <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {m.suggestions.map((s, sIdx) => (
                    <button
                      key={sIdx}
                      onClick={() => handleSend(s)}
                      className="copilot-pill-btn"
                    >
                      <span>{s}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '12px', fontStyle: 'italic' }}>
              <Bot size={14} className="spinner" />
              <span>Copilot is formulating response...</span>
            </div>
          )}
        </div>

        {/* Input */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend(input);
          }}
          className="copilot-input-bar"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Copilot for diagnostic queries..."
            className="copilot-input"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn btn-primary"
            style={{ padding: '6px 12px' }}
          >
            <Send size={13} />
          </button>
        </form>
      </div>
    </>
  );
};

