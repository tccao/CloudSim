# CloudSim – User Flow Documentation

## Overview
This document describes detailed user flows for **resource provisioning**, **scaling**, and **termination** in CloudSim.  
Each flow illustrates the user's interaction from the frontend interface to the backend API, database, and system response.

---

# Epic 1: Compute Instance Management (EC2 Simulation)

## 1. Provisioning Flow (Create Instance)

### Goal
Enable users to create new simulated compute instances within the CloudSim dashboard.

### User Actions
1. User clicks **“Create Instance”** on the dashboard.
2. A configuration modal appears (CPU, RAM, region, name).
3. User submits the form → frontend sends POST request to `/api/instances/create`.
4. Backend validates input, saves instance to DB, and starts orchestration simulation.
5. System returns JSON response with instance ID and initial status (`creating`).
6. Frontend updates dashboard and displays instance card with status badge.

### API Triggered
`POST /api/instances/create`

**Request Body**
```json
{
  "name": "tinh-sim-1",
  "cpu": 2,
  "memory": 4096,
  "region": "us-east-1"
}
```

**Response**
```json
{
  "id": "i-001",
  "status": "creating",
  "created_at": "2025-11-04T15:00:00Z"
}
```

**Diagram Reference:** `provisioning_flow.png`

---

## 2. Scaling Flow (Modify Instance)

### Goal
Allow users to scale compute resources or modify configurations dynamically.

### User Actions
1. User clicks **“Scale Instance”** button on instance card.
2. System prompts for new configuration (CPU, RAM).
3. Frontend sends PUT request to `/api/instances/scale/{id}`.
4. Backend updates instance in DB and simulates resource adjustment.
5. Updated resource data returned to frontend and dashboard refreshes.

### API Triggered
`PUT /api/instances/scale/{id}`

**Request Body**
```json
{
  "cpu": 4,
  "memory": 8192
}
```

**Response**
```json
{
  "id": "i-001",
  "status": "updating",
  "message": "Scaling initiated"
}
```

**Diagram Reference:** `scaling_flow.png`

---

## 3. Termination Flow (Delete Instance)

### Goal
Allow users to remove simulated instances safely from the system.

### User Actions
1. User selects an instance and clicks **“Terminate”**.
2. Confirmation modal appears (“Are you sure?”).
3. Frontend sends DELETE request to `/api/instances/{id}`.
4. Backend removes the instance record from DB.
5. Response confirms termination → frontend removes instance card.

### API Triggered
`DELETE /api/instances/{id}`

**Response**
```json
{
  "id": "i-001",
  "status": "terminated",
  "message": "Instance successfully terminated"
}
```

**Diagram Reference:** `termination_flow.png`

---
# Epic 2: Storage and Networking Simulation

## 4. Storage Volume Attachment Flow

### Goal
Allow users to create and attach simulated storage volumes to existing compute instances.

### User Actions
1. User navigates to an instance detail page and clicks **“Attach Storage”**.
2. A modal appears prompting volume name, size (GB), and type (SSD/HDD).
3. User submits → frontend sends POST request to `/api/storage/create`.
4. Backend creates a new volume record and associates it with the selected instance.
5. Backend responds with success message and updated volume info.
6. Frontend refreshes the instance page and lists the new attached volume.

### API Triggered
`POST /api/storage/create`

**Request Body**
```json
{
  "instance_id": "i-001",
  "name": "vol-01",
  "size_gb": 50,
  "type": "SSD"
}
```

**Response**
```json
{
  "id": "vol-01",
  "instance_id": "i-001",
  "status": "attached",
  "size_gb": 50,
  "type": "SSD"
}
```

**Diagram Reference:** `storage_attachment_flow.png`

---

## 5. Network Visualization Flow

### Goal
Allow users to view simulated network connections between instances for better visibility of cloud topology.

### User Actions
1. User clicks **“Network View”** on the dashboard.
2. Frontend sends GET request to `/api/network/topology`.
3. Backend retrieves all instance and connection data from the DB.
4. Backend responds with topology graph data in JSON format.
5. Frontend renders a visual network graph using nodes (instances) and edges (connections).

### API Triggered
`GET /api/network/topology`

**Response**
```json
{
  "nodes": [
    {"id": "i-001", "label": "Instance 1"},
    {"id": "i-002", "label": "Instance 2"}
  ],
  "connections": [
    {"from": "i-001", "to": "i-002", "latency": 20, "bandwidth": 100}
  ]
}
```

**Diagram Reference:** `network_visualization_flow.png`

---

## 6. Bandwidth Adjustment Flow

### Goal
Allow admin users to modify simulated bandwidth or latency between instances to test network performance.

### User Actions
1. Admin opens the **Network Settings** panel.
2. Selects a connection and enters new bandwidth or latency values.
3. Frontend sends PUT request to `/api/network/update` with updated configuration.
4. Backend validates and updates the corresponding network record in DB.
5. Response confirms the modification and triggers a visual graph update.

### API Triggered
`PUT /api/network/update`

**Request Body**
```json
{
  "connection_id": "conn-01",
  "bandwidth": 200,
  "latency": 10
}
```

**Response**
```json
{
  "connection_id": "conn-01",
  "status": "updated",
  "bandwidth": 200,
  "latency": 10
}
```

**Diagram Reference:** `bandwidth_adjustment_flow.png`

---
# Epic 3: Monitoring & Metrics Visualization

## 7. Instance Metrics Retrieval Flow

