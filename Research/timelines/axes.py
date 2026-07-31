#!/usr/bin/env python3
"""axes.py — the living axis registry + belief network + seeded ensemble
sampler for AI Atlas v2 rev 3 (register T1). Prototype r0: proves the
architecture; the full registry lands across T1.

Design commitments implemented here (proposal rev 3, decisions of record
2026-07-31):
  - axes carry SUB-AXES; the registry is versioned and grows (add_axis /
    changelog — never silent);
  - every position carries a PRIOR with PROVENANCE (citations into the wiki);
  - CONDITIONALS form a small inspectable belief network (topологically
    ordered, acyclic by construction);
  - sample(seed) → deterministic ensemble of world-lines; conditioning by
    pinning positions;
  - EVIDENCE updates are bounded per day (the forecast breathes, never
    thrashes) and logged with their driver;
  - probabilities are the model's structured judgments — every number here
    is inspectable and none is presented as measurement.

stdlib only. python3 axes.py runs selftests + a worked demonstration.
"""

from __future__ import annotations

import json
import math
import os
import random

REGISTRY_VERSION = "r0-2026-07-31"

# The tiered impact methodology (decision of record 2026-07-31: deltas small
# ON AVERAGE, not an iron rule — "very significant events should also have
# some concomitant (but not necessarily proportional) impact"). An event's
# magnitude = class base × corroboration × novelty decay; a week of piling
# onto one axis engages a soft logistic squash, never a wall.
IMPACT_CLASS = {
    "minor": 0.003,        # routine reporting, incremental funding
    "notable": 0.008,      # enacted state law, notable release, ruling
    "major": 0.030,        # frontier capability jump, national policy turn
    "structural": 0.090,   # treaty, AI-attributed catastrophe, autonomous
}                          #   R&D demonstrated — rare by definition
WEEKLY_SOFT_CAP = 0.10     # per-axis 7-day drift where damping begins

# ---------------------------------------------------------------------------
# The seed registry. Every position: (key, label, prior, provenance[]).
# Priors are the model's opening judgments — documented, adjustable, graded.
# Wiki page slugs verified to exist 2026-07-31.
# ---------------------------------------------------------------------------

