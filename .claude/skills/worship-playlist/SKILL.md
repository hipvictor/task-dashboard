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
- The week's content usually lives in a **Drive folder** the user points you to: the **Run Down**
  (AV Production Run Down / Worship Guide), the **CTW doc**, hymn lyrics for anything not in the
  library, a **children's-time liturgy** (e.g. Backpack Blessing), the series/sermon images, and
  intro videos. `search_files parentId='<folder>'` to enumerate it; read the docs you need.
- **The Run Down is authoritative** — the raw schedule cells are often rough or blank this late
  (empty welcome/accompanist, a hymn not yet in the library, a `Cathy/Terri` cell that fuzzy-
  matches wrong). Reconcile against the Run Down's order of worship before planning.

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
- Generate/refresh the CTW `.pro` for the week (see "Liturgy decks" below), with the liturgist
  name (col 12) on the title.
- **Hymn not in the library** (`analyze_week` shows `NO MATCH`): build it with `gen_hymn.py`
  (see the hymn skill / `gen_hymn` docstring), drop the `<n> - <Title>.pro` in the swapcache, and
  **register it so `build_week` matches it** — the matcher reads `data/library_inventory.json`;
  either add the filename to a patched HYMNS list before calling `build_week.build(...)` (import
  it and set `bw.HYMNS+=["<n> - <Title>.pro"]`), and feed a corrected CSV row where the closing/
  opening cell carries the number so `match_hymn` resolves it.
- **Children's-time liturgy** (Backpack Blessing, etc.): same responsive format as the CTW —
  `gen_ctw.py <doc.txt> --title "<Heading>" --out "<Heading>.pro"` (see "Liturgy decks").
- `python3 tools/propresenter/build_week.py --template templates/<standard|communion> \
   --csv <csv> --date "<Date>" --ctw <ctw.pro> --swapcache <dir> --out "<Date>.proplaylist"`
  (add the baptism flag in code for a baptism Sunday so the Baptismal Liturgy is kept).
  When a slot's cell is rough/blank but the Run Down settles it, feed a **corrected CSV row**
  (e.g. welcome=Jonathan, accompanist=Kyungrae Cho, invitation=Cathy) so the matcher resolves it.
- **Media (backgrounds / videos) is NOT edited in the `.pro`.** The playlist is media-less and
  media references nest length-prefixed paths — an in-place edit corrupts the framing (SwiftProto
  `error 3`). Swapping the Welcome-slide series image or the hook video is a **manual step in
  ProPresenter on the church machine** (which holds the media): drop the series `…-Main.jpg` on the
  Welcome background; drop the intro video in the Hook slot. Flag these two in delivery.

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

## Liturgy decks = formatter, not author
The liturgy text is written by humans **before** this skill runs (so are hymn picks, liturgist,
etc.). The skill's job is to *find, match, and lay them out* — and **flag** anything missing or
unmatchable, never invent it. One tool builds every responsive liturgy — the CTW and any
children's-time / blessing liturgy:
- `gen_ctw.py <doc.txt> --liturgist "<col-12 name>" --out CALL\ TO\ WORSHIP-2.pro` — the weekly
  **CTW** (default title "Call To Worship"; keeps the `CALL TO WORSHIP-2` name so `build_week`
  swaps it).
- `gen_ctw.py <doc.txt> --title "Backpack Blessing" --liturgist "You Got This!" --out "Backpack
  Blessing.pro"` — any other **responsive liturgy** (custom heading; names the presentation for
  the title). Feed only the call-and-response the congregation reads; the leader's narrative and
  spoken prayers stay off-screen unless asked.
- It pulls `Leader:` / `People:` exchanges + a closing `All:`. Get the doc via `read_file_content`
  (find by title, e.g. `CTW <MM/DD>` or the week folder); save a `.txt` first. **If the doc isn't
  found / empty / doesn't parse → flag it**, don't proceed on that slot.
- **Flexible length**: rebuilds to any number of exchanges — keeps the title cue, clones a content
  cue (regenerating every UUID) per exchange, fills each, rewrites the cue-group display order +
  cue list, and self-validates (round-trip, canonical/unique UUIDs, no dangling refs).

## Toolbelt (all under tools/propresenter/)
- `analyze_week.py` — pre-build plan + gap flags.
- `build_week.py` — clone template, swap slots, insert community prayer, set special-music +
  retitle, validate, bundle in PP's zip dialect.
- `match_library.py` — hymn (UMH/TFWS/W&S # or title) and name→L3 matching.
- `slot_map.py` — classify template items (cue/fixed/swap).
- `gen_ctw.py` — responsive-liturgy deck (CTW or, with `--title`, any children's/blessing
  liturgy); flexible length, self-validating.
- `gen_hymn.py` — lyrics → hymn deck to the church spec (title + 4-line stanzas @ 55pt) for a
  hymn not in the library; register its filename with `build_week` (see Phase 4).
- `ppzip.py` — ProPresenter ZIP64 writer (required; stock zip won't import).
- `check_sizes.py` — download-truncation guard.
- `pb.py` — protobuf read/encode (lenient parser; see UUID/framing gotchas in CONVENTIONS).
- `templates/{standard,communion}` + `templates/hymn-donor.pro`; `data/library_inventory.json`.
