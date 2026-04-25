#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_ANON_KEY:-}" ]]; then
  echo "Set SUPABASE_URL and SUPABASE_ANON_KEY first."
  exit 1
fi

DEMO_USER_ID="${DEMO_USER_ID:-11111111-1111-1111-1111-111111111111}"

curl -sS \
  "${SUPABASE_URL}/rest/v1/ms_watchlist?select=id,symbol,price,change_pct,user_id&user_id=eq.${DEMO_USER_ID}&order=symbol.asc" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" \
  -H "Accept: application/json"
echo
