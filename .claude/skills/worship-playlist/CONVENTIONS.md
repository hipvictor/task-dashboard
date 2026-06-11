# Worship Playlist — Conventions & Facts

## Schedule column map (0-indexed CSV columns)
| Col | Header | Drives |
|----|--------|--------|
| 1  | Date | row key (e.g. "June 14") |
| 8  | Welcome | Welcome person → `L3 - <NAME>` |
| 10 | Prelude | Accompanist → `L3 - <NAME>` |
| 12 | LITURGIST | name on the CTW title slide |
| 13 | Call to Worship | which CTW doc to regenerate from |
| 15 | Opening Hymn | opening hymn `.pro` (UMH/TFWS/W&S # or title) |
| 19 | Special Music/Anthem | text on the `L3 - Song Title` card (title before " by ") |
| 22 | Preacher(s) | informational (sermon is user-built) |
| 24 | Community Prayer | community-prayer leader → `L3 - <NAME>` |
| 26 / 27 / 33 | Communion Servers / Communion / Communion Music | communion signal |
| 28 | Invitation | invitation person → `L3 - <NAME>` |
| 30 | Closing Hymn | closing hymn `.pro` |

## Template selection
Communion if it's the **1st Sunday of the month** OR any communion column (26/27/33) is
populated; else Standard. Templates live committed at `tools/propresenter/templates/standard`
and `.../communion` (data manifest + fixed `.pro` files, media-less).

## Slot positions within a template (verified)
Swap items in document order: name L3s = **[Welcome, Accompanist, Invitation]**; song items =
**[opening, closing]**; plus the CTW item (`CALL TO WORSHIP-2`) and the `L3 - Song Title`
card. On a typical Sunday the `Baptismal Liturgy` item is replaced by the sequence
**blank · leader-L3 (col 24) · Lord's Prayer · blank**; a baptism Sunday keeps the liturgy.

## Decisions (standing)
- **Bundle everything** (full self-contained export) — turnkey on any machine. Confirmed.
- **Empty source cell** → keep the template default, but flag it in the plan.
- **No confident match** → placeholder + flag; never silently guess (esp. special weeks).
- Sermon slides and the CTW text are user-provided; we don't generate sermons.

## Drive locations (ProPresenter library mirror, owner jonathan@arapahoumc.org)
- Hymns & Songs folder: `1BJda2SqzVIFDON7a8rCNALlhnyGkrfrA`
- Name Lower Thirds folder: `1z0RW_Yi6H7hWh6IQXlunMIVQGkb-_riK`
- Prayer & Communion folder: `1kO-kqsME0CpsfiikUg9qEdh31AIoqIXn`
  (`Lord's Prayer.pro` = `1iAP2bRGMlje51oXp39EYmpT37-qI_h9P`)
Search a folder with `search_files`: `title contains '<name>' and parentId = '<folder>'`.
Fixed items (Worship Blank, Welcome To Worship, sermon shell, web slides, PrePost) are already
in the committed template — only fetch the week's VARIABLE files.

## Gotchas (each one cost a debugging cycle)
- **Zip dialect**: ProPresenter writes a non-standard ZIP64 (stored, ver 45, every entry forces
  0xFFFFFFFF sizes + a 24-byte zip64 extra). Stock zip imports `data` but not the slides →
  "presentation, no slides". Always write with `ppzip.py`.
- **Cue UUID**: an item's cue UUID is `item/1/1` = a 36-char string (`0a26 0a24 <uuid>`). The
  lenient parser can mis-split it; write the string directly (value, msg=None). Never
  mark-all-dirty + re-encode — UUID/RTF strings that coincidentally parse as protobuf get
  corrupted (→ `ProtobufSerializableError`). Mark only edited fields + their ancestor chain.
- **Download truncation**: large `.pro` can download short and still round-trip. Verify every
  fetched file against `get_file_metadata` size (`check_sizes.py`) before building.
- **CSV not markdown**: export the Sheet as `text/csv`; the markdown render drops trailing columns.
- **avmac paths**: absolute refs are `file:///Users/avmac/...` (church machine user). Build by
  editing the relative `Libraries/...` path; the abs URL is derived (only spaces → %20).
- **Validation**: `build_week._validate()` fails the build unless every item has a canonical
  cue UUID and every ref resolves to a bundled file. Don't bypass it.

## Known name → L3 (extend as learned)
Jonathan→`L3 - JONATHAN PERRY`, Aaron→`L3 - AARON MANES`, Cathy→`L3 - CATHY`,
Jack Knagg→`L3 - Jack Knagg`. Generic fallbacks: `L3 - Song Title`,
`L3 - Community Prayer Name`. Welcome defaults to JONATHAN PERRY when col 8 is "Jonathan".
