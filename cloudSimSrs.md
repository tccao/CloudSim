# CloudSim — Product Requirements Document (PRD / SRS)

> Version: 1.1  
> Owner: Tinh  
> Last Updated: May 2026  
> Project Type: Cloud Infrastructure Simulator with Real AWS EC2 Integration

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [User Stories](#3-user-stories)
4. [User Flows](#4-user-flows)
5. [System Features (Functional Requirements)](#5-system-features-functional-requirements)
6. [External Interface Requirements](#6-external-interface-requirements)
7. [Data Requirements](#7-data-requirements)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [System Architecture](#9-system-architecture)
10. [Use Cases](#10-use-cases)
11. [Acceptance Criteria](#11-acceptance-criteria-mvp)
12. [Quality Assurance Plan](#12-quality-assurance-plan)
13. [Project Management](#13-project-management)

---

## 1. Introduction

### 1.1 Purpose

This document defines the product and functional requirements for **CloudSim**, a web-based cloud infrastructure management application that integrates with real AWS EC2 for compute, storage, networking, and monitoring. It serves as both the **Product Requirements Document (PRD)** for stakeholders and the **Software Requirements Specification (SRS)** for engineering.

### 1.2 Scope

CloudSim provides an AWS console-like experience:

- Provision, start, stop, reboot, and terminate **EC2 instances**.
- View **security groups**, **VPC / subnet networking**, **EBS storage**, and **tags**.
- **Monitor** CPU, network, and disk metrics via CloudWatch — with snapshots persisted to PostgreSQL.
- **Cost tracking** via AWS Cost Explorer (daily breakdown, monthly projection).
- **Role-Based Access Control** (Admin, DevOps Engineer, User) enforced at the API layer.
- Provide **REST APIs** for developer automation.

### 1.3 Definitions, Acronyms, Abbreviations

| Term | Definition |
|------|------------|
| Instance | AWS EC2 compute node |
| Volume | EBS block storage attached to an instance |
| Security Group | Virtual firewall for instance network rules |
| Metric | CloudWatch time-series data (CPU, Network, Disk I/O) |
| RBAC | Role-Based Access Control (Admin, DevOps Engineer, User) |
| JWT | JSON Web Token used for stateless authentication |
| MVP | Minimum Viable Product |

### 1.4 References

- AWS EC2 Documentation
- AWS CloudWatch API
- FastAPI Documentation
- React Documentation

---

## 2. Overall Description

### 2.1 Product Perspective

CloudSim is a fullstack web application with:

- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui (deployed as a Vercel static site)
- **Backend**: FastAPI + SQLAlchemy + boto3 (deployed as a Render Docker web service)
- **Database**: PostgreSQL (local, Docker Compose, or Render PostgreSQL)
- **Cloud**: AWS EC2, CloudWatch, Cost Explorer in `live` mode; PostgreSQL-backed mock resources in `mock` mode
- **CI/CD**: GitHub Actions (backend tests, frontend lint/test/build, Compose validation, Docker image builds)

### 2.2 User Classes & Characteristics

| Role | Permissions |
|------|-------------|
| **User** | Launch instances, manage (start/stop/reboot/terminate) own instances, view own CloudWatch metrics and Cost Explorer data filtered to resources tagged with their user ID. No quota modification or user management. |
| **DevOps Engineer** | Full EC2 lifecycle on any instance, CloudWatch, Cost Explorer, configure auto-scaling and notifications. View-only quotas. No user management. |
| **Admin** | All DevOps permissions, plus full user CRUD and modifiable resource quotas. |

### 2.3 Operating Environment

- Modern desktop browser (Chrome, Firefox, Safari)
- Production deployment with Vercel frontend and Render backend/database
- Local development through Docker Compose or separate frontend/backend processes
- AWS account with EC2 access only when `CLOUDSIM_AWS_BACKEND=live`

### 2.4 Design & Implementation Constraints

- Role-based access control enforced at API level
- `mock` mode for safe public demos; `live` mode for real AWS resources where costs apply
- Single-developer velocity

### 2.5 Assumptions & Dependencies

- Valid AWS credentials configured only for live AWS mode (see `iamSetupGuide.md`)
- PostgreSQL database available locally or via managed service
- Node.js 22+ and Python 3.14+ installed for local parity with CI/Docker

---

## 3. User Stories

### Epic 1: Compute Instance Management (EC2)

| As a | I want to | So that I can | Acceptance Criteria |
|------|-----------|---------------|---------------------|
| User | View my own virtual instances | Monitor my infrastructure | Dashboard shows instance name, status, type, IPs (filtered by `CreatedBy` tag) |
| User | Launch a new instance | Provision my own workload | 4-step wizard creates a real EC2 instance tagged with my user ID |
| User | Manage (start / stop / reboot / terminate) my instance | Manage compute lifecycle | State transitions for own instance only; 403 for others |
| DevOps Engineer | Manage / Terminate any instance across users | Clean up resources team-wide | Instance removed from AWS and UI regardless of owner |
| DevOps Engineer | View instance details | Inspect configuration | Details page shows security groups, storage, tags |

### Epic 2: Storage and Networking

| As a | I want to | So that I can | Acceptance Criteria |
|------|-----------|---------------|---------------------|
| DevOps Engineer | View attached EBS volumes | Understand storage config | Storage tab shows volume ID, size, type, encryption |
| DevOps Engineer | View security groups | Understand network rules | Security tab shows group names and IDs |
| DevOps Engineer | View VPC/Subnet info | Understand network topology | Networking tab shows VPC ID, Subnet ID, DNS names |

### Epic 3: Monitoring & Metrics

| As a | I want to | So that I can | Acceptance Criteria |
|------|-----------|---------------|---------------------|
| User | View metrics for my own instances | Catch performance issues early | CPU / Network / Disk charts render via CloudWatch |
| User | View cost breakdown for my own resources | Track spend from workloads I launched | Cost Explorer data is filtered by the `CreatedBy` cost allocation tag |
| DevOps Engineer | View metrics for any instance | Monitor team performance | Instance dropdown lists all instances; charts update on selection |
| DevOps Engineer | View cost breakdown | Track spending | Daily and monthly Cost Explorer data displayed |
| Admin | Retain historical metrics in our DB | Run trend analysis offline | Each fetch persists datapoints to the `metrics` table |

### Epic 4: System Management

| As a | I want to | So that I can | Acceptance Criteria |
|------|-----------|---------------|---------------------|
| Admin | Create users with assigned roles | Onboard new team members | New user appears in `/api/admin/users` and can log in |
| Admin | Update or deactivate users | Manage access lifecycle | `is_active=false` blocks login; cannot self-disable |
| Admin | Delete users | Off-board departed members | Self-deletion blocked; account removed from DB |

### Epic 5: API Integration

| As a | I want to | So that I can | Acceptance Criteria |
|------|-----------|---------------|---------------------|
| DevOps Engineer | Use REST APIs for automation | Integrate with pipelines | All CRUD operations available via API |
| DevOps Engineer | Query metrics programmatically | Build custom dashboards | `/api/ec2/instances/{id}/metrics` returns JSON |

---

## 4. User Flows

### 4.1 Instance Provisioning Flow (Create)

**Actor:** Any authenticated user (User, DevOps Engineer, Admin)

1. User clicks **"+ Launch Instance"** button on Dashboard
2. 4-step wizard opens (Name & AMI → Instance Type → Network & Storage → Review)
3. User submits → Frontend sends `POST /api/ec2/instances`
4. Backend calls AWS `ec2.run_instances()` and tags the instance with `CreatedBy=<user_id>` and `CreatedByEmail`
5. AWS returns instance ID with `pending` status
6. Backend returns `{ message, instance_id }`
7. Frontend refreshes Dashboard showing the new instance

**API:** `POST /api/ec2/instances`

```json
Request: { "name": "web-server-01", "instance_type": "t2.micro" }
Response: { "message": "Instance created", "instance_id": "i-0abc123..." }
```

### 4.2 Instance Details Flow (View)

**Actor:** Any authenticated user

1. User clicks instance name in Dashboard table
2. App navigates to Instance Details tab
3. Frontend sends `GET /api/ec2/instances/{instance_id}`
4. Backend calls AWS `ec2.describe_instances()` and `ec2.describe_volumes()`
5. Backend returns comprehensive instance details
6. Frontend renders Details, Security, Networking, Storage, Tags tabs

**API:** `GET /api/ec2/instances/{instance_id}`

```json
Response: {
  "instance_id": "i-0abc123...",
  "name": "web-server-01",
  "instance_type": "t2.micro",
  "state": "running",
  "public_ip": "54.123.45.67",
  "private_ip": "172.31.16.22",
  "security_groups": [{ "GroupId": "sg-xxx", "GroupName": "default" }],
  "block_devices": [{ "device_name": "/dev/xvda", "volume_id": "vol-xxx", "size": 8 }],
  "tags": [{ "Key": "Name", "Value": "web-server-01" }]
}
```

### 4.3 Instance Action Flow (Start/Stop/Reboot)

**Actor:** User (own instances only), DevOps Engineer, Admin

1. User clicks action button (Start/Stop/Reboot) on instance
2. Frontend sends `POST /api/ec2/instances/{id}/start|stop|reboot`
3. Backend calls corresponding AWS API
4. AWS initiates state change
5. Backend returns action confirmation
6. Frontend shows toast notification and refreshes instance state

### 4.4 Instance Termination Flow (Delete)

**Actor:** User (own instances only), DevOps Engineer, Admin

1. User clicks "Terminate" button on instance
2. Confirmation dialog appears with warning
3. User confirms → Frontend sends `DELETE /api/ec2/instances/{id}`
4. Backend calls `ec2.terminate_instances()`
5. Instance state changes to `shutting-down` then `terminated`
6. Frontend removes instance from active list

### 4.5 Metrics Monitoring Flow

**Actor:** Any authenticated user

1. User navigates to Monitoring tab
2. User selects an instance from dropdown
3. Frontend sends `GET /api/ec2/instances/{id}/metrics`
4. Backend calls CloudWatch `get_metric_statistics()`
5. Backend returns time-series data for CPU, Network In/Out
6. Frontend renders charts with Recharts library

---

## 5. System Features (Functional Requirements)

### 5.1 Instance Management (Epic 1)

- **FR-1:** List all EC2 instances with sync to database
- **FR-2:** Create instance with name and type selection
- **FR-3:** Start/Stop instance with state persistence
- **FR-4:** Reboot running instances
- **FR-5:** Terminate instance (requires ownership for User; DevOps/Admin can terminate any)
- **FR-6:** View detailed instance information

### 5.2 Storage & Networking (Epic 2)

- **FR-7:** Display attached EBS volumes with details
- **FR-8:** Display security group associations
- **FR-9:** Display VPC, Subnet, and DNS information

### 5.3 Monitoring & Metrics (Epic 3)

- **FR-10:** Fetch CloudWatch metrics (CPU, NetworkIn, NetworkOut, DiskReadOps, DiskWriteOps) for instances
- **FR-11:** Display CPU utilization, network, and disk I/O charts (Recharts)
- **FR-12:** Persist each CloudWatch datapoint to the local `metrics` table on fetch (idempotent)
- **FR-13:** Display Cost Explorer data — daily breakdown and current-month projection; `User` results are filtered to resources tagged with their CloudSim user ID

### 5.4 System Management (Epic 4)

- **FR-14:** User authentication with JWT (HS256, 30-minute TTL) and bcrypt password hashing
- **FR-15:** Role-based access control: `Admin`, `DevOps Engineer`, `User`
- **FR-16:** Admin-only IAM panel for full user CRUD (`/api/admin/users`)
- **FR-17:** Ownership filtering for `User` role via the `CreatedBy` AWS resource tag

### 5.5 API Integration (Epic 5)

- **FR-18:** RESTful API for all instance, metrics, cost, and admin operations
- **FR-19:** Consistent JSON response format with Pydantic schemas
- **FR-20:** Error handling with appropriate HTTP status codes (401, 403, 404, 502, 503)
- **FR-21:** Security headers middleware (X-Frame-Options, X-XSS-Protection, etc.) on all responses

---

## 6. External Interface Requirements

### 6.1 User Interface (UI)

| Page | Components |
|------|------------|
| **Login** | Role selection, credentials form |
| **Dashboard** | Instance table, action buttons, zone health, alarms |
| **Instance Details** | Header, quick info cards, tabbed details (Details, Security, Networking, Storage, Tags) |
| **Monitoring** | Instance selector, metric charts, cost breakdown |

### 6.2 REST API Endpoints

Base URL (dev): `http://localhost:8000`

**Authentication — `/api/auth`**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register a new user (default role `User`) |
| POST | `/api/auth/login` | OAuth2 password flow → returns JWT |
| GET | `/api/auth/me` | Return the currently authenticated user |

**EC2 Instances — `/api/ec2`**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ec2/instances` | List instances (filtered by ownership for `User` role) |
| GET | `/api/ec2/instances/{id}` | Get instance details (Details / Security / Networking / Storage / Tags) |
| POST | `/api/ec2/instances` | Create new instance |
| POST | `/api/ec2/instances/{id}/start` | Start instance |
| POST | `/api/ec2/instances/{id}/stop` | Stop instance |
| POST | `/api/ec2/instances/{id}/reboot` | Reboot instance |
| DELETE | `/api/ec2/instances/{id}` | Terminate instance |
| GET | `/api/ec2/launch-options` | List current AMI, instance type, VPC, subnet, and security group launch choices |
| GET | `/api/ec2/instance-types` | List available instance types |

**Metrics & Costs — `/api/ec2`**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ec2/instances/{id}/metrics` | CloudWatch history (CPU, Network, Disk) — ownership-filtered for `User`, also persisted to DB |
| GET | `/api/ec2/instances/{id}/metrics/current` | Latest single-point metrics for dashboard cards — ownership-filtered for `User` |
| GET | `/api/ec2/costs/daily` | Daily cost breakdown for last N days; `User` results are filtered by the `CreatedBy` tag |
| GET | `/api/ec2/costs/summary` | Month-to-date spend and projected monthly total; `User` results are filtered by the `CreatedBy` tag |

**Admin — `/api/admin` (Admin role required)**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users` | List all users |
| POST | `/api/admin/users` | Create user with role |
| PUT | `/api/admin/users/{user_id}` | Update user role / active status |
| DELETE | `/api/admin/users/{user_id}` | Delete user |

**System**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness check for load balancers |
| GET | `/docs` | OpenAPI Swagger UI (development only) |

### 6.3 Authentication

- JWT Bearer token in `Authorization` header
- Tokens stored in localStorage
- Auto-logout on 401 response

---

## 7. Data Requirements

### 7.1 Database Entities

**User** (`users` table)

```
id, email, hashed_password, role, is_active, created_at
```

- `role` is constrained to `Admin`, `DevOps Engineer`, or `User` via a CHECK constraint.

**Instance** (`instances` table — synced from AWS)

```
instance_id (PK), name, instance_type, state, public_ip, private_ip,
availability_zone, launch_time, last_synced, created_by_user_id
```

- Composite index on `(state, last_synced)` for fast dashboard queries.

**Metric** (`metrics` table — CloudWatch snapshots)

```
id (PK), instance_id, metric_name, value, unit, recorded_at, collected_at
```

- Composite index on `(instance_id, metric_name, recorded_at)`.
- Idempotency guard prevents duplicate datapoints when a metric refresh is repeated.

### 7.2 External Data (AWS)

Retrieved in real-time via boto3:

- Security Groups (EC2)
- EBS Volumes (EC2)
- Resource Tags (EC2 — including the `CreatedBy` ownership tag)
- CloudWatch Metrics (CPU, Network, Disk)
- Cost Explorer (`GetCostAndUsage`, `GetCostForecast`)

---

## 8. Non-Functional Requirements

### 8.1 Performance

- API response time < 500ms for CRUD operations
- Frontend first paint < 2.5s
- Charts update within 1s of data fetch

### 8.2 Security

- JWT authentication (HS256, 30-minute TTL) with bcrypt password hashing (work factor 12)
- Role-based access control enforced at the API layer via FastAPI dependencies
- CORS restricted to configured frontend origins (localhost dev + production domain)
- Security headers middleware (X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) on every response
- AWS credentials via environment variables (never in code)

### 8.3 Reliability

- Graceful error handling with user-friendly messages
- Toast notifications for action feedback
- Loading states during async operations

### 8.4 Maintainability

- TypeScript for type safety in frontend
- Pydantic schemas for API validation
- Modular component architecture

---

## 9. System Architecture

### 9.1 Component Diagram

See `architectureDiagram.md` for the full Mermaid diagram with numbered flows. A simplified text view:

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  (React 18 + TypeScript + Vite + Tailwind + shadcn/ui)      │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │Dashboard │  │ Details  │  │Monitoring│  │  IAM &   │    │
│  │          │  │ (5 tabs) │  │ (5 tabs) │  │ Settings │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       └─────────────┴──────┬──────┴─────────────┘           │
│                     Axios API Client                         │
└──────────────────────────┼──────────────────────────────────┘
                           │ HTTPS  (Authorization: Bearer JWT)
┌──────────────────────────┼──────────────────────────────────┐
│                Backend (FastAPI on Render)                   │
│  Security Headers Middleware → CORS → get_current_user()    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Auth Routes │  │  EC2 Routes │  │Admin Routes │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         └────────────────┼────────────────┘                  │
│                  ┌───────┴───────┐                           │
│                  │  aws_service  │ (boto3 wrapper)           │
│                  └───────┬───────┘                           │
└──────────────────────────┼──────────────────────────────────┘
                           │
   ┌───────────┬───────────┼───────────┬─────────────┐
   ▼           ▼           ▼           ▼             ▼
┌──────┐  ┌──────────┐  ┌──────┐  ┌──────────┐  ┌──────────┐
│ EC2  │  │CloudWatch│  │Cost  │  │PostgreSQL│  │PostgreSQL│
│      │  │          │  │Expl. │  │  users   │  │instances │
└──────┘  └──────────┘  └──────┘  └──────────┘  │ + metrics│
                                                 └──────────┘
```

### 9.2 Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, Recharts |
| API Client | Axios |
| Backend | FastAPI (lifespan handlers), Pydantic, SQLAlchemy |
| AWS SDK | boto3 |
| Database | PostgreSQL |
| Auth | JWT (python-jose, HS256), bcrypt |
| CI/CD | GitHub Actions |
| Hosting | Vercel frontend static site, Render backend web service, Render PostgreSQL |

---

## 10. Use Cases

### UC-1: View Dashboard

**Trigger:** User logs in
**Flow:** Fetch instances → Render table → Show zone health and alarms
**Output:** Dashboard with real-time instance data

### UC-2: Launch New Instance

**Trigger:** User clicks "Launch Instance"
**Flow:** Open modal → Fill form → Submit → Create in mock or live AWS backend → Refresh list
**Output:** New instance appears in dashboard

### UC-3: Manage Instance State

**Trigger:** User clicks Start/Stop/Reboot
**Flow:** Call API → instance state change → Toast notification → Refresh
**Output:** Instance state updated

### UC-4: View Instance Details

**Trigger:** User clicks instance name
**Flow:** Navigate to details → Fetch from API → Render tabs
**Output:** Comprehensive instance information displayed

### UC-5: Monitor Performance

**Trigger:** User opens Monitoring tab
**Flow:** Select instance → Fetch CloudWatch or mock metrics → Persist datapoints to `metrics` table → Render charts
**Output:** CPU, Network, and Disk I/O charts with historical data

### UC-6: Manage Users (Admin)

**Trigger:** Admin opens IAM & Settings → User Management
**Flow:** List users → Create / update / delete via `/api/admin/users` endpoints
**Output:** User table updated; new accounts can immediately log in

### UC-7: Track Spend

**Trigger:** User, DevOps Engineer, or Admin opens Monitoring → Cost tab
**Flow:** Fetch `/api/ec2/costs/daily` and `/api/ec2/costs/summary` from Cost Explorer
**Output:** Daily breakdown chart and month-to-date / projected total; `User` output is filtered to their own `CreatedBy` tag

---

## 11. Acceptance Criteria (MVP)

- [x] **AC-1:** Authenticated users log in via JWT and receive a role-scoped token
- [x] **AC-2:** Dashboard displays instances from mock mode or live EC2, with metadata synced to the local `instances` table
- [x] **AC-3:** Instance details show security groups, networking, EBS storage, and tags
- [x] **AC-4:** Start / Stop / Reboot buttons trigger the corresponding mock or live lifecycle actions
- [x] **AC-5:** Admin and DevOps can act on any instance; Users are restricted to instances they created (via `CreatedBy` tag)
- [x] **AC-6:** Monitoring page shows CPU, Network, and Disk I/O charts from CloudWatch or mock metrics
- [x] **AC-7:** Each CloudWatch fetch persists datapoints to the `metrics` table (idempotent)
- [x] **AC-8:** Cost Explorer integration shows daily breakdown and monthly projection, with `User` results filtered to their own resources
- [x] **AC-9:** Admin can create, update, and delete users through `/api/admin/users`
- [x] **AC-10:** All API endpoints require authentication; role checks enforced server-side
- [x] **AC-11:** Error states surface clear toasts with appropriate HTTP status codes

---

## 12. Quality Assurance Plan

### 12.1 Testing Strategy

- **Unit Tests:** API route handlers, utility functions
- **Integration Tests:** Frontend-backend data flow
- **Manual Testing:** UI interactions, AWS operations

### 12.2 Code Quality

- TypeScript strict mode for frontend
- ESLint for code style
- Pydantic for API schema validation

### 12.3 Security Testing

- JWT token validation
- Role-based permission checks
- CORS configuration verification

---

## 13. Project Management

### 13.1 Completed Milestones

- ✅ Project setup, wireframes, SRS/PRD draft
- ✅ Frontend UI implementation (Dashboard, Instance Details, Monitoring, IAM panel)
- ✅ Backend API implementation (FastAPI + SQLAlchemy)
- ✅ AWS EC2 integration (boto3, ownership tagging)
- ✅ CloudWatch metrics integration with Recharts
- ✅ Instance Details page with real AWS data (5 tabs)
- ✅ Cost Explorer integration (daily + monthly summary)
- ✅ Admin user management (CRUD)
- ✅ Local persistence of CloudWatch metrics (`metrics` table)
- ✅ Migration to FastAPI lifespan handlers
- ✅ Security headers middleware
- ✅ Mock AWS backend for safe production demos
- ✅ Production deployment guide for Vercel frontend, Render backend, and Render PostgreSQL
- ✅ Deployment smoke test script

### 13.2 Current Status

- All MVP features implemented and production-deployable
- Vite frontend documented for Vercel and FastAPI backend documented for Render production mode
- Mock mode supports safe public demos without real AWS calls
- Live mode supports AWS EC2, CloudWatch, and Cost Explorer integration
- RBAC enforced at the API layer for all three roles
- Deployment smoke testing available through `scripts/smoke_deployment.sh`
- See `docs/ProjectSprintPlan.csv` for detailed sprint history

### 13.3 Future Enhancements

- [ ] Auto-scaling simulation (UI exists, policy execution pending)
- [ ] Multi-region support
- [ ] WebSocket for real-time instance state updates
- [ ] Dark mode theme
- [ ] Trend queries / threshold alerts off the persisted `metrics` table

---

*Document Last Updated: May 2026*
