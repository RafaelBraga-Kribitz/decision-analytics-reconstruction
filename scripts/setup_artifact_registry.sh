#!/bin/bash
# Set up Artifact Registry for Cloud Run deployments
# Usage: ./scripts/setup_artifact_registry.sh <GCP_PROJECT> [REGION]

set -euo pipefail

GCP_PROJECT="${1:?GCP_PROJECT required}"
REGION="${2:-europe-west3}"
REPOSITORY="decision-analytics"

echo "🏗️  Setting up Artifact Registry"
echo "   Project: $GCP_PROJECT"
echo "   Region: $REGION"
echo "   Repository: $REPOSITORY"

# Enable required APIs
echo "✅ Enabling APIs..."
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  storage-api.googleapis.com \
  --project="${GCP_PROJECT}" || true

# Create Artifact Registry repository
echo "📦 Creating Artifact Registry repository..."
if gcloud artifacts repositories describe "${REPOSITORY}" \
  --location="${REGION}" \
  --project="${GCP_PROJECT}" &>/dev/null; then
  echo "   Repository already exists"
else
  gcloud artifacts repositories create "${REPOSITORY}" \
    --location="${REGION}" \
    --repository-format=docker \
    --project="${GCP_PROJECT}"
  echo "   Repository created"
fi

# Configure Docker authentication
echo "🔑 Configuring Docker authentication..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" \
  --quiet \
  --project="${GCP_PROJECT}"

# Create Cloud Storage bucket for artifacts
BUCKET_NAME="${GCP_PROJECT}-decision-analytics-artifacts"
echo "🪣 Creating Cloud Storage bucket..."
if gsutil ls "gs://${BUCKET_NAME}" &>/dev/null; then
  echo "   Bucket already exists"
else
  gsutil mb -l "${REGION}" "gs://${BUCKET_NAME}"
  echo "   Bucket created"
fi

# Set bucket versioning
gsutil versioning set on "gs://${BUCKET_NAME}"

echo "✅ Artifact Registry setup complete!"
echo "   Registry: ${REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPOSITORY}"
echo "   Bucket: gs://${BUCKET_NAME}"
