# governance-bootstrap

A reusable governance kit for software & data-science projects. Drops in a
ratchet-based audit system, a finding/PR workflow, and CI gates for
single-source-of-truth, test coverage, cyclomatic complexity, module size,
dependency structure, and CRAP score.

Built to be **vendored** by every project you own and **kept in sync**
bidirectionally — you fix a bug in the kit while working on _project A_, a
workflow opens a PR back to this hub, on merge it fans out to projects _B_
and _C_ automatically.

---

## What's inside

```
.
├── BOOTSTRAP_PROMPT.md          ← master prompt for a fresh Claude Code session
├── consumers.yaml               ← registry of projects subscribed to updates
├── CONSUMER_SETUP.md            ← how to vendor + subscribe a project
├── .github/workflows/
│   └── fanout-update.yml        ← broadcasts releases to every consumer
└── templates/                   ← the kit itself (vendored by consumers)
    ├── CLAUDE.md                ← agent protocol (anti-patterns + session rule)
    ├── PROJECT_CHARTER.md       ← SSOT skeleton (≤200-line budget)
    ├── AUDIT_PROCEDURE.md       ← Steward / Remediator / Adversary methodology
    ├── CATEGORIES.md            ← sanctioned finding categories
    ├── CONTRIBUTING.md          ← the four rules + finding workflow
    ├── Makefile.governance      ← audit, verify, session-start, session-end, baseline
    ├── .pre-commit-config.yaml
    ├── config/                  ← SSOT scaffolding
    │   ├── parameter_registry.yaml
    │   ├── global.yaml
    │   ├── modeling.yaml
    │   ├── business_rules.yaml
    │   ├── visualization.yaml
    │   ├── paths.yaml
    │   ├── features.yaml
    │   └── quality_gates.yaml
    ├── scripts/
    │   ├── _governance_check.py       ← ratchet helper
    │   ├── _hardcoded_scan.py         ← shared AST visitor
    │   ├── write_audit_state.py
    │   ├── session_start.py
    │   ├── session_end.py
    │   ├── check_closed_findings.py   ← the Adversary
    │   ├── check_claude_md.py
    │   ├── check_finding_coverage.py
    │   ├── check_charter_size.py
    │   ├── check_hardcoded_values.py        ← Python literals
    │   ├── check_notebook_values.py         ← .ipynb cells
    │   ├── check_sql_values.py              ← .sql / .sql.j2
    │   ├── check_parameter_registry.py      ← registry integrity
    │   ├── check_config_orphans.py          ← unreferenced config keys
    │   ├── check_config_references.py       ← typo'd config.X refs
    │   ├── check_test_coverage.py
    │   ├── check_complexity.py
    │   ├── check_module_sizes.py
    │   ├── check_dependency_structure.py
    │   └── check_crap_score.py
    ├── tests/governance/
    │   ├── _ratchet.py
    │   └── conftest.py
    ├── governance/
    │   ├── findings/F-*.yaml    ← one YAML per recurrence invariant
    │   ├── adrs/ADR-TEMPLATE.md
    │   └── migrations/MIGRATION_TEMPLATE.yaml
    └── .github/workflows/
        ├── governance.yml             ← audit + adversary + code-quality jobs
        ├── sync-from-upstream.yml     ← pulls hub updates into the consumer
        └── propose-upstream.yml       ← pushes consumer diffs to the hub
```

---

## The governance discipline (one paragraph)

Every recurrence-prone problem becomes a YAML file under `governance/findings/`.
Each YAML names a `verification_script`. While the finding is `open` the
script reports `[GAP]` and CI stays green; the moment status flips to
`closed`, the same script becomes a hard CI gate — regressing it fails the
PR and reopens the finding automatically. Three roles operate the queue:
the **Steward** (read state, regenerate the session handout), the
**Remediator** (one finding per PR), and the **Adversary** (re-verifies
every closed finding on every PR). The methodology is documented in
`templates/AUDIT_PROCEDURE.md` and the agent protocol in
`templates/CLAUDE.md`.

What gets gated out of the box:

| Gate | Script | Finding |
|---|---|---|
| Hardcoded values in `.py` | `check_hardcoded_values.py` | `F-HARDCODED-VALUES` |
| Hardcoded values in `.ipynb` | `check_notebook_values.py` | `F-NOTEBOOK-HARDCODED-VALUES` |
| Hardcoded values in `.sql` | `check_sql_values.py` | `F-SQL-HARDCODED-VALUES` |
| Parameter registry integrity | `check_parameter_registry.py` | `F-PARAMETER-REGISTRY-INCOMPLETE` |
| Orphan config keys | `check_config_orphans.py` | `F-CONFIG-ORPHANS` |
| Unresolved `config.X` refs | `check_config_references.py` | `F-CONFIG-REFERENCE-RESOLUTION` |
| Line + branch coverage | `check_test_coverage.py` | `F-COVERAGE-GAP` |
| Cyclomatic complexity | `check_complexity.py` | `F-COMPLEXITY-VIOLATION` |
| File + function line budgets | `check_module_sizes.py` | `F-MODULE-SIZE` |
| Dependency layer rules | `check_dependency_structure.py` | `F-DEPENDENCY-VIOLATION` |
| CRAP score (C²·(1−COV)³+C) | `check_crap_score.py` | `F-CRAP-SCORE` |

