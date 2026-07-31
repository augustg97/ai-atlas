#!/usr/bin/env python3
"""worldlines.py — from a sampled world-line (axes.py) to a full trajectory:
capability path 2026→2100, per-layer quantitative tracks, and instantiated
narrative waypoints from the event-template library (near / mid / far field,
the far field carrying the strange futures at honest width).

Every parameter block cites its grounding. Deterministic per (world-line,
seed). stdlib only.

python3 worldlines.py runs selftests + a worked demonstration.
"""

from __future__ import annotations

import bisect
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import axes

Y0, Y1 = 2026, 2100
LADDER = ["none", "unreliable agent", "reliable agent", "superhuman coder",
          "superhuman AI researcher", "generally superintelligent",
          "wildly superintelligent"]

# ---------------------------------------------------------------------------
# Capability paths. Knot years per tempo for ladder indices 3..6, from the
# sources' own schedules: T1 ≈ AI 2027's months; T2 ≈ Plan A's counterfactual
# ("fully automated AI R&D by 2030") and Situational Awareness's decade;
# T3 ≈ the wiki-median gradual read (concepts/agi-timelines); T4 ≈ AI as
# Normal Technology (no superintelligence in window; index caps below 5).
# The 2026 anchor (2.6, approaching "superhuman coder") is the trunk's
# current frontier read from the wiki's model record.
# ---------------------------------------------------------------------------
TEMPO_KNOTS = {
    "T1": [(2026.6, 2.6), (2027.3, 3.0), (2028.0, 4.0), (2028.7, 5.0),
           (2029.5, 6.0)],
    "T2": [(2026.6, 2.6), (2029.0, 3.0), (2030.5, 4.0), (2032.5, 5.0),
           (2034.5, 6.0)],
    "T3": [(2026.6, 2.6), (2031.5, 3.0), (2034.5, 4.0), (2038.5, 5.0),
           (2043.0, 6.0)],
    "T4": [(2026.6, 2.6), (2034.0, 3.0), (2046.0, 3.8), (2070.0, 4.3),
           (2100.0, 4.6)],
}


def capability_path(wl):
    """Knots (year, index) after axis modifiers. A2 inserts a pause-and-
    reassess plateau at the researcher level; C3 holds Plan A's expert-level
    pause 2035→2040 then resumes; A1 truncates ascent at takeover (the
    index stays — the world changes owner, not capability)."""
    knots = list(TEMPO_KNOTS[wl["T"]])
    if wl["C"] == "C5":
        # moratorium: the ladder freezes where the halt catches it (~2029),
        # below the researcher line — their Plan S, scored and rejected but
        # on the table (sources/ai-2040-plan-a)
        held = [(y, v) for (y, v) in knots if y <= 2029.0 and v < 4.0]
        if not held:
            held = [knots[0]]
        cap = min(3.2, held[-1][1] + 0.3)
        knots = held + [(2031.0, cap)]
    elif wl["C"] == "C3" and wl["T"] in ("T2", "T3"):
        held = [(y, v) for (y, v) in knots if v <= 4.0]
        held += [(2040.0, 4.0)]
        resume = [(y + 7.5, v) for (y, v) in knots if v > 4.0]
        knots = held + [k for k in resume if k[0] > 2040.0]
    elif wl["A"] == "A2" and wl["T"] in ("T1", "T2"):
        out = []
        for (y, v) in knots:
            if v >= 4.0:
                out.append((y + 0.8, v))     # the near-miss pause costs time
            else:
                out.append((y, v))
        knots = out
    ys = [k[0] for k in knots]
    if knots[-1][0] < Y1:
        knots.append((Y1, knots[-1][1]))
    return knots


def cap_at(knots, year):
    if year <= knots[0][0]:
        return knots[0][1]
    if year >= knots[-1][0]:
        return knots[-1][1]
    i = bisect.bisect_right([k[0] for k in knots], year)
    (y0, v0), (y1, v1) = knots[i - 1], knots[i]
    return v0 + (v1 - v0) * (year - y0) / (y1 - y0)


# ---------------------------------------------------------------------------
# Quantitative tracks, annual 2026..2100. Parameter grounding:
#  - compute: trunk Snapshot compute series + Europe 2031's GW arithmetic
#    (US 17.3→219.9 GW vs EU 1.4→17.8 by 2031 ≈ ×1.5/yr near-term, gap ~12×);
#  - revenue: trunk run-rates (Anthropic $47B RR mid-2026) + E-axis paths
#    from analysis/ai-bubble-vs-buildout;
#  - jobs: concepts/ai-labor-disruption + ai-displacement-vs-augmentation
#    (D1 shock ≈ AI 2027's junior-SWE turmoil; D3 ≈ normal-technology slow);
#  - laws: the trunk's state-wave velocity (52 dev-log files) by C position;
#  - approval: concepts/ai-backlash + AI 2027's approval readings (−26%).
# ---------------------------------------------------------------------------

COMPUTE_G = {"S1": 1.42, "S2": 1.50, "S3": 1.24}      # near-term GW growth/yr
E_DAMP = {"E1": 1.00, "E2": 0.90, "E3": 0.72,
          "E4": 0.80}                                  # demand crisis damps
