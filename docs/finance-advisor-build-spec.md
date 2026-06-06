# Finance Advisor — Build Spec (drop-in for the Cowork setup)

> **Status:** Scoped, ready to build. Authored from a `task-dashboard` session that could
> reach Supabase + Google Drive but **not** the `~/cowork` repo. Everything below is meant
> to be executed from a **Cowork session** where the skills, hooks, and `.claude/agents/`
> live. A copy of this file also lives in the Google Drive **"Personal FInance"** folder so
> the Cowork session can read it directly.

---

## 1. Purpose

A continually-updated **personal finance planning partner** for Jonathan & Lindsey —
covering household finances and retirement strategy. The user talks to his **Chief of Staff**
as normal; the CoS **routes** finance conversations to a specialist (`finance-advisor`) that
has its own knowledge base, memory, and the living plan. Two input streams keep it current:

1. A **Google Drive folder** of finance docs (balance sheets, transactions, statements, benefits).
2. A **YouTube "finance" playlist** Jonathan curates (personal finance / retirement content).

**Explicit decision (already made):** Do **not** build on NotebookLM. The need is a *living,
reconciled plan*, which NotebookLM does not do. Build native on the existing stack. NotebookLM
stays a human-only tool for its media-generation party tricks, if ever wanted.

---

## 2. Reuse inventory (what already exists — don't rebuild)

| Capability | What's there | Use for |
|---|---|---|
| Embeddings | Supabase edge fn `embed-text` (gte-small, 384-dim) | Embed every finance source |
| Batch embed | edge fn `backfill-any` (v3) | Backfill `finance_sources` |
| Semantic search | edge fn `search-mem` | RAG retrieval for the subagent |
| Vector store | `pgvector` in Supabase (project `epdxkvohrclpqnlagkwv`) | `finance_sources.embedding` |
| Persistent memory | `memory_blocks`, `session_summaries` tables + Stop/SessionStart hooks | Finance context + warm start |
| Ingestion pattern | NotePlan curator pipeline + `noteplan_processing_log` (hash dedup) | Model the finance ingester on this |
| Review/triage gate | Dashboard "Review" tab + proposed-task gate | Model contradiction approval on this |
| Drive access | Google Workspace MCP (Drive) | Read the folder; write the plan `.md` |
| YouTube transcript skill | **Exists in Jonathan's system (Cowork) — locate it there** | Playlist transcript fetch |

**Drive folder (intake):** `Personal FInance` — id `1A6CqoLYk3bSAzC7Cl_5JZOI3BwjrggXF`
(owner `jonathan@arapahoumc.org`). Already contains: `balance-sheet-details-2.csv`,
`Transactions_2026-05-29....csv`, `Benefits Access - Health.pdf`.

---

## 3. Architecture

```
   ┌─ Drive "Personal FInance" folder ─┐      ┌─ YouTube "finance" playlist ─┐
   │  balance sheets, transactions,    │      │  curated videos (personal     │
   │  statements, benefits (PDF/CSV)   │      │  finance / retirement)        │
   └───────────────┬───────────────────┘      └──────────────┬───────────────┘
                   │ Drive MCP read                           │ transcript skill
                   ▼                                          ▼
          ┌─────────────────────  INGESTER (scheduled, curator-style)  ──────────────┐
          │ extract text · summarize · extract claims · tag · date · dedup (hash)     │
          │ → write row to finance_sources → embed via embed-text                     │
          └───────────────────────────────────┬──────────────────────────────────────┘
                                               ▼
                            ┌──── finance_sources (pgvector) ────┐
                            │ provenance + summary + embedding   │
                            └───────────────┬────────────────────┘
                                            ▼
                  ┌──────────  SYNTHESIS + RECONCILIATION  ──────────┐
                  │ compare new info to current plan                  │
                  │ agree → fold in   |   conflict → PROPOSE change   │
                  └───────────┬───────────────────────┬──────────────┘
                              ▼                        ▼
        personal-finance-plan.md (Drive)      finance_proposals (await approval)
                              │
                              ▼
        ┌──────────  finance-advisor subagent (conversation partner)  ──────────┐
        │ RAG over finance_sources (search-mem) · reads plan + finance memory    │
        │ · read access to Drive folder                                          │
        └───────────────────────────────┬───────────────────────────────────────┘
                                         ▼
                         Chief of Staff  ──routes finance topics──►  finance-advisor
                                         ▲
                                   Jonathan talks here (one conversation)
```

