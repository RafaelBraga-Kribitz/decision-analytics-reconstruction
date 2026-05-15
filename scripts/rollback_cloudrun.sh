#!/bin/bash
# Rollback Cloud Run services to previous revision
# Usage: ./scripts/rollback_cloudrun.sh <GCP_PROJECT> <SERVICE_NAME> [REGION]

set -euo pipefail

GCP_PROJECT="${1:?GCP_PROJECT required}"
SERVICE_NAME="${2:?SERVICE_NAME required (module-a-streamlit or module-b-fastapi)}"
REGION="${3:-europe-west3}"

echo "⏮️  Rolling back Cloud Run service"
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo "   Project: $GCP_PROJECT"
echo ""

# Get current and previous revisions
echo "📋 Retrieving revision history..."
revisions=$(gcloud run revisions list \
  --service="${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${GCP_PROJECT}" \
  --limit=2 \
  --format="value(name)" 2>/dev/null || true)

revision_array=($revisions)

if [ ${#revision_array[@]} -lt 2 ]; then
  echo "❌ Only one revision available; cannot rollback"
  exit 1
fi

current_rev="${revision_array[0]}"
previous_rev="${revision_array[1]}"

echo "   Current revision: $current_rev"
echo "   Previous revision: $previous_rev"
echo ""

# Confirm rollback
read -p "⚠️  Proceed with rollback to $previous_rev? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "❌ Rollback cancelled"
  exit 0
fi

# Update traffic to previous revision
echo "🔄 Updating traffic to previous revision..."
gcloud run services update-traffic "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${GCP_PROJECT}" \
  --to-revisions="${previous_rev}=100" \
  --async

echo "✅ Rollback initiated!"
echo "   Monitor progress: gcloud run services describe $SERVICE_NAME --region=$REGION --project=$GCP_PROJECT"