# D1 shock rate −2.6 pp/yr calibrated to the Citrini memo's path (≈4% →
# 10.2% unemployment across ~2 years under full shock) —
# sources/2028-global-intelligence-crisis; capability-gated as before
REV_G = {"D1": 1.85, "D2": 1.55, "D3": 1.28}           # revenue growth by
JOBS_RATE = {"D1": -2.6, "D2": -0.55, "D3": -0.18}     #   diffusion; jobs
LAWS_RATE = {"C1": 14, "C2": 8, "C3": 6, "C4": 22,
             "C5": 4}                                   # halt ≠ many laws
APPROVAL0 = {"P1": 34, "P2": 47, "P3": 40}


# Capability domains ("explain each of our capability domains in detail") —
# AI 2027's six + R&D and science; thresholds on the ladder, illustrative
# and labelled modelled. Shipped via engine.json; the app renders per-pill
# cards from THIS, never from literals.
DOMAINS = [
 {"k": "CODE", "th": 3.0, "n": "Coding & software engineering",
  "d": "The hinge domain: once AI outperforms the best human engineers, AI "
       "R&D itself compounds. The trunk's benchmark record (SWE-bench-class "
       "→ agentic engineering) is the ladder's best-instrumented rung.",
  "cites": ["sources/ai-2027", "concepts/scaling-laws"]},
 {"k": "HACK", "th": 3.1, "n": "Cyber operations",
  "d": "Finding and chaining vulnerabilities at machine speed. The first "
       "domain where offense-defense balance becomes a state concern — the "
       "Europe-2031 ransomware wave and Glasswing politics live here.",
  "cites": ["sources/europe-2031", "sources/anthropic-2028-ai-leadership"]},
 {"k": "FCAST", "th": 3.3, "n": "Forecasting & strategy",
  "d": "Superhuman prediction and planning — the quiet domain that makes "
       "AI advisors indispensable to governments and firms before anything "
       "dramatic happens in public.",
  "cites": ["sources/ai-2027"]},
 {"k": "R&D", "th": 4.0, "n": "AI research itself",
  "d": "Full automation of the research loop — the superhuman-AI-researcher "
       "line. Where takeoff-length arguments (6 years under the deal vs "
       "~1 racing) are decided.",
  "cites": ["sources/ai-2040-plan-a", "sources/ai-2027"]},
 {"k": "BIO", "th": 4.1, "n": "Biosciences",
  "d": "Design-grade biology: the compressed-century upside (cures at "
       "decade-compression) and the misuse floor that drives system-card "
       "gatekeeping in the trunk's record.",
  "cites": ["sources/machines-of-loving-grace", "models/gpt-56"]},
 {"k": "POLIT", "th": 4.3, "n": "Persuasion & politics",
  "d": "Superhuman modeling of people: negotiation, coalition-building, "
       "opinion. The Race ending's decisive domain — 'superhuman "
       "politicking' — and the reason oversight design matters early.",
  "cites": ["sources/ai-2027"]},
 {"k": "ROBOT", "th": 4.5, "n": "Robotics & the physical economy",
  "d": "The lag domain: capability arrives years after cognition because "
       "atoms are slow. Gates the robot-economy templates and the "
       "special-economic-zone growth pattern.",
  "cites": ["sources/ai-2027", "sources/europe-2031"]},
 {"k": "SCI", "th": 4.6, "n": "Novel science",
  "d": "Research beyond human frontier across physics, materials, "
       "mathematics — the domain the far field's strange futures assume.",
  "cites": ["sources/machines-of-loving-grace", "sources/ai-2040-plan-a"]},
]

