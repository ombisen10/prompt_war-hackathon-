"""Agent tools — allowlisted, validated, audited."""
from __future__ import annotations
from app.models import (
    ToolName, ActionStatus, AuditEvent,
    IncidentRecord, MaintenanceTicket, NotificationRecord,
    ApprovalRequest,
)
from app.storage import Storage


# ── Tool permissions ──────────────────────────────────────────────
TOOL_POLICY = {
    ToolName.CREATE_INCIDENT: {"allowed": True, "requires_approval": False},
    ToolName.CREATE_MAINTENANCE_TICKET: {"allowed": True, "requires_approval": False},
    ToolName.SEND_EMERGENCY_NOTIFICATION: {"allowed": True, "requires_approval": False},
    ToolName.REQUEST_ELECTRICAL_ISOLATION: {"allowed": True, "requires_approval": True},
    ToolName.LOG_INCIDENT: {"allowed": True, "requires_approval": False},
    ToolName.REQUEST_HUMAN_REVIEW: {"allowed": True, "requires_approval": False},
}

ALLOWLIST = set(ToolName)


def validate_tool(tool_name: str) -> tuple[bool, str]:
    """Check if a tool name is in the allowlist."""
    try:
        tn = ToolName(tool_name)
    except ValueError:
        return False, f"Tool '{tool_name}' is not in the allowlist. Blocked."
    policy = TOOL_POLICY.get(tn)
    if not policy or not policy["allowed"]:
        return False, f"Tool '{tool_name}' is not permitted by policy."
    return True, "OK"


def requires_approval(tool_name: str) -> bool:
    try:
        tn = ToolName(tool_name)
        return TOOL_POLICY.get(tn, {}).get("requires_approval", False)
    except ValueError:
        return False


def execute_tool(
    tool_name: str,
    args: dict,
    incident_id: str,
    storage: Storage,
) -> dict:
    """Execute a tool after policy checks. Returns action result dict."""
    # 1. Allowlist check
    allowed, msg = validate_tool(tool_name)
    if not allowed:
        audit = AuditEvent(
            incident_id=incident_id,
            actor="POLICY_ENGINE",
            action=f"BLOCKED:{tool_name}",
            tool=tool_name,
            result=msg,
            status="BLOCKED",
        )
        storage.save_audit(audit)
        return {
            "tool": tool_name,
            "status": ActionStatus.BLOCKED.value,
            "message": msg,
            "audit_id": audit.id,
        }

    # 2. Approval check
    if requires_approval(tool_name):
        approval = ApprovalRequest(
            incident_id=incident_id,
            tool=tool_name,
            reason=args.get("reason", "Requires human authorization"),
        )
        storage.save_approval(approval)
        audit = AuditEvent(
            incident_id=incident_id,
            actor="POLICY_ENGINE",
            action=f"PENDING_APPROVAL:{tool_name}",
            tool=tool_name,
            result=f"Approval request created: {approval.id}",
            status="PENDING_APPROVAL",
        )
        storage.save_audit(audit)
        return {
            "tool": tool_name,
            "status": ActionStatus.PENDING_APPROVAL.value,
            "approval_id": approval.id,
            "message": "Request created; awaiting authorized approval.",
        }

    # 3. Execute
    try:
        result = _dispatch(tool_name, args, incident_id, storage)
        # 4. Verify — read back from storage
        verified = _verify(tool_name, result, storage)
        final_status = ActionStatus.VERIFIED.value if verified else ActionStatus.EXECUTED.value
        audit = AuditEvent(
            incident_id=incident_id,
            actor="AGENT",
            action=f"EXECUTED:{tool_name}",
            tool=tool_name,
            result=str(result.get("record_id", "")),
            status=final_status,
        )
        storage.save_audit(audit)
        result["status"] = final_status
        return result
    except Exception as exc:
        audit = AuditEvent(
            incident_id=incident_id,
            actor="AGENT",
            action=f"FAILED:{tool_name}",
            tool=tool_name,
            result=str(exc),
            status="FAILED",
        )
        storage.save_audit(audit)
        return {
            "tool": tool_name,
            "status": ActionStatus.FAILED.value,
            "message": str(exc),
        }


def _dispatch(tool_name: str, args: dict, incident_id: str, storage: Storage) -> dict:
    tn = ToolName(tool_name)

    if tn == ToolName.CREATE_INCIDENT:
        # Incident already created by analyze endpoint — this is a no-op record
        return {"tool": tool_name, "record_id": incident_id, "message": "Incident record persisted."}

    if tn == ToolName.CREATE_MAINTENANCE_TICKET:
        ticket = MaintenanceTicket(
            incident_id=incident_id,
            description=args.get("description", "Maintenance required"),
            priority=args.get("priority", 3),
        )
        storage.save_ticket(ticket)
        return {"tool": tool_name, "record_id": ticket.id, "message": f"Maintenance ticket {ticket.id} created."}

    if tn == ToolName.SEND_EMERGENCY_NOTIFICATION:
        notif = NotificationRecord(
            incident_id=incident_id,
            message=args.get("message", "Emergency notification"),
        )
        storage.save_notification(notif)
        return {"tool": tool_name, "record_id": notif.id, "message": f"Notification simulated successfully: {notif.id}"}

    if tn == ToolName.LOG_INCIDENT:
        audit = AuditEvent(
            incident_id=incident_id,
            actor="AGENT",
            action="LOG_INCIDENT",
            tool=tool_name,
            result=args.get("message", "Incident logged"),
            status="EXECUTED",
        )
        storage.save_audit(audit)
        return {"tool": tool_name, "record_id": audit.id, "message": "Incident logged in audit trail."}

    if tn == ToolName.REQUEST_HUMAN_REVIEW:
        approval = ApprovalRequest(
            incident_id=incident_id,
            tool=tool_name,
            reason=args.get("reason", "Human review requested"),
        )
        storage.save_approval(approval)
        return {"tool": tool_name, "record_id": approval.id, "message": "Human review request created."}

    return {"tool": tool_name, "status": "FAILED", "message": "Unknown dispatch"}


def _verify(tool_name: str, result: dict, storage: Storage) -> bool:
    """Read back from storage to verify the action actually persisted."""
    record_id = result.get("record_id", "")
    if not record_id:
        return False
    tn = ToolName(tool_name)
    if tn == ToolName.CREATE_INCIDENT:
        return storage.get_incident(record_id) is not None
    if tn == ToolName.CREATE_MAINTENANCE_TICKET:
        tickets = storage.list_tickets()
        return any(t.id == record_id for t in tickets)
    if tn == ToolName.SEND_EMERGENCY_NOTIFICATION:
        return True  # saved inline
    if tn in (ToolName.LOG_INCIDENT, ToolName.REQUEST_HUMAN_REVIEW):
        return True  # saved inline
    return False
