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

HERE = os.path.dirname(os.path.abspath(__file__))

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
# Each T position now NAMES the window in which the research rung at 4.0 is
# first crossed, so the knots are derived from the window rather than chosen
# beside it: T1 2027-2028, T2 2029-2031, T3 2032-2036, T4 2037-2050. T5 asserts
# that the method asymptotes, so it stays below 4.0 through 2050 and never
# reaches 5.0 inside the window at all.
TEMPO_KNOTS = {
    "T1": [(2026.6, 2.6), (2027.2, 3.0), (2027.9, 4.0), (2028.6, 5.0),
           (2029.4, 6.0)],
    "T2": [(2026.6, 2.6), (2028.6, 3.0), (2030.2, 4.0), (2032.2, 5.0),
           (2034.4, 6.0)],
    "T3": [(2026.6, 2.6), (2031.0, 3.0), (2034.0, 4.0), (2038.0, 5.0),
           (2042.5, 6.0)],
    "T4": [(2026.6, 2.6), (2033.5, 3.0), (2043.5, 4.0), (2058.0, 5.0),
           (2078.0, 6.0)],
    "T5": [(2026.6, 2.6), (2036.0, 3.0), (2050.0, 3.6), (2075.0, 3.9),
           (2100.0, 4.0)],
}


# M1 (r9): THE TAKEOFF SHAPE REACHES THE CURVE. K names the months between the
# coding rung at 3.0 and the research rung at 4.0, and the tempo knots carried a
# gap of T's own (T2: 1.6 years), so a path that said "rungs inside one year"
# drew a curve that took longer, and the chronicle lettered "about three years
# after" beside K1's "within twelve months" on the published mainline. The
# research crossing is T's dated quantity and stays where T puts it; the coding
# crossing moves to sit K's gap before it, no earlier than K_FLOOR, which is
# where the 2026 anchor at 2.6 leaves room for the climb. The gaps are the
# midpoints of the registry's own bands (K4 is open-ended and takes six and a half
# years); a path whose gap cannot fit — T1 with K4 — is clamped and counted, and
# the count is reported by the self-test rather than hidden.
K_GAP = {"K1": 0.75, "K2": 1.5, "K3": 3.5, "K4": 6.5}
K_FLOOR = 2027.2


def capability_path(wl):
    """Knots (year, index) after axis modifiers. A2 inserts a pause-and-
    reassess plateau at the researcher level; C3 holds Plan A's expert-level
    pause 2035→2040 then resumes; A1 truncates ascent at takeover (the
    index stays — the world changes owner, not capability). K then places the
    coding crossing its gap before the research crossing (M1, r9)."""
    knots = list(TEMPO_KNOTS[wl["T"]])
    if wl["C"] == "C8":
        # moratorium: the ladder freezes where the halt catches it (~2029),
        # below the researcher line — their Plan S, scored and rejected but
        # on the table (sources/ai-2040-plan-a)
        held = [(y, v) for (y, v) in knots if y <= 2029.0 and v < 4.0]
        if not held:
            held = [knots[0]]
        cap = min(3.2, held[-1][1] + 0.3)
        knots = held + [(2031.0, cap)]
    elif wl["C"] in ("C5", "C4") and wl["T"] in ("T2", "T3"):
        held = [(y, v) for (y, v) in knots if v <= 4.0]
        held += [(2040.0, 4.0)]
        resume = [(y + 7.5, v) for (y, v) in knots if v > 4.0]
        knots = held + [k for k in resume if k[0] > 2040.0]
    elif wl["A"] in ("A2", "A3") and wl["T"] in ("T1", "T2"):
        out = []
        for (y, v) in knots:
            if v >= 4.0:
                out.append((y + 0.8, v))     # the near-miss pause costs time
            else:
                out.append((y, v))
        knots = out
    kpos = wl.get("K")
    if kpos in K_GAP:
        i3 = next((i for i, (y, v) in enumerate(knots) if v >= 3.0), None)
        i4 = next((i for i, (y, v) in enumerate(knots) if v >= 4.0), None)
        if (i3 is not None and i4 is not None and i3 < i4
                and knots[i4][0] < Y1 and abs(knots[i3][1] - 3.0) < 1e-9):
            y3 = max(K_FLOOR, knots[i4][0] - K_GAP[kpos])
            knots[i3] = (y3, 3.0)
            knots = [k for i, k in enumerate(knots)
                     if not (i < i3 and k[0] >= y3)]
            knots.sort()
    if knots[-1][0] < Y1:
        knots.append((Y1, knots[-1][1]))
    return knots


def k_gap_clamped(wl):
    """Whether K's gap could not fit before T's research crossing on this
    line, so the coding crossing sits at K_FLOOR and the gap is shorter than
    the position says. The self-test reports the ensemble share."""
    kpos = wl.get("K")
    if kpos not in K_GAP:
        return False
    knots = capability_path(wl)
    y3 = next((y for y, v in knots if v >= 3.0), None)
    y4 = next((y for y, v in knots if v >= 4.0), None)
    if y3 is None or y4 is None or y4 >= Y1:
        return False
    return (y4 - y3) < K_GAP[kpos] - 1e-6


def crossings(knots):
    """The exact year each rung is first reached on a path, from the knots."""
    out = {}
    for r in (3, 4, 5, 6):
        y = None
        for (y0, v0), (y1, v1) in zip(knots, knots[1:]):
            if v0 < r <= v1:
                y = y0 + (y1 - y0) * (r - v0) / (v1 - v0) if v1 > v0 else y1
                break
        if y is None and knots and knots[0][1] >= r:
            y = knots[0][0]
        if y is not None and y < Y1:
            out[str(r)] = round(y, 2)
    return out