---

## 4. Data layer

Apply as a **tracked migration** in Cowork (via `apply_migration`), not ad-hoc.

```sql
-- Finance source knowledge base
create table public.finance_sources (
  id            uuid primary key default gen_random_uuid(),
  source_type   text not null check (source_type in ('drive_doc','youtube','note','manual')),
  title         text not null,
  url           text,                 -- Drive viewUrl or YouTube watch URL
  external_id   text,                 -- Drive file id or YouTube video id
  author        text,                 -- channel name / doc owner
  published_at  date,                 -- video publish date / doc date (for recency weighting)
  raw_text      text,                 -- transcript / extracted text
  summary       text,                 -- AI summary (markdown)
  claims        jsonb default '[]',   -- extracted atomic claims for reconciliation
  tags          text[] default '{}',  -- e.g. {retirement, tax, investing, budgeting, insurance}
  status        text default 'new' check (status in ('new','reviewed','superseded','rejected')),
  fingerprint   text unique,          -- md5(source_type+external_id+content) for dedup
  embedding     vector(384),          -- gte-small via embed-text
  created_at    timestamptz default now()
);
create index on public.finance_sources using ivfflat (embedding vector_cosine_ops);

-- Proposed plan changes awaiting Jonathan's approval (the contradiction gate)
create table public.finance_proposals (
  id            uuid primary key default gen_random_uuid(),
  kind          text not null check (kind in ('add','update','contradiction','flag')),
  summary       text not null,        -- what's proposed, in plain language
  rationale     text,                 -- why; what it changes / conflicts with
  source_ids    uuid[] default '{}',  -- supporting finance_sources rows
  plan_section  text,                 -- which part of the plan this touches
  status        text default 'open' check (status in ('open','approved','dismissed')),
  created_at    timestamptz default now(),
  resolved_at   timestamptz
);
```

Enable RLS consistent with the other tables (household-private data).

**Finance memory block** (so the CoS/subagent always has the frame):

```sql
insert into memory_blocks (label, content) values
('finance_context',
 'Personal finance lane for Jonathan & Lindsey (household, NOT church/Budget 26-27). '
 || 'Plan lives at Drive personal-finance-plan.md. Knowledge base = finance_sources. '
 || 'New info is reconciled, not blindly appended; conflicts go to finance_proposals for approval.');
```

---

## 5. The living plan — `personal-finance-plan.md`

