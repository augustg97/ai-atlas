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

**Kickoff complete, 2026-07-31.** Scaffold + SCOPE + survey + register exist; no research round
has run; no app code beyond the scaffold shell.

**Round 1 — the datum round — in priority order:**

1. **Refresh the embedding index** (`bin/build-embedding-index.py` in the vault; incremental,
   needs `VOYAGE_API_KEY`) — everything else waits on it.
2. **Datum v1** (register A2): method study → freeze → `frames.py` with selftests → ε and the
   drift audit. Deliverable: every current page has a stable (x,y), and the transform is
   versioned and shipped.
3. **Emit v0** (B1): entities + windows + events with date kinds; needs-review report; the
   date-kind audit red/green.
4. **Witness bootstrap** (C1): Epoch fetched, mapped, audited both directions; tracker named;
   docket check scripted. First baselines recorded.
5. **The field-engine design study** (A1): dossier + white paper ending in staged changes for
   the v0.1/v0.2 build — how the terrain, weather and settlement fabric are actually computed,
   with reference frames from Tectonic Earth's shader read alongside.

Round 1 ends with a white paper, staged changes, and the register updated — then `/model-build`
takes the staged changes into the app.
