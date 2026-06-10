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

### 8.3 Reuse-first strategy (confirmed against June 14)
**Most of a service already exists as files — reference, don't recreate.** For June 14, every
hymn, lower-third, and setup slide matched an existing library file (e.g. Opening Hymn
"UMH 519" → `Hymns & Songs/519 - Lift Every Voice.pro`; Liturgist Gabe Meadows →
`L3 - Gabe Meadows & Band.pro`). The ONLY new content was the Call to Worship liturgy and the
sermon title slide.

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
