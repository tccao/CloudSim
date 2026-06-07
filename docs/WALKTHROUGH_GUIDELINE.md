# CloudSim Production Walkthrough

Use this guide to demo or review the final CloudSim production app. The
recommended public-demo configuration is the Vercel frontend, Render FastAPI
backend, Render PostgreSQL, and `CLOUDSIM_AWS_BACKEND=mock`.

## What Is Live In The Demo

| Surface | Final Behavior |
| :--- | :--- |
| Login, registration, session validation | API-backed |
| Instance table and lifecycle actions | API-backed |
| Launch options and instance creation | API-backed |
| Instance details | API-backed |
| CPU, network, and disk monitoring | API-backed; metric history is persisted |
| Cost charts | API-backed in mock/live mode, but the UI falls back to static demo values if the request fails |
| Admin user list, create, delete | API-backed |
| Admin role/status update | Backend API exists; current UI does not expose it |
| Dashboard alarms, zone health, resource summary | Presentation-only static data |
| Monitoring memory, system logs, export | Presentation-only |
| IAM audit logs and advanced settings | Presentation-only; changes are not persisted |

## Preflight

Confirm before presenting:

- Frontend URL loads over HTTPS.
- `GET <backend-url>/health` returns a healthy response.
- `ALLOWED_ORIGINS` includes the exact frontend origin.
- The Vercel build uses the correct `VITE_API_URL`.
- An Admin account exists through backend bootstrap or an existing Admin.
- `CLOUDSIM_AWS_BACKEND` is intentionally set to `mock` or `live`.
- For live mode, AWS credentials, permissions, region, Cost Explorer flag, and
  optional role mapping have been validated.
- For an honest cost demo, verify the cost requests succeed in browser network
  tools; the monitoring UI otherwise uses fallback demo values.

Optional deployment check:

```bash
BACKEND_URL=https://<your-backend-service>.onrender.com \
FRONTEND_URL=https://<your-frontend-domain>.vercel.app \
SMOKE_AUTH=1 \
./scripts/smoke_deployment.sh
```

## Recommended Demo Path

### 1. Open The Production App

Open the Vercel frontend URL. Explain:

- Vercel serves the static React/Vite bundle.
- The browser calls the Render FastAPI URL directly.
- `VITE_API_URL` is public build-time configuration; backend secrets never
  belong in Vite variables.

Reference screenshots:

- `docs/images/user/01-login-empty.png`
- `docs/images/user/02-login-credentials.png`

### 2. Register Or Sign In

The login modal supports both sign-in and public registration. Public
registration always creates a standard `User`.

After sign-in, point out the email and role badge. Explain:

- The backend verifies bcrypt password hashes.
- Login returns an expiring JWT stored in browser `localStorage`.
- The JWT contains the email subject, while the current role is reloaded from
  PostgreSQL on every protected request.
- The shared Axios client attaches the bearer token and clears it after a `401`.

### 3. Show The Dashboard

The instance table and its refresh/start/stop/reboot/terminate actions are
API-backed through `/api/ec2/instances`.

Explain:

- Admin and DevOps Engineer accounts see all returned instances.
- User accounts see only owned instances.
- Mock mode stores virtual instance state in PostgreSQL and never calls AWS.
- Live mode sends lifecycle operations to EC2 through boto3.

Be explicit that the alarms, availability-zone health, and resource-usage
summary cards below the table are presentation-only static data.

Reference screenshots:

- `docs/images/user/03-dashboard-empty.png`
- `docs/images/user/07-dashboard-instance-running.png`
- `docs/images/admin/01-dashboard-all-instances.png`

### 4. Launch An Instance

Click `Launch Instance` and show the four steps:

1. Name and AMI.
2. Instance type.
3. VPC, subnet, security group, public IP, and storage.
4. Review and launch.

Explain:

- The wizard requests options from `/api/ec2/launch-options`.
- The backend restricts launches to the supported `t2.*` types.
- All authenticated roles can launch.
- Ownership is recorded with `created_by_user_id` in mock mode and
  `CreatedBy=<user_id>` tags in live mode.
- Mock launch is safe for a public demo; live launch creates a real billable EC2
  instance and EBS volume.

Reference screenshots:

- `docs/images/user/04-launch-step1-name-ami.png`
- `docs/images/user/05-launch-step2-instance-type.png`
- `docs/images/user/06-launch-step4-review.png`

### 5. Inspect Instance Details

Click an instance name and show:

- Details
- Security
- Networking
- Storage
- Tags

