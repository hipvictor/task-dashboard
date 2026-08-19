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
Jack Knagg→`L3 - Jack Knagg`, Jenny→`L3 - JENNY BATES`, Kyungrae Cho→`L3 - KYUNGRAE CHO`.
Generic fallbacks: `L3 - Song Title`,
`L3 - Community Prayer Name`. Welcome defaults to JONATHAN PERRY when col 8 is "Jonathan".

## Hymn slide spec (for hymns generated with `gen_hymn.py`, not in the library)
Build by cloning a real library hymn deck (e.g. `3152 - Welcome.pro`) so slide geometry matches
the church's actual slides, then re-text. The canonical spec:
- **Stanza breaks:** 4 lyric lines per slide — a full 4-line stanza, or split a longer stanza
  into half-stanzas (4+4). Never more than 4 lines on a slide. (Odd counts: split as sensible;
  default 4-then-remainder.)
- **Verse slide layout (lower third):** black background bar **height 370px, opacity 75%**;
  **Helvetica Bold 55pt** (`\fs110` in RTF); text bounding box **1620 × 325px at x150, y732.7**,
  centered horizontally + vertically. (Geometry is inherited from the donor deck; font is forced
  to 55pt. If a donor's box differs from these px, set the element bounds explicitly.)
- **Title slide — 3 lines:**
  1. Hymn Title
  2. Hymnal + number: UMH → `The United Methodist Hymnal #NNN`; TFWS → `The Faith We Sing #NNNN`;
     W&S → `Worship & Song #NNNN`.
  3. Hymnal color: **Blue Hymnal** (UMH) · **Black Hymnal** (TFWS) · **Green Hymnal** (W&S).
- Always rename the presentation's internal name (field 3) to the hymn title so no donor
  metadata (e.g. "3152 - Welcome") leaks into the imported deck.

## Hymn/deck generation gotchas (each cost a debugging cycle — ProPresenter's SwiftProtobuf
decoder is STRICT; our lenient `pb.py` round-trips things it rejects with `binaryDecoding
error 3`, so "round-trips in pb" ≠ "imports")
- **Never byte-replace text inside a nested protobuf message.** Some text fields mis-parse as
  sub-messages; replacing bytes changes the inner length but not the length prefixes → strict
  decode fails. Fill text via `gen_ctw._fill_cue` (rebuilds the box + reframes correctly).
- **Never clone slide-GROUPS by re-parsing their bytes.** A cueGroup's cue-ref uuid mis-splits
  on re-parse and corrupts on re-encode. Use ONE cueGroup and build its cue-ref list FRESH
  (`pb.mfield(2,[pb.sfield(1,uuid)])`); clone only CUES (`_clone_cue`). This is the `gen_ctw`
  pattern — proven to import.
- **Regenerate the presentation uuid (field 2)** on any cloned-donor deck. A duplicate
  presentation uuid makes ProPresenter treat the import as the donor already in the library
  (slides appear empty / import ignored).
- **Deliver decks ZIPPED.** ProPresenter names an imported `.pro` from its FILENAME, and file
  downloads strip punctuation (a `453 - Title` becomes `453  Title`, `Christ's`→`Christs`). A
  zip preserves the exact inner filename through extraction, so the import lands named right.
- Validate before shipping: round-trip (`pb.encode(pb.parse(x))==x`), every cue-ref resolves,
  arrangement field 17 present, and NO leftover donor text (search for the donor's title/number).

## Weekly content folder & the Run Down
The week's assets usually live in a Drive folder the user shares: the **Run Down** (AV Production
Run Down + Worship Guide), the **CTW doc**, **hymn lyrics** for anything not in the library, a
**children's-time liturgy** (e.g. Backpack Blessing), **series/sermon images**, and **intro
videos**. Enumerate with `search_files parentId='<folder>'`.
- **The Run Down overrides the raw schedule cells.** Late in the week the schedule row is often
  rough/blank (empty welcome/accompanist; a hymn not yet in the library; a `Cathy/Terri` cell that
  fuzzy-matches to the wrong L3). Take welcome/accompanist/invitation/special-music/closing from
  the Run Down's order of worship, and feed `build_week` a corrected CSV row.
- **Hymn not in the library:** build with `gen_hymn.py`, place `<n> - <Title>.pro` in the
  swapcache, and register it — `bw.HYMNS += ["<n> - <Title>.pro"]` before `build_week.build(...)`,
  plus a corrected CSV cell carrying the number so `match_hymn` resolves it. (Don't persist it to
  `library_inventory.json` — it's a built deck, not a church-library file.)
- **Non-CTW liturgy:** `gen_ctw.py --title "<Heading>"` (e.g. Backpack Blessing). Deliver
  standalone (zipped) or insert into the playlist's children's-time slot.

## Media (backgrounds / videos) is NOT edited in the `.pro`
The playlist is media-less and media refs nest length-prefixed file paths — an in-place byte edit
corrupts the framing (SwiftProtobuf `error 3`). Swapping the **Welcome-slide series image** or the
**hook/intro video** is a **manual step in ProPresenter on the church machine** (which holds the
media): drop the `…-Main.jpg` on the Welcome background; drop the intro video into the Hook slot.
Always flag these two in delivery. (A schema-aware media-reference editor is the proper long-term
fix if this needs automating.)
