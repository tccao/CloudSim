# CloudSim – User Stories Document
> Version: 0.9 (Draft)  
> Owner: Tinh  
> Project Type: Systems/Infrastructure Simulator (Free-tier stack)
## Overview
CloudSim is a cloud infrastructure simulator designed to mimic AWS EC2-style compute, storage, and network environments.

This document outlines the key user stories grouped by functional epics for the MVP release.

---

## Epic 1: Compute Instance Management (EC2 Simulation)

| **As a** | **I want to** | **So that I can** | **Criteria** |
|------------|----------------|---------------------|--------------------------|
| User | View all my virtual instances | Monitor simulated infrastructure | Dashboard displays instance name, status, and metrics |
| User | Create new instances | Simulate provisioning behavior | “Create Instance” triggers backend request → instance saved in DB |
| User | Start or stop an instance | Manage compute lifecycle | Instance status toggles between *Running* and *Stopped* |
| User | Delete an instance | Clean up unused resources | Instance removed from UI and DB |
| User | View instance metrics | Track resource usage | CPU/RAM usage charts visible in dashboard |

---

## Epic 2: Storage and Networking Simulation

| **As a** | **I want to** | **So that I can** | **Criteria** |
|------------|----------------|---------------------|--------------------------|
| DevOps Engineer | Create and attach simulated storage volumes | Expand storage capacity | Volume appears in instance details |
| DevOps Engineer | View network connections between instances | Understand topology | Network graph displayed in dashboard |
| Admin User | Adjust bandwidth and latency | Test network performance | Network metrics dynamically update |

---

## Epic 3: Monitoring & Metrics Visualization

| **As a** | **I want to** | **So that I can** | **Criteria** |
|------------|----------------|---------------------|--------------------------|
| User | View real-time metrics (CPU, RAM, I/O) | Monitor simulated performance | Metrics update every 5s via WebSocket |
| DevOps Engineer | Receive alerts on threshold breaches | Detect anomalies | Alerts visible on dashboard and logged |
| Admin User | Export metrics data | Perform external analysis | Exportable CSV generated via backend endpoint |

---

## Epic 4: System Management & Configuration

| **As a** | **I want to** | **So that I can** | **Criteria** |
|------------|----------------|---------------------|--------------------------|
| Admin User | Add or remove users | Control access | CRUD operations visible in admin panel |
| Admin User | Set resource limits | Enforce quotas | System blocks instance creation beyond limit |
| DevOps Engineer | Adjust simulation parameters | Tune orchestration behavior | Configurations persist between sessions |

---

## Epic 5: Developer and API Integration

| **As a** | **I want to** | **So that I can** | **Criteria** |
|------------|----------------|---------------------|--------------------------|
| Developer | Use REST APIs for automation | Integrate with pipelines | `/instances/create` returns 201 + instance ID | 
| Developer | Query system metrics programmatically | Build custom dashboards | `/metrics` returns real-time JSON stats |
| Developer | Delete instances via API | Automate cleanup | `/instances/delete/{id}` returns 200 |

---

## Epic 6: Future Enhancements (Post-MVP)

| **As a** | **I want to** | **So that I can** | **Criteria** |
|------------|----------------|---------------------|--------------------------|
| User | View cost simulation per resource | Estimate usage costs | Cost table per instance in UI |
| DevOps Engineer | Simulate auto-scaling behavior | Test elasticity scenarios | Auto-scale triggers new instance creation |
| Admin User | Track all user actions | Maintain audit trail | Logs persisted and exportable |

---

## Summary
This user story document defines the foundational scope for CloudSim’s MVP.  
Future sprints will convert these stories into epics and tasks within the Agile backlog, supported by API reference documentation and UI/UX prototypes.
