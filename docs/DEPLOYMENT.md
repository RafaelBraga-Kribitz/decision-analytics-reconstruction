---
doc_id: DOC-DOCS-001
doc_type: narrative
doc_role: canonical
visibility: public
status: active
owner: project
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Cloud Run Deployment Guide

Production deployment architecture for Module A (Streamlit) and Module B (FastAPI) on Google Cloud Run.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ GitHub Repository (main branch)                                 │
│ ├─ Push to main triggers GitHub Actions workflow                │
│ └─ deploy-cloudrun.yml builds & deploys                         │
└────────────────────┬────────────────────────────────────────────┘
                     │
     ┌───────────────┴───────────────┐
     │                               │
┌────▼────────────────┐   ┌──────────▼──────────────┐
│ Module A Streamlit  │   │ Module B FastAPI        │
│ Docker build        │   │ Docker build            │
│ (python:3.11-slim)  │   │ (python:3.11-slim)      │
└────┬────────────────┘   └──────────┬──────────────┘
     │                               │
     └───────────────┬───────────────┘
                     │
         ┌───────────▼───────────┐
         │ Artifact Registry     │
         │ (europe-west3)        │
         │ repo: decision-analytics
         └───────────┬───────────┘
                     │
     ┌───────────────┴───────────────┐
     │                               │
┌────▼────────────────┐   ┌──────────▼──────────────┐
│ Cloud Run (A)       │   │ Cloud Run (B)           │
│ 2 Gi memory         │   │ 1 Gi memory             │
│ 2 CPUs              │   │ 1 CPU                   │
│ Timeout: 3600s      │   │ Timeout: 300s           │
│ Health: /           │   │ Health: /healthz        │
│ Port: 8501          │   │ Port: 8000              │
└────┬────────────────┘   └──────────┬──────────────┘
     │                               │
     └──────────────┬────────────────┘
                    │
         ┌──────────▼──────────┐
         │ Cloud Storage       │
         │ (versioned bucket)  │
         │ Artifacts + logs    │
         └─────────────────────┘
```

---

## Prerequisites

1. **GCP Account** with billing enabled
2. **gcloud CLI** installed + authenticated
   ```bash
   gcloud auth login
   gcloud config set project <GCP_PROJECT>
   ```
3. **Docker** installed locally (for image builds)
4. **Workload Identity** configured (for GitHub Actions)
   - Service account with Editor role
   - OIDC provider configured
   - Environment secrets set in GitHub repo

---

## Step 1: Set Up Artifact Registry

Initialize Artifact Registry, Cloud Storage, and enable required APIs:

```bash
make setup-artifact-registry GCP_PROJECT=<your-project-id>
```

This creates:
- Artifact Registry repository (`decision-analytics`)
- Cloud Storage bucket for artifacts + versioning
- Required API enablement (Cloud Run, Artifact Registry, Cloud Build)

**Cost impact:** ~$0.10/month for empty Artifact Registry repo; GCS versioning adds ~$0.02/month per object version.

---

## Step 2: Deploy Module A (Streamlit)

Deploy Module A dashboard to Cloud Run:

```bash
make deploy-module-a GCP_PROJECT=<your-project-id>
```

**What happens:**
1. Builds Docker image from `docker/Dockerfile`
2. Pushes to Artifact Registry
3. Deploys to Cloud Run with:
   - 2 Gi memory, 2 CPUs
   - 3600s timeout (for long dashboard interactions)
   - Unauthenticated access
   - Auto-scaling (0–100 instances)

**Output:** Live Cloud Run URL (e.g., `https://module-a-streamlit-xxxxx.run.app`)

---

## Step 3: Deploy Module B (FastAPI)

Deploy Module B API to Cloud Run:

```bash
make deploy-module-b GCP_PROJECT=<your-project-id>
```

**What happens:**
1. Builds Docker image from `docker/Dockerfile.module-b`
2. Pushes to Artifact Registry
3. Deploys to Cloud Run with:
   - 1 Gi memory, 1 CPU
   - 300s timeout (for solver requests)
   - Unauthenticated access
   - Health check: `/healthz` endpoint
   - Auto-scaling (0–100 instances)

**Output:** Live Cloud Run URL (e.g., `https://module-b-fastapi-xxxxx.run.app`)

---

## Step 4: Smoke Test Deployments

Verify both services are healthy:

```bash
make smoke-test \
  MODULE_A_URL=https://module-a-streamlit-xxxxx.run.app \
  MODULE_B_URL=https://module-b-fastapi-xxxxx.run.app
```

**Tests:**
- Module B `/healthz` endpoint returns 200 OK
- Module B `/allocation/baseline` endpoint returns rows
- Module A root endpoint loads (Streamlit)

---

## Automatic Deployment via GitHub Actions

On push to `main`, GitHub Actions automatically:

1. Detects which modules changed
2. Builds Docker images
3. Pushes to Artifact Registry
4. Deploys to Cloud Run
5. Runs smoke tests
6. Comments PR with deployment URLs + docs link

**Secrets required in GitHub repo:**
- `GCP_PROJECT` — GCP project ID
- `GCP_WORKLOAD_IDENTITY_PROVIDER` — Workload Identity provider URI
- `GCP_SERVICE_ACCOUNT` — Service account email

[See GitHub Actions Setup Guide](../docs/GITHUB_ACTIONS_SETUP.md) for configuration.

---

## Health Checks & Observability

### Module A (Streamlit)
- **Root path** (`/`) returns 200 OK
- **Logs** available via Cloud Logging: `resource.type="cloud_run_revision" resource.labels.service_name="module-a-streamlit"`
- **No explicit health endpoint** (Streamlit serves root)