# M5 (r9): A MEASURED SERIES UNDER THE LADDER. METR's 50% time horizon in hours,
# anchored to the rungs: 8 hours at the reliable-agent rung (2.0); 16 hours at
# the 2026 anchor (2.6; METR's frontier report of 2026-05-19 placed the
# strongest public model near 12 hours in February and March 2026 and internal
# models at or above 16 hours, the registry's own T description); one working
# month of 167 hours at the coding rung (3.0; T1's arithmetic); one working
# year of 2,000 hours at the research rung (4.0). Log-linear between anchors.
# Above 4.0 no human has been timed at the task, so the series stops being a
# measurement: it is emitted at the rung-4 figure and the sheet says so.
HORIZON_ANCHORS = [(1.0, 1.0), (2.0, 8.0), (2.6, 16.0), (3.0, 167.0),
                   (4.0, 2000.0)]


def horizon_hours(c):
    if c <= HORIZON_ANCHORS[0][0]:
        return HORIZON_ANCHORS[0][1]
    if c >= HORIZON_ANCHORS[-1][0]:
        return HORIZON_ANCHORS[-1][1]
    for (c0, h0), (c1, h1) in zip(HORIZON_ANCHORS, HORIZON_ANCHORS[1:]):
        if c0 <= c <= c1:
            t = (c - c0) / (c1 - c0)
            return math.exp(math.log(h0) + t * (math.log(h1) - math.log(h0)))
    return HORIZON_ANCHORS[-1][1]


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

# r5 re-keyed every one of these. S now names WHICH constraint binds, so capacity
# growth follows the constraint: capital binding leaves siting free and grows
# fastest, power and siting binding is the slowest, and a leading-edge supply
# shock is slower still while it lasts.
COMPUTE_G = {"S1": 1.44, "S2": 1.50, "S3": 1.22, "S4": 1.30, "S5": 1.15}
# E is now five states of the capital side, ordered by how hard each cuts the
# spend that builds capacity.
E_DAMP = {"E1": 1.00, "E2": 0.94, "E3": 0.88, "E4": 0.72, "E5": 0.62}
# D is a measured ladder: the share of client-judged paid work finished at
# acceptable quality. The Remote Labor Index graded 240 real freelance projects
# at 15.8% on 2026-07-01 against 2.5% in October 2025, so D1 (delivery stalls
# under a tenth) and D2 (reliability gates it) are the two live bands today.
REV_G = {"D1": 1.22, "D2": 1.48, "D3": 1.70, "D4": 1.88}
# The jobs rate follows the same ladder. D4's −2.6 pp/yr is the rate calibrated
# to the displacement path; a stalled delivery band barely moves employment.
JOBS_RATE = {"D1": -0.12, "D2": -0.45, "D3": -1.10, "D4": -2.60}
# LAW VELOCITY MOVED AXIS. Counting statutes was never a question about what the
# principal states settle between them; it is a question about regulatory
# architecture, which is why r5 carved R out of C. Keyed on R now.
LAWS_RATE = {"R1": 5, "R2": 24, "R3": 9, "R4": 12, "R5": 18, "R6": 7}
APPROVAL0 = {"P1": 47, "P2": 38, "P3": 40, "P4": 36, "P5": 31}

# M4 (r9): TRACKS AS DYNAMICS AGAINST CEILINGS. Every track used to be a
# compounding rate with a hard cap — compute at 60,000 GW, revenue at $30
# trillion, employment at −35%, agent copies at 50 million — and by the 2040s
# every sampled path sat at its caps, so the far decades of the chronicle read
# as frozen numbers (Research/plan-2026-09-02-chronicle.md, §3, in the
# forecaster). The caps are replaced by logistic growth against ceilings that
# are themselves quantities of the world, and the arrival era's axes set which
# ceiling binds. Every constant here is modelled and the sheet says so; the
# transformation era's own variables (M3) will take these over.
#
# compute — world electricity generating capacity was near 9,500 GW in 2026
# (IEA and Energy Institute statistical reviews) and has grown 2 to 3% a year;
# an AI load larger than all generation cannot be served. The share a supply
# position can reach: capital-bound build-outs (S1, S2) toward a third of world
# generation, the fast scenarios' asymptote (Situational Awareness's 100 GW
# clusters and 20% of US power by 2030; the 2026 record of 6% of US electricity
# to data centres in the S dossier); grid- and permission-bound (S3) an eighth;
# licence-bound (S4) a fifth; a leading-edge supply shock (S5) a sixth.
WORLD_GW_2026, WORLD_GW_GROWTH = 9500.0, 1.025
GW_SHARE_MAX = {"S1": 0.30, "S2": 0.35, "S3": 0.12, "S4": 0.20, "S5": 0.15}
# world output — near $115 trillion in 2026 (IMF), 3% a year at trend. The
# growth regime is the transformation era's variable; until M3 the benefit
# position sets how much of the capability above the coding rung reaches
# measured growth, two index units at most: G4 (gains large, real and audited)
# lets a fast regime through at 9% a year, G5 (measured net gain flat) none.
GWP_2026, GWP_GROWTH = 115.0, 1.03
GWP_LIFT = {"G1": 0.010, "G2": 0.015, "G3": 0.010, "G4": 0.030, "G5": 0.000,
            "G6": 0.005}
