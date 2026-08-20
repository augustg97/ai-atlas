# AI Atlas — instructions for Claude sessions

An interactive time-model of the AI world, 2012 → today (advancing daily), built from the AI
policy wiki in August's Vault and rendered as living semantic terrain.

**Read `README.md` first** — §1 (what this is trying to be), §2 (the working rules), §7 (traps),
§9 (known limits). Then `SCOPE.md` for the contract and `HANDOFF.md` for the live state.

The general protocol lives in `/Users/augustgweon/Modeling Studio`. Its skills apply here:
`/model-research`, `/model-build`, `/model-verify`, `/model-ship`.

---

## Standing rules — these override default behaviour

1. **Always visually verify.** An update is not done when the data contains the value. It is done
   when it has been **rendered and looked at**. Render the frame, `Read` the image, confirm the
   change is on screen and is correct. "The field has the value" is not confirmation.

2. **Fix the system, not the instance.** When correcting an error, make the change at the level
   that fixes the whole **class** across the whole timeline. A patched instance leaves the same
   bug at every other time and place.

3. **Prefer structural, model-based changes over cosmetic ones.** Ask what the real-world object
   or process is, and model that. Let the appearance fall out of it. Parameter tuning produces
   "modest improvements" and never closes a gap.

4. **Measure before tuning.** Histogram it, spectrum it, or A/B each term behind a debug flag
   before changing a constant.

5. **Track every request each round and address all of them.** If something genuinely cannot be
   done, say so explicitly and say why — do not omit it.

6. **Always deploy, and verify the live artefact.** Every round ends with a build, a commit, a
   push, and a check of the live data-version stamp.

7. **Never ship on an average.** Score every item individually, before and after, and classify
   every regression.

8. **When an audit disagrees with the app, check the audit first.**

9. **Say what is contested**, in the data, as a field.

10. **"Unknown" is a legitimate return**, and where a fallback is unavoidable the UI labels it as
    a fallback.

11. **The vault is read-only, except the queue.** The one sanctioned write path into August's
    Vault is filing task files into `Wiki/_meta/queue/` (approved 2026-07-31). Fixes to wiki
    content go through the queue, never directly.

12. **Three date kinds, never conflated** — `event` / `published` / `ingested` (+ `checked`),
    everything through `frames.py`, every emitted date carries its kind. A digest filename date
    is not an event date; `last_updated` is not edit history.

13. **The map must not editorialise by geometry.** Every visual channel appears in SCOPE §3
    with a stated mechanism or it does not ship; datum changes are versioned events, never
    nightly drift.

14. **People are cards, not map features** (decision of record 2026-07-31).

15. **Nothing the record disputes is stated flatly** — `contested` renders "What the sources
    say"; ranges, not numbers; allegation vs holding distinct.

16. **The surface is the argument.** The substrate must read as a rendered landscape at
    Tectonic Earth's register — per-pixel composition, relief, texture, weather, procedural
    detail on material coordinates — never dots and symbols on flat ground. A full-frame
    screenshot is assessed honestly against this bar every round (SCOPE §7).

---

## The canonical frame

**Datum v1** — frozen, seeded 2-D projection of voyage-3-large page vectors, unit square;
rebases are versioned, Procrustes-aligned, update-log-announced events · **ISO-8601 dates, each
carrying a kind** (`event` / `published` / `ingested` / `checked`), event-date primacy ·
**wiki slugs** as canonical IDs · **ISO 3166-1 + US-XX** jurisdictions · the dev-log's
**13 sections** as territory taxonomy.

Every source is converted into it. The conversions are in `Research/modeling/frames.py`, with
selftests. **Never combine two sources without checking they are in the same frame** — this is
the most expensive class of bug in this kind of project.

## The evidence boundary

Three edges, each with designed UI behaviour (SCOPE §4): the **wiki horizon 2026-04-13**
(sub-daily coverage begins; earlier eras render sparser, labelled "reconstructed from the
record"); **today** (a hard right edge, advancing daily, no forecast pixels); and the
**construction boundary** (positions are computed — About carries "What distance on this map
is, and is not"; every card's position row says "placed by the model").

Past them, the model is inference and the UI says so.

---

## Commands

```bash
# run the app locally (preview config in .claude/launch.json, port 8143)
python3 -m http.server 8143

# the research loop
cd Research/modeling && python3 frames.py       # selftests
python3 emit.py                                  # vault → staged data
python3 audit_all.py                             # the gate

# deploy (only route)
python3 build/build_site.py && git add -A && git commit && git push
# then verify the live data-version stamp
```

- **`worldlines.mainline()` was a full Cartesian product, and every new axis multiplied it.** Its
  docstring said "≤ a few thousand cells" while r7 made it 20,160,000 and r8's eleventh axis made
  it 120,960,000. At its measured 19,722 lines a second that is 102 minutes a call, and the emit
  makes two — about three and a half hours on 2026-08-20, up from roughly half an hour the day
  before. It is now depth-first branch and bound over the same factorisation: axis k's factor
  depends only on positions already chosen, so a partial assignment can be abandoned once its
  product times the most the unassigned tail could contribute cannot reach the best complete line.
  0.53 seconds. **`mainline_enumerate()` is kept as the reference implementation and is never
  called by the emit** — `_selftest` checks the two agree on real prefixes of the live registry
  and on randomised sub-registries, on the LINE and not merely on its probability, because
  enumeration keeps the first maximum it meets and a mainline that flips between builds for no
  visible reason is worse than a slow one.

- **Check what an emit WROTE, and treat a nonzero exit as authoritative.** `forecast_emit.py`
  writes `weights.json` early and its eleven staged files at the end, none of it atomically, so a
  run stopped in between leaves weights at the new revision and `Research/staged/forecast/*` at
  the previous night's — which reads like a crash between two writes when it was an interruption.
  `forecast_emit.py || exit 2` in `build/nightly.sh` is what keeps that mixed frame out of
  `build_site.py`; on 2026-08-20 it did exactly that, with an eleven-axis `grounding.json` sitting
  against ten ten-axis files. So: read `network.json`'s version and mtime after any emit, and do
  not treat a nonzero exit as noise.

- **Two sessions must not run the emit at once.** Both call `load_weights()` and write
  `weights.json`, and neither writes atomically, so an overlapping run wins on whichever file it
  touches last. On 2026-08-20 a run begun at 10:29 would have published a `weights.json` read
  before `nightly_update` wrote that night's four applications, overwriting them. Check
  `pgrep -f forecast_emit` before starting one, and say so in the other session.

## Traps that have each cost real time here

- **The dev-log SCHEMA.md lies** — 1 of 201 files follows it; parse the prose+footnote format
  actually in use.
- **`last_updated` is not edit history** (June 2026 mass restamp) — wiki-time comes from
  `Wiki/_meta/log.md`.
- **Digest dates are not event dates** — the date-kind audit exists for exactly this.
- **The embedding index goes stale silently** (sat untouched May→July) — the nightly emit
  rebuilds it and the gate checks its timestamp.
- **Two site dirs in the vault** — `site/` is dead; read `site.nosync/`.
- **iCloud paths** — spaces and an apostrophe in the vault path: quote everything; a cold
  iCloud file can read as empty — check size before parsing.

Plus the standing ones: a process backgrounded with `&` inside a tool call dies when that call
ends; a waiter on a `pgrep` pattern can match itself — wait on a **PID**; a static host can serve
stale JSON after a successful push, so stamp the data version before copying the app file and
verify the live value.