REGISTRY = {
  "version": REGISTRY_VERSION,
  "axes": [
    {"key": "T", "name": "Capability tempo",
     "cites": ["concepts/agi-timelines", "concepts/scaling-laws",
               "sources/ai-2027", "sources/aschenbrenner-situational-awareness",
               "sources/ai-as-normal-technology"],
     "positions": [
       ("T1", "explosive (SC 2027-28)", 0.10,
        ["sources/ai-2027", "sources/grading-ai-2027-2025-predictions"]),
       ("T2", "fast (2029-31)", 0.30,
        ["sources/ai-2040-plan-a", "sources/aschenbrenner-situational-awareness"]),
       ("T3", "gradual (2032-36)", 0.38,
        ["concepts/agi-timelines"]),
       ("T4", "continuous-normal (no SC in window)", 0.22,
        ["sources/ai-as-normal-technology"]),
     ],
     "subaxes": [
       {"key": "T.bench", "name": "benchmark-to-deployment lag",
        "cites": ["concepts/ai-diffusion"]},
     ]},
    {"key": "A", "name": "Alignment outcome",
     "cites": ["analysis/interpretability-and-safety",
               "concepts/responsible-scaling-policy"],
     "positions": [
       ("A1", "fails undetected", 0.12, ["sources/ai-2027"]),
       ("A2", "near-miss, managed", 0.26, ["sources/ai-2027"]),
       ("A3", "tractable with effort", 0.34,
        ["analysis/interpretability-and-safety"]),
       ("A4", "untested in window", 0.28, ["sources/ai-as-normal-technology"]),
     ]},
    {"key": "C", "name": "Coordination",
     "cites": ["analysis/coordinated-slowdown-proposals",
               "analysis/eu-vs-us-ai-regulation", "concepts/compute-governance"],
     "positions": [
       ("C1", "none / race", 0.42, ["analysis/us-china-ai-competition"]),
       ("C2", "US securitization", 0.27,
        ["sources/aschenbrenner-situational-awareness"]),
       ("C3", "US-CN transparency deal", 0.09, ["sources/ai-2040-plan-a"]),
       ("C4", "fragmented blocs", 0.22, ["analysis/eu-vs-us-ai-regulation"]),
     ],
     "subaxes": [
       {"key": "C.us-cn", "name": "US-China axis",
        "cites": ["analysis/us-china-ai-competition",
                  "concepts/export-controls-ai"]},
       {"key": "C.domestic", "name": "US domestic preemption vs patchwork",
        "cites": ["legislation/", "concepts/ai-preemption"]},
     ]},
    {"key": "D", "name": "Diffusion & labor",
     "cites": ["concepts/ai-diffusion", "concepts/ai-labor-disruption",
               "concepts/ai-displacement-vs-augmentation",
               "concepts/middle-manager-displacement",
               "concepts/professional-services-ai-adoption"],
     "positions": [
       ("D1", "shock", 0.18, ["sources/ai-2027"]),
       ("D2", "uneven by sector", 0.55,
        ["industries/healthcare", "industries/legal", "industries/financial",
         "industries/education", "industries/media"]),
       ("D3", "slow absorption", 0.27, ["sources/ai-as-normal-technology"]),
     ]},
    {"key": "S", "name": "Compute & supply",
     "cites": ["concepts/export-controls-ai", "concepts/compute-governance"],
     "positions": [
       ("S1", "concentration + flashpoint", 0.33,
        ["analysis/us-china-ai-competition"]),
       ("S2", "diversified build-out", 0.41, ["concepts/compute-governance"]),
       ("S3", "constrained (controls + energy)", 0.26,
        ["concepts/export-controls-ai"]),
     ]},
    {"key": "P", "name": "Public response",
     "cites": ["concepts/ai-backlash", "analysis/companion-chatbot-harms"],
     "positions": [
       ("P1", "populist backlash", 0.26, ["concepts/ai-backlash"]),
       ("P2", "adoption/acquiescence", 0.31, ["concepts/ai-diffusion"]),
       ("P3", "polarized-fractured", 0.43, ["sources/europe-2031"]),
     ]},
    {"key": "E", "name": "Economy",
     "cites": ["concepts/ai-bubble-debate", "analysis/ai-bubble-vs-buildout"],
     "positions": [
       ("E1", "boom sustained", 0.30, ["analysis/ai-bubble-vs-buildout"]),
       ("E2", "bubble corrects, build-out survives", 0.48,
        ["concepts/ai-bubble-debate"]),
       ("E3", "deflates hard", 0.22, ["concepts/ai-bubble-debate"]),
     ]},
  ],
  # Conditionals: child axis → {parent-position: multiplicative tilts on the
  # child's positions}. Applied in axis order (acyclic by construction).
  # Each entry cites the mechanism it encodes.
  "conditionals": {
    "A": {"T4": {"A4": 3.0, "A1": 0.2},          # no SC window → untested
          "T1": {"A4": 0.1, "A1": 2.2, "A2": 1.6}},
    "C": {"T1": {"C3": 0.4, "C2": 1.5},          # explosive tempo squeezes
          "T4": {"C2": 0.5, "C4": 1.6},          #   the deal window
          "A1": {"C3": 0.5}},
    "S": {"C2": {"S1": 1.8}, "C3": {"S2": 1.7},
          "E3": {"S3": 1.6}},                     # capex crunch constrains
    "P": {"D1": {"P1": 1.9}},                     # shock feeds backlash
    "E": {"T4": {"E3": 1.5, "E1": 0.6}},
  },
  "changelog": [
    {"version": REGISTRY_VERSION, "date": "2026-07-31",
     "change": "seed registry: 7 axes, 24 positions, 3 sub-axes, "
               "5 conditional families",
     "approved": "August (design of record, rev 3)"},
  ],
}

