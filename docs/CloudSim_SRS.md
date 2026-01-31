# CloudSim — Software Requirements Specification (SRS)

> Version: 1.0  
> Owner: Tinh  
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
This SRS defines the requirements for **CloudSim**, a web-based cloud infrastructure management application that integrates with real AWS EC2 for compute, storage, networking, and monitoring.

### 1.2 Scope
CloudSim provides an AWS console-like experience:
- Provision, start/stop, reboot, and terminate **EC2 instances**.
- View **security groups**, **networking**, and **storage** details.
- **Monitor** CPU/RAM/network metrics via CloudWatch integration.
- **Cost tracking** via AWS Cost Explorer.
- Provide **REST APIs** for developer automation.

### 1.3 Definitions, Acronyms, Abbreviations
| Term | Definition |
|------|------------|
| Instance | AWS EC2 compute node |
| Volume | EBS block storage attached to an instance |
| Security Group | Virtual firewall for instance network rules |
| Metric | CloudWatch time series data (CPU, Network, etc.) |
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
- **Frontend**: React 18 + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + SQLAlchemy + boto3 (AWS SDK)
- **Database**: PostgreSQL
- **Cloud**: AWS EC2, CloudWatch, Cost Explorer
- **CI/CD**: GitHub Actions

### 2.2 User Classes & Characteristics
| Role | Permissions |
|------|-------------|
| **User** | View instances, start/stop own instances |
| **DevOps Engineer** | Full EC2 + CloudWatch + Cost Explorer (no terminate) |
| **Admin** | All permissions + terminate instances, manage users, quotas |

### 2.3 Operating Environment
- Modern desktop browser (Chrome, Firefox, Safari)
- Backend on Linux (Ubuntu/WSL)
- AWS account with EC2 access

### 2.4 Design & Implementation Constraints
- Role-based access control enforced at API level
- Real AWS resources (costs apply for running instances)
- Single-developer velocity

### 2.5 Assumptions & Dependencies
- Valid AWS credentials configured
- PostgreSQL database available
- Node.js 18+ and Python 3.11+ installed

---

## 3. User Stories

### Epic 1: Compute Instance Management (EC2)

| As a | I want to | So that I can | Acceptance Criteria |
|------|-----------|---------------|---------------------|
| User | View all my virtual instances | Monitor infrastructure | Dashboard shows instance name, status, type, IPs |
| User | Start or stop my instance | Manage compute lifecycle | Status toggles between Running and Stopped |
| DevOps Engineer | Create new instances | Provision resources | "Launch Instance" creates real EC2 instance |
| Admin | Terminate an instance | Clean up resources | Instance removed from AWS and UI |
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
| User | View real-time metrics (CPU, Network) | Monitor performance | Charts update with CloudWatch data |
| DevOps Engineer | View cost breakdown | Track spending | Cost charts show daily spend by service |
| Admin | Export metrics data | Perform analysis | CSV export available |

### Epic 4: System Management

| As a | I want to | So that I can | Acceptance Criteria |
|------|-----------|---------------|---------------------|
| Admin | Add or remove users | Control access | Users manageable in IAM panel |
| Admin | Set resource limits | Enforce quotas | System blocks unauthorized actions |

### Epic 5: API Integration

| As a | I want to | So that I can | Acceptance Criteria |
|------|-----------|---------------|---------------------|
| DevOps Engineer | Use REST APIs for automation | Integrate with pipelines | All CRUD operations available via API |
| DevOps Engineer | Query metrics programmatically | Build custom dashboards | `/api/ec2/instances/{id}/metrics` returns JSON |

---

## 4. User Flows

### 4.1 Instance Provisioning Flow (Create)

**Actor:** DevOps Engineer

1. User clicks **"Launch Instance"** button on Dashboard
2. Modal appears with instance configuration form (name, type)
3. User submits form → Frontend sends `POST /api/ec2/instances`
4. Backend calls AWS `ec2.run_instances()` API
5. AWS returns instance ID with `pending` status
6. Backend returns success response with instance details
7. Frontend refreshes Dashboard showing new instance

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

**Actor:** User (own instances), Admin (any instance)

1. User clicks action button (Start/Stop/Reboot) on instance
2. Frontend sends `POST /api/ec2/instances/{id}/start|stop|reboot`
3. Backend calls corresponding AWS API
4. AWS initiates state change
5. Backend returns action confirmation
6. Frontend shows toast notification and refreshes instance state

### 4.4 Instance Termination Flow (Delete)

**Actor:** Admin only

1. Admin clicks "Terminate" button on instance
2. Confirmation dialog appears with warning
3. Admin confirms → Frontend sends `DELETE /api/ec2/instances/{id}`
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
- **FR-5:** Terminate instance (Admin only)
- **FR-6:** View detailed instance information

### 5.2 Storage & Networking (Epic 2)
- **FR-7:** Display attached EBS volumes with details
- **FR-8:** Display security group associations
- **FR-9:** Display VPC, Subnet, and DNS information

### 5.3 Monitoring & Metrics (Epic 3)
- **FR-10:** Fetch CloudWatch metrics for instances
- **FR-11:** Display CPU utilization charts
- **FR-12:** Display network I/O charts
- **FR-13:** Display cost breakdown (mocked for cost savings)

### 5.4 System Management (Epic 4)
- **FR-14:** User authentication with JWT tokens
- **FR-15:** Role-based access control (User, DevOps Engineer, Admin)
- **FR-16:** IAM panel for user management