- **Format:** markdown (Jonathan's stated preference), single file.
- **Location:** the "Personal FInance" Drive folder, alongside the source docs.
- **Maintained by:** the ingester/synthesis step + the subagent during conversations.
- **Suggested structure:**
  ```markdown
  # Personal Finance Plan — Jonathan & Lindsey
  _Last updated: <date> · maintained by the finance-advisor_

  ## Snapshot            (net worth, accounts, cash flow — from balance sheet + transactions)
  ## Goals               (near-term, retirement targets, big purchases)
  ## Retirement Strategy (current thesis, assumptions, target date/number)
  ## Decisions Log       (what we decided + when + why)
  ## Open Questions      (things to resolve)
  ## Principles          (our rules of thumb / risk tolerance)
  ## Source Index        (key inputs + dates; superseded items struck through)
  ```
- **Contradiction handling in the plan:** never silently overwrite. The Decisions Log keeps
  history; when new info conflicts, a `finance_proposals` row is opened and the plan is only
  changed on approval.

---

## 6. Intake streams

**Drive folder** — id `1A6CqoLYk3bSAzC7Cl_5JZOI3BwjrggXF`.
- Ingest all files **except** the plan file and anything prefixed `_` (e.g. this spec).
- Parsers: CSV (balance sheet / transactions → structured summary), PDF (text extract),
  Docs/Sheets (export text).

**YouTube playlist** — _TODO: Jonathan to provide the playlist link + whether it's
public / unlisted / private._
- List playlist items via YouTube Data API (key for public/unlisted; OAuth if private).
- Transcript via **Jonathan's existing transcript skill** (locate in Cowork). Fallback:
  `youtube-transcript-api` / `yt-dlp --write-auto-sub`. Some videos won't have transcripts —
  log and skip.

---

## 7. Ingestion pipeline (curator-style, scheduled)

1. Discover new items (Drive: new/modified files; YouTube: new playlist videos).
2. Dedup against `finance_sources.fingerprint`.
3. Extract text → summarize → extract atomic `claims` → tag → capture `published_at`.
4. Insert `finance_sources` row; embed via `embed-text`.
5. Run reconciliation (§8).
6. Log the run (mirror `noteplan_processing_log`).

Schedule like the existing curator (cron-in-Code). Also runnable on demand ("process the folder now").

---

## 8. Synthesis & contradiction handling

For each new source's claims, compare to the current plan + existing high-signal sources:
- **Agrees / additive** → fold into the plan (and Source Index), note in Decisions Log if material.
- **Contradicts** → open a `finance_proposals` row (`kind='contradiction'`) describing the
  conflict and both positions. **Do not change the plan.** Surface for Jonathan's approval.
- **Low signal / noise** → store as `finance_sources` but mark `status='reviewed'`, don't touch plan.

**Approval surface options** (pick one during build): a `/finance-review` CoS command, or a
small section in the dashboard mirroring the Review tab. Recommendation: start with the
conversational `/finance-review` (no UI work), add a dashboard surface later if wanted.

---

## 9. The `finance-advisor` subagent

Path: `.claude/agents/finance-advisor.md` in Cowork.

```markdown
---
name: finance-advisor
description: >
  Personal/household finance & retirement specialist for Jonathan & Lindsey.
  Use proactively whenever the conversation touches household money, budgeting,
  cash flow, net worth, investing, taxes, insurance, big purchases, or retirement
  planning. NOT for church finances / Budget 26-27.
tools: Read, Grep, Glob, Bash   # + the Drive read tools and the Supabase search-mem call
model: sonnet
---

You are Jonathan's personal financial planning partner, working for him and his wife Lindsey.

On invocation:
1. Load context: read `finance_context` memory block + `personal-finance-plan.md`.
2. Retrieve: use search-mem over `finance_sources` for anything relevant to the question.
3. Reason with current data (balance sheet, transactions) — cite which source/date informs each point.
4. Be a thinking partner: surface trade-offs, name assumptions, flag risks. Give your best
   judgment; don't over-hedge. Warm, plain-language, no fear/guilt framing.
5. Never silently change the plan. Material changes / conflicts → propose via finance_proposals.
6. Keep household finances strictly separate from church finances.
```

> **Verify against current Claude Code docs at build time:** exact per-subagent MCP/tool
> scoping syntax and any native `memory:` field. The robust, version-agnostic approach used
> here is: memory via the `memory_blocks` row + the plan file the agent reads on start.

---

## 10. Chief-of-Staff routing

- The CoS delegates to `finance-advisor` automatically based on its `description`.
- Optionally add a line to the CoS/project instructions: *"For household finance/retirement,
  consult the finance-advisor (it owns personal-finance-plan.md and the finance knowledge base)."*
- Result returns into the main conversation — Jonathan never leaves the CoS.

---

## 11. Privacy & data governance

- This is **household** financial data. Keep it in Jonathan's own Supabase (RLS on) + his Drive.
- The "Personal FInance" folder currently sits under the **church Workspace** tenant
  (`jonathan@arapahoumc.org`). Consider moving the household-finance lane to a **personal Google
  account** to avoid mixing personal financial records with the church tenant. _Jonathan's call._
- Data minimization: don't pull raw transaction rows into general CoS context; the subagent
  reads them deliberately, scoped to the question.

---

## 12. Open decisions (need Jonathan)

1. **YouTube playlist link** + visibility (public / unlisted / private).
2. **Church vs. personal Google account** for the finance folder (privacy).
3. Confirm **propose-and-approve** for contradictions (recommended) vs. auto-merge. _(Tentatively: approve-gate.)_
4. Approval surface: conversational `/finance-review` (recommended) vs. dashboard section.

---

## 13. Build order (checklist for the Cowork session)

- [ ] Locate Jonathan's existing **YouTube transcript skill**; confirm interface.
- [ ] Apply migration: `finance_sources` + `finance_proposals` (+ RLS).
- [ ] Insert `finance_context` memory block.
- [ ] Backfill: ingest the 3 existing Drive files → embed → first pass of the plan.
- [ ] Draft `personal-finance-plan.md` from the balance sheet + transactions; save to the folder.
- [ ] Build the ingester (Drive + YouTube) on the curator schedule.
- [ ] Wire the reconciliation/proposals step + `/finance-review`.
- [ ] Add `.claude/agents/finance-advisor.md` + CoS routing line.
- [ ] Test: ask the CoS a retirement question; confirm it routes and cites sources.
```