### Module B (FastAPI)
- **Health endpoint** `/healthz` returns `{"status": "ok", "module": "module_b_resource_allocation", "version": "0.1.0"}`
- **API docs** available at `<URL>/docs` (auto-generated by FastAPI)
- **Logs** available via Cloud Logging: `resource.type="cloud_run_revision" resource.labels.service_name="module-b-fastapi"`

### Query Cloud Logs

```bash
# Module A logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=module-a-streamlit" \
  --limit 50 --format json

# Module B logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=module-b-fastapi" \
  --limit 50 --format json
```

---

## Rollback Procedures

### Quick Rollback to Previous Revision

```bash
# Module A
make rollback-module-a GCP_PROJECT=<your-project-id>

# Module B
make rollback-module-b GCP_PROJECT=<your-project-id>
```

This updates traffic 100% to the previous revision and prompts for confirmation.

### Manual Rollback via gcloud

```bash
# List revisions
gcloud run revisions list \
  --service=module-a-streamlit \
  --region=europe-west3 \
  --project=<GCP_PROJECT>

# Split traffic between revisions
gcloud run services update-traffic module-a-streamlit \
  --region=europe-west3 \
  --project=<GCP_PROJECT> \
  --to-revisions=<OLD_REVISION_NAME>=50,<NEW_REVISION_NAME>=50
```

---

## Cost Estimation

Monthly costs (per service, typical usage):

| Component | Estimate | Notes |
|-----------|----------|-------|
| Cloud Run (Module A, Streamlit) | $10–$30 | 2 Gi, 2 CPUs; scales with invocations |
| Cloud Run (Module B, FastAPI) | $5–$15 | 1 Gi, 1 CPU; stateless solver |
| Artifact Registry storage | $0.10–$0.50 | ~10 image versions |
| Cloud Storage (artifacts) | $0.02–$0.20 | Versioned bucket |
| Cloud Logging | $0.50–$2.00 | Depends on request volume |
| **Total (both modules)** | **$15.62–$47.70/month** | Mid-range estimate: ~$30/month |

**Cost reduction tips:**
- Use `--memory=1Gi --cpu=1` for Module A if acceptable (saves ~50%)
- Delete old image versions from Artifact Registry
- Reduce log retention in Cloud Logging (default 30 days)
- Use VPC egress (cheaper than public IP)

---

## Environment Variables & Secrets

### Module A (Streamlit)
No environment variables required; uses local config files and cached data.

### Module B (FastAPI)
No environment variables required; reads from local data directory.

### GCP Integration
- Uses Application Default Credentials (ADC) in Cloud Run
- No service account keys needed
- Automatic authentication via Workload Identity

---

## Monitoring & Alerts

### View Service Metrics

```bash
gcloud run services describe module-a-streamlit \
  --region=europe-west3 \
  --project=<GCP_PROJECT>
```

### Create Alert Policy

```bash
# Alert if service errors exceed 5% over 5 minutes
gcloud alpha monitoring policies create \
  --notification-channels=<CHANNEL_ID> \
  --display-name="Module A Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold=0.05
```

---

## Troubleshooting

### Module A not loading (Streamlit)
- Check logs: `gcloud logging read "resource.labels.service_name=module-a-streamlit"`
- Verify Docker build: `docker build -f docker/Dockerfile .`
- Check memory: Streamlit requires ~500 MB + data caching

### Module B returns 500 errors
- Check `/healthz` endpoint first: `curl -s https://<URL>/healthz | jq`
- Verify MILP solver installed: `poetry show pulp`
- Check allocation data directory: `ls data/processed/module_b/`

### Slow deployments
- First deployment: ~3–5 min (image build + registry push)
- Subsequent: ~1–2 min (only code changes pushed)
- Use `--async` flag to submit and return immediately

---

## Clean Up

### Delete Cloud Run services
```bash
gcloud run services delete module-a-streamlit --region=europe-west3 --quiet
gcloud run services delete module-b-fastapi --region=europe-west3 --quiet
```

### Delete Artifact Registry repository
```bash
gcloud artifacts repositories delete decision-analytics --location=europe-west3 --quiet
```

### Delete Cloud Storage bucket
```bash
gsutil -m rm -r gs://<project>-decision-analytics-artifacts/
```

---

## Next Steps

1. **Set up GitHub Secrets** for automatic deployment
2. **Configure Cloud Logging sink** to external storage (BigQuery, GCS)
3. **Add custom domain** (optional):
   ```bash
   gcloud run services update module-a-streamlit \
     --set-cloudsql-instances="" \
     --region=europe-west3
   ```
4. **Enable Cloud Armour** for DDoS protection (if public API)

---

**Last updated:** 2026-05-15


---

## Cost Controls

Use the Cloud Run resource tier deliberately; keep Docker workflows on this
maintainer machine CLI-first and prefer Colima over Docker Desktop.

| Tier | Module A | Module B | Monthly Cost | Trade-offs |
|---|---|---|---|---|
| Maximum | 2 Gi, 2 CPU, 3600s | 1 Gi, 1 CPU, 300s | $30-$50 | Best dashboard responsiveness and solver headroom |
| Balanced | 1 Gi, 1 CPU, 1800s | 512 Mi, 0.5 CPU, 300s | $12-$20 | Default cost/performance posture |
| Minimum | 512 Mi, 0.5 CPU, 900s | 256 Mi, 0.25 CPU, 300s | $5-$10 | Demo-only unless tested under load |

Set cost alerts before deployment and preserve smoke-test output from
`scripts/smoke_test_cloudrun.sh` when changing tiers.
