# ProPresenter playlist generator (proof of concept)

Working code from the first end-to-end build. See `docs/propresenter-playlist-workflow.md`
for the full design.

- **`pb.py`** — a faithful, schema-free ProPresenter protobuf wire-format codec
  (decode → mutate string leaves → encode). Proven byte-exact (round-trips all real
  `.pro`/`data` files). This is the core building block: it lets us edit slide text inside
  the binary `.pro` format without the official `.proto` schema, recomputing all length
  prefixes correctly.
- **`gen_ctw_june14_poc.py`** — proof of concept: takes the real
  `CALL TO WORSHIP-2.pro` as a template and replaces its 5 text slots with the June 14
  Juneteenth liturgy (template-and-replace), preserving fonts/sizes/centering. Output was
  packaged into a `.proplaylist`.

## Status / next steps
- DONE: slide-text generation (template-and-replace) + `.proplaylist` packaging.
- TODO: build the `data` playlist manifest from scratch off the spreadsheet order
  (currently the POC reuses an existing manifest); wire in hook-video + sermon placeholders
  per the content rules; fuzzy-match spreadsheet items to `Libraries/*.pro`.

## Caveat
No ProPresenter is available in CI/cloud to render output. Every generated file must be
test-imported on the HOME machine before use at church.
