import os
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.runbooks.schema import Runbook

CATALOG_DIR = Path(__file__).parent / "catalog"

_CACHED_CATALOG: Optional[List[Runbook]] = None

def load_runbook_catalog(force_reload: bool = False) -> List[Runbook]:
    """Loads and validates all declarative YAML runbooks from the catalog directory."""
    global _CACHED_CATALOG
    if _CACHED_CATALOG is not None and not force_reload:
        return _CACHED_CATALOG

    catalog: List[Runbook] = []
    if not CATALOG_DIR.exists():
        return []

    for file_path in CATALOG_DIR.glob("*.yaml"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    catalog.append(Runbook(**data))
        except Exception as e:
            print(f"Error loading runbook {file_path}: {e}")

    _CACHED_CATALOG = catalog
    return catalog

def match_runbook(
    incident: Dict[str, Any],
    evidence: Optional[Dict[str, Any]] = None,
    catalog: Optional[List[Runbook]] = None
) -> Optional[Tuple[Runbook, float]]:
    """
    Correlates incident alert metadata and gathered investigation telemetry
    against the SRE runbook catalog. Returns the highest-scoring runbook and score.
    """
    matches = find_all_matching_runbooks(incident, evidence, catalog)
    return matches[0] if matches else None

def find_all_matching_runbooks(
    incident: Dict[str, Any],
    evidence: Optional[Dict[str, Any]] = None,
    catalog: Optional[List[Runbook]] = None
) -> List[Tuple[Runbook, float]]:
    """
    Evaluates all runbooks against incident alert signatures and evidence telemetry,
    returning a sorted list of (Runbook, confidence_score) tuples.
    """
    runbooks = catalog or load_runbook_catalog()
    scored_runbooks: List[Tuple[Runbook, float]] = []

    alert_name = str(incident.get("alert_name", "")).lower()
    title = str(incident.get("title", "")).lower()
    service = str(incident.get("service", ""))
    labels = incident.get("labels", {}) or {}
    diagnosis = incident.get("diagnosis", {}) or {}
    root_cause = str(diagnosis.get("root_cause", "")).lower()
    action_type = str(diagnosis.get("action_type", "")).upper()

    ev = evidence or incident.get("evidence", {}) or {}
    pods = ev.get("pods", [])
    logs = ev.get("logs", {})
    errors = logs.get("errors", [])
    signals = ev.get("golden_signals", {}).get("signals", {})

    for rb in runbooks:
        score = 0.0

        # 1. Alert Pattern Correlation (up to +0.45)
        for pattern in rb.alert_patterns:
            p_lower = pattern.lower()
            if p_lower in alert_name or p_lower in title or any(p_lower in str(v).lower() for v in labels.values()):
                score += 0.45
                break

        # 2. Target Service Scope Matching (+0.10)
        if rb.target_service == "*" or rb.target_service == service:
            score += 0.10

        # 3. Direct Remediation / Diagnosis Action Alignment (+0.25)
        if rb.id == "rb-k8s-oom-recovery":
            has_exit_137 = any(p.get("exit_code") == 137 or p.get("reason") == "OOMKilled" for p in pods)
            if has_exit_137 or "oom" in root_cause or action_type == "RESTART_POD":
                score += 0.35
            if signals.get("memory_saturation_pct", 0) > 85:
                score += 0.10

        elif rb.id == "rb-k8s-crashloop-rollback":
            has_crash = any(p.get("status") == "CrashLoopBackOff" or p.get("exit_code") == 1 for p in pods)
            if has_crash or "crash" in root_cause or action_type == "ROLLBACK_DEPLOYMENT":
                score += 0.35
            if any("config" in str(err.get("message", "")).lower() for err in errors):
                score += 0.10

        elif rb.id == "rb-k8s-upstream-timeout":
            has_timeout = any("timeout" in str(err.get("message", "")).lower() or "504" in str(err.get("message", "")) for err in errors)
            if has_timeout or "timeout" in root_cause or signals.get("latency_p99_ms", 0) > 1000:
                score += 0.35
            if signals.get("error_rate_pct", 0) > 5.0 or action_type == "SCALE_DEPLOYMENT":
                score += 0.10

        if score > 0.35:
            normalized_score = min(1.0, round(score, 2))
            scored_runbooks.append((rb, normalized_score))

    # Sort descending by score
    scored_runbooks.sort(key=lambda x: x[1], reverse=True)
    return scored_runbooks
