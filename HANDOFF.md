# Handoff — AI Atlas

Paste this whole file as the first message of a new session.

---

## What you are working on

**AI Atlas v2 — the living forecast**: a probabilistic world-model of the AI transition,
2012 → 2100, built from the AI policy wiki in August's Vault and re-sampled every morning as
the wiki records what actually happened. Probabilities are the product (decision of record,
SCOPE §11b); the composer is the instrument for asking *what if*.

- Repo: `/Users/augustgweon/AI Atlas` · GitHub `augustg97/ai-atlas` (Pages serves `main:/docs`)
- **Live: https://augustg97.github.io/ai-atlas/** — v2 shipped 2026-07-31, stamp
  `20260731-0510` verified; v1's semantic terrain is retired completely.
- **Read `README.md` §1-§2** (visual bar + rules), **`SCOPE.md`** (§11/§11b = August's
  decisions verbatim; the full v2 SCOPE rewrite is open item T5), **`Research/MODEL-GAPS.md`**
  (the register — T-round outcomes + 27 open items), and the proposal artifact rev 3
  (33657b8d-2c49-4129-8afe-0ec977e6b5c3).

## The system, in one paragraph

`Research/timelines/` is the engine: `axes.py` (7-axis belief network; tiered impact
methodology — minor/notable/major/structural × corroboration × novelty with a weekly soft
squash; do-pinning AND observational conditioning; registry grows autonomously with an origin
log, never silently), `worldlines.py` (capability paths incl. Plan A's C3 pause shelf; annual
tracks 2026-2100; 26 cited event templates incl. the strange far field; exact-argmax
mainline), `wiki_grounding.py` (1,221 direct + 479 corpus pages; thin axes widen priors),
`forecast_emit.py` (staged/forecast/*: engine.json is the SINGLE SOURCE of constants the app's
JS implements functions against), `nightly_update.py` (classify → tiered updates with drivers
→ residue → Monday schema review that can auto-add sub-axes, logged for August's post-hoc
review). The app (`web/index.html`) renders the probability river on a piecewise time scale,
the composer (client-side resampling; the mode chip names do vs observe), the instrument rail
(axis bars + 30-day drift, delta panel, pills/donut/copies/stats), narrative waypoint cards
with citations, and the World view (real Earth, regime tints ∝ compute share, 16 authored
sites glowing by modelled GW). The gate (`Research/modeling/audit_all.py`) now also checks the
forecast surface and ratchets grounding.

## State right now

- Live and verified; the nightly task `ai-atlas-nightly` (10:47 local) runs
  `build/nightly.sh`: trunk emit → witness (epoch + **statelaw**) → nightly_update →
  grounding → forecast_emit → gate → stamp → push → live verify. Its prompt (in
  `~/.claude/scheduled-tasks/`) requires attributed deltas, verbatim SCHEMA ADDITIONS blocks,
  claim-resolution notes, and forbids SKIP_AUDIT.
- **D1/T4 acceptance PASSED 2026-08-02** (three unattended mornings, gate PASS each). Mornings
  1–4 then produced the machine's central finding: **the forecast never moved on evidence** —
  14 fresh events, 14 residue, `evidence_log` empty, and by morning 4 the distribution was
  static to 2.4e-16.
- **Evidence layer r1 shipped 2026-08-04 (`09ff4fc`, stamp `20260804-0129`)** — August's
  "fix all of the issues flagged" round. Registry `r0-2026-07-31` → `r1-2026-08-03`. Six
  repairs, in the order they matter:
  1. **Day boundary** — the watermark selector dropped 84% of events (41 of 49 on settled
     days), including the only item that ever satisfied a rule. Now a **seen-ledger** on a
     collision-free fingerprint, 14-day lookback, floored at the nightly epoch.
  2. **Matcher** — whole-word terms with explicit `*` stems, section aliases onto the
     canonical 13 (matching only), `text_all` / `text_none` / `section_any` / `kind_any` /
     `min_sources` / `update`.
  3. **Rule set** — `ev-state-law-enacted` had no content gate (fired on section+kind alone);
     and `IMPACT_CLASS`'s **`minor` tier had no rules at all**, so nothing watched the
     mainline. 15 mainline rules added, most sections read both ways. Coverage 3.55% → 30.4%.
  4. **Claim registration** — no longer stamped `today` nightly; held in weights.json,
     back-filled to the true 2026-07-31.
  5. **State-law counter** — `witness_statelaw.py`, 8 laws / 7 states, a declared **lower
     bound** that the gate fails if it ever claims it can refute.
  6. **Gate** — DRIFT report vs the previous run + ratchet-forward on improvement;
     `review.n` → `review.pct`.
  Effect: 55 events considered vs 6, **16 applications vs 0**, total L1 0.100. Mainline path
  unchanged (T3·A3·C1·D2·S2·P3·E2).
- weights.json (Research/timelines/) is the evolving state; it now also carries `seen`,
  `schema_log`, `claims_registered`, and `residue_r0` (the pre-r1 residue, archived not
  deleted). The seed priors live in axes.REGISTRY.
- The queue loop remains live; `INGEST-ncsl-state-ai-legislation-tracker` filed 2026-08-04.

## Honest limits, recorded

- World view is features-on-real-geography, not per-pixel lit terrain — T8 is the §13a round.
- exemplars.json ships unused (T6); sub-axes are registered but do not yet drive tracks (T10).
- **`cl-state-laws-2026` still cannot be scored.** Three different universes sit under it: 8
  observed enactments (wiki lower bound), a *projected* `laws` track seeded at a hardcoded
  **61** whose provenance is a code comment, and a threshold of 90. The queue task asks for
  NCSL; the right outcome may be to **reword the claim** rather than score it.
- **Duplicate reports still count separately.** Illinois SB 315 was reported by four digests
  and fires the rule four times; novelty decay damps it (0.008 → 0.015 total, not 0.032) but
  entity resolution would be the real fix.
- The r1 rule set is **cited but not calibrated** — directions are argued from the axis
  stories, never fitted. Nothing has been scored against outcomes yet; that is the Brier
  round (T7), for which registration dates are now finally usable.
- `apply_schema_log` is exercised by selftest and a dry run but **has not yet fired in
  production** — the next Monday review is 2026-08-10.
- Priors are the model's opening judgments with provenance — August may adjust; the About
  page says all of this in public.

## Traps (beyond README §7)

- `style.display=""` restores the STYLESHEET value — for #world that meant `none`; the world
  drew perfectly on an invisible canvas. Use explicit "block"/"none".
- The app implements FUNCTIONS against engine.json CONSTANTS — never mirror a literal into
  JS; extend engine.json instead (single source of truth).
- Percentile bands saturate at the ladder ceiling by the 2040s in most sampled futures —
  that is the model speaking, not a bug; the piecewise x-scale exists so the action keeps
  its pixels.
- The gate self-extends its baseline on first new-check runs (recorded in stdout) — read the
  output, don't assume refusal. Since r1 it ALSO ratchets forward on improvement and prints a
  DRIFT block vs the previous run; both are stdout-only, so read them.
- **`nightly.sh` runs `git add -A`.** Any uncommitted working-tree change is swept into a
  commit messaged "Nightly emit YYYY-MM-DD". The r1 source changes landed that way in
  `cb15cd9` before being documented in `09ff4fc`. Commit your work before running the chain.
- A trailing `*` in a rule term means STEM; without it the term is a whole word. Writing
  "invest" where you meant "invest*" silently matches nothing, and the rule looks alive.
- `text` in the trunk is truncated near 300 chars. Anything the matcher or a witness needs to
  read must be in the opening prose — Tennessee's enactment is cut off mid-sentence and is
  therefore, correctly, not counted.

## The work queue (register order)

1. Watch three mornings (T4/D1 acceptance); expect residue-heavy first reports.
2. **T7** calibration scorer (first claim deadlines: 2026-12-31).
3. **T8** World view to the full visual bar.
4. **T9** evidence-rule library expansion (target ~40 rules with citations).
5. T6 variance narrative · T10 sub-axis dynamics · T5 SCOPE v2 rewrite · then B3/E2/C1-cur.

## Commands

```bash
# app locally (or preview_start name="ai-atlas"): serve repo root, open /web/
python3 -m http.server 8143 --directory "/Users/augustgweon/AI Atlas"

# engine loop
cd "/Users/augustgweon/AI Atlas/Research/timelines" && \
  python3 axes.py && python3 worldlines.py && python3 nightly_update.py && \
  python3 wiki_grounding.py && python3 forecast_emit.py
cd ../modeling && python3 audit_all.py

# deploy (only route; gate inside)
python3 build/build_site.py && git add -A && git commit && git push
# then verify the live DATA_V stamp (build prints the curl)

# the whole morning, manually
bash build/nightly.sh
```

## How the user wants this done

README §2 + SCOPE §11b, distilled: **probabilities are the product** — documented, cited,
bounded-on-average but concomitant with big events, graded in public · **the registry lives**
— add axes/sub-axes autonomously with a clear log for review, never silently · **deep wiki**
— more pages informing the model every round, coverage ratcheted · **visually rich and
legible** — Tectonic Earth craft, AI 2027 legibility, real-world surfaces · **honesty
everywhere** — do vs observe named on screen, hedges never flattened, thin grounding rendered
as width, the About page owes every mechanism.