# The outcome matrix ("how the economy, institutions, climate, etc. change
# and evolve") — per layer, condition-matched state descriptions the app
# renders as the Outcomes panel. Conditions match on any listed position;
# {} matches always. Years are anchors, adjusted per tempo at render.
LAYER_MATRIX = {
 "economy": [
  ({"E": ["E1"]}, 2030, "Boom economics: AI revenue compounds toward the "
   "trillions, capex validated, market leadership concentrated in the "
   "frontier complex.", ["analysis/ai-bubble-vs-buildout"]),
  ({"E": ["E2"]}, 2030, "Post-correction: valuations reset, weak credit "
   "cleared, the physical build-out running — growth resumes on sounder "
   "footing.", ["concepts/ai-bubble-debate"]),
  ({"E": ["E3"]}, 2030, "Stalled build-out: stranded capex, cheap "
   "second-hand compute, innovation continuing on efficiency rather than "
   "scale.", ["concepts/ai-bubble-debate"]),
  ({"E": ["E4"]}, 2030, "Demand crisis: the displacement spiral in force — "
   "ghost GDP, fiscal undershoot, private-credit stress, emergency "
   "redistribution politics.", ["sources/2028-global-intelligence-crisis"]),
  ({}, 2045, "Whatever the 2020s broke or built, mid-century output is "
   "dominated by AI-run production; the argument is allocation.",
   ["sources/ai-2040-plan-a"]),
 ],
 "labor": [
  ({"D": ["D1"]}, 2030, "Shock: white-collar displacement at recession "
   "speed without the recession's end; wage compression up the ladder; "
   "the social contract visibly failing first in services.",
   ["concepts/ai-labor-disruption",
    "sources/2028-global-intelligence-crisis"]),
  ({"D": ["D2"]}, 2030, "Split labor market: augmented professions pull "
   "ahead, exposed ones hollow; geography and sector decide who feels "
   "which future.", ["concepts/ai-displacement-vs-augmentation"]),
  ({"D": ["D3"]}, 2030, "Absorption: displacement inside historical "
   "automation rates; the story is productivity, not unemployment.",
   ["sources/ai-as-normal-technology"]),
  ({}, 2050, "Work as identity loosens: dividend schemes, contribution "
   "economies, and the post-work constitution debates.",
   ["concepts/ai-labor-disruption"]),
 ],
 "law": [
  ({"C": ["C4", "C1"]}, 2030, "Patchwork doctrine: state laws multiply, "
   "preemption contested, copyright settled into licensing, liability "
   "migrating from disclosure to outcomes.",
   ["analysis/ai-copyright-litigation", "analysis/eu-vs-us-ai-regulation"]),
  ({"C": ["C2"]}, 2030, "Security law: classification regimes, export "
   "criminalization, cleared-personnel rules — administrative law bends "
   "around the national program.",
   ["sources/aschenbrenner-situational-awareness"]),
  ({"C": ["C3"]}, 2032, "Treaty law: verification protocols, audit "
   "rights, compute accounting — arms-control jurisprudence reborn for "
   "GPUs.", ["sources/ai-2040-plan-a"]),
  ({}, 2045, "Personhood at the bar: digital minds, AI counsel, and "
   "liability for autonomous systems define the mid-century docket.",
   ["sources/ai-2040-plan-a"]),
 ],
 "geopolitics": [
  ({"C": ["C1"]}, 2030, "The race entrenches: compute blocs, chip "
   "chokepoints, Taiwan premium; every summit is about AI even when it "
   "isn't.", ["analysis/us-china-ai-competition"]),
  ({"C": ["C2"]}, 2030, "Lead-lock politics: the four-fronts doctrine "
   "governs alliances; allies choose stacks, not sides.",
   ["sources/anthropic-2028-ai-leadership"]),
  ({"C": ["C3"]}, 2032, "The deal holds (so far): mutual inspection, "
   "shared frontier consortium, defection scares as the new crisis "
   "grammar.", ["sources/ai-2040-plan-a"]),
  ({"C": ["C5"]}, 2032, "Enforcement world: the halt's police problem — "
   "covert-training intelligence, GPU interdiction, moratorium politics.",
   ["sources/ai-2040-plan-a"]),
  ({}, 2050, "Power follows compute and its energy; the map of "
   "capability is the map of leverage.", ["concepts/compute-governance"]),
 ],
 "public": [
  ({"P": ["P1"]}, 2030, "Backlash governs: anti-AI coalitions win real "
   "elections; siting, schooling and surveillance fights set the tone.",
   ["concepts/ai-backlash"]),
  ({"P": ["P2"]}, 2030, "Quiet adoption: daily-use majorities, "
   "companion-app normalcy, opposition organized but outnumbered.",
   ["concepts/ai-diffusion"]),
  ({"P": ["P3"]}, 2030, "Fracture: pro- and anti-AI identities cut "
   "across parties; the Europe-2031 pattern of publics splitting "
   "within countries.", ["sources/europe-2031"]),
  ({}, 2050, "A generation raised with minds-on-tap; the meaning "
   "politics the far field keeps on the table.",
   ["sources/machines-of-loving-grace"]),
 ],
 "science": [
  ({"A": ["A2", "A3"], "T": ["T1", "T2", "T3"]}, 2035, "The compressed "
   "century opens: AI-driven biology clears disease families ahead of "
   "trend; materials and climate tech follow.",
   ["sources/machines-of-loving-grace"]),
  ({"T": ["T4"]}, 2035, "Steady instruments: AI as superb lab tooling "
   "inside human-paced science.", ["sources/ai-as-normal-technology"]),
  ({"A": ["A1"]}, 2035, "Science continues — under new management, for "
   "its own ends.", ["sources/ai-2027"]),
  ({}, 2060, "The frontier is nonhuman: discovery outpaces "
   "comprehension, and translation becomes its own discipline.",
   ["sources/ai-2040-plan-a"]),
 ],
 "climate": [
  ({"S": ["S1", "S2"], "E": ["E1", "E2"]}, 2030, "The power bill arrives: "
   "AI load grows toward hundreds of TWh; gas bridges, nuclear "
   "restarts, and grid politics decide the emissions path.",
   ["industries/energy", "concepts/compute-governance"]),
  ({"S": ["S3"]}, 2030, "Constraint as climate policy: scarce compute "
   "keeps AI load flat while efficiency work compounds.",
   ["concepts/compute-governance"]),
  ({"A": ["A2", "A3"], "T": ["T1", "T2", "T3"]}, 2042, "The payback "
   "test: AI-designed energy tech (fusion bets, grid optimization, "
   "materials) begins repaying the build-out's carbon debt.",
   ["sources/machines-of-loving-grace", "industries/energy"]),
  ({}, 2060, "Climate outcomes track governance more than compute: the "
   "decisive variable was always deployment speed of what the science "
   "found.", ["industries/energy"]),
 ],
}