GWP_LIFT_UNITS = 2.0
# the lift is the transformation era's, and that era ends in a settlement: it
# tapers to trend over GWP_LIFT_TAPER years after the research crossing, so a
# fast regime is a period and not a permanent state of the world
GWP_LIFT_TAPER = 40.0
# revenue — a share of world output the diffusion band can reach: the labour
# share of output near 55%, times the share of paid work the band names
# (a tenth, a third, a half, more than half), times the part of that value the
# seller captures.
REV_SHARE_MAX = {"D1": 0.03, "D2": 0.08, "D3": 0.15, "D4": 0.25}
# work — the machine share of paid work rises toward the band's own ceiling
# (D's criteria: under a tenth, a tenth to a third, a third to a half, more
# than half), gated by capability as before; re-employment then absorbs a part
# of it over REEMPLOY_TAU years (the postwar regional record: a decade or two),
# high where the band says the postwar record
# contains the transfer (D3) and low where it says re-employment has not
# closed the window (D4). Employment against 2026 is the machine share the
# re-employment has not absorbed, so a dip has a settlement level.
WORK_SHARE_MAX = {"D1": 0.10, "D2": 0.33, "D3": 0.50, "D4": 0.70}
WORK_RATE = {"D1": 0.005, "D2": 0.020, "D3": 0.045, "D4": 0.100}
REEMPLOY_MAX = {"D1": 0.80, "D2": 0.60, "D3": 0.70, "D4": 0.30}
REEMPLOY_TAU = 12.0
# approval — mean-reverting to a level the public position sets (a majority
# under normalised adoption, a minority under an anti-AI coalition), lowered by
# employment loss and raised where a verified limit holds, and shocked by the
# path's own events. APPROVAL0 stays the 2026 reading.
APPROVAL_EQ = {"P1": 55.0, "P2": 36.0, "P3": 42.0, "P4": 40.0, "P5": 30.0}
APPROVAL_K, APPROVAL_JOBS, APPROVAL_LIMIT = 0.12, 0.35, 5.0
# statutes in force — accretion slows as consolidation and preemption replace it
LAWS_MAX = 1200.0
# agent copies — a machine population bounded by compute and by the efficiency
# the index buys: 22,000 copies on 62 GW at the 2026 anchor (AI 2027's April
# 2026 frame), ten times per 1.1 index units.
COPIES_PER_GW0, COPIES_PER_GW_LOG = 355.0, 0.9


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
    shift = {"T1": -3, "T2": -1, "T3": 0, "T4": +6, "T5": +12}[wl["T"]]
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


def tracks(wl, knots, events=None):
    """Annual series dict, 2026..2100, as dynamics against ceilings (M4, r9):
    compute logistic toward the share of world generating capacity its supply
    position can reach; revenue toward its share of a world output whose growth
    the benefit position sets; the machine share of paid work toward its
    diffusion band's ceiling, with re-employment absorbing part of it; approval
    mean-reverting to the level the public position and the labour market set;
    statutes saturating; agent copies bounded by compute. The path's own events
    move the tracks that follow them (M2). Nothing here holds a hard cap."""
    yrs = list(range(Y0, Y1 + 1))
    eff = effect_series(events, yrs)
    S, E, D, R, P, C = wl["S"], wl["E"], wl["D"], wl["R"], wl["P"], wl["C"]
    lift_g = GWP_LIFT.get(wl.get("G"), 0.01)
    gw = 62.0                                   # 2026 global AI GW (trunk)
    us, cn, eu = 0.58, 0.22, 0.05               # shares (Europe 2031 ch.1)
    rev = 0.14                                  # $T/yr run-rate 2026
    gwp = GWP_2026
    y4 = crossings(knots).get("4")
    m, t_on = 0.0, None
    laws = 61.0                                  # trunk: laws tracked
    appr = float(APPROVAL0[P])
    out = {"year": yrs, "cap": [], "gw": [], "us": [], "cn": [], "eu": [],
           "rev": [], "jobs": [], "laws": [], "appr": [], "copies": [],
           "speed": [], "twh": [], "co2": [], "hz": [], "gwp": [], "work": []}
    # climate coupling: AI electricity ≈ GW × 8.76 TWh/GW-yr × utilization;
    # grid intensity declines faster where build-out is coordinated/clean
    # (industries/energy, concepts/compute-governance); floor 40 g/kWh
    intensity = 350.0
    # the forecaster's build extracts this block from the source by its shape
    # (build_site.py climate_params): the map indexed by wl["S"], the bonus
    # condition on wl["C"], the hours, the utilisation and the floor
    int_decline = {"S1": 0.955, "S2": 0.940, "S3": 0.950,
                   "S4": 0.948, "S5": 0.958}[wl["S"]]
    if wl["C"] in ("C5", "C4"):
        int_decline -= 0.005
    for i, y in enumerate(yrs):
        c = cap_at(knots, y)
        # compute: logistic growth toward the ceiling of the year; E damps the
        # GROWTH EXCESS, the path's capital events cut or lift it. The r8 form
        # multiplied the growth factor itself, so a demand crisis on a slow
        # supply (E5 on S5: 1.15 × 0.62) shrank compute 29% a year for seventy
        # years, which no correction does; the tenth percentile of compute sat
        # at the floor by the 2070s.
        g = (COMPUTE_G[S] - 1.0) * E_DAMP[E] * eff["gw_g"][i]
        ceiling = GW_SHARE_MAX[S] * WORLD_GW_2026 * WORLD_GW_GROWTH ** (y - Y0)
        gw = max(10.0, gw * (1.0 + g * max(0.0, 1.0 - gw / ceiling))
                 * eff["gw_mult"][i])
        # shares drift: C2 concentrates US; C3 diversifies; C4 lifts EU a bit
        if R == "R4":
            us = min(0.72, us + 0.004)
        if C in ("C5", "C4"):
            us = max(0.44, us - 0.003); cn = min(0.30, cn + 0.002)
        if R == "R2":
            eu = min(0.16, eu + 0.0025)
        cn = min(0.34, cn + (0.003 if S != "S3" else 0.000))
        # world output: trend growth plus what the benefit position lets
        # through of the capability above the coding rung
        taper = 1.0 if y4 is None else max(0.0, 1.0 - max(0.0, y - y4) / GWP_LIFT_TAPER)
        gwp *= GWP_GROWTH + lift_g * min(GWP_LIFT_UNITS, max(0.0, c - 3.0)) * taper
        # revenue: diffusion growth × capability lift, logistic toward the
        # band's share of world output
        lift = 1.0 + 0.10 * max(0, c - 2.6)
        rg = (REV_G[D] - 1.0) * lift * eff["rev_g"][i]
        rev_max = REV_SHARE_MAX[D] * gwp
        rev = rev * (1.0 + rg * max(0.0, 1.0 - rev / rev_max))
        # work: the machine share, capability-gated, toward the band's ceiling
        gate = min(2.5, max(0.3, c - 2.0))
        m += (WORK_RATE[D] * gate * eff["work_rate"][i]
              * max(0.0, 1.0 - m / WORK_SHARE_MAX[D]))
        if t_on is None and m >= 0.005:
            t_on = y
        rho_max = max(0.0, min(0.95, REEMPLOY_MAX[D] + eff["reemploy"][i]))
        rho = 0.0 if t_on is None else \
            rho_max * (1.0 - math.exp(-(y - t_on) / REEMPLOY_TAU))
        jobs = -100.0 * m * (1.0 - rho)
        # statutes: the rate of the regulatory architecture, saturating
        laws += LAWS_RATE[R] * eff["laws_g"][i] * max(0.0, 1.0 - laws / LAWS_MAX)
        # approval: toward the level the public position and the labour
        # market set, raised where a verified limit holds, shocked by events
        eq = (APPROVAL_EQ[P] + APPROVAL_JOBS * jobs
              + (APPROVAL_LIMIT if C in ("C5", "C4") else 0.0))
        appr += APPROVAL_K * (eq - appr) + eff["appr_shock"][i]
        appr = max(8.0, min(80.0, appr))
        # the machine population and its clock rate
        copies = 0.0 if c < 3.0 else \
            gw * COPIES_PER_GW0 * (10 ** (COPIES_PER_GW_LOG * (c - 2.6)))
        speed = 1 if c < 3.0 else min(1000, int(13 * (5.5 ** (c - 3.0))))
        out["cap"].append(round(c, 3)); out["gw"].append(round(gw, 1))
        out["us"].append(round(us, 3)); out["cn"].append(round(cn, 3))
        out["eu"].append(round(eu, 3)); out["rev"].append(round(rev, 3))
        out["jobs"].append(round(jobs, 1)); out["laws"].append(int(laws))
        out["appr"].append(round(appr, 1)); out["copies"].append(int(copies))
        out["speed"].append(int(speed))
        out["hz"].append(round(horizon_hours(c), 1))
        out["gwp"].append(round(gwp, 1)); out["work"].append(round(m, 4))
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


