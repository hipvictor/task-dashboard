---
name: worship-playlist
description: Build an importable ProPresenter .proplaylist for one Sunday at Arapaho UMC from the Worship Service Schedule + that week's Call to Worship doc. Use when the user asks to build / generate / assemble / "do" the worship playlist for a date, or types /worship-playlist <date>. Orchestrates the full flow — load context, analyze, clarify, plan, build, self-check, deliver for import, iterate, and fold learnings back in.
---

# Worship Playlist Builder

Build a turnkey, self-contained `.proplaylist` for one service date. Inputs: the schedule row
for that date + the week's CTW text. Output: an importable bundle the user test-imports at
home, then loads on the church machine. Read `CONVENTIONS.md` (next to this file) for the
column map, library locations, decisions, and gotchas — do not rely on memory for those.

Run the phases in order. Gates (⛔) require the user before continuing.

## Phase 0 — Load context
- Read `docs/propresenter-playlist-workflow.md` (full spec + decoded format + history).
- Read `CONVENTIONS.md` here (column map, Drive folder IDs, decisions, gotchas).
- Read repo `CLAUDE.md` memory for standing notes / per-person or per-date corrections.
- Confirm the tools are present under `tools/propresenter/` and the templates under
  `tools/propresenter/templates/{standard,communion}/`.

## Phase 1 — Analyze the week
- Get the schedule as CSV (export the Sheet to `text/csv`; NEVER the markdown render — it
  drops trailing columns). Save to a temp CSV.
- `python3 tools/propresenter/analyze_week.py <csv> "<Date>"` → build plan: template choice,
  each slot's source value, matched file, and **flagged** gaps (empty cell, no match).

## Phase 2 — Clarify (Q&A)  ⛔
- For every flag or ambiguity, ask the user with `AskUserQuestion` BEFORE planning:
  empty cells (keep template default?), no-match items (placeholder + which file?),
  baptism vs community-prayer Sunday, special weeks (VBS/guest/holiday), unusual hymns or
  names. Carry answers into the plan. Don't guess on anything the schedule doesn't settle.

## Phase 3 — Present the plan  ⛔
- Show the full slot→file plan: template, every swap (source value → matched `.pro`), the
  CTW liturgist + special-music text, community-prayer leader, and anything left as a
  placeholder/default. Iterate with the user until they confirm. Do not build before confirm.

## Phase 4 — Build
- Fetch from Drive ONLY the variable files the plan needs (matched hymns, matched name L3s,
  `Lord's Prayer.pro` for the community prayer). Fixed items come from the committed template.
  Use the folder IDs in `CONVENTIONS.md`. Download as raw bytes (no exportMimeType); decode
  base64 to a file (never hand-transcribe).
- **Verify integrity** (the truncation trap): get each file's size via `get_file_metadata`
  and run `tools/propresenter/check_sizes.py <dir> sizes.json`. Re-fetch any short file. A
  truncated `.pro` still parses — size is the only reliable signal.
- Generate/refresh the CTW `.pro` for the week (see "CTW" below), with the liturgist name
  (col 12) on the title.
- `python3 tools/propresenter/build_week.py --template templates/<standard|communion> \
   --csv <csv> --date "<Date>" --ctw <ctw.pro> --swapcache <dir> --out "<Date>.proplaylist"`
  (add the baptism flag in code for a baptism Sunday so the Baptismal Liturgy is kept).

## Phase 5 — Self-check (you, before sending)
- The build's `_validate()` must pass (canonical cue UUIDs + every ref bundled) — it raises
  otherwise. Then re-extract the output and confirm: title = date; all refs resolve to a
  bundled file (zero dangling); swaps + community-prayer block + special-music card present;
  CTW carries the liturgist; entries CRC-valid; zip is the ProPresenter dialect. Only then
  deliver with `SendUserFile`, naming the two open risks if any remain.

## Phase 6 — User validates on import  ⛔
- User test-imports at home. Watch specifically for: clean import (no
  `ProtobufSerializableError`), hymn lyrics actually showing, the community-prayer sequence,
  liturgist name, special-music title. If anything's off → diagnose → fix → rebuild → redeliver.
  Loop until the user is satisfied.

## Phase 7 — Capture learnings & memory
- Any new bug/insight → update this `SKILL.md`, `CONVENTIONS.md`, and
  `docs/propresenter-playlist-workflow.md` so the next run inherits it.
- Any durable fact (a name→L3 mapping, a recurring placeholder, a schedule quirk, a person's
  spelling) → append to repo `CLAUDE.md`.
- Commit and push to the working branch.

## CTW generation — current limitation
`gen_ctw_june14_poc.py` is a proof-of-concept hardcoded to June 14 (Juneteenth). It is NOT
yet generalized to "any CTW doc → CTW slides." Until it is, generating the CTW for a new date
is itself a build/iterate task within Phase 4: read the week's CTW doc, map its leader/people
responsive sections to the title + body slides, regenerate `CALL TO WORSHIP-2.pro` (targeted
dirty-marking only — never mark-all-dirty; see gotchas), set the liturgist name on the title.
Generalizing this is the top open work item; fold progress back per Phase 7.

## Toolbelt (all under tools/propresenter/)
- `analyze_week.py` — pre-build plan + gap flags.
- `build_week.py` — clone template, swap slots, insert community prayer, set special-music +
  retitle, validate, bundle in PP's zip dialect.
- `match_library.py` — hymn (UMH/TFWS/W&S # or title) and name→L3 matching.
- `slot_map.py` — classify template items (cue/fixed/swap).
- `ppzip.py` — ProPresenter ZIP64 writer (required; stock zip won't import).
- `check_sizes.py` — download-truncation guard.
- `pb.py` — protobuf read/encode (lenient parser; see UUID gotcha).