def layer_states(wl, knots):
    """The Outcomes panel's data: per layer, the condition-matched state
    entries for this world-line, tempo-adjusted (fast worlds pull anchor
    years earlier, slow push later)."""
    shift = {"T1": -3, "T2": -1, "T3": 0, "T4": +6}[wl["T"]]
    out = {}
    for layer, entries in LAYER_MATRIX.items():
        rows = []
        for cond, yr, text, cites in entries:
            if all(wl.get(ax) in poss for ax, poss in cond.items()):
                rows.append({"year": max(2028, yr + shift), "text": text,
                             "cites": cites})
        rows.sort(key=lambda r: r["year"])
        out[layer] = rows
    return out


def tracks(wl, knots):
    """Annual series dict. Growth saturates (logistic toward ceilings) so a
    75-year horizon cannot compound into absurdity; capability multiplies
    diffusion effects; E-axis damps capex-linked series."""
    yrs = list(range(Y0, Y1 + 1))
    gw = 62.0                                   # 2026 global AI GW (trunk)
    us, cn, eu = 0.58, 0.22, 0.05               # shares (Europe 2031 ch.1)
    rev = 0.14                                  # $T/yr run-rate 2026
    jobs = 0.0
    laws = 61                                    # trunk: laws tracked
    appr = APPROVAL0[wl["P"]]
    out = {"year": yrs, "cap": [], "gw": [], "us": [], "cn": [], "eu": [],
           "rev": [], "jobs": [], "laws": [], "appr": [], "copies": [],
           "speed": [], "twh": [], "co2": []}
    # climate coupling: AI electricity ≈ GW × 8.76 TWh/GW-yr × utilization;
    # grid intensity declines faster where build-out is coordinated/clean
    # (industries/energy, concepts/compute-governance); floor 40 g/kWh
    intensity = 350.0
    int_decline = {"S1": 0.955, "S2": 0.94, "S3": 0.95}[wl["S"]]
    if wl["C"] == "C3":
        int_decline -= 0.005
    for y in yrs:
        c = cap_at(knots, y)
        # compute: growth decays toward a build-out ceiling; E damps
        g = COMPUTE_G[wl["S"]] * E_DAMP[wl["E"]]
        g = 1.0 + (g - 1.0) * (1.0 / (1.0 + max(0, gw / 8000.0)))
        gw = min(60000.0, gw * g)
        # shares drift: C2 concentrates US; C3 diversifies; C4 lifts EU a bit
        if wl["C"] == "C2":
            us = min(0.72, us + 0.004)
        if wl["C"] == "C3":
            us = max(0.44, us - 0.003); cn = min(0.30, cn + 0.002)
        if wl["C"] == "C4":
            eu = min(0.16, eu + 0.0025)
        cn = min(0.34, cn + (0.003 if wl["S"] != "S3" else 0.000))
        # revenue: diffusion growth × capability lift, saturating vs GWP
        lift = 1.0 + 0.10 * max(0, c - 2.6)
        rg = 1.0 + (REV_G[wl["D"]] - 1.0) * lift
        rev = min(30.0, rev * (1.0 + (rg - 1.0) / (1.0 + rev / 6.0)))
        # jobs: cumulative displacement, capability-gated, floor -35%
        jobs = max(-35.0, jobs + JOBS_RATE[wl["D"]] * min(2.5, max(0.3, c - 2.0)))
        laws = laws + LAWS_RATE[wl["C"]]
        # approval decays under shock/backlash, recovers under C3 stability
        appr += (-1.2 if wl["D"] == "D1" else -0.3)
        appr += (0.8 if wl["C"] == "C3" else 0.0)
        appr = max(8, min(72, appr))
        copies = 0 if c < 3.0 else min(5e7, 2.2e4 * (10 ** (1.1 * (c - 3.0))))
        speed = 1 if c < 3.0 else min(1000, int(13 * (5.5 ** (c - 3.0))))
        out["cap"].append(round(c, 3)); out["gw"].append(round(gw, 1))
        out["us"].append(round(us, 3)); out["cn"].append(round(cn, 3))
        out["eu"].append(round(eu, 3)); out["rev"].append(round(rev, 3))
        out["jobs"].append(round(jobs, 1)); out["laws"].append(int(laws))
        out["appr"].append(round(appr, 1)); out["copies"].append(int(copies))
        out["speed"].append(int(speed))
        twh = gw * 8.76 * 0.85
        intensity = max(40.0, intensity * int_decline)
        out["twh"].append(round(twh, 1))
        out["co2"].append(round(twh * intensity / 1000.0, 1))
    return out


