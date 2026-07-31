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
  `build/nightly.sh`: trunk emit → witness → nightly_update → grounding → forecast_emit →
  gate → stamp → push → live verify. Its prompt (in `~/.claude/scheduled-tasks/`) requires
  attributed deltas, verbatim SCHEMA ADDITIONS blocks, claim-resolution notes, and forbids
  SKIP_AUDIT. **Acceptance (T4/D1): three unattended correct mornings — WATCH THEM.**
- weights.json (Research/timelines/) is the evolving state; the seed priors live in
  axes.REGISTRY. delta panel reads the evidence log; marginals history accrues daily.
- The queue loop remains live (6 tasks filed earlier drain with the vault's cycles).

## Honest limits, recorded

- World view is features-on-real-geography, not per-pixel lit terrain — T8 is the §13a round.
- Six evidence rules are a floor (T9); residue will dominate mornings until the library grows.
- exemplars.json ships unused (T6); calibration claims register exists but the Brier scorer
  is T7; sub-axes are registered but do not yet drive tracks (T10).
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
  output, don't assume refusal.

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
