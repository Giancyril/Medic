

interface Props { visible: boolean; message?: string; }
export function LoadingOverlay({ visible, message = "Loading…" }: Props) {
  if (!visible) return null;
  return (
    <div className="empty-state" style={{ minHeight: 200 }}>
      <div className="spinner" />
      <p>{message}</p>
    </div>
  );
}

interface ErrorProps { message: string; onRetry?: () => void; }
export function ErrorBanner({ message, onRetry }: ErrorProps) {
  return (
    <div style={{ margin: "16px", padding: "14px 16px", background: "rgba(255,71,87,0.08)", border: "1px solid rgba(255,71,87,0.25)", borderRadius: "var(--radius)", display: "flex", alignItems: "center", gap: "10px" }}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--sev-critical)" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
      <span style={{ flex: 1, fontSize: "12px", color: "var(--sev-critical)" }}>{message}</span>
      {onRetry && <button className="btn btn-ghost btn-sm" onClick={onRetry}>Retry</button>}
    </div>
  );
}
