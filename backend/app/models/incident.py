from datetime import datetime, timezone
import json
import enum
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base

class IncidentStatus(str, enum.Enum):
    NEW = "NEW"
    INVESTIGATING = "INVESTIGATING"
    DIAGNOSED = "DIAGNOSED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    REMEDIATING = "REMEDIATING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"

class IncidentSeverity(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    fingerprint: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(256))
    service: Mapped[str] = mapped_column(String(128), index=True)
    namespace: Mapped[str] = mapped_column(String(128), default="default", index=True)
    alert_name: Mapped[str] = mapped_column(String(128), index=True)
    severity: Mapped[str] = mapped_column(String(32), default=IncidentSeverity.WARNING.value, index=True)
    status: Mapped[str] = mapped_column(String(32), default=IncidentStatus.NEW.value, index=True)
    
    summary: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    firing_count: Mapped[int] = mapped_column(Integer, default=1)
    
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    labels_json: Mapped[str] = mapped_column(Text, default="{}")
    annotations_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    diagnosis_json: Mapped[str] = mapped_column(Text, default="{}")
    remediation_json: Mapped[str] = mapped_column(Text, default="{}")

    events: Mapped[List["IncidentEvent"]] = relationship(
        "IncidentEvent", back_populates="incident", cascade="all, delete-orphan", order_by="IncidentEvent.created_at"
    )

    @property
    def labels(self) -> Dict[str, Any]:
        return json.loads(self.labels_json) if self.labels_json else {}

    @labels.setter
    def labels(self, val: Dict[str, Any]):
        self.labels_json = json.dumps(val)

    @property
    def annotations(self) -> Dict[str, Any]:
        return json.loads(self.annotations_json) if self.annotations_json else {}

    @annotations.setter
    def annotations(self, val: Dict[str, Any]):
        self.annotations_json = json.dumps(val)

    @property
    def evidence(self) -> Dict[str, Any]:
        return json.loads(self.evidence_json) if self.evidence_json else {}

    @evidence.setter
    def evidence(self, val: Dict[str, Any]):
        self.evidence_json = json.dumps(val)

    @property
    def diagnosis(self) -> Dict[str, Any]:
        return json.loads(self.diagnosis_json) if self.diagnosis_json else {}

    @diagnosis.setter
    def diagnosis(self, val: Dict[str, Any]):
        self.diagnosis_json = json.dumps(val)

    @property
    def remediation(self) -> Dict[str, Any]:
        return json.loads(self.remediation_json) if self.remediation_json else {}

    @remediation.setter
    def remediation(self, val: Dict[str, Any]):
        self.remediation_json = json.dumps(val)

class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(64), ForeignKey("incidents.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="events")

    @property
    def payload(self) -> Dict[str, Any]:
        return json.loads(self.payload_json) if self.payload_json else {}

    @payload.setter
    def payload(self, val: Dict[str, Any]):
        self.payload_json = json.dumps(val)