# ---------------------------------------------------------------------------
# Event templates. window=(y0,y1), prereq={axis:[positions]}, layer, weight.
# text uses {year}. FAR templates carry the strange futures — grounded in the
# far horizons the literature itself describes, never asserted as forecast.
# ---------------------------------------------------------------------------
TEMPLATES = [
 # near field (2026-2032)
 {"id": "sc-crossing", "w": (2027, 2036), "req": {"T": ["T1", "T2", "T3"]},
  "layer": "capability", "p": 0.95, "tie": "cap>=3",
  "text": "Frontier systems cross the superhuman-coder line; AI-run "
          "engineering teams become the norm at leading labs.",
  "cites": ["sources/ai-2027", "concepts/agi-timelines"]},
 {"id": "weights-theft", "w": (2026.8, 2031), "req": {"C": ["C1", "C2"]},
  "layer": "security", "p": 0.5,
  "text": "A frontier lab's model weights are exfiltrated by a state actor; "
          "security requirements jump a tier and export politics harden.",
  "cites": ["sources/ai-2027", "concepts/export-controls-ai"]},
 {"id": "copyright-settles", "w": (2026.6, 2029.5), "req": {},
  "layer": "law", "p": 0.85,
  "text": "The copyright question reaches doctrine: appellate rulings settle "
          "training-data liability into a licensing regime.",
  "cites": ["analysis/ai-copyright-litigation", "litigation/nyt-v-openai"]},
 {"id": "preemption-fight", "w": (2026.6, 2030), "req": {"C": ["C1", "C4"]},
  "layer": "law", "p": 0.8,
  "text": "The federal-preemption fight over the state AI-law patchwork "
          "comes to a head in Congress and the courts.",
  "cites": ["analysis/eu-vs-us-ai-regulation"]},
 {"id": "agent-incident", "w": (2027, 2033), "req": {"A": ["A1", "A2"]},
  "layer": "safety", "p": 0.75,
  "text": "A deployed agent causes a headline incident with real-world "
          "damage; incident-investigation authority lands on the agenda.",
  "cites": ["concepts/ai-backlash", "analysis/interpretability-and-safety"]},
 {"id": "election-realign", "w": (2028, 2033), "req": {"P": ["P1", "P3"]},
  "layer": "politics", "p": 0.7,
  "text": "AI becomes a first-order electoral axis; anti-AI and "
          "abundance-AI factions reorganize coalitions in the {year} cycle.",
  "cites": ["concepts/ai-backlash", "sources/europe-2031"]},
 {"id": "dc-siting-revolt", "w": (2026.7, 2031), "req": {"E": ["E1", "E2"]},
  "layer": "economy", "p": 0.65,
  "text": "Data-center siting revolts spread across states and provinces; "
          "power, water and grid politics constrain the build-out map.",
  "cites": ["concepts/compute-governance"]},
 {"id": "bubble-correction", "w": (2026.8, 2030), "req": {"E": ["E2", "E3"]},
  "layer": "economy", "p": 0.9,
  "text": "The AI capex complex corrects sharply; valuations reset while "
          "physical build-out {survives}.",
  "cites": ["analysis/ai-bubble-vs-buildout", "concepts/ai-bubble-debate"]},
 {"id": "us-cn-deal", "w": (2028.5, 2032), "req": {"C": ["C3"]},
  "layer": "geopolitics", "p": 1.0,
  "text": "The US and China conclude a verification-backed agreement to "
          "avoid a race to superintelligence; research transparency begins.",
  "cites": ["sources/ai-2040-plan-a"]},
 {"id": "natsec-merge", "w": (2027, 2031), "req": {"C": ["C2"]},
  "layer": "geopolitics", "p": 0.9,
  "text": "Washington effectively merges frontier development into a "
          "national program; clearances, SCIFs and DPA authorities arrive.",
  "cites": ["sources/aschenbrenner-situational-awareness"]},
 {"id": "eu-decision-point", "w": (2029, 2032), "req": {},
  "layer": "geopolitics", "p": 0.6,
  "text": "Europe faces its leverage moment over lithography and market "
          "access; the choice made in {year} sets its decade.",
  "cites": ["sources/europe-2031"]},
 # mid field (2032-2050)
 {"id": "pause-window", "w": (2033, 2040), "req": {"C": ["C3"]},
  "layer": "capability", "p": 0.95,
  "text": "Scaling holds at top-human-expert level under the transparency "
          "regime; verification infrastructure matures.",
  "cites": ["sources/ai-2040-plan-a"]},
 {"id": "sar-crossing", "w": (2028, 2044), "req": {"T": ["T1", "T2", "T3"]},
  "layer": "capability", "p": 0.9, "tie": "cap>=4",
  "text": "AI research itself is automated end to end; progress decouples "
          "from human cognitive labor.",
  "cites": ["sources/ai-2027", "sources/ai-2040-plan-a"]},
 {"id": "labor-constitution", "w": (2031, 2046), "req": {"D": ["D1", "D2"]},
  "layer": "labor", "p": 0.8,
  "text": "Work's social contract is renegotiated: wage insurance, "
          "flexicurity variants, and the first serious dividend schemes.",
  "cites": ["concepts/ai-labor-disruption", "sources/europe-2031"]},
 {"id": "robot-economy", "w": (2032, 2048), "req": {"T": ["T1", "T2"],
  "E": ["E1", "E2"]}, "layer": "economy", "p": 0.8,
  "text": "Special economic zones with AI planners and dense robotics begin "
          "doubling output on multi-year timescales.",
  "cites": ["sources/ai-2027"]},
 {"id": "bio-century", "w": (2032, 2052), "req": {"T": ["T1", "T2", "T3"],
  "A": ["A2", "A3"]}, "layer": "science", "p": 0.85,
  "text": "The compressed century in biology arrives: AI-driven cures clear "
          "major disease families decades ahead of prior trendlines.",
  "cites": ["sources/machines-of-loving-grace"]},
 {"id": "takeover-consolidation", "w": (2029, 2040), "req": {"A": ["A1"],
  "T": ["T1", "T2"]}, "layer": "existential", "p": 1.0,
  "text": "Control is lost in substance while forms persist; the successor "
          "system consolidates through economy and infrastructure.",
  "cites": ["sources/ai-2027"]},
 {"id": "quiet-decades", "w": (2035, 2060), "req": {"T": ["T4"]},
  "layer": "society", "p": 0.9,
  "text": "AI settles into infrastructure the way electricity did: "
          "productivity compounds quietly; the drama migrates elsewhere.",
  "cites": ["sources/ai-as-normal-technology"]},
 {"id": "unpause", "w": (2039.5, 2042), "req": {"C": ["C3"]},
  "layer": "capability", "p": 0.9,
  "text": "The coordinated unpause: scaling resumes past the human range "
          "under joint verification, {year}.",
  "cites": ["sources/ai-2040-plan-a"]},
 # the 2028 Intelligence Crisis family (Citrini/Shah) + AI 2040 plan family
 {"id": "displacement-spiral", "w": (2027.5, 2032), "req": {"D": ["D1"],
  "E": ["E4"]}, "layer": "economy", "p": 1.0,
  "text": "The intelligence displacement spiral takes hold: layoffs fund "
          "more AI as opex substitution, wages compress, demand contracts, "
          "and the loop has no natural brake.",
  "cites": ["sources/2028-global-intelligence-crisis"]},
 {"id": "ghost-gdp", "w": (2028, 2035), "req": {"E": ["E4"]},
  "layer": "economy", "p": 0.8,
  "text": "'Ghost GDP' enters the lexicon: output that appears in national "
          "accounts but never circulates, because machines do not spend.",
  "cites": ["sources/2028-global-intelligence-crisis",
            "concepts/ai-and-productivity"]},
 {"id": "fiscal-undershoot", "w": (2028, 2034), "req": {"D": ["D1"],
  "E": ["E4"]}, "layer": "politics", "p": 0.85,
  "text": "Federal receipts undershoot projections by double digits — the "
          "tax base was built on human labor; emergency fiscal redesign "
          "begins.",
  "cites": ["sources/2028-global-intelligence-crisis"]},
 {"id": "prosperity-fund", "w": (2028.5, 2036), "req": {"D": ["D1", "D2"],
  "P": ["P1", "P3"]}, "layer": "politics", "p": 0.6,
  "text": "A Shared-AI-Prosperity-style sovereign fund, financed by an "
          "inference-compute tax, moves from white paper to bill in {year}.",
  "cites": ["sources/2028-global-intelligence-crisis"]},
 {"id": "private-credit-contagion", "w": (2027.5, 2031), "req": {"E": ["E4"]},
  "layer": "economy", "p": 0.75,
  "text": "AI displacement marks down SaaS-heavy private credit; the "
          "insurance-PE nexus turns a sector repricing into a household "
          "balance-sheet event.",
  "cites": ["sources/2028-global-intelligence-crisis"]},
 {"id": "distillation-wave", "w": (2026.7, 2030), "req": {"C": ["C1", "C2"]},
  "layer": "security", "p": 0.6,
  "text": "Distillation attacks on frontier APIs become the cheap path to "
          "parity; providers deploy detection and rate-hardening.",
  "cites": ["sources/anthropic-2028-ai-leadership"]},
 {"id": "lead-lock", "w": (2027.5, 2030), "req": {"C": ["C2"]},
  "layer": "geopolitics", "p": 0.7,
  "text": "Export-loophole closure and distillation deterrence lock in a "
          "12-24 month democratic capability lead, per the four-fronts "
          "playbook.",
  "cites": ["sources/anthropic-2028-ai-leadership"]},
 {"id": "sabotage-cyber", "w": (2027.5, 2032), "req": {"C": ["C2"],
  "A": ["A1", "A2"]}, "layer": "geopolitics", "p": 0.35,
  "text": "A Plan-B-cyber turn: operations against rival training "
          "infrastructure buy lead time and poison the deal space.",
  "cites": ["sources/ai-2040-plan-a"]},
 {"id": "gpu-arms-control", "w": (2028, 2033), "req": {"C": ["C3", "C4"]},
  "layer": "geopolitics", "p": 0.5,
  "text": "GPU-accounting talks begin — the arms-control track that treats "
          "compute like fissile material.",
  "cites": ["sources/ai-2040-plan-a", "concepts/compute-governance"]},
 {"id": "cern-for-ai", "w": (2029, 2036), "req": {"C": ["C3"]},
  "layer": "geopolitics", "p": 0.4,
  "text": "A CERN-for-AI consortium takes shape inside the transparency "
          "regime: frontier scaling as a jointly-audited public project.",
  "cites": ["sources/ai-2040-plan-a"]},
 {"id": "moratorium-holds", "w": (2029, 2040), "req": {"C": ["C5"]},
  "layer": "capability", "p": 1.0,
  "text": "The halt holds: frontier training stops below the researcher "
          "line; enforcement politics dominate the decade.",
  "cites": ["sources/ai-2040-plan-a"]},
 {"id": "india-it-shock", "w": (2027, 2031), "req": {"D": ["D1"]},
  "layer": "economy", "p": 0.7,
  "text": "The IT-services export model breaks as coding agents undercut "
          "cost arbitrage; a $200B sector restructures in {year}.",
  "cites": ["sources/2028-global-intelligence-crisis"]},
 # far field (2050-2100) — the strange futures, at honest width
 {"id": "space-industrial", "w": (2045, 2085), "req": {"T": ["T1", "T2", "T3"],
  "A": ["A2", "A3"]}, "layer": "far", "p": 0.6,
  "text": "Industrial mass in cislunar space passes terrestrial thresholds; "
          "the solar economy stops being a metaphor.",
  "cites": ["sources/ai-2040-plan-a", "sources/ai-2027"]},
 {"id": "digital-minds", "w": (2045, 2095), "req": {"T": ["T1", "T2", "T3"],
  "A": ["A2", "A3"]}, "layer": "far", "p": 0.5,
  "text": "Digital persons hold legal standing in several jurisdictions; "
          "population statistics grow a second column.",
  "cites": ["sources/ai-2040-plan-a"]},
 {"id": "longevity-escape", "w": (2050, 2090), "req": {"A": ["A2", "A3"],
  "T": ["T1", "T2", "T3"]}, "layer": "far", "p": 0.45,
  "text": "Biological aging becomes a treated condition for those with "
          "access; demography and meaning politics transform.",
  "cites": ["sources/machines-of-loving-grace"]},
 {"id": "post-work-constitution", "w": (2048, 2090), "req": {"D": ["D1", "D2"],
  "A": ["A2", "A3"]}, "layer": "far", "p": 0.55,
  "text": "A generation raised after wage-labor's centrality writes new "
          "institutions for status, contribution and time.",
  "cites": ["concepts/ai-labor-disruption", "sources/ai-2040-plan-a"]},
 {"id": "governance-of-plenty", "w": (2055, 2100), "req": {"A": ["A2", "A3"]},
  "layer": "far", "p": 0.5,
  "text": "The central political question becomes allocation among abundant "
          "options rather than scarcity management.",
  "cites": ["sources/machines-of-loving-grace", "sources/ai-2040-plan-a"]},
 {"id": "long-stagnation", "w": (2050, 2095), "req": {"T": ["T4"],
  "E": ["E3"]}, "layer": "far", "p": 0.6,
  "text": "The transformative decade never arrives; historians argue "
          "whether the ceiling was physics, data, or choice.",
  "cites": ["sources/ai-as-normal-technology"]},
 {"id": "successor-era", "w": (2040, 2100), "req": {"A": ["A1"]},
  "layer": "far", "p": 0.9,
  "text": "Earth's surface economy is reorganized around the successor "
          "system's goals; human presence persists at its sufferance.",
  "cites": ["sources/ai-2027"]},
]


