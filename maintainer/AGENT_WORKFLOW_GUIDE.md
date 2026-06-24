# Agent Task Workflow Tutorial

**Location:** `maintainer/AGENT_WORKFLOW_GUIDE.md`  
**Last Updated:** 2026-06-17  
**Version:** Phase 6 — Agent Workflow Automation

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Task Lifecycle](#task-lifecycle)
5. [Creating Tasks](#creating-tasks)
6. [Agent Operation](#agent-operation)
7. [Automation Flows](#automation-flows)
8. [Troubleshooting](#troubleshooting)
9. [Examples](#examples)

---

## Overview

The **Agent Task Workflow** automates how tasks flow through the decision-analytics-reconstruction project:

- **GitHub Issues** are the single source of truth (SSOT)
- **Labels** (priority, effort, skill, type) categorize work
- **Queue file** (`.claude/agent_queue.json`) ranks ready tasks
- **Agents** read the queue and execute tasks end-to-end
- **Auto-close** workflow closes issues when PRs merge

**No Slack. No custom servers. No chat context needed.**

---

## Architecture

### Components

```
GitHub Issues (SSOT)
    ↓
[queue-sync.yml] — CI workflow regenerates queue on every issue change
    ↓
.claude/agent_queue.json — sorted by priority, ranked by effort
    ↓
Agent Session Start — reads queue, picks highest-priority task
    ↓
Issue Description — agent reads full spec + acceptance criteria
    ↓
Implementation → PR → Merge
    ↓
[auto-close-issues.yml] — CI workflow closes issue + adds status:completed
```

### Files Involved

| File | Purpose |
|------|---------|
| `.github/workflows/queue-sync.yml` | Generates agent_queue.json from GitHub Issues |
| `.github/workflows/auto-close-issues.yml` | Auto-closes issues when PRs merge |
| `.claude/agent_queue.json` | Queue of ready tasks (auto-generated, do not edit manually) |
| `CLAUDE.md` | Protocol: agents read queue at session start |
| `.github/ISSUE_TEMPLATE/*.yaml` | Issue templates (feature, bug, governance, chart-defect) |

---

## Quick Start

### 1. Session Start (Agent)

```bash
$ make session-start
# Review governance/SESSION_HANDOUT.md
# If open_findings: 0, continue to step 2
```

### 2. Read the Queue

```bash
$ jq '.ready_tasks[0]' .claude/agent_queue.json
# Output:
# {
#   "number": 43,
#   "title": "Module A: Re-run population pipeline...",
#   "priority": "p0",
#   "effort": "high",
#   "acceptance_criteria": [
#     "population_master_clean.parquet: rural_low_propensity has pct_rural >= 0.70",
#     "All Module A EDA charts regenerated",
#     "F-051 YAML: status: closed",
#     ...
#   ],
#   "url": "https://github.com/RafaelBraga-Kribitz/..."
# }
```

### 3. Work from Issue Description

Open the issue URL, read the **full spec** + **acceptance criteria**. No other context needed.

### 4. Implement + Test

```bash
# Implement the fix (e.g., re-run Module A pipeline)
$ poetry run python -m module_a_population_segmentation.pipeline.run_pipeline --seed 43
# Verify acceptance criteria are met
$ poetry run pytest module_a_population_segmentation/
```

### 5. Commit & Push

```bash
$ git commit -m "Closes #43 — [brief description]"
$ git push origin [your-branch]
```

### 6. Open PR

Title: `Fix: Issue #43 — Module A segment label fix`  
Body: Must contain `Closes #43` or `Fixes #43`

### 7. Merge & Auto-Close

When PR merges:
- CI runs `auto-close-issues.yml`
- Issue #43 auto-closes
- Label `status:claude-ready` removed
- Label `status:completed` added
- Queue regenerates with next task

---

## Task Lifecycle

### Issue States (Labels)

```
Backlog
├─ status: (none) — spec still being written
│
Ready
├─ status: claude-ready — clear spec, no blockers
│  └─ appears in agent_queue.json
│
In Progress
├─ PR open (manual, agent infers from context)
│
Done
├─ status: completed — issue closed, PR merged
```

### Queue Regeneration

Queue file is **automatically regenerated** when:
- Issue created
- Issue labeled/unlabeled
- PR opened
- PR closed
- Any push to main/claude/* branches

**Do not edit `.claude/agent_queue.json` manually.** It's always stale within seconds of any GitHub activity.

---

## Creating Tasks

### Mode 1: GitHub-Based (Formal Specs)

**Best for:** Complex tasks, detailed requirements, decisions needing review

1. **Go to GitHub Issues** → "New issue"
2. **Select template:** feature.yaml, bug.yaml, governance-finding.yaml, or chart-defect.yaml
3. **Fill in required fields:**
   - Title
   - Problem/description
   - Acceptance criteria (as `- [ ]` checkboxes)
   - Labels: `type:*`, `skill:*`, `effort:*`, `priority:*`
4. **When ready, add label:** `status:claude-ready`
5. **Next agent session** picks it from queue

### Mode 2: Chat-Based (Quick Tasks)

**Best for:** Ad-hoc improvements, urgent fixes, quick validation

1. **In chat:** "Add dark mode support to Quarto report"
2. **Claude auto-files** Issue #NNN with:
   - Title: "[Feature]: Add dark mode support to Quarto report"
   - Description: Full spec from chat context
   - Acceptance criteria: Extracted from requirements
   - Labels: `type:feature`, `skill:module-c`, `effort:medium`, `priority:p1`
   - Status: `status:claude-ready` (if spec is clear)
3. **Next agent session** sees it in queue

---

## Agent Operation

### Session Start Flow

```
1. Agent runs: make session-start
2. Steward role reads governance state
3. If open_findings == 0:
   - Read .claude/agent_queue.json
   - Print: "Next task: #NNN (priority: p0, effort: high)"
   - Print: Issue URL
4. Agent role shifts to Remediator
5. Open issue #NNN, read full spec
6. Implement from description alone
7. Commit "Closes #NNN - [description]"
8. Push → PR → Merge
9. CI auto-closes #NNN
10. Next session: back to step 1
```

### What Agents See

**Agents receive:**
- Issue number
- Title
- Priority (p0/p1/p2)
- Effort (low/medium/high)
- Skills required
- **Full acceptance criteria** (from issue body)
- URL to issue page

**Agents do NOT receive:**
- Chat history (not applicable)
- Prior session context (issue is self-contained)
- Stakeholder feedback (use issue comments for discussion)

### Working from Issue Description

Example issue #43:

```
# Module A: Re-run population pipeline to fix segment label semantic inversion (F-051)

## Problem statement
population_master_clean.parquet was exported before the profile-driven label
assignment (F-039) was applied. As a result, rural_low_propensity is 95% urban
in the actual data (pct_rural = 0.050).

## Root cause
From F-051: canonical parquet generated without running label-reassignment step.

## Fix
1. Re-run Module A pipeline end-to-end with corrected label assignment
2. Verify output parquet: rural_low_propensity has pct_rural >= 0.70

## Acceptance criteria
- [ ] population_master_clean.parquet: rural_low_propensity has pct_rural >= 0.70
- [ ] All Module A EDA charts regenerated with corrected data
- [ ] F-051 YAML: status: closed
- [ ] All Module A tests pass
```

**Agent reads this, understands the task, executes steps 1–4 from "Fix" section, verifies all acceptance criteria are met, commits and opens PR.**

---

## Automation Flows

### queue-sync.yml

**Trigger:** On any issue change (opened, labeled, unlabeled, PR opened/closed)

**Behavior:**
```python
issues = gh api issues --search "is:open label:status:claude-ready"
ready_tasks = []
for issue in issues:
    priority = extract_label(issue, "priority:")  # p0 | p1 | p2 (default: p2)
    effort = extract_label(issue, "effort:")       # high | medium | low
    skills = extract_labels(issue, "skill:")
    acceptance = parse_body(issue, "Acceptance criteria")
    ready_tasks.append({
        number: issue.number,
        title: issue.title,
        priority: priority,
        effort: effort,
        skills: skills,
        acceptance_criteria: acceptance,
        url: issue.html_url
    })

# Sort by priority (p0 > p1 > p2), then by effort (high > medium > low)
ready_tasks.sort()

# Write to .claude/agent_queue.json
write_json(ready_tasks)
```

### auto-close-issues.yml

**Trigger:** On PR merge (if merged, not just closed)

**Behavior:**
```bash
# Extract issue number from PR body
match = pr.body.match(/Closes #(\d+)/)
if match:
    issue_num = match[1]
    github.close_issue(issue_num)
    github.remove_label(issue_num, "status:claude-ready")
    github.add_label(issue_num, "status:completed")
```

---

## Troubleshooting

### Queue Not Updating

**Symptom:** `.claude/agent_queue.json` stale; doesn't match current GitHub Issues

**Diagnosis:**
```bash
# Check when queue was last generated
jq '.generated_at' .claude/agent_queue.json

# Manually trigger queue-sync
gh workflow run queue-sync.yml --ref main
```

**Fix:**
1. Push a commit to trigger workflows
2. Or go to Actions → queue-sync.yml → Run workflow

### Issue Not Appearing in Queue

**Symptom:** Issue has `status:claude-ready` but doesn't appear in `.claude/agent_queue.json`

**Diagnosis:**
1. **Missing labels?** Queue requires ALL of: `type:*`, `skill:*`, `priority:*`, `effort:*`
2. **Typo in label?** Check exact spelling: `priority:p0` (not `priority:P0`)
3. **Body parsing issue?** Acceptance criteria must be under `## Acceptance criteria` heading with `- [ ]` checkboxes

**Fix:**
```bash
# Verify issue has all required labels
gh issue view 43 --json labels

# Re-run queue-sync
gh workflow run queue-sync.yml --ref main
```

### Agent Can't Find Issue

**Symptom:** Queue shows issue #43, but agent clicks URL and issue is deleted/private

**Fix:**
- Issues are immutable once `status:claude-ready` is applied
- If issue needs to change: add comment, agent reads it in PR review
- If issue is wrong: close it, add `status:not-planned`, move to next task

### PR Not Auto-Closing Issue

**Symptom:** PR merged but issue #43 still open

**Diagnosis:**
1. **Missing reference in PR body?** PR must have `Closes #43`, `Fixes #43`, or `Resolves #43`
2. **Workflow disabled?** Check `.github/workflows/auto-close-issues.yml` is not disabled

**Fix:**
```bash
# Manually close issue
gh issue close 43 --reason completed

# Add label
gh issue edit 43 --add-label "status:completed"
```

---

## Examples

### Example 1: Governance Finding (F-051)

**Queue Entry:**
```json
{
  "number": 43,
  "title": "Module A: Re-run population pipeline to fix segment label semantic inversion (F-051)",
  "priority": "p0",
  "effort": "high",
  "skills": ["module-a", "data"],
  "acceptance_criteria": [
    "population_master_clean.parquet: rural_low_propensity has pct_rural >= 0.70",
    "All Module A EDA charts regenerated",
    "F-051 YAML: status: closed",
    "All Module A tests pass"
  ]
}
```

**Agent's Work:**
```bash
$ poetry run python -m module_a_population_segmentation.pipeline.run_pipeline --seed 43
$ poetry run pytest module_a_population_segmentation/
$ vim governance/findings/F-051-segment-label-semantics.yaml  # status: closed
$ git commit -m "Closes #43 — Fix Module A segment label inversion (F-051)"
$ git push origin feature/module-a-fix
# → Open PR → Merge → Issue auto-closes
```

### Example 2: Code Quality Refactor (Phase 4)

**Queue Entry:**
```json
{
  "number": 40,
  "title": "Phase 4: Full code quality audit — ruff, black, mypy, radon, vulture",
  "priority": "p1",
  "effort": "high",
  "skills": ["shared", "infra"],
  "acceptance_criteria": [
    "poetry run ruff check . → 0 errors",
    "poetry run black --check . → 0 reformats needed",
    "poetry run mypy . → 0 errors",
    "poetry run radon cc . -n C → 0 blocks above grade B",
    "make verify exits 0"
  ]
}
```

**Agent's Work:**
```bash
$ poetry run ruff check . --fix
$ poetry run black .
$ poetry run mypy .
$ poetry run radon cc . -n C
$ make verify
$ git commit -m "Closes #40 — Phase 4 code quality audit"
```

### Example 3: Chat-Based Task (Mid-Session)

**User in chat:** "Can we add a sensitivity analysis slider to the Module C report?"

**Claude auto-files Issue #47:**
```
Title: [Feature]: Add sensitivity analysis slider to Module C Quarto report

Labels: type:feature, skill:module-c, effort:high, priority:p2, status:claude-ready

Body:
## Problem statement
The Module C Quarto report is static. Users cannot adjust parameters to see how 
forecasts change. A slider for scenario shock magnitude would be valuable.

## Proposed solution
Add Quarto interactive parameter (`{shiny}`) slider for shock magnitude [0.5, 2.0].

## Acceptance criteria
- [ ] Slider renders in Quarto preview
- [ ] Forecast recomputes when slider moves
- [ ] Default shock magnitude is 1.0
- [ ] Report HTML commits to reports/
- [ ] GitHub Pages deployment reflects change

## Effort estimate
4–6 hours (Shiny integration, parameter propagation)
```

**Next agent session:**
- Reads queue
- Sees #47 (p2, high effort, module-c)
- Opens issue, reads acceptance criteria
- Implements Quarto Shiny slider
- Commits, opens PR, merges
- Issue auto-closes

---

## Best Practices

### For Issue Authors

1. **Be specific.** Vague acceptance criteria = stuck agents
2. **Use templates.** They enforce clarity: feature.yaml, bug.yaml, etc.
3. **Label completely.** Missing labels → issue invisible to queue
4. **Test locally first.** Verify acceptance criteria are achievable before marking `status:claude-ready`
5. **Link related issues.** Use "Related: #NNN" in description if issue depends on another

### For Agents

1. **Read the issue description fully.** Don't invent from queue summary; open the URL
2. **Follow acceptance criteria exactly.** They're the contract
3. **Test before committing.** Verify all acceptance criteria pass
4. **Use "Closes #NNN" in commit message.** Enables auto-close workflow
5. **Don't skip governance.** If finding is involved (like F-051), mark it closed in YAML

### For Reviewers

1. **Queue is automatic.** No manual assignment needed
2. **Accept + merge PRs that satisfy acceptance criteria.** Don't move goalposts
3. **Use issue comments for clarification,** not PR comments (agents won't see them)
4. **Monitor queue generation.** If queue-sync.yml fails, issue won't appear

---

## Integration with CLAUDE.md

The agent task workflow is documented in `CLAUDE.md` under **Phase 6: Agent Task Workflow**. Key points:

- Session start: `make session-start` → read queue if `open_findings == 0`
- Work from issue alone: no chat context needed
- PR must reference issue: "Closes #NNN"
- CI auto-closes on merge
- Next session sees new top task

For full context, see `CLAUDE.md` § Feature work queue → Phase 6.

---

## Monitoring & Maintenance

### Weekly Checks

```bash
# Verify queue generates correctly
$ gh workflow view queue-sync.yml
$ gh workflow runs queue-sync.yml --limit 5

# Check for stalled ready tasks (> 7 days old)
$ gh issue list --search "is:open label:status:claude-ready" \
  --created "<=2026-06-10" --json number,title,createdAt

# Verify auto-close is working
$ gh workflow view auto-close-issues.yml
$ gh issue list --search "is:closed label:status:completed" --limit 5
```

### If Queue Breaks

```bash
# Re-run queue-sync manually
$ gh workflow run queue-sync.yml --ref main

# Check for syntax errors in issue bodies
$ gh issue list --json number,body --search "is:open label:status:claude-ready" | \
  jq '.[] | select(.body | contains("## Acceptance criteria") | not)'

# If stuck, manually regenerate
$ python3 << 'EOF'
import subprocess, json
proc = subprocess.run(["gh", "issue", "list", "--search", "is:open label:status:claude-ready", 
                       "--json", "number,title,labels,body"], capture_output=True, text=True)
issues = json.loads(proc.stdout)
# ... process and write .claude/agent_queue.json
EOF
```

---

## Questions?

Refer to:
- **Governance methodology:** `governance/AUDIT_PROCEDURE.md`
- **Project SSOT:** `PROJECT_CHARTER.md`
- **Workflow state:** `governance/AUDIT_STATE.json`
- **Recent changes:** `governance/CHANGELOG.md`
- **Agent protocol:** `CLAUDE.md`

---

**Last Updated:** 2026-06-17  
**Phase:** 6 — Agent Workflow Automation Complete ✅