# Evidence rules r0: development-class → bounded weight nudges (per source).
# Applied by the nightly chain; every application logged with its driver.
# nudge values are DIRECTIONS (sign + relative share); magnitude comes from
# the impact class via impact_magnitude().
EVIDENCE_RULES = [
  {"id": "ev-state-law-enacted", "impact": "notable",
   "match": {"section": "U.S. State AI Legislation", "kind": "event"},
   "nudge": {("C", "C4"): +2, ("C", "C3"): -1},
   "cites": ["analysis/eu-vs-us-ai-regulation"]},
  {"id": "ev-export-retaliation", "impact": "notable",
   "match": {"text_any": ["retaliat", "export control", "MOFCOM"],
             "section": "National Security & Geopolitics"},
   "nudge": {("C", "C1"): +2, ("S", "S3"): +2, ("C", "C3"): -1},
   "cites": ["concepts/export-controls-ai"]},
  {"id": "ev-frontier-release-gov-coordinated", "impact": "notable",
   "match": {"text_any": ["government-coordinated", "limited preview"],
             "section": "Frontier Models & Capabilities"},
   "nudge": {("C", "C2"): +2, ("T", "T2"): +1},
   "cites": ["models/gpt-56"]},
  {"id": "ev-big-correction", "impact": "major",
   "match": {"text_any": ["writedown", "correction", "bubble bursts"],
             "section": "AI Industry & Markets"},
   "nudge": {("E", "E2"): +2, ("E", "E1"): -2},
   "cites": ["analysis/ai-bubble-vs-buildout"]},
  {"id": "ev-us-cn-agreement", "impact": "structural",
   "match": {"text_any": ["bilateral AI agreement", "AI treaty",
                          "joint verification"],
             "section": "International AI Regulation"},
   "nudge": {("C", "C3"): +3, ("C", "C1"): -2},
   "cites": ["sources/ai-2040-plan-a",
             "analysis/coordinated-slowdown-proposals"]},
  {"id": "ev-autonomous-rd-demonstrated", "impact": "structural",
   "match": {"text_any": ["autonomous AI R&D", "fully automated research"],
             "section": "Frontier Models & Capabilities"},
   "nudge": {("T", "T1"): +2, ("T", "T2"): +1, ("T", "T4"): -2},
   "cites": ["sources/ai-2027", "models/gpt-56"]},
]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def axis(reg, key):
    return next(a for a in reg["axes"] if a["key"] == key)


def normalized(weights):
    tot = sum(weights.values())
    return {k: v / tot for k, v in weights.items()}


def marginals(reg):
    return {a["key"]: normalized({p[0]: p[2] for p in a["positions"]})
            for a in reg["axes"]}


def sample_one(reg, rng, pinned=None):
    """One world-line: choose per axis in order, applying conditional tilts
    from already-chosen parents; `pinned` fixes positions (the composer)."""
    pinned = pinned or {}
    world = {}
    for a in reg["axes"]:
        k = a["key"]
        if k in pinned:
            world[k] = pinned[k]
            continue
        w = {p[0]: p[2] for p in a["positions"]}
        cond = reg["conditionals"].get(k, {})
        for parent_pos, tilts in cond.items():
            if parent_pos in world.values():
                for pos, mult in tilts.items():
                    if pos in w:
                        w[pos] *= mult
        w = normalized(w)
        r = rng.random()
        acc = 0.0
        for pos, pr in w.items():
            acc += pr
            if r <= acc:
                world[k] = pos
                break
        else:
            world[k] = pos
    return world


def ensemble(reg, n=10000, seed=20260731, pinned=None):
    rng = random.Random(seed)
    return [sample_one(reg, rng, pinned) for _ in range(n)]


def ensemble_marginals(lines):
    out = {}
    for wl in lines:
        for k, pos in wl.items():
            out.setdefault(k, {}).setdefault(pos, 0)
            out[k][pos] += 1
    n = len(lines)
    return {k: {p: c / n for p, c in v.items()} for k, v in out.items()}


def impact_magnitude(rule, sources=1, repeat_k=0):
    """Class base × corroboration (independent sources, capped ×1.5) ×
    novelty decay (k-th repeat of the same class halves). Stepwise by
    design — concomitant, not proportional."""
    base = IMPACT_CLASS[rule.get("impact", "notable")]
    corro = 1.0 + 0.25 * min(2, max(0, sources - 1))
    novelty = 0.5 ** repeat_k
    return base * corro * novelty


def soft_squash(cum, delta, cap=WEEKLY_SOFT_CAP):
    """Damp the marginal effect on an axis that has already drifted `cum`
    this week — logistic taper past the soft cap, never a hard wall, so a
    structural event still lands."""
    if abs(cum) < cap:
        return delta
    over = (abs(cum) - cap) / cap
    return delta / (1.0 + 2.0 * over)


