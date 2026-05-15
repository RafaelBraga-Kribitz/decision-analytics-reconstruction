#!/bin/bash
# Deploy Module A (Streamlit) to Google Cloud Run
# Usage: ./scripts/deploy_module_a_cloudrun.sh <GCP_PROJECT> [REGION] [IMAGE_TAG]

set -euo pipefail

GCP_PROJECT="${1:?GCP_PROJECT required}"
REGION="${2:-europe-west3}"
IMAGE_TAG="${3:-latest}"
REPOSITORY="decision-analytics"
SERVICE_NAME="module-a-streamlit"
IMAGE_URI="${REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPOSITORY}/module-a:${IMAGE_TAG}"

echo "🚀 Deploying Module A (Streamlit) to Cloud Run"
echo "   Project: $GCP_PROJECT"
echo "   Region: $REGION"
echo "   Image: $IMAGE_URI"

# Build Docker image
echo "📦 Building Docker image..."
docker build \
  --file docker/Dockerfile \
  --tag "${IMAGE_URI}" \
  --build-arg INSTALL_DEV=0 \
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
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --no-gen2 \
  --set-cloudsql-instances="" \
  --labels="module=a,component=streamlit,deployment=cloud-run" \
  --format="value(status.url)"

echo "✅ Module A deployed successfully!"