Explain that `GET /api/ec2/instances/{instance_id}` returns the normalized
detail contract in both modes. The action buttons call the same protected
lifecycle endpoints used by the dashboard.

Reference screenshots:

- `docs/images/user/08-instance-details-tab.png`
- `docs/images/user/09-instance-security-tab.png`
- `docs/images/user/10-instance-networking-tab.png`
- `docs/images/user/11-instance-storage-tab.png`
- `docs/images/user/12-instance-tags-tab.png`

### 6. Show Monitoring And Costs

Open Monitoring, select an instance, change the time period, and refresh.

API-backed behavior:

- CPU, network, disk read, and disk write series come from the selected backend.
- Mock mode generates deterministic synthetic series.
- Live mode reads EC2 metrics from CloudWatch.
- Metric history responses are written idempotently to the PostgreSQL `metrics`
  table.
- Mock costs are estimates based on visible mock instances.
- Live costs come from Cost Explorer only when `ENABLE_COST_EXPLORER=true`.

Presentation-only behavior:

- Memory chart and system logs are static examples.
- Export has no implemented action.
- The UI uses static fallback cost values if cost requests fail.

Reference screenshots:

- `docs/images/user/13-monitoring-cpu.png`
- `docs/images/user/14-monitoring-memory.png`
- `docs/images/user/15-monitoring-network.png`
- `docs/images/user/16-monitoring-disk.png`

### 7. Show IAM And Settings As Admin

Open `IAM & Settings`.

API-backed behavior:

- Current user card reflects `/api/auth/me`.
- Admin sees the user table from `GET /api/admin/users`.
- Admin can create a user with a selected role.
- Admin can delete another user.
- The backend API also supports role and active-status updates, although the
  current UI does not expose those controls.

Presentation-only behavior:

- Recent audit logs are labeled mock data.
- Resource quotas, auto scaling, and notification settings are not persisted.
- DevOps Engineer and User accounts do not see Admin user management.

Reference screenshots:

- `docs/images/admin/02-iam-user-management.png`
- `docs/images/admin/03-add-new-user-modal.png`
- `docs/images/admin/04-user-created-success.png`
- `docs/images/deng/04-iam-settings-overview.png`
- `docs/images/user/17-iam-settings-overview.png`
- `docs/images/user/18-iam-settings-advanced.png`

### 8. Prove Role Isolation

Log out and sign in as a different standard User. Show that the instance list
contains only that account's resources.

Explain:

- Frontend visibility improves the experience, but FastAPI enforces permissions.
- Direct requests for another user's details, lifecycle actions, or metrics
  receive `403`.
- Admin and DevOps Engineer have cross-user operational access.
- In optional live role-based mode, IAM policies add a second authorization
  boundary through STS AssumeRole.

Reference screenshot:

- `docs/images/user/19-user2-dashboard.png`

### 9. Close With The Production Architecture

Open [Architecture_Diagram.md](Architecture_Diagram.md) and summarize:

1. Vercel serves the static frontend.
2. The browser sends bearer-authenticated HTTPS requests directly to Render.
3. FastAPI reloads users/roles from PostgreSQL and enforces RBAC.
4. The service facade selects PostgreSQL-backed mock behavior or live boto3.
5. PostgreSQL stores users, instance metadata/ownership, and metric snapshots.
6. GitHub Actions validates tests, builds, Compose, and Docker images.

## Five-Minute Reviewer Script

1. Sign in and show the role badge.
2. Refresh the API-backed instance table and perform one lifecycle action.
3. Launch a mock instance through the four-step wizard.
4. Open details and show the normalized detail tabs.
5. Open monitoring and distinguish API-backed charts from presentation panels.
6. Open IAM as Admin and create or delete a user.
7. Explain role isolation and the mock/live production architecture.

## Final Validation Checklist

- Login and optional public registration work.
- Refreshing the page restores and validates the stored session.
- Admin and DevOps Engineer see all instances; User sees owned instances only.
- Launch, details, start, stop, reboot, and terminate call the backend.
- Monitoring CPU/network/disk requests succeed and persist datapoints.
- Mock/live and presentation-only surfaces are described accurately.
- Admin can list, create, and delete users in the UI.
- Non-Admin calls to `/api/admin/users` return `403`.
- `/health`, CORS, and deployed API URL are correct.

## Related Documentation

- [Architecture](Architecture_Diagram.md)
- [Roles](ROLES_REFERENCE.md)
- [Deployment](deployment/PRODUCTION_DEPLOYMENT.md)
- [Database](Database_Schema.md)
- [User journeys](user-journeys/)
