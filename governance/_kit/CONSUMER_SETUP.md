# Consumer setup

How to wire a project into the governance-bootstrap upstream/downstream sync.

> **TL;DR** — vendor the kit as a `git subtree` at `governance/_kit/`,
> drop in two workflow files, mint one PAT, register your repo in
> `consumers.yaml` here. After that, updates flow both ways automatically.

---

## Prerequisites

- The consumer repo exists on GitHub.
- You have `gh` CLI authenticated locally.
- You can create a fine-grained PAT on the account that owns the
  consumer + hub repos.

---

## Step 1 — Mint the cross-repo PAT

The sync workflows need a token that can:

- read + write the consumer's contents and PRs (`sync-from-upstream` PR);
- read + write the hub's contents and PRs (`propose-upstream` PR).

Create a **fine-grained personal access token**:

1. https://github.com/settings/tokens?type=beta → **Generate new token**
2. **Resource owner**: the account that owns both repos.
3. **Repository access**: select the hub repo (`governance-bootstrap`) **and**
   every consumer repo (`project-a`, `project-b`, …).
4. **Permissions** → Repository permissions:
   - **Contents**: Read and write
   - **Pull requests**: Read and write
   - **Metadata**: Read-only (auto-selected)
5. **Expiration**: pick a rotation cadence you can keep (90 days is fine
   for a personal setup; set a calendar reminder).
6. Copy the token. Save it once — GitHub will not show it again.

Store it as **`GOV_SYNC_TOKEN`** in each consumer **and** in the hub:

```bash
# In each consumer repo:
gh secret set GOV_SYNC_TOKEN --repo RafaelBraga-Kribitz/project-a
# Paste the token when prompted.

# In the hub repo:
gh secret set GOV_SYNC_TOKEN --repo RafaelBraga-Kribitz/governance-bootstrap
```

---

## Step 2 — Vendor the kit

From the consumer repo's root:

```bash
git remote add gov-upstream \
  https://github.com/RafaelBraga-Kribitz/governance-bootstrap.git
git fetch gov-upstream

git subtree add \
  --prefix=governance/_kit \
  gov-upstream main \
  --squash

git push origin main
```

You now have `governance/_kit/` containing every file from this hub repo,
collapsed into a single commit on your `main` branch.

---

## Step 3 — Install the sync workflows

```bash
mkdir -p .github/workflows
cp governance/_kit/templates/.github/workflows/sync-from-upstream.yml \
   .github/workflows/
cp governance/_kit/templates/.github/workflows/propose-upstream.yml \
   .github/workflows/
git add .github/workflows
git commit -m "ci: install governance kit sync workflows"
git push
```

These workflows reference `RafaelBraga-Kribitz/governance-bootstrap`
hard-coded. If you fork the hub, update the `UPSTREAM_REPO:` env block at
the top of each file.

---

## Step 4 — Bootstrap the project's governance state

If this is a brand-new project, run the master prompt to copy the
project-level files (`CLAUDE.md`, `PROJECT_CHARTER.md`, `config/*.yaml`,
finding YAMLs, governance workflow) into place. See
[`BOOTSTRAP_PROMPT.md`](BOOTSTRAP_PROMPT.md) at the hub repo root.

The vendored `governance/_kit/` is the **source of scripts and
templates**. The project-level files are **your** customizations and
are not synced.

Your project's `Makefile` should call kit scripts via the vendored path:

```makefile
audit:
	@python governance/_kit/scripts/check_claude_md.py
	@python governance/_kit/scripts/check_hardcoded_values.py
	# ...etc
```

(Or `cp governance/_kit/templates/Makefile.governance .` and edit the
paths in one place.)

The kit's `_governance_check.py` walks up from `__file__` looking for
`PROJECT_CHARTER.md` or `.git/`, so `REPO_ROOT` resolves to your
project's root, **not** to `governance/_kit/`. No environment variable
is required. (If you want to override, set `GOV_REPO_ROOT`.)

---

## Step 5 — Register the consumer in the hub

Open a PR against this hub repo adding your project to `consumers.yaml`:

```yaml
consumers:
  - repo: RafaelBraga-Kribitz/project-a
    contact: rafaelbragakribitz@gmail.com
    notes: "Production data pipeline"
```

Once merged, every release on the hub will fire a
`repository_dispatch: governance-update` at your project, and your
`sync-from-upstream.yml` workflow will open a sync PR within ~1 minute.

---

## Step 6 — Verify the loop

**Downstream test.** From the hub repo's Actions tab, run
`Fanout governance update` with `ref: main`. Within a minute your
project should show a new PR titled
`Governance kit sync: RafaelBraga-Kribitz/governance-bootstrap@main`.
Merge it. Confirm `governance/_kit/` is now in sync with the hub.

**Upstream test.** In the consumer repo, edit any file under
`governance/_kit/` — e.g. add a comment to
`governance/_kit/scripts/check_hardcoded_values.py`. Commit and push.
Then from the consumer's Actions tab, run
`Propose change to governance kit` with a test title. A PR should open
on the hub repo titled
`[from RafaelBraga-Kribitz/project-a] <your title>`. Close the test PR.

You're wired up.

---

## Daily flow

### Routine work (no kit changes)

Just commit. The consumer's `governance.yml` runs your project's audit
on every PR. Nothing special.

### You discover a bug or want to improve the kit while in project A

1. Edit the file under `governance/_kit/` in a branch.
2. Run `make audit` locally — confirm it still passes.
3. Open a normal PR and merge to project-A's `main`. This fixes A.
4. Actions tab → **Propose change to governance kit** → fill title + body.
5. Approve and merge the hub PR (you're the reviewer).
6. Tag the hub `vX.Y.Z` → fanout fires → projects B and C see sync PRs.

### Hub gets an update from somewhere else

`sync-from-upstream.yml` runs nightly as a safety net (cron `17 5 * * *`
UTC). The `repository_dispatch` from a hub release usually wins first.
Either way, you get a PR — review, merge, done.

---

## Troubleshooting

**`subtree pull` says "fatal: refusing to merge unrelated histories"**.
You vendored the kit without `--squash`, or rewrote the squashed commit.
Fix: re-vendor with `git rm -r governance/_kit && git commit && git subtree add --prefix=governance/_kit gov-upstream main --squash`.

**`fanout-update.yml` runs but the consumer never gets a PR**.
The token doesn't have access to the consumer repo. Re-check the
fine-grained PAT's repository access list, or rotate.

**A `propose-upstream` PR has no diff**.
The consumer's `_kit/` matches hub `main` exactly. Sync first, edit
second.

**Consumer's CI fails after a sync PR**.
Expected: the hub introduced a stricter gate. Either:
- (a) close the offending finding before merging the sync PR, or
- (b) merge anyway and file a new finding to track the gap.

---

## Removing a consumer

Open a PR against this hub repo removing the entry from
`consumers.yaml`. The consumer keeps its vendored `_kit/` but stops
receiving release dispatches. The nightly safety-net cron will still
catch any new tags if you ever re-subscribe.
