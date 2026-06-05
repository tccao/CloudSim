# CloudSim Production Deployment

This guide deploys CloudSim with the production hosting split used by the app:

- Frontend UI: Vite static site on Vercel
- Backend API: FastAPI Docker web service on Render
- Database: Render PostgreSQL

The production hardening audit is tracked in [PRODUCTION_AUDIT.md](PRODUCTION_AUDIT.md).

## 1. Preflight

Run these checks from the repository root before deploying. The Docker Compose steps are for local validation only and are not required for Render/Vercel production deployment.

```bash
cd backend
source venv/bin/activate
python -m pytest

cd ../frontend
npm ci
npm run lint
npm run test
npm run build

cd ..
docker compose config
docker compose pull db
docker compose build db backend frontend
docker compose up --build -d
docker compose ps
# Inspect logs while needed:
docker compose logs -f
# Stop and remove containers when finished:
docker compose down
# add -v to remove anonymous volumes if you want a clean reset
```

## 2. Database On Render

Create a Render PostgreSQL database before the backend service.

Use the internal database URL for `DATABASE_URL` when the backend and database are in the same Render region. Keep the external URL only for local admin tools.

## 3. Backend On Render

Create a Render web service:

- Runtime: Docker
- Root directory: `backend`
- Dockerfile path: `Dockerfile` when using `backend` as the service root
- Health check path: `/health`
- Port: Render injects `PORT`; the Dockerfile reads `${PORT:-8000}`

Set backend environment variables:

```text
CLOUDSIM_ENVIRONMENT=production
CLOUDSIM_DEBUG=false
DATABASE_URL=<render-postgres-internal-url>
SECRET_KEY=<openssl-rand-hex-32-output>
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=https://<your-frontend-domain>.vercel.app
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<your-aws-account-id>
CLOUDSIM_AWS_BACKEND=mock
ENABLE_COST_EXPLORER=false
ENABLE_ROLE_BASED_ACCESS=false
CLOUDSIM_BOOTSTRAP_ADMIN_ENABLED=true
CLOUDSIM_BOOTSTRAP_ADMIN_EMAIL=<admin-email>
CLOUDSIM_BOOTSTRAP_ADMIN_PASSWORD=<strong-secret-password>
CLOUDSIM_BOOTSTRAP_ADMIN_RESET_PASSWORD=false
```
Generate a secure secret key and copy it into `SECRET_KEY`:

```bash
openssl rand -hex 32
```

The backend validator enforces a minimum 32-character `SECRET_KEY` in production.

`CLOUDSIM_AWS_BACKEND=mock` is the recommended public demo setting. It stores virtual instances in PostgreSQL and returns synthetic metrics/costs without calling EC2, CloudWatch, or Cost Explorer.

Use `live` only when you intentionally want CloudSim to manage real AWS resources.

For live AWS role-based access, also set:

```text
CLOUDSIM_AWS_BACKEND=live
ENABLE_ROLE_BASED_ACCESS=true
ENABLE_COST_EXPLORER=true
AWS_ROLE_ADMIN=arn:aws:iam::<account-id>:role/CloudSimAdminRole
AWS_ROLE_DEVOPS=arn:aws:iam::<account-id>:role/CloudSimDevOpsRole
AWS_ROLE_READONLY=arn:aws:iam::<account-id>:role/CloudSimUserRole
```

Only when `CLOUDSIM_AWS_BACKEND=live`, if not using role assumption, set AWS credentials as backend service secrets:

```text
AWS_ACCESS_KEY_ID=<access-key>
AWS_SECRET_ACCESS_KEY=<secret-key>
AWS_SESSION_TOKEN=<optional-session-token>
```

Never commit AWS credentials, database URLs, JWT secrets, or admin bootstrap passwords.

## 4. Admin Bootstrap

CloudSim can create or restore the first production admin during backend startup. This is backend-only and must be configured in Render secret environment variables, not in Vite.

Required when bootstrap is enabled:

```text
CLOUDSIM_BOOTSTRAP_ADMIN_ENABLED=true
CLOUDSIM_BOOTSTRAP_ADMIN_EMAIL=<admin-email>
CLOUDSIM_BOOTSTRAP_ADMIN_PASSWORD=<strong-secret-password>
```

