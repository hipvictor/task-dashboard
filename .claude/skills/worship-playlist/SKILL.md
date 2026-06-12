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
- Always read (the per-run essentials): `CONVENTIONS.md` here (column map, Drive folder IDs,
  decisions, gotchas) and repo `CLAUDE.md` memory (standing notes, per-person / per-date
  corrections).
- Consult `docs/propresenter-playlist-workflow.md` (full spec + decoded format + history)
  **only when something the conventions don't settle comes up** — a new format quirk, an
  import failure, an unfamiliar element. Don't read it end-to-end every run.

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

## CTW = formatter, not author
The CTW text is written by humans **before** this skill runs (so are hymn picks, liturgist,
etc.). The skill's job is to *find, match, and lay them out* — and **flag** anything missing
or unmatchable in planning, never invent it. For the CTW:
- `gen_ctw.py <doc.txt> --liturgist "<col-12 name>" --out CALL\ TO\ WORSHIP-2.pro` reads the
  week's CTW doc, pulls the `Leader:` / `People:` exchanges + closing `All:`, and lays them
  into the deck. Title slide = "Call To Worship" + the liturgist; scripture/theme/rubric stay
  doc-only.
- Get the doc text via `read_file_content` on the week's CTW doc (find it by title `CTW
  <MM/DD>`); save to a `.txt` first. **If the doc isn't found / is empty / doesn't parse →
  flag it in the plan**, don't proceed on that slot.
- **Flexible length**: it rebuilds the deck to any number of exchanges — keeps the title cue,
  clones a content cue (regenerating every UUID) once per exchange, fills each, and rewrites
  the cue-group display order + cue list. Works by the cue-group's DISPLAY order (storage
  order differs), and self-validates (round-trip, canonical/unique cue UUIDs, no dangling
  refs). Verified for 2 / 4 / 6 exchanges.

## Toolbelt (all under tools/propresenter/)
- `analyze_week.py` — pre-build plan + gap flags.
- `build_week.py` — clone template, swap slots, insert community prayer, set special-music +
  retitle, validate, bundle in PP's zip dialect.
- `match_library.py` — hymn (UMH/TFWS/W&S # or title) and name→L3 matching.
- `slot_map.py` — classify template items (cue/fixed/swap).
- `gen_ctw.py` — CTW doc → CTW deck (formatter; ≤4 exchanges, flags overflow).
- `ppzip.py` — ProPresenter ZIP64 writer (required; stock zip won't import).
- `check_sizes.py` — download-truncation guard.
- `pb.py` — protobuf read/encode (lenient parser; see UUID gotcha).
- `gen_ctw_june14_poc.py` — superseded by `gen_ctw.py`; kept for reference only.
