"""GuardianAI — FastAPI Backend."""
from __future__ import annotations
import os
import sys
import time
from contextlib import asynccontextmanager

# Ensure backend directory is in sys.path regardless of how or from where script is launched
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from app.models import (
    AnalyzeRequest, AnalyzeResponse, IncidentRecord, AuditEvent,
    ApprovalDecision, MetricsResponse, MAX_INPUT_LENGTH,
)
from app.storage import Storage
from app.ai_service import analyze_incident
from app.tools import execute_tool, validate_tool

# Load .env
load_dotenv()

storage = Storage(os.environ.get("DATABASE_PATH", "guardian.db"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title="GuardianAI",
    description="Autonomous Incident Detection & Response Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend origins (both localhost and 127.0.0.1)
cors_origins = [
    os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"),
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    mock_mode = os.environ.get("MOCK_AI", "false").lower() in ("true", "1", "yes")
    mode = "mock" if (mock_mode or not api_key) else "gemini"
    return {"status": "healthy", "ai_mode": mode, "version": "1.0.0"}


# ── Analyze Incident ──────────────────────────────────────────────
@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    start = time.time()

    # AI analysis
    analysis, ai_mode = await analyze_incident(req.description)

    elapsed_ms = round((time.time() - start) * 1000, 1)

    # Create incident record
    incident = IncidentRecord(
        description=req.description,
        incident_type=analysis.incident_type,
        severity=analysis.severity,
        confidence=analysis.confidence,
        location=analysis.location,
        summary=analysis.summary,
        risks=analysis.risks,
        reasoning=analysis.reasoning,
        safety_instructions=analysis.safety_instructions,
        ai_mode=ai_mode,
        processing_time_ms=elapsed_ms,
    )
    storage.save_incident(incident)

    # Execute recommended actions
    action_results = []
    for rec_action in analysis.recommended_actions:
        tool_name = rec_action.tool
        args = {"reason": rec_action.reason, "description": analysis.summary,
                "message": f"[{analysis.severity.value}] {analysis.summary}",
                "priority": rec_action.priority}
        result = execute_tool(tool_name, args, incident.id, storage)
        action_results.append(result)

    # Update incident with action results
    incident.actions = action_results
    incident.status = "PROCESSED"
    storage.update_incident(incident)

    return AnalyzeResponse(
        incident=incident,
        analysis=analysis,
        actions=action_results,
        ai_mode=ai_mode,
    )


# ── Incidents CRUD ────────────────────────────────────────────────
@app.get("/api/incidents")
async def list_incidents():
    return storage.list_incidents()


@app.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str):
    incident = storage.get_incident(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


# ── Execute actions for an existing incident ──────────────────────
@app.post("/api/incidents/{incident_id}/execute")
async def execute_actions(incident_id: str, request: Request):
    incident = storage.get_incident(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    body = await request.json()
    tool_name = body.get("tool", "")
    args = body.get("args", {})

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
        raise HTTPException(403, msg)

    result = execute_tool(tool_name, args, incident_id, storage)
    return result


# ── Audit Logs ────────────────────────────────────────────────────
@app.get("/api/logs")
async def list_logs():
    return storage.list_audits()


# ── Metrics ───────────────────────────────────────────────────────
@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics():
    return storage.get_metrics()


# ── Approvals ─────────────────────────────────────────────────────
@app.get("/api/approvals")
async def list_approvals():
    return storage.list_approvals()


@app.post("/api/approvals/{approval_id}/decision")
async def decide_approval(approval_id: str, decision: ApprovalDecision):
    approval = storage.get_approval(approval_id)
    if not approval:
        raise HTTPException(404, "Approval request not found")
    if approval.status != "PENDING_APPROVAL":
        raise HTTPException(400, f"Approval already decided: {approval.status}")

    from datetime import datetime, timezone
    approval.status = decision.decision
    approval.decided_by = decision.decided_by
    approval.decided_at = datetime.now(timezone.utc).isoformat()
    storage.save_approval(approval)

    # Audit
    audit = AuditEvent(
        incident_id=approval.incident_id,
        actor=decision.decided_by,
        action=f"APPROVAL_{decision.decision}",
        tool=approval.tool,
        result=f"Approval {approval_id} {decision.decision.lower()} by {decision.decided_by}",
        status=decision.decision,
    )
    storage.save_audit(audit)

    return {"approval_id": approval_id, "status": decision.decision, "decided_by": decision.decided_by}


# ── Error handlers ────────────────────────────────────────────────
@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    return {"error": "Validation error", "detail": "Invalid input. Check your request."}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)

