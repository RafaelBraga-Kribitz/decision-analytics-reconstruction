#!/bin/bash
# Deploy Module B (FastAPI) to Google Cloud Run
# Usage: ./scripts/deploy_module_b_cloudrun.sh <GCP_PROJECT> [REGION] [IMAGE_TAG]

set -euo pipefail

GCP_PROJECT="${1:?GCP_PROJECT required}"
REGION="${2:-europe-west3}"
IMAGE_TAG="${3:-latest}"
REPOSITORY="decision-analytics"
SERVICE_NAME="module-b-fastapi"
IMAGE_URI="${REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPOSITORY}/module-b:${IMAGE_TAG}"

echo "🚀 Deploying Module B (FastAPI) to Cloud Run"
echo "   Project: $GCP_PROJECT"
echo "   Region: $REGION"
echo "   Image: $IMAGE_URI"

# Build Docker image
echo "📦 Building Docker image..."
docker build \
  --file docker/Dockerfile.module-b \
  --tag "${IMAGE_URI}" \
  .

# Push to Artifact Registry
echo "📤 Pushing to Artifact Registry..."
docker push "${IMAGE_URI}"

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --project="${GCP_PROJECT}" \
  --region="${REGION}" \
  --image="${IMAGE_URI}" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --no-gen2 \
  --labels="module=b,component=fastapi,deployment=cloud-run" \
  --health-check-path="/healthz" \
  --format="value(status.url)"

echo "✅ Module B deployed successfully!"
