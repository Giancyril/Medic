"""
On-Call Schedule & Escalation Engine.
Dispatches pages across tiers, tracks acknowledgments, and escalates unhandled incidents.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid
from backend.oncall.models import (
    PageStatus,
    ResponderRole,
    Responder,
    OnCallShift,
    PageEvent,
    OnCallRosterStatus,
    utc_now,
)

class OnCallEngine:
    """Manages active on-call shifts, paging alerts, and tiered escalation."""

    def __init__(self):
        self.responders: Dict[str, Responder] = {}
        self.active_shift: Optional[OnCallShift] = None
        self.pages: Dict[str, PageEvent] = {}
        self._init_default_roster()

    def _init_default_roster(self):
        """Seed standard SRE on-call rotation."""
        r_primary = Responder(
            id="resp-alex",
            name="Alex Chen",
            email="alex.chen@sre.ops",
            role=ResponderRole.PRIMARY_SRE,
            phone="+1 (555) 019-4821",
            avatar_initials="AC",
        )
        r_secondary = Responder(
            id="resp-maria",
            name="Maria Santos",
            email="maria.santos@sre.ops",
            role=ResponderRole.SECONDARY_SRE,
            phone="+1 (555) 019-8832",
            avatar_initials="MS",
        )
        r_lead = Responder(
            id="resp-david",
            name="David Vance",
            email="david.vance@sre.ops",
            role=ResponderRole.INCIDENT_COMMANDER,
            phone="+1 (555) 019-9944",
            avatar_initials="DV",
        )

        self.responders[r_primary.id] = r_primary
        self.responders[r_secondary.id] = r_secondary
        self.responders[r_lead.id] = r_lead

        self.active_shift = OnCallShift(
            shift_id="shift-emea-na-2026-w39",
            rotation_name="Production Core Reliability (24/7 Follow-the-Sun)",
            primary_responder=r_primary,
            secondary_responder=r_secondary,
            escalation_lead=r_lead,
            starts_at="2026-09-25T08:00:00Z",
            ends_at="2026-09-26T08:00:00Z",
            tz="UTC",
        )

        # Pre-seed one acknowledged page for realistic MTTA calculation
        demo_page = PageEvent(
            page_id="page-seed-01",
            incident_id="inc-demo-1",
            tier_level=1,
            responder=r_primary,
            status=PageStatus.ACKNOWLEDGED,
            dispatched_at="2026-09-25T18:45:00Z",
            acknowledged_at="2026-09-25T18:45:38Z",
            notes="Acknowledged in 38s via mobile push.",
        )
        self.pages[demo_page.page_id] = demo_page

    def dispatch_page(self, incident_id: str, tier: int = 1, notes: str = "") -> PageEvent:
        """Trigger an automated page to the appropriate tier responder."""
        if tier == 1:
            target_resp = self.active_shift.primary_responder
        elif tier == 2:
            target_resp = self.active_shift.secondary_responder
        else:
            target_resp = self.active_shift.escalation_lead

        page = PageEvent(
            page_id=f"page-{uuid.uuid4().hex[:8]}",
            incident_id=incident_id,
            tier_level=tier,
            responder=target_resp,
            status=PageStatus.PENDING,
            dispatched_at=utc_now(),
            notes=notes or f"Page dispatched to {target_resp.role.value}: {target_resp.name}",
        )
        self.pages[page.page_id] = page
        return page

    def acknowledge_page(self, page_id: str, responder_id: Optional[str] = None) -> Optional[PageEvent]:
        """Mark page as acknowledged by responder."""
        page = self.pages.get(page_id)
        if not page:
            return None
        page.status = PageStatus.ACKNOWLEDGED
        page.acknowledged_at = utc_now()
        page.notes = f"Acknowledged by {page.responder.name} at {page.acknowledged_at}"
        return page

    def escalate_page(self, page_id: str, reason: str = "Timeout reached or manual escalation requested") -> Optional[PageEvent]:
        """Escalate an unhandled page to the next tier responder."""
        old_page = self.pages.get(page_id)
        if not old_page:
            return None

        old_page.status = PageStatus.ESCALATED
        next_tier = min(3, old_page.tier_level + 1)
        return self.dispatch_page(
            incident_id=old_page.incident_id,
            tier=next_tier,
            notes=f"Escalated from Tier {old_page.tier_level}: {reason}",
        )

    def get_status(self) -> OnCallRosterStatus:
        """Return full status of on-call roster, active pages, and recent pages."""
        active = [p for p in self.pages.values() if p.status in [PageStatus.PENDING, PageStatus.ESCALATED]]
        recent = [p for p in self.pages.values() if p.status in [PageStatus.ACKNOWLEDGED, PageStatus.RESOLVED]]

        # Compute average MTTA
        mtta_times = []
        for p in recent:
            if p.acknowledged_at and p.dispatched_at:
                try:
                    d = datetime.fromisoformat(p.dispatched_at)
                    a = datetime.fromisoformat(p.acknowledged_at)
                    mtta_times.append(max(5.0, (a - d).total_seconds()))
                except Exception:
                    pass

        avg_mtta = round(sum(mtta_times) / len(mtta_times), 1) if mtta_times else 38.0

        return OnCallRosterStatus(
            current_shift=self.active_shift,
            active_pages=sorted(active, key=lambda x: x.dispatched_at, reverse=True),
            recent_resolved_pages=sorted(recent, key=lambda x: x.dispatched_at, reverse=True),
            mtta_seconds_avg=avg_mtta,
        )

# Global on-call engine singleton
oncall_engine = OnCallEngine()