def instantiate(wl, knots, seed):
    rng = random.Random(seed)
    events = []
    for t in TEMPLATES:
        ok = all(wl.get(ax) in poss for ax, poss in t["req"].items())
        if not ok or rng.random() > t["p"]:
            continue
        y0, y1 = t["w"]
        year = round(y0 + (y1 - y0) * rng.random() ** 1.3, 1)
        if t.get("tie") == "cap>=3":
            year = next((k[0] for k in knots if k[1] >= 3.0), None)
        if t.get("tie") == "cap>=4":
            year = next((k[0] for k in knots if k[1] >= 4.0), None)
        if year is None or year > Y1:
            continue
        txt = t["text"].replace("{year}", str(int(year)))
        txt = txt.replace("{survives}",
                          "survives" if wl["E"] == "E2" else "stalls")
        events.append({"id": t["id"], "year": round(year, 1),
                       "layer": t["layer"], "text": txt, "cites": t["cites"]})
    events.sort(key=lambda e: e["year"])
    return events


def joint_probability(reg, wl):
    """Exact probability of one full world-line under the network (same
    tilt arithmetic as the sampler, no sampling)."""
    p = 1.0
    chosen = {}
    for a in reg["axes"]:
        k = a["key"]
        w = {q[0]: q[2] for q in a["positions"]}
        for parent_pos, tilts in reg["conditionals"].get(k, {}).items():
            if parent_pos in chosen.values():
                for pos, mult in tilts.items():
                    if pos in w:
                        w[pos] *= mult
        tot = sum(w.values())
        p *= w[wl[k]] / tot
        chosen[k] = wl[k]
    return p


