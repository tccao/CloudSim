# CloudSim

CloudSim is a production-oriented cloud infrastructure management app with an
AWS-console-style interface. It combines first-party authentication, three
application roles, EC2-style instance lifecycle controls, monitoring, cost
visibility, and admin user management.

The final production topology is a Vite/React static frontend on Vercel, a
Dockerized FastAPI API on Render, and Render PostgreSQL. The backend can run in
safe PostgreSQL-backed mock mode for a public demo or in live mode against AWS
EC2, CloudWatch, Cost Explorer, and optional STS AssumeRole sessions.

## Implemented Scope

| Area | Production Behavior |
| :--- | :--- |
| Authentication | Public registration, email/password login, bcrypt hashes, expiring JWT bearer tokens, disabled-account checks |
| Roles | `Admin`, `DevOps Engineer`, and `User`; the backend reloads the current database user and role on every protected request |
| Instances | List, launch, details, start, stop, reboot, and terminate; standard users are restricted to instances they created |
| Launch Wizard | API-backed AMI, instance type, VPC, subnet, security group, public IP, and root-volume options |
| Monitoring | API-backed CPU, network, and disk metrics; returned datapoints are persisted to PostgreSQL |
| Costs | PostgreSQL-backed estimates in mock mode or Cost Explorer data in live mode when enabled |
| Admin | Admin UI lists, creates, and deletes users; the admin API also supports role/status updates |
| Deployment | Vercel frontend, Render Docker backend, Render PostgreSQL, CORS/security headers, health checks, smoke tests, and CI validation |

Some visible panels are presentation-only in the final UI: dashboard alarms,
zone health, resource-usage summaries, monitoring memory/logs, export, IAM audit
logs, and advanced settings. They do not currently persist changes or call a
production API.

## Production Architecture

```text
Browser
  |-- loads static React app --------------------------> Vercel
  `-- sends HTTPS API requests with a bearer token ---> Render FastAPI
                                                           |
                         +---------------------------------+------------------+
                         |                                                    |
                         v                                                    v
                  Render PostgreSQL                              AWS service facade
                  users / instances / metrics                    |             |
                                                                 v             v
                                                        mock adapter       live boto3
                                                        PostgreSQL         EC2 / CW / CE
                                                                             |
                                                                     optional STS roles
```

Important runtime rules:

- The browser calls the Render API directly; Vercel does not proxy API traffic.
- The JWT contains the user email as its subject. The backend loads the current
  user and role from PostgreSQL for every protected request.
- `CLOUDSIM_AWS_BACKEND=mock` never calls AWS. Virtual instances live in
  PostgreSQL and metrics/costs are generated safely for demos.
- `CLOUDSIM_AWS_BACKEND=live` uses boto3. `ENABLE_ROLE_BASED_ACCESS=true`
  additionally maps CloudSim roles to IAM roles through STS AssumeRole.
- Application RBAC and ownership checks remain enforced by FastAPI in both
  backend modes.

See [docs/Architecture_Diagram.md](docs/Architecture_Diagram.md) for the full
component and request-flow diagram.

## Configuration Modes

| Setting | Behavior |
| :--- | :--- |
| `CLOUDSIM_AWS_BACKEND=mock` | Recommended public production demo; PostgreSQL-backed virtual instances, synthetic metrics, estimated costs, no AWS calls |
| `CLOUDSIM_AWS_BACKEND=live` | Real EC2 lifecycle, CloudWatch metrics, and optional Cost Explorer |
| `ENABLE_ROLE_BASED_ACCESS=false` | Live mode uses the backend service's shared boto3 credential chain |
| `ENABLE_ROLE_BASED_ACCESS=true` | Live mode assumes the IAM role mapped to the current CloudSim role |
| `ENABLE_COST_EXPLORER=false` | Live cost endpoints return a configuration error; mock cost estimates still work |
| `ENABLE_COST_EXPLORER=true` | Live cost endpoints query Cost Explorer |

## Requirements

- Node.js 22+
- Python 3.14+ to match the Dockerfile and CI workflow
- PostgreSQL 15+ for local non-Docker development
- Docker and Docker Compose for the fastest local full-stack run

## Quick Start

### Docker Compose

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- Backend API docs in development mode: http://localhost:8000/docs

Compose starts PostgreSQL, FastAPI, and the built Vite app served by nginx. It
uses `CLOUDSIM_AWS_BACKEND=mock` by default.

To create a local admin during startup:

```bash
export CLOUDSIM_LOCAL_ADMIN_PASSWORD="$(openssl rand -hex 24)"
CLOUDSIM_BOOTSTRAP_ADMIN_ENABLED=true \
CLOUDSIM_BOOTSTRAP_ADMIN_EMAIL=docker-admin@example.com \
CLOUDSIM_BOOTSTRAP_ADMIN_PASSWORD="$CLOUDSIM_LOCAL_ADMIN_PASSWORD" \
docker compose up --build
```

Bootstrap creates the account if missing, or restores `role=Admin` and active
status if it already exists. It preserves an existing password unless
`CLOUDSIM_BOOTSTRAP_ADMIN_RESET_PASSWORD=true`.

### Backend Development

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
export DATABASE_URL="postgresql://postgres:1@localhost:5432/cloudsim"
export CLOUDSIM_AWS_BACKEND=mock
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Local frontend development falls back to `http://localhost:8000`. Vercel builds
must set:

```text
VITE_API_URL=https://<your-backend-service>.onrender.com
```

## Production Deployment

The recommended public production deployment is:

- Frontend: Vercel static deployment from `frontend/dist`
- Backend: Render Docker web service from `backend/Dockerfile`
- Database: Render PostgreSQL
- AWS mode: `CLOUDSIM_AWS_BACKEND=mock`

Use `live` only when the backend has intentionally configured AWS credentials,
IAM permissions, and cost controls. Keep database credentials, JWT secrets, AWS
credentials, and admin bootstrap values on the backend only.

Follow [docs/deployment/PRODUCTION_DEPLOYMENT.md](docs/deployment/PRODUCTION_DEPLOYMENT.md)
for the deployment checklist. Validate a deployment with:

```bash
BACKEND_URL=https://<your-backend-service>.onrender.com \
FRONTEND_URL=https://<your-frontend-domain>.vercel.app \
SMOKE_AUTH=1 \
./scripts/smoke_deployment.sh
```

## Quality Checks

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
```

GitHub Actions runs backend tests, frontend lint/test/build, Compose validation,
and both Docker image builds on pushes and pull requests to `main`.

## Documentation

- [Production Architecture](docs/Architecture_Diagram.md)
- [Production Walkthrough](docs/WALKTHROUGH_GUIDELINE.md)
- [Roles and Permissions](docs/ROLES_REFERENCE.md)
- [Production Deployment](docs/deployment/PRODUCTION_DEPLOYMENT.md)
- [Production Audit](docs/deployment/PRODUCTION_AUDIT.md)
- [Database Schema](docs/Database_Schema.md)
- [Product Requirements / SRS](docs/CloudSim_SRS.md)
- [User Journeys](docs/user-journeys/)