# M2 (r9): EFFECTS. An event that the ledger dates now moves the tracks that
# follow it, so the chronicle is causal rather than listed. Multiplicative
# entries are [factor, years]: the factor applies to the compute growth excess
# (gw_g), to compute itself year on year (gw_mult), to the revenue growth
# excess (rev_g), to the rate paid work transfers (work_rate), or to the
# statute rate (laws_g). Additive entries: reemploy raises the share
# re-employment can absorb for [amount, years]; appr_shock moves approval once,
# in the event's year, and the mean reversion carries it off. Magnitudes are
# modelled and stated as such; the families are grounded — a capital event
# cuts the growth excess while the correction lasts (analysis/ai-bubble-vs-
# buildout), an incident shocks approval and speeds statutes (concepts/
# ai-backlash), a labour statute raises re-employment for good (concepts/
# ai-labor-disruption). A dividend or a post-work constitution moves approval
# and status, and no one's employment, so they carry no re-employment effect.
EFFECTS = {
    "bubble-correction": {"gw_g": [0.55, 3], "rev_g": [0.80, 2],
                          "appr_shock": -2.0},
    "dc-siting-revolt": {"gw_g": [0.80, 4]},
    "moratorium-holds": {"gw_g": [0.50, 10]},
    "natsec-merge": {"gw_g": [1.10, 5]},
    "pause-window": {"gw_g": [0.85, 6]},
    "unpause": {"gw_g": [1.15, 5]},
    "gpu-arms-control": {"gw_g": [0.90, 5]},
    "lead-lock": {"gw_g": [1.05, 5]},
    "sabotage-cyber": {"gw_mult": [0.98, 2], "appr_shock": -3.0},
    "private-credit-contagion": {"gw_mult": [0.97, 3], "appr_shock": -4.0},
    "displacement-spiral": {"work_rate": [1.5, 5], "rev_g": [0.85, 5],
                            "reemploy": [-0.15, 8], "appr_shock": -4.0},
    "india-it-shock": {"work_rate": [1.2, 3]},
    "robot-economy": {"rev_g": [1.15, 10]},
    "fiscal-undershoot": {"appr_shock": -4.0, "laws_g": [1.3, 3]},
    "labor-constitution": {"reemploy": [0.10, 999], "appr_shock": 3.0},
    "prosperity-fund": {"appr_shock": 2.0},
    "agent-incident": {"appr_shock": -6.0, "laws_g": [1.5, 3]},
    "weights-theft": {"appr_shock": -3.0, "laws_g": [1.3, 2]},
    "election-realign": {"laws_g": [1.4, 4]},
    "preemption-fight": {"laws_g": [0.7, 3]},
    "copyright-settles": {"laws_g": [1.2, 2]},
    "us-cn-deal": {"appr_shock": 4.0},
    "bio-century": {"appr_shock": 5.0},
    "longevity-escape": {"appr_shock": 3.0},
    "governance-of-plenty": {"appr_shock": 4.0},
    "takeover-consolidation": {"appr_shock": -10.0},
}
for _t in TEMPLATES:
    _t["effects"] = EFFECTS.get(_t["id"], {})
