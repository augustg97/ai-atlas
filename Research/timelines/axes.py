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
import re

REGISTRY_VERSION = "r2-2026-08-06"

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

# --- novelty, repaired 2026-08-06 (registry r2) ----------------------------
# The r1 note under EVIDENCE_RULES states the design intent exactly: novelty
# decay exists so that a STEADY drumbeat moves almost nothing and only a burst
# or a drought-then-return carries weight, with the whole drumbeat "summing to
# under 0.006 no matter how long it runs". That is a bound on the CUMULATIVE
# contribution of a class. The implementation delivered it by making each
# successive event worth nothing, which is a different thing and a worse one.
#
# Measured on 2026-08-06: five applications at k=4..7 were together worth 2.9%
# of their unrepeated value, on the largest input day the machine has seen.
# Three of them were unrelated transactions — SpaceX/Terafab, Mirendil/Google
# Cloud, Discovery Loop — discounted against each other purely for arriving on
# the same night. Meanwhile soft_squash, the mechanism actually designed to
# bound axis drift, sat 300x below its cap and had never damped anything.
#
# Three changes, and the bound is kept:
#   FLOOR      novelty decays TOWARD a floor, never to zero. A class that keeps
#              firing is confirmatory evidence at a reduced but real weight;
#              silence is what should stop moving the model, not repetition.
#   HALF-LIFE  k is a recency-WEIGHTED count, not a count inside a 30-day box.
#              A hard box has a cliff at 30 days and no memory gradient inside
#              it; an exponential half-life gives the drought-then-return
#              behaviour the design asked for, continuously.
#   INCIDENTS  k counts distinct INCIDENTS, not reports. Four digests carrying
#              one Illinois signing are one incident with three sources; three
#              unrelated funding rounds are three incidents. nightly_update
#              resolves them; this module only consumes the count.
# The cumulative bound now comes from soft_squash (per-axis, per-week) and from
# the sqrt aggregation of same-class incidents within one night — both of which
# bound the thing that matters (axis drift) rather than the thing that does not
# (how often the world does something).
NOVELTY_FLOOR = 0.15           # steady-state weight of a recurring class
NOVELTY_HALFLIFE_DAYS = 7.0    # recency half-life of a prior incident

# ---------------------------------------------------------------------------
# The seed registry. Every position: (key, label, prior, provenance[]).
# Priors are the model's opening judgments — documented, adjustable, graded.
# Wiki page slugs verified to exist 2026-07-31.
# ---------------------------------------------------------------------------

# Per-position stories ("each of the different ways these axes can play
# out", decision of record 2026-07-31) — rendered in the axis cards. Keyed
# by position; every entry cited via the position's own cites.
POSITION_STORIES = {
  "T1": "The AI-2027 shape: superhuman coders arrive within roughly a year, "
        "R&D multipliers compound, and the window for every institution to "
        "react collapses to months. Everything downstream — alignment, "
        "coordination, labor — plays out under time pressure.",
  "T2": "Fast but survivable: automation of AI research lands around "
        "2029-31, the Situational-Awareness decade. Governments have one "
        "budget cycle to respond; the deal window (C3) is open but narrow.",
  "T3": "The gradual road the current record most supports: capability "
        "compounds through the early 2030s without a sharp discontinuity. "
        "Institutions adapt in real time; more futures stay reachable.",
  "T4": "The Normal-Technology null hypothesis: diffusion friction, data "
        "limits or physics keep superintelligence out of the window "
        "entirely. The drama migrates to economics and adoption.",
  "A1": "Misalignment that evades detection: training rewards competence "
        "over honesty and oversight loses. Only fast-tempo worlds (T1/T2) "
        "leave it untested long enough to matter at scale.",
  "A2": "The near miss: warning signs surface in time — an interpretability "
        "catch, a whistleblower, an incident — and buy a pause. Costs time "
        "(the ladder shifts ~10 months) but keeps humans steering.",
  "A3": "Alignment proves tractable with sustained effort: the deal-world's "
        "100B-H100e-year safety compute or its domestic equivalent turns "
        "the problem into engineering.",
  "A4": "Never truly tested: capability stays below the threshold where "
        "alignment failure is catastrophic. The question transfers to the "
        "2040s and beyond.",
  "C1": "No coordination: labs race, states posture, and safety investment "
        "is whatever competition permits (~1% in the AI-2040 scoring). The "
        "modal world in today's record.",
  "C2": "Securitization: Washington treats frontier AI as a national "
        "program — clearances, export lockdown, distillation deterrence, "
        "the four-fronts playbook. A 12-24 month lead becomes policy.",
  "C3": "The verified deal: US-CN transparency, mutual compute restraint, "
        "a pause at expert level 2035-2040, then joint ascent. The authors "
        "themselves give it 3-15% — priced accordingly.",
  "C4": "Fragmented blocs: no global deal, but overlapping regional "
        "regimes — the EU acquis, state patchworks, export walls. "
        "Compliance becomes the industry's second product.",
  "C5": "The moratorium: development halts below the researcher line. "
        "Scored and rejected by the AI-2040 authors as unstable and "
        "unverifiable at current politics; kept on the table at 1-2%.",
  "D1": "The displacement shock: white-collar automation outruns "
        "reabsorption; the Citrini spiral (layoffs → opex AI → demand "
        "contraction) becomes the macro story.",
  "D2": "Uneven diffusion — the wiki's sector pages' actual shape: coding "
        "and content first, healthcare and law gated by liability, "
        "physical work last. Winners and losers by sector, not en masse.",
  "D3": "Slow absorption: integration friction, liability, and "
        "organizational inertia keep AI's labor impact inside historical "
        "automation rates for years.",
  "S1": "Concentration: compute pools in a few national champions and "
        "sovereign clusters; Taiwan stays the single point of failure the "
        "system argues about.",
  "S2": "Diversified build-out: the capex wave lands widely — sovereign "
        "clouds, second-tier hubs, the Gulf — and no single chokepoint "
        "dominates by 2030.",
  "S3": "Constrained supply: export controls bite, energy and permitting "
        "bind, and compute scarcity itself shapes the capability path.",
  "P1": "Backlash wins elections: data-center revolts, displacement "
        "anger and safety fears converge into governing coalitions.",
  "P2": "Acquiescence-through-use: adoption normalizes faster than "
        "opposition organizes; AI becomes infrastructure politics.",
  "P3": "Fracture: publics split within countries — the Europe-2031 "
        "pattern — and AI politics cuts across old coalitions without "
        "resolving.",
  "E1": "The boom holds: revenue growth validates the capex; the "
        "build-out continues on trend.",
  "E2": "The correction that doesn't kill: valuations reset hard, some "
        "credit fails, but the physical build-out survives — the "
        "railway-mania precedent the bubble literature leans on.",
  "E3": "Capex-led hard deflation: the spending wave breaks before the "
        "revenue arrives; build-out stalls for years.",
  "E4": "Demand-led crisis: displacement undercuts the consumer economy "
        "the AI revenue depends on — the 2028-memo spiral, financial "
        "contagion included.",
}

