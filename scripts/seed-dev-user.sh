#!/usr/bin/env bash
# Seed the development user. Safe to run multiple times — 409 = already exists.
set -euo pipefail

BASE="${BASE_URL:-http://localhost}"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${BASE}/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@localhost.dev","handle":"dev","display_name":"Dev User","password":"devdev99"}')

case "$HTTP_STATUS" in
  201) echo "Dev user created: dev@localhost.dev / devdev99" ;;
  409) echo "Dev user already exists — nothing to do." ;;
  *)   echo "Unexpected status from /api/auth/register: ${HTTP_STATUS}"; exit 1 ;;
esac
