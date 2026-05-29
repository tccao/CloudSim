# CloudSim Production Deployment

This guide deploys CloudSim as two services:

- Backend API: Docker web service on Render
- Frontend UI: Vite static app on Vercel
- Database: Managed PostgreSQL

This split keeps the backend close to PostgreSQL and lets the frontend use a CDN.

## 1. Preflight

Run these checks from the repository root before deploying:

```bash
cd backend
source venv/bin/activate
python -m pytest

cd ../frontend
npm run lint
npm run test
npm run build

cd ..
docker compose config
docker compose build backend frontend
```

## 2. Backend On Render

Create a PostgreSQL database first. Use the internal database URL for the backend service when both are in the same Render region.

Create a Render web service:

- Runtime: Docker
- Root directory: `backend`
- Dockerfile path: `backend/Dockerfile` if using repository root as the service root, or `Dockerfile` if using `backend` as the root directory
- Health check path: `/health`
- Port: use Render's injected `PORT` environment variable

Render web services need the app to bind to `0.0.0.0`; the backend Dockerfile does this and reads `${PORT:-8000}`.

Set backend environment variables:

```text
CLOUDSIM_ENVIRONMENT=production
CLOUDSIM_DEBUG=false
DATABASE_URL=<render-postgres-internal-url>
SECRET_KEY=<openssl-rand-hex-32-output>
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=https://<your-frontend-domain>
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<your-aws-account-id>
CLOUDSIM_AWS_BACKEND=mock
ENABLE_COST_EXPLORER=false
ENABLE_ROLE_BASED_ACCESS=false
```

`CLOUDSIM_AWS_BACKEND=mock` is the recommended public demo setting. It stores
virtual instances in PostgreSQL and returns synthetic metrics/costs without
calling EC2, CloudWatch, or Cost Explorer. Use `live` only when you intentionally
want CloudSim to manage real AWS resources.

For live AWS role-based access, also set:

```text
CLOUDSIM_AWS_BACKEND=live
ENABLE_ROLE_BASED_ACCESS=true
AWS_ROLE_ADMIN=arn:aws:iam::<account-id>:role/CloudSimAdminRole
AWS_ROLE_DEVOPS=arn:aws:iam::<account-id>:role/CloudSimDevOpsRole
AWS_ROLE_READONLY=arn:aws:iam::<account-id>:role/CloudSimUserRole
```

Only when `CLOUDSIM_AWS_BACKEND=live`, if not using role assumption, set AWS
credentials as provider secrets:

```text
AWS_ACCESS_KEY_ID=<access-key>
AWS_SECRET_ACCESS_KEY=<secret-key>
AWS_SESSION_TOKEN=<optional-session-token>
```

Never commit AWS credentials or production secrets.

## 3. Frontend On Vercel

Create a Vercel project from the same Git repository:

- Root directory: `frontend`
- Install command: `npm ci`
- Build command: `npm run build`
- Output directory: `dist`

Set frontend environment variables:

```text
VITE_API_URL=https://<your-backend-domain>
```

Vite only exposes frontend environment variables that begin with `VITE_`.

After changing `VITE_API_URL`, redeploy the frontend so the value is baked into the static build.

## 4. CORS Checklist

Backend `ALLOWED_ORIGINS` must include the exact frontend URL:

```text
ALLOWED_ORIGINS=https://cloudsim.example.com
```

For multiple origins, use commas:

```text
ALLOWED_ORIGINS=https://cloudsim.example.com,https://cloudsim-preview.vercel.app
```

Do not use a wildcard with credentials enabled.

## 5. Smoke Test

Health-only check:

```bash
BACKEND_URL=https://<your-backend-domain> ./scripts/smoke_deployment.sh
```

Health plus auth check:

```bash
BACKEND_URL=https://<your-backend-domain> \
FRONTEND_URL=https://<your-frontend-domain> \
SMOKE_AUTH=1 \
./scripts/smoke_deployment.sh
```

The auth check creates a unique `User` account, logs in, and calls `/api/auth/me`.

## 6. Rollback

If deployment fails:

1. Roll back the backend service to the previous successful deploy.
2. Roll back the frontend deployment.
3. Confirm `/health` returns `{"status":"healthy"}`.
4. Confirm frontend requests are not blocked by CORS.

Keep database rollback separate from app rollback. Do not reset production data unless you have a backup and a clear restore plan.

## 7. Production Validation

Before marking production complete:

- Backend `/health` returns healthy.
- Frontend loads over HTTPS.
- Register/login works.
- Admin can create users after a controlled admin seed/promotion.
- EC2 list endpoint returns either live data or a clear AWS configuration error.
- Metrics endpoint returns data or a clear AWS configuration error.
- Logs show no repeated auth, CORS, database, or AWS credential errors.
