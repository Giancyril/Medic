import { useState, useEffect, useCallback, useRef } from "react";
import type { Incident, SSEMessage } from "../types/incident";
import { api } from "../api/client";

export function useIncidents(pollMs = 0) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastEvent, setLastEvent] = useState<SSEMessage | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const data = await api.incidents.list({ limit: 100 });
      setIncidents(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch incidents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();

    // Connect SSE stream for real-time updates
    try {
      const es = api.incidents.stream();
      esRef.current = es;

      es.onmessage = (event) => {
        try {
          const msg: SSEMessage = JSON.parse(event.data);
          setLastEvent(msg);
          // Refetch on incident changes
          if (["incident_created", "incident_updated", "incident_status_changed", "incident_diagnosed", "incident_resolved", "incident_escalated"].includes(msg.event)) {
            fetchAll();
          }
        } catch {}
      };

      es.onerror = () => {
        es.close();
      };
    } catch {}

    return () => {
      esRef.current?.close();
    };
  }, [fetchAll]);

  // Optional polling fallback
  useEffect(() => {
    if (!pollMs) return;
    const t = setInterval(fetchAll, pollMs);
    return () => clearInterval(t);
  }, [pollMs, fetchAll]);

  return { incidents, loading, error, lastEvent, refetch: fetchAll };
}

export function useIncident(id: string | null) {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await api.incidents.get(id);
      setIncident(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch incident");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetch(); }, [fetch]);

  return { incident, loading, error, refetch: fetch };
}
