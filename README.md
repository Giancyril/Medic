# Incident Response Agent

An autonomous SRE & Incident Response Agent that watches your Kubernetes clusters, investigates system failures upon alert ingestion, reasons over telemetry (Prometheus metrics, cluster events, container logs) using LangGraph, diagnoses probable root causes with calibrated confidence, and safely executes remediation or escalates with human-in-the-loop safety gates.

Following the **Alert -> Investigate -> Diagnose -> Act** loop.

---

## Architecture Overview

```
+--------------------+     +-----------------------+     +--------------------+
|  ALERT             |---->|  INVESTIGATE          |---->|  DIAGNOSE          |
|  (Prometheus       |     |  (LangGraph tool      |     |  (LLM synthesizes  |
|  Alertmanager      |     |  nodes: PromQL golden |     |  evidence into root|
|  webhook)          |     |  signals, k8s, logs)  |     |  cause + confidence|
+--------------------+     +-----------------------+     +---------+----------+
                                                                   |
+--------------------+     +-----------------------+               |
|  Human Escalation  |<----|  ACT / REMEDIATE      |<--------------+
|  (Slack/PD with    |     |  (LangGraph interrupt |
|  investigation)    |     |  safety gate for T3)  |
+--------------------+     +-----------------------+
```

### Core Technology Stack

- **Agent Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph) (explicit stateful graph, state checkpointing, human-approval interrupts)
- **Backend API**: FastAPI (async Webhook receiver, Server-Sent Events telemetry stream, management API)
- **Metrics Source**: Prometheus (PromQL queries for request rate, error rate, latency, saturation)
- **Target Environment**: Kubernetes (Pod statuses, events, restart counters, container logs, declarative remediation)
- **Frontend Dashboard**: React + Vite + TypeScript (Grafana-style golden signal charts + PagerDuty-style high-contrast active incident triage)

---

## Monorepo Layout

```
incident-response-agent/
├── backend/
│   ├── app/              # FastAPI: webhook receiver, incident API, SQLite/PostgreSQL
│   ├── agent/            # LangGraph StateGraph: Alert, Investigate, Diagnose, Act nodes
│   ├── tools/            # PromQL query client, k8s inspector, log streamer, cluster simulator
│   └── remediation/      # Action catalog, risk tiers, LangGraph approval safety gate
├── frontend/             # React + Vite + TypeScript: Grafana/PagerDuty dark ops UI
├── infra/
│   ├── helm/             # Deployment manifests for the agent with scoped RBAC
│   └── local-dev/        # Prometheus and local dev configurations
├── scripts/              # Commit helper scripts (commit-stage.ps1, commit-stage.sh)
└── tests/                # Automated pytest suite (alerts, tools, diagnosis, safety gates)
```

---

## Quickstart

### 1. Backend Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload --port 8000
```

- API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Alertmanager Webhook: `http://localhost:8000/api/v1/alerts/webhook`

### 2. Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

- Web Dashboard: `http://localhost:5173`

### 3. Run Automated Tests

```powershell
pytest -v
```

---

## Phased Implementation Roadmap

- [x] **Phase 0 — Project Scaffolding**: Monorepo layout, FastAPI backend, Vite frontend, test harness.
- [ ] **Phase 1 — Alert Ingestion**: Webhook parser, fingerprinting, deduplication, incident lifecycle.
- [ ] **Phase 2 — Investigation Tools**: PromQL golden signals, Kubernetes inspector, container log tailer.
- [ ] **Phase 3 — Diagnosis**: LLM reasoning engine, root cause synthesis, calibrated confidence scoring.
- [ ] **Phase 4 — Remediation & Safety Gate**: Action catalog, risk tiers, LangGraph interrupt gate.
- [ ] **Phase 5 — Escalation**: Slack / PagerDuty deep-link notifications with investigation trail.
- [ ] **Phase 6 — Frontend UI**: Grafana golden signals, 4-stage pipeline cards, approval modal.
- [ ] **Phase 7 — Testing & Chaos**: Chaos scenario harness, safety gate bypass prevention tests.
- [ ] **Phase 8 — Deployment & CI/CD**: Dockerfiles, Helm charts, GitHub Actions workflow.
