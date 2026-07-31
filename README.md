# AI Atlas

An interactive time-model of the AI world — 2012 to today, advancing daily — built from the AI
policy wiki in August's Vault. The idea plane rendered as living terrain: territories of the
field, attention as weather, entities as grown structures, every one of them clickable, every
claim cited, every uncertainty shown.

**Live:** https://augustg97.github.io/ai-atlas/ (once first shipped; Pages serves `main:/docs`)
**Source of truth:** August's Vault (read-only, except the approved `Wiki/_meta/queue/` loop)

---

## 1. What this is trying to be

A **model**, not a slideshow. The app ships the emitted state of the AI world — entities with
lifetimes, dated events, typed relationships, quantitative series, field keyframes — plus the
rules to compose them, and assembles the world at render time. Nothing is a pre-rendered picture
of a moment.

That choice is the whole architecture, and everything below follows from it:

- The surface at any date is composed per pixel from interpolated fields — attention brightens,
  territories swell, the ChatGPT shock propagates — rather than one chart dissolving into
  another.
- An entity grows because its Snapshot series says so; a card rewrites itself for the date on
  the timeline; adding a date between two authored ones produces a defensible frame without new
  authoring.
- Every layer is derived from the same emitted data, so the layers cannot disagree with each
  other — and the chatbot answers from that same data, so it cannot disagree with the map.

### Goals

1. **Veracity first.** Where the wiki's record says something, follow it — dates, statuses,
   ranges, contested claims. Where the model computes something (positions, territories,
   prominence), say plainly that it is computed.
2. **Coherence.** One world: a single emitted state feeds the terrain, the features, the cards,
   the readout, the jurisdiction view and the chatbot.
3. **Detail that survives inspection.** Zooming into a territory reveals structure — settlement
   fabric grown from the series, texture keyed to material coordinates — not blur. **The named
   bar is Tectonic Earth: a living, breathing surface, not dots and symbols** (decision of
   record, 2026-07-31; SCOPE §11).
4. **Honesty about uncertainty.** The wiki's confidence and decay ratings render on every card;
   contested claims show both sides; the knowledge-horizon layer shows what the wiki had not
   yet learned; the About page says what distance on this map is, and is not.

---

## 2. Working rules

Standing constraints on how work is done here, not suggestions. Each came from a specific
failure. *(Copied from `Modeling Studio/references/WORKING-RULES.md` — keep in sync; add rules
as new failures produce them.)*

**2.1 Always visually verify.** An update is not done when the data contains the value. It is
done when it has been rendered and looked at.

**2.2 Fix the system, not the instance.** Make the change at the level that fixes the whole class
across the whole timeline.

**2.3 Prefer structural, model-based changes over cosmetic ones.** Model the object or process;
let the appearance fall out of it.

**2.4 Measure before tuning.** If you cannot say what the number is now, you cannot say your
change improved it.

**2.5 Track every request; never silently drop one.** If something cannot be done, say so and say
why.

**2.6 Always deploy, and verify the live artefact.** Local-only changes read as "not done".

**2.7 Never ship on an average.** Score every item individually and classify every regression.

**2.8 When an audit disagrees with the app, check the audit first.**

**2.9 Say what is contested.** Confidence is a field on the data, not a footnote.

**2.10 "Unknown" is a legitimate return** — and where a fallback is unavoidable, the UI labels it.

### Project-specific rules

**2.11 The vault is read-only, except the queue.** The emitter never writes into August's Vault;
the one sanctioned write path is filing task files into `Wiki/_meta/queue/` (approved
2026-07-31). Fixes to wiki content go through the queue, never directly.

**2.12 Three date kinds, never conflated.** `event` / `published` / `ingested` (+ `checked`).
A digest's filename date is not an event date; `last_updated` is not edit history. Everything
through `frames.py`; every date in emitted data carries its kind.

**2.13 The map must not editorialise by geometry.** Every visual channel appears in the SCOPE §3
layer table with a stated mechanism, or it does not ship. Proximity is a property of the corpus
and the About page says so. Datum changes are versioned events, never nightly drift.

**2.14 People are cards, not map features** (decision of record). Only documented, cited,
neutral facts on person cards; no inferred person-to-person networks.

**2.15 Nothing the record disputes is stated flatly.** `contested` renders "What the sources
say"; ranges, not numbers, for contested quantities; allegation vs holding distinct on
litigation cards.

**2.16 The surface is the argument.** The substrate must read as a rendered landscape, not a
chart — per-pixel composition, relief, texture, weather, procedural detail on material
coordinates. A round that adds information by adding dots and symbols to a flat ground is going
backwards; the acceptance check is a full-frame screenshot assessed honestly against Tectonic
Earth's register (SCOPE §7).

---

## 3. Repository layout

```
SCOPE.md                the contract — read before changing anything
Research/               the standing research programme; never imported by the app or build
  SOURCE-SURVEY.md      what data exists, frames, licences, witnesses
  MODEL-GAPS.md         the register — the handover surface between research and build
  modeling/             frames.py, emit.py, runnable models, audit_all.py + audits
index.html · js/ · css/ · data/    the app shell (feature side) — working copy
web/                    field-side working data (keyframes, datum) as the engine grows
build/                  build_site.py: gate → stamp → docs/
docs/                   the built static site; GitHub Pages serves main:/docs
reference/              measured-against material (gitignored, never shipped)
```

---

## 4. The layers

The full table with mechanisms is **SCOPE §3** — it is the project's spine and every round is
measured against it. Summary: territory terrain, boundaries + names, attention weather
(**modelled fields**); entities, growth footprints, typed arcs, event strikes, knowledge
horizon (**authored features, modelled positions**); eras/chapters (**authored**); jurisdiction
view + readout + Ask the Atlas (**derived**); people (**cards only**).

