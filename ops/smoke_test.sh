#!/usr/bin/env bash
set -euo pipefail

: "${BASE_URL:=http://127.0.0.1:8000}"
curl --fail --silent --show-error --max-time 10 "$BASE_URL/api/health" >/dev/null
curl --fail --silent --show-error --max-time 10 "$BASE_URL/api/ready" >/dev/null
echo "FadeReach smoke checks passed"
