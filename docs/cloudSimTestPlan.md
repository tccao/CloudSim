# CloudSim — Full Testing Suite Implementation Plan

## Step-by-Step Implementation

### Step 1 — Install test dependencies

Create `backend/requirements-dev.txt`:
```
pytest>=8.0.0
pytest-asyncio>=0.23.0    # routes are async def — without this they silently pass without running
pytest-cov>=5.0.0         # coverage reports
httpx>=0.27.0             # TestClient dependency in newer FastAPI/Starlette
moto[ec2,cloudwatch,ce]>=5.0.0  # intercept boto3 calls at the botocore transport layer
```

### Step 2 — Create pytest.ini

`backend/pytest.ini`:
```ini
[pytest]
testpaths = tests
minversion = 8.0
asyncio_mode = auto
markers =
    unit: Pure functions, no IO
    integration: DB involved, no HTTP
    api: Full HTTP through TestClient
    aws: Requires moto
addopts = -v --tb=short
log_cli = true
log_cli_level = WARNING
```

**Clarification** `asyncio_mode = auto` means every `async def test_*` function is treated
as an async test automatically. Without it we'd need `@pytest.mark.asyncio` on every function.

## How to Run

```bash
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt

# All tests
pytest

# With coverage (target 75–80%)
pytest --cov=app --cov-report=term-missing

# Fast feedback during writing (unit only)
pytest -m unit

# Stop at first failure
pytest -x

# One file
pytest tests/test_auth_routes.py::test_register_success