TEMPLATE_BY_ID = {t["id"]: t for t in TEMPLATES}
EFFECT_MULT = ("gw_g", "gw_mult", "rev_g", "work_rate", "laws_g")
EFFECT_ADD = ("reemploy", "appr_shock")


def effect_series(events, yrs):
    """Per-year multipliers and shocks from a path's dated events."""
    eff = {k: [1.0] * len(yrs) for k in EFFECT_MULT}
    eff.update({k: [0.0] * len(yrs) for k in EFFECT_ADD})
    for e in events or []:
        fx = e.get("effects")
        if fx is None:
            fx = TEMPLATE_BY_ID.get(e.get("id"), {}).get("effects", {})
        y = int(math.floor(e["year"]))
        for k, spec in fx.items():
            if k == "appr_shock":
                i = y - yrs[0]
                if 0 <= i < len(yrs):
                    eff[k][i] += spec
                continue
            val, dur = spec
            for i in range(max(0, y - yrs[0]),
                           min(len(yrs), y - yrs[0] + int(dur))):
                if k in EFFECT_ADD:
                    eff[k][i] += val
                else:
                    eff[k][i] *= val
    return eff


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
                          "survives" if wl["E"] in ("E2", "E3") else "stalls")
        events.append({"id": t["id"], "year": round(year, 1),
                       "layer": t["layer"], "text": txt, "cites": t["cites"]})
    events.sort(key=lambda e: e["year"])
    return events


def onsets(wl, knots, events, tr):
    """The year each position of a path comes into force, by the rule the
    registry states for it (axes.ONSETS): dated by a template the path
    instantiated, by a rung the capability path crosses, by a track passing a
    level, or by a year its criterion names. A position with no rule is in
    force from the record and is absent here."""
    by_id = {}
    for e in events or []:
        by_id.setdefault(e["id"], e["year"])
    cross = crossings(knots)
    out = {}
    for ax, pos in wl.items():
        rule = axes.ONSETS.get(pos)
        if not rule:
            continue
        y = None
        if "template" in rule:
            y = by_id.get(rule["template"])
        elif "milestone" in rule:
            y = cross.get(str(rule["milestone"]))
        elif "track" in rule:
            series = tr.get(rule["track"]) or []
            for yy, v in zip(tr["year"], series):
                if (v <= rule["at"]) if rule.get("dir") == "below" \
                        else (v >= rule["at"]):
                    y = yy
                    break
        elif "year" in rule:
            y = rule["year"]
        if y is not None:
            out[pos] = round(float(y), 1)
    return out


def medoid(lines):
    """The sampled line closest to all the others (M6, r9). Under Hamming
    distance the sum of distances from one line to the set decomposes by axis,
    so the medoid is the line whose positions the most other lines share,
    summed over the axes — exact, in one pass over the marginal counts, and a
    real sample with a real ledger where the argmax cell may have been sampled
    once or never. Returns (line, mean share of the ensemble agreeing with it
    per axis). Ties go to the first line in the ensemble's order."""
    counts = {}
    for wl in lines:
        for k, pos in wl.items():
            counts.setdefault(k, {}).setdefault(pos, 0)
            counts[k][pos] += 1
    best, bs = None, -1
    for wl in lines:
        sc = sum(counts[k][pos] for k, pos in wl.items())
        if sc > bs:
            best, bs = wl, sc
    n = len(lines)
    return dict(best), bs / float(n * len(best))


def medoid_brute(lines):
    best, bd = None, None
    for a in lines:
        d = sum(sum(1 for k in a if a[k] != b[k]) for b in lines)
        if bd is None or d < bd:
            best, bd = a, d
    return dict(best)


TRACK_BAND_KEYS = ("gw", "rev", "jobs", "appr", "laws", "hz", "copies", "gwp")


def track_bands(lines, seed, pcts=(10, 50, 90)):
    """Percentile envelopes per year for every quantitative track over an
    ensemble of lines, each with its own instantiated events (M4, r9): what
    the bands do for capability, for the quantities."""
    yrs = list(range(Y0, Y1 + 1))
    cols = {k: [[] for _ in yrs] for k in TRACK_BAND_KEYS}
    for i, wl in enumerate(lines):
        kn = capability_path(wl)
        tr = tracks(wl, kn, instantiate(wl, kn, seed + i))
        for k in TRACK_BAND_KEYS:
            for j, v in enumerate(tr[k]):
                cols[k][j].append(v)
    out = {"year": yrs, "n": len(lines)}
    for k in TRACK_BAND_KEYS:
        out[k] = {}
        for p in pcts:
            out[k]["p%d" % p] = []
        for j in range(len(yrs)):
            vals = sorted(cols[k][j])
            for p in pcts:
                out[k]["p%d" % p].append(vals[min(len(vals) - 1,
                                                  int(len(vals) * p / 100))])
    return out


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


def mainline_enumerate(reg):
    """The argmax by full enumeration. Kept as the reference implementation the
    fast one is tested against, and never called by the emit."""
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


