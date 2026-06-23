FROM python:3.14-slim AS runtime

# pythonwritebytecode=1 prevents Python from writing .pyc files, which can save space in the container.
# pythonunbuffered=1 ensures that Python output is sent directly to the terminal without buffering, which is useful for logging in a containerized environment.
# uv no cache disables the uv cache, which is unnecessary in a single-shot image build.
# uv compile bytecode precompiles installed packages for faster cold starts.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    CLOUDSIM_BOOTSTRAP_ADMIN_ENABLED=false

# uv is the package manager; copy its static binary from the official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Create a non-root user to run the application
RUN addgroup --system cloudsim && adduser --system --ingroup cloudsim cloudsim

# Install dependencies from the lockfile for reproducible builds. --no-dev omits
# test-only packages; the resulting .venv is placed on PATH above so uvicorn resolves to it.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy the application code into the container, setting ownership to the non-root user we created earlier. This ensures that the application files are owned by the cloudsim user
COPY --chown=cloudsim:cloudsim app ./app

USER cloudsim

# EXPOSE instruction informs Docker that the container listens on the specified network ports at runtime. In this case, it indicates that the application will be accessible on port 8000, which is the default port for FastAPI applications when using Uvicorn as the ASGI server. This allows Docker to map the container's port to a port on the host machine when running the container, enabling access to the application from outside the container.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\", \"8000\")}/health', timeout=2)" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
