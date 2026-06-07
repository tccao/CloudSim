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
        GUARD["Protected-route dependencies<br/>load current user from DB<br/>role and ownership checks"]
        FACADE["aws_service.py facade"]
        MOCK["PostgreSQL-backed mock adapter<br/>synthetic metrics + cost estimates"]
        LIVE["Lazy boto3 live adapter"]

        EDGE --> AUTH
        EDGE --> ADMIN
        EDGE --> EC2API
        AUTH -->|"/me only"| GUARD
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
    EC2API -->|"6. list endpoint syncs provider metadata"| INSTANCES
    EC2API -->|"7. metrics history endpoint persists datapoints"| METRICS
    MOCK -->|"8. virtual instance state and ownership"| INSTANCES
    LIVE -->|"9a. shared backend credentials when role access is off"| EC2
    LIVE -->|"9b. role-mapped temporary clients when role access is on"| STS
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
    alt Register
        UI->>API: POST /api/auth/register
        API->>DB: Create User-role account with bcrypt hash
        API-->>UI: Created user record
        UI->>API: POST /api/auth/login
    else Sign in
        UI->>API: POST /api/auth/login
    end
    API->>DB: Verify bcrypt hash and active status
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
    opt User lifecycle action or metrics request
        Route->>Facade: Resolve target instance for ownership check
        Facade->>Provider: Dispatch by CLOUDSIM_AWS_BACKEND
        Provider-->>Facade: Target instance and CreatedBy tag
        Facade-->>Route: Normalized target instance
        Route->>Route: Verify CreatedBy matches current user
    end
    Route->>Facade: Fetch or perform operation with role and user id
    Facade->>Provider: Dispatch by CLOUDSIM_AWS_BACKEND
    Provider-->>Facade: Instance, metric, or cost data
    Facade-->>Route: Normalized response
    alt Instance list
        Route->>DB: Sync returned instance summaries
        Route->>Route: Filter response by CreatedBy for User
    else Instance detail
        Route->>Route: Verify CreatedBy for User
    else Metrics history
        Route->>DB: Persist returned metric datapoints
    else Cost request
        Note over Facade,Provider: Provider scopes regular-user costs
    end
    Route-->>UI: JSON response
```

The exact ordering is endpoint-specific. Lifecycle actions and metrics requests
first resolve the target instance to check ownership, then perform the requested
operation. The list endpoint fetches provider data, syncs the returned summaries,
then filters the response for a `User`. Instance details are fetched and then
checked. Cost scoping is applied inside the selected provider.

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
| Live instances | AWS EC2 | List endpoint syncs summary/cache; ownership remains in AWS `CreatedBy` tags |
| CPU/network/disk metrics | Mock generator or CloudWatch | Metrics history is persisted before its response; current/latest metrics are not persisted |
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

## Brief Presentation Walkthrough

Use this as a two-to-three-minute talk track:

1. **Deployment boundary:** Vercel serves a static React/Vite SPA. The browser
   calls the Render-hosted FastAPI API directly through `VITE_API_URL`; Vercel
   is not an API proxy.
2. **Identity boundary:** Login returns a JWT containing only the user's email.
   Every protected request reloads the user from PostgreSQL, making role,
   active-status, and deletion changes effective immediately.
3. **Authorization boundary:** FastAPI is the primary policy-enforcement layer.
   Admin and DevOps roles can operate across instances; regular users are
   restricted by the `CreatedBy=<user_id>` ownership contract.
4. **Provider boundary:** EC2 routes call one `aws_service.py` facade. A feature
   flag selects either the PostgreSQL-backed mock adapter or lazy boto3 clients
   without changing the frontend or route contract.
5. **Data ownership:** PostgreSQL is authoritative for users and mock instances.
   In live mode, AWS remains authoritative for resources and costs; PostgreSQL
   only receives instance summaries from list requests and metric-history
   snapshots.
6. **Optional defense in depth:** In live mode, role-based access can use STS
   AssumeRole. Effective permission is then the intersection of FastAPI policy
   and AWS IAM policy.
7. **Operational validation:** GitHub Actions tests the backend, lints/tests/builds
   the frontend, validates Compose, and builds both Docker images before
   deployment.

Be ready to call out these deliberate trade-offs:

- JWTs in `localStorage` keep the SPA simple but increase exposure to XSS
  compared with `httpOnly` cookies.
- `Base.metadata.create_all()` is sufficient for the current deployment but is
  not a versioned migration strategy.
- The live-instance PostgreSQL copy is a list-triggered cache, not a continuously
  synchronized source of truth.
- Mock and live providers share a route contract, but provider-specific
  integration and authorization behavior still require separate tests.

Document version: 3.1
Last updated: June 7, 2026