def _axis_bounds(reg):
    """The largest factor each axis can contribute under ANY parent assignment.

    Admissible and cheap. The numerator is bounded above by taking every tilt
    ABOVE one that could reach a position; the denominator below by taking
    every tilt BELOW one on every position. No real parent assignment can beat
    that, so the product of these bounds over the unassigned tail can never
    understate what the tail is worth — which is what makes the pruning exact.
    """
    out = []
    for a in reg["axes"]:
        pri = {q[0]: q[2] for q in a["positions"]}
        up = {k: v for k, v in pri.items()}
        lo = {k: v for k, v in pri.items()}
        for _parent, tilts in reg["conditionals"].get(a["key"], {}).items():
            for pos, mult in tilts.items():
                if pos not in pri:
                    continue
                if mult > 1.0:
                    up[pos] *= mult
                else:
                    lo[pos] *= mult
        best = 0.0
        for pos in pri:
            # the denominator is smallest when every OTHER position is tilted
            # down as far as it can go and this one sits at its own low value
            den = sum(lo[q] for q in pri if q != pos) + min(lo[pos], up[pos])
            if den > 0:
                best = max(best, up[pos] / den)
        out.append(min(1.0, best) if best <= 1.0 else best)
    return out


def mainline(reg, n=None, seed=None):
    """The exact argmax world-line — deterministic, no sampling noise. Returns
    (line, its exact joint probability). Per-axis modes can be jointly
    incoherent; the argmax cannot.

    IT WAS A FULL CARTESIAN PRODUCT, and the docstring said "≤ a few thousand
    cells" while r8 made it 120,960,000. Ten axes were 20.16M and eleven are
    six times that; the emit calls this twice, so 2026-08-20's run needed about
    three and a half hours and was killed twice before anyone read the cause.
    The cost was never in the arithmetic — it is 19,722 lines a second — but in
    enumerating lines that cannot possibly win.

    The joint factorises along the registry's own axis order: axis k's factor
    depends only on positions already chosen, because `joint_probability` tests
    `parent_pos in chosen.values()`. So this is depth-first with branch and
    bound. A partial assignment is abandoned when its product, times the most
    any unassigned axis could contribute, cannot reach the best complete line
    already found. The bound is admissible, so the argmax cannot be pruned.

    Children are tried in descending order of their own factor, which finds a
    strong incumbent in the first few descents and makes the bound bite. Ties
    are resolved to the line enumeration would have reached first, so this
    returns the same answer as `mainline_enumerate` and not merely an equally
    probable one.
    """
    axes_ = reg["axes"]
    keys = [a["key"] for a in axes_]
    posl = [[q[0] for q in a["positions"]] for a in axes_]
    pris = [{q[0]: q[2] for q in a["positions"]} for a in axes_]
    conds = [reg["conditionals"].get(k, {}) for k in keys]
    rank = [{pos: i for i, pos in enumerate(pl)} for pl in posl]
    bounds = _axis_bounds(reg)
    # tail[d] — the most the axes from d onward can contribute together
    tail = [1.0] * (len(axes_) + 1)
    for d in range(len(axes_) - 1, -1, -1):
        tail[d] = tail[d + 1] * bounds[d]

    best = {"p": -1.0, "combo": None}

    def descend(d, chosen, prod):
        if prod * tail[d] <= best["p"]:
            return
        if d == len(axes_):
            if prod > best["p"]:
                best["p"], best["combo"] = prod, list(chosen)
            return
        w = dict(pris[d])
        for parent_pos, tilts in conds[d].items():
            if parent_pos in chosen:
                for pos, mult in tilts.items():
                    if pos in w:
                        w[pos] *= mult
        tot = sum(w.values())
        # descending factor, then the enumeration's own order, so a tie lands
        # exactly where a full sweep would have left it
        order = sorted(w, key=lambda pos: (-w[pos], rank[d][pos]))
        for pos in order:
            f = w[pos] / tot
            nxt = prod * f
            if nxt * tail[d + 1] <= best["p"]:
                break        # every later child has a factor no larger
            chosen.append(pos)
            descend(d + 1, chosen, nxt)
            chosen.pop()

    import sys as _sys
    lim = _sys.getrecursionlimit()
    _sys.setrecursionlimit(max(lim, 200 + 20 * len(axes_)))
    try:
        descend(0, [], 1.0)
    finally:
        _sys.setrecursionlimit(lim)
    return dict(zip(keys, best["combo"])), best["p"]


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


def trajectory(wl, seed):
    """One path in full: knots, crossings, events, the tracks the events
    moved, and the positions' onsets."""
    kn = capability_path(wl)
    ev = instantiate(wl, kn, seed)
    tr = tracks(wl, kn, ev)
    return {"wl": wl, "knots": [[round(y, 3), round(v, 3)] for y, v in kn],
            "crossings": crossings(kn), "events": ev, "tracks": tr,
            "onsets": onsets(wl, kn, ev, tr)}