### Goal
Enable users to view live CPU, RAM, and network metrics for simulated instances in the CloudSim dashboard.

### User Actions
1. User opens the **Monitoring tab** on the dashboard.
2. Frontend sends GET request to `/api/metrics/{instance_id}`.
3. Backend retrieves latest simulated performance data from DB or cache.
4. Backend responds with JSON data containing metrics for CPU, memory, and network I/O.
5. Frontend renders charts updating every 5 seconds through WebSocket feed.

### API Triggered
`GET /api/metrics/{instance_id}`

**Response**
```json
{
  "instance_id": "i-001",
  "cpu": 35.6,
  "memory": 2048,
  "network_in": 150,
  "network_out": 120,
  "timestamp": "2025-11-04T15:00:00Z"
}
```

**WebSocket Endpoint**
`/ws/metrics/{instance_id}`  
Used for pushing real-time metric updates to the frontend every 5 seconds.

**Diagram Reference:** `metrics_retrieval_flow.png`

---

## 8. Threshold Alert Flow

### Goal
Notify users when simulated resource usage exceeds predefined thresholds.

### User Actions
1. User configures alert thresholds for CPU, memory, or network via **Alert Settings** panel.
2. Frontend sends POST request to `/api/alerts/set` with chosen metrics and limits.
3. Backend stores thresholds in DB and monitors metrics asynchronously.
4. When a threshold is exceeded, backend emits alert event through WebSocket.
5. Frontend displays red alert badge and sends optional toast notification.

### API Triggered
`POST /api/alerts/set`

**Request Body**
```json
{
  "instance_id": "i-001",
  "cpu_threshold": 80,
  "memory_threshold": 4096
}
```

**Response**
```json
{
  "status": "configured",
  "message": "Alert thresholds saved successfully"
}
```

**Alert Event Payload (WebSocket)**
```json
{
  "instance_id": "i-001",
  "metric": "cpu",
  "value": 92.3,
  "status": "alert_triggered"
}
```

**Diagram Reference:** `threshold_alert_flow.png`

---

## 9. Metrics Export Flow

### Goal
Allow users to export historical performance data as CSV for offline analysis.

### User Actions
1. User clicks **“Export Metrics”** on the Monitoring page.
2. Frontend sends GET request to `/api/metrics/export?instance_id={id}`.
3. Backend aggregates metric logs from DB and formats them as CSV.
4. Backend returns downloadable file response.
5. Frontend triggers browser download of the CSV file.

### API Triggered
`GET /api/metrics/export`

**Query Example**
`/api/metrics/export?instance_id=i-001&range=1h`

**Response (CSV Content Example)**
```
timestamp,cpu,memory,network_in,network_out
2025-11-04T15:00:00Z,25.6,2048,120,100
2025-11-04T15:05:00Z,35.2,2200,140,120
```

**Diagram Reference:** `metrics_export_flow.png`

---

# Epic 4: System Management & Configuration

## 10. User Management Flow

### Goal
Allow administrators to add, update, or remove user accounts within CloudSim.

### User Actions
1. Admin navigates to the **User Management** page.
2. Admin clicks **"Add User"** and enters username, role, and permissions.
3. Frontend sends POST request to `/api/users/create`.
4. Backend validates data, sores user record in DB, and returns confirmation.
5. Frontend updates the user list dynamically.

### API Triggered
`POST /api/users/create`

**Request Body**
```json
{
    "username": "tinh",
    "email": "tinh@cloudsim.com",
    "role": "devops"
}
```

**Response**
```json
{
    "user_id": "u-001",
    "status": "created",
    "message": "User successfully added"
}
```

**Diagram Reference:** `user_management_flow.png`

---

## 11. Resource Limit Configuration Flow

### Goal
Allow admins to define global limits for simulated compute, storage, and network resrouces.

### User Actions
1. Admin opens **System Settings** and selects **Resource Limits** tab.
2. Inputs max CPU, storage, and network usage values.
3. Frontend sends PUT request to `/api/config/resources`.
4. Backend updates global configuration table in DB.
5. Confirmation message appears with updated limits displayed.

### API Triggered
`PUT /api/config/resources`

**Request Body**
```json
{
    "max_cpu": 128,
    "max_storage_gb": 5000,
    "max_network_mbps": 1000
}

**Response**
```json
{
    "status": "updated",
    "message": "Global resource limits applied"
}
```

**Diagram Reference:** `resource_limit_flow.png`

---

## 12. System Parameter Adjustment Flow

### Goal
Allow DevOps engineers to modify backend orchestration parameters (e.g., scheduling interval, instance refresh rate).

### User Actions
1. DevOps navigates to **Configuration Panel -> Orchestration Setting**.
2. Adjusts parameters such as job interval or max concurrent simulations.
3. Frontend sends PATCH request to `/api/config/orchestration`.
4. Backend updates configuration file or DB and reloads parameters in memory.
5. Success message returned to frontend.

### API Triggered
`PATCH /api/config/orchestration`

**Request Body**
```json
{
    "scheduler_interval": 15,
    "max_concurrent_jobs": 10
}
```

**Request Response**
```json
{
    "stuatus": "ok",
    "message": "Orchestration configuration updated"
}
```

**Diagram Reference:** `orchestration_config_flow.png`

---


---

## Summary
These flows define how users interact with the system during key operations.  
Each action follows the **request → backend logic → database update → UI refresh** pattern, forming the backbone of CloudSim’s interactive simulation experience.
