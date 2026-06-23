# CloudSim Database Schema

## Entity Relationship Diagram

```mermaid
erDiagram
    USERS {
        int         id                PK "auto-increment"
        varchar     email             UK "login identity"
        varchar     hashed_password      "bcrypt hash"
        varchar     role                 "Admin | DevOps Engineer | User"
        boolean     is_active            "default true"
        timestamp   created_at           "UTC, set on insert"
    }

    INSTANCES {
        varchar     instance_id       PK "AWS EC2 instance ID"
        varchar     name                 "Name tag"
        varchar     instance_type        "e.g. t2.micro"
        varchar     state                "pending | running | stopped | terminated"
        varchar     public_ip            "nullable"
        varchar     private_ip           "nullable"
        varchar     availability_zone    "nullable"
        timestamp   launch_time          "nullable, from AWS"
        timestamp   last_synced          "UTC, updated on each sync"
        int         created_by_user_id   FK "references USERS.id"
    }

    METRICS {
        int         id                PK "auto-increment"
        varchar     instance_id          "AWS EC2 instance ID, indexed"
        varchar     metric_name          "CPUUtilization | NetworkIn | NetworkOut | DiskReadOps | DiskWriteOps"
        float       value                "numeric reading"
        varchar     unit                 "Percent | Bytes | Count"
        timestamp   recorded_at          "CloudWatch timestamp"
        timestamp   collected_at         "when CloudSim wrote the row"
    }

    USERS ||--o{ INSTANCES : "creates"
    INSTANCES ||--o{ METRICS : "produces"
```

> **Note:** `created_by_user_id` is enforced at the application layer, not as a database-level foreign key constraint. This is intentional — if a user is deleted, their historical instance records are preserved.

---

## Overview

CloudSim uses PostgreSQL as its primary application database. The database supports three core concerns:

- authentication through locally stored user accounts
- authorization through role values attached to each user
- local tracking of EC2 instance metadata that the application syncs from AWS
- local persistence of CloudWatch metric snapshots for historical replay

The current backend ORM defines three application tables:

- `users`
- `instances`
- `metrics`

The backend source of truth is the SQLAlchemy model layer in [backend/app/models.py](/home/tinhc/CloudSim/backend/app/models.py). This document exists as a standalone schema specification so engineers can understand the data model without reverse-engineering the ORM.

## Role Model

CloudSim currently supports three application roles. These roles are stored directly as string values in the `users.role` column. There is no separate `roles` table or permissions matrix table at this stage.

### `Admin`

Admins have full access to the application. They can manage users through the admin API and can perform all EC2 operations.

### `DevOps Engineer`

DevOps Engineers can perform EC2 lifecycle operations and view all instances, but they cannot use the admin user-management endpoints.

### `User`

Users are limited to their own resources. Instance access is filtered by application logic using ownership metadata such as `created_by_user_id` or AWS tagging.

## Table Definitions

### `users`

Purpose: store application accounts used for login, authorization, and admin-controlled user management.

| Column | Type | Nullable | Default | Constraints | Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | integer | No | auto-increment | Primary key, indexed | Internal user identifier |
| `email` | string / varchar | No | None | Unique, indexed | Login identity and primary lookup field |
| `hashed_password` | string / varchar | No | None | Must store a bcrypt hash | Password digest, never plaintext |
| `role` | string / varchar | No | `User` | Valid values: `Admin`, `DevOps Engineer`, `User` | Authorization level |
| `is_active` | boolean | No | `true` | None | Soft-enable or disable an account |
| `created_at` | datetime / timestamp | No | current UTC time in ORM | None | Account creation time |

Behavior notes:

- `email` is the unique login field used during authentication.
- `hashed_password` is checked during `/api/auth/login`.
- `role` is consulted by both admin routes and EC2 routes to decide access.
- `is_active` allows an account to be disabled without deleting it.

### `instances`

Purpose: store a local representation of EC2 instances so the application can cache AWS metadata and apply user-specific visibility rules.

| Column | Type | Nullable | Default | Constraints | Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `instance_id` | string / varchar | No | None | Primary key, indexed | AWS EC2 instance ID |
| `name` | string / varchar | Yes | None | None | Name tag or local display name |
| `instance_type` | string / varchar | No | None | None | EC2 instance class such as `t2.micro` |
| `state` | string / varchar | No | `pending` | None | Current lifecycle state |
| `public_ip` | string / varchar | Yes | None | None | Public IPv4 address if assigned |
| `private_ip` | string / varchar | Yes | None | None | Private IPv4 address |
| `availability_zone` | string / varchar | Yes | None | None | AWS availability zone |
| `launch_time` | datetime / timestamp | Yes | None | None | Original EC2 launch timestamp |
| `last_synced` | datetime / timestamp | No | current UTC time in ORM | None | Last application sync from AWS |
| `created_by_user_id` | integer | Yes | None | Application metadata only | CloudSim user associated with creation |

Behavior notes:

- `instance_id` is the durable external identifier, so it is used as the table primary key.
- The table is not meant to replace AWS as the source of truth for infrastructure.
- `created_by_user_id` helps the app decide which `User` accounts can manage an instance.
- A composite index on `(state, last_synced)` accelerates dashboard queries that filter by state and order by recency.

### `metrics`

Purpose: persist CloudWatch metric snapshots so the application can avoid repeated AWS calls for historical reads and build a long-term performance dataset.

