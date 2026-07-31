# Research — the AI-world knowledge base for AI Atlas

**Started 2026-07-31.** A standing research programme covering the datum (semantic
cartography), the dated spine of the AI world 2012→now, the witnesses that score the model, the
field-engine design that must clear the visual bar, and Ask the Atlas.

**This folder does not change the model.** Nothing here is imported by the app or `build/`. Its
output is *evidence and models* that inform deliberate, staged changes to the app — so that when
a position, a window, a card or a surface changes, the change has a citation and a mechanism
behind it rather than a guess.

---

## How it is organised

```
Research/
├── SOURCE-SURVEY.md              what data exists, in what frame, under what licence — DONE at kickoff
├── MODEL-GAPS.md                 the register — 16 items seeded at kickoff, 4 at P1
├── research/                     evidence: dossiers per domain, with sources and caution flags
│   └── 09-source-documents/      fetched primary material, kept verbatim
├── research reports/             illustrated white papers, each ending in actions
│   └── STAGED-CHANGES.md         the handover surface
├── modeling/                     runnable models + read-only audits
│   ├── frames.py                 (round 1) the canonical frame: datum, date kinds, slugs, jurisdictions
│   ├── emit.py                   (round 1) vault → staged data
│   └── audit_all.py              the gate
└── figures/
    ├── authored/                 generated FROM the models, so they cannot drift
    └── collected/                third-party + MANIFEST.json (licence + review verdict)
```

## The models

All runnable, all self-testing. None exist yet — round 1 creates the first three
(`frames.py`, `emit.py` v0, the Epoch witness module).

## The audits

Read-only; they change nothing. First baselines land in round 1 (register C1, B1).

## The dossiers

| planned, round 1 | covers |
|---|---|
| `01-datum/` | projection method study: seeded determinism, stability under corpus growth, ε measurement, rebase protocol |
| `02-field-engine/` | porting Tectonic's substrate patterns to abstract space — relief from density, material coordinates, procedural fabric, attention as weather (register A1, the user's named worry) |
| `03-spine/` | date-kind extraction coverage; the 2012–2020 era; chapter proposal from the wiki's analysis pages |

---

## Working method

1. **Verify, don't reconstruct from memory.** Every claim traces to a named source; where a
   fetched source is internally inconsistent, the dossier says so rather than propagating it.
2. **Say what is contested.** A card that states an open question flatly misrepresents how well
   it is known.
3. **Prefer a model to a table.** Every finding that could be a hand-written row is written as a
   function with a selftest, so a new input produces a defensible answer without new authoring.
4. **Figures are generated, not drawn.** They read from the same modules, so a corrected value
   propagates automatically.
5. **Every white paper ends in actions**, and every action lands in `MODEL-GAPS.md`.

---

## Status

**Round 1 complete and APPLIED; v1.0 live, 2026-07-31** at
https://augustg97.github.io/ai-atlas/ (stamp 20260731-0207 verified). The full path ran in one
session: embedding refresh (13,737 chunks) → datum v1 frozen (int8 recall 0.989) → emit
(855 entities · 1,825 events 92% event-dated · 11,397 arcs) → witness baselined (20 matched /
4 unit-choice disagreements) → 190 field keyframes → gate PASS → app built → deployed →
live-verified → nightly scheduled → 6 queue tasks filed into the vault.

WP-01 records the round; the register's APPLIED table records the measurements; HANDOFF.md
carries the honest assessment (shock test partial-pass, corpus-limited; resting substrate
good-not-yet-Tectonic).

**Next round, in priority order:** watch three nightlies (D1 acceptance) · visual round 2
(A1 continuation, against captured reference framings — F1) · B3 era-prose tiling ·
jurisdiction view · E2 worker tier (needs August's key + CF approval) · C1 W3 curation.