# Conditional explanations ("how they affect each other") — one entry per
# (child, parent-position) family, rendered in axis cards.
CONDITIONAL_STORIES = {
  ("A", "T4"): "No superintelligence in the window means alignment is never "
               "truly tested — A4 becomes the default outcome of T4.",
  ("A", "T1"): "Explosive tempo compresses oversight: failure modes (A1) "
               "and near-misses (A2) both become likelier because there is "
               "less time to check anything.",
  ("C", "T1"): "A deal needs a window; explosive tempo closes it. "
               "Securitization (C2) thrives on the same urgency.",
  ("C", "T4"): "Without an emergency, securitization loses its argument and "
               "regulation fragments regionally (C4).",
  ("C", "A1"): "A world already losing control quietly is a world that "
               "cannot verify a deal (C3 down).",
  ("S", "C2"): "National programs concentrate compute by design.",
  ("S", "C3"): "The transparency regime deliberately diversifies the "
               "frontier across dozens of audited companies.",
  ("S", "E3"): "A capex bust strands build-outs and makes compute scarce "
               "(S3) even without export walls.",
  ("S", "E4"): "A demand crisis chokes data-center financing the same way.",
  ("P", "D1"): "Displacement shock is the strongest known driver of "
               "populist backlash (P1).",
  ("P", "E4"): "A visible AI-attributed recession radicalizes the politics "
               "further.",
  ("E", "T4"): "If capability disappoints, the boom thesis (E1) weakens "
               "and hard deflation (E3) strengthens.",
  ("E", "D1"): "The Citrini mechanism: the displacement shock is what "
               "turns a market correction into a demand crisis (E4).",
  ("E", "D3"): "Slow diffusion starves the spiral — E4 nearly requires a "
               "labor shock to ignite.",
}

REGISTRY = {
  "version": REGISTRY_VERSION,
  "axes": [
    {"key": "T", "name": "Capability tempo",
     "desc": "How fast frontier capability climbs the milestone ladder — "
             "the master variable every other axis conditions on. The "
             "positions span the literature: AI 2027's months, the "
             "Situational-Awareness decade, the gradual road, and the "
             "Normal-Technology null.",
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
     "desc": "Whether humans keep meaningful control as capability passes "
             "through the danger band — failure undetected, near-miss "
             "managed, tractable with effort, or never tested in the "
             "window. Tempo decides how much of this axis gets played.",
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
     "desc": "What the states do about it: race, securitize, deal, "
             "fragment, or halt — the AI-2040 plan family as live "
             "positions. This axis owns the biggest policy forks (the "
             "2029-32 deal window, the moratorium tail) and drives compute "
             "concentration, law velocity, and the pause shelf.",
     "cites": ["analysis/coordinated-slowdown-proposals",
               "analysis/eu-vs-us-ai-regulation", "concepts/compute-governance"],
     "positions": [
       ("C1", "none / race", 0.41, ["analysis/us-china-ai-competition"]),
       ("C2", "US securitization", 0.265,
        ["sources/aschenbrenner-situational-awareness",
         "sources/anthropic-2028-ai-leadership"]),
       # C3 prior ~0.09 independently cross-checked: the AI 2040 authors'
       # own implementation odds run 3-15% (median ~5-8%) —
       # ai-2040.com/supplements/comparing-possible-plans
       ("C3", "US-CN transparency deal", 0.09, ["sources/ai-2040-plan-a"]),
       ("C4", "fragmented blocs", 0.22, ["analysis/eu-vs-us-ai-regulation"]),
       ("C5", "moratorium / shutdown", 0.015,
        ["sources/ai-2040-plan-a"]),          # their Plan S, scored & rejected
     ],
     "subaxes": [
       {"key": "C.us-cn", "name": "US-China axis",
        "cites": ["analysis/us-china-ai-competition",
                  "concepts/export-controls-ai"]},
       {"key": "C.domestic", "name": "US domestic preemption vs patchwork",
        "cites": ["legislation/", "concepts/ai-preemption"]},
     ]},
    {"key": "D", "name": "Diffusion & labor",
     "desc": "How fast capability becomes deployment, and what it does to "
             "work — shock, uneven-by-sector, or slow absorption. Grounded "
             "in all thirteen industry pages; the shock position is what "
             "arms the displacement-crisis economy (E4) and the backlash "
             "politics (P1).",
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
     "desc": "Where the physical substrate lands and who controls it — "
             "concentration with a Taiwan flashpoint, diversified "
             "build-out, or constraint by controls and energy. Feeds the "
             "World view's geography and the climate coupling.",
     "cites": ["concepts/export-controls-ai", "concepts/compute-governance"],
     "positions": [
       ("S1", "concentration + flashpoint", 0.33,
        ["analysis/us-china-ai-competition"]),
       ("S2", "diversified build-out", 0.41, ["concepts/compute-governance"]),
       ("S3", "constrained (controls + energy)", 0.26,
        ["concepts/export-controls-ai"]),
     ]},
    {"key": "P", "name": "Public response",
     "desc": "What publics do as it arrives — organized backlash, "
             "acquiescence through use, or durable fracture. Drives "
             "approval, election realignments, siting revolts, and the "
             "political room every other axis has to work in.",
     "cites": ["concepts/ai-backlash", "analysis/companion-chatbot-harms"],
     "positions": [
       ("P1", "populist backlash", 0.26, ["concepts/ai-backlash"]),
       ("P2", "adoption/acquiescence", 0.31, ["concepts/ai-diffusion"]),
       ("P3", "polarized-fractured", 0.43, ["sources/europe-2031"]),
     ]},
    {"key": "E", "name": "Economy",
     "desc": "How the money side breaks — boom sustained, correction that "
             "spares the build-out, capex-led hard deflation, or the "
             "displacement-led demand crisis. The axis exists because the "
             "record genuinely disagrees; two distinct failure modes are "
             "kept apart on purpose.",
     "cites": ["concepts/ai-bubble-debate", "analysis/ai-bubble-vs-buildout"],
     "positions": [
       ("E1", "boom sustained", 0.28, ["analysis/ai-bubble-vs-buildout"]),
       ("E2", "bubble corrects, build-out survives", 0.45,
        ["concepts/ai-bubble-debate"]),
       ("E3", "deflates hard (capex-led)", 0.19,
        ["concepts/ai-bubble-debate"]),
       # the Citrini "intelligence displacement spiral": a demand-side
       # crisis originating in labor, not capex — distinct failure mode
       ("E4", "displacement-led demand crisis", 0.08,
        ["sources/2028-global-intelligence-crisis",
         "concepts/ai-labor-disruption"]),
     ]},
  ],
  # Conditionals: child axis → {parent-position: multiplicative tilts on the
  # child's positions}. Applied in axis order (acyclic by construction).
  # Each entry cites the mechanism it encodes.
  "conditionals": {
    # A-given-C tilts encode the AI 2040 comparison table's p(alignment)
    # spread — 72% under the deal's 100B-H100e-yr safety compute vs 25%
    # racing (ai-2040.com/supplements/comparing-possible-plans; cited on
    # sources/ai-2040-plan-a until the supplement is ingested)
    "A": {"T4": {"A4": 3.0, "A1": 0.2},          # no SC window → untested
          "T1": {"A4": 0.1, "A1": 2.2, "A2": 1.6}},
    "C": {"T1": {"C3": 0.4, "C2": 1.5},          # explosive tempo squeezes
          "T4": {"C2": 0.5, "C4": 1.6},          #   the deal window
          "A1": {"C3": 0.5}},
    "S": {"C2": {"S1": 1.8}, "C3": {"S2": 1.7},
          "E3": {"S3": 1.6}, "E4": {"S3": 1.4}},  # demand crunch constrains
    "P": {"D1": {"P1": 1.9}, "E4": {"P1": 1.7}},  # shock+crisis feed backlash
    "E": {"T4": {"E3": 1.5, "E1": 0.6},
          "D1": {"E4": 2.6},                      # the spiral needs the shock
          "D3": {"E4": 0.3}},
  },
  # position-conditioned A-tilts applied AFTER C is drawn would need a
  # reordering; instead the same evidence enters as A-priors' provenance and
  # the takeoff-length cross-check in worldlines (C3 pause ≈ their 6-year
  # takeoff; race lines ≈ their 1.0-1.1 years) — recorded, not double-counted.
  "changelog": [
    {"version": "r0-2026-07-31", "date": "2026-07-31",
     "change": "seed registry: 7 axes, 24 positions, 3 sub-axes, "
               "5 conditional families",
     "approved": "August (design of record, rev 3)"},
    {"version": "r1-2026-08-03", "date": "2026-08-03",
     "change": "evidence layer r1: structured matcher (section aliases, "
               "word-boundary terms, text_all/text_none, min_sources); "
               "ev-state-law-enacted given the content gate it never had; "
               "15 MAINLINE rules added at the `minor` tier — the tier the "
               "seed methodology defined and no rule used, which is why the "
               "forecast never moved on ordinary evidence. All 13 canonical "
               "sections now watched, most from both directions.",
     "approved": "August (2026-08-03: 'can we please fix all of the issues "
                 "flagged above') — morning-4 report §8"},
    {"version": REGISTRY_VERSION, "date": "2026-08-06",
     "change": "evidence layer r2 — the novelty repair. (1) Novelty decays "
               "toward a FLOOR (0.15) instead of to zero, so a class that "
               "keeps firing stays audible; the cumulative bound the design "
               "asked for now comes from soft_squash and sqrt aggregation, "
               "which bound axis drift rather than the world's event rate. "
               "(2) k is recency-WEIGHTED with a 7-day half-life, not a "
               "count inside a 30-day box, so a drought-then-return carries "
               "weight and there is no cliff. (3) k counts INCIDENTS, not "
               "reports: nightly_update resolves reports into developments, "
               "so four digests carrying one signing are one incident with "
               "several sources while three unrelated funding rounds are "
               "three incidents, each at equal weight. (4) classify() ranks "
               "by SPECIFICITY instead of taking the first list entry, and "
               "records `contested` when a matching rule disagrees, damping "
               "rather than silently picking. (5) Vocabulary repairs, each "
               "measured against the whole trunk: ev-compute-buildout could "
               "not read a chip fab and read six moratoria as build-out; "
               "ev-safety-incident was written in the vocabulary of "
               "alignment papers and missed every incident the record "
               "reported; ev-capital-commitment's `invest*` reached "
               "INVESTIGATION.",
     "approved": "August (2026-08-06: 'give repeat_k a floor and fix the "
                 "decay window … teach the difference between multiple "
                 "reports of one event and three unrelated events of one "
                 "kind') — morning-7 report §5"},
  ],
}

