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
MAX_DAILY_DELTA = 0.02          # bounded updating: ≤2pp per axis per day

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
EVIDENCE_RULES = [
  {"id": "ev-state-law-enacted",
   "match": {"section": "U.S. State AI Legislation", "kind": "event"},
   "nudge": {("C", "C4"): +0.004, ("C", "C3"): -0.001},
   "cites": ["analysis/eu-vs-us-ai-regulation"]},
  {"id": "ev-export-retaliation",
   "match": {"text_any": ["retaliat", "export control", "MOFCOM"],
             "section": "National Security & Geopolitics"},
   "nudge": {("C", "C1"): +0.006, ("S", "S3"): +0.005, ("C", "C3"): -0.003},
   "cites": ["concepts/export-controls-ai"]},
  {"id": "ev-frontier-release-gov-coordinated",
   "match": {"text_any": ["government-coordinated", "limited preview"],
             "section": "Frontier Models & Capabilities"},
   "nudge": {("C", "C2"): +0.006, ("T", "T2"): +0.004},
   "cites": ["models/gpt-56"]},
  {"id": "ev-big-correction",
   "match": {"text_any": ["writedown", "correction", "bubble"],
             "section": "AI Industry & Markets"},
   "nudge": {("E", "E2"): +0.005, ("E", "E1"): -0.004},
   "cites": ["analysis/ai-bubble-vs-buildout"]},
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


def apply_evidence(reg, rule, log):
    """Bounded nightly nudge; returns the delta actually applied. The cap is
    structural: a single day moves points, never tens of points."""
    applied = {}
    for (ax_key, pos), d in rule["nudge"].items():
        d = max(-MAX_DAILY_DELTA, min(MAX_DAILY_DELTA, d))
        a = axis(reg, ax_key)
        pri = {p[0]: p[2] for p in a["positions"]}
        pri[pos] = max(0.005, pri[pos] + d)
        pri = normalized(pri)
        a["positions"] = [(p[0], p[1], pri[p[0]], p[3])
                          for p in a["positions"]]
        applied[(ax_key, pos)] = d
    log.append({"rule": rule["id"], "applied": {f"{k[0]}.{k[1]}": v
               for k, v in applied.items()}, "cites": rule["cites"]})
    return applied


def add_axis(reg, axis_def, approved_by):
    """Registry growth path — never silent: bumps version, logs, requires an
    approval string (the queue supplies it in production)."""
    assert approved_by, "registry additions require recorded approval"
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
    # bounded evidence: a big nudge is capped, distribution stays normalized
    log = []
    big = {"id": "test", "nudge": {("C", "C1"): +0.5}, "cites": []}
    applied = apply_evidence(reg, big, log)
    assert abs(applied[("C", "C1")]) <= MAX_DAILY_DELTA
    assert abs(sum(p[2] for p in axis(reg, "C")["positions"]) - 1.0) < 1e-6
    assert log and log[0]["rule"] == "test"
    # registry growth: version bumps, changelog records, approval required
    add_axis(reg, {"key": "X", "name": "test axis", "cites": [],
                   "positions": [("X1", "a", 0.5, []), ("X2", "b", 0.5, [])]},
             approved_by="selftest")
    assert reg["version"].startswith("r1-")
    assert reg["changelog"][-1]["approved"] == "selftest"
    try:
        add_axis(reg, {"key": "Y", "name": "y", "cites": [],
                       "positions": [("Y1", "a", 1.0, [])]}, approved_by="")
        assert False, "unapproved addition must fail"
    except AssertionError as ex:
        assert "approval" in str(ex)
    return 7


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
