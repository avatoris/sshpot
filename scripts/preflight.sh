#!/usr/bin/env bash
# Checks the host is ready before `docker compose up`.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

fail=0

echo "== Docker =="
if ! command -v docker >/dev/null; then
    echo "FAIL: docker is not installed"
    fail=1
else
    docker --version
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "FAIL: 'docker compose' (v2 plugin) not available"
    fail=1
fi

echo
echo "== .env =="
if [ ! -f .env ]; then
    echo "FAIL: .env is missing. Copy .env.example to .env and fill in AVATORIS_API_KEY."
    fail=1
else
    if ! grep -q '^AVATORIS_API_KEY=.\+' .env; then
        echo "FAIL: AVATORIS_API_KEY is empty in .env"
        fail=1
    else
        echo "OK: AVATORIS_API_KEY is set"
    fi
fi

echo
echo "== Vendored Cowrie source =="
if [ ! -d vendor/cowrie/docker ]; then
    echo "FAIL: vendor/cowrie is missing. Run ./scripts/vendor_cowrie.sh first"
    echo "      (fetches a pinned Cowrie release and applies the Dockerfile fix)."
    fail=1
elif ! grep -q -- "--no-deps -e \${COWRIE_HOME}/cowrie-git" vendor/cowrie/docker/Dockerfile 2>/dev/null; then
    echo "WARN: vendor/cowrie/docker/Dockerfile doesn't look patched."
    echo "      Re-run ./scripts/vendor_cowrie.sh to re-apply the fix."
else
    echo "OK: vendor/cowrie present with the patched Dockerfile"
fi

echo
echo "== Port availability =="
PUBLIC_PORT="$(grep -m1 '^HONEYPOT_PUBLIC_PORT=' .env 2>/dev/null | cut -d= -f2)"
PUBLIC_PORT="${PUBLIC_PORT:-22}"
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${PUBLIC_PORT}\$"; then
    echo "FAIL: port ${PUBLIC_PORT} is already in use on the host."
    echo "      If that's your real sshd, move it to another port first"
    echo "      (edit /etc/ssh/sshd_config, set 'Port 2200', restart sshd),"
    echo "      then re-run this check."
    fail=1
else
    echo "OK: port ${PUBLIC_PORT} is free"
fi

echo
echo "== Host auth.log readability =="
AUTH_LOG="$(grep -m1 '^HOST_AUTH_LOG_PATH=' .env 2>/dev/null | cut -d= -f2)"
AUTH_LOG="${AUTH_LOG:-/var/log/auth.log}"
if [ ! -e "$AUTH_LOG" ]; then
    echo "WARN: $AUTH_LOG does not exist on this host."
    echo "      Set ENABLE_HOST_SSHD_WATCH=false in .env if this host has no"
    echo "      real sshd to monitor, or point HOST_AUTH_LOG_PATH elsewhere"
    echo "      (RHEL/CentOS typically use /var/log/secure)."
else
    ADM_GID="$(getent group adm 2>/dev/null | cut -d: -f3 || true)"
    echo "OK: $AUTH_LOG exists. Host 'adm' group GID is: ${ADM_GID:-unknown}"
    if [ -n "${ADM_GID:-}" ] && ! grep -q "^GROUP_ADD_GID=${ADM_GID}\$" .env 2>/dev/null; then
        echo "      NOTE: set GROUP_ADD_GID=${ADM_GID} in .env if it isn't already."
    fi
fi

echo
if [ "$fail" -ne 0 ]; then
    echo "Preflight FAILED - fix the issues above before starting."
    exit 1
fi
echo "Preflight OK."