| Column | Type | Nullable | Default | Constraints | Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | integer | No | auto-increment | Primary key | Internal row identifier |
| `instance_id` | string / varchar | No | None | Indexed | EC2 instance the reading belongs to |
| `metric_name` | string / varchar | No | None | None | `CPUUtilization`, `NetworkIn`, `NetworkOut`, `DiskReadOps`, `DiskWriteOps` |
| `value` | float | No | None | None | Numeric reading |
| `unit` | string / varchar | Yes | None | None | `Percent`, `Bytes`, `Count` |
| `recorded_at` | datetime / timestamp | No | None | None | Timestamp from CloudWatch (when AWS measured it) |
| `collected_at` | datetime / timestamp | No | current UTC time in ORM | None | When CloudSim wrote the row (audit trail) |

Behavior notes:

- Rows are written as a side effect of `GET /api/ec2/instances/{id}/metrics`.
- A composite index on `(instance_id, metric_name, recorded_at)` makes time-windowed queries fast.
- Insertion is idempotent: if a row with the same `instance_id + metric_name + recorded_at` already exists, the new datapoint is skipped — safe to re-fetch the same metric window without duplicating data.

## Constraints and Rules

### Database-level constraints

- `users.id` is the primary key.
- `users.email` is unique.
- `instances.instance_id` is the primary key.
- `metrics.id` is the primary key.
- `users.role` is constrained to `Admin`, `DevOps Engineer`, or `User` in the PostgreSQL recreation script and ORM check constraint.
- Composite index `ix_instances_state_synced` on `instances(state, last_synced)`.
- Composite index `ix_metrics_instance_name_recorded` on `metrics(instance_id, metric_name, recorded_at)`.

### Application rules

- `hashed_password` must always store bcrypt hashes.
- `created_by_user_id` is application-owned metadata and is not currently enforced as a foreign key by the ORM.
- Admin-only behavior is enforced in route dependencies, not through relational permissions.
- Instance visibility and control rules are enforced in application logic, not through row-level security.

## Seed And Bootstrap Data

Production does not ship with hard-coded users. The backend can optionally
bootstrap one admin account from environment variables during startup:

```text
CLOUDSIM_BOOTSTRAP_ADMIN_ENABLED=true
CLOUDSIM_BOOTSTRAP_ADMIN_EMAIL=<admin-email>
CLOUDSIM_BOOTSTRAP_ADMIN_PASSWORD=<strong-secret-password>
```

The startup bootstrap creates the user if missing, restores `role=Admin` and
`is_active=true` for an existing user, and preserves the existing password
unless `CLOUDSIM_BOOTSTRAP_ADMIN_RESET_PASSWORD=true`.

Local development can still use `backend/scripts/recreate_seed_database.py` for
demo walkthrough accounts, but that script is blocked when
`CLOUDSIM_ENVIRONMENT=production`.

## Detailed Walkthrough

The `users` table exists because CloudSim uses first-party authentication instead of delegating all identity management to AWS or an external identity provider. A user signs in with an email and password. During login, the backend looks up `users.email`, checks the submitted password against `users.hashed_password`, and then issues a JWT. That means this table is the root of the entire auth flow: if the row is missing, inactive, or assigned the wrong role, the rest of the application behaves differently immediately.

The `role` column is the second key part of the design. CloudSim keeps authorization intentionally simple by using a single string column instead of normalized roles and permissions tables. That choice keeps local development and debugging easy. When the current user hits an admin route, the backend checks whether `role == "Admin"`. When the user accesses EC2 endpoints, route logic treats `Admin` and `DevOps Engineer` as broader-access roles and treats `User` as a restricted role. Because the role is embedded directly on the user row, changing one value can immediately change what the frontend and backend permit.

The `instances` table exists for a different reason. CloudSim interacts with AWS, but it still needs a local view of instances so it can display them efficiently and track application-specific ownership metadata. The application stores fields like instance type, state, IPs, launch time, and sync time locally. That gives the frontend a stable contract while the backend refreshes data from AWS as needed.

The most important application-owned field on the `instances` table is `created_by_user_id`. It is not modeled as a foreign key today, but it still matters because the app uses it as part of ownership and visibility decisions. In practice, this lets CloudSim answer questions like “which instances belong to this regular user?” without needing a separate join table or a more complex policy engine.

Just as important is what the schema does not model yet. There is no separate `roles` table, no normalized permissions schema, no audit log tables, no database migration framework in the current code, and no strict foreign-key enforcement between `instances.created_by_user_id` and `users.id`. Those omissions are intentional for now. The current schema favors clarity and development speed over deeper normalization.

## Recreation Workflow

CloudSim now has two recommended recreation paths.

### SQL recreation

Use SQL when you want a direct PostgreSQL schema reset, especially if you are operating from `psql`. The SQL script is schema-only and intentionally does not seed users.

Recommended command:

```bash
psql -U postgres -d cloudsim -f backend/sql/recreate_cloudsim_schema.sql
```

Verification query:

```sql
SELECT email, role, is_active
FROM users
ORDER BY id;
```

### Python recreation

Use the Python script when you want the database rebuild to stay aligned with backend ORM behavior and password hashing logic. This is the preferred developer workflow because it creates tables through SQLAlchemy and hashes seed passwords through the backend auth module.

Recommended command:

```bash
cd backend
env -u DEBUG ENVIRONMENT=development DEBUG=true SECRET_KEY=dev-secret-key \
  .venv/bin/python scripts/recreate_seed_database.py --drop-existing
```

Expected output:

```text
CloudSim database recreation complete.
- admin@gmail.com -> Admin
- devops@gmail.com -> DevOps Engineer
- deng@gmail.com -> DevOps Engineer
- user@gmail.com -> User
```

### Choosing between them

- Use SQL when you need a simple schema reset from a database shell.
- Use Python when you want development demo users and the recreation path to follow the backend’s models and auth utilities.
- Prefer the Python path during ongoing development.
