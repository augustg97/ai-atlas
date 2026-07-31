# Staged changes — round 1 → `/model-build`

The research folder does not change the app. This file is the handover: every item that
would touch the app, with the artifact that makes it a drop-in, ordered by measured value.
Evidence lives in WP-01 and the module outputs; every gate below is a check `audit_all.py`
already runs.

### 1. Build the app on the WP-01 field-engine design · closes A1, A4 (build side)
**Evidence:** WP-01 §5; datum v1 frozen (deterministic, selftested); fields baked by
`fields_bake.py` (terrain + monthly/weekly heat keyframes, fixed global scales).
**Artifact:** `Research/staged/{datum,entities,events,arcs,series,eras,wikitime}.json` +
`staged/fields/` + `staged/anchors50.json` — the complete data surface, already emitted.
**Change:** replace the scaffold shell with `web/index.html`: WebGL2 quad shader composing
paper → territory tint → hillshade(bedrock + settlement(t)) → contours → attention glow →
era light → procedural grain on frozen material coordinates; SVG features (entities as grown
structures, arcs, strikes, labels); DOM cards/panels/readout/timeline; hash state; lazy
two-keyframe loading with background fill.
**Gate:** rule-2.16 full-frame screenshot assessment ("a rendered landscape, not a chart");
the ChatGPT-shock test (attention visibly propagates across every territory at 2022-11);
first frame < 1 MB / < 1 s local.
**Cost:** the build itself; fields re-bake is ~2 min for all keyframes, seconds for the
weekly increment.

### 2. Ship the staged data as the app's data directory · closes B1 (app side)
**Evidence:** 855 entities (221 windowed), 1,825 events (92% explicit event dates, 80%
entity-targeted), 11,397 arcs, 421 series rows, 562 wiki-time ops, eras tiling 2012→now.
**Artifact:** the staged JSONs, verbatim.
**Change:** `build/build_site.py` copies staged → `web/data/` (arcs and anchors lazy-loaded),
stamps `DATA_V`, runs the gate first.
**Gate:** `audit_all.py` — windows 0 bad, cards 0 bad, datekinds 0 bad, eras 0 bad,
explicit% ≥ baseline, target% ≥ baseline, review ≤ 223.

### 3. Ask the Atlas Tier 0 · closes E1 (static tier)
**Evidence:** anchors50.json int8 top-8 recall (datum_build output); a few hundred KB.
**Artifact:** `staged/anchors50.json`.
**Change:** search panel: lexical find over titles/tags → fly-to + open card; "related"
neighbours by int8 cosine, client-side; every result is a card, so every answer is cited.
**Gate:** none new — the artifact ships as-is; T2 (worker synthesis) stays open at E2.

### 4. The honesty chrome · closes parts of SCOPE §4 UI behaviour
**Change:** About overlay with "What distance on this map is, and is not", date-kind legend,
the wiki-horizon register change (pre-horizon eras render sparse + labelled), "placed by the
model" on card position rows, confidence + decay badges on every card, update log fed by
`meta.json`.
**Gate:** cards check (audit) + visual verification of each element.

### Deferred, recorded
- B3 era-prose tiling per entity (P2) — cards ship with description + series + status.
- E2 worker synthesis (needs August's key + CF deploy approval at ship time).
- D1/D2 nightly chain + queue filing — wired at `/model-ship`, acceptance = three unattended
  mornings.
- Jurisdiction view — build if time allows this session (world-atlas TopoJSON fetched, ISC
  licence); otherwise it stays a stated layer with a register item.
