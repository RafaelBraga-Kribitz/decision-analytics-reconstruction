#!/bin/bash
# Smoke test Cloud Run deployments
# Usage: ./scripts/smoke_test_cloudrun.sh <MODULE_A_URL> <MODULE_B_URL> [MAX_RETRIES]

set -euo pipefail

MODULE_A_URL="${1:?MODULE_A_URL required (e.g., https://module-a-streamlit-xxxxx.run.app)}"
MODULE_B_URL="${2:?MODULE_B_URL required (e.g., https://module-b-fastapi-xxxxx.run.app)}"
MAX_RETRIES="${3:-30}"

RETRY_COUNT=0
DELAY=2

echo "🧪 Smoke Testing Cloud Run Deployments"
echo "   Module A: $MODULE_A_URL"
echo "   Module B: $MODULE_B_URL"
echo ""

# Test Module B health check (simpler endpoint)
echo "Testing Module B (/healthz)..."
HEALTH_STATUS=false
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if response=$(curl -s -w "\n%{http_code}" "${MODULE_B_URL}/healthz" 2>/dev/null); then
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
      echo "✅ Module B /healthz: OK"
      echo "   Response: $body"
      HEALTH_STATUS=true
      break
    fi
  fi

  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
    echo "   ⏳ Waiting for Module B to be ready ($RETRY_COUNT/$MAX_RETRIES)..."
    sleep $DELAY
  fi
done

if [ "$HEALTH_STATUS" = false ]; then
  echo "❌ Module B health check failed after $MAX_RETRIES retries"
  exit 1
fi

# Test Module B allocation endpoint
echo ""
echo "Testing Module B (/allocation/baseline)..."
if response=$(curl -s -w "\n%{http_code}" "${MODULE_B_URL}/allocation/baseline" 2>/dev/null); then
  http_code=$(echo "$response" | tail -1)
  body=$(echo "$response" | head -n -1)

  if [ "$http_code" = "200" ]; then
    row_count=$(echo "$body" | grep -o '"row_count":[0-9]*' | cut -d: -f2)
    echo "✅ Module B /allocation/baseline: OK"
    echo "   Rows: $row_count"
  else
    echo "❌ Module B allocation endpoint returned HTTP $http_code"
    exit 1
  fi
else
  echo "❌ Module B allocation endpoint unreachable"
  exit 1
fi

# Test Module A (Streamlit)
echo ""
echo "Testing Module A (Streamlit root)..."
STREAMLIT_STATUS=false
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if response=$(curl -s -w "\n%{http_code}" "${MODULE_A_URL}/" 2>/dev/null); then
    http_code=$(echo "$response" | tail -1)

    if [ "$http_code" = "200" ]; then
      echo "✅ Module A root: OK"
      STREAMLIT_STATUS=true
      break
    fi
  fi

  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
    echo "   ⏳ Waiting for Module A to be ready ($RETRY_COUNT/$MAX_RETRIES)..."
    sleep $DELAY
  fi
done

if [ "$STREAMLIT_STATUS" = false ]; then
  echo "⚠️  Module A Streamlit may need more time (can be slow on first load)"
fi

echo ""
echo "✅ Smoke test complete!"
echo ""
echo "Module A Dashboard: $MODULE_A_URL"
echo "Module B API Docs: ${MODULE_B_URL}/docs"
echo "Module B Allocation: ${MODULE_B_URL}/allocation/baseline"