def apply_evidence(reg, rule, log, sources=1, repeat_k=0, weekly_cum=None):
    """Apply one evidence rule under the tiered methodology. rule["nudge"]
    values are DIRECTIONS (+1/-1 scaled by their relative share); the
    magnitude comes from impact_magnitude. Every application logs its
    arithmetic — the delta is auditable end to end."""
    weekly_cum = weekly_cum if weekly_cum is not None else {}
    mag = impact_magnitude(rule, sources, repeat_k)
    total_share = sum(abs(v) for v in rule["nudge"].values()) or 1.0
    applied = {}
    for (ax_key, pos), direction in rule["nudge"].items():
        d = mag * (direction / total_share) * len(rule["nudge"])
        d = soft_squash(weekly_cum.get(ax_key, 0.0), d)
        a = axis(reg, ax_key)
        pri = {p[0]: p[2] for p in a["positions"]}
        pri[pos] = max(0.005, pri[pos] + d)
        pri = normalized(pri)
        a["positions"] = [(p[0], p[1], pri[p[0]], p[3])
                          for p in a["positions"]]
        applied[(ax_key, pos)] = d
        weekly_cum[ax_key] = weekly_cum.get(ax_key, 0.0) + abs(d)
    log.append({"rule": rule["id"],
                "impact_class": rule.get("impact", "notable"),
                "magnitude": round(mag, 5), "sources": sources,
                "repeat_k": repeat_k,
                "applied": {"%s.%s" % k: round(v, 5)
                            for k, v in applied.items()},
                "cites": rule["cites"]})
    return applied


def observe(lines, condition):
    """OBSERVATIONAL conditioning — filter the ensemble on what was learned,
    so belief propagates backward through the network (P(parents|child)).
    Distinct from the composer's do-semantics pinning, which severs the
    child from its parents. Both ship; the UI names which one it is using."""
    return [wl for wl in lines
            if all(wl.get(k) == v for k, v in condition.items())]


def add_axis(reg, axis_def, approved_by):
    """Registry growth path — never silent: bumps version and logs. Per the
    decision of record (2026-07-31), additions do NOT wait for pre-approval:
    the schema review applies them autonomously and the changelog + review
    report exist for August's post-hoc review. `approved_by` records the
    ORIGIN of the addition (e.g. "auto: weekly schema review 2026-08-04"),
    and stays mandatory so no addition is ever unattributed."""
    assert approved_by, "registry additions require recorded origin"
    assert axis_def["key"] not in [a["key"] for a in reg["axes"]]
    reg["axes"].append(axis_def)
    old = reg["version"]
    n = int(old.split("-")[0][1:]) + 1
    reg["version"] = "r%d-%s" % (n, old.split("-", 1)[1])
    reg["changelog"].append({"version": reg["version"],
                             "change": "add axis %s" % axis_def["key"],
                             "approved": approved_by})


def coverage(reg):
    pages = set()
    for a in reg["axes"]:
        pages.update(a.get("cites", []))
        for p in a["positions"]:
            pages.update(p[3])
        for s in a.get("subaxes", []):
            pages.update(s.get("cites", []))
    for r in EVIDENCE_RULES:
        pages.update(r["cites"])
    return pages


# ---------------------------------------------------------------------------
# Selftests
# ---------------------------------------------------------------------------