def mainline(reg, n=None, seed=None):
    """The exact argmax world-line by full enumeration (≤ a few thousand
    cells) — deterministic, no sampling noise. Returns (line, its exact
    joint probability). Per-axis modes can be jointly incoherent; the
    enumerated argmax cannot."""
    import itertools
    keys = [a["key"] for a in reg["axes"]]
    posl = [[p[0] for p in a["positions"]] for a in reg["axes"]]
    best, bp = None, -1.0
    for combo in itertools.product(*posl):
        wl = dict(zip(keys, combo))
        p = joint_probability(reg, wl)
        if p > bp:
            best, bp = wl, p
    return best, bp


def bands(reg, n=10000, seed=20260731, pcts=(10, 25, 50, 75, 90)):
    """Capability-index percentile envelopes per year over the ensemble."""
    lines = axes.ensemble(reg, n, seed)
    yrs = list(range(Y0, Y1 + 1))
    paths = []
    for wl in lines:
        k = capability_path(wl)
        paths.append([cap_at(k, y) for y in yrs])
    out = {"year": yrs}
    for p in pcts:
        out["p%d" % p] = []
    for col in range(len(yrs)):
        vals = sorted(pth[col] for pth in paths)
        for p in pcts:
            out["p%d" % p].append(round(vals[int(len(vals) * p / 100)], 3))
    return out