---

## 5. Subsystems

- **The emitter** (`Research/modeling/emit.py`) — vault → staged JSON (entities, events, arcs,
  series, eras, datum, quantized chat index). Normalises the known hygiene defects in one
  place; unparseable → needs-review, never guessed.
- **The datum** (`frames.py`) — the frozen semantic projection, its transform parameters,
  drift audit, and the versioned rebase protocol (Procrustes-aligned, update-log announced).
- **The engine** — WebGL field compositor (terrain, attention, territories) + feature overlays
  (entities, arcs, strikes) + DOM cards, one scalar `t` driving all of it; two-keyframe lazy
  loading from day one.
- **The card system** — the SCOPE §6 contract: fact rows, era-keyed prose tiling the entity's
  life (audited), visible span, confidence + decay badge, citations deep-linking into the
  vault's live dashboard.
- **Ask the Atlas** — SCOPE §12: Tier 0 semantic navigation fully static; Tier 2 grounded
  synthesis via a small worker, every claim carrying an enforced card citation; index rebuilt
  nightly so it can never go stale again.
- **The daily machine** — nightly emit after the vault's 09:22 cycle → gate → stamp → deploy →
  live-stamp verification → automated update-log line; audit findings filed into the wiki's
  queue.

---

## 6. Build and deploy

```bash
# research loop
cd Research/modeling && python3 frames.py        # selftests
python3 emit.py                                   # vault → staged data
python3 audit_all.py                              # the gate (--quick to skip slow ones)

# deploy (only route)
python3 build/build_site.py && git add -A && git commit && git push
# then verify the live data-version stamp (the build prints the curl line)
```

The build **runs the validators first and refuses to publish if one moved backwards**.

| check | baseline | what it catches |
|---|---|---|
| existence windows | 0 | anything drawn before it existed or after it ended |
| card contract | 0 / 0 | missing citations, missing confidence, era gaps/overlaps in prose tiling |
| frame stability | ε (set round 1) | unchanged pages moving between emits — the datum quietly re-fitting |
| witness: Epoch models | recorded | releases missing or misdated, both directions |
| witness: state-law tracker | recorded | legislation counts by status diverging at spot dates |
| witness: dockets | recorded | litigation status drift vs public record |
| date-kind audit | 0 | an `event` field carrying a `published` date (the send-date bug class) |
| needs-review count | recorded | normaliser fallout growing instead of shrinking |

Baselines are not all zero and should not be; the rule is **none may move backwards**, tighten
in the same commit when one improves, `SKIP_AUDIT=1` overrides deliberately awkwardly.
**Verify the live data-version stamp after every push.**

---

## 7. Traps

*(General catalogue: `Modeling Studio/references/TRAPS.md`; the vault-specific ones found at
kickoff — add new ones here and there.)*

- **The dev-log SCHEMA.md lies** — 1 of 201 files follows it. Parse the prose+footnote format
  actually in use.
- **`last_updated` is not edit history** (June 2026 mass restamp). Wiki-time comes from
  `log.md`.
- **Digest dates are not event dates.** The send-date-as-event-date bug is the reason the
  vault's source-fidelity skill exists; the date-kind audit enforces it here.
- **The embedding index goes stale silently** — it sat untouched from May to July. The nightly
  emit rebuilds it; the gate checks the index timestamp against the emit timestamp.
- **Two site dirs in the vault** — `site/` is dead; read `site.nosync/`.
- **iCloud paths** — the vault lives under `~/Library/Mobile Documents/...` with spaces and an
  apostrophe; quote everything; a cold iCloud file can read as empty — check size before
  parsing.
- **The stale-dev-JS trap (inherited from Aztec, bitten four times there)** — dev serving
  carries no cache-buster; read a value back through the console before believing a null
  result.

---

## 8. Sources

| role | source |
|---|---|
| primary corpus | August's Vault (wiki + dev-log + log.md + Snapshot tables + embeddings) |
| 2012–2020 spine + models witness | Epoch AI notable-models dataset (CC-BY, attributed) |
| legislation witness | named US state-AI-law tracker (measure-against-only) |
| litigation witness | CourtListener dockets (measure-against-only) |
| aggregate sanity | Stanford AI Index, at rebase points |

**Canonical frame:** datum v1 positions · ISO dates with kinds · wiki slugs · ISO 3166 + US-XX ·
the 13-section taxonomy — conversions in `Research/modeling/frames.py`, with selftests.

---

## 9. Known limits

- **Positions are constructions.** The idea plane is a frozen projection of embeddings —
  adjacency reflects the corpus's language, not alliance or causation. Said in About, on every
  card's position row, and enforced by rule 2.13.
- **Coverage is the wiki's coverage.** Dense from 2026-04-13; reconstructed before that; the
  knowledge-horizon layer makes this visible instead of implying omniscience.
- **Relationships are undated.** Arcs draw while both endpoints exist; when a relationship
  began is not claimed.
- **Prominence is proxied** (link degree + mention counts), not measured influence — labelled
  as modelled.
- **The wiki inherits its sources' disputes.** Contested amounts stay ranges; both sides render;
  the model never resolves what the record does not.

---

## 10. Reference material

`reference/` (gitignored): visual-standard framings captured at v0.2 (five, at stated zooms);
witness snapshots as fetched at audit time. The Tectonic Earth engine
(`~/Tectonic Plate Model/web/index.html`) is the standing architectural reference — read its
FRAG shader and loader before building the field engine here.

`HANDOFF.md` carries the live state, the measured facts, and the work queue for a fresh session.
