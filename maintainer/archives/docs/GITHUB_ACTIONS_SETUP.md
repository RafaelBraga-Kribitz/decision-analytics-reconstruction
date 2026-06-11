# GitHub Actions & Workload Identity Setup

Configure GitHub Actions for automatic Cloud Run deployment.

---

## Overview

This project uses **GitHub Actions + Workload Identity Federation** for secure, keyless authentication to Google Cloud. No service account JSON keys required.

---

## Prerequisites

- GitHub repo with admin access
- GCP project with billing enabled
- `gcloud` CLI installed

---

## Step 1: Enable Workload Identity Federation

Create OpenID Connect (OIDC) provider for GitHub:

```bash
export GCP_PROJECT="<your-project-id>"
export GITHUB_ORG="<your-github-username-or-org>"
export GITHUB_REPO="decision-analytics-reconstruction"

# Enable required APIs
gcloud services enable iam.googleapis.com iamcredentials.googleapis.com cloudresourcemanager.googleapis.com --project=$GCP_PROJECT

# Create Workload Identity pool
gcloud iam workload-identity-pools create "github-actions" \
  --project=$GCP_PROJECT \
  --location="global" \
  --display-name="GitHub Actions"

# Create OIDC provider
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project=$GCP_PROJECT \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --display-name="GitHub provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.aud=assertion.aud,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Get Workload Identity Provider resource name
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project=$GCP_PROJECT \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --format="value(name)"
# Output: projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-actions/providers/github-provider
```

Save the provider name—you'll use it in Step 3.

---

## Step 2: Create Service Account

Create service account for Cloud Run deployments:

```bash
export SERVICE_ACCOUNT_NAME="github-actions-deployer"

# Create service account
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --project=$GCP_PROJECT \
  --display-name="GitHub Actions Cloud Run Deployer"

# Grant required roles
gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"

# Get service account email
echo "${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"
```

---

## Step 3: Configure Workload Identity Binding

Allow GitHub Actions to impersonate the service account:

```bash
# Set environment variables
export SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"
export WORKLOAD_IDENTITY_PROVIDER="projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-actions/providers/github-provider"

# Update service account to allow GitHub Actions OIDC
gcloud iam service-accounts add-iam-policy-binding $SERVICE_ACCOUNT_EMAIL \
  --project=$GCP_PROJECT \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}"
```

---

## Step 4: Add GitHub Secrets

In your GitHub repository, add these secrets:

1. Go to **Settings → Secrets and variables → Actions**
2. Add the following secrets:

| Secret Name | Value |
|-------------|-------|
| `GCP_PROJECT` | Your GCP project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | The provider name from Step 1 |
| `GCP_SERVICE_ACCOUNT` | The service account email from Step 2 |

**Example values:**
```
GCP_PROJECT: my-project-123456
GCP_WORKLOAD_IDENTITY_PROVIDER: projects/123456789/locations/global/workloadIdentityPools/github-actions/providers/github-provider
GCP_SERVICE_ACCOUNT: github-actions-deployer@my-project-123456.iam.gserviceaccount.com
```

---

## Step 5: Test the Workflow

1. Push a small change to `main` (or use **Actions → Deploy to Cloud Run → Run workflow**)
2. Monitor the workflow: **Actions tab → Deploy to Cloud Run → Latest run**
3. Verify:
   - Docker images pushed to Artifact Registry
   - Services deployed to Cloud Run
   - Smoke tests pass
   - PR comments with URLs (if from PR)

---

## Workflow Behavior

**Trigger:** Push to `main` that changes:
- `module_a_population_segmentation/**`
- `module_b_resource_allocation/**`
- `docker/**`
- `pyproject.toml`

**Workflow steps:**
1. Check which modules changed
2. Build Docker images in parallel
3. Push to Artifact Registry
4. Deploy to Cloud Run
5. Run smoke tests
6. Comment PR with deployment URLs

**Manual trigger:**
```
Actions → Deploy to Cloud Run → Run workflow → Select module (module-a, module-b, or both)
```

---

## Troubleshooting

### `Error: permission denied while trying to connect to the Docker daemon`
- Run script locally: Ensure Docker daemon running (`docker ps`)
- Run in Actions: Docker is pre-installed; check logs for actual error

### `403 Forbidden` from Artifact Registry
- Verify service account has `artifactregistry.writer` role
- Check project ID matches in secrets

### Cloud Run deployment fails
- Verify service account has `run.admin` role
- Check Docker image pushed successfully
- Review Cloud Run logs: `gcloud run services describe <service> --region=europe-west3`

### Workload Identity issues
- Re-check provider name (must include full path)
- Verify OIDC trust relationship: `gcloud iam service-accounts get-iam-policy <service-account>`
- Test locally: `gcloud auth application-default print-access-token`

---

## Cleanup

To remove Workload Identity setup:

```bash
# Delete service account
gcloud iam service-accounts delete $SERVICE_ACCOUNT_EMAIL --project=$GCP_PROJECT --quiet

# Delete OIDC provider
gcloud iam workload-identity-pools providers delete github-provider \
  --project=$GCP_PROJECT \
  --location=global \
  --workload-identity-pool=github-actions \
  --quiet

# Delete pool
gcloud iam workload-identity-pools delete github-actions \
  --project=$GCP_PROJECT \
  --location=global \
  --quiet
```

---

## References

- [Google Cloud Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub Actions Google Cloud Auth](https://github.com/google-github-actions/auth)
- [Cloud Run Deployment Best Practices](https://cloud.google.com/run/docs/deployment)

---

**Last updated:** 2026-05-15