# ---------------------------------------------------------------------------
# The matcher (r1). Matching used to be naive substring containment against a
# single exact section string, which failed in three separate ways at once:
#   1. "correction" matched inside "corrections"/"correctional"; no term could
#      be anchored. Terms are now word-boundary-anchored at the START only, so
#      deliberate stems ("retaliat") still catch "retaliation/retaliatory"
#      while mid-word collisions stop.
#   2. The wiki's section names are not stable — the trunk holds "AI Markets",
#      "State Legislation & Regulation", "International Governance" and six
#      more one-off variants. An exact-string section gate silently skips them.
#      SECTION_ALIASES folds the variants onto the 13 canonical sections.
#      THIS IS MATCHING-ONLY: the territory taxonomy in emit.py is untouched.
#   3. A rule could only ever say "one of these strings appears". Rules can now
#      require every term (text_all), forbid terms (text_none), accept several
#      sections (section_any) or kinds (kind_any), and demand corroboration
#      (min_sources) — which is what lets a rule be specific instead of either
#      unfireable or content-blind.
# ---------------------------------------------------------------------------

SECTION_ALIASES = {
    "U.S. State AI Legislation & Litigation": "U.S. State AI Legislation",
    "State Legislation & Regulation": "U.S. State AI Legislation",
    "AI Markets": "AI Industry & Markets",
    "International Governance": "International AI Regulation",
    "International AI Regulation & Geopolitics": "International AI Regulation",
    "AI Adoption & Biometric Identity": "AI Adoption by Industry",
    "AI Safety, Liability & Security": "AI Safety, Alignment & Interpretability",
    "U.S. Federal Policy & Geopolitics": "Federal AI Policy & Agency Action",
    "Social Media Governance": "Labor, Society & Democratic Institutions",
}


def canon_section(s):
    """Fold a wiki section name onto its canonical form. Matching only."""
    s = " ".join((s or "").split())
    return SECTION_ALIASES.get(s, s)


def _compile(patterns):
    """Terms are WHOLE WORDS by default; a trailing `*` marks a deliberate
    stem. So "correction" no longer hides inside "correctional", while
    "retaliat*" still reaches retaliation/retaliatory. Interior spaces
    tolerate hyphens and line-wrapped whitespace, so one term covers both
    "red team" and "red-team"."""
    out = []
    for p in patterns:
        stem = p.endswith("*")
        body = r"[\s\-]+".join(re.escape(w) for w in p[:-1 if stem else None]
                               .lower().split())
        out.append(re.compile(r"\b" + body + ("" if stem else r"\b")))
    return out


