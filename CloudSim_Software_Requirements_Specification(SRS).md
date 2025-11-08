# CloudSim — Software Requirements Specification (SRS)

> Version: 0.9 (Draft)  
> Owner: Tinh  
> Project Type: Systems/Infrastructure Simulator (Free-tier stack)

---

## 1. Introduction

### 1.1 Purpose
This SRS defines the requirements for **CloudSim**, a web-based cloud infrastructure simulator that models compute, storage, networking, monitoring, and orchestration. 

### 1.2 Scope
CloudSim simulates a minimal AWS‑like experience:
- Provision, start/stop, scale, and terminate **instances**.
- Create/attach **storage volumes**.
- Visualize **network topology** and adjust bandwidth/latency.
- **Monitor** CPU/RAM/IO metrics and receive **alerts**.
- Provide **REST + WebSocket** APIs for developer automation.

### 1.3 Definitions, Acronyms, Abbreviations
- **Instance**: Simulated compute node.
- **Volume**: Simulated block storage attached to an instance.
- **Topology**: Graph of instances and their connections.
- **Metric**: Time series datapoint for CPU, RAM, Network I/O.
- **MVP**: Minimum Viable Product.

### 1.4 References
- User Stories, Epics 1–6 (Markdown docs).  
- User Flows (Provisioning, Scaling, Termination, Storage/Network, Monitoring).  
- OpenAI‑style API doc pattern for response shapes.

---

## 2. Overall Description

### 2.1 Product Perspective
CloudSim is a standalone web app with:
- **Frontend**: React + Tailwind.
- **Backend**: FastAPI + WebSockets.
- **DB**: SQLite (dev) / PostgreSQL (prod).
- **Async**: Optional Celery + Redis for advanced scheduling.
- **Hosting**: Vercel/Render/Railway free tiers.
- **CI/CD**: GitHub Actions.

### 2.2 User Classes & Characteristics
- **CloudSim User**: Creates and manages instances; views metrics.
- **DevOps Engineer**: Tunes parameters; analyzes performance; uses APIs.
- **Admin**: Manages users and global limits; audits activity.

### 2.3 Operating Environment
- Modern desktop browser (Chromium/Firefox).
- Backend on Linux container; DB managed instance or container.
- Free‑tier resource budgets.

### 2.4 Design & Implementation Constraints
- No paid services; free tiers only.
- Real‑time data is **simulated**, not sourced from real cloud.
- Single‑developer velocity; 200‑hour cap for MVP.

### 2.5 Assumptions & Dependencies
- Reliable free hosting available.
- Basic email/password or token auth sufficient.
- Non‑production data; minimal privacy exposure.

---

## 3. System Features (Functional Requirements)

### 3.1 Instance Management (Epic 1)
- FR‑1: Create instance with name, CPU, RAM, region.
- FR‑2: Start/Stop instance; persist state.
- FR‑3: Terminate instance; cascade detach volumes.
- FR‑4: View instance list/detail with latest metrics.

### 3.2 Storage & Networking (Epic 2)
- FR‑5: Create volume and attach/detach to/from instance.
- FR‑6: Render network topology (nodes/edges).
- FR‑7: Update bandwidth/latency per connection.

### 3.3 Monitoring & Alerts (Epic 3)
- FR‑8: Stream instance metrics at 5‑second cadence.
- FR‑9: Set threshold alerts; push events on breach.
- FR‑10: Export metrics as CSV.

### 3.4 System Management (Epic 4)
- FR‑11: CRUD users, roles (user/devops/admin).
- FR‑12: Configure global resource limits.
- FR‑13: Adjust orchestration parameters.

### 3.5 Developer APIs (Epic 5)
- FR‑14: Public REST endpoints for instances, metrics, storage, network.
- FR‑15: Token‑based auth for API access.
- FR‑16: Rate‑limit API requests.

---

## 4. External Interface Requirements

