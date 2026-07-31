# Handoff — AI Atlas

Paste this whole file as the first message of a new session.

---

## What you are working on

**AI Atlas** — an interactive time-model of the AI world, 2012 → today (advancing daily), built
from the AI policy wiki in August's Vault and rendered as living semantic terrain.

- Repo: `/Users/augustgweon/AI Atlas` · GitHub: `augustg97/ai-atlas` (create on first ship if
  not yet pushed) · Live (once shipped): https://augustg97.github.io/ai-atlas/
- **Read `README.md` first.** Goals incl. the visual bar (§1), working rules incl. the six
  subject-specific ones (§2), traps (§7), known limits (§9).
- `SCOPE.md` is the contract — including §11, the user's five decisions of record and two
  charter-level requirements (the chatbot, and the visual-fidelity bar), and §12, the Ask the
  Atlas design.
- The general protocol lives in `/Users/augustgweon/Modeling Studio`; its skills apply here:
  `/model-research`, `/model-build`, `/model-verify`, `/model-ship`.

## The current task

**Round 1 — the datum round** (`Research/README.md` §Status, in priority order):

1. Refresh the vault's embedding index (`bin/build-embedding-index.py`, incremental, needs
   `VOYAGE_API_KEY` in the vault's environment) — everything waits on this.
2. Datum v1 (register A2): projection method study → freeze → `frames.py` + selftests → ε +
   drift audit.
3. Emit v0 (B1): entities + windows + events with date kinds; needs-review report; date-kind
   audit.
4. Witness bootstrap (C1): Epoch fetched + mapped + audited; tracker named; docket check.
   First baselines.
5. Field-engine design study (A1 — **the user's named worry**): dossier + white paper ending in
   staged changes for the v0.1/v0.2 build.

Then `/model-build` takes the staged changes into the app.

## Reference material and the measurement harness

- The **Tectonic Earth engine** is the standing architectural reference:
  `~/Tectonic Plate Model/web/index.html` — read the FRAG shader (lines ~1362–3892), the lazy
  loader (~1021–1330), and the `window.APP` verification harness (~6470) before building the
  field engine here. Its transferable bar is recorded in the kickoff survey (this session's
  options artifact) and in `Modeling Studio/references/`.
- The full **vault data inventory** (formats, counts, defects, time axes) is in
  `Research/SOURCE-SURVEY.md` — trust it over guessing, verify counts before relying on them
  (the vault changes daily).
- Visual standard: five reference framings to be captured at v0.2 into `reference/`
  (gitignored) with zooms recorded here.

## State right now

- Kickoff complete 2026-07-31: scaffold (hybrid), SCOPE.md, SOURCE-SURVEY.md, README charter,
  CLAUDE.md, MODEL-GAPS.md (16 items, 4 P1), Research/README.md round-1 plan.
- App: the scaffold's feature-engine shell at the project root (D3/SVG, placeholder data) —
  loads locally on port 8143; **the field engine does not exist yet**; `web/` and `build/` are
  empty placeholders.
- Last live deploy: none. Uncommitted: none if the kickoff commit landed (check `git log`).
- The options document (the decision record's context) is the claude.ai artifact "Charting the
  AI Wiki", 2026-07-30.

## What this round found

1. The vault clears the Studio ambition bar with existing data: 1,699 pages, 2,698 dated
   dev-log items, 31,681 links, ~6,200 typed edges, 444 dated Snapshot rows, confidence +
   decay on every page (counts of 2026-07-30; they grow daily).
2. Two time axes: world-time (event dates, curated in dev-log text) and wiki-time
   (`Wiki/_meta/log.md`, 650 dated operations since 2026-04-13). `last_updated` is NOT edit
   history (June 2026 mass restamp).
3. The embedding index (voyage-3-large, 1024-d, LanceDB, 257 MB) is stale since ~2026-05-16 —
   refresh before cutting datum v1.
4. Ready-made bootstrap: `Wiki/_meta/site.nosync/search.js` (current node table, rebuilt by the
   vault's Stop hook). Edges must be parsed from markdown; port `build_backlinks()` from
   `bin/build-dashboard.py:626`.
5. The dev-log's `SCHEMA.md` describes a format 1/201 files uses — parse the prose+footnote
   format actually in use.

## Traps that have each cost real time

See `README.md` §7 and `CLAUDE.md` — dev-log SCHEMA.md lies · `last_updated` is not edit
history · digest dates are not event dates · the embedding index goes stale silently · two site
dirs (`site/` dead, use `site.nosync/`) · iCloud paths (spaces + apostrophe; cold files read
empty) · the stale-dev-JS trap inherited from Aztec.

Plus the standing ones:

- a process backgrounded with `&` inside a tool call dies when that call ends; wait on a PID.
- a static host can serve stale JSON after a successful push — stamp before copying, verify the
  live value.

## The work queue

Ranked by how much of the remaining gap each closes (= register order):

1. A1 field-engine design study — the visual bar (the user's named worry).
2. A2 datum v1 — nothing has a position until it lands.
3. B1 the dated spine — nothing has a time until it lands.
4. C1 witnesses — the instrument later disputes are settled with.
5. D1 the nightly chain (then D2 queue loop, E1 Ask-the-Atlas T0, B2 2012–2020 spine).

## Commands

```bash
# run locally (or: preview_start name="ai-atlas")
python3 -m http.server 8143 --directory "/Users/augustgweon/AI Atlas"

# research loop
cd "/Users/augustgweon/AI Atlas/Research/modeling" && python3 frames.py && python3 emit.py && python3 audit_all.py

# deploy (only route, once build_site.py exists)
python3 build/build_site.py && git add -A && git commit && git push
```

## How the user wants this done

Read the working rules in `README.md` §2 — the ones that matter most here:

- **The surface is the argument** (rule 2.16): a living, breathing landscape at Tectonic
  Earth's register, never dots and symbols on flat ground. Assess a full-frame screenshot
  honestly against that bar every round. This is the user's explicit, verbatim requirement.
- **Visually verify** — render it and look; statistics are not confirmation.
- **Fix the system, not the instance** · **measure before tuning** · **address every item
  raised** and say so when one cannot be done.
- **The vault is read-only except the queue**; the wiki stays the single source of truth.
- **Honesty everywhere**: confidence + decay rendered, contested claims two-sided, the
  knowledge horizon visible, "placed by the model" on every position.
