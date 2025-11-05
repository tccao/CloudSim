# CloudSim – User Flow Documentation

## Overview
This document describes detailed user flows for **resource provisioning**, **scaling**, and **termination** in CloudSim.  
Each flow illustrates the user's interaction from the frontend interface to the backend API, database, and system response.

---

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

## Summary
These flows define how users interact with the system during key operations.  
Each action follows the **request → backend logic → database update → UI refresh** pattern, forming the backbone of CloudSim’s interactive simulation experience.