def match_event(rule, ev):
    """Structured match of one event against one rule. Pure; no side effects
    beyond memoising compiled patterns onto the rule."""
    m = rule["match"]
    want = m.get("section_any") or (
        [m["section"]] if "section" in m else None)
    if want is not None and canon_section(ev.get("section")) not in want:
        return False
    kinds = m.get("kind_any") or ([m["kind"]] if "kind" in m else None)
    if kinds is not None and (ev.get("date") or {}).get("kind") not in kinds:
        return False
    if len(ev.get("urls") or []) < m.get("min_sources", 0):
        return False
    # the trunk already marks follow-up items (`update: true`, 131 of 1894).
    # A rule that counts first occurrences says so rather than re-counting
    # the same development every time the wiki revisits it.
    if "update" in m and bool(ev.get("update")) != m["update"]:
        return False
    txt = " ".join((ev.get("text") or "").lower().split())
    cache = rule.setdefault("_re", {})
    for key, mode in (("text_any", "any"), ("text_all", "all"),
                      ("text_none", "none")):
        pats = m.get(key)
        if not pats:
            continue
        if key not in cache:
            cache[key] = _compile(pats)
        hits = [p.search(txt) is not None for p in cache[key]]
        if mode == "any" and not any(hits):
            return False
        if mode == "all" and not all(hits):
            return False
        if mode == "none" and any(hits):
            return False
    return True


def rule_specificity(rule, ev):
    """How much of this event a rule actually accounts for.

    r1 matched by walking EVIDENCE_RULES and taking the first hit, so "most
    specific" meant "earliest in the list". On 2026-08-05 that read a Texas
    data-centre MORATORIUM as evidence for build-out, because
    ev-compute-buildout sits at index 13 and ev-compute-constraint at 14.
    Every rule ever shadowed lost to a neighbour, which is the signature of
    ordering rather than of judgment.

    Score = the constraints the rule actually had to satisfy. A rule gated on
    a section and matching four of its terms has explained more of the event
    than one gated on nothing that matched a single generic verb."""
    m = rule["match"]
    txt = " ".join((ev.get("text") or "").lower().split())
    score = 0.0
    if m.get("section_any") or m.get("section"):
        score += 2.0
    if m.get("kind_any") or m.get("kind"):
        score += 1.0
    if "update" in m:
        score += 1.0
    score += min(2, m.get("min_sources", 0))
    cache = rule.setdefault("_re", {})
    for key, weight in (("text_any", 1.0), ("text_all", 1.5)):
        pats = m.get(key)
        if not pats:
            continue
        if key not in cache:
            cache[key] = _compile(pats)
        score += weight * sum(1 for p in cache[key] if p.search(txt))
    if m.get("text_none"):
        score += 0.5          # a rule that also had to NOT see something
    return score


def opposes(a, b):
    """True when two rules push the SAME position of an axis in opposite
    directions — a genuine contradiction about what the event means.

    Two rules that both raise T3 while one also raises T2 are not in
    conflict; they are two compatible readings of one release. Measured on
    the trunk, a looser test flagged every frontier release as contested
    against the benchmark rule, which would have damped agreement."""
    for (ax1, pos1), d1 in a["nudge"].items():
        for (ax2, pos2), d2 in b["nudge"].items():
            if ax1 == ax2 and pos1 == pos2 and d1 * d2 < 0:
                return True
    return False


def classify(ev, rules=None):
    """Pick the rule that best explains one event.

    Returns (rule, contested_ids, all_matching_ids). `contested_ids` are the
    other matching rules that pull the winner's axes the other way — the
    application is damped and the dispute is recorded, rather than being
    resolved silently by whichever rule happens to be listed first."""
    rules = EVIDENCE_RULES if rules is None else rules
    hits = [r for r in rules if match_event(r, ev)]
    if not hits:
        return None, [], []
    idx = {id(r): i for i, r in enumerate(rules)}
    best = max(hits, key=lambda r: (rule_specificity(r, ev), -idx[id(r)]))
    contested = [r["id"] for r in hits if r is not best and opposes(best, r)]
    return best, contested, [r["id"] for r in hits]


