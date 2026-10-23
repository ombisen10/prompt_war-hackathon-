"""SQLite storage layer for GuardianAI using raw sqlite3 with JSON serialization."""
from __future__ import annotations
import json
import sqlite3
import threading
from typing import Optional
from app.models import (
    IncidentRecord, MaintenanceTicket, NotificationRecord,
    ApprovalRequest, AuditEvent, MetricsResponse,
)


class Storage:
    def __init__(self, db_path: str = "guardian.db"):
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS maintenance_tickets (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                incident_id TEXT DEFAULT '',
                data TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()

    # ── Incidents ─────────────────────────────────────────────────
    def save_incident(self, incident: IncidentRecord) -> IncidentRecord:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO incidents (id, data) VALUES (?, ?)",
            (incident.id, incident.model_dump_json()),
        )
        conn.commit()
        return incident

    def get_incident(self, incident_id: str) -> Optional[IncidentRecord]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone()
        if row:
            return IncidentRecord.model_validate_json(row["data"])
        return None

    def list_incidents(self) -> list[IncidentRecord]:
        conn = self._get_conn()
        rows = conn.execute("SELECT data FROM incidents ORDER BY rowid DESC").fetchall()
        return [IncidentRecord.model_validate_json(r["data"]) for r in rows]

    def update_incident(self, incident: IncidentRecord) -> IncidentRecord:
        return self.save_incident(incident)

    # ── Maintenance Tickets ───────────────────────────────────────
    def save_ticket(self, ticket: MaintenanceTicket) -> MaintenanceTicket:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO maintenance_tickets (id, incident_id, data) VALUES (?, ?, ?)",
            (ticket.id, ticket.incident_id, ticket.model_dump_json()),
        )
        conn.commit()
        return ticket

    def list_tickets(self) -> list[MaintenanceTicket]:
        conn = self._get_conn()
        rows = conn.execute("SELECT data FROM maintenance_tickets ORDER BY rowid DESC").fetchall()
        return [MaintenanceTicket.model_validate_json(r["data"]) for r in rows]

    # ── Notifications ─────────────────────────────────────────────
    def save_notification(self, notif: NotificationRecord) -> NotificationRecord:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO notifications (id, incident_id, data) VALUES (?, ?, ?)",
            (notif.id, notif.incident_id, notif.model_dump_json()),
        )
        conn.commit()
        return notif

    # ── Approvals ─────────────────────────────────────────────────
    def save_approval(self, approval: ApprovalRequest) -> ApprovalRequest:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO approvals (id, incident_id, status, data) VALUES (?, ?, ?, ?)",
            (approval.id, approval.incident_id, approval.status, approval.model_dump_json()),
        )
        conn.commit()
        return approval

    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM approvals WHERE id = ?", (approval_id,)
        ).fetchone()
        if row:
            return ApprovalRequest.model_validate_json(row["data"])
        return None

    def list_approvals(self) -> list[ApprovalRequest]:
        conn = self._get_conn()
        rows = conn.execute("SELECT data FROM approvals ORDER BY rowid DESC").fetchall()
        return [ApprovalRequest.model_validate_json(r["data"]) for r in rows]

    # ── Audit Events ──────────────────────────────────────────────
    def save_audit(self, event: AuditEvent) -> AuditEvent:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO audit_events (id, incident_id, data, created_at) VALUES (?, ?, ?, ?)",
            (event.id, event.incident_id, event.model_dump_json(), event.created_at),
        )
        conn.commit()
        return event

    def list_audits(self) -> list[AuditEvent]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT data FROM audit_events ORDER BY rowid DESC"
        ).fetchall()
        return [AuditEvent.model_validate_json(r["data"]) for r in rows]

    # ── Metrics ───────────────────────────────────────────────────
    def get_metrics(self) -> MetricsResponse:
        conn = self._get_conn()
        incidents = self.list_incidents()
        total = len(incidents)
        critical = sum(1 for i in incidents if i.severity == "CRITICAL")
        processing_times = [
            i.processing_time_ms for i in incidents if i.processing_time_ms is not None
        ]
        avg_ms = sum(processing_times) / len(processing_times) if processing_times else 0.0

        audits = self.list_audits()
        completed = sum(1 for a in audits if a.status in ("EXECUTED", "VERIFIED"))
        blocked = sum(1 for a in audits if a.status == "BLOCKED")

        approvals = self.list_approvals()
        pending = sum(1 for a in approvals if a.status == "PENDING_APPROVAL")

        return MetricsResponse(
            total_incidents=total,
            critical_incidents=critical,
            actions_completed=completed,
            actions_blocked=blocked,
            actions_pending=pending,
            avg_processing_ms=round(avg_ms, 1),
        )