def _selftest():
    import copy
    reg = copy.deepcopy(REGISTRY)
    # priors normalize
    for a in reg["axes"]:
        s = sum(p[2] for p in a["positions"])
        assert abs(s - 1.0) < 1e-6, (a["key"], s)
    # determinism
    e1 = ensemble(reg, n=400, seed=7)
    e2 = ensemble(reg, n=400, seed=7)
    assert e1 == e2
    # marginals ≈ priors where unconditioned (T is a root axis)
    m = ensemble_marginals(ensemble(reg, n=8000, seed=11))
    pri = marginals(reg)["T"]
    for pos, p in pri.items():
        assert abs(m["T"][pos] - p) < 0.03, (pos, m["T"][pos], p)
    # conditionals act: A4 far likelier under pinned T4 than pinned T1
    a4_t4 = ensemble_marginals(ensemble(reg, 4000, 13, {"T": "T4"}))["A"]["A4"]
    a4_t1 = ensemble_marginals(ensemble(reg, 4000, 13, {"T": "T1"}))["A"]["A4"]
    assert a4_t4 > 3 * a4_t1, (a4_t4, a4_t1)
    # conditioning pins exactly
    for wl in ensemble(reg, 200, 5, {"C": "C3"}):
        assert wl["C"] == "C3"
    # tiered impact: structural ≫ notable ≫ minor; corroboration amplifies;
    # repeats decay; normalization holds after application
    m_minor = impact_magnitude({"impact": "minor"})
    m_note = impact_magnitude({"impact": "notable"})
    m_struct = impact_magnitude({"impact": "structural"})
    assert m_struct > 3 * m_note > 3 * m_minor
    assert impact_magnitude({"impact": "notable"}, sources=3) > m_note
    assert impact_magnitude({"impact": "notable"}, repeat_k=2) < m_note / 3
    log = []
    struct_rule = {"id": "test-struct", "impact": "structural",
                   "nudge": {("C", "C3"): +1}, "cites": ["x"]}
    before = dict((p[0], p[2]) for p in axis(reg, "C")["positions"])
    applied = apply_evidence(reg, struct_rule, log)
    moved = applied[("C", "C3")]
    assert moved > IMPACT_CLASS["notable"], "a structural event must jump"
    assert abs(sum(p[2] for p in axis(reg, "C")["positions"]) - 1.0) < 1e-6
    assert log[0]["impact_class"] == "structural" and log[0]["magnitude"] > 0
    # soft squash: the same rule against a saturated week moves less
    wc = {"C": 0.30}
    applied2 = apply_evidence(reg, struct_rule, log, weekly_cum=wc)
    assert abs(applied2[("C", "C3")]) < abs(moved)
    # observational conditioning propagates BACKWARD (unlike do-pinning):
    # T4 is likelier among lines where A4 was observed than in the prior
    lines = ensemble(reg, 8000, 17)
    obs = observe(lines, {"A": "A4"})
    assert len(obs) > 200
    pT4_obs = sum(1 for w in obs if w["T"] == "T4") / len(obs)
    pT4_prior = sum(1 for w in lines if w["T"] == "T4") / len(lines)
    assert pT4_obs > 1.5 * pT4_prior, (pT4_obs, pT4_prior)
    # registry growth: version bumps, changelog records origin; unattributed
    # additions still fail (autonomy ≠ anonymity)
    add_axis(reg, {"key": "X", "name": "test axis", "cites": [],
                   "positions": [("X1", "a", 0.5, []), ("X2", "b", 0.5, [])]},
             approved_by="auto: schema review selftest")
    assert reg["version"].startswith("r1-")
    assert "schema review" in reg["changelog"][-1]["approved"]
    try:
        add_axis(reg, {"key": "Y", "name": "y", "cites": [],
                       "positions": [("Y1", "a", 1.0, [])]}, approved_by="")
        assert False, "unattributed addition must fail"
    except AssertionError as ex:
        assert "origin" in str(ex)
    return 8


if __name__ == "__main__":
    n = _selftest()
    print("axes.py selftest: %d groups passed" % n)
    reg = json.loads(json.dumps(REGISTRY))  # work on a copy
    # priors normalize on load (seed values are close; normalize exactly)
    for a in reg["axes"]:
        pri = normalized({p[0]: p[2] for p in a["positions"]})
        a["positions"] = [[p[0], p[1], round(pri[p[0]], 5), p[3]]
                          for p in a["positions"]]
    print("registry %s: %d axes, %d positions, %d sub-axes" %
          (reg["version"], len(reg["axes"]),
           sum(len(a["positions"]) for a in reg["axes"]),
           sum(len(a.get("subaxes", [])) for a in reg["axes"])))
    print("wiki pages cited by the seed registry: %d" % len(coverage(reg)))
    m = ensemble_marginals(ensemble(reg, 10000))
    print("\nunconditioned marginals (10k samples, seed 20260731):")
    for k, v in m.items():
        top = sorted(v.items(), key=lambda x: -x[1])
        print("  %s: %s" % (k, "  ".join("%s %.2f" % t for t in top)))
    mc = ensemble_marginals(ensemble(reg, 10000, pinned={"C": "C3"}))
    print("\nconditioned on C3 (the deal): tempo shifts to %s" %
          "  ".join("%s %.2f" % t for t in
                    sorted(mc["T"].items(), key=lambda x: -x[1])))
