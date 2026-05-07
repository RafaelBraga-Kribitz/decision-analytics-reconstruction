# Agent instructions (PARAGUAY_ELLECTION)

This repository uses a **project-local orchestration harness** for AI-assisted work.

## Start here

1. Read `**docs/ai_harness/README.md`** — operator workflow and failure recovery.
2. Follow **plan-first** rules in `**.cursor/rules/00-plan-first-governance.mdc`** (always applied in Cursor).
3. Use slash-style command templates in `**.cursor/commands/**` (`task-intake` … `task-complete`).
4. Routing and specialists: `**docs/ai_harness/routing-matrix.md**` and `**.cursor/agents/**`.

## Project skills

- **Cursor:** `.cursor/skills/project-*/SKILL.md`
- **Claude (mirror):** `.claude/skills/project-*/SKILL.md` — keep in sync.

## Scope source of truth

Internal specs live under `**project_scope/`** (may be gitignored in this clone). Terminology and quality gates follow `**scope_master_reconstruction_project.md**` §11–12 and module scope files.

## Graphify knowledge graph (always-on context)

- The project knowledge graph lives in `**graphify-out/**`.
- Before architecture or cross-module reasoning, read `**graphify-out/GRAPH_REPORT.md**` first.
- Keep graph context fresh after code changes with `**graphify update .**`.
- Git hooks are enabled via `**graphify hook install**` so post-commit and post-checkout refreshes run automatically.
- Cursor always-on awareness is enforced by `**.cursor/rules/graphify.mdc**`.
- Claude always-on awareness is enforced by `**CLAUDE.md**` plus `**.claude/settings.json**` PreToolUse hook.