### 4.1 User Interface (UI)
- **Dashboard**: Instance cards, create button, quick metrics.
- **Instance Detail**: Controls (start/stop/terminate/scale), charts, volume list.
- **Network View**: Topology graph with editable edges.
- **Monitoring**: Real‑time charts + “Export CSV”.
- **Admin**: Users, resource limits, orchestration settings.

### 4.2 REST API (OpenAI‑style schema excerpts)
Base URL: `/api`

#### 4.2.1 Instances
**Create Instance**  
`POST /instances/create`
```json
{ "name": "tinh-sim-1", "cpu": 2, "memory": 4096, "region": "us-east-1" }
```
Response
```json
{ "id": "i-001", "status": "creating", "created_at": "2025-11-04T15:00:00Z" }
```

**List Instances**  
`GET /instances`
```json
{ "items": [{ "id": "i-001", "name": "tinh-sim-1", "status": "running" }] }
```

**Start/Stop**  
`POST /instances/{id}/start` | `POST /instances/{id}/stop`  
Response: `{ "id": "i-001", "status": "running" }`

**Terminate**  
`DELETE /instances/{id}`  
Response: `{ "id": "i-001", "status": "terminated" }`

**Scale**  
`PUT /instances/{id}/scale`  
Req: `{ "cpu": 4, "memory": 8192 }` → Resp: `{ "status": "updating" }`

#### 4.2.2 Storage
`POST /storage/create`  
Req: `{ "instance_id":"i-001","name":"vol-01","size_gb":50,"type":"SSD" }`  
Resp: `{ "id":"vol-01","status":"attached" }`

#### 4.2.3 Network
`GET /network/topology` → nodes/edges graph  
`PUT /network/update` → update bandwidth/latency

#### 4.2.4 Metrics & Alerts
`GET /metrics/{instance_id}` → latest metrics JSON  
`GET /metrics/export?instance_id={id}&range=1h` → CSV file  
`POST /alerts/set` → save thresholds

### 4.3 WebSockets
- `/ws/metrics/{instance_id}` → JSON push every 5s.
- `/ws/alerts` → alert events.

### 4.4 Authentication
- JWT Bearer token.  
- Header: `Authorization: Bearer <token>`.

---

## 5. Data Requirements

### 5.1 Entities
- **User**(id, email, role, created_at)
- **Instance**(id, name, cpu, memory, region, status, created_at)
- **Volume**(id, instance_id?, size_gb, type, status)
- **Connection**(id, from_instance, to_instance, bandwidth, latency)
- **Metric**(id, instance_id, cpu, memory, net_in, net_out, ts)
- **AlertRule**(id, instance_id, cpu_threshold?, mem_threshold?, created_at)

### 5.2 Relationships
- User 1..* Instance (ownership).  
- Instance 0..* Volume.  
- Instance ↔ Instance (Connection edges).  
- Instance 1..* Metric.  
- Instance 0..* AlertRule.

### 5.3 Data Retention
- Metrics retained 7 days (MVP).  
- Export path for CSV on demand.

---

## 6. Non‑Functional Requirements (NFR) - (Stretch goal)

### 6.1 Performance
- P95 API latency < 500 ms for CRUD.  
- WebSocket updates every 5 s without UI freeze.  
- Frontend first paint < 2.5 s on free-tier hosting.

### 6.2 Reliability & Availability
- Auto‑restart on host crashes (provider managed).  
- Graceful degradation when WebSockets unavailable (polling fallback).

### 6.3 Security
- JWT auth; password hashing (bcrypt).  
- Role‑based access: admin/devops/user.  
- Rate‑limit: 60 req/min/IP for public endpoints.  
- CORS configured for frontend origin only.

### 6.4 Maintainability
- Modular FastAPI routers; typed Pydantic schemas.  
- Linting (ruff/black) + pre‑commit.  
- 70%+ unit test coverage at MVP.

### 6.5 Portability
- Dockerized services; single `docker-compose up` local run.

