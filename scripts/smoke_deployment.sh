#!/usr/bin/env bash
set -euo pipefail

# Step 01: Read deployment smoke-test settings from the environment.
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-}"
SMOKE_AUTH="${SMOKE_AUTH:-0}"
SMOKE_PASSWORD="${SMOKE_PASSWORD:-testpassword123}"
SMOKE_CLEANUP="${SMOKE_CLEANUP:-1}"
SMOKE_ADMIN_EMAIL="${SMOKE_ADMIN_EMAIL:-}"
SMOKE_ADMIN_PASSWORD="${SMOKE_ADMIN_PASSWORD:-}"
SMOKE_USER_CREATED=0
SMOKE_USER_ID=""
SMOKE_EMAIL="${SMOKE_EMAIL:-}"

# Step 02: Normalize URLs so endpoint joins do not produce double slashes.
trim_trailing_slash() {
  printf '%s' "${1%/}"
}

BACKEND_URL="$(trim_trailing_slash "$BACKEND_URL")"
if [ -n "$FRONTEND_URL" ]; then
  FRONTEND_URL="$(trim_trailing_slash "$FRONTEND_URL")"
fi

# Step 03: Parse one top-level JSON field from stdin without requiring jq.
json_field() {
  local field="$1"
  python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$field"
}

# Step 04: Log in and print the returned JWT access token.
login_user() {
  local email="$1"
  local password="$2"

  curl -fsS -X POST "$BACKEND_URL/api/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "username=$email" \
    --data-urlencode "password=$password" \
    | json_field "access_token"
}

# Step 05: Delete the smoke user after auth checks, when admin credentials exist.
cleanup_smoke_user() {
  local exit_code=$?

  if [ "$SMOKE_CLEANUP" != "1" ] || [ "$SMOKE_USER_CREATED" != "1" ]; then
    return "$exit_code"
  fi

  if [ -z "$SMOKE_ADMIN_EMAIL" ] || [ -z "$SMOKE_ADMIN_PASSWORD" ]; then
    echo "Skipping smoke user cleanup; set SMOKE_ADMIN_EMAIL and SMOKE_ADMIN_PASSWORD."
    return "$exit_code"
  fi

  if [ -z "$SMOKE_USER_ID" ]; then
    echo "Skipping smoke user cleanup; no smoke user id was captured."
    return "$exit_code"
  fi

  echo "Cleaning up smoke user: $SMOKE_EMAIL"
  local admin_token
  if admin_token="$(login_user "$SMOKE_ADMIN_EMAIL" "$SMOKE_ADMIN_PASSWORD")"; then
    if curl -fsS -X DELETE "$BACKEND_URL/api/admin/users/$SMOKE_USER_ID" \
      -H "Authorization: Bearer $admin_token" >/dev/null; then
      echo "Smoke user cleaned up."
    else
      echo "Warning: failed to delete smoke user $SMOKE_EMAIL." >&2
    fi
  else
    echo "Warning: failed to log in as admin for smoke user cleanup." >&2
  fi

  return "$exit_code"
}

trap cleanup_smoke_user EXIT

# Step 06: Backend health is the required deployment smoke check.
echo "Checking backend health: $BACKEND_URL/health"
curl -fsS "$BACKEND_URL/health"
echo

# Step 07: Frontend availability is optional because API-only deploys are valid.
if [ -n "$FRONTEND_URL" ]; then
  echo "Checking frontend: $FRONTEND_URL"
  curl -fsSI "$FRONTEND_URL" >/dev/null
fi

# Step 08: Auth smoke testing is opt-in because it creates a real user.
if [ "$SMOKE_AUTH" != "1" ]; then
  echo "Smoke test passed."
  exit 0
fi

SMOKE_EMAIL="${SMOKE_EMAIL:-smoke-$(date +%s)@example.com}"

# Step 09: Register a unique smoke user and remember its ID for cleanup.
echo "Registering smoke user: $SMOKE_EMAIL"
REGISTER_RESPONSE="$(
  curl -fsS -X POST "$BACKEND_URL/api/auth/register" \
  -H "Content-Type: application/json" \
    -d "$(
      python3 -c 'import json,sys; print(json.dumps({"email": sys.argv[1], "password": sys.argv[2]}))' \
        "$SMOKE_EMAIL" \
        "$SMOKE_PASSWORD"
    )"
)"
SMOKE_USER_CREATED=1
SMOKE_USER_ID="$(printf '%s' "$REGISTER_RESPONSE" | json_field "id")"

# Step 10: Log in as the smoke user and validate the protected profile endpoint.
echo "Logging in smoke user"
TOKEN="$(login_user "$SMOKE_EMAIL" "$SMOKE_PASSWORD")"

echo "Checking /api/auth/me"
curl -fsS "$BACKEND_URL/api/auth/me" \
  -H "Authorization: Bearer $TOKEN" >/dev/null

echo "Smoke test passed."
