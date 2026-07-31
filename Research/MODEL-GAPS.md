# Model gaps register — AI Atlas

Every open item this research programme has produced, tied to the specific subsystem it would
change. **This is the handover surface between research and the build.**

Priority: **P1** = closes a known visible defect · **P2** = adds real fidelity ·
**P3** = correctness housekeeping · **P4** = worth knowing, no action yet.

Status: **RESOLVED** = answered, with the answer recorded · **MEASURED** = quantified and ready
to apply · **DELIVERED** = the artifact exists · **APPLIED** = in the app, with the measurement ·
**RETIRED** = no longer needed · **CLOSED, negative result** = tried, did not work, recorded so
nobody retries it · items with no status are open.

IDs are referenced from white papers, code comments and commit messages. **Never recycle one.**

*Seeded at kickoff, 2026-07-31, from the interview, the survey, and the decisions of record.*

---

## APPLIED

| item | what shipped | measured |
|---|---|---|
| A2 **DELIVERED** | datum v1 frozen (`datum_build.py`, seed 20260731): PCA-50 → seeded kNN layout, numpy-only; 1,700 pages positioned; drift audit live at ε=0.005 | int8 top-8 recall **0.989**; datum 194 KB, anchors 785 KB; selftest separates planted clusters ≥2.5× |
| A3 **DELIVERED** | territories = tf-idf-weighted event-target prototypes per dev-log section (first mechanism — single-header chunks — CLOSED, negative result: 12/13 sections starved) | 13/13 sections live, 22–136 distinct targets each |
| B1 **DELIVERED** | emit v0 with date kinds + the date-kind audit in the gate | 1,825 events, **92% explicit event dates**, 80% entity-targeted; datekinds bad = 0 |
| C1 **DELIVERED** | Epoch witness (CC-BY CSV, 1,041 rows) + baselines; instrument-error lesson recorded (aliases require identity) | matched 20, disagreements 4 (unit-choice, baselined), W3 candidates 133 (curation pending D2) |
| A4 **MEASURED** | field cadence monthly→2026-03 / weekly→now; fixed global scales; ChatGPT-shock test defined | 188 keyframes, 9.4 MB total |
| E1 **MEASURED** | int8-50 static index viable for Tier 0 | recall 0.989 at 785 KB |
| A1 **APPLIED** (v1) | the app: WebGL2 substrate (terrain/attention/settlement per pixel, precision-smeared spine, era registers) + windowed features + cards + T0 search; **live** at augustg97.github.io/ai-atlas | rule-2.16 verdict: selection view reads as a world; resting substrate good-not-yet-Tectonic → visual round 2 open. Shock test: partial pass (+59% at 2023-01, 2.3× by 2023-04; opening weeks corpus-limited — queue filed) |
| D1 **DELIVERED** | nightly chain scheduled (10:47, `build/nightly.sh`, gate-refusal = designed no-publish) | acceptance PENDING: three unattended correct mornings |
| D2 **APPLIED** | queue loop live: 6 tasks filed 2026-07-31 (4 INGEST era landmarks, 1 RESEARCH era coverage, 1 LINT sentinel-date fix) | drains at the vault's next 09:22 cycle |

---

## A. The datum and the substrate

