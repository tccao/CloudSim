#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-}"
SMOKE_AUTH="${SMOKE_AUTH:-0}"
SMOKE_PASSWORD="${SMOKE_PASSWORD:-testpassword123}"

trim_trailing_slash() {
  printf '%s' "${1%/}"
}

BACKEND_URL="$(trim_trailing_slash "$BACKEND_URL")"
if [ -n "$FRONTEND_URL" ]; then
  FRONTEND_URL="$(trim_trailing_slash "$FRONTEND_URL")"
fi

echo "Checking backend health: $BACKEND_URL/health"
curl -fsS "$BACKEND_URL/health"
echo

if [ -n "$FRONTEND_URL" ]; then
  echo "Checking frontend: $FRONTEND_URL"
  curl -fsSI "$FRONTEND_URL" >/dev/null
fi

if [ "$SMOKE_AUTH" != "1" ]; then
  echo "Smoke test passed."
  exit 0
fi

SMOKE_EMAIL="${SMOKE_EMAIL:-smoke-$(date +%s)@example.com}"

echo "Registering smoke user: $SMOKE_EMAIL"
curl -fsS -X POST "$BACKEND_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$SMOKE_EMAIL\",\"password\":\"$SMOKE_PASSWORD\"}" >/dev/null

echo "Logging in smoke user"
TOKEN="$(
  curl -fsS -X POST "$BACKEND_URL/api/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$SMOKE_EMAIL&password=$SMOKE_PASSWORD" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"
)"

echo "Checking /api/auth/me"
curl -fsS "$BACKEND_URL/api/auth/me" \
  -H "Authorization: Bearer $TOKEN" >/dev/null

echo "Smoke test passed."