### 6.6 Observability
- Structured logs (JSON) for API and workers.  
- Optional Prometheus exporter for internal metrics.

---

## 7. System Architecture

### 7.1 High‑Level Components
- **Web UI** (React): dashboards, forms, topology, charts.  
- **API** (FastAPI): REST + WebSockets, auth, validation.  
- **Sim Engine**: async jobs for state transitions and metrics synthesis.  
- **DB**: relational storage for state and events.  
- **Broker (optional)**: Redis for Celery tasks.

### 7.2 Deployment Topology (MVP)
- Frontend: Vercel.  
- Backend API: Render (Docker).  
- DB: Railway Postgres (free).  
- Optional worker: Render background worker or single‑dyno process.

---

## 8. Use Cases (Primary)

### UC‑1: Provision Instance
Trigger: User clicks **Create Instance** → POST `/instances/create` → DB save → status `creating` → UI updates.

### UC‑2: Scale Instance
Trigger: PUT `/instances/{id}/scale` → update spec → set status `updating` → confirm in UI.

### UC‑3: Terminate Instance
Trigger: DELETE `/instances/{id}` → detach volumes → delete record → remove from UI.

### UC‑4: Attach Volume
Trigger: POST `/storage/create` with `instance_id` → status `attached` → show in detail page.

### UC‑5: View Topology
Trigger: GET `/network/topology` → graph JSON → render nodes/edges.

### UC‑6: Monitor Metrics
Trigger: GET `/metrics/{id}` + WebSocket `/ws/metrics/{id}` → live charts.

### UC‑7: Configure Alerts
Trigger: POST `/alerts/set` → rule saved → alert event on breach via `/ws/alerts`.

---

## 9. Acceptance Criteria (MVP)

- AC‑1: Instance can be created, appears in list, and transitions to **running** within 10s.  
- AC‑2: Start/Stop toggles state with persisted result.  
- AC‑3: Volume attach shows under instance with correct metadata.  
- AC‑4: Network topology renders at least 5 instances and 6 edges.  
- AC‑5: Metrics chart updates every 5s for a running instance.  
- AC‑6: CSV export downloads with header row and ≥ 12 rows per hour.  
- AC‑7: Admin can add a user and set resource limits.  
- AC‑8: All REST endpoints require valid JWT; unauthorized requests return 401.  
- AC‑9: Docker Compose starts full stack locally with one command.  
- AC‑10: README includes setup, run, and demo steps.

---

## 10. Quality Assurance Plan

- **Unit Tests**: API routes, schema validation, state transitions.  
- **Integration Tests**: UI/API flows (provision, scale, terminate).  
- **Performance Test**: 100 concurrent reads of `/metrics/{id}` within free‑tier limits.  
- **Security Test**: JWT misuse, CORS checks, simple fuzz on payloads.  
- **UAT**: Checklist mapped to Acceptance Criteria.

---

## 11. Project Management

### 11.1 Milestones (first 4 weeks)
- Wk 1: User stories + SRS draft complete.  
- Wk 2: Wireframes + 1 static React page.  
- Wk 3: API reference spec complete.  
- Wk 4: MVP page wired to DB + backend.

### 11.2 Risks (Hypothetical)
- Free‑tier quotas; cold starts affect latency.  
- WebSocket reliability in free hosting.  
- Single‑developer bandwidth.

### 11.3 Mitigations (Hypothetical)
- Cache & batch metrics.  
- Polling fallback.  
- Strict feature prioritization.

---

## 12. Appendices

### A. Sample OpenAPI Schema Snippet
```yaml
paths:
  /instances/create:
    post:
      summary: Create a new instance
      requestBody:
        required: true
      responses:
        '201':
          description: Created
```

### B. Data Dictionary (Key Fields)
- `instances.status`: enum[creating, running, stopped, updating, terminated]  
- `connections.bandwidth`: Mbps integer  
- `metrics.ts`: RFC3339 timestamp

