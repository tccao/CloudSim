# CloudSim Production Audit

Audit scope: backend auth/RBAC, frontend token handling, AWS access paths,
Docker/Render/Vite deployment config, dependency health, script redundancy, and
secret/demo credential exposure.

## Findings

### P0 - Critical

- None found in the checked code paths after adding backend-only admin bootstrap.

### P1 - High

- None remaining after Docker and Python vulnerability validation completed.

### P2 - Medium

- Public registration remains enabled at `/api/auth/register`. That is fine for
  demos, but production should decide whether open signup is intentional and add
  rate limiting or an invite/admin-created-user flow if it is not.
- JWTs are stored in `localStorage`. The frontend documents this tradeoff, but a
  production hardening pass should consider httpOnly cookies or stronger CSP if
  the threat model includes XSS token theft.
- Login/register/admin APIs do not currently show rate limiting or account
  lockout controls. Add request throttling before exposing the app broadly.
- The backend still creates tables with `Base.metadata.create_all` on startup.
  This is workable for the current schema but should move to migrations before
  production schema changes become routine.

### P3 - Low

- `backend/scripts/recreate_seed_database.py` still contains fixed local demo
  credentials, but it is now blocked in `CLOUDSIM_ENVIRONMENT=production`.
- `backend/sql/recreate_cloudsim_schema.sql` is now schema-only and no longer
  embeds demo password hashes.
- `verify_system.py` was retired; `scripts/smoke_deployment.sh` is the canonical
  deployment smoke test and now supports an optional admin API check.

## Verification

- Backend tests: `venv/bin/python -m pytest` passed, 156 tests.
- Frontend lint: `npm run lint` passed.
- Frontend tests: `npm run test` passed, 1 file / 4 tests.
- Frontend build: `npm run build` passed.
- npm dependency audit: `npm audit` found 0 vulnerabilities.
- Python vulnerability audit: `venv/bin/python -m pip_audit --cache-dir /tmp/pip-audit --local` found no known vulnerabilities.
- Python dependency compatibility: `venv/bin/python -m pip check` found no broken requirements.
- Docker daemon check: `docker info` succeeded against Docker Desktop.
- Docker Compose validation: `docker compose config` passed.
- Backend Docker build: `docker build -t cloudsim-backend:prod ./backend` passed.
- Frontend Docker build: `docker build --build-arg VITE_API_URL=http://localhost:8000 -t cloudsim-frontend:prod ./frontend` passed.
- Secret/demo credential scan: no production secrets found; remaining fixed demo
  passwords are in the dev-only seed script.
- Smoke script syntax: `bash -n scripts/smoke_deployment.sh` passed.

## Production Checklist

- Set admin bootstrap variables only on the backend Render service:
  `CLOUDSIM_BOOTSTRAP_ADMIN_ENABLED`, `CLOUDSIM_BOOTSTRAP_ADMIN_EMAIL`,
  `CLOUDSIM_BOOTSTRAP_ADMIN_PASSWORD`, and optionally
  `CLOUDSIM_BOOTSTRAP_ADMIN_RESET_PASSWORD`.
- Keep Vite limited to public settings such as `VITE_API_URL`.
- Re-run Docker validation after changing Dockerfiles, Compose, or dependency
  manifests.
- Run the admin smoke check after deployment:
  `SMOKE_ADMIN_CHECK=1 SMOKE_ADMIN_EMAIL=<admin-email> SMOKE_ADMIN_PASSWORD=<admin-password> ./scripts/smoke_deployment.sh`.
