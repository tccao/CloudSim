# CloudSim Frontend

This is the Vite React frontend for CloudSim. It provides the authenticated dashboard, launch wizard, instance details, monitoring charts, and IAM/settings panel.

## Stack

- React 18 + TypeScript
- Vite / rolldown-vite
- Tailwind CSS 4
- shadcn/ui and Radix primitives
- Recharts for monitoring charts
- Axios API client with JWT request/response interceptors
- Vitest + React Testing Library

## Runtime Contract

The frontend talks to the FastAPI backend through the shared Axios client in `src/api/client.ts`.

```text
VITE_API_URL=https://<your-backend-service>.onrender.com
```

If `VITE_API_URL` is not set, local development falls back to `http://localhost:8000`.

Only `VITE_*` values are exposed to the browser. Keep admin bootstrap variables, database URLs, JWT secrets, and AWS credentials on the backend service.

## Local Development

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Expected local backend:

```text
http://localhost:8000
```

## Production Build

```bash
npm run build
npm run preview
```

The build output is written to `dist/`. On Vercel, deploy it as a Vite static app with:

- Root directory: `frontend`
- Install command: `npm ci`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_URL=https://<your-backend-service>.onrender.com`

The Docker production path also exists in `frontend/Dockerfile` for local Compose and container validation; it builds the Vite app and serves `dist/` through nginx with SPA fallback routing.

## Quality Checks

```bash
npm run lint
npm run test
npm run build
```

## Feature Areas

- `src/App.tsx`: top-level authenticated shell, tabs, launch modal, IAM panel.
- `src/contexts/UserContext.tsx`: login, registration, token validation, logout, role state.
- `src/components/DashboardPage.tsx`: instance inventory and lifecycle actions.
- `src/components/CreateInstanceModal.tsx`: four-step EC2 launch wizard.
- `src/components/InstanceDetailsPage.tsx`: details, security, networking, storage, and tags.
- `src/components/InstanceMonitoringPage.tsx`: metrics, costs, and chart tabs.
- `src/components/IAMPanel.tsx`: current user, admin user management, role permissions, advanced settings.
- `src/api/`: typed API wrappers for auth, admin, instances, EC2, metrics, and costs.
