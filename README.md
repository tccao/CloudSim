# CloudSim
A web-based platform that simulates core cloud infrastructure concepts like compute instances, containers, networking, and monitoring without using real cloud costs. Users can “spin up” virtual VMs, deploy sample apps, visualize network traffic, and monitor resource usage through custom backend simulation.

## Features

| Feature | Description |
| :--- | :--- |
| <img src="icons/cloud.svg" alt="Cloud" width="24"> **Cloud Simulation** | Simulate a cloud environment without incurring costs. |
| <img src="icons/server.svg" alt="Server" width="24"> **Virtual Machines** | Create and manage virtual machines. |
| <img src="icons/globe-alt.svg" alt="Network" width="24"> **Networking** | Visualize network traffic between services. |
| <img src="icons/circle-stack.svg" alt="Storage" width="24"> **Storage** | Simulate object and block storage. |
| <img src="icons/beaker.svg" alt="Simulation" width="24"> **Deploy & Monitor** | Deploy sample applications and monitor their performance. |
| <img src="icons/document-text.svg" alt="Documentation" width="24"> **Documentation** | Comprehensive documentation for all features. |

## Backend Requirements

The backend is a FastAPI application and needs both Python dependencies and a running PostgreSQL database.

- Python 3.12+
- PostgreSQL 15+ running locally or reachable remotely
- `uvicorn` for the ASGI development server

Backend Python packages are listed in [backend/requirements.txt](/home/tinhc/CloudSim/backend/requirements.txt), including:

- `fastapi`
- `uvicorn[standard]`
- `sqlalchemy`
- `psycopg2-binary`
- `pydantic` and `pydantic-settings`
- `python-jose[cryptography]`
- `passlib[bcrypt]`
- `boto3`

## Quick Start

### Docker Compose

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- Backend API docs: http://localhost:8000/docs

The Compose stack uses a local Postgres container and creates API tables on backend startup. For live AWS calls, export the needed AWS environment variables before starting Compose, or add them to a local `.env` file used by Docker Compose.

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://postgres:1@localhost:5432/cloudsim"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
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
npm run build
```

CI runs backend tests, frontend lint/build, Compose validation, and Docker image builds on pushes and pull requests to `main`.