Startup behavior is idempotent:

- If the admin email does not exist, CloudSim creates an active `Admin` user.
- If the user exists, CloudSim ensures `role=Admin` and `is_active=true`.
- Existing passwords are preserved unless `CLOUDSIM_BOOTSTRAP_ADMIN_RESET_PASSWORD=true`.
- Passwords and password hashes are never logged.

After the admin is confirmed, you may leave bootstrap enabled to restore the admin role on relaunch, or disable it to stop enforcing that account.

## 5. Frontend On Vercel

Create a Vercel project from the same Git repository:

- Root directory: `frontend`
- Install command: `npm ci`
- Build command: `npm run build`
- Output directory: `dist`

Set frontend environment variables:

```text
VITE_API_URL=https://<your-backend-service>.onrender.com
```

Notes:
- `VITE_API_URL` must point to the Render backend service URL.
- Do not include a trailing slash.
- Vite only exposes environment variables that begin with `VITE_`.
- Do not put admin bootstrap settings, database URLs, JWT secrets, or AWS credentials in the frontend service.

After changing `VITE_API_URL`, redeploy the frontend so the value is baked into the static bundle.

### Optional Frontend Docker Path

The `frontend/Dockerfile` still exists for local Compose and container validation. It builds the Vite app and serves `dist/` through nginx with SPA fallback routing. Pass the API URL as a Docker build argument:

```text
VITE_API_URL=https://<your-backend-service>.onrender.com
```

## 6. CORS Checklist

Backend webapp `ALLOWED_ORIGINS` must include the exact frontend URL:

```text
ALLOWED_ORIGINS=https://<your-frontend-domain>.vercel.app
```

If you use Vercel preview deployments, include them as well:

```text
ALLOWED_ORIGINS=https://<your-frontend-domain>.vercel.app,https://<preview-domain>.vercel.app
```

Do not use a wildcard (`*`) when `allow_credentials=True`.

If authentication appears to fail after a successful backend response, the most likely cause is a mismatched frontend origin in `ALLOWED_ORIGINS`.

## 7. Smoke Test

Health-only check:

```bash
BACKEND_URL=https://<your-backend-service>.onrender.com ./scripts/smoke_deployment.sh
```

Health plus auth check:

```bash
BACKEND_URL=https://<your-backend-service>.onrender.com \
FRONTEND_URL=https://<your-frontend-domain>.vercel.app \
SMOKE_AUTH=1 \
./scripts/smoke_deployment.sh
```

The auth check creates a unique `User` account, logs in, and calls `/api/auth/me`. When `SMOKE_ADMIN_EMAIL` and `SMOKE_ADMIN_PASSWORD` are provided, the script also cleans up the smoke user through the admin API.

Admin bootstrap/admin API check:

```bash
BACKEND_URL=https://<your-backend-service>.onrender.com \
SMOKE_ADMIN_CHECK=1 \
SMOKE_ADMIN_EMAIL=<admin-email> \
SMOKE_ADMIN_PASSWORD=<admin-password> \
./scripts/smoke_deployment.sh
```

## 8. Rollback

If deployment fails:

1. Roll back the backend service to the previous successful deploy.
2. Roll back the Vercel frontend deploy.
3. Confirm `/health` returns `{"status":"healthy"}`.
4. Confirm frontend requests are not blocked by CORS.

Keep database rollback separate from app rollback. Do not reset production data unless you have a backup and a clear restore plan.

## 9. Production Validation

Before marking production complete:

- Backend `/health` returns healthy.
- Frontend loads over HTTPS.
- Frontend API calls use the deployed backend URL.
- Register/login works.
- Admin bootstrap has created or restored the configured admin account.
- Admin can create users through `/api/admin/users`.
- Dashboard lists mock or live instances according to `CLOUDSIM_AWS_BACKEND`.
- Launch wizard can create an instance in the selected mode.
- Instance details tabs render data.
- Monitoring renders metrics and persists datapoints.
- Logs show no repeated auth, CORS, database, or AWS credential errors.
