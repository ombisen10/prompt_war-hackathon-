# GuardianAI — Autonomous Incident Detection & Response Agent

**Hackathon Project: Build Beyond AI — Engineer Secure, Intelligent and Autonomous Applications**

🌐 **Live Production Deployment:** [https://prompt-war-hackathon.vercel.app](https://prompt-war-hackathon.vercel.app)

GuardianAI is an AI-powered incident-response application that analyzes real-world operational incidents, identifies risks, classifies severity, generates response plans, selects approved tools, executes safe actions, verifies execution, and maintains an auditable incident history.

## Core Workflow

```
OBSERVE → ANALYZE → REASON → PLAN → VALIDATE → ACT → VERIFY → AUDIT
```

## Tech Stack

| Layer      | Technology                |
|------------|---------------------------|
| Frontend   | React + Vite              |
| Backend    | Python + FastAPI          |
| AI         | Google Gemini 2.0 Flash   |
| Database   | SQLite                    |
| Validation | Pydantic                  |

## Quick Start (Windows PowerShell)

### 1. Backend Setup

```powershell
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv
.\venv\Scripts\Activate

# Install dependencies
pip install fastapi uvicorn pydantic python-dotenv google-genai pytest httpx

# Configure environment
copy ..\.env.example .env
# Edit .env to add your GEMINI_API_KEY (or leave MOCK_AI=true for demo)

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup (new terminal)

```powershell
cd frontend
npm install
npm run dev
```

### 3. Open the App

Navigate to **http://localhost:5173** in your browser.

## Environment Variables

| Variable         | Description                          | Default            |
|------------------|--------------------------------------|--------------------|
| `GEMINI_API_KEY` | Google Gemini API key                | (empty → mock)     |
| `MOCK_AI`        | Force mock mode (`true`/`false`)     | `true`             |
| `FRONTEND_ORIGIN`| CORS origin for frontend             | `http://localhost:5173` |
| `DATABASE_PATH`  | SQLite database file path            | `guardian.db`      |

## Demo Scenarios

1. **Critical Water Leak** — Multi-hazard incident with electrical isolation approval required
2. **Equipment Failure** — Standard maintenance workflow
3. **Security Test** — Prompt injection defense demonstration

## API Endpoints

| Method | Endpoint                              | Description                |
|--------|---------------------------------------|----------------------------|
| GET    | `/api/health`                         | System health check        |
| POST   | `/api/analyze`                        | Analyze an incident        |
| GET    | `/api/incidents`                      | List all incidents         |
| GET    | `/api/incidents/{id}`                 | Get incident details       |
| POST   | `/api/incidents/{id}/execute`         | Execute a tool action      |
| GET    | `/api/logs`                           | Audit log                  |
| GET    | `/api/metrics`                        | Dashboard metrics          |
| GET    | `/api/approvals`                      | Approval queue             |
| POST   | `/api/approvals/{id}/decision`        | Approve/reject a request   |

## Running Tests

```powershell
cd backend
pytest tests/ -v
```

## Security Features

- **Tool Allowlist**: Only 6 predefined tools are permitted
- **Input Validation**: Max 5000 chars, empty rejection, Pydantic schemas
- **Prompt Injection Defense**: Input treated as untrusted data; backend policy enforcement
- **No Destructive Operations**: DELETE not implemented as a tool
- **API Key Protection**: Server-side only, never sent to frontend
- **Human Approval**: Electrical isolation requires explicit authorization
- **CORS**: Restricted to configured frontend origin
- **Parameterized Queries**: No raw SQL injection

## Architecture

```
Frontend (React/Vite:5173) → API (FastAPI:8000) → AI Service (Gemini/Mock)
                                                 → Policy Engine (Allowlist)
                                                 → Tool Executor (Validated)
                                                 → SQLite (Persistent)
                                                 → Audit Logger
```

## Limitations (MVP)

- No authentication/authorization (local demo only — must not be exposed publicly)
- Notifications are simulated, not sent to real systems
- Physical infrastructure requests create records but do not control equipment
- SQLite is suitable for demos; production would use PostgreSQL
- AI confidence scores are model-reported estimates, not calibrated accuracy
- Approval workflow is a demo control, not production-grade authorization

## Future Enhancements

- **Firebase Authentication** for user identity and role-based access
- **Cloud Run** for containerized, scalable deployment
- **BigQuery** for long-term incident analytics and trend analysis
- **Pub/Sub** for real-time notification delivery
- **Cloud Monitoring** for operational metrics and alerting

## License

Hackathon project — for demonstration purposes.
