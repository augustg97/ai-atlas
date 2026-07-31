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
| — | nothing yet; the scaffold is the only artefact | — |

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

**What the audits did NOT find:** nothing yet — no audits have run. First baselines land with C1
and B1.

---

**Count: 16 items — 4 at P1.** The ones that would move the model furthest, in order:

1. **A1** — the visual bar: the field-engine design study (the user's named worry).
2. **A2** — datum v1: until it lands, nothing has a position.
3. **B1** — the dated spine with date kinds audited: until it lands, nothing has a time.
4. **C1** — the witnesses: the instrument every later dispute is settled with.
5. **D1** — the nightly chain: the "ongoing basis" the project exists for.