def exemplars(reg, k=120, seed=20260731, drawn=None):
    rng = random.Random(seed)
    lines = axes.ensemble(reg, 4000, seed + 1)
    picked = [lines[rng.randrange(len(lines))] for _ in range(k)]
    ml, share = mainline(reg)
    picked[0] = drawn or ml
    out = []
    for i, wl in enumerate(picked):
        t = trajectory(wl, seed + 100 + i)
        t["mainline"] = i == 0
        out.append(t)
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
    # A TEST KEYED TO A LETTER INHERITS WHATEVER THE LETTER LATER MEANS. This
    # asserted that T4 never reaches researcher level, and r5 redefined T4 from
    # "no arrival" to "arrival 2037 to 2050" and moved no-arrival to T5. The
    # assertion then failed for a reason that had nothing to do with the code
    # under test, and nobody saw it because nothing ran this file. It is keyed
    # to the MEASURED thing now: whichever tempo position is the asymptote.
    slow = next(q[0] for q in axes.axis(reg, "T")["positions"]
                if "asymptote" in q[1].lower())
    assert max(v for _, v in capability_path(
        {"T": slow, "A": "A4", "C": "C4"})) < 5.0
    # The same letter defect once more: this read C3 for "the pause", and r5
    # made C3 a declaratory accord that pauses nothing while the binding limit
    # moved to C5. Keyed to the meaning, so a rebuild that renames it fails
    # loudly and a rebuild that merely renumbers it does not.
    hold = next(q[0] for q in axes.axis(reg, "C")["positions"]
                if "limit holds" in q[1].lower())
    knHold = capability_path({"T": "T2", "A": "A3", "C": hold})
    assert abs(cap_at(knHold, 2037.0) - 4.0) < 0.05
    assert cap_at(knHold, 2043.0) > 4.3
    # tracks: laws monotone, revenue positive and capped, approval bounded
    # A HAND-WRITTEN WORLD-LINE GOES STALE THE NEXT TIME AN AXIS IS ADDED. This
    # literal named seven axes; r5 added R, which `tracks` reads, and r7 and r8
    # added two more. It raised KeyError on a file nothing ran. Start from the
    # registry's own modal line, so every axis is present whatever the
    # revision, and override only the positions this test is about.
    wl = {a["key"]: max(a["positions"], key=lambda q: q[2])[0]
          for a in reg["axes"]}
    wl.update({"T": "T2", "A": "A2", "C": "C1", "D": "D2", "S": "S1",
               "P": "P3", "E": "E2"})
    tr = tracks(wl, capability_path(wl))
    assert all(b >= a for a, b in zip(tr["laws"], tr["laws"][1:]))
    assert 0 < max(tr["rev"])
    assert all(8 <= a <= 80 for a in tr["appr"])
    assert len(tr["year"]) == Y1 - Y0 + 1
    assert len(tr["co2"]) == len(tr["year"]) and min(tr["co2"]) > 0
    # M1: K places the coding crossing its gap before the research crossing,
    # and the research crossing is T's and does not move
    # on the T3 tempo (research crossing 2034) every band fits before the
    # crossing; on T2 (2030.2) a seven-year gap cannot, and is clamped
    for kpos, lo, hi in (("K1", 0.0, 1.0), ("K2", 1.0, 2.0),
                         ("K3", 2.0, 5.0), ("K4", 5.0, 99.0)):
        w2 = dict(wl, T="T3", K=kpos, A="A4")
        cr = crossings(capability_path(w2))
        gap = cr["4"] - cr["3"]
        assert lo - 1e-6 <= gap <= hi + 1e-6, (kpos, gap)
        base = crossings(capability_path(dict(wl, T="T3", A="A4")))
        assert abs(cr["4"] - base["4"]) < 1e-6, (kpos, cr, base)
        assert not k_gap_clamped(w2), kpos
    assert k_gap_clamped(dict(wl, T="T2", K="K4", A="A4"))
    assert not k_gap_clamped(dict(wl, T="T2", K="K1", A="A4"))
    # the clamp is counted, and rare: on the registry's own ensemble under a
    # tenth of lines cannot fit K's gap before T's crossing
    ens_k = axes.ensemble(reg, 600, seed=3)
    clamped = sum(1 for w in ens_k if k_gap_clamped(w)) / float(len(ens_k))
    assert clamped < 0.10, clamped
    # M4: no track holds a hard cap. Compute stays under its ceiling and keeps
    # moving with the world's capacity; revenue stays under its share of world
    # output; employment dips and settles rather than falling to a floor;
    # approval stays inside its bounds and converges; copies follow compute.
    for i, y in enumerate(tr["year"]):
        ceil = GW_SHARE_MAX[wl["S"]] * WORLD_GW_2026 * WORLD_GW_GROWTH ** (y - Y0)
        assert tr["gw"][i] <= ceil * 1.001, (y, tr["gw"][i], ceil)
        assert tr["rev"][i] <= REV_SHARE_MAX[wl["D"]] * tr["gwp"][i] * 1.001
        assert -100.0 <= tr["jobs"][i] <= 0.0
    assert tr["gw"][-1] > tr["gw"][-10] > tr["gw"][-30]      # still moving at the horizon
    trough = min(tr["jobs"])
    assert trough < -5.0 and tr["jobs"][-1] > trough + 1.0    # a dip with a settlement
    assert abs(tr["appr"][-1] - tr["appr"][-15]) < 2.0         # converged
    assert tr["laws"][-1] < LAWS_MAX
    assert tr["copies"][-1] > tr["copies"][-30]                # bounded by compute, which moves
    assert all(b >= a for a, b in zip(tr["hz"], tr["hz"][1:]))
    assert abs(horizon_hours(2.6) - 16.0) < 1e-9 and abs(horizon_hours(3.0) - 167.0) < 1e-9
    # M2: an event moves the tracks after it. The same line with its
    # correction removed grows compute faster in the years the correction
    # covers, and the difference is zero before the event.
    kn = capability_path(wl)
    ev = instantiate(wl, kn, 7)
    corr = next((e for e in ev if e["id"] == "bubble-correction"), None)
    assert corr is not None
    with_ev = tracks(wl, kn, ev)
    without = tracks(wl, kn, [e for e in ev if e["id"] != "bubble-correction"])
    yc = int(corr["year"])
    i_c = yc - Y0
    assert with_ev["gw"][i_c + 2] < without["gw"][i_c + 2]
    assert all(a == b for a, b in zip(with_ev["gw"][:max(0, i_c - 1)],
                                      without["gw"][:max(0, i_c - 1)]))
    inc = next((e for e in ev if e["id"] == "agent-incident"), None)
    if inc is not None:
        j = int(inc["year"]) - Y0
        without_inc = tracks(wl, kn, [e for e in ev if e["id"] != "agent-incident"])
        assert with_ev["appr"][j] < without_inc["appr"][j]
    assert all(t["effects"] is not None for t in TEMPLATES)
    assert set(EFFECTS) <= {t["id"] for t in TEMPLATES}, set(EFFECTS) - {t["id"] for t in TEMPLATES}
    # onsets: every rule names a live position and a live template; the
    # modal line dates the positions its rules can date
    live = {q[0] for a in reg["axes"] for q in a["positions"]}
    assert set(axes.ONSETS) <= live, set(axes.ONSETS) - live
    for pos, rule in axes.ONSETS.items():
        if "template" in rule:
            assert rule["template"] in TEMPLATE_BY_ID, (pos, rule)
    on = onsets(wl, kn, ev, with_ev)
    assert "T2" in on and abs(on["T2"] - crossings(kn)["4"]) < 0.11, on
    assert "D2" in on and on["D2"] >= Y0
    # M6: the one-pass medoid is the brute-force medoid
    small = axes.ensemble(reg, 300, seed=11)
    md, agree = medoid(small)
    assert md == medoid_brute(small), (md, medoid_brute(small))
    assert 0.0 < agree <= 1.0
    # track bands ordered
    tb = track_bands(axes.ensemble(reg, 120, seed=13), seed=99)
    for k in TRACK_BAND_KEYS:
        for j in range(len(tb["year"])):
            assert tb[k]["p10"][j] <= tb[k]["p50"][j] <= tb[k]["p90"][j], (k, j)
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
    # derived, not listed — the seven-axis literal here survived r7 and r8
    assert set(ml.keys()) == {a["key"] for a in reg["axes"]}
    assert p_ml > 0
    naive = {a["key"]: max(a["positions"], key=lambda q: q[2])[0]
             for a in reg["axes"]}
    assert p_ml >= joint_probability(reg, naive) - 1e-12
    ml2, p2 = mainline(reg)
    assert ml2 == ml and abs(p2 - p_ml) < 1e-15
    # THE FAST ARGMAX MUST RETURN WHAT ENUMERATION RETURNS, and the same LINE
    # rather than merely one of equal probability: enumeration keeps the first
    # maximum it meets, and a mainline that flips between builds for no visible
    # reason is worse than a slow one. Checked on real prefixes of the live
    # registry, so the priors and the conditionals are the real ones, at sizes
    # a full sweep can still reach.
    keys = [a["key"] for a in reg["axes"]]
    for n in (4, 6, 7):
        sub = copy.deepcopy(reg)
        keep = set(keys[:n])
        sub["axes"] = [a for a in sub["axes"] if a["key"] in keep]
        alive = {q[0] for a in sub["axes"] for q in a["positions"]}
        sub["conditionals"] = {
            k: {pp: {q: m for q, m in t.items() if q in alive}
                for pp, t in v.items() if pp in alive}
            for k, v in sub["conditionals"].items() if k in keep}
        e_line, e_p = mainline_enumerate(sub)
        b_line, b_p = mainline(sub)
        assert e_line == b_line, (n, e_line, b_line)
        assert abs(e_p - b_p) <= 1e-15 * max(1.0, abs(e_p)), (n, e_p, b_p)
    # THE SEED AND WIDENED ARGMAXES MUST AGREE, or a spot-check against
    # axes.REGISTRY is comparing the published line to a different space. On
    # 2026-08-20 they did agree, but the margin does not make that safe:
    # widening moved the top line's probability by 18.6% while first-to-second
    # on the seed registry was 3.8%, so the perturbation is larger than what it
    # has to survive. This costs one 0.5s call and fails on the night the
    # shortcut stops being valid, instead of a future check silently reading
    # the wrong space and concluding the artefact is fine.
    try:
        import forecast_emit
        wts = json.load(open(os.path.join(HERE, "weights.json"))) \
            if os.path.isfile(os.path.join(HERE, "weights.json")) else None
        gpath = os.path.join(HERE, "..", "staged", "forecast", "grounding.json")
        grd = json.load(open(gpath)) if os.path.isfile(gpath) else {}
    except Exception:
        wts = None
    if wts:
        wide = forecast_emit.widened_registry(wts, grd.get("widen", {}))
        assert mainline(wide)[0] == ml, (
            "the seed and widened argmaxes have diverged; a check of a "
            "published LINE against axes.REGISTRY is no longer valid",
            mainline(wide)[0], ml)
    return 8


