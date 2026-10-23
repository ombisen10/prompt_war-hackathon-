const API_BASE = import.meta.env.VITE_API_URL || '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}

export async function analyzeIncident(description) {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.error || 'Analysis failed');
  }
  return res.json();
}

export async function fetchIncidents() {
  const res = await fetch(`${API_BASE}/api/incidents`);
  return res.json();
}

export async function fetchIncident(id) {
  const res = await fetch(`${API_BASE}/api/incidents/${id}`);
  return res.json();
}

export async function fetchLogs() {
  const res = await fetch(`${API_BASE}/api/logs`);
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/api/metrics`);
  return res.json();
}

export async function fetchApprovals() {
  const res = await fetch(`${API_BASE}/api/approvals`);
  return res.json();
}

export async function submitApprovalDecision(approvalId, decision, decidedBy = 'demo_operator') {
  const res = await fetch(`${API_BASE}/api/approvals/${approvalId}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, decided_by: decidedBy }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Decision failed');
  }
  return res.json();
}
