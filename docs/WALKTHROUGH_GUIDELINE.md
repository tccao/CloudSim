# CloudSim Walkthrough Guideline

Use this guide to demo or review the finished CloudSim app in production mode.

## Audience

This walkthrough is written for instructors, reviewers, teammates, and portfolio viewers who need to understand what the app does without reading the code first.

## Preflight

Before starting the walkthrough, confirm:

- Frontend URL loads over HTTPS.
- Backend health returns `{"status":"healthy"}` at `/health`.
- Backend `ALLOWED_ORIGINS` includes the exact frontend URL.
- Frontend was built with `VITE_API_URL` pointing to the backend URL.
- An admin account exists through backend bootstrap or admin-created credentials.
- `CLOUDSIM_AWS_BACKEND` is set intentionally:
  - `mock` for a safe public demo.
  - `live` for real AWS EC2, CloudWatch, and Cost Explorer.

Optional command check:

```bash
BACKEND_URL=https://<your-backend-service>.onrender.com \
FRONTEND_URL=https://<your-frontend-domain>.vercel.app \
SMOKE_AUTH=1 \
./scripts/smoke_deployment.sh
```

## Demo Path

### 1. Open The App

Open the Vercel frontend URL. The first screen should be the CloudSim login modal. Explain that the frontend is a Vite static build and the API URL is baked in through `VITE_API_URL`.

Reference screenshots:

- `docs/images/user/01-login-empty.png`
- `docs/images/user/02-login-credentials.png`

### 2. Sign In

Sign in as an existing user. After login, the top bar shows the user email and role badge. The dashboard loads through `GET /api/ec2/instances`.

What to call out:

- Passwords are verified server-side with bcrypt.
- The backend returns a JWT bearer token.
- The frontend Axios client attaches the token to later requests.
- The backend revalidates the current user on every protected route.

### 3. Dashboard Overview

Show the account overview cards and instance table.

What to call out:

- Admin and DevOps users can see all instances.
- Standard users only see instances they created.
- The dashboard actions call backend lifecycle endpoints, not local-only state.
- In mock mode, instance state is stored in PostgreSQL.
- In live mode, actions call AWS EC2 through boto3.

Reference screenshots:

- `docs/images/user/03-dashboard-empty.png`
- `docs/images/user/07-dashboard-instance-running.png`
- `docs/images/admin/01-dashboard-all-instances.png`

### 4. Launch An Instance

Click `Launch Instance` and walk through the four-step wizard:

1. Name and AMI.
2. Instance type.
3. VPC, subnet, security group, public IP, storage.
4. Review and launch.

What to call out:

- Launch options come from `/api/ec2/launch-options`.
- New instances are tagged or stored with CloudSim ownership metadata.
- `t2.*` instance types are intentionally constrained for cost control.
- Mock mode is safe for public demos because it does not call AWS.

Reference screenshots:

- `docs/images/user/04-launch-step1-name-ami.png`
- `docs/images/user/05-launch-step2-instance-type.png`
- `docs/images/user/06-launch-step4-review.png`

### 5. Instance Details

Click an instance name from the dashboard and review the details page tabs:

- Details
- Security
- Networking
- Storage
- Tags

What to call out:

- Details are fetched from `GET /api/ec2/instances/{instance_id}`.
- Security groups, VPC/subnet, DNS, EBS volume, and tags are shown in separate tabs.
- Action buttons reuse the same protected lifecycle endpoints as the dashboard.

Reference screenshots:

- `docs/images/user/08-instance-details-tab.png`
- `docs/images/user/09-instance-security-tab.png`
- `docs/images/user/10-instance-networking-tab.png`
- `docs/images/user/11-instance-storage-tab.png`
- `docs/images/user/12-instance-tags-tab.png`

### 6. Monitoring

Open the Monitoring tab, select an instance, and switch between CPU, memory, network, disk, and cost tabs.

What to call out:

- CPU, network, and disk data come from CloudWatch in live mode.
- Mock mode produces synthetic time-series data for demos.
- Metric datapoints are persisted into the `metrics` table idempotently.
- Memory and some log-style panels are presentation placeholders for future CloudWatch Agent or Logs integration.
- Cost summaries come from Cost Explorer in live mode when enabled, or mock estimates in demo mode.

Reference screenshots:

- `docs/images/user/13-monitoring-cpu.png`
- `docs/images/user/14-monitoring-memory.png`
- `docs/images/user/15-monitoring-network.png`
- `docs/images/user/16-monitoring-disk.png`

### 7. IAM And Settings

Open `IAM & Settings`.

For Admin:

- Show the current user card.
- Show the user management table.
- Create a new user with a selected role.
- Explain that admin bootstrap is backend-only and never exposed through Vite.

For DevOps Engineer:

- Show that user management is hidden.
- Show operational settings that DevOps can view or adjust in the UI.

For User:

- Show read-oriented role permissions and disabled advanced settings.

Reference screenshots:

- `docs/images/admin/02-iam-user-management.png`
- `docs/images/admin/03-add-new-user-modal.png`
- `docs/images/admin/04-user-created-success.png`
- `docs/images/deng/04-iam-settings-overview.png`
- `docs/images/user/17-iam-settings-overview.png`
- `docs/images/user/18-iam-settings-advanced.png`

### 8. Role Isolation

To demonstrate isolation, log out and log in as a different standard user. The dashboard should show only that user's own instances.

What to call out:

- The UI reflects role state, but the backend enforces the actual permissions.
- A user cannot view or manage another user's instance through direct API calls.
- Admin and DevOps have cross-user operational visibility.

Reference screenshot:

- `docs/images/user/19-user2-dashboard.png`

## Reviewer Script

Use this short version when time is limited:

1. Login and show the role badge.
2. Open the dashboard and refresh the instance list.
3. Launch a mock instance through the four-step wizard.
4. Open details and show the five instance tabs.
5. Open monitoring and show CPU/network/disk charts.
6. Open IAM as Admin and create a user.
7. Explain `mock` versus `live` backend mode and the Vercel + Render deployment shape.

## Documentation Cross-References

- Architecture: [Architecture_Diagram.md](Architecture_Diagram.md)
- Deployment: [deployment/PRODUCTION_DEPLOYMENT.md](deployment/PRODUCTION_DEPLOYMENT.md)
- Roles: [ROLES_REFERENCE.md](ROLES_REFERENCE.md)
- Database: [Database_Schema.md](Database_Schema.md)
- User journeys: [user-journeys/](user-journeys/)
