# ProPresenter Playlist Workflow — Project Brief

> Goal: Build worship-service ProPresenter playlists **at home** and load them on the
> **church computer**. Both machines run **ProPresenter 7**.
>
> Status: **Format reverse-engineered from a real church playlist.** Ready to prototype
> the generator. See Section 7 for the decoded format.
>
> Last updated: 2026-06-10

---

## 1. The Goal (in the user's words)

Take recurring liturgical/service elements — e.g. a **Call to Worship** formatted in our
*typical format* — plus the other elements of a service, and **assemble them into a
worship-service playlist** automatically, instead of hand-building every slide each week.

Long-term this becomes: paste weekly inputs (lyrics, readings, order of service) →
get an importable ProPresenter file → do final visual tweaks in-app.

---

## 2. How ProPresenter Handles Home → Church Transfer

ProPresenter is built for the "edit at home, present at church" pattern. Two approaches:

### Option A — Export / Import a Playlist Bundle (simplest; recommended to start)
- **At home:** build playlist → `File → Export → Playlist` → **check "include media"** →
  save the `.pro7plx` to USB or cloud (Dropbox/Drive/iCloud).
- **At church:** double-click the `.pro7plx` (or `File → Import`) → it rebuilds the playlist
  with all slides and media.
- Leave media *unchecked* only if the church machine already has those exact media files
  (smaller file, but risks missing-media placeholders).

### Option B — Sync Repository (best once this is a weekly habit)
- Settings → **Sync** tab → point both machines at a shared repository (e.g. a Dropbox folder).
- Home: select Playlists + Media + Library → **"Sync up to repository."**
- Church: **+** to add that repository → select options → **"Sync Down From Repository."**
- ⚠️ **"Replace My Files" DELETES** anything on the target not in the repository. Leave it
  **unchecked** unless you intend a full mirror — otherwise you can wipe the church's content.

---

## 3. Gotchas to Plan Around

| Issue | Mitigation |
|---|---|
| **Version mismatch** | Confirm both machines are the same PP7 version (ideally same minor). A newer-version bundle may not open on an older install. Check `ProPresenter → About` on both. |
| **Fonts** | Bundles carry slides + media but **not fonts**. Use fonts installed on both machines, or install matching fonts at church. |
| **Screen size / resolution** | Home screen geometry may differ from the church projector/LED wall. Verify text-box / lower-third alignment on arrival. |
| **Themes / Looks / Stage layouts** | Don't always travel inside a playlist bundle. Export separately or rely on Sync. |
| **Media not included** | If exported without media, the church machine must already have the exact files. |
| **Licensing** | Home and church installs are separate licenses — fine for this workflow. |

---

## 4. What Claude Can Actually Generate

The reason this is worth automating: the file formats are open enough to generate directly.

- **Content shaping (any version):** Turning lyrics / Scripture / sermon points / order of
  service into properly chunked slides (verse/chorus breaks, line counts, section labels) is
  pure text work — fully doable.
- **ProPresenter 6 (`.pro6`):** Human-readable XML. Trivial to generate from scratch.
  Reference libs: `propresenter_lib2`, `featherbear/python-propresenter`. *(We are on PP7, so
  this is fallback/reference only.)*
- **ProPresenter 7 (`.pro7` / `.pro7plx`) — OUR TARGET:** Binary **Google Protocol Buffers**.
  Not human-readable, but the schema is reverse-engineered and community-proven:
  - `.proto` schema: https://github.com/greyshirtguy/ProPresenter7-Proto
  - Outline → presentation builder (Electron, proof it works): https://github.com/cgarwood/propresenter-presentation-builder
  - Multi-language importer example: https://github.com/JacobBaartse/MultiLanuageProPresenter
  - Format deep-dives: https://greyshirtguy.com/blog/pro7fileformat1/ and …/part-2/
  - Approach: compile the `.proto` with `protoc`, generate code, emit valid `.pro7` files from
    plain-text inputs.

### What WON'T help
- **Official ProPresenter API (7.9+):** Local-network HTTP API that only *controls a running
  instance* (trigger next slide, fire macros). It cannot build a playlist remotely and does
  **not** bridge home → church. Wrong tool for this goal.
  Docs: https://jeffmikels.github.io/ProPresenter-API/Pro7/
- **No live testing here:** Claude's environment has no ProPresenter installed. Anything
  generated must be **test-imported on the HOME copy first** before it touches the church machine.
