# CloudSim — Full Testing Suite Implementation Plan

## Step-by-Step Implementation

### Step 1 — Declare test dependencies

Test-only packages live in the `dev` dependency group in `backend/pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",   # routes are async def — without this they silently pass without running
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",            # TestClient dependency in newer FastAPI/Starlette
    "moto[ec2,cloudwatch,ce]>=5.0.0",  # intercept boto3 calls at the botocore transport layer
]
```

`uv sync` installs this group by default; production images use `uv sync --no-dev`.

### Step 2 — Configure pytest

pytest config lives in `[tool.pytest.ini_options]` in `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
minversion = "9.0"
asyncio_mode = "auto"
markers = [
    "unit: Pure functions, no IO",
    "integration: DB involved, no HTTP",
    "api: Full HTTP through TestClient",
    "aws: Requires moto",
]
addopts = "-v --tb=short"
log_cli = true
log_cli_level = "WARNING"
```

**Clarification** `asyncio_mode = auto` means every `async def test_*` function is treated
as an async test automatically. Without it we'd need `@pytest.mark.asyncio` on every function.

## How to Run

```bash
cd backend
uv sync

# All tests
uv run pytest

# With coverage (target 75–80%)
uv run pytest --cov=app --cov-report=term-missing

# Fast feedback during writing (unit only)
uv run pytest -m unit

# Stop at first failure
uv run pytest -x

# One file
uv run pytest tests/test_auth_routes.py::test_register_success