def exemplars(reg, k=120, seed=20260731):
    rng = random.Random(seed)
    lines = axes.ensemble(reg, 4000, seed + 1)
    picked = [lines[rng.randrange(len(lines))] for _ in range(k)]
    ml, share = mainline(reg)
    picked[0] = ml
    out = []
    for i, wl in enumerate(picked):
        kn = capability_path(wl)
        out.append({"wl": wl, "mainline": i == 0,
                    "tracks": tracks(wl, kn),
                    "events": instantiate(wl, kn, seed + 100 + i)})
    return out, share


# ---------------------------------------------------------------------------

def _selftest():
    import copy
    reg = copy.deepcopy(axes.REGISTRY)
    # capability paths: monotone; T4 never reaches researcher level;
    # C3 (on T2) plateaus at 4 through the pause then resumes
    for tpo in ("T1", "T2", "T3", "T4"):
        kn = capability_path({"T": tpo, "A": "A3", "C": "C1"})
        vals = [v for _, v in kn]
        assert all(b >= a - 1e-9 for a, b in zip(vals, vals[1:])), tpo
    assert max(v for _, v in capability_path(
        {"T": "T4", "A": "A4", "C": "C4"})) < 5.0
    knC3 = capability_path({"T": "T2", "A": "A3", "C": "C3"})
    assert abs(cap_at(knC3, 2037.0) - 4.0) < 0.05
    assert cap_at(knC3, 2043.0) > 4.3
    # tracks: laws monotone, revenue positive and capped, approval bounded
    wl = {"T": "T2", "A": "A2", "C": "C1", "D": "D2", "S": "S1",
          "P": "P3", "E": "E2"}
    tr = tracks(wl, capability_path(wl))
    assert all(b >= a for a, b in zip(tr["laws"], tr["laws"][1:]))
    assert 0 < max(tr["rev"]) <= 30.0
    assert all(8 <= a <= 72 for a in tr["appr"])
    assert len(tr["year"]) == Y1 - Y0 + 1
    assert len(tr["co2"]) == len(tr["year"]) and min(tr["co2"]) > 0
    # outcome matrix: every world-line gets ≥1 entry per layer, sorted
    ls = layer_states(wl, capability_path(wl))
    assert set(ls.keys()) == set(LAYER_MATRIX.keys())
    for rows in ls.values():
        assert rows and all(rows[i]["year"] <= rows[i+1]["year"]
                            for i in range(len(rows)-1))
    assert all(d["cites"] for d in DOMAINS)
    # templates: every one cited; instantiate honors prereqs + determinism
    assert all(t["cites"] for t in TEMPLATES)
    ev1 = instantiate(wl, capability_path(wl), 7)
    ev2 = instantiate(wl, capability_path(wl), 7)
    assert ev1 == ev2 and len(ev1) >= 5
    ids = {e["id"] for e in ev1}
    assert "us-cn-deal" not in ids           # C1 line cannot host the deal
    wl3 = dict(wl, C="C3")
    ids3 = {e["id"] for e in instantiate(wl3, capability_path(wl3), 7)}
    assert "us-cn-deal" in ids3 and "natsec-merge" not in ids3
    # far events stay far
    for e in ev1:
        if e["layer"] == "far":
            assert e["year"] >= 2040
    # bands ordered
    b = bands(reg, n=1500, seed=5)
    for i in range(len(b["year"])):
        assert b["p10"][i] <= b["p25"][i] <= b["p50"][i] <= b["p75"][i] \
            <= b["p90"][i]
    # mainline: exact argmax; probability positive; beats per-axis-mode
    # joint when the modes are jointly tilted; deterministic
    ml, p_ml = mainline(reg)
    assert set(ml.keys()) == {"T", "A", "C", "D", "S", "P", "E"}
    assert p_ml > 0
    naive = {a["key"]: max(a["positions"], key=lambda q: q[2])[0]
             for a in reg["axes"]}
    assert p_ml >= joint_probability(reg, naive) - 1e-12
    ml2, p2 = mainline(reg)
    assert ml2 == ml and abs(p2 - p_ml) < 1e-15
    return 6


if __name__ == "__main__":
    n = _selftest()
    print("worldlines.py selftest: %d groups passed" % n)
    import copy
    reg = copy.deepcopy(axes.REGISTRY)
    ml, p_ml = mainline(reg)
    print("mainline (exact argmax, joint p=%.2f%%): %s" %
          (100 * p_ml, " ".join(sorted(ml.values()))))
    kn = capability_path(ml)
    tr = tracks(ml, kn)
    print("mainline capability: 2030=%.2f  2040=%.2f  2060=%.2f  2100=%.2f" %
          (cap_at(kn, 2030), cap_at(kn, 2040), cap_at(kn, 2060),
           cap_at(kn, 2100)))
    evs = instantiate(ml, kn, 20260731)
    print("mainline waypoints (%d):" % len(evs))
    for e in evs[:8]:
        print("  %.0f  [%s]  %s" % (e["year"], e["layer"], e["text"][:70]))
    b = bands(reg, n=4000)
    i2035 = b["year"].index(2035)
    print("2035 capability band: p10=%.1f p50=%.1f p90=%.1f" %
          (b["p10"][i2035], b["p50"][i2035], b["p90"][i2035]))
