# Handoff — AI Atlas

Paste this whole file as the first message of a new session.

---

## What you are working on

**AI Atlas** — an interactive time-model of the AI world, 2012 → today (advancing daily), built
from the AI policy wiki in August's Vault and rendered as living semantic terrain.

- Repo: `/Users/augustgweon/AI Atlas` · GitHub `augustg97/ai-atlas` (Pages serves `main:/docs`)
- **Live: https://augustg97.github.io/ai-atlas/** — v1.0 shipped 2026-07-31,
  last verified stamp `20260731-0207`
- **Read `README.md` first** (goals incl. the visual bar §1; working rules incl. the six
  subject-specific §2; traps §7; limits §9), then `SCOPE.md` (the contract; §11 = the user's
  decisions verbatim; §12 = Ask-the-Atlas design), then `Research/MODEL-GAPS.md`.
- Protocol: `/Users/augustgweon/Modeling Studio` — `/model-research`, `/model-build`,
  `/model-verify`, `/model-ship` apply here.

## State right now

- **Shipped and live-verified**: the WebGL2 field substrate (terrain/attention/settlement
  composed per pixel from 190 baked keyframes), 855 windowed feature entities + 270 person
  cards, 1,825 dated events (92% explicit event dates), 11,397 typed arcs, growth footprints
  from 421 Snapshot rows, era-registered readout, chapters, territories, layers, Ask-the-Atlas
  Tier 0 (find + int8 semantic neighbours), About with the honesty essays, in-app update log.
- **The gate** (`Research/modeling/audit_all.py`): PASS at ship; baselines in
  `baselines.json` — review 224 (tightened from 223 when the spine path added a reporting
  surface), witness matched 20 / disagreements 4, datum drift ε 0.005, datum v1-2026-07-31.
- **The daily machine**: scheduled task `ai-atlas-nightly` (10:47 local, after the vault's
  09:22 cycle) runs `build/nightly.sh` → emit → witness → bake → gate → stamp → push →
  live-stamp verify; on gate refusal it publishes nothing and reports (yesterday's data
  serving is the designed failure mode). Reports land in `Research/nightly-reports/`.
  **D1 acceptance (three unattended correct mornings) is PENDING — watch the first three.**
- **The queue loop is live**: six tasks filed into the vault's `Wiki/_meta/queue/`
  (2026-07-31): four INGESTs (ChatGPT launch, AlexNet, GPT-4 report, AlphaGo), one RESEARCH
  (2022–23 era coverage), one LINT (the Mori 1970 sentinel). The vault's next ingest cycle
  drains them; the atlas inherits the improvements at its next emit.

## Honest assessment vs SCOPE (what is and is not there)

- **Rule-2.16 screenshot verdict:** the selection view (entity + arc fan + card) reads as a
  rendered world; the resting substrate reads as a dark luminous map — good, not yet at
  Tectonic's terrain register. Next visual round: stronger relief/contours, settlement fabric
  at zoom, glyph refinement.
- **ChatGPT-shock test: partial pass, measured.** The shock reads as a sustained regime change
  (+59% attention at 2023-01, 2.3× by 2023-04, never returns to 2022 baseline) — but its
  opening weeks are corpus-limited (the wiki holds 7 sources Oct–Dec 2022). Filed to the
  queue; re-measure after the wiki ingests the era.
- **Jurisdiction view: not built** (deferred at STAGED-CHANGES; world-atlas TopoJSON is
  already fetched at `data/witness/countries-110m.json`, ISC). B3 era-prose tiling not built
  (cards show description + dated series + status). E2 worker synthesis not built (needs
  August's key + CF deploy approval).
- Pre-horizon eras render sparse and dimmer BY DESIGN (labelled "reconstructed from the
  record"); the 2012–2020 era will stay thin until the queue-filed landmarks are ingested.

## Traps that have cost time IN THIS PROJECT (beyond README §7)

- The scaffold's `.gitignore` pattern `data/` swallowed `web/data` and `docs/data` — the
  first deploy served a stamped app with **no JSON payload** (splash hang). Now `/data/`.
- **Cross-metric and hedged Snapshot rows**: a $5B compute row rolled over the $1T valuation
  row, then a "$1.75T (SpaceX IPO target)" hedge became a headline fact. `usdAt` is
  group-filtered and hedge-filtered; cards still show every row verbatim.
- **Year-precision dates spike as July-1 phantoms** in any KDE — precision-smear them
  (`fields_bake.py` does; the unsmeared version's top-6 "burst" frames were all artifacts).
- A ternary is not an assignment target in JS (`(a?x:y)=v` parses nowhere); the whole app
  died silently on it once. `node --check` the extracted script before serving.
- The pane can render the live site letterboxed — a browser-pane artifact, not the app;
  verify layout on localhost before chasing it.

## The work queue (= register order)

1. **Watch the first three nightlies** (D1 acceptance); expect the queue-filed ingests to
   enrich the shock era within days — re-run the shock measurement after.
2. **Visual round 2 (A1 continuation):** relief/contour strength, settlement fabric at zoom,
   pre-horizon register polish — against five captured reference framings (F1, still to
   capture into `reference/`).
3. **B3** era-prose tiling per entity (the largest card-quality item).
4. **Jurisdiction view** (TopoJSON in hand).
5. **E2** Ask-the-Atlas worker tier (key + CF approval from August first).
6. **C1 curation**: the 133 Epoch W3 candidates → a curated queue filing.

## Commands

```bash
# run locally (or: preview_start name="ai-atlas") — serve repo root, open /web/
python3 -m http.server 8143 --directory "/Users/augustgweon/AI Atlas"

# research loop
cd "/Users/augustgweon/AI Atlas/Research/modeling" && \
  python3 frames.py && python3 emit.py && python3 witness_epoch.py && \
  python3 fields_bake.py && python3 audit_all.py

# deploy (only route; the gate lives inside)
python3 build/build_site.py && git add -A && git commit && git push
# then verify the live stamp (build prints the curl line)

# the nightly chain, manually
bash build/nightly.sh
```

## How the user wants this done

README §2, especially: **the surface is the argument** (2.16 — assess a full-frame screenshot
honestly every round; Tectonic Earth is the register) · **visually verify** · **fix the
system, not the instance** · **measure before tuning** · **the vault is read-only except the
queue** · **nothing the record disputes or hedges is stated flatly** (2.15 — the xAI target
lesson) · **address every item raised, and say so when one cannot be done.**