# Evidence rules r1: development-class → bounded weight nudges (per source).
# Applied by the nightly chain; every application logged with its driver.
# nudge values are DIRECTIONS (sign + relative share); magnitude comes from
# the impact class via impact_magnitude().
#
# TWO LAYERS, and the second one is new:
#
#   TAIL rules (notable/major/structural) fire on the dramatic, rare thing —
#   a treaty, a demonstrated autonomous R&D run, a hard correction. These are
#   the eleven seed rules. They match ~3.6% of the trunk by design.
#
#   MAINLINE rules (`minor`, 0.003) fire on the ordinary drumbeat: a model
#   ships, a datacenter breaks ground, a safety paper lands, a regulator
#   opens a file. The seed methodology DEFINED this tier ("routine reporting,
#   incremental funding") and then no rule ever used it — which is the whole
#   reason the forecast could not move on an ordinary day. It is safe to watch
#   the drumbeat because novelty decay is already 0.5**k over a 30-day window:
#   a rule that fires daily contributes 0.003, then 0.0015, then 0.00075 …
#   summing to under 0.006 no matter how long the drumbeat runs. So a STEADY
#   rate moves almost nothing and only a BURST (many corroborated sources at
#   once) or a DROUGHT-then-return carries weight. The decay is the
#   rate-deviation mechanism; it was already built, just never exercised.
#
# Wherever a section can speak both ways, it gets a rule in each direction, so
# the mainline layer cannot drift monotonically: buildout vs constraint,
# safety progress vs safety incident, capital in vs capital out.
EVIDENCE_RULES = [
  # --- tail rules (seed r0, gates repaired) -------------------------------
  {"id": "ev-state-law-enacted", "impact": "notable",
   # r1: this rule had NO text gate at all — section + kind alone, so every
   # event-kind item in the section fired a "state law enacted" nudge
   # regardless of content (52 candidates across the trunk). It is now gated
   # on enactment language. The 2026-08-03 CPPA compliance-audit item, which
   # would have fired the ungated rule had its date carried kind `event`, is
   # correctly excluded: opening an audit under an existing statute is not an
   # enactment. Illinois HB 5511 (Pritzker signing, 2026-07-31) still fires.
   "match": {"section": "U.S. State AI Legislation", "kind": "event",
             "text_any": ["signed into law", "signed house bill",
                          "signed senate bill", "signed hb", "signed sb",
                          "signed the", "enacted", "was enacted",
                          "became law", "takes effect", "took effect",
                          "passed the legislature", "overrode"]},
   "nudge": {("C", "C4"): +2, ("C", "C3"): -1},
   "cites": ["analysis/eu-vs-us-ai-regulation"]},
  {"id": "ev-export-retaliation", "impact": "notable",
   "match": {"text_any": ["retaliat*", "export control*", "MOFCOM"],
             "section": "National Security & Geopolitics"},
   "nudge": {("C", "C1"): +2, ("S", "S3"): +2, ("C", "C3"): -1},
   "cites": ["concepts/export-controls-ai"]},
  {"id": "ev-frontier-release-gov-coordinated", "impact": "notable",
   "match": {"text_any": ["government-coordinated", "limited preview"],
             "section": "Frontier Models & Capabilities"},
   "nudge": {("C", "C2"): +2, ("T", "T2"): +1},
   "cites": ["models/gpt-56"]},
  {"id": "ev-big-correction", "impact": "major",
   "match": {"text_any": ["writedown*", "correction", "bubble bursts"],
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
  {"id": "ev-unemployment-spike", "impact": "major",
   "match": {"text_any": ["unemployment rose", "jobless rate", "layoffs "
             "exceeded", "white-collar layoffs"],
             "section": "Labor, Society & Democratic Institutions"},
   "nudge": {("D", "D1"): +2, ("E", "E4"): +2, ("D", "D3"): -1},
   "cites": ["sources/2028-global-intelligence-crisis",
             "concepts/ai-labor-disruption"]},
  {"id": "ev-inference-tax-proposal", "impact": "notable",
   "match": {"text_any": ["compute tax", "inference tax", "AI dividend",
             "sovereign wealth fund"],
             "section": "Federal AI Policy & Agency Action"},
   "nudge": {("D", "D1"): +1, ("P", "P1"): +1},
   "cites": ["sources/2028-global-intelligence-crisis"]},
  {"id": "ev-distillation-attack", "impact": "notable",
   "match": {"text_any": ["distillation attack", "model extraction",
             "distilled from"],
             "section": "National Security & Geopolitics"},
   "nudge": {("C", "C2"): +2, ("S", "S3"): +1},
   "cites": ["sources/anthropic-2028-ai-leadership"]},
  {"id": "ev-sabotage-ops", "impact": "major",
   "match": {"text_any": ["cyberattack on datacenter", "sabotage",
             "cyber operation against"],
             "section": "National Security & Geopolitics"},
   "nudge": {("C", "C2"): +2, ("C", "C3"): -2, ("S", "S1"): +1},
   "cites": ["sources/ai-2040-plan-a"]},
  {"id": "ev-moratorium-movement", "impact": "notable",
   "match": {"text_any": ["moratorium", "halt AI development", "pause all"],
             "section": "International AI Regulation"},
   "nudge": {("C", "C5"): +2, ("P", "P1"): +1},
   "cites": ["sources/ai-2040-plan-a", "concepts/ai-backlash"]},

  # --- mainline rules (r1, `minor` tier) ----------------------------------
  # T — capability tempo. An ordinary release is evidence that capability
  # keeps compounding, NOT that it is accelerating; it therefore supports the
  # gradual road and cuts against the no-SC-in-window null, and leaves the
  # explosive positions to the tail rules that actually detect discontinuity.
  {"id": "ev-frontier-release", "impact": "minor",
   # measured at 63.9% of its section before the gates below: nearly every
   # item in Frontier Models mentions a release somewhere in its prose. The
   # rule is meant to register a model ACTUALLY SHIPPING, so it now excludes
   # follow-up items (the trunk's own `update` flag) and forward-looking
   # announcements, and requires two sources.
   "match": {"section": "Frontier Models & Capabilities", "update": False,
             "min_sources": 2,
             "text_any": ["releas*", "launch*", "unveil*", "generally "
                          "available", "open-sourc*", "open-weight",
                          "now available", "shipped", "in preview"],
             "text_none": ["plans to", "expected to", "is preparing",
                           "will release", "reportedly", "rumored",
                           "tentatively named"]},
   "nudge": {("T", "T3"): +2, ("T", "T4"): -1},
   "cites": ["concepts/scaling-laws", "concepts/agi-timelines"]},
  {"id": "ev-benchmark-progress", "impact": "minor",
   "match": {"section_any": ["Frontier Models & Capabilities",
                             "Agentic AI & Coding"],
             "text_any": ["benchmark*", "state of the art", "swe-bench",
                          "outperform*", "surpass*", "record score",
                          "frontier of"],
             "text_none": ["failed to", "no better than", "plateau*"]},
   "nudge": {("T", "T2"): +1, ("T", "T3"): +1, ("T", "T4"): -1},
   "cites": ["concepts/agi-timelines", "sources/ai-2027"]},

  # S — compute & supply, watched from both sides so buildout news and
  # constraint news cannot both push the same way.
  {"id": "ev-compute-buildout", "impact": "minor",
   # r2 (2026-08-06): this rule is written in the vocabulary of data centres
   # and had almost nothing to say about CHIPS. SpaceX/Tesla's $16.8bn
   # Terafab complex, filed in this very section, did not match it and fell
   # through to ev-capital-commitment — moving the economy axis instead of
   # compute & supply, at an eighth of the weight. Verified: "fab" is a whole
   # word and "Terafab" is not it, and the obvious repair fails too, because
   # \bfab\w* still needs a word boundary that "Terafab" does not have. The
   # gap was never the stem; it was that the record says "manufacturing".
   # text_none gains restriction framings so a moratorium item cannot read as
   # build-out even before classify() sees the contest.
   "match": {"section": "Compute, Chips & Infrastructure",
             "text_any": ["datacenter*", "data center*", "gigawatt*",
                          "megawatt*", "fab", "fabs", "fabrication",
                          "foundry", "foundries", "capacity expansion",
                          "broke ground", "capex", "supply agreement",
                          # ACT-phrases, not the bare stem. "manufactur*"
                          # was tried and rejected on measurement: it fired
                          # on "DRAM manufacturing" in a demand forecast, on
                          # "manufacturability" in a delay notice, on "China
                          # manufactures 60%" in an analysis, and on "pilot
                          # manufacturing" in a Series B. The rule wants the
                          # act of adding capacity, not the word.
                          "chip manufacturing", "manufacturing complex",
                          "manufacturing capacity", "manufacturing plant*",
                          "will manufacture", "begin production",
                          "begins production", "began production",
                          "into production", "chip plant*", "wafer fab*",
                          "semiconductor plant*", "in-house chip*",
                          "in-house ai chip*", "custom ai chip*",
                          "custom accelerator*", "assembly line*"],
             # two families of exclusion, both measured on the trunk:
             # RESTRICTIONS (a moratorium is not a build-out — this is the
             # 2026-08-03 Texas class, six more items of which were being
             # read the same wrong way), and COMMENTARY (a market-size
             # estimate, a delay notice or a strike is talk or trouble about
             # capacity, not capacity being added).
             "text_none": ["shortage*", "export control*", "denied",
                           "halted", "moratorium", "moratoria",
                           "rationing", "curtailment*",
                           "strike", "walkout", "disrupting",
                           "addressable market", "delayed",
                           "manufacturability"]},
   "nudge": {("S", "S2"): +2, ("S", "S3"): -1},
   "cites": ["concepts/compute-governance", "analysis/ai-bubble-vs-buildout"]},
  {"id": "ev-compute-constraint", "impact": "minor",
   # r2 (2026-08-06): "moratorium on datacenter*" was spelled as one word and
   # the record writes two. Verified on the 08-03 Texas item: the one-word
   # spelling matched nothing, the two-word spelling would have. It escaped
   # notice only because "interconnection queue" happened to carry the match.
   # The term is now just the restriction itself — the section gate already
   # establishes that the subject is compute.
   "match": {"section_any": ["Compute, Chips & Infrastructure",
                             "National Security & Geopolitics"],
             "text_any": ["shortage*", "export control*", "licence denied",
                          "license denied", "grid constraint*", "power "
                          "constraint*", "interconnection queue",
                          "moratorium", "moratoria", "rationing",
                          "permitting pause", "halted construction",
                          "curtailment*", "denied interconnection"]},
   "nudge": {("S", "S3"): +2, ("S", "S2"): -1},
   "cites": ["concepts/export-controls-ai", "concepts/compute-governance"]},

  # A — alignment. Research output is weak evidence the problem is tractable
  # and that failures get SEEN; a demonstrated failure mode is weak evidence
  # the danger band is real and partly unmonitored.
  {"id": "ev-safety-research", "impact": "minor",
   "match": {"section_any": ["AI Safety, Alignment & Interpretability",
                             "AI Standards & Safety Frameworks"],
             "text_any": ["published", "paper*", "interpretability",
                          "evaluation*", "eval suite", "red team",
                          "safety case", "model card"],
             "text_none": ["exfiltrat*", "jailbreak*", "scheming"]},
   "nudge": {("A", "A3"): +2, ("A", "A1"): -1},
   "cites": ["analysis/interpretability-and-safety",
             "concepts/responsible-scaling-policy"]},
  {"id": "ev-safety-incident", "impact": "minor",
   # r2 (2026-08-06): every term here was the vocabulary of ALIGNMENT PAPERS,
   # and the record reports incidents in the vocabulary of NEWS. On 08-05 a
   # Meta model "hacked another company during cybersecurity testing" and
   # "exploited a security vulnerability in a third-party service"; the rule
   # that exists for exactly that event matched none of it and the item went
   # to residue with no competitor present. The second block is the incident
   # vocabulary; the section gate keeps ordinary cyber news out.
   "match": {"section_any": ["AI Safety, Alignment & Interpretability",
                             "Agentic AI & Coding"],
             "text_any": ["jailbreak*", "exfiltrat*", "deceptive", "scheming",
                          "misaligned", "reward hacking", "autonomous "
                          "replication", "worm", "worms", "prompt injection",
                          "sandbagging",
                          "hacked", "hacking", "exploited",
                          "security vulnerabilit*", "unauthorized access",
                          "unintended access", "escaped its", "self-exfil*",
                          "took control", "acted without authorization",
                          "unsanctioned"]},
   "nudge": {("A", "A1"): +1, ("A", "A2"): +2, ("A", "A4"): -1},
   "cites": ["sources/ai-2027", "analysis/interpretability-and-safety"]},

  # C — coordination. Four mainline readings, pulling apart rather than
  # together: courts and regulators acting without a federal statute is the
  # fragmented road; a preemption push is the argument against it.
  {"id": "ev-enforcement-action", "impact": "minor",
   "match": {"section_any": ["AI Litigation, Liability & Enforcement",
                             "U.S. State AI Legislation"],
             "text_any": ["lawsuit*", "sued", "settlement*", "ruling*",
                          "injunction*", "consent decree*", "penalt*",
                          "fined", "investigation*", "subpoena*",
                          "compliance audit*", "cease and desist",
                          "class action"]},
   "nudge": {("C", "C4"): +2, ("C", "C1"): -1},
   "cites": ["analysis/eu-vs-us-ai-regulation", "concepts/ai-preemption"]},
  {"id": "ev-federal-preemption-push", "impact": "minor",
   "match": {"section": "Federal AI Policy & Agency Action",
             "text_any": ["national standard*", "preempt*",
                          "federal framework", "single national",
                          "patchwork", "uniform federal"]},
   "nudge": {("C", "C2"): +2, ("C", "C4"): -2},
   "cites": ["concepts/ai-preemption", "analysis/eu-vs-us-ai-regulation"]},
  {"id": "ev-regulatory-implementation", "impact": "minor",
   # the EU AI Act Art. 50 enforcement of 2026-08-02 — three corroborating
   # sources — passed through the r0 rule set untouched. It fires here.
   "match": {"section": "International AI Regulation",
             "text_any": ["enforceable", "takes effect", "took effect",
                          "obligation*", "guidance", "code of practice",
                          "implementing act*", "transparency requirement*",
                          "came into force", "deadline*"]},
   "nudge": {("C", "C4"): +2, ("C", "C3"): -1},
   "cites": ["analysis/eu-vs-us-ai-regulation", "sources/europe-2031"]},
  {"id": "ev-state-bill-activity", "impact": "minor",
   "match": {"section": "U.S. State AI Legislation",
             "text_any": ["introduced", "advanced", "committee", "passed the "
                          "house", "passed the senate", "vetoed", "filed",
                          "ballot measure*"],
             "text_none": ["signed into law", "enacted"]},
   "nudge": {("C", "C4"): +2, ("C", "C1"): -1},
   "cites": ["analysis/eu-vs-us-ai-regulation", "concepts/ai-preemption"]},
  {"id": "ev-natsec-posture", "impact": "minor",
   "match": {"section": "National Security & Geopolitics",
             "text_any": ["allied", "alliance*", "chip control*", "entity "
                          "list", "screening", "procurement", "defense "
                          "contract*", "classified", "security review*"]},
   "nudge": {("C", "C2"): +2, ("C", "C3"): -1},
   "cites": ["analysis/us-china-ai-competition", "concepts/export-controls-ai"]},
  {"id": "ev-standards-published", "impact": "minor",
   "match": {"section": "AI Standards & Safety Frameworks",
             "text_any": ["framework*", "standard*", "nist", "iso",
                          "guideline*", "commitment*", "voluntary",
                          "assurance"]},
   "nudge": {("C", "C4"): +1, ("C", "C5"): -1, ("A", "A3"): +1},
   "cites": ["concepts/responsible-scaling-policy",
             "analysis/eu-vs-us-ai-regulation"]},

  # D — diffusion & labor. Deployment reporting is the uneven-by-sector road
  # by construction: it is sector-by-sector news, neither a shock nor a
  # standstill. The shock reading stays with the major-tier tail rule.
  {"id": "ev-agentic-deployment", "impact": "minor",
   "match": {"section": "Agentic AI & Coding",
             "text_any": ["deploy*", "in production", "rollout*", "agentic",
                          "autonomous workflow*", "coding assistant*",
                          "enterprise customer*", "adoption"]},
   "nudge": {("D", "D2"): +2, ("D", "D3"): -1},
   "cites": ["concepts/ai-diffusion",
             "concepts/professional-services-ai-adoption"]},
  {"id": "ev-enterprise-adoption", "impact": "minor",
   "match": {"section_any": ["AI Adoption by Industry",
                             "Labor, Society & Democratic Institutions"],
             "text_any": ["adoption", "rollout*", "pilot*", "deploy*",
                          "seats", "enterprise", "productivity",
                          "reskilling", "hiring", "job posting*"],
             "text_none": ["layoffs exceeded", "unemployment rose"]},
   "nudge": {("D", "D2"): +2, ("D", "D1"): -1, ("P", "P2"): +1},
   "cites": ["concepts/ai-diffusion",
             "concepts/ai-displacement-vs-augmentation"]},

  # E — economy. The mainline counterweight to ev-big-correction: capital
  # still arriving is evidence the boom has not broken yet.
  {"id": "ev-capital-commitment", "impact": "minor",
   "match": {"section_any": ["AI Industry & Markets",
                             "Compute, Chips & Infrastructure"],
             # r2 (2026-08-06): "invest*" was a stem and it reached
             # INVESTIGATION, INVESTIGATORS, INVESTIGATIVE. That is how a
             # Taiwanese prosecutor detaining an Nvidia employee over export
             # controls came to match the capital-commitment rule. This is
             # the most-fired rule in the set, so the term is now enumerated.
             "text_any": ["raised", "funding round*", "valuation*",
                          "invest", "invests", "invested", "investing",
                          "investment*", "investor*",
                          "commitment*", "backlog", "revenue run-rate",
                          "annualized revenue", "ipo"],
             "text_none": ["writedown*", "wrote down", "bubble bursts",
                           "impairment*"]},
   "nudge": {("E", "E1"): +2, ("E", "E3"): -1},
   "cites": ["analysis/ai-bubble-vs-buildout", "concepts/ai-bubble-debate"]},
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


def novelty(repeat_k):
    """Weight of the (k+1)-th incident of a class, decaying toward a floor.

    k is a real number: the recency-weighted count of PRIOR incidents of this
    class (see NOVELTY_HALFLIFE_DAYS), so it falls between nights as old
    incidents age out and rises as new ones land.

        k = 0  → 1.000    the class speaks for the first time in a while
        k = 1  → 0.575
        k = 2  → 0.363
        k = 4  → 0.203
        k → ∞  → 0.150    the steady-state rate of a class that always fires
    """
    return NOVELTY_FLOOR + (1.0 - NOVELTY_FLOOR) * (0.5 ** max(0.0, repeat_k))


def corroboration(sources=1):
    """Independent sources amplify, capped at ×1.5. `sources` is a count of
    distinct DOMAINS, not of URLs — four links to one newsroom are one
    source, and the r1 code counted them as four."""
    return 1.0 + 0.25 * min(2, max(0, sources - 1))


def impact_magnitude(rule, sources=1, repeat_k=0, spread=1.0):
    """Class base × corroboration × novelty × spread.

    `spread` divides one night's same-class incidents so that n distinct
    incidents together carry sqrt(n) times one incident's weight, and each
    carries an EQUAL share of it. Equal because the order of events inside a
    night is an artefact of the trunk's file order and must not decide which
    funding round counts and which does not; sqrt because n observations of
    one class are not n independent units of information."""
    base = IMPACT_CLASS[rule.get("impact", "notable")]
    return base * corroboration(sources) * novelty(repeat_k) * spread


def soft_squash(cum, delta, cap=WEEKLY_SOFT_CAP):
    """Damp the marginal effect on an axis that has already drifted `cum`
    this week — logistic taper past the soft cap, never a hard wall, so a
    structural event still lands."""
    if abs(cum) < cap:
        return delta
    over = (abs(cum) - cap) / cap
    return delta / (1.0 + 2.0 * over)


CONTESTED_DAMP = 0.5       # weight of an application the record disputes


def apply_evidence(reg, rule, log, sources=1, repeat_k=0, weekly_cum=None,
                   spread=1.0, contested=None, incident=None):
    """Apply one evidence rule under the tiered methodology. rule["nudge"]
    values are DIRECTIONS (+1/-1 scaled by their relative share); the
    magnitude comes from impact_magnitude. Every application logs its
    arithmetic — the delta is auditable end to end.

    `contested` is the list of rule ids that also matched this event and
    nudge an axis the OPPOSITE way. Standing rule 9 — say what is contested,
    in the data, as a field — so a disputed reading is damped and named
    rather than silently resolved by list order (which is how the 2026-08-05
    Texas moratorium came to be read as evidence FOR build-out).

    The log now separates `requested` (what the rule asked the registry for,
    before normalisation and before the grounding widener) from `applied`
    (what the registry actually moved). Those differ every night and until
    now only the first was recorded, so the panel showed a number the
    distribution never used."""
    weekly_cum = weekly_cum if weekly_cum is not None else {}
    contested = list(contested or [])
    mag = impact_magnitude(rule, sources, repeat_k, spread)
    if contested:
        mag *= CONTESTED_DAMP
    total_share = sum(abs(v) for v in rule["nudge"].values()) or 1.0
    applied, requested = {}, {}
    for (ax_key, pos), direction in rule["nudge"].items():
        d = mag * (direction / total_share) * len(rule["nudge"])
        requested[(ax_key, pos)] = d
        d = soft_squash(weekly_cum.get(ax_key, 0.0), d)
        a = axis(reg, ax_key)
        pri = {p[0]: p[2] for p in a["positions"]}
        pri[pos] = max(0.005, pri[pos] + d)
        pri = normalized(pri)
        a["positions"] = [(p[0], p[1], pri[p[0]], p[3])
                          for p in a["positions"]]
        applied[(ax_key, pos)] = d
        weekly_cum[ax_key] = weekly_cum.get(ax_key, 0.0) + abs(d)
    entry = {"rule": rule["id"],
             "impact_class": rule.get("impact", "notable"),
             "magnitude": round(mag, 7), "sources": sources,
             "repeat_k": round(repeat_k, 3), "spread": round(spread, 4),
             "requested": {"%s.%s" % k: round(v, 7)
                           for k, v in requested.items()},
             "applied": {"%s.%s" % k: round(v, 7)
                         for k, v in applied.items()},
             "cites": rule["cites"]}
    if contested:
        entry["contested"] = contested
    if incident:
        entry["incident"] = incident
    log.append(entry)
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


def apply_schema_log(reg, schema_log):
    """Re-apply auto-added sub-axes onto a freshly built registry.

    The weekly schema review appended its additions to the module-level
    REGISTRY inside the nightly_update process and recorded them in
    weights["schema_log"]. But every stage of the chain is a separate
    process, so the mutation died at exit and forecast_emit — which is what
    actually publishes `subaxes` — never saw it. The review logged growth it
    never performed. Rebuilding from the log makes the addition real, which
    is what "autonomy with attribution" was supposed to mean."""
    existing = {s["key"] for a in reg["axes"] for s in a.get("subaxes", [])}
    added = 0
    for entry in schema_log or []:
        sub = entry["subaxis"]
        if sub["key"] in existing:
            continue
        for a in reg["axes"]:
            if a["key"] == entry["axis"]:
                a.setdefault("subaxes", []).append(sub)
                existing.add(sub["key"])
                added += 1
                break
    return added


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
    # r2 novelty: repeats decay TOWARD A FLOOR, never to zero. The r1 test
    # asserted `repeat_k=2 < m_note/3`, which encoded the behaviour that made
    # the machine deaf — by k=7 an event was worth 0.8% of base, and on
    # 2026-08-06 three unrelated funding rounds were annihilated by it. What
    # must hold now is that repeats fall, that they fall monotonically, and
    # that they never fall past the floor.
    ks = [impact_magnitude({"impact": "notable"}, repeat_k=k)
          for k in (0, 1, 2, 4, 8, 40)]
    assert ks == sorted(ks, reverse=True), ks
    assert ks[1] < ks[0] * 0.7, "a repeat must cost something"
    assert ks[-1] >= m_note * NOVELTY_FLOOR * 0.999, "the floor must hold"
    assert ks[-1] > m_note * 0.10, "a recurring class must still speak"
    # and k is continuous, so a class recovers as its incidents age out
    assert (impact_magnitude({"impact": "notable"}, repeat_k=0.5)
            > impact_magnitude({"impact": "notable"}, repeat_k=2.0))
    # spread: n incidents of one class in one night carry sqrt(n) together,
    # and each carries the SAME weight — order inside a night must not decide
    # which funding round counts.
    one = impact_magnitude({"impact": "minor"}, spread=1.0)
    each = impact_magnitude({"impact": "minor"}, spread=(3 ** 0.5) / 3)
    assert abs(3 * each - one * (3 ** 0.5)) < 1e-12
    assert each < one and 3 * each > one
    # corroboration counts distinct publishers
    assert corroboration(4) == corroboration(3) == 1.5 and corroboration(1) == 1.0
    # specificity beats list order: the 2026-08-05 Texas item matched both
    # compute rules and lost to the earlier one. Now the contest is named.
    tex = {"section": "Compute, Chips & Infrastructure",
           "date": {"kind": "event", "iso": "2026-08-03"},
           "text": "Texas announced a moratorium on data center approvals, "
                   "directing the utility commission to audit the "
                   "interconnection queue", "urls": ["u1"]}
    r, contested, allm = classify(tex)
    assert r["id"] == "ev-compute-constraint", (r["id"], allm)
    assert "ev-compute-buildout" not in allm, allm
    # opposition is about the SAME position, not merely the same axis
    buildout = [x for x in EVIDENCE_RULES if x["id"] == "ev-compute-buildout"][0]
    constraint = [x for x in EVIDENCE_RULES
                  if x["id"] == "ev-compute-constraint"][0]
    release = [x for x in EVIDENCE_RULES if x["id"] == "ev-frontier-release"][0]
    bench = [x for x in EVIDENCE_RULES
             if x["id"] == "ev-benchmark-progress"][0]
    assert opposes(buildout, constraint)
    assert not opposes(release, bench), "two compatible readings of a release"
    # a contested application is damped and says so
    lg = []
    apply_evidence(reg, constraint, lg, contested=["ev-compute-buildout"])
    assert lg[-1]["contested"] == ["ev-compute-buildout"]
    assert lg[-1]["magnitude"] < impact_magnitude(constraint)
    assert "requested" in lg[-1] and "applied" in lg[-1]
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
    # version-agnostic: derive the expected bump from whatever the registry
    # is on now. A literal "r1-" here goes stale the moment the registry
    # legitimately grows — the same failure mode that broke the 07-31 chain.
    _n_before = int(reg["version"].split("-")[0][1:])
    add_axis(reg, {"key": "X", "name": "test axis", "cites": [],
                   "positions": [("X1", "a", 0.5, []), ("X2", "b", 0.5, [])]},
             approved_by="auto: schema review selftest")
    assert reg["version"].startswith("r%d-" % (_n_before + 1)), reg["version"]
    assert "schema review" in reg["changelog"][-1]["approved"]
    try:
        add_axis(reg, {"key": "Y", "name": "y", "cites": [],
                       "positions": [("Y1", "a", 1.0, [])]}, approved_by="")
        assert False, "unattributed addition must fail"
    except AssertionError as ex:
        assert "origin" in str(ex)

    # --- matcher (r1) ----------------------------------------------------
    def _ev(sec, text, kind="event", urls=1):
        return {"section": sec, "text": text,
                "date": {"kind": kind, "iso": "2026-08-03"},
                "urls": ["u%d" % i for i in range(urls)]}

    # word-boundary anchoring: the seed matcher fired "correction" inside
    # "correctional", which is the class of false positive that made every
    # text gate untrustworthy.
    corr = [r for r in EVIDENCE_RULES if r["id"] == "ev-big-correction"][0]
    assert match_event(corr, _ev("AI Industry & Markets",
                                 "A sharp correction hit AI equities."))
    assert not match_event(corr, _ev("AI Industry & Markets",
                                     "The correctional facility bought GPUs."))
    # stems still reach their inflections
    ret = [r for r in EVIDENCE_RULES if r["id"] == "ev-export-retaliation"][0]
    assert match_event(ret, _ev("National Security & Geopolitics",
                                "Beijing promised retaliatory measures."))
    # section aliases fold onto the canonical 13
    assert canon_section("AI Markets") == "AI Industry & Markets"
    assert canon_section("State Legislation & Regulation") == \
        "U.S. State AI Legislation"
    assert match_event(corr, _ev("AI Markets", "A correction is under way."))
    # ev-state-law-enacted: the gate it never had. An enactment fires; an
    # enforcement action under an existing statute does not.
    law = [r for r in EVIDENCE_RULES if r["id"] == "ev-state-law-enacted"][0]
    assert match_event(law, _ev(
        "U.S. State AI Legislation",
        "Illinois Gov. JB Pritzker signed House Bill 5511, the Children's "
        "Social Media Safety Act, on July 31, 2026."))
    assert not match_event(law, _ev(
        "U.S. State AI Legislation",
        "The California Privacy Protection Agency opened its first formal "
        "compliance audit targeting gig economy platforms."))
    # kind gate still holds
    assert not match_event(law, _ev(
        "U.S. State AI Legislation", "The governor signed the bill.",
        kind="published"))
    # text_none excludes; text_all requires; min_sources demands corroboration
    probe = {"id": "probe", "impact": "minor",
             "match": {"section": "AI Industry & Markets",
                       "text_all": ["revenue", "growth"],
                       "text_none": ["writedown"], "min_sources": 2},
             "nudge": {("E", "E1"): +1}, "cites": []}
    assert match_event(probe, _ev("AI Industry & Markets",
                                  "revenue growth continued", urls=2))
    assert not match_event(probe, _ev("AI Industry & Markets",
                                      "revenue growth continued", urls=1))
    assert not match_event(probe, _ev("AI Industry & Markets",
                                      "revenue only", urls=2))
    assert not match_event(probe, _ev("AI Industry & Markets",
                                      "revenue growth, then a writedown",
                                      urls=2))
    # every rule is well-formed and every mainline rule is `minor`
    keys = {a["key"] for a in REGISTRY["axes"]}
    for r in EVIDENCE_RULES:
        assert r["impact"] in IMPACT_CLASS, r["id"]
        assert r["cites"], r["id"]
        assert r["nudge"], r["id"]
        for (ax, pos) in r["nudge"]:
            assert ax in keys, (r["id"], ax)
            assert pos in {p[0] for p in axis(REGISTRY, ax)["positions"]}, \
                (r["id"], pos)
    # the `minor` tier is no longer empty — that emptiness was the defect
    assert any(r["impact"] == "minor" for r in EVIDENCE_RULES)
    return 9


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
