# CloudSim Production Architecture

This is the canonical architecture diagram for the final CloudSim production
app. It documents the Vercel/Render deployment, the browser-to-API boundary,
PostgreSQL responsibilities, backend-enforced RBAC, and the switchable mock/live
AWS service layer.

## System Diagram

```mermaid
flowchart LR
    PERSON["CloudSim user"]

    subgraph DELIVERY["Source and validation"]
        REPO["GitHub repository"]
        CI["GitHub Actions<br/>backend tests<br/>frontend lint/test/build<br/>Compose validation<br/>Docker image builds"]
        REPO --> CI
    end

    subgraph VERCEL["Vercel - static frontend"]
        SPA["React 18 + TypeScript + Vite"]
        SHELL["Login / Dashboard / Details<br/>Monitoring / IAM / Launch Wizard"]
        AUTHCTX["UserContext<br/>localStorage JWT"]
        AXIOS["Shared Axios client<br/>VITE_API_URL + bearer interceptor"]
        SPA --> SHELL
        SHELL --> AXIOS
        AUTHCTX --> AXIOS
    end

    subgraph RENDER["Render - Docker web service"]
        EDGE["FastAPI app<br/>CORS + security headers + /health"]
        AUTH["/api/auth<br/>register / login / me"]
        ADMIN["/api/admin/users<br/>Admin-only CRUD"]
        EC2API["/api/ec2<br/>instances / launch options<br/>metrics / costs"]
        GUARD["Authentication + RBAC<br/>load current user from DB<br/>ownership checks"]
        FACADE["aws_service.py facade"]
        MOCK["PostgreSQL-backed mock adapter"]
        LIVE["Lazy boto3 live adapter"]

        EDGE --> AUTH
        EDGE --> ADMIN
        EDGE --> EC2API
        AUTH --> GUARD
        ADMIN --> GUARD
        EC2API --> GUARD
        EC2API --> FACADE
        FACADE -->|"CLOUDSIM_AWS_BACKEND=mock"| MOCK
        FACADE -->|"CLOUDSIM_AWS_BACKEND=live"| LIVE
    end

    subgraph POSTGRES["Render PostgreSQL"]
        USERS[("users<br/>credentials / roles / status")]
        INSTANCES[("instances<br/>mock state / synced metadata / ownership")]
        METRICS[("metrics<br/>persisted metric datapoints")]
    end

    subgraph AWS["AWS - live mode only"]
        STS["STS AssumeRole<br/>optional"]
        EC2["EC2<br/>instances / AMIs / network / volumes"]
        CW["CloudWatch<br/>CPU / network / disk metrics"]
        CE["Cost Explorer<br/>daily / monthly costs"]
    end

    PERSON -->|"1. load app"| SPA
    AXIOS -->|"2. direct HTTPS requests"| EDGE
    AUTH -->|"3. credentials and current user"| USERS
    GUARD -->|"4. reload role and active status"| USERS
    ADMIN -->|"5. user management"| USERS
    EC2API -->|"6. sync live metadata"| INSTANCES
    EC2API -->|"7. persist returned metrics"| METRICS
    MOCK -->|"8. virtual instance state and ownership"| INSTANCES
    MOCK -->|"9. generate metrics and cost estimates"| EC2API
    LIVE -->|"10a. shared backend credentials when role access is off"| EC2
    LIVE -->|"10b. role-mapped temporary clients when role access is on"| STS
    STS --> EC2
    STS --> CW
    STS --> CE
    LIVE --> EC2
    LIVE --> CW
    LIVE --> CE
```

The browser calls the Render API directly using the URL baked into the Vite
bundle as `VITE_API_URL`. Vercel serves static files and does not proxy the API.

## Request Flows

### Authentication

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Vercel React app
    participant API as Render FastAPI
    participant DB as PostgreSQL users

    User->>UI: Register or sign in
    UI->>API: POST /api/auth/register or /api/auth/login
    API->>DB: Create user or verify bcrypt hash
    API-->>UI: JWT bearer token
    UI->>UI: Store token in localStorage
    UI->>API: GET /api/auth/me with bearer token
    API->>DB: Decode email subject, reload user/role/status
    DB-->>API: Current user record
    API-->>UI: id, email, role, active status