Thresholds live in `templates/config/quality_gates.yaml` and are themselves
registered in `templates/config/parameter_registry.yaml`. `make baseline`
discovers your project's current values; `make audit` enforces them.

---

## Two consumption modes

### Mode A — vendored (recommended)

The consumer keeps the kit as a `git subtree` at `governance/_kit/`.
Updates flow bidirectionally through GitHub Actions. See
[`CONSUMER_SETUP.md`](CONSUMER_SETUP.md).

```
project-a/
├── governance/
│   ├── _kit/              ← vendored from this repo (subtree, squashed)
│   ├── findings/          ← project-specific, NOT synced
│   ├── adrs/
│   └── AUDIT_STATE.json
└── .github/workflows/
    ├── governance.yml
    ├── sync-from-upstream.yml      ← pulls
    └── propose-upstream.yml        ← pushes back
```

### Mode B — copy-once bootstrap (legacy)

Paste `BOOTSTRAP_PROMPT.md` into a fresh Claude Code session inside an
empty project. The agent copies files into place and replaces the
placeholders. No sync workflows. Good for one-off projects you don't
expect to keep current with the kit.

---

## The bidirectional sync flow

```
   ┌─────────────────────────────────────────────────────┐
   │            governance-bootstrap (this repo)         │
   │                                                     │
   │   templates/   scripts/   consumers.yaml            │
   │                                                     │
   │   .github/workflows/fanout-update.yml               │
   └────┬────────────────────────────────────────────────┘
        │ on tag v*.*.* push:                  ▲
        │   repository_dispatch                │ propose-upstream
        │     event_type=governance-update     │   PR opened on hub
        │     payload.ref=<tag>                │
        ▼                                      │
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │  project-a  │  │  project-b  │  │  project-c  │
   │             │  │             │  │             │
   │  sync-from- │  │  sync-from- │  │  sync-from- │
   │  upstream   │  │  upstream   │  │  upstream   │
   │   → PR      │  │   → PR      │  │   → PR      │
   └─────────────┘  └─────────────┘  └─────────────┘
```

**Downstream (hub → consumers).** Merging a PR on `main` here and pushing
a tag `vX.Y.Z` triggers `fanout-update.yml`, which sends a
`repository_dispatch: governance-update` event to every project in
`consumers.yaml`. Each consumer's `sync-from-upstream.yml` runs
`git subtree pull --squash` against the tagged ref and opens a PR titled
`Governance kit sync: <tag>` on its own `main` branch. The consumer's
existing `governance.yml` CI runs against the PR. Merge to adopt.

**Upstream (any consumer → hub → other consumers).** A developer fixes a
bug in `governance/_kit/scripts/check_x.py` while working in project A.
After landing the fix locally, they run the **Actions → Propose change to
governance kit** workflow, providing a PR title and motivation.
`propose-upstream.yml` clones the hub, rsyncs the consumer's `_kit/`
contents over the hub root, and opens a PR back here. Once reviewed and
merged here → tag → fanout → projects B and C see a sync PR within
minutes.

---

## Quick start

### Subscribe a new project (3 steps)

```bash
# 1. Vendor the kit
cd ~/code/project-a
git remote add gov-upstream https://github.com/RafaelBraga-Kribitz/governance-bootstrap.git
git fetch gov-upstream
git subtree add --prefix=governance/_kit gov-upstream main --squash

# 2. Drop the two sync workflows into your repo
cp governance/_kit/templates/.github/workflows/sync-from-upstream.yml .github/workflows/
cp governance/_kit/templates/.github/workflows/propose-upstream.yml   .github/workflows/

# 3. Add a fine-grained PAT as GOV_SYNC_TOKEN secret in your repo settings
#    (Contents: write, Pull requests: write on this repo + the hub repo)
gh secret set GOV_SYNC_TOKEN < /path/to/pat.txt
```

Then open a PR on **this** repo adding `project-a` to `consumers.yaml`.

Full walkthrough: [`CONSUMER_SETUP.md`](CONSUMER_SETUP.md).

### Bootstrap a project (Mode B)

Paste [`BOOTSTRAP_PROMPT.md`](BOOTSTRAP_PROMPT.md) into a Claude Code
session inside the new project's directory and follow the prompts.

---

## Releases

Every change to `main` should be tagged `vX.Y.Z` to trigger fanout. Until
the project has its first real release, manual `workflow_dispatch` of
`fanout-update.yml` with `ref: main` is the way to push updates.

---

## License

MIT — see [`LICENSE`](LICENSE).
