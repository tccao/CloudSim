# CloudSim

CloudSim is a production-ready full-stack cloud infrastructure management app. It gives users an AWS-console-style workflow for authentication, role-based access, EC2-style instance launch and lifecycle control, instance details, monitoring charts, cost visibility, and admin user management.

The app is built with a Vite React frontend, a FastAPI backend, PostgreSQL, and a switchable AWS service layer. In production the Vite frontend is hosted on Vercel, while the backend runs as a Render Docker web service connected to Render PostgreSQL.

## Features

| Area | What CloudSim Provides |
| :--- | :--- |
| Authentication | Email/password login, bcrypt password hashes, JWT bearer tokens, disabled-account checks |
| Roles | `Admin`, `DevOps Engineer`, and `User` RBAC enforced by the backend |
| Instances | Launch, list, view details, start, stop, reboot, and terminate EC2-style instances |
| Launch Wizard | AMI, instance type, VPC, subnet, security group, public IP, and root volume options |
| Monitoring | CPU, network, and disk metrics from CloudWatch or mock data; metrics persisted to PostgreSQL |
| Costs | Daily and monthly cost summaries through Cost Explorer or mock estimates |
| Admin Tools | Admin-only user list, create, update, deactivate, and delete flows |
| Production Mode | Vercel frontend, Render backend/PostgreSQL, health checks, smoke test script, security headers, CORS config |

## Architecture

CloudSim has four main runtime layers:

- `frontend/`: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, Recharts, Axios.
- `backend/`: FastAPI, SQLAlchemy, Pydantic, python-jose JWT auth, bcrypt, boto3.
- PostgreSQL: stores users, synced instance metadata, and persisted metric snapshots.
- AWS adapter: `CLOUDSIM_AWS_BACKEND=mock` for public demos, or `live` for EC2, CloudWatch, and Cost Explorer.

Start with the full diagram in [docs/Architecture_Diagram.md](docs/Architecture_Diagram.md), then use [docs/WALKTHROUGH_GUIDELINE.md](docs/WALKTHROUGH_GUIDELINE.md) for a reviewer/demo walkthrough.

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

The Compose stack starts PostgreSQL, the FastAPI backend, and the built Vite frontend served by nginx. By default it uses `CLOUDSIM_AWS_BACKEND=mock`, so the app can be demonstrated without touching real AWS resources.

To create a local admin during startup:

```bash
export CLOUDSIM_LOCAL_ADMIN_PASSWORD="$(openssl rand -hex 24)"
CLOUDSIM_BOOTSTRAP_ADMIN_ENABLED=true \
CLOUDSIM_BOOTSTRAP_ADMIN_EMAIL=docker-admin@example.com \
CLOUDSIM_BOOTSTRAP_ADMIN_PASSWORD="$CLOUDSIM_LOCAL_ADMIN_PASSWORD" \
docker compose up --build
```

Bootstrap creates the account if missing, or restores `role=Admin` and active status if it already exists. The password is preserved on later relaunches unless `CLOUDSIM_BOOTSTRAP_ADMIN_RESET_PASSWORD=true` is also set.

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

For local development the frontend falls back to `http://localhost:8000`. For deployed Vercel builds, set:

```text
VITE_API_URL=https://<your-backend-service>.onrender.com
```

## Quality Checks

Backend:

```bash
cd backend
source venv/bin/activate
python -m pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run test
npm run build
```

CI runs backend tests, frontend lint/test/build, Compose validation, and Docker image builds on pushes and pull requests to `main`.

## Production Deployment

Use [docs/deployment/PRODUCTION_DEPLOYMENT.md](docs/deployment/PRODUCTION_DEPLOYMENT.md) for the production deployment checklist. The recommended public demo mode is:

- Backend: Render Docker web service from `backend/Dockerfile`
- Frontend: Vercel static deployment from the Vite `frontend/dist` build
- Database: Render PostgreSQL
- AWS mode: `CLOUDSIM_AWS_BACKEND=mock`

For live AWS operation, set `CLOUDSIM_AWS_BACKEND=live` and configure AWS credentials or role-based AssumeRole settings in the backend service only.

Run a deployment smoke test with:

```bash
BACKEND_URL=https://<your-backend-service>.onrender.com ./scripts/smoke_deployment.sh
```

## Documentation Map

- [Walkthrough Guideline](docs/WALKTHROUGH_GUIDELINE.md)
- [Architecture Diagram](docs/Architecture_Diagram.md)
- [Production Deployment](docs/deployment/PRODUCTION_DEPLOYMENT.md)
- [Production Audit](docs/deployment/PRODUCTION_AUDIT.md)
- [Database Schema](docs/Database_Schema.md)
- [Roles Reference](docs/ROLES_REFERENCE.md)
- [Product Requirements / SRS](docs/CloudSim_SRS.md)
- [Project Sprint Plan](docs/ProjectSprintPlan.csv)
- [User Journeys](docs/user-journeys/)
