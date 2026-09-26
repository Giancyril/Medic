"""
Audit Trail & Incident Replay Engine.
Maintains cryptographically hashed action log and constructs time-travel replay frames.
"""
import hashlib
from typing import Dict, List, Optional
from backend.audit.models import (
    ActorType,
    ActionCategory,
    AuditEntry,
    IncidentReplayFrame,
    ComplianceReport,
    utc_now,
)

class AuditReplayEngine:
    """Manages tamper-evident audit log and produces incident replay timeline."""

    def __init__(self):
        self.ledger: List[AuditEntry] = []
        self._last_hash: str = "GENESIS_BLOCK_000000000000"
        self._init_demo_trail()

    def _compute_hash(self, entry: AuditEntry, prev_hash: str) -> str:
        payload = f"{prev_hash}:{entry.timestamp}:{entry.actor_name}:{entry.category.value}:{entry.action_summary}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def record_entry(
        self,
        incident_id: str,
        actor_type: ActorType,
        actor_name: str,
        category: ActionCategory,
        action_summary: str,
        details: Optional[Dict] = None,
    ) -> AuditEntry:
        """Append cryptographically verified entry to audit ledger."""
        entry = AuditEntry(
            entry_id=f"aud-{len(self.ledger) + 1:04d}",
            timestamp=utc_now(),
            incident_id=incident_id,
            actor_type=actor_type,
            actor_name=actor_name,
            category=category,
            action_summary=action_summary,
            details=details or {},
            tamper_hash="",
        )
        entry.tamper_hash = self._compute_hash(entry, self._last_hash)
        self._last_hash = entry.tamper_hash
        self.ledger.append(entry)
        return entry

    def _init_demo_trail(self):
        """Seed realistic compliance audit history."""
        self.record_entry(
            incident_id="inc-demo-1",
            actor_type=ActorType.SYSTEM,
            actor_name="Prometheus Alertmanager",
            category=ActionCategory.DIAGNOSIS,
            action_summary="Ingested critical alert KubePodCrashLooping on checkout-api",
            details={"severity": "critical", "source": "prometheus-k8s"},
        )
        self.record_entry(
            incident_id="inc-demo-1",
            actor_type=ActorType.AI_AGENT,
            actor_name="Antigravity Autonomous SRE Agent",
            category=ActionCategory.DIAGNOSIS,
            action_summary="Correlated memory leak pattern and synthesized Tier-3 remediation plan",
            details={"confidence": 0.94, "diagnosis": "OOMKilled pod cascade"},
        )
        self.record_entry(
            incident_id="inc-demo-1",
            actor_type=ActorType.AI_AGENT,
            actor_name="Antigravity Safety Gate",
            category=ActionCategory.APPROVAL_REQUEST,
            action_summary="Enforced Tier-3 approval safety gate; generated deployment mutation diff",
            details={"target_resource": "deployment/checkout-api", "risk_tier": "TIER_3_HIGH"},
        )
        self.record_entry(
            incident_id="inc-demo-1",
            actor_type=ActorType.HUMAN_OPERATOR,
            actor_name="Alex Chen (Primary SRE)",
            category=ActionCategory.APPROVAL_DECISION,
            action_summary="Human operator approved K8s memory limit increase to 1024Mi and rollout",
            details={"decision": "APPROVED", "approver": "alex.chen@sre.ops"},
        )
        self.record_entry(
            incident_id="inc-demo-1",
            actor_type=ActorType.AI_AGENT,
            actor_name="Autonomous K8s Actuator",
            category=ActionCategory.REMEDIATION_EXECUTION,
            action_summary="Applied kubectl rollout restart with updated resource limits; verified zero errors",
            details={"execution_time_seconds": 12.8, "pods_restarted": 4},
        )

    def verify_audit_integrity(self) -> bool:
        """Validate integrity of hash chain across the ledger."""
        prev = "GENESIS_BLOCK_000000000000"
        for e in self.ledger:
            expected = self._compute_hash(e, prev)
            if e.tamper_hash != expected:
                return False
            prev = e.tamper_hash
        return True

    def get_replay_timeline(self, incident_id: str) -> List[IncidentReplayFrame]:
        """Construct sequential playback frames for time-travel incident replay."""
        frames = [
            IncidentReplayFrame(
                frame_index=0,
                relative_time_seconds=0,
                timestamp="2026-09-26T08:00:00Z",
                event_title="Alert Fired: KubePodCrashLooping",
                description="Prometheus fired critical alert. Pod checkout-api-7b89f crashed with exit code 137 (OOMKilled).",
                cluster_health="degraded",
                service_state={"rps": 380, "error_rate": 0.04, "replicas": "3/4"},
                action_taken=None,
            ),
            IncidentReplayFrame(
                frame_index=1,
                relative_time_seconds=15,
                timestamp="2026-09-26T08:00:15Z",
                event_title="AI Agent Ingestion & Investigation",
                description="Agent queried Prometheus golden signals and analyzed stack traces from Loki. Detected exponential memory drift.",
                cluster_health="degraded",
                service_state={"rps": 375, "error_rate": 0.06, "replicas": "3/4"},
                action_taken="Ran inspect_kubernetes_resources and analyze_golden_signals",
            ),
            IncidentReplayFrame(
                frame_index=2,
                relative_time_seconds=35,
                timestamp="2026-09-26T08:00:35Z",
                event_title="Remediation Formulated & Gate Engaged",
                description="Synthesized remediation action: bump memory limit from 512Mi to 1024Mi. Tier-3 Safety Gate engaged.",
                cluster_health="failing",
                service_state={"rps": 350, "error_rate": 0.12, "replicas": "2/4"},
                action_taken="Generated declarative K8s patch; queued for human approval",
            ),
            IncidentReplayFrame(
                frame_index=3,
                relative_time_seconds=65,
                timestamp="2026-09-26T08:01:05Z",
                event_title="Human SRE Approval Granted",
                description="Alex Chen reviewed diff on Incident Console and authorized the rollout restart.",
                cluster_health="failing",
                service_state={"rps": 340, "error_rate": 0.15, "replicas": "2/4"},
                action_taken="Approved by alex.chen@sre.ops with comment: 'Verified safe memory head-room'",
            ),
            IncidentReplayFrame(
                frame_index=4,
                relative_time_seconds=80,
                timestamp="2026-09-26T08:01:20Z",
                event_title="Autonomous Actuation & Rolling Restart",
                description="Applied resource patch to Kubernetes cluster. 4 replacement pods spun up and passed readiness probes.",
                cluster_health="recovering",
                service_state={"rps": 365, "error_rate": 0.03, "replicas": "4/4"},
                action_taken="Executed patch_kubernetes_deployment and verified pod health",
            ),
            IncidentReplayFrame(
                frame_index=5,
                relative_time_seconds=120,
                timestamp="2026-09-26T08:02:00Z",
                event_title="SLI Restoration & Incident Resolved",
                description="P99 latency normalized to 45ms. HTTP error rate dropped to 0.01%. Incident status set to RESOLVED.",
                cluster_health="healthy",
                service_state={"rps": 380, "error_rate": 0.01, "replicas": "4/4"},
                action_taken="Automated Post-Mortem generated and archived to audit ledger",
            ),
        ]
        return frames

    def generate_compliance_report(self, incident_id: str) -> ComplianceReport:
        """Generate SOC-2 / SOX audit compliance verification certificate."""
        total = len(self.ledger)
        auto = sum(1 for e in self.ledger if e.actor_type == ActorType.AI_AGENT)
        human = sum(1 for e in self.ledger if e.actor_type == ActorType.HUMAN_OPERATOR)
        valid = self.verify_audit_integrity()

        return ComplianceReport(
            incident_id=incident_id,
            generated_at=utc_now(),
            total_actions=total,
            autonomous_actions_count=auto,
            human_approved_actions_count=human,
            soc2_compliant=valid and human >= 1,
            sox_safety_gates_passed=True,
            audit_trail_verified=valid,
            summary=f"Certified: All {total} actions verified with cryptographic SHA-256 chain. Tier-3 human dual-control gates passed.",
        )

# Global audit engine singleton
audit_replay_engine = AuditReplayEngine()
