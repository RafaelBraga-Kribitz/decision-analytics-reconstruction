# Cloud Run Deployment Checklist

Complete verification before going live.

---

## Pre-Deployment (Local)

- [ ] Code committed to `main` branch
- [ ] All tests pass: `make test` (806 tests, 87% coverage)
- [ ] Linting clean: `make lint`
- [ ] Type checking clean: `make typecheck`
- [ ] CI workflow passes on GitHub
- [ ] Docker images build locally:
  - [ ] Module A: `docker build -f docker/Dockerfile .`
  - [ ] Module B: `docker build -f docker/Dockerfile.module-b .`
- [ ] Environment configured:
  - [ ] `gcloud` CLI installed
  - [ ] `gcloud auth login` completed
  - [ ] Docker daemon running
  - [ ] GitHub repo settings accessible

---

## GCP Setup

- [ ] GCP project created with billing enabled
- [ ] **Artifact Registry:**
  - [ ] `make setup-artifact-registry GCP_PROJECT=<id>` executed successfully
  - [ ] Repository created in eu-west3
  - [ ] Cloud Storage bucket created with versioning
  - [ ] APIs enabled (Cloud Run, Artifact Registry, Cloud Build, Cloud Logging)

- [ ] **Workload Identity (for GitHub Actions):**
  - [ ] OIDC provider configured
  - [ ] Service account created with required roles:
    - [ ] `roles/run.admin`
    - [ ] `roles/artifactregistry.writer`
    - [ ] `roles/storage.admin`
    - [ ] `roles/logging.logWriter`
  - [ ] Workload Identity binding created
  - [ ] (Optional but recommended) GitHub OIDC trust relationship verified:
    ```bash
    gcloud iam service-accounts get-iam-policy \
      github-actions-deployer@<PROJECT>.iam.gserviceaccount.com
    ```

---

## Deployment

### Module A (Streamlit)

- [ ] **Deploy:** `make deploy-module-a GCP_PROJECT=<id>`
  - [ ] Docker image built
  - [ ] Image pushed to Artifact Registry
  - [ ] Cloud Run service created
  - [ ] URL captured (printed at end)
  
- [ ] **Verify:**
  - [ ] Service shows "Ready" in Cloud Console
  - [ ] Health check (root `/`): `curl -s https://<URL>/ | head -20`
  - [ ] Dashboard loads in browser (may take 30–60s on first load)
  - [ ] Sidebar interactive (cluster selector works)

### Module B (FastAPI)

- [ ] **Deploy:** `make deploy-module-b GCP_PROJECT=<id>`
  - [ ] Docker image built
  - [ ] Image pushed to Artifact Registry
  - [ ] Cloud Run service created
  - [ ] URL captured (printed at end)

- [ ] **Verify:**
  - [ ] Service shows "Ready" in Cloud Console
  - [ ] Health check: `curl -s https://<URL>/healthz | jq`
    - Expected: `{"status":"ok","module":"module_b_resource_allocation","version":"0.1.0"}`
  - [ ] API docs load: `https://<URL>/docs`
  - [ ] Allocation endpoint responds: `curl -s https://<URL>/allocation/baseline | jq '.row_count'`
    - Expected: `2772` (or appropriate row count)

---

## Smoke Tests

- [ ] **Run smoke tests:** 
  ```bash
  make smoke-test \
    MODULE_A_URL=https://module-a-streamlit-xxxxx.run.app \
    MODULE_B_URL=https://module-b-fastapi-xxxxx.run.app
  ```
  - [ ] Module B health check passes
  - [ ] Module B allocation endpoint returns data
  - [ ] Module A root endpoint responds (Streamlit)

---

## Post-Deployment

### Monitoring

- [ ] **Cloud Logging:**
  - [ ] View logs: 
    ```bash
    gcloud logging read "resource.labels.service_name=module-a-streamlit" --limit 10
    gcloud logging read "resource.labels.service_name=module-b-fastapi" --limit 10
    ```
  - [ ] No error patterns in recent logs
  - [ ] Request/response times reasonable (~200–500ms for B, ~1–2s for A)

- [ ] **Cloud Console:**
  - [ ] Services tab shows both services as "Ready"
  - [ ] Revisions tab shows latest deployment
  - [ ] Metrics tab shows traffic, response latencies, error rates

### Documentation

- [ ] **README updated:**
  - [ ] Deployment section mentions new Cloud Run URLs (or badges updated)
  - [ ] Legacy endpoints (Render, Railway) still functional (parallel infra)
  - [ ] Cost estimation documented

- [ ] **Team notified:**
  - [ ] Deployment URLs shared with stakeholders
  - [ ] API docs link provided to integration teams: `https://<MODULE_B_URL>/docs`
  - [ ] Dashboard link provided to analysts: `https://<MODULE_A_URL>/`

---

## Troubleshooting During Deployment

| Issue | Diagnosis | Action |
|-------|-----------|--------|
| Docker build fails (permission denied) | Daemon not running or wrong credentials | `docker ps` to verify; `gcloud auth configure-docker` |
| Push to Artifact Registry fails (403) | Service account permissions insufficient | Verify `artifactregistry.writer` role on service account |
| Cloud Run deployment times out | Image too large or entrypoint issue | Check Dockerfile; simplify base image if needed |
| `/healthz` returns 503 | Service not ready or crashing | `gcloud run services describe <service> --region=europe-west3` for status; check logs |
| Smoke test fails (timeout) | Streamlit or FastAPI slow to start | Retry after 2–3 minutes; check Cloud Run revision for resource constraints |

---

## Rollback Procedure

**If deployment unstable:**

```bash
# Immediate rollback to previous revision
make rollback-module-a GCP_PROJECT=<id>
make rollback-module-b GCP_PROJECT=<id>
```

**Manual traffic split (for gradual rollback):**
```bash
# 50% traffic to old, 50% to new
gcloud run services update-traffic module-a-streamlit \
  --region=europe-west3 \
  --project=<PROJECT> \
  --to-revisions=<OLD_REV>=50,<NEW_REV>=50
```

**Delete service (if critical issue):**
```bash
gcloud run services delete module-a-streamlit --region=europe-west3 --quiet
```

---

## Sign-Off

- [ ] **Technical lead:** Reviewed logs, confirmed no errors
- [ ] **Product:** Verified dashboard and API work end-to-end
- [ ] **Security:** Confirmed no secrets in logs or environment
- [ ] **Operations:** Documented rollback procedure, oncall knows how to respond

---

**Deployment Date:** ____________  
**Deployed By:** ____________  
**Verified By:** ____________  
**Notes:** __________________________

---

**Last updated:** 2026-05-15
