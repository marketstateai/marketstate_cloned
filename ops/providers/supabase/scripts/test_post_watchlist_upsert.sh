#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_ANON_KEY:-}" ]]; then
  echo "Set SUPABASE_URL and SUPABASE_ANON_KEY first."
  exit 1
fi

DEMO_USER_ID="${DEMO_USER_ID:-11111111-1111-1111-1111-111111111111}"
SYMBOL="${1:-PLTR}"
PRICE="${2:-31.42}"
CHANGE_PCT="${3:-2.54}"

curl -sS \
  -X POST \
  "${SUPABASE_URL}/rest/v1/ms_watchlist?on_conflict=user_id,symbol" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: resolution=merge-duplicates,return=representation" \
  -d "[{\"user_id\":\"${DEMO_USER_ID}\",\"symbol\":\"${SYMBOL}\",\"price\":${PRICE},\"change_pct\":${CHANGE_PCT}}]"
echo
