#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_ANON_KEY:-}" ]]; then
  echo "Set SUPABASE_URL and SUPABASE_ANON_KEY first."
  exit 1
fi

curl -sS \
  "${SUPABASE_URL}/rest/v1/rpc/ms_get_portal_payload" \
  -X POST \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"p_email":"demo@marketstate.ai"}'
echo