### 5.5 API Integration (Epic 5)
- **FR-17:** RESTful API for all instance operations
- **FR-18:** Consistent JSON response format
- **FR-19:** Error handling with appropriate HTTP status codes

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

Base URL: `http://localhost:8000/api/ec2`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/instances` | List all instances |
| GET | `/instances/{id}` | Get instance details |
| POST | `/instances` | Create new instance |
| POST | `/instances/{id}/start` | Start instance |
| POST | `/instances/{id}/stop` | Stop instance |
| POST | `/instances/{id}/reboot` | Reboot instance |
| DELETE | `/instances/{id}` | Terminate instance |
| GET | `/instances/{id}/metrics` | Get CloudWatch metrics |
| GET | `/instance-types` | List available instance types |

### 6.3 Authentication
- JWT Bearer token in `Authorization` header
- Tokens stored in localStorage
- Auto-logout on 401 response

---

## 7. Data Requirements

### 7.1 Database Entities

**User**
```
id, email, password_hash, role, created_at
```

**Instance** (synced from AWS)
```
id, instance_id, name, instance_type, state, public_ip, private_ip, availability_zone, launch_time, synced_at
```

### 7.2 External Data (AWS)

Retrieved in real-time via boto3:
- Security Groups
- EBS Volumes
- Tags
- CloudWatch Metrics
- Cost Explorer data

---

## 8. Non-Functional Requirements

### 8.1 Performance
- API response time < 500ms for CRUD operations
- Frontend first paint < 2.5s
- Charts update within 1s of data fetch

### 8.2 Security
- JWT authentication with bcrypt password hashing
- Role-based access control at API level
- CORS configured for frontend origin only
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

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  (React + TypeScript + Tailwind + shadcn/ui)                │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │Dashboard │  │ Details  │  │Monitoring│  │  Login   │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │             │             │             │           │
│       └─────────────┴─────────────┴─────────────┘           │
│                          │                                   │
│                     Axios API Client                         │
└──────────────────────────┼──────────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────┼──────────────────────────────────┐
│                     Backend (FastAPI)                        │
│                          │                                   │
│  ┌─────────────┐  ┌──────┴──────┐  ┌─────────────┐         │
│  │ Auth Routes │  │  EC2 Routes │  │Admin Routes │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│              ┌───────────┴───────────┐                      │
│              │    AWS Service        │                      │
│              │      (boto3)          │                      │
│              └───────────┬───────────┘                      │
└──────────────────────────┼──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────┴────┐      ┌────┴────┐      ┌────┴────┐
    │   AWS   │      │   AWS   │      │PostgreSQL│
    │   EC2   │      │CloudWatch│     │    DB    │
    └─────────┘      └─────────┘      └──────────┘
```

### 9.2 Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| API Client | Axios |
| Backend | FastAPI, Pydantic, SQLAlchemy |
| AWS SDK | boto3 |
| Database | PostgreSQL |
| Auth | JWT (python-jose), bcrypt |

---

## 10. Use Cases

### UC-1: View Dashboard
**Trigger:** User logs in
**Flow:** Fetch instances → Render table → Show zone health and alarms
**Output:** Dashboard with real-time instance data

### UC-2: Launch New Instance
**Trigger:** User clicks "Launch Instance"
**Flow:** Open modal → Fill form → Submit → Create in AWS → Refresh list
**Output:** New instance appears in dashboard

### UC-3: Manage Instance State
**Trigger:** User clicks Start/Stop/Reboot
**Flow:** Call API → AWS state change → Toast notification → Refresh
**Output:** Instance state updated

### UC-4: View Instance Details
**Trigger:** User clicks instance name
**Flow:** Navigate to details → Fetch from API → Render tabs
**Output:** Comprehensive instance information displayed

### UC-5: Monitor Performance
**Trigger:** User opens Monitoring tab
**Flow:** Select instance → Fetch metrics → Render charts
**Output:** CPU and network charts with historical data

---

## 11. Acceptance Criteria (MVP)

- [x] **AC-1:** User can log in with role selection
- [x] **AC-2:** Dashboard displays real EC2 instances from AWS
- [x] **AC-3:** Instance details show security groups, storage, and tags
- [x] **AC-4:** Start/Stop/Reboot buttons trigger corresponding AWS actions
- [x] **AC-5:** Admin can terminate instances
- [x] **AC-6:** Monitoring page shows CloudWatch metrics charts
- [x] **AC-7:** DevOps Engineer can create new instances
- [x] **AC-8:** All API endpoints require authentication
- [x] **AC-9:** Role-based access control enforced
- [x] **AC-10:** Error states handled with user feedback (toasts)

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
- ✅ Week 1: Project setup, wireframes, SRS draft
- ✅ Week 2: Frontend UI implementation
- ✅ Week 3: Backend API implementation
- ✅ Week 4: AWS EC2 integration
- ✅ Week 5: CloudWatch metrics integration
- ✅ Week 6: Instance details page with real data

### 13.2 Current Status
- All MVP features implemented
- Real AWS EC2 integration working
- Frontend connected to backend

### 13.3 Future Enhancements
- [ ] Auto-scaling simulation
- [ ] Cost forecasting
- [ ] Multi-region support
- [ ] WebSocket for real-time updates
- [ ] Dark mode theme

---

*Document Last Updated: January 2026*
