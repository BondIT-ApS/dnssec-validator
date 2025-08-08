#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://localhost:8080"
DOMAINS=("example.com" "cloudflare.com" "google.com" "bondit.dk" "ripe.net")

# helper: make N calls to validate with optional X-Client header
call_api() {
  local count="$1"; shift
  local mode="$1"; shift  # webapp|external
  local domain
  for ((i=1; i<=count; i++)); do
    domain="${DOMAINS[$((RANDOM % ${#DOMAINS[@]}))]}"
    if [[ "$mode" == "webapp" ]]; then
      curl -sS "${BASE_URL}/api/validate/${domain}" -H "X-Client: webapp" >/dev/null || true
    else
      curl -sS "${BASE_URL}/api/validate/${domain}" >/dev/null || true
    fi
  done
}

# Sequence over ~15 minutes
# Round 1 (t=0): 17 internal, 28 external
call_api 17 webapp
call_api 28 external

# wait 1 minute
sleep 60
# Round 2: 10 internal, 15 external
call_api 10 webapp
call_api 15 external

# wait 2 minutes
sleep 120
# Round 3: 8 internal, 12 external
call_api 8 webapp
call_api 12 external

# wait 3 minutes
sleep 180
# Round 4: 6 internal, 9 external
call_api 6 webapp
call_api 9 external

# wait 4 minutes
sleep 240
# Round 5: 5 internal, 7 external
call_api 5 webapp
call_api 7 external

# Final fetch of analytics (printed to stdout)
echo "\n=== Overview (1h) ==="
curl -sS "${BASE_URL}/api/analytics/overview?period=1h" | jq . || true

echo "\n=== Time series (1h) ==="
curl -sS "${BASE_URL}/api/analytics/timeseries?period=1h" | jq . || true

echo "\n=== Sources (1h) ==="
curl -sS "${BASE_URL}/api/analytics/sources?period=1h" | jq . || true

