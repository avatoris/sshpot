#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

PORT="$(grep -m1 '^HONEYPOT_PUBLIC_PORT=' .env 2>/dev/null | cut -d= -f2)"
PORT="${PORT:-22}"

echo "== Triggering a failed login against localhost:${PORT} =="
sshpass -p "wrong-password" \
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 -p "$PORT" test@127.0.0.1 exit 2>/dev/null || true

echo "Waiting a few seconds for the reporter to process the event..."
sleep 5

echo
echo "== Reporter log (last 20 lines) =="
docker compose logs --tail=20 reporter

echo
if docker compose logs reporter | grep -q "reported 127.0.0.1"; then
    echo "OK: reporter sent (or attempted) a report for 127.0.0.1."
else
    echo "No report line found yet for 127.0.0.1 - check the log above."
    echo "Note: only the FIRST failed attempt per IP within the 30-minute"
    echo "window triggers an immediate report; re-running this script"
    echo "within that window will be suppressed by design."
fi

echo
echo "To independently confirm Avatoris received it, run:"
echo "  curl -s -H \"Authorization: Bearer \$AVATORIS_API_KEY\" https://avatoris.com/api/v1/lookup/127.0.0.1"