- **Unofficial schema = small corruption risk.** Always keep backups; always home-test first.

---

## 5. Proposed Build (when we resume)

A generator where weekly inputs (lyrics + order of service, in the church's typical format)
produce an importable `.pro7` presentation or full `.pro7plx` playlist, refined in-app afterward.

Suggested first milestone: **one element end-to-end** — e.g. a single Call to Worship →
one `.pro7` file → test-import on the home machine → confirm formatting matches "our typical
format" → then scale to the full service playlist.

---

## 6. When We Resume — Checklist (what to bring)

1. **One real example of the "typical format"** — e.g. an existing Call to Worship as currently
   laid out: the text + how it's split across slides (lines per slide, leader/congregation
   split, headers). A screenshot or exported slide is ideal.
2. **A sample order of service** — the elements in sequence (Call to Worship, hymns/songs,
   Scripture reading, Confession, Doxology, sermon title slide, Benediction, etc.).
3. **Exact PP7 version number on BOTH machines** (`ProPresenter → About`) — to match output
   format and flag any mismatch.

With those three, Claude can scaffold the generator and validate via a single home-machine
test-import before trusting it for a live service.

---

## 7. DECODED FORMAT (from a real church playlist export)

We analyzed an actual exported playlist (`June_14.proplaylist`, the "Standard Worship
Service"). This confirms exactly how the church's files are built. **This is the spec the
generator targets.**

### 7.1 `.proplaylist` container
- A **ZIP64 archive, stored (no compression)**. Note: ProPresenter writes a non-standard
  central directory — stock `unzip`/Python `zipfile` choke on it ("overlapped components" /
  "corrupt zip64"). Extract by **scanning local file headers** (`PK\x03\x04`) and reading
  ZIP64 sizes from each entry's extra field (id `0x0001`). A working extractor exists in the
  session history; re-create it if needed.
- Contents: **one `.pro` file per presentation** referenced in the service, **plus a `data`
  manifest** (the playlist itself).

### 7.2 `data` manifest (the playlist)
- Protobuf. Encodes an **ordered list of groups and items**:
  - **Group headers double as production notes/cues**, e.g.
    `"Hymn #1 - REMINDER: CLICK TO NEXT SLIDE ON FIRST LETTER OF LAST WORD"`,
    `"Children's Time - PUT EACH SLIDE UP FOR ABOUT 15 SECONDS"`,
    `"Prelude & Call To Worship"`.
  - Each **item** carries: a UUID, a display name, and a reference to its `.pro` by both a
    relative library path and an absolute `file:///Users/avmac/Documents/ProPresenter/...`
    URL. ⚠️ The church machine's user is **`avmac`** — absolute paths are machine-specific;
    rely on the relative `Libraries/...` paths when generating.
- **Playlist title (display name):** stored in the `data` manifest as a string leaf at
  field path `3/12/1/2`. Set this to the service date (e.g. "June 14", or "June 14 v2"
  when versioning) when generating.
- **Library folders in use:** `Hymns & Songs`, `Name Lower Thirds`, `Worship Service Setup`,
  `Slideshows`. (Lower-thirds `L3 - …` files are reused every week.)

### 7.3 `.pro` presentation
- Protobuf wrapping slides. Each text element's content is stored as **RTF** (not plain text).
  - Styling lives in the RTF: `\qc` (center), `\fsNN` (size in **half-points** — `\fs110` =
    55pt), bold via font `Helvetica-Bold`, white text. Fonts seen: Helvetica / Helvetica
    Neue / Times.
  - RTF escapes to handle: `\'92` = curly apostrophe, `\'97` = em dash, `\'a0` = non-breaking
    space.

### 7.4 The Call to Worship "typical format" (decoded sample)
A responsive reading. Structure observed:
- **Title slide:** `Call To Worship` / subtitle `Led By VBS Students` (~55pt, bold, centered).
- **Reading slides** (~65–70pt, centered) alternating **`Leaders:`** and **`All:`** parts,
  with the congregation's `All:` response often emphasized. The liturgy is split across
  several slides (one thought per slide), with a Scripture verse slide
  (e.g. *Philippians 4:13*) called out for a unison reading.

### 7.5 Recommended implementation strategy → **template-and-replace**
Rather than build `.pro` files from scratch via the raw protobuf schema (flexible but
higher corruption risk), **clone the church's real `.pro` files as templates and swap the
RTF text per slide**, then reassemble the `.proplaylist` ZIP. This preserves their exact
theme/fonts/layout and is the lowest-risk path. The greyshirtguy proto schema stays as a
fallback for structural edits the template approach can't reach.

**Open question for next session:** how will weekly liturgy be supplied to the generator?
(e.g. a plain-text file with `Leader:` / `All:` markers, a Word doc, a Google Doc, a
spreadsheet.) That choice drives the input parser.

---

### 7.6 STYLING IS IN NATIVE "RUNS", NOT THE RTF (important)
ProPresenter 7 does NOT render slide styling from the RTF. Each text element's attributes
message (container fn=3) holds:
- `fn=1` default font for the whole element (e.g. title uses `Helvetica-Bold` -> whole slide
  bold, no runs).
- repeated `fn=13` **runs**: each has a range (`fn=1`: {fn=1 start, fn=2 end}) and a font
  (`fn=12`: {fn=1 PostScript name, fn=2 size f64, fn=8=1 bold flag, fn=4=1 italic flag,
  fn=9 display name}). Character indices count EVERY visible char (spaces, nbsp, line breaks
  each = 1).
When regenerating slide text you MUST regenerate these runs to match the new character
offsets, or bold/italic is lost (first attempt edited only the RTF -> all type came out
regular). `tools/propresenter/pb.py` has `make_run(...)`, validated byte-exact against the
original runs. Church convention: Leader prompts regular, People/All responses bold.


## 8. THE LIBRARY (pre-built reusable pieces) + the data pipeline

We confirmed the full source pipeline. Three connected sources:

### 8.1 Planning spreadsheet — "AUMC Worship Service Schedule"
- Google Sheet ID `16-r_WbF7S5Nbz9zj4GTiatqe0OGAGgVp6W1nAHdBvtE`, tabs by year (2017–2026).
- One row per Sunday. Column map (from the worship-planning skill's key file):
  A/0 Point Person · B/1 Date · D/3 Sermon Series · H/7 Staff Out · I/8 Welcome ·
  K/10 Prelude · **M/12 Liturgist** · **N/13 Call to Worship** · O/14 Hymn Leader ·
  P/15 Opening Hymn · Q/16 Children's Sermon · T/19 Special Music · U/20 Scripture ·
  W/22 Preacher · X/23 Sermon Title · **Y/24 Community Prayer** · AB/27 Communion ·
  AC/28 Invitation · AD/29 Generosity · AE/30 Closing Hymn · AF/31 Benediction ·
  AG/32 Postlude.
- The `Call to Worship` cell holds a reference (e.g. `CTW 06/14`) that points to a Google
  Doc in Drive containing the actual responsive-reading liturgy text. Resolve doc → text.
- ⚠️ Point Person (col A) ≠ Liturgist (col M). Col L is blank.

### 8.2 ProPresenter library — MIRRORED ON GOOGLE DRIVE
The church's `~/Documents/ProPresenter/Libraries` is backed up to Drive under
**"ProPresenter Files / Libraries"** (folder id `1zK9MxOrGdaFWZYy40cr7O5ouzBfvmfYi`), so the
full inventory is readable via the Drive connector. Category folders:
- **Hymns & Songs** (~200 `.pro`) — numbered UMH/TFWS/W&S hymns + named songs.
- **Name Lower Thirds** (~154 `.pro`) — `L3 - [Name]` for people + utility L3s
  (Scripture Reading, Song Title, Children's Time, Memorial, etc.).
- **Worship Service Setup** (Welcome, Generosity, Invitation, Worship Blank, Children's
  Pickup, Web Divide), **Prayer & Communion**, **Calls to Worship**, **Sermon Slides**,
  **Slideshows** (AUMC PrePost Slides, Web Slides Out).
- Plus a `LibraryData` index file.

### 8.3 Reuse-first strategy
**Most of a service already exists as files — reference, don't recreate.** A typical service's
hymns, lower-thirds, and setup slides each correspond to an existing library file, so the
generator references them. The genuinely new content each week is the Call to Worship liturgy
(generated from the linked CTW doc); the sermon is owned by the user.

> ⚠️ **Provenance note (re-corrected 2026-06-10):** these June 14 values are **REAL**, read
> column-by-column from the AUMC Worship Service Schedule sheet (§8.5): Liturgist **Gabe
> Meadows** (col M), Opening Hymn **"UMH 519, Lift Every Voice and Sing"** (col P), Closing
> Hymn **"TFWS #2172 We Are Called"** (col AE). An intermediate draft wrongly labeled them
> "fabricated" — that was an over-correction after context loss dropped the provenance link.
> The one genuine error: **W&S 3004 "Step By Step" is June 7's closing hymn, not June 14's**,
> so the earlier "June 14 had 3 songs" conflated two adjacent weeks. June 14 has 2 hymns
> (519 opening, 2172 closing); special music that week is the anthem "The Road Home."

So the generator pipeline is:
1. Read spreadsheet row for the target date → order of service + names/hymns.
2. Fuzzy-match each item to an existing `Libraries/<category>/<file>.pro` (e.g. "UMH 519",
   "TFWS #2172", person names → `L3 - NAME.pro`).
3. Generate ONLY the genuinely new pieces (Call to Worship from the linked doc; sermon title)
   via the template-and-replace approach (Section 7.5).
4. Assemble the `data` manifest in service order, zip into a `.proplaylist` (ZIP64/stored).

Paths stay relative (`Libraries/...`) so the bundle is portable between the home machine
(`/Users/jonathan/...`) and church machine (`/Users/avmac/...`).

**Dependency:** matching relies on the Drive mirror of the library staying reasonably current.

### 8.4 Generator content rules (what to build vs. placeholder vs. skip)
User-specified handling for each element type:
- **Hook (video):** when the Hook/Visual column is a video, insert a **labeled placeholder
  slide** only (e.g. "HOOK VIDEO — add later"). Do NOT source or embed the video; the user
  adds the actual media afterward.
- **Sermon slides:** **do NOT generate.** The user builds the sermon deck themselves and adds
  it on Sunday. The generator leaves at most a placeholder/section marker so the service order
  stays intact. (The `Sermon Slides` library folder is therefore not auto-pulled.)
- **Musical items (Prelude, Special Music/Anthem, Postlude):** reference the performer's
  existing `L3 - <Name>.pro` lower-third if present, but do NOT generate lyric/content slides —
  these are live performances.
- **Generate new content only for:** the weekly **Call to Worship** (from the linked Drive
  doc) and any other genuinely new text element with no library match. Everything else is
  reference-an-existing-file assembly.

---

## 9. PROGRESS LOG

### ✅ Milestone 1 — Slide generation + packaging (VALIDATED on home machine, 2026-06-10)
First end-to-end proof of concept built and **confirmed working by test-import on the user's
home ProPresenter**.

What was proven:
- **`tools/propresenter/pb.py`** — schema-free protobuf codec, byte-exact round-trip on all
  real `.pro`/`data` files. Includes `make_run(...)` for building styling runs.
- **Generated a new Call to Worship** (`tools/propresenter/gen_ctw_june14_poc.py`) for
  June 14 (Juneteenth / Phil 2) via **template-and-replace** on `CALL TO WORSHIP-2.pro`:
  replaced text in 5 slide slots, preserving fonts/sizes/centering/white color.
- **Styling fix:** first attempt edited only the RTF → all bold lost. Root cause: styling is
  in native `fn=13` character-range runs (see §7.6), not the RTF. Regenerated the runs to
  match new text offsets → **Leader regular, People/All bold** (church convention). Confirmed
  correct on import.
- **Playlist title** renamed via the manifest (`data` field `3/12/1/2`):
  "Standard Worship Service" → "June 14 v2". Confirmed it shows in the library.
- **Packaged** a valid `.proplaylist` (standard ZIP, stored) that ProPresenter imports cleanly.

Delivered bundle: `June 14 v2.proplaylist`.

### ▶ Milestone 2 — Assemble the manifest from the spreadsheet (IN PROGRESS)

### 🏗️ Milestone 2 — ARCHITECTURE DECIDED (template-swap)
Per the user:
- **Two base template playlists**: **Standard** and **Communion**. Communion = the **first
  Sunday of the month**; the generator picks the template by date.
- **Swap every week** (everything else stays fixed from the template):
  1. **Call to Worship** — generate fresh from the linked CTW Drive doc (Milestone 1, done).
  2. **Hymns/songs** — match spreadsheet hymn number/title -> `Libraries/Hymns & Songs/*.pro`.
  3. **People lower-thirds** — liturgist, preacher, children's sermon, community prayer, etc.
     -> `Libraries/Name Lower Thirds/L3 - NAME.pro`.
- **Do NOT** generate the sermon title slide or sermon deck (user handles the sermon).

**Matcher DONE** (`tools/propresenter/match_library.py`), validated on **example inputs**
(NOT a real service row — see provenance note in 8.3): "UMH 519..." -> `519 - Lift Every
Voice.pro`, "TFWS #2172..." -> `2172 - We Are Called.pro`, name -> `L3 - NAME.pro`, etc.
Logic resolves hymn number→file and name→L3 against the live library inventory; once a real
weekly-input source exists, re-validate against an actual row. Low-confidence matches should
be surfaced for review, not silently guessed.

**NEXT INPUT NEEDED:** the two real template playlists (export "Standard" and "Communion"
as `.proplaylist`). Then define how each swap-slot is identified within the template
(by its group header / item role) so the generator knows which item to replace.


**Manifest structure decoded** (the `data` protobuf):
- Playlist node at `root.fn3.fn12.fn1` = { `fn1` uuid, `fn2` display name, `fn13` children }.
- `fn13.msg` = ordered list of `fn=1` items. Three item types:
  - **GROUP** (section header / production cue): `fn1` uuid, `fn2` name, `fn3` marker.
  - **PRES** (presentation): `fn1` uuid, `fn2` name, `fn4` reference holding the
    `Libraries/<cat>/<file>.pro` relative path (twice) + a `file://` absolute URL.
  - **VIDEO**: `fn1` uuid, `fn2` name, `fn5` media element (mp4 path, codec, etc.).

**Builder DONE + verified** (`tools/propresenter/build_manifest.py`):
- `pb.clone` / `pb.mark_all_dirty` added to the codec; rebuilding `fn13` from clones is
  byte-identical to the original (proves faithful (de)construction).
- `build(template_data, playlist_name, spec)` assembles a manifest from a spec list of
  GROUP/PRES items: clones templates, assigns fresh unique UUIDs, sets names + library
  paths + home `file://` URLs. Output parses cleanly; UUIDs verified unique.
- Gotcha fixed: editing a nested leaf requires marking the whole item subtree dirty
  (`mark_all_dirty`), else the re-encoder emits the template\'s old nested bytes.

**Remaining for a fully importable spreadsheet-driven bundle:**
1. Map spreadsheet row -> ordered spec; fuzzy-match items to `Libraries/*.pro`
   (e.g. "UMH 519" -> `519 - Lift Every Voice.pro`).
2. Fetch the matched `.pro` files (Drive mirror) into the zip.
3. Insert hook-video + sermon placeholders per section 8.4.
4. OPEN DESIGN CHOICE: template-swap vs spreadsheet-skeleton (see below).
Next: stop reusing an existing `data` manifest and instead **build the playlist from the
spreadsheet row**: parse service order → fuzzy-match each item to a `Libraries/*.pro` →
insert hook-video + sermon placeholders (per §8.4) → construct the `data` manifest in order →
zip. Requires decoding the manifest's group/item structure well enough to construct it.

---

## Sources
- Working with Files — Renewed Vision: https://learn.renewedvision.com/propresenter/working-with-files
- Syncing Between Computers: https://support.renewedvision.com/hc/en-us/articles/360041588774-Syncing-Between-Computers-with-ProPresenter
- Exporting Playlists: https://learn.renewedvision.com/propresenter6/working-with-documents/importing-and-exporting-files/exporting-playlists
- PP7 File Format (GreyShirtGuy): https://greyshirtguy.com/blog/pro7fileformat1/
- PP7 Proto schema: https://github.com/greyshirtguy/ProPresenter7-Proto
- Presentation builder: https://github.com/cgarwood/propresenter-presentation-builder
- Official API docs: https://jeffmikels.github.io/ProPresenter-API/Pro7/
- PP7 User Guide (PDF): https://files.renewedvision.com/propresenter/support/Pro7UserGuide.pdf

---

## 8. SLOT-MATCHING SPEC (both templates decoded)

Both `Standard Worship Service` and `Worship Service With Communion` share one ordered
backbone. Items are either **cue headers** (production notes, no `.pro` ref) or
**presentation items** (carry a `Libraries/...pro` ref). Swap slots are identified by the
**library category of the ref** (+ the cue header that precedes them), so the generator
never hard-codes positions.

### 8.1 Item classification rule
| Ref category / name | Treatment |
|---|---|
| `CALL TO WORSHIP-2.pro` (Name Lower Thirds) | **CTW slot** — regenerate content weekly (Milestone 1 generator) |
| `Libraries/Hymns & Songs/####.pro` | **Song slot** — swap to matched library file |
| `Name Lower Thirds/L3 - <Proper Name>.pro` | **Person slot** — swap to matched `L3 - NAME.pro` |
| `Name Lower Thirds/L3 - <ALL-CAPS ROLE>.pro` (WORSHIP GUIDE, GO IN PEACE, WORSHIP APP CHECK IN, Children's Time, Song Title) | **FIXED** — generic role label, keep as-is |
| Sermon Slides, Worship Blank, Web *, AUMC PrePost, Generosity, Invitation-1, Communion, Lord's Prayer, Baptismal Liturgy | **FIXED** — template owns these |

### 8.2 Swap slots — VERIFIED against both templates (via `tools/propresenter/slot_map.py`)
Each swap slot is anchored by the **cue header it sits under** (robust to reordering). Both
templates contain exactly these 6 swap slots; everything else is fixed.
| Slot | Anchor cue | Standard | Communion | Weekly source (TBD column) |
|---|---|---|---|---|
| **A** person | "In-Person Welcome" | `L3 - JONATHAN PERRY` | `L3 - JONATHAN PERRY` | welcome person (pastor?) |
| **B** person | "Prelude & Call To Worship" | `L3 - GUEST - PIANO` | `L3 - Ashton Landry` | accompanist/musician |
| **C** CTW | (same section) | `CALL TO WORSHIP-2` | `CALL TO WORSHIP-2` | CTW Drive doc |
| **D** song | "Hymn #1" | `3149 - Place At The Table` | `3179 - The Risen Christ` | opening hymn |
| **E** person | "Invitation" | `L3 - JENNY BATES` | `L3 - CATHY` | liturgist/invitation |
| **F** song | "Hymn #2" | `3154 - Draw The Circle Wide` | `672 - God Be With You` | closing hymn |

**Song-count resolved:** templates have **only 2 hymn-file slots** (D, F). The "Performance
Song" section holds just an `L3 - Song Title` title-card (no song deck) — so special music is
a *title-card* swap, not a third hymn slot. Matcher (`match_library.py`) resolves the song &
person values; classifier (`slot_map.py`) tags each item swap/fixed/cue.

### 8.3 Slot → spreadsheet-column mapping — VERIFIED against 4 real weeks
Each swap slot now maps to a confirmed column. Confirmations come from exact template↔sheet
matches: May 3 (a Communion week) Prelude = "Ashton Landry" = Communion template's
`L3 - Ashton Landry`; May 3 Invitation = "cathy" = `L3 - CATHY`; Welcome = "Jonathan" =
`L3 - JONATHAN PERRY`.
| Slot | Source column | Idx | June 14 value |
|---|---|---|---|
| **A** person (welcome) | I · Welcome | 8 | Jonathan |
| **B** person (accompanist) | K · Prelude | 10 | Jack Knagg ~ Wade in the Water |
| **C** CTW | N · Call to Worship (+ linked CTW doc) | 13 | CTW 06/14 |
| **D** opening hymn | P · Opening Hymn | 15 | UMH 519, Lift Every Voice and Sing |
| **E** person (invitation) | AC · Invitation | 28 | Aaron |
| **F** closing hymn | AE · Closing Hymn | 30 | TFWS #2172 We Are Called |
| title-card special music | T · Special Music/Anthem | 19 | The Road Home by Stephen Paulus |

**Edge cases seen in real data (need handling rules):**
- **Hymn cell formats vary**: `UMH 519, …`, `TFWS #2172 …`, `W&S 3004 …`, `#451 …`,
  `…, UMH 672`. Matcher's "first 2–4-digit number" heuristic covers all of these.
- **Non-hymn entries**: VBS Sunday (June 7) Opening Hymn = "Philippians Four Thirteen/VBS
  Kids" — no library match. Special weeks must fall back to human review / skip.
- **Special music is usually an anthem/choir piece** ("The Road Home", "You Do Not Walk
  Alone/Choir"), not a congregational deck → title-card text only, confirming slot is a card.
- **Empty source cell** (May 3 Welcome blank): rule needed — keep template default or drop
  the L3.

### 8.5 Weekly-input source — IDENTIFIED ✓
**AUMC Worship Service Schedule** Google Sheet (id `16-r_WbF7S5Nbz9zj4GTiatqe0OGAGgVp6W1nAHdBvtE`),
one tab per year, one row per Sunday, columns A–AJ (full map in the shared *Worship Planning*
skill: `arapaho-service-schedule-key.md`). **Read it as CSV** (`download_file_content`,
`exportMimeType=text/csv`) — the markdown/`read_file_content` render silently drops trailing
columns and is NOT reliable for column-accurate values. Point Person (col A) rotates among
Terri/Aaron/Cathy/Jonathan/Jenny and is NOT the Liturgist (col M).

### 8.6 Pre-build analyzer — BUILT + verified on real weeks
`tools/propresenter/analyze_week.py` reads the schedule CSV + a target date and prints a
**build plan** for human review before anything is generated (per user: "analyze the info
and missing things before building"). It picks the template (Standard/Communion), maps each
swap slot to its column, runs the matcher, and flags gaps. Behavior rules wired in:
- **Empty source cell** → keep template default, **flag for review** (e.g. May 3 Welcome).
- **No confident match** → **placeholder + report** (e.g. VBS "Philippians Four Thirteen",
  "Snowball Mountain Challenge" — special weeks flagged, never silently guessed).

Verified output on three real weeks: **June 14** (Standard) all 7 slots resolved; **June 7**
(Communion) flags the two VBS non-library items; **May 3** (Communion) matches Ashton Landry
→ `L3 - Ashton Landry`, cathy → `L3 - CATHY`, flags empty Welcome. Inventory cached in
`data/library_inventory.json` (200 hymns, 154 L3s); refresh from the Drive mirror.
Demo fixture (`data/schedule_sample.csv`) holds real values for these weeks.

### 8.7 First full build — DONE (June 14), awaiting home test-import
`build_week.py` produced **`June 14.proplaylist`** end-to-end from the Standard template.
Self-verification on the output: playlist retitled "June 14"; **all 24 manifest refs resolve
to a bundled `.pro` (zero dangling)**; swaps landed (519, 2172, Jack Knagg, Aaron Manes);
swapped-out files removed; CTW deck = regenerated Juneteenth `.pro`; bundled library files
byte-identical to Drive originals; unedited items byte-identical to template. Output is a
standard `ZIP_STORED` archive (stock `unzip` reads it).

**Open risk (only a home test can settle):** whether PP7 import accepts this standard stored
zip vs the native ZIP64-quirk format PP writes on export. If import fails, switch the writer
to match PP's ZIP64 layout.
**Known v1 gap:** the special-music title card is left as the generic template `L3 - Song
Title` — the week's anthem text ("The Road Home by Stephen Paulus") is not auto-filled yet.
**Next:** home test-import → confirm → then add special-music card text + wire CTW-doc → CTW
`.pro` regeneration into `build_week` so any date builds in one command.

### 8.8 v2 — import fixes (after first home test)
First home import reported: hymns showed as "presentation there, no slides." Root cause: the
re-zip used Python's `zipfile`, but **ProPresenter writes a non-standard ZIP64** its importer
depends on — it read `data` but couldn't index the bundled `.pro` entries. `ppzip.py` now
replicates PP's exact dialect (stored, ver 45, every entry forces `0xFFFFFFFF` sizes + a
24-byte zip64 extra `[usize,csize,offset]`; Zip64 EOCD + locator + classic EOCD), verified
byte-for-byte vs a real church export. Bundle is flat `.pro` + `data` only (no media tree).

Also in v2:
- **CTW liturgist**: title's second line now shows the liturgist (col 12) instead of the
  theme word; all other CTW slides byte-identical.
- **Community Prayer**: typical Sundays replace the special-case `Baptismal Liturgy` with
  `blank · leader-L3 (col 24) · Lord's Prayer · blank` (clone template items, rewrite refs,
  fresh cue UUIDs). `build_week(..., baptism=True)` keeps the Baptismal Liturgy for baptism
  Sundays. Library has `L3 - Community Prayer Name.pro` as a generic fallback when the leader
  has no personal L3.

v2 self-verify (June 14): 42 items, 27 refs, **zero dangling**, 23 entries CRC-valid, all
swaps + community-prayer block present, Baptismal Liturgy removed, CTW title = liturgist.

### 8.9 v2.1 — fix ProtobufSerializableError on import
v2 imported far enough to hit `ProtoHelpers.ProtobufSerializableError error 1` — i.e. the zip
dialect was now correct (PP read the payloads) but a protobuf failed PP's *strict* (Swift)
deserializer, which our lenient round-trip check can't catch.

Root cause: the cue UUID is `item/1/1` = a 36-char string (`0a26 0a24 <uuid>`). Our lenient
parser sometimes mis-splits that string into phantom sub-fields, and the community-prayer
`_fresh_uuid` wrote a new UUID *into the misparse* — producing bytes that round-trip locally
but violate the schema. PP parses `data` first, so this errored before any slide loaded.

Fix: `_fresh_uuid` now sets `item/1/1` directly (value, `msg=None`). Added a `_validate()`
guard that **fails the build** unless every item has a canonical cue UUID and every ref is
bundled. Verified: all 42 items canonical + unique, CTW structurally identical to the known-
good template CTW (only an optional run attribute differs), zero dangling refs.

### 8.10 v2.2 — truncated hymn downloads + special-music card
After v2.1 imported cleanly, two issues remained:
- **Lift Every Voice had no lyrics.** Root cause: the subagent that downloaded library .pro
  files **truncated the large ones** while handling base64 (519 came down 9,773 of 21,736 B;
  2172 19,980 of 22,709 B). A truncated protobuf still round-trips, so it passed the old
  check — but the lost tail held fields 17/18 (the arrangement), so ProPresenter showed the
  presentation with no usable slides. Fix: re-fetched both in full by extracting the complete
  base64 from the session transcript (reliable; no hand-transcription) and verifying byte size
  == Drive `fileSize`. Added a build guard: every bundled presentation must carry fields 17/18
  or the build fails (catches truncation).
- **Performance-song card said "Rainbow."** That was template placeholder text in
  `L3 - Song Title.pro`. Added `song_title_card()`: sets the quoted title from col 19
  (Special Music/Anthem), dropping the "by <composer>" tail. The card has no character-range
  runs, so a substring swap is safe.

Download lesson: `download_file_content` returns base64; large files must be size-checked
against Drive `fileSize`, and the bytes recovered from the tool result on disk — never
re-typed.

### 8.10 v2.2 + the repeatable flow (skill)
v2.2 closed the last two import issues: "Lift Every Voice" had no lyrics because the Drive
download was **truncated** (9773 of 21736 bytes — a truncated `.pro` still round-trips, so size
is the only signal; added `check_sizes.py` + a fetch-time size check), and the performance card
still said "Rainbow" because the special-music title (col 19) wasn't being set (now wired:
`L3 - Song Title` text ← col 19, title before " by ").

The whole process is now a **skill**: `.claude/skills/worship-playlist/` (SKILL.md +
CONVENTIONS.md), invoked as `/worship-playlist <date>`. It runs: load context → analyze →
clarify (Q&A) → plan → confirm → build → self-check → user imports → iterate → fold learnings
into the skill/docs + `CLAUDE.md` memory. Templates are committed media-less under
`tools/propresenter/templates/{standard,communion}/`, so a build only fetches the week's
variable library files from Drive. **Top open item:** generalize CTW-doc → CTW slides (still a
June-14 POC).

### 8.11 CTW formatter (gen_ctw.py)
The CTW is **written by humans before the skill runs** — the skill formats it, it doesn't
author it. `gen_ctw.py` reads the week's CTW doc text, parses the `Leader:` / `People:`
exchanges + closing `All:`, and lays them into `CALL TO WORSHIP-2.pro`: title slide =
"Call To Worship" + the liturgist (col 12); scripture/theme/rubric stay doc-only. It reuses
the proven June-14 RTF/run/targeted-dirty machinery (the POC is superseded, kept for
reference). Deck capacity = title + 4 content slots; ≤4 fill/clear cleanly, **>4 raises so the
week is flagged** (dynamic slide add/remove — "mostly 4 but must flex" — is the open follow-up).
Verified on the real June 14 doc: title + 3 exchanges + All, end-to-end build validates, and a
5-exchange doc is correctly flagged. Planning (`analyze_week`) now also covers the liturgist
(col 12) and community-prayer leader (col 24), so every element is checked/flagged.