```

The JWT contains the user's email in `sub`; it does not contain the authoritative
role. Every protected route reloads the current user from PostgreSQL, so role,
active-status, and deletion changes take effect without waiting for a new token.

### Instance And Monitoring Request

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React UI
    participant Route as FastAPI EC2 route
    participant DB as PostgreSQL
    participant Facade as AWS service facade
    participant Provider as Mock adapter or AWS

    User->>UI: List, launch, act, or open monitoring
    UI->>Route: Bearer-authenticated /api/ec2 request
    Route->>DB: Load current user
    Route->>Facade: Operation with role and user id
    Facade->>Provider: Dispatch by CLOUDSIM_AWS_BACKEND
    Provider-->>Facade: Instance, metric, or cost data
    Facade-->>Route: Normalized response
    Route->>Route: Enforce ownership for User role
    Route->>DB: Sync instance metadata or persist metrics
    Route-->>UI: JSON response
```

## Component Responsibilities

| Component | Responsibility |
| :--- | :--- |
| Vercel static frontend | Serves the React SPA; renders auth, dashboard, launch, details, monitoring, and IAM experiences |
| `UserContext` and Axios client | Stores the JWT, validates it through `/api/auth/me`, attaches bearer headers, and clears invalid sessions on `401` |
| Render FastAPI service | Owns API routing, request validation, CORS, security headers, health checks, startup table creation, and admin bootstrap |
| Auth and admin routes | Register/login/current-user flow and Admin-only user management |
| EC2 routes | Backend RBAC, ownership checks, normalized instance operations, metadata sync, metric persistence, and cost endpoints |
| AWS service facade | Selects mock or live behavior without changing the route contract |
| Mock adapter | Uses PostgreSQL for virtual instances and generates deterministic demo metrics and estimated costs; never calls AWS |
| Live boto3 adapter | Calls EC2, CloudWatch, and optional Cost Explorer; optionally obtains role-mapped clients through STS |
| PostgreSQL | Stores users, mock instance state/ownership, synced live instance metadata, and metric snapshots |
| GitHub Actions | Validates backend, frontend, Compose, and Docker builds; it does not define runtime request flow |

## Data Ownership

| Data | Production Source Of Truth | PostgreSQL Use |
| :--- | :--- | :--- |
| Users, roles, active status | PostgreSQL | Authoritative |
| Mock instances | PostgreSQL | Authoritative |
| Live instances | AWS EC2 | Synced summary/cache; ownership remains in AWS `CreatedBy` tags |
| CPU/network/disk metrics | Mock generator or CloudWatch | Persisted after the metrics history endpoint returns data |
| Mock costs | Calculated from visible mock instances | Instances provide calculation input |
| Live costs | Cost Explorer | Returned to the UI; not persisted |
| Dashboard alarms/zones/resource summaries | Static frontend presentation data | Not persisted |
| Memory, system logs, audit logs, advanced settings | Static/local frontend presentation data | Not persisted |

## Application Authorization

- `Admin`: all instances and admin user-management API.
- `DevOps Engineer`: all instance, metric, and cost operations; no admin API.
- `User`: can launch instances and access only owned instances, metrics, and
  scoped costs.
- Live instances carry `CreatedBy=<user_id>` and `ManagedBy=CloudSim` tags.
- Mock ownership is stored as `instances.created_by_user_id` and exposed through
  the same `CreatedBy` tag contract.
- In live mode, optional IAM role policies add a second authorization boundary.
  Effective access is the intersection of FastAPI checks and AWS IAM policy.

## Deployment And Feature Flags

| Service | Production Target | Required Configuration |
| :--- | :--- | :--- |
| Frontend | Vercel static site | Root `frontend`, build `npm run build`, output `dist`, `VITE_API_URL` |
| Backend | Render Docker web service | Root `backend`, `backend/Dockerfile`, `/health`, Render `PORT` |
| Database | Render PostgreSQL | Internal `DATABASE_URL` on the backend |

| Flag | Effect |
| :--- | :--- |
| `CLOUDSIM_AWS_BACKEND=mock` | PostgreSQL-backed demo resources; no AWS calls |
| `CLOUDSIM_AWS_BACKEND=live` | Real AWS service calls |
| `ENABLE_ROLE_BASED_ACCESS=true` | Live boto3 clients use role-mapped STS sessions |
| `ENABLE_ROLE_BASED_ACCESS=false` | Live boto3 clients use the backend credential chain |
| `ENABLE_COST_EXPLORER=true` | Enables live Cost Explorer endpoints |
| `CLOUDSIM_BOOTSTRAP_ADMIN_ENABLED=true` | Creates or restores the configured backend-only admin at startup |

Document version: 3.0
Last updated: June 6, 2026
