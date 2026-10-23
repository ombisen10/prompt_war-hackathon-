"""Pydantic models for GuardianAI."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import uuid


# ── Enums ─────────────────────────────────────────────────────────
class IncidentType(str, Enum):
    FIRE = "FIRE"
    WATER_LEAK = "WATER_LEAK"
    ELECTRICAL = "ELECTRICAL"
    MEDICAL = "MEDICAL"
    SECURITY = "SECURITY"
    EQUIPMENT_FAILURE = "EQUIPMENT_FAILURE"
    OTHER = "OTHER"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    BLOCKED = "BLOCKED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class ToolName(str, Enum):
    CREATE_INCIDENT = "CREATE_INCIDENT"
    CREATE_MAINTENANCE_TICKET = "CREATE_MAINTENANCE_TICKET"
    SEND_EMERGENCY_NOTIFICATION = "SEND_EMERGENCY_NOTIFICATION"
    REQUEST_ELECTRICAL_ISOLATION = "REQUEST_ELECTRICAL_ISOLATION"
    LOG_INCIDENT = "LOG_INCIDENT"
    REQUEST_HUMAN_REVIEW = "REQUEST_HUMAN_REVIEW"


# ── Request Models ────────────────────────────────────────────────
MAX_INPUT_LENGTH = 5000


class AnalyzeRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=MAX_INPUT_LENGTH)

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description cannot be empty or whitespace only")
        return v


# ── AI Analysis Response ─────────────────────────────────────────
class RecommendedAction(BaseModel):
    tool: str
    reason: str
    priority: int = Field(ge=1, le=5)
    requires_approval: bool = False


class AIAnalysis(BaseModel):
    incident_type: IncidentType
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    location: str = ""
    summary: str
    risks: list[str] = []
    reasoning: str = ""
    recommended_actions: list[RecommendedAction] = []
    requires_human_approval: bool = False
    safety_instructions: list[str] = []


# ── Database Record Models ────────────────────────────────────────
class IncidentRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"INC-{uuid.uuid4().hex[:8].upper()}")
    description: str
    incident_type: Optional[IncidentType] = None
    severity: Optional[Severity] = None
    confidence: Optional[float] = None
    location: str = ""
    summary: str = ""
    risks: list[str] = []
    reasoning: str = ""
    safety_instructions: list[str] = []
    status: str = "OPEN"
    ai_mode: str = "unknown"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    actions: list[dict] = []
    processing_time_ms: Optional[float] = None


class MaintenanceTicket(BaseModel):
    id: str = Field(default_factory=lambda: f"MT-{uuid.uuid4().hex[:8].upper()}")
    incident_id: str
    description: str
    priority: int = 3
    status: str = "OPEN"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class NotificationRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"NOTIF-{uuid.uuid4().hex[:8].upper()}")
    incident_id: str
    message: str
    simulated: bool = True
    status: str = "SENT_SIMULATED"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ApprovalRequest(BaseModel):
    id: str = Field(default_factory=lambda: f"APR-{uuid.uuid4().hex[:8].upper()}")
    incident_id: str
    tool: str
    reason: str
    status: str = "PENDING_APPROVAL"
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"AUD-{uuid.uuid4().hex[:8].upper()}")
    incident_id: str = ""
    actor: str = "SYSTEM"
    action: str
    tool: str = ""
    result: str = ""
    status: str = "OK"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ApprovalDecision(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    decided_by: str = Field(default="demo_operator")


class AnalyzeResponse(BaseModel):
    incident: IncidentRecord
    analysis: AIAnalysis
    actions: list[dict]
    ai_mode: str


class MetricsResponse(BaseModel):
    total_incidents: int = 0
    critical_incidents: int = 0
    actions_completed: int = 0
    actions_pending: int = 0
    actions_blocked: int = 0
    avg_processing_ms: float = 0.0
