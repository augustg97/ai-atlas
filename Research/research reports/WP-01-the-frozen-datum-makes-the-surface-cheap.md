# WP-01 — The frozen datum makes the living surface cheap

*Round 1, 2026-07-31. Feeds: `web/index.html` (the app), `Research/modeling/emit.py`,
`fields_bake.py`, `datum_build.py`. Register: A1, A2, A4, B1, C1, E1.*

## Executive summary

The user's named worry (A1) is that this model, like Aztec and Territorial US, will ship dots
on a flat ground instead of a living surface. The study finds the worry is well-aimed but the
cost is lower than the prior projects suggest, for one structural reason: **the datum is
frozen, so the map does not move within a version — and everything that made Tectonic Earth's
field engine hard (advected interpolation, material coordinates that travel with crust,
per-interval displacement fields) simply does not arise.** The surface can be composed per
pixel from three cheap fields (bedrock density, settlement, attention) with procedural detail
keyed directly to position, because position is stable by construction. The expensive problem
here is different: it is the *honesty* of the two time axes (event vs published dates) and the
stability discipline of the datum itself — and both are now enforced by code, not intention.

## 1. What the thing is, and what it cannot know

The substrate is a 2-D projection of voyage-3-large embeddings of 1,697 wiki pages. It can
know: which pages the corpus's own language places in one conversation, at what density, and
where the day's attention lands. It cannot know: alliance, causation, similarity of *position*
(two opposed advocacy groups debate one topic and sit adjacently — correctly, for this map).
The About page owes the reader that sentence ("What distance on this map is, and is not"), and
every card's position row says "placed by the model".

## 2. The record, in the form the model needs (measured this round)

| spine component | measured | note |
|---|---|---|
| feature entities | **855** (+270 people, cards only) | 13 folders |
| windowed entities | 221 | models 56/56, litigation 41, companies by founding year; the undated render as background presence, by design |
| dev-log events | **1,825** | = 100% of *rendered* items; the survey's 2,698 counted frontmatter sub-developments, a different unit (verified per-file, zero gap files) |
| explicit event dates | **92%** (1,674) | kind=event; the 151 without an in-text date fall back to kind=published, labelled |
| events matching an entity | **80%** (1,469) | strike positions inherit entity positions; the rest sit at territory centroids, mode recorded |
| typed arcs | **11,397** | multi-target relationship lines expand to one arc per (src,dst); `contradicts` 294 lines |
| dated series rows | 421 (161 with USD values) | company growth footprints |
| wiki-time operations | 562 | the knowledge-horizon layer |
| needs-review | 223 | duplicate keys, dangling targets, unparseable dates — reported, never guessed |

## 3. What we measured on the datum

*(numbers from `datum_build.py`, seed 20260731 — see `Research/staged/datum.json` meta)*

- Layout: PCA-50 → PCA-2 init → kNN-12 attraction + 8-negative sampled repulsion × 300
  iterations, numpy only. **Deterministic: same inputs + seed reproduce bit-identical
  positions; no sklearn/umap version can drift a rebase.** Synthetic selftest separates
  planted clusters at inter/intra ≥ 2.5×.
- Territory assignment: argmax cosine against the dev-log's own 13 section prototypes
  (a prototype = mean of dev-log chunks containing exactly one section header) — the machine
  positions, the human taxonomy labels, and the taxonomy is one August's corpus already uses
  daily.
- int8 quantisation of the 50-d anchors (for `place_new` and the chat index): top-8
  neighbour recall measured in `datum_build.py` output — see the round report; the shipped
  index is a few hundred KB, which makes fully-static semantic explore (E1 Tier 0) viable.
- Drift discipline: `audit_all.py` fails the gate if any unchanged page moves > 0.005 in the
  unit square within a datum version; rebases bump the version and are announced in the
  update log (A5 keeps Procrustes alignment as the rebase method).

## 4. The witness, first readings (C1)

Epoch AI notable-models CSV (CC-BY 4.0; 1,041 rows): 20/56 wiki models match by strict name
normalisation; **4 date disagreements, all unit-choice disputes, recorded as the baseline**
(e.g. AlphaFold: wiki dates CASP14 2020-11-30, Epoch dates the AlphaFold 1 paper 2020-01-15;
DeepSeek-R1: wiki dates the January release, Epoch the 0528 revision). **First-run lesson,
recorded:** three "helpful" near-version aliases (llama-3 → Llama 3.1-405B …) manufactured
false disagreements that indicted the wiki for the witness's unit choice — the instrument was
wrong before the model was. Aliases now require identity, not proximity. W3 (Epoch
high-notability rows absent from the wiki) reads 133 candidates, mostly non-policy-relevant
lite variants; filing them wholesale into the queue would be noise — a curated subset goes
with D2.

## 5. The field engine (the design, ready to build)

Three fields, one static + keyframed pairs, all baked by `fields_bake.py` from the same
staged data the features read (coherence by construction):

| texture | channels | cadence |
|---|---|---|
| `terrain.png` (per datum version) | R bedrock density (KDE over all pages) · G territory id (NEAREST) · B distance-to-boundary | static |
| `heat_<date>.png` | R attention (KDE of events, 14-day kernel) · G settlement (KDE of existing entities, prominence-weighted) · B freshness | **monthly to 2026-03, weekly from the wiki horizon** — the keyframe cadence follows the evidence density, so the sparse era *renders* sparse |

Shader composition per pixel (WebGL2, one quad, no three.js): paper ground → territory tint
(muted cartographic hues, borders AA'd from the distance channel) → hillshade from
`a·bedrock + b·settlement(t)` (the land literally builds up as the field grows) → contour
lines → attention as warm luminance with a slow heat-haze shimmer whose amplitude *is* the
attention value → era-tinted ambient light → procedural micro-grain keyed to
position × territory id (stable because the datum is frozen — the material-coordinate problem
solved by construction). Features (entities, arcs, strikes, labels) draw above on SVG; cards
and panels are DOM. Every channel maps to a stated mechanism (rule 2.13), and the acceptance
check is rule 2.16's full-frame screenshot assessment.

## 6. Ranked remediations → actions

1. **Build the app on this design** (A1, A4 → `/model-build`): staged below. Expected
   measurement: the ChatGPT-shock test — scrubbing 2022-11 visibly propagates attention into
   every territory; and the rule-2.16 screenshot assessment reads "a rendered landscape".
2. **Ship the date-kind audit as part of the gate** (B1 — DONE this round; the send-date bug
   class is now a structural gate failure, not a review note).
3. **Record witness baselines and stop** (C1 — DONE: matched 20, disagreements 4; the
   ratchet forbids growth). Curate W3 into a queue filing with D2, not before.
4. **Defer edge dating** (B5) and **person dots** (never — decision of record): both stay
   closed to v1.
5. **Era prose tiling per entity** (B3) is the largest remaining card-quality item and is
   NOT addressed by this round — cards ship v1 with description + series + status, honestly
   labelled, and B3 stays open at P2.

## Actions → the register

A2 → MEASURED/DELIVERED (datum v1 frozen; drift audit live) · B1 → DELIVERED (92% explicit
event dates; audit in gate) · C1 → DELIVERED (baselines recorded; instrument-error lesson
written in) · A4 → MEASURED (cadence chosen; ChatGPT-shock test defined) · A1 → staged for
`/model-build` · E1 → MEASURED (int8 recall; T0 static design viable) · A3 → DELIVERED
(territories from section prototypes; straddlers noted as future refinement).
