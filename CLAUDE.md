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
- The skill is **assembly, not authorship**: CTW text, hymn picks, liturgist, etc. are decided
  before it runs; planning must flag anything missing/unmatched, never invent it.
- CTW is formatted from the week's doc by `gen_ctw.py` (title + Leader/People exchanges + All;
  liturgist on the title). It is **flexible to any length** — clones content cues and rewrites
  the cue-group display order; works by display order (not storage order) and self-validates.

### Working branch
Develop on `claude/propresenter-playlist-workflow-eonzM`; commit + push when work is complete.
Don't open a PR unless asked.
