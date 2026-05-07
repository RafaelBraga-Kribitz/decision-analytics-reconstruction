# /task-plan

Produces the **approved execution plan** before implementation. Must satisfy plan-first rules. No plan → no dispatch.

---

## Required sections (all mandatory — no section may be blank or have placeholders)

### A. Objective
Clear, single-sentence outcome. One task, one objective.

### B. Context payload (copy from orchestrator output)
```yaml
task_id: "TASK-YYYYMMDD-###"
taxonomy: "<label>"
risk: "low | medium | high"
primary_agent: "<agent slug>"
secondary_agents: []
skills: []
```

### C. Constraints
Time, hardware, "must use Poetry", "no secrets in code", active module series for Module C, etc.

### D. Must-do (numbered)
Numbered list. Each item must be verifiable.

### E. Must-not (numbered)
Explicit anti-goals: no banned terminology, no hard-coded literals, no mixing calibration series, no fixing without root-cause investigation.

### F. Success criteria with quantitative thresholds

| Criterion | Verification command | Expected pass condition | Gate |
|-----------|---------------------|------------------------|------|
| <criterion 1> | `<exact command>` | `<exit 0 / value ≥ X / PASS>` | A1/B1/C1/... |
| <criterion 2> | `<exact command>` | `<expected>` | |

**Rule:** Every criterion MUST have an exact verification command. "Review confirms" or "looks correct" are not valid conditions. If you cannot specify a command, the criterion is incomplete.

### G. TDD plan
- List each function/class/endpoint to be implemented.
- For each: name the test file and test function to write first.
- Confirm: code will be written only after the test fails for the expected reason.

### H. Impact map
- **Files touched:** list every `src/` file expected to change.
- **Schema contracts touched:** yes/no + which contracts.
- **Upstream/downstream:**
  - Does this change outputs consumed by Module B or C? (Module A)
  - Does this change inputs expected from Module A or outputs to Module C? (Module B)
  - Does this change calibration priors or scenario outputs? (Module C)

### I. Todo list (mirror Cursor todos)
Checkboxes aligned with Cursor todo items for this task.

### J. Rollback
Exact steps to revert if `/task-verify` fails.

---

## Approval gate

- **Low risk:** author self-approves after all sections filled with non-placeholder content.
- **Medium/high risk:** human acknowledgment required before dispatch. List open questions explicitly.
- **Never approve:** plan with blank sections, placeholder text, or criteria lacking verification commands.

### Next step
→ **`/task-dispatch`** then **`/task-execute`**.
