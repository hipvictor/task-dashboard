# Project memory

## ProPresenter worship-playlist automation
The recurring task here is building weekly ProPresenter `.proplaylist` files for Arapaho UMC
worship services (build at home, load on the church machine; both run PP7).

- **To build a week's playlist, use the `worship-playlist` skill** (`/worship-playlist <date>`).
  It orchestrates the full flow: load context → analyze → clarify (Q&A) → plan → confirm →
  build → self-check → user imports → iterate → fold learnings back in.
- Skill + conventions: `.claude/skills/worship-playlist/` (SKILL.md, CONVENTIONS.md).
- Full spec & decode history: `docs/propresenter-playlist-workflow.md`.
- Tools + committed templates: `tools/propresenter/`.

### Standing facts
- Inputs each week: the Worship Service Schedule (Google Sheet) row + that week's Call to
  Worship doc. Outputs: a self-contained importable `.proplaylist`. Sermon slides and CTW text
  are user-provided.
- Library files come from the church's Drive mirror (owner jonathan@arapahoumc.org). Always
  size-verify downloads — large `.pro` files truncate silently and still parse.
- ProPresenter needs its own ZIP64 dialect (`ppzip.py`) or slides won't import.
- **Open work item**: CTW generation is still a June-14 proof-of-concept; generalizing
  "any CTW doc → CTW slides" is the main piece left for fully one-command builds.

### Working branch
Develop on `claude/propresenter-playlist-workflow-eonzM`; commit + push when work is complete.
Don't open a PR unless asked.
