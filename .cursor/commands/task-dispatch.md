# /task-dispatch

Assigns **primary specialist**, optional **reviewer**, and **skills** after `/task-plan`.

## Inputs
Paste summary from `/task-intake` + `/task-plan`.

## Required output

### 1. Classification confirmation
Taxonomy + risk from intake.

### 2. Primary agent (exact name from `.cursor/agents/`)
Example: `module-a-specialist`

### 3. Secondary (optional)
`qa-gatekeeper` | `integration-impact-auditor` | `reviewer` — when triggered per routing matrix.

### 4. Skills to invoke
List global Claude skill names or project `.cursor/skills/*/SKILL.md` names (read those files first).

### 5. Execution mode
`subagent_per_step` | `single_session` — per task size.

### 6. Handoff notes
What the specialist must read first (paths).

### Next step
→ **`/task-execute`**
