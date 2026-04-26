#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_ANON_KEY:-}" ]]; then
  echo "Set SUPABASE_URL and SUPABASE_ANON_KEY first."
  exit 1
fi

DEMO_USER_ID="${DEMO_USER_ID:-11111111-1111-1111-1111-111111111111}"
SYMBOL="${1:-AMZN}"
PRICE="${2:-199.99}"
CHANGE_PCT="${3:-1.23}"

curl -sS \
  -X PUT \
  "${SUPABASE_URL}/rest/v1/ms_watchlist?user_id=eq.${DEMO_USER_ID}&symbol=eq.${SYMBOL}" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d "{\"price\": ${PRICE}, \"change_pct\": ${CHANGE_PCT}}"
echo