if __name__ == "__main__":
    n = _selftest()
    print("worldlines.py selftest: %d groups passed" % n)
    import copy
    reg = copy.deepcopy(axes.REGISTRY)
    ml, p_ml = mainline(reg)
    print("mainline (exact argmax, joint p=%.2f%%): %s" %
          (100 * p_ml, " ".join(sorted(ml.values()))))
    kn = capability_path(ml)
    evs = instantiate(ml, kn, 20260731)
    tr = tracks(ml, kn, evs)
    print("mainline capability: 2030=%.2f  2040=%.2f  2060=%.2f  2100=%.2f" %
          (cap_at(kn, 2030), cap_at(kn, 2040), cap_at(kn, 2060),
           cap_at(kn, 2100)))
    for yy in (2035, 2050, 2077, 2100):
        i = yy - Y0
        print("  %d  gw=%.0f  rev=%.1f  gwp=%.0f  jobs=%.1f  appr=%.0f  laws=%d  hz=%.0f" %
              (yy, tr["gw"][i], tr["rev"][i], tr["gwp"][i], tr["jobs"][i],
               tr["appr"][i], tr["laws"][i], tr["hz"][i]))
    print("mainline waypoints (%d):" % len(evs))
    for e in evs[:8]:
        print("  %.0f  [%s]  %s" % (e["year"], e["layer"], e["text"][:70]))
    b = bands(reg, n=4000)
    i2035 = b["year"].index(2035)
    print("2035 capability band: p10=%.1f p50=%.1f p90=%.1f" %
          (b["p10"][i2035], b["p50"][i2035], b["p90"][i2035]))