| # | P | item | touches | from |
|---|---|---|---|---|
| A1 | **P1** | **The visual bar** — the substrate must read as a living, breathing surface (Tectonic Earth's register), not dots and symbols on flat ground. This is the thing the user most expects to go wrong, named from the two prior projects' failure. Round-1 deliverable: a field-engine design study porting Tectonic's patterns to abstract space — relief from corpus density, material coordinates from territory id + per-page anchors so texture never slides under its terrain, procedural settlement/fabric grown from the series, attention as weather. Acceptance: full-frame screenshot honestly assessed as "a rendered landscape", per SCOPE §7. | engine, every field layer | decision of record 2026-07-31 |
| A2 | **P1** | **Datum v1** — refresh the embedding index (stale since ~2026-05-16), choose the projection method (seeded, deterministic; candidates: PCA init + UMAP frozen, or anchored custom layout), freeze the transform, ship its parameters, set ε, and write the drift audit. All in `frames.py` with selftests. Until this lands nothing has a position. | frames.py, emit.py, engine | survey §1 |
| A3 | P2 | Territory model — clustering in datum v1 reconciled with the 13-section taxonomy (machine positions, human labels); boundary/hull generation; what happens to pages that straddle. | emit.py, terrain | SCOPE §3 |
| A4 | P2 | Attention field — KDE bandwidth and normalisation, weekly keyframes + daily trailing window, encoding; define the ChatGPT-shock test concretely (which territories, what visible change, at what dates). | emit.py, engine | SCOPE §7 |
| A5 | P3 | The rebase protocol as code before it is ever needed — Procrustes alignment, version stamp, update-log entry, side-by-side drift report. | frames.py | SCOPE §5 |

## B. The dated spine

| # | P | item | touches | from |
|---|---|---|---|---|
| B1 | **P1** | **Date kinds, extracted and audited** — emit v0: frontmatter dates + dev-log in-text event dates + Snapshot rows, every date carrying `event`/`published`/`ingested`/`checked`; non-ISO normalisation; needs-review report; the date-kind audit (an `event` field carrying a `published` date is the send-date bug class and fails the gate). | emit.py, frames.py, gate | survey §2 |
| B2 | P2 | The 2012–2020 spine — Epoch CSV → wiki-slug mapping (tested); era landmarks missing from the wiki (AlexNet, seq2seq, GANs, ResNet, AlphaGo, transformers, GPT-2, …) filed into the queue so the wiki ingests them with citations; chapter/era boundaries proposed from `Wiki/analysis/` for August's sign-off. | emit.py, queue loop, eras | decision §11.2 |
| B3 | P2 | Era-keyed card prose — generate `eras: [{from,to,text}]` per entity from the page's dated material; audit that eras tile each life with no gaps or overlaps. | emit.py, cards, gate | SCOPE §6 |
| B4 | P3 | Legislation enacted/effective dates live in prose, not frontmatter — extract with citations; until then legislation windows use what frontmatter carries, kind-labelled. | emit.py | survey §1 |
| B5 | P4 | Edge dating — first-co-mention inference from log.md would date arcs (modelled, labelled). Deferred; v1 draws arcs while both endpoints exist and says so. | emit.py, arcs | SCOPE §4 |

## C. Witnesses and audits

| # | P | item | touches | from |
|---|---|---|---|---|
| C1 | **P1** | **Build the reference audits early** — verify the Epoch dataset URL + schema and build the mapping + two-direction audit; pick and name the state-law tracker and script the spot-count check; script the CourtListener docket check for the 41 cases. Record first baselines. This is the instrument every later dispute is settled with. | audit_all.py | survey §5 |
| C2 | P3 | The needs-review ratchet — normaliser fallout count recorded per emit; may not grow without a note. | gate | survey §2 |

## D. The daily machine

| # | P | item | touches | from |
|---|---|---|---|---|
| D1 | P2 | The nightly chain — scheduled emit after the vault's 09:22 cycle; gate → stamp → deploy → live-stamp verification → automated update-log line. Acceptance: three consecutive unattended mornings publish correctly or refuse correctly. | scheduled task, build_site.py | SCOPE §10 |
| D2 | P2 | The queue feedback loop — task-file format matching the vault's queue-processor expectations; hard guard that the only write path into the vault is `Wiki/_meta/queue/`. | emit.py, audits | decision §11.5 |

## E. Ask the Atlas

| # | P | item | touches | from |
|---|---|---|---|---|
| E1 | P2 | Tier 0 design honestly — client-side *query* embedding is not free (no key in the browser): T0 = name/tag/text find + precomputed semantic-neighbour lists per page (emitted nightly) for explore-by-similarity; true semantic *query* search arrives with the worker. Measure quantized-index recall vs full precision before shipping neighbour lists. | emit.py, app panel | SCOPE §12 |
| E2 | P3 | Tier 2 worker — endpoint, citation-enforced response schema (every claim carries a card link or the response is rejected), token budget, key handling, multi-turn caching; "corpus is silent" path offers to file the gap into the queue. Depends on August's CF account + key. | worker, panel | SCOPE §12 |

## F. The research programme itself

| # | P | item |
|---|---|---|
| F1 | P3 | Capture the five visual-standard reference framings at v0.2 and record their zooms in HANDOFF. |
| F2 | P4 | Card images pipeline — excluded v1; copy the Aztec licence machinery (`fetch_images.py` + MANIFEST verdicts) if/when wanted. |

---

**What the audits did NOT find** (first gate run, 2026-07-31): windows bad **0** · cards bad
**0** · datekinds bad **0** · eras bad **0** · unpositioned features **0** · unterritoried
**0**. The dev-log "undercount" was NOT a parser loss — frontmatter counts sub-developments;
per-file verification found zero gap files at the rendered-item unit.

---

## T. The v2 pivot — Timelines (2026-07-31, after v1 shipped)

**User verdict on v1:** "pretty, but too abstract and not visually useful" — reassess the
whole approach; keep the spirit (an AI atlas from the vault); the new subject is **branching
future timelines** (the next decade and longer), our own creative work grounded in the wiki
and the scenario literature (AI 2027, Plan A, Europe 2031, Situational Awareness, …),
documenting how society's layers change under frontier capabilities. The AI 2027 and Plan A
sites are the named visual inspiration. **Aztec Conquest is retired as a reference model.**
Proposal: claude.ai artifact 33657b8d-2c49-4129-8afe-0ec977e6b5c3 (decision pending).

| # | P | item | touches | from |
|---|---|---|---|---|
**Rev 2 (same day), after August's composability note:** not eight static lanes but a
**composable scenario space** — 7 axes (capability tempo T, alignment A, coordination C,
diffusion/labor D, compute/supply S, public response P, economy E) × positions + regional
strands (EU-sidelined/EU-agenda, China-internal, US-states) + authored compatibility rules +
an event-template library citing the wiki's concepts/analysis/industries pages. Published
scenarios become PINNED COMPOSITIONS (calibration anchors reproducing their own numbers);
~300 coherent world-lines composable; a Composer UI with shareable composition strings;
scoreboard grades PER-AXIS positions against the trunk. Psychohistory as stated-loose
metaphor: no probabilities, assumption bookkeeping only.

**Rev 3 (same day), all five answers received — the design of record:** a **living
probabilistic world-model**. Probabilities ARE the product; the mainline of our timeline is
the focus; the ensemble updates daily from the wiki's record with bounded deltas and an
attributed "what moved today" panel; the axis registry is living (sub-axes; weekly schema
review proposes additions from unexplained-residue clusters, approved via the queue);
**no pinned compositions** — the literature is deconstructed into cited building blocks;
horizon **2100** with the strange far futures rendered at honest width; a World view on real
geography satisfies Studio §13b; a public calibration page grades the model on itself; v1's
terrain retires completely at T2. SCOPE §11b records the decisions verbatim.

| # | P | item | touches | from |
|---|---|---|---|---|
| T1 | **P1** | The engine core: full axis registry (axes+sub-axes, priors w/ provenance), conditional network with BOTH intervention (do) and observational (rejection) conditioning, evidence-rule library, event templates incl. far-field to 2100, dynamics parameters, deep-wiki pass (>400 pages cited; coverage audit + thin-grounding→wider-bands rule), registry changelog + weekly schema review. **Prototype r0 DELIVERED** (`Research/timelines/axes.py`): 7 axes/24 positions/3 sub-axes, seeded 10k sampler, 7 selftest groups green, bounded updates (≤2pp/day), approval-gated growth, 32 pages cited | Research/timelines/ + emit | rev 3 §1-§2 |
| T2 | **P1** | The Mainline + rail: probability river to 2100 (percentile bands, median mainline, crisis cards, resolution coarsening monthly→decadal), delta panel, axis bars + 30-day drift, narrative, composer-as-conditioning, forecast-history scrubbing; **v1 terrain removed** | web/index.html rebuild | rev 3 §3 |
| T3 | P2 | The World view: real-Earth surface per date/world-line (compute sites glowing, regime coloring, adoption, flashpoints) at the full Studio visual bar (§13a-c) | app | rev 3 §3 |
| T4 | P2 | The daily machine + calibration: nightly classify→update→re-sample→publish→archive; public Brier/log record; gate extended (probability conservation, delta attribution, coverage ratchet) | emit, audit_all, nightly | rev 3 §1, §5 |
| T5 | P3 | SCOPE v2 full rewrite in the Studio's new 11-section shape (substrate §3 = the World view) at T1's close | SCOPE.md | Studio update |

**v1 items on hold pending the pivot:** visual round 2 (superseded by T2/T3), B3,
jurisdiction view. **Still live regardless:** the nightly chain (the trunk keeps growing),
the queue loop, E2, C1-curation. The datum/terrain code stays in-repo; its fate on the main
stage is the proposal's open question 4.

**T-round outcomes (2026-07-31, v2 live at stamp 20260731-0510):**

| item | what shipped | measured |
|---|---|---|
| T1 **APPLIED** | the engine core: `axes.py` (tiered impacts minor 0.3pp→structural 9pp × corroboration × novelty, weekly soft squash at 10pp; observe(); origin-logged auto-growth), `worldlines.py` (paths w/ C3 pause shelf + A2 delay, tracks, 26 cited templates to 2100, exact-argmax mainline), `wiki_grounding.py`, `forecast_emit.py`, `nightly_update.py` | 20 selftest groups green across 5 modules; grounding **1,221 direct + 479 corpus = 1,700/1,700 pages**, two honest tiers; observe verified (P(T4given A4) > 1.5× prior); mainline = T3·A3·C1·D2·S2·P3·E2, p50 crosses coder ~2032, researcher ~2035 (80% crisis reading), p10 stays sub-researcher into the 2050s |
| T2 **APPLIED** | Mainline stage + composer: probability river (piecewise scale, 66% width to 2040), trunk, crisis diamonds, do/observe conditioning with client resampling against shipped engine.json constants, shareable pins | pinning C3 renders Plan A's pause as a visible shelf; mode chip names the semantics; JS constants single-sourced from engine.json |
| T3 **APPLIED (v1 level)** | instrument rail (pills/donut/copies/stat strip, drift arrows, delta panel) + World view: real Earth, regime tints ∝ compute share, 16 authored sites glowing by modelled GW | honest limit RECORDED: World view is features-on-real-geography, not yet per-pixel lit terrain — §13a full treatment = T8 |
| T4 **APPLIED (partial)** | nightly chain wired end-to-end (update → grounding → emit → gate → deploy), morning forecast reports, claims register (4 claims), gate extended (forecast surface + grounding ratchet) | acceptance PENDING three unattended mornings; Brier scorer = T7 open |

**Open after the T-round:** T6 exemplars-driven variance narrative (exemplars.json ships,
unused) · **T7 the calibration scorer** (claims resolve → Brier record in-app) · **T8 World
view to the full visual bar** (per-pixel relief/light; §13a) · T9 evidence-rule library
expansion (6 seeded rules is a floor, not a library) · T10 sub-axis dynamics (registered,
not yet driving tracks) · T5 SCOPE v2 full rewrite (11-section shape) · plus standing: B3,
E2, C1-curation, D1-acceptance-watch.

**Round T+1 (2026-07-31, stamp 20260731-0801): sources + interactivity APPLIED.**
- **Scenario intake:** the 2028 Global Intelligence Crisis (Citrini/Shah — E4
  displacement-crisis position, D1 jobs-rate recalibrated to the memo's ~10% path, 5 crisis
  templates + 2 rules), Anthropic's 2028 Two Scenarios (C2 four-fronts enrichment,
  distillation-wave + lead-lock templates + rule), and the FULL AI 2040 plan family fetched
  from ai-2040.com/supplements/comparing-possible-plans (C5 moratorium position; Plan-B-cyber,
  GPU-arms-control, CERN-for-AI templates; C3 prior cross-checked vs the authors' own 3-15%
  implementation odds; takeoff-length table vs our knots recorded as a consistency check).
  Registry: 26 positions, 38 templates, 12 rules; grounding 1,222 direct + 480 corpus.
  **Supplement INGEST filed to the wiki queue** (engine cites the URL until it lands).
- **Interactivity (decision of record):** hover + click explanatory cards with grounding
  links across crisis diamonds, ladder milestones, band crosshair (p10/50/90), axis bars
  (full position table + live weights), delta entries (impact arithmetic: class × sources ×
  novelty), instrument panels, narrative waypoints, and World sites (GW + provenance).
- **Fixed:** registry-growth weight migration (new positions enter at seed priors — C5/E4
  broke the first emit; now structural).
- New open: T11 — an in-app "plans overlay" tracing each named strategy's path once the
  supplement is wiki-ingested; T12 — Economic Growth Explorer-style track charts on click.

**Count: 29 items — the machine runs nightly. Watch three mornings (D1+T4); then T7 scorer,
T8 World bar, T9 rule library.**
