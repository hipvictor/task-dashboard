# ProPresenter Playlist Workflow — Project Brief

> Goal: Build worship-service ProPresenter playlists **at home** and load them on the
> **church computer**. Both machines run **ProPresenter 7**.
>
> Status: **Research complete, paused before implementation.** Pick up using the
> "When We Resume" checklist at the bottom.
>
> Last updated: 2026-06-04

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

## Sources
- Working with Files — Renewed Vision: https://learn.renewedvision.com/propresenter/working-with-files
- Syncing Between Computers: https://support.renewedvision.com/hc/en-us/articles/360041588774-Syncing-Between-Computers-with-ProPresenter
- Exporting Playlists: https://learn.renewedvision.com/propresenter6/working-with-documents/importing-and-exporting-files/exporting-playlists
- PP7 File Format (GreyShirtGuy): https://greyshirtguy.com/blog/pro7fileformat1/
- PP7 Proto schema: https://github.com/greyshirtguy/ProPresenter7-Proto
- Presentation builder: https://github.com/cgarwood/propresenter-presentation-builder
- Official API docs: https://jeffmikels.github.io/ProPresenter-API/Pro7/
- PP7 User Guide (PDF): https://files.renewedvision.com/propresenter/support/Pro7UserGuide.pdf
