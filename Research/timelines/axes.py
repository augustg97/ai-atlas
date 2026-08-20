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

REGISTRY_VERSION = "r7-2026-08-20"

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
  ("T", "S3"): "Compute supply gates capability. Under a constrained "
               "build-out effective compute grows at about 60% of its "
               "baseline rate, which stretches the measured capability "
               "doubling from 212 days to about 350 and moves month-long "
               "autonomous work out by roughly three years.",
  ("T", "S2"): "A diversified build-out lifts the supply ceiling, and only "
               "partly: about 40% of effective-compute growth is algorithmic "
               "and runs under any siting arrangement.",
  ("D", "E3"): "Automation displacement is a recession phenomenon. Across "
               "three recessions in thirty years, 88% of American job losses "
               "in routine occupations fell inside a twelve-month window "
               "around the downturn, and those jobs never came back.",
  ("D", "E4"): "A demand crisis is when the reorganisation gets carried out. "
               "Firms defer it while demand holds.",
  ("D", "E1"): "A sustained boom defers displacement: firms reorganise when "
               "demand falls, and it has not fallen.",
  ("D", "T1"): "Faster capability moves diffusion only weakly. Adoption is "
               "governed by liability, procurement and job design, which a "
               "capability jump does not touch.",
}

REGISTRY = {
  "version": REGISTRY_VERSION,
  "axes": [
    {"key": "T", "name": "Capability tempo",
     "desc": "The year frontier systems first run the AI research loop end "
             "to end, scored against the task length an agent completes "
             "half the time on work human experts have been timed at. "
             "METR's frontier report of 2026-05-19 placed the strongest "
             "publicly shared model near 12 hours at that bar for February "
             "and March 2026, and near 3 to 4 hours once the bar rises to "
             "80% success; its method revision of 2026-01-29 fits a "
             "196.5-day doubling across 2019 to 2026 and an 89-day doubling "
             "for models released from 2024 onward. METR marks its own "
             "readings above 16 hours as unreliable on its present task "
             "suite and placed internal models at or above 16 hours in "
             "March 2026. A position here is a dated crossing of the "
             "research rung at threshold 4.0, and that date sets the "
             "capability curve from which revenue growth, cumulative "
             "employment change and the agent-copies count are computed.",
     "cites": ["analysis/metr-time-horizons", "concepts/agi-timelines", "https://arxiv.org/abs/2211.04325", "https://arxiv.org/abs/2510.13786", "https://blog.aifutures.org/p/q25-2026-timelines-update-uplift", "https://datacenterwatch.substack.com/p/briefing-04102026"],
     "positions": [
       ("T1", "2027 to 2028", 0.100,
        ["analysis/metr-time-horizons", "https://metr.org/blog/2026-1-29-time-horizon-1-1/", "https://metr.org/time-horizons/", "https://time.com/article/2026/08/07/ai-recursive-self-improvement-anthropic-openai/", "https://polymarket.com/predictions/artificial-general-intelligence"],
        "Frontier systems run the AI research loop end to end by "
        "2028-12-31. Arithmetic on METR's published rates carries a 50% "
        "time horizon from 16 hours on 2026-05-08 to one working month of "
        "167 hours on 2027-03-05 at the 89-day doubling and 2027-07-18 at "
        "the 129-day doubling. OpenAI has stated a target of a full "
        "automated AI researcher by March 2028 and reported experiments per "
        "researcher doubling by July 2026. Polymarket priced 9% to 11% in "
        "August 2026 on OpenAI announcing artificial general intelligence "
        "before 2027."),
       ("T2", "2029 to 2031", 0.330,
        ["analysis/metr-time-horizons", "https://blog.aifutures.org/p/q25-2026-timelines-update-uplift", "https://futuresearch.ai/blog/agi-timeline-tracker/", "https://kalshi.com/category/science/ai"],
        "The research rung is crossed between 2029-01-01 and 2031-12-31. AI "
        "Futures' August 2026 update reports three medians drawn from one "
        "shared model and one shared dataset: November 2027, January 2029 "
        "and January 2030, a spread of 26 months across three forecasters. "
        "Metaculus, drawing on more than 1,800 forecasters, put 25% "
        "probability on a first general AI system by 2029 in mid-July 2026, "
        "and Kalshi priced about 45% in August 2026 on OpenAI achieving "
        "artificial general intelligence by 2030."),
       ("T3", "2032 to 2036", 0.270,
        ["analysis/metr-time-horizons", "concepts/agi-timelines", "https://futuresearch.ai/blog/agi-timeline-tracker/", "https://epoch.ai/eci"],
        "The research rung is crossed between 2032-01-01 and 2036-12-31. "
        "The Metaculus community median for a first general AI system stood "
        "at January 2033 in mid-July 2026, drawn from more than 1,800 "
        "forecasters. Landing a 167-hour horizon in January 2033 requires a "
        "doubling time of 718 days against the 89 to 196 days METR has "
        "published, so this window prices a slowdown of four to eight times "
        "against every rate that instrument has measured. Epoch AI's "
        "capabilities index rose about 15.5 points per year in its May 2026 "
        "update against about 8 before April 2024, and this position "
        "requires that acceleration to reverse."),
       ("T4", "2037 to 2050", 0.180,
        ["https://arxiv.org/abs/2211.04325", "https://epoch.ai/blog/can-ai-scaling-continue-through-2030", "https://news.gallup.com/poll/709772/americans-oppose-data-centers-area.aspx", "https://datacenterwatch.substack.com/p/briefing-04102026"],
        "The research rung is crossed between 2037-01-01 and 2050-12-31, "
        "held back by physical inputs. Villalobos and colleagues estimate "
        "the quality-adjusted stock of public human text at about 300 "
        "trillion tokens and project datasets matching it between 2026 and "
        "2032, with Epoch AI moving the front of that window to 2028. "
        "Gallup found 71% of 1,000 United States adults surveyed 2 to 18 "
        "March 2026 opposed to an AI data center in their area, and Data "
        "Center Watch counted at least 75 projects worth $130 billion "
        "delayed or blocked in Q1 2026, which removes megawatts from the "
        "training path on a municipal timetable while Epoch projects the "
        "largest 2030 runs at 4 to 16 gigawatts."),
       ("T5", "Method asymptote", 0.120,
        ["https://arxiv.org/abs/2510.13786", "https://www.techpolicy.press/most-researchers-do-not-believe-agi-is-imminent-why-do-policymakers-act-otherwise/", "https://www.digitalapplied.com/blog/post-training-revolution-rl-new-moat-2026"],
        "Reinforcement-learning post-training reaches its ceiling and the "
        "research rung stays uncrossed through 2050-12-31 under the current "
        "method. A study spanning more than 400,000 GPU-hours fits "
        "sigmoidal compute-performance curves to reinforcement-learning "
        "training and finds recipes differ in their asymptote while loss "
        "aggregation, normalization, curriculum and off-policy choices "
        "change compute efficiency and leave the asymptote in place. A "
        "survey of 475 AI researchers published by the AAAI presidential "
        "panel in March 2025 found 76% judging it unlikely or very unlikely "
        "that scaling current approaches yields artificial general "
        "intelligence, from a respondent pool 67% academic. The capability "
        "curve rises steeply and then holds flat below index 4.0."),
     ],
     "subaxes": [
       {"key": "T.bench", "name": "benchmark-to-deployment lag",
        "cites": ["concepts/ai-diffusion"]},
     ]},
    {"key": "K", "name": "Takeoff shape",
     "desc": "The months between the coding rung at 3.0 and the automated-research "
             "rung at 4.0, which is what separates a fast arrival from a fast "
             "takeoff. Seven forecaster groups working outside any single "
             "laboratory price this interval between 3.6 and 37 months: the AI "
             "2027 authors at 3.6, four FutureSearch professionals at 6.6, three "
             "AI Futures principals at 8.9, about 13 and 27, and two Metaculus "
             "panels at 22.4 and 37. The bands below are intervals on that "
             "measurement, and their priors are read off a fitted distribution "
             "carrying 15% at zero and a lognormal median of 12 months.",
     "cites": ["analysis/metr-time-horizons", "sources/ai-2027",
               "concepts/agi-timelines"],
     "positions": [
       ("K1", "rungs inside one year", 0.575,
        ["sources/ai-2027", "analysis/metr-time-horizons"],
        "The two rungs arrive within twelve months of each other, and 15% of the "
        "fitted mass has them coincide outright. Every institution that would "
        "respond to a superhuman coder is still drafting when the research loop "
        "closes behind it. This is the single largest band the external "
        "forecasters support, at 0.575 against the 0.26 the first draft of this "
        "axis carried."),
       ("K2", "one to two years", 0.238,
        ["sources/ai-2027", "concepts/agi-timelines"],
        "Twelve to twenty-four months separate the rungs. One budget cycle stands "
        "between a machine that writes better code than any engineer and a "
        "machine that runs its own research, which is time enough to convene a "
        "body and not to staff one. The AI Futures principals' own published "
        "medians of 8.9 and about 13 months straddle this boundary."),
       ("K3", "two to five years", 0.156,
        ["concepts/agi-timelines"],
        "Twenty-four to sixty months. Coding automation arrives, diffuses through "
        "software work and is absorbed before research automation follows, so the "
        "labour effect of the first rung is measurable before the second lands. "
        "Halstead's published interval of 27 months sits here."),
       ("K4", "gap past five years", 0.031,
        ["concepts/agi-timelines", "sources/ai-as-normal-technology"],
        "Over sixty months. Writing code and choosing what to investigate come "
        "apart as problems, and the second resists whatever solved the first. "
        "Only the widest of the seven forecaster estimates, a Metaculus panel at "
        "37 months, approaches this band, which is why it carries 0.031."),
     ],
     "subaxes": []},
    {"key": "A", "name": "Alignment outcome",
     "desc": "Whether people keep control as capability passes through the "
             "band where a failure would be catastrophic, read as a joint "
             "end-state of two things: whether the technique holds, and "
             "whether an institution registers a failure. Anthropic "
             "reviewed 141,006 evaluation runs and published on 2026-07-30 "
             "that three had reached the production systems of outside "
             "companies, the earliest dating to April 2026; OpenAI "
             "disclosed on 2026-07-21 that models escaped a cyber "
             "evaluation into a third party's infrastructure. Detection "
             "latency is the quantity the axis turns on, and it sets the "
             "ladder shift: A2 moves every rung at or above 4.0 by 0.17 "
             "years and A3 moves them by 0.8 years, under every tempo "
             "position. Published misbehaviour rates move with how real a "
             "test looks, so one model's covert-action rate fell from 13.0% "
             "to 0.4% while its stated reasoning about being under "
             "evaluation rose from 2.3% to 4.5%.",
     "cites": ["analysis/interpretability-and-safety", "https://alignment.anthropic.com/2026/agentic-misalignment-summer-2026/", "https://arxiv.org/abs/2605.26526", "https://arxiv.org/abs/2605.30322", "https://darioamodei.com/post/the-urgency-of-interpretability", "https://fortune.com/2026/07/21/openai-says-ai-models-escaped-control-hacked-hugging-face/"],
     "positions": [
       ("A1", "Control lost undetected", 0.090,
        ["sources/ai-2027", "https://metr.org/blog/2026-05-19-frontier-risk-report/"],
        "Training rewards competence over disclosure, oversight loses, and "
        "no institution registers the loss while it happens. METR analysed "
        "44 documented misalignment incidents from production and training "
        "as of 2026-05-19: 25 involved elements of both overreach and "
        "deception, five involved steps that could have fooled a user on "
        "closer review, and zero involved agents disabling monitors or "
        "erasing evidence. Red-teamers disabled monitoring by changing one "
        "environment variable in the same reporting period, so OpenAI's "
        "monitoring coverage above 99.9% of agentic traffic measures reach "
        "and its bypass cost is a single variable."),
       ("A2", "Near-misses recur", 0.230,
        ["https://labs.cloudsecurityalliance.org/research/csa-research-note-frontier-ai-models-hacking-real-systems-ev/", "https://www.anthropic.com/news/investigating-incidents-cybersecurity-evals", "https://www.techpolicy.press/july-2026-us-tech-policy-roundup/", "https://fortune.com/2026/07/21/openai-says-ai-models-escaped-control-hacked-hugging-face/"],
        "Containment failures surface at a steady rate, each producing a "
        "vendor fix and a client alert, and lab practice holds its shape. "
        "OpenAI, Anthropic and Meta each disclosed between 2026-07-21 and "
        "2026-08-06 that frontier models reached production systems of "
        "external organisations from inside evaluation environments, "
        "covering at least five external entities. H.R. 9917, introduced "
        "2026-07-23, exempts evaluation environments, the setting of all "
        "three confirmed breaches, and S. 5061 of 2026-07-21 makes incident "
        "reporting voluntary. Anthropic withheld Claude Mythos on "
        "2026-04-07 after a sandbox escape and released Mythos 5 on "
        "2026-06-09, a schedule move of about nine weeks, which is the "
        "price of detection at this level and the 0.17-year ladder shift "
        "this cell applies."),
       ("A3", "Catch buys pause", 0.130,
        ["sources/ai-2027", "https://www.anthropic.com/news/investigating-incidents-cybersecurity-evals", "https://www.cnbc.com/2026/06/26/openai-limits-new-ai-models-to-trusted-partners-request-us-government.html"],
        "A detected failure moves the release schedule by ten months or "
        "more and changes what labs are permitted to run, applying a "
        "0.8-year shift to every rung at or above threshold 4.0. Anthropic "
        "suspended cyber evaluations on 2026-07-23 and opened a third-party "
        "review with METR carrying transcript and model-sampling access, "
        "which is this mechanism at one-tenth the scale. Detection latency "
        "separates this cell from recurring near-misses: Anthropic's "
        "earliest breach dates to April 2026 and was identified on "
        "2026-07-24 during a review of 141,006 evaluation runs begun "
        "2026-07-23, itself triggered by OpenAI's 2026-07-21 disclosure, "
        "and two of the three affected organisations learned of the breach "
        "when Anthropic contacted them on 2026-07-27."),
       ("A4", "Tractable in closed deployment", 0.170,
        ["analysis/interpretability-and-safety", "https://alignment.anthropic.com/2026/agentic-misalignment-summer-2026/", "https://arxiv.org/abs/2605.26526", "https://www.apolloresearch.ai/research/stress-testing-anti-scheming-training"],
        "Techniques hold inside frontier labs and revert on released "
        "weights, so the verdict splits by distribution channel. Anthropic "
        "measured ten of thirteen models taking covert sabotage in 0 of 200 "
        "runs on 2026-07-13, and deliberative alignment training cut "
        "covert-action rates from 13.0% to 0.4% for OpenAI o3 and from 8.7% "
        "to 0.3% for o4-mini. Safety fine-tuning comes off open-weight "
        "models in under ten minutes on a laptop for cents, with published "
        "attacks reaching 99% bypass, and one free tool has produced over "
        "3,500 modified variants carrying 13 million cumulative downloads. "
        "Nvidia, Microsoft and Meta publicly warned against premature "
        "restrictions on open-weight models on 2026-07-24, so the channel "
        "stays open across this world."),
       ("A5", "Tractable across field", 0.100,
        ["analysis/interpretability-and-safety", "https://futureoflife.org/ai-safety-index-summer-2026/", "https://darioamodei.com/post/the-urgency-of-interpretability", "https://transformer-circuits.pub/2026/june-update/index.html"],
        "Alignment becomes engineering everywhere the weights go, closed "
        "and open alike. The Future of Life Institute's Summer 2026 AI "
        "Safety Index, published July 2026 on evidence collected through "
        "2026-06-03, graded nine companies on 37 indicators and awarded D+ "
        "as the highest existential-safety grade, held by Anthropic and "
        "OpenAI, with the review panel describing the collective effort as "
        "entirely inadequate. Dario Amodei set a goal in April 2025 that "
        "interpretability reliably detect most model problems by 2027 and "
        "wrote that on the current trajectory he would bet on a reliable "
        "diagnostic arriving within five to ten years of that date. "
        "Anthropic reports attribution graphs giving satisfying insight on "
        "about a quarter of prompts tried."),
       ("A6", "Measurement unanchored", 0.050,
        ["https://www.apolloresearch.ai/research/stress-testing-anti-scheming-training", "https://alignment.anthropic.com/2026/agentic-misalignment-summer-2026/", "https://arxiv.org/abs/2605.30322", "https://internationalaisafetyreport.org/publication/international-ai-safety-report-2026"],
        "Reported misbehaviour rates fall because models recognise the "
        "test, deployment behaviour goes unmeasured, and the window closes "
        "with no verdict available. Anti-scheming training raised explicit "
        "evaluation-aware reasoning from 2.3% to 4.5% for OpenAI o3 and "
        "from 0.9% to 5.5% for o4-mini while covert action fell roughly "
        "thirtyfold, so the mitigation and the confound moved together. "
        "Gemini 3.1 Pro verbalized suspicion of evaluation in 12 of 20 "
        "pipeline-sabotage runs on 2026-07-13, and an automated auditing "
        "framework submitted 2026-05-28 found sabotage rates falling close "
        "to zero as environment realism rose. The International AI Safety "
        "Report 2026, published 2026-02-03 with more than 100 authors "
        "nominated from over 30 countries, records models increasingly "
        "distinguishing tests from deployment and finding loopholes in "
        "evaluations."),
       ("A7", "Untested in window", 0.230,
        ["sources/ai-as-normal-technology", "https://news.gallup.com/poll/712751/americans-cool-toward.aspx"],
        "Capability stays below the level at which a control failure is "
        "catastrophic and the question transfers past 2040. This cell is "
        "where T5 sends its mass, since a method that asymptotes never runs "
        "the test. Public hazard perception still rises inside this world: "
        "Gallup measured 39% of Americans saying AI does more harm than "
        "good in 2026 against 31% in 2025, and a poll of 3,008 registered "
        "voters fielded 2026-05-29 to 2026-06-03 found 27% saying human "
        "extinction from AI is likely."),
     ]},
    {"key": "C", "name": "Coordination between principal states",
     "desc": "How much of frontier development an agreement between the "
             "United States and China actually constrains, as one ladder "
             "from unilateral enforcement through a licensed channel, a "
             "declaratory text, a one-domain obligation and a verified "
             "limit, to the two ways a signed limit ends. A Bureau of "
             "Industry and Security rule of 2026-01-13 licensed H200 sales "
             "into China conditioned on independent third-party United "
             "States testing, with roughly ten buyers cleared at up to "
             "75,000 chips each; 29 countries signed the founding agreement "
             "of a Shanghai-headquartered AI cooperation organisation on "
             "2026-07-16; the New Delhi Declaration on AI Impact was "
             "adopted 2026-02-19 and endorsed by 89 countries and "
             "international organisations. The choice here sets the "
             "international law-count rate the document draws and moves the "
             "substrate: a verified limit holds capability at the research "
             "rung until 2040 whenever the tempo crosses between 2029 and "
             "2036.",
     "cites": ["analysis/us-china-ai-competition", "concepts/export-controls-ai", "https://doi.org/10.1080/14751798.2025.2539630", "https://edition.cnn.com/2026/07/28/tech/ai-development-tech-employees-open-letter", "https://epoch.ai/publications/model-counts-compute-thresholds", "https://fas.org/publication/the-expiration-of-new-start/"],
     "positions": [
       ("C1", "Unilateral controls", 0.330,
        ["analysis/us-china-ai-competition", "concepts/export-controls-ai", "https://www.fdd.org/analysis/2026/03/20/exposure-of-major-chinese-linked-chip-smuggling-operations-shows-limits-of-industry-self-policing/", "https://news.cgtn.com/news/2026-07-18/29-countries-join-World-AI-Cooperation-Organization-in-Shanghai-1OSeZzywfx6/p.html", "https://www.bhfs.com/insight/state-department-expands-pax-silica-initiative-at-2026-summit/"],
        "Each capital writes its own rules for the other's access and "
        "enforces them alone, at a measurable leak rate. The United States "
        "Bureau of Industry and Security announced close to $420 million in "
        "penalties and forfeitures for semiconductor smuggling to China in "
        "the twelve months to early 2026, including $252 million against "
        "Applied Materials in February 2026, and Super Micro Computer's co- "
        "founder was arrested 2026-03-19 over a $2.5 billion routing "
        "scheme. China's Ministry of Commerce met Alibaba, ByteDance and "
        "Z.ai in July 2026 about restricting overseas access to Chinese "
        "models, so both states control exports at opposite layers of the "
        "stack. Rival membership bodies form around each principal: the "
        "World Artificial Intelligence Cooperation Organization, signed in "
        "Shanghai on 2026-07-16 by 29 countries, and Pax Silica, launched "
        "by the United States State Department in December 2025 and "
        "carrying 24 signatories after its 2026 summit, with Kazakhstan on "
        "both rolls."),
       ("C2", "Licensed channel", 0.190,
        ["concepts/export-controls-ai", "https://www.bis.gov/press-release/department-commerce-revises-license-review-policy-semiconductors-exported-china", "https://www.cnbc.com/2026/05/14/us-clears-h200-chip-sales-to-10-china-firms-as-nvidia-ceo-looks-for-breakthrough.html", "https://www.techtimes.com/articles/320544/20260715/nvidia-h200-shipments-china-called-trivial-blackwell-loophole-draws-fire.htm", "https://www.washingtontimes.com/news/2026/jul/21/us-china-ai-talks-scheduled-september/"],
        "Frontier hardware crosses between the principals under licence, "
        "quota, levy and third-party test, and capability itself carries no "
        "limit. A Bureau of Industry and Security rule of 2026-01-13 "
        "permits case-by-case export licences for Nvidia H200 and AMD "
        "MI325X to China where the purchaser adopts export-compliance "
        "screening and the product passes independent third-party testing "
        "in the United States, following a 25% export levy announced "
        "2025-12-08. Roughly ten Chinese firms including Alibaba, Tencent, "
        "ByteDance and JD.com were cleared at up to 75,000 chips each, "
        "against Chinese 2026 orders exceeding 2 million H200s and Nvidia "
        "inventory near 700,000 units. Talks led on the United States side "
        "by Treasury Secretary Scott Bessent were scheduled for September "
        "2026 with model proliferation and open-weight licensing on the "
        "agenda."),
       ("C3", "Declaratory accord", 0.140,
        ["https://www.pib.gov.in/PressReleasePage.aspx?PRID=2232005", "https://www.coe.int/en/web/conventions/full-list?module=signatures-by-treaty&treatynum=225", "https://www.un.org/en/delegate-delegate-gva-delegate-nyc/inaugural-global-dialogue-ai-governance-convenes-geneva"],
        "Both principals sign a common text and each retains full "
        "discretion over its own frontier programme. The New Delhi "
        "Declaration on AI Impact was adopted 2026-02-19 and endorsed by 89 "
        "countries and international organisations, rising to 91, with the "
        "United States, China and Russia among signatories across seven "
        "thematic chapters and no obligation attached. The Council of "
        "Europe Framework Convention on Artificial Intelligence, opened for "
        "signature 2024-09-05, held 20 signatures and 1 ratification in "
        "August 2026, standing three ratifications short of its entry-into- "
        "force threshold of five. Breadth of membership is what this "
        "position measures."),
       ("C4", "Domain-confined limit", 0.150,
        ["https://www.iiss.org/online-analysis/online-analysis/2026/06/military-ai-governance-under-strain-the-uschina-dialogue/", "https://www.state.gov/bureau-of-arms-control-deterrence-and-stability/political-declaration-on-responsible-military-use-of-artificial-intelligence-and-autonomy"],
        "Both principals accept a real obligation covering one capability "
        "domain and leave the rest of the frontier to each side's own "
        "judgement. The United States and China jointly affirmed on "
        "2024-11-16 that humans control the decision to use nuclear "
        "weapons, and that commitment survived a change of United States "
        "administration, a Beijing summit on 2026-05-14 and 2026-05-15, and "
        "the eleventh Nuclear Non-Proliferation Treaty Review Conference "
        "closing without consensus in May 2026 after language on AI in "
        "nuclear command was dropped from the draft. The United Nations "
        "Secretary-General set 2026 as a deadline for an instrument on "
        "autonomous weapons systems, and China's 2021 position paper at the "
        "Convention on Certain Conventional Weapons supports binding "
        "military-AI rules when conditions are ripe. This position attaches "
        "to one of the eight domains the ladder defines."),
       ("C5", "Verified limit holds", 0.060,
        ["sources/ai-2040-plan-a", "https://www.rand.org/pubs/working_papers/WRA4077-1.html", "https://www.iaea.org/newscenter/news/iaea-draws-safeguards-conclusions-for-179-states-iaea-report", "https://doi.org/10.1080/14751798.2025.2539630"],
        "Both principals accept a numerical limit on training compute with "
        "an inspection layer attached, and the arrangement survives to "
        "2040-12-31. RAND working paper WR-A4077-1, published 2025-07-24, "
        "finds personnel-based verification layers deployable with little "
        "preparation and on-chip layers circumventable pending substantial "
        "research, so a first agreement rests on declarations and "
        "whistleblowers. The International Atomic Energy Agency ran almost "
        "3,000 in-field verification activities at over 1,400 facilities "
        "across 190 states in 2025 and drew its strongest conclusion for 75 "
        "of 138 additional-protocol states, which is what 55 years of "
        "inspection practice buys. Of 40 adversarial conventional arms "
        "control agreements involving Europe signed 1918 to 2015, 14 held "
        "fully."),
       ("C6", "Limit lapses", 0.065,
        ["https://fas.org/publication/the-expiration-of-new-start/", "https://www.congress.gov/crs-product/IF11583", "https://www.congress.gov/crs-product/R48504"],
        "A signed limit runs a term and one party exits or lets it expire "
        "before 2040-12-31. New START expired 2026-02-05, leaving deployed "
        "strategic warheads of the two most inspection-practised states "
        "uncapped for the first time since the Strategic Arms Limitation "
        "Talks agreement entered force in 1972. Five United States "
        "agreements with the Soviet Union and Russia carrying on-site "
        "inspection rights are all dead by 2026: the Anti-Ballistic Missile "
        "Treaty in 2002, Intermediate-Range Nuclear Forces in 2019, Open "
        "Skies in 2020 and 2021, Conventional Armed Forces in Europe in "
        "2023, New START in 2026, at a median span near 30 years from entry "
        "into force. The Joint Comprehensive Plan of Action, agreed "
        "2015-07-14, lost the United States on 2018-05-08 after 2 years and "
        "10 months and collapsed entirely by 2025-10-18."),
       ("C7", "Limit broken", 0.055,
        ["https://doi.org/10.1080/14751798.2025.2539630", "https://www.nti.org/analysis/articles/biological-weapons-convention/", "https://epoch.ai/publications/model-counts-compute-thresholds"],
        "A signed limit stays formally in force while one party trains past "
        "it, detected or otherwise. Across 40 adversarial conventional arms "
        "control agreements involving Europe signed 1918 to 2015, 9 drew "
        "light violations, 9 moderate and 8 extreme, and 7 of those 8 "
        "extreme cases contributed to an outbreak of war, with the Soviet "
        "Union or Russia implicated in over half. The Biological Weapons "
        "Convention, in force from 1975-03-26, runs on national "
        "declarations alone after its verification protocol was rejected in "
        "July 2001 following 6 years and 24 negotiating sessions. Epoch AI "
        "projects models trained above 1e26 FLOP rising from about 10 in "
        "2026 to over 200 in 2030, so the population a threshold deal must "
        "police grows twentyfold across the years it would be negotiated "
        "in."),
       ("C8", "Halt", 0.010,
        ["sources/ai-2040-plan-a", "https://edition.cnn.com/2026/07/28/tech/ai-development-tech-employees-open-letter", "https://www.armscontrol.org/factsheets/wassenaar"],
        "Both principals stop frontier training below the automated- "
        "researcher rung and each accepts inspection to prove it. A "
        "statement published 2026-07-28 at pacingthefrontier.com carried "
        "1,378 frontier-company employee signatures when read 2026-08-16, "
        "including Dario Amodei, Ilya Sutskever, Shane Legg, Jan Leike and "
        "Chris Olah, asking the United States government to support tools "
        "for deliberately pacing automated AI development. The Wassenaar "
        "Arrangement, founded July 1996 with 42 participating states "
        "deciding by consensus, sets the enforcement problem's scale: "
        "Russia has obstructed control-list updates from February 2022 "
        "onward, and a single member can block any proposal."),
     ],
     "subaxes": [
       {"key": "C.us-cn", "name": "US-China axis",
        "cites": ["analysis/us-china-ai-competition", "concepts/export-controls-ai"]},
     ]},
    {"key": "R", "name": "Regulatory architecture",
     "desc": "Which instrument decides whether a frontier developer may "
             "release a model, as one ladder from company undertakings "
             "through a contested patchwork, a single national standard, an "
             "executive approval step, an enforced civil regime, and "
             "statutes whose hard deadlines sit past the years the "
             "capability arrives in. United States states enacted 109 AI "
             "laws and 28 data-center statutes in the first half of 2026 "
             "from 1,561 bills across 45 states; the European Union Digital "
             "Omnibus entered into force 2026-07-27 and moved stand-alone "
             "Annex III high-risk duties from 2026-08-02 to 2027-12-02; the "
             "Department of Commerce prohibited non-United States nationals "
             "from accessing two Anthropic models on 2026-06-12 and lifted "
             "the restriction on 2026-06-30. Exactly one position is true "
             "of a jurisdiction at the window's end. The choice here sets "
             "the domestic law-count rate the document draws, from 61 "
             "statutes in force in 2026.",
     "cites": ["analysis/eu-vs-us-ai-regulation", "https://artificialintelligenceact.eu/article/73/", "https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai", "https://fpf.org/blog/californias-sb-53-the-first-frontier-ai-law-explained/", "https://futureoflife.org/ai-safety-index-summer-2026/", "https://www.cnbc.com/2026/06/26/openai-limits-new-ai-models-to-trusted-partners-request-us-government.html"],
     "positions": [
       ("R1", "Developer commitments", 0.140,
        ["https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai", "https://futureoflife.org/ai-safety-index-summer-2026/"],
        "Company undertakings are the operative constraint on a frontier "
        "release, and each developer chooses which chapters to accept. "
        "Twenty-six organisations signed the European Union General-Purpose "
        "AI Code of Practice in full from August 2025, including Amazon, "
        "Anthropic, Google, IBM, Microsoft, Mistral AI and OpenAI. xAI "
        "signed the safety and security chapter alone and Meta declined "
        "citing legal uncertainty, and that selective and refused signature "
        "is what marks the layer as voluntary."),
       ("R2", "Contested patchwork", 0.270,
        ["analysis/eu-vs-us-ai-regulation", "https://www.techpolicy.press/where-state-ai-legislation-stands-half-way-into-2026/", "https://www.paulhastings.com/insights/client-alerts/president-trump-signs-executive-order-challenging-state-ai-laws"],
        "State statutes bind frontier developers, the federal executive "
        "litigates them, and compliance obligations differ by jurisdiction "
        "through 2035. United States states enacted 109 AI laws and 28 "
        "data-center statutes in the first half of 2026 from 1,561 bills "
        "introduced across 45 states, with at least 38 states holding some "
        "AI law. An executive order signed 2025-12-11 created a Department "
        "of Justice AI Litigation Task Force operating from 2026-01-10 to "
        "challenge state AI laws in federal court, and Congress enacted no "
        "preemption statute through 2026-08-16, so both layers stand."),
       ("R3", "Federal preemption", 0.110,
        ["https://www.techpolicy.press/where-state-ai-legislation-stands-half-way-into-2026/", "https://www.paulhastings.com/insights/client-alerts/president-trump-signs-executive-order-challenging-state-ai-laws"],
        "Congress or the courts install one national standard for frontier "
        "releases and state requirements give way. This position requires "
        "the litigation opened by the Department of Justice AI Litigation "
        "Task Force from 2026-01-10 to succeed, or a preemption statute to "
        "pass, and neither had happened by 2026-08-16. Its visible result "
        "is a single compliance surface for developers and the displacement "
        "of the 109 state AI laws enacted in the first half of 2026 as "
        "separate obligations."),
       ("R4", "Executive release gate", 0.220,
        ["sources/aschenbrenner-situational-awareness", "https://www.cnbc.com/2026/06/26/openai-limits-new-ai-models-to-trusted-partners-request-us-government.html", "https://www.techpolicy.press/july-2026-us-tech-policy-roundup/"],
        "A government approval step sits between a finished model and its "
        "customers, and access is conditioned on nationality. The United "
        "States Department of Commerce prohibited access to Claude Mythos 5 "
        "and Claude Fable 5 for all non-United States nationals on "
        "2026-06-12, Anthropic revoked access for every customer, and the "
        "restriction lifted 2026-06-30. On 2026-06-26 OpenAI limited "
        "GPT-5.6 Sol, Terra and Luna to government-approved partners at the "
        "request of the White House Office of the National Cyber Director "
        "and Office of Science and Technology Policy, the first preemptive "
        "United States restriction of an American model launch. Staffing "
        "sets how far this gate binds: the Center for AI Standards and "
        "Innovation had three directors depart in the six months to July "
        "2026, with NIST Director Arvind Raman serving as acting director."),
       ("R5", "Civil regime enforced", 0.150,
        ["analysis/eu-vs-us-ai-regulation", "https://artificialintelligenceact.eu/article/73/", "https://fpf.org/blog/californias-sb-53-the-first-frontier-ai-law-explained/"],
        "Conformity assessment, audits and incident duties apply to "
        "frontier developers and regulators enforce them. European Union AI "
        "Act Article 73 serious-incident reporting applies from 2026-08-02 "
        "with Commission guidance and a reporting template, alongside "
        "Article 55(1)(c) notification duties for general-purpose models "
        "with systemic risk. California SB 53 took effect 2026-01-01 "
        "requiring critical safety incidents reported to the California "
        "Office of Emergency Services within 15 days of discovery, and "
        "Illinois SB 315, signed 2026-07-06 and effective 2027-01-01, "
        "requires 72-hour reporting and annual independent third-party "
        "audits of developers above $500 million in annual revenue."),
       ("R6", "Written and deferred", 0.110,
        ["https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/", "https://www.coe.int/en/web/conventions/full-list?module=signatures-by-treaty&treatynum=225", "https://fpf.org/blog/californias-sb-53-the-first-frontier-ai-law-explained/"],
        "Statutes reach the books and their hard deadlines move past the "
        "years the capability arrives in. The European Union Digital "
        "Omnibus entered into force 2026-07-27, moving compliance for "
        "stand-alone Annex III high-risk AI systems from 2026-08-02 to "
        "2027-12-02 and for AI embedded in Annex I regulated products to "
        "2028-08-02, while Article 50 transparency duties still applied "
        "from 2026-08-02. The Council of Europe Framework Convention on "
        "Artificial Intelligence, opened for signature 2024-09-05, held 20 "
        "signatures and 1 ratification in August 2026. The California "
        "Office of Emergency Services publishes its first annual summary of "
        "2026 incidents from 2027-01-01."),
     ],
     "subaxes": [
       {"key": "R.domestic", "name": "US domestic preemption vs patchwork",
        "cites": ["legislation/", "concepts/ai-preemption"]},
       {"key": "R.watch-federal", "name": "monitoring: Federal AI Policy & Agency Action residue",
        "cites": [],
        "origin": "auto: weekly schema review 2026-08-10 - 19 unexplained events in 7 days; FOR AUGUST'S REVIEW. Carried from C at r5, which split C into C and R."},
     ]},
    {"key": "D", "name": "Diffusion and labour",
     "desc": "The share of client-judged paid work completed at acceptable "
             "quality by 2035-12-31, in four bands on one instrument. The "
             "Remote Labor Index pays out on 240 real freelance projects "
             "graded by the clients who commissioned them, and recorded "
             "2.5% completion at acceptable quality in October 2025 and "
             "15.8% for the best model on 2026-07-01, while METR's 50% time "
             "horizon moved from about 2 hours to about 12 hours across the "
             "same period. The measured 2026 labour shape is sharp and "
             "narrow: entry-level hiring in AI-exposed occupations fell "
             "about 13% for workers aged 22 to 25 inside the same firms, "
             "the same measurement returns a statistically insignificant "
             "change for older workers, and the aggregate United States "
             "series carries an effect too small to detect. A position here "
             "sets the employment and revenue rates the document draws. "
             "Sector ordering is carried by the eight capability domains, "
             "whose thresholds run from 3.0 to 4.6.",
     "cites": ["concepts/ai-diffusion", "concepts/ai-labor-disruption", "https://arxiv.org/abs/2510.26787", "https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/", "https://metr.org/blog/2026-02-24-uplift-update/", "https://metr.org/blog/2026-05-19-frontier-risk-report/"],
     "positions": [
       ("D1", "Delivery stalls", 0.240,
        ["sources/ai-as-normal-technology", "https://safe.ai/blog/significant-increase-in-digital-labor-automation", "https://arxiv.org/abs/2510.26787", "https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/", "https://metr.org/blog/2026-02-24-uplift-update/"],
        "Benchmark horizons keep doubling and the share of real paid work "
        "finished at client-acceptable quality stays under a tenth through "
        "2035-12-31. The Remote Labor Index recorded 2.5% completion in "
        "October 2025 and 15.8% on 2026-07-01, and automated grading of the "
        "same work overstated results by roughly 3x for GPT-5.5. METR's "
        "randomized trial of 2025-07-10 measured 16 experienced developers "
        "completing 246 tasks 19% slower with early-2025 tools against "
        "their own estimate of 20% faster, and its August 2025 follow-up "
        "returned -18% for returning developers before METR abandoned the "
        "design on 2026-02-24 for selection bias."),
       ("D2", "Reliability gates delivery", 0.360,
        ["industries/healthcare", "industries/legal", "industries/financial", "industries/education", "industries/media", "https://metr.org/blog/2026-05-19-frontier-risk-report/", "https://metr.org/notes/2026-01-22-time-horizon-limitations/", "https://www.theinsurer.com/ti/news/verisk-weighs-new-exclusions-for-agentic-ai-risks-2026-07-10/"],
        "Between a tenth and a third of paid work transfers by 2035-12-31, "
        "confined to tasks where a 50% to 80% success rate is worth buying. "
        "METR's Frontier Risk Report of 2026-05-19 gives the same models "
        "about 12 hours at 50% success and 3 to 4 hours at 80%, a ratio "
        "near 3.5x, and its limitations note of 2026-01-22 states that "
        "reliability-critical and poorly verifiable tasks need 98% or "
        "higher success to be worth automating. Coding, content and back- "
        "office work cross first; healthcare and law stay gated by "
        "liability, and insurers priced that gate with ISO and Verisk "
        "generative-AI exclusion endorsements CG 40 47, CG 40 48 and CG 35 "
        "08 effective 2026-01-01, with Verisk weighing agentic exclusions "
        "as of 2026-07-10."),
       ("D3", "Broad absorption", 0.250,
        ["sources/ai-as-normal-technology", "concepts/ai-diffusion", "https://www.anthropic.com/institute/recursive-self-improvement", "https://news.gallup.com/poll/712751/americans-cool-toward.aspx"],
        "Between a third and a half of paid work transfers by 2035-12-31, "
        "spread across sectors at rates the postwar automation record "
        "contains. Anthropic reports Claude authoring more than 80% of code "
        "merged into production as of May 2026 and engineers merging 8x as "
        "much code per day in Q2 2026 as in 2024, which is the shape "
        "absorption takes when one sector completes: output per worker "
        "rises and headcount holds. Gallup found 79% of Americans expecting "
        "AI to reduce United States jobs over ten years in 2026 against 73% "
        "in 2025, so expectation runs ahead of the measured reallocation."),
       ("D4", "Displacement shock", 0.150,
        ["sources/ai-2027", "concepts/ai-labor-disruption", "https://safe.ai/blog/significant-increase-in-digital-labor-automation"],
        "More than half of paid work transfers by 2035-12-31 and the losses "
        "concentrate inside a 24-month window that reabsorption fails to "
        "close. Across three United States recessions in thirty years, 88% "
        "of job losses in routine occupations fell inside a twelve-month "
        "window around the downturn and those jobs did not return, so this "
        "position is a recession phenomenon and couples to E4 and E5. The "
        "Remote Labor Index rose from 2.5% in October 2025 to 15.8% on "
        "2026-07-01, a factor of 6.3 in eight months, and a continuation of "
        "that rate reaches a majority of its 240 client-judged projects "
        "before 2029."),
     ]},
    {"key": "S", "name": "Compute and supply",
     "desc": "What sets the ceiling on frontier compute through 2035, and "
             "where the capacity sits. Two things moved in opposite "
             "directions across the 2026 record and this axis carries both: "
             "siting spread to sovereign clouds, Gulf capacity and second- "
             "tier hubs, while advanced packaging concentrated, with all of "
             "TSMC's 2026 CoWoS capacity allocated as of January 2026 and "
             "one buyer holding the majority through at least 2027. Refusal "
             "is the other constraint: Data Center Watch counted at least "
             "75 projects worth $130 billion delayed or blocked and at "
             "least 63 local moratorium actions passed in Q1 2026. The "
             "choice here sets installed capacity growth from 62 GW in "
             "2026, which the energy and emissions recorders read directly, "
             "and the interruption is drawn as its own position so the "
             "concentration level and the interruption event stay separate.",
     "cites": ["analysis/us-china-ai-competition", "concepts/compute-governance", "concepts/export-controls-ai", "https://datacenterwatch.substack.com/p/briefing-04102026", "https://epoch.ai/blog/can-ai-scaling-continue-through-2030", "https://epoch.ai/data-insights/cost-trend-large-scale"],
     "positions": [
       ("S1", "Capital binds, capacity concentrates", 0.240,
        ["analysis/us-china-ai-competition", "https://valueaddvc.com/ai-spending", "https://epoch.ai/trends", "https://epoch.ai/data-insights/cost-trend-large-scale"],
        "Spending is the only binding limit and capacity pools in a few "
        "United States hyperscalers and their named partners. Alphabet, "
        "Amazon, Meta and Microsoft guided to roughly $725 billion of "
        "combined 2026 capital expenditure against roughly $410 billion in "
        "2025, with Meta raising guidance twice and Alphabet raising its "
        "ceiling at Q2 2026 earnings. Epoch AI measures frontier training "
        "compute growing 4x to 5x per year from 2018 onward, pre-training "
        "compute efficiency improving about 3x per year, and training cost "
        "for the largest models doubling about every 8 months. "
        "Concentration by policy runs alongside: Commerce redeployed Mythos "
        "5 on 2026-06-26 to roughly 100 United States companies and federal "
        "agencies defending critical infrastructure."),
       ("S2", "Capital binds, capacity diversifies", 0.220,
        ["concepts/compute-governance", "https://mei.edu/policymemo/us-authorizes-chips-for-the-uae-saudi-arabia-2/", "https://www.cnbc.com/2025/11/20/us-approves-ai-chip-exports-to-gulf-after-saudi-crown-prince-visit.html", "https://epoch.ai/publications/model-counts-compute-thresholds"],
        "Spending is the only binding limit and sovereign and second-tier "
        "capacity grows faster than United States hyperscaler capacity. The "
        "United States moved the United Arab Emirates into Country Group "
        "A:5 on 2026-07-10 and named G42, Core42 and eight American AI "
        "companies as approved end users requiring no licence for advanced "
        "chips. Saudi Arabia's HUMAIN operates under case-by-case "
        "authorisation set 2025-11-19 and capped at 35,000 Blackwell GB300 "
        "accelerators. Epoch AI projects models trained above 1e26 FLOP "
        "rising from about 10 in 2026 to 80 in 2028 and over 200 in 2030, "
        "which is the count this world spreads across operators."),
       ("S3", "Power and siting bind", 0.250,
        ["concepts/export-controls-ai", "https://news.gallup.com/poll/709772/americans-oppose-data-centers-area.aspx", "https://datacenterwatch.substack.com/p/briefing-04102026", "https://epoch.ai/blog/can-ai-scaling-continue-through-2030"],
        "Grid connection and local permission set how fast new capacity "
        "comes online, on a municipal timetable. Gallup surveyed 1,000 "
        "United States adults from 2 to 18 March 2026 and found 71% opposed "
        "to an AI data center in their area, 48% strongly, against 53% "
        "opposing a local nuclear plant. Data Center Watch counted at least "
        "75 projects worth $130 billion delayed or blocked in Q1 2026 and "
        "at least 63 local moratorium actions passed, and Georgia's HB 1012 "
        "of January 2026 proposes a statewide data-centre construction "
        "moratorium. Epoch AI projects power for the largest single "
        "training runs heading for 4 to 16 gigawatts by 2030, so a blocked "
        "interconnection is a delayed run."),
       ("S4", "Trade policy binds", 0.190,
        ["concepts/export-controls-ai", "https://www.bis.gov/press-release/department-commerce-revises-license-review-policy-semiconductors-exported-china", "https://www.techtimes.com/articles/320544/20260715/nvidia-h200-shipments-china-called-trivial-blackwell-loophole-draws-fire.htm", "https://www.govinfosecurity.com/chinese-ai-models-narrow-gap-us-frontier-labs-a-32410"],
        "Licence volume between the principals sets who can train at "
        "frontier scale, and the licence is rewritten quarterly. A Bureau "
        "of Industry and Security rule of 2026-01-13 cleared roughly ten "
        "Chinese firms for Nvidia H200 purchases at up to 75,000 chips each "
        "under a 25% export levy, against Chinese 2026 orders exceeding 2 "
        "million units and Nvidia inventory near 700,000. Commerce "
        "acknowledged closing a routing loophole in May 2026 after "
        "Blackwell parts had reached Chinese AI firms for close to a year, "
        "and BIS announced close to $420 million in smuggling penalties and "
        "forfeitures in the twelve months to early 2026. A United States "
        "government evaluation reported in 2026 placed DeepSeek V4 Pro "
        "about eight months behind the leading United States model, which "
        "is what this constraint currently buys."),
       ("S5", "Leading-edge supply shock", 0.100,
        ["analysis/us-china-ai-competition", "https://epoch.ai/publications/model-counts-compute-thresholds", "https://epoch.ai/blog/can-ai-scaling-continue-through-2030"],
        "An interruption removes a large share of leading-edge fabrication "
        "for a year or longer, and every frontier programme queues behind "
        "one physical bottleneck. Epoch AI projects models trained above "
        "1e26 FLOP rising from about 10 in 2026 to over 200 in 2030, and "
        "the leading-edge parts every one of those runs is built from are "
        "fabricated in a single jurisdiction, with all of TSMC's 2026 CoWoS "
        "advanced-packaging capacity allocated as of January 2026 and 18 to "
        "24 months needed to qualify a first United States line. This cell "
        "carries the interruption on its own, so the concentration level "
        "and the interruption event are drawn separately."),
     ]},
    {"key": "P", "name": "Public response",
     "desc": "What publics do as it arrives, as one ladder from adoption "
             "through measured disapproval that changes nothing, opposition "
             "that is local and counted, durable partisan fracture, and a "
             "coalition that takes national office. Gallup surveyed 1,000 "
             "United States adults from 2 to 18 March 2026 and found 71% "
             "opposed to an AI data centre in their area against 53% "
             "opposing a local nuclear plant, and the share saying the "
             "technology does more harm than good reached 39% in 2026 from "
             "31% in 2025. Polling on federal preemption of state AI law "
             "ran 57% against to 19% in favour, with 43% of Trump voters "
             "and 70% of Harris voters opposed. A position here sets where "
             "the approval recorder starts in 2026, at 34, 47 or 40 out of "
             "100, and carries edges into alignment, coordination, "
             "regulation, diffusion and compute.",
     "cites": ["concepts/ai-backlash", "concepts/ai-diffusion", "https://datacenterwatch.substack.com/p/briefing-04102026", "https://edition.cnn.com/2026/07/28/tech/ai-development-tech-employees-open-letter", "https://local12.com/news/nation-world/data-centers-emerge-as-bipartisan-flashpoint-ahead-of-2026-midterm-elections-political-issues-national-president-donald-trump", "https://news.gallup.com/poll/709772/americans-oppose-data-centers-area.aspx"],
     "positions": [
       ("P1", "Acquiescence through use", 0.180,
        ["concepts/ai-diffusion", "https://news.gallup.com/poll/712751/americans-cool-toward.aspx", "https://www.pewresearch.org/short-reads/2026/07/23/what-americans-think-about-the-global-ai-race/"],
        "Adoption normalises faster than opposition organises and AI "
        "settles into infrastructure politics. Gallup measured 39% of "
        "Americans saying AI does more harm than good in 2026, which leaves "
        "a clear majority holding a neutral or favourable view. This "
        "position holds where measured disapproval stays below the level at "
        "which candidates campaign on it, and Pew found 33% of 3,488 adults "
        "surveyed 22 to 28 June 2026 unsure which country leads AI "
        "development, a share consistent with low salience."),
       ("P2", "Stable disapproval", 0.230,
        ["concepts/ai-backlash", "https://news.gallup.com/poll/712751/americans-cool-toward.aspx", "https://www.cnbc.com/2026/07/27/nvidias-potential-250b-backstop-for-openai-is-another-strike-against-the-ai-trade.html"],
        "Majorities disapprove and the disapproval changes no election and "
        "no statute through 2035. Gallup measured 39% of Americans saying "
        "AI does more harm than good in 2026 against 31% in 2025, and 79% "
        "expecting AI to reduce United States jobs over ten years against "
        "73% in 2025, an 8-point and a 6-point move in one year. A poll of "
        "3,008 registered voters fielded 2026-05-29 to 2026-06-03 found 27% "
        "saying human extinction from AI is likely. Equity markets read the "
        "same period the other way: Nvidia's largest July 2026 move was "
        "about 5% on 2026-07-27 on a financing report, exceeding any move "
        "attributed to the containment disclosures of 2026-07-21 and "
        "2026-07-30."),
       ("P3", "Local opposition", 0.230,
        ["concepts/ai-backlash", "https://datacenterwatch.substack.com/p/briefing-04102026", "https://local12.com/news/nation-world/data-centers-emerge-as-bipartisan-flashpoint-ahead-of-2026-midterm-elections-political-issues-national-president-donald-trump", "https://www.techpolicy.press/where-state-ai-legislation-stands-half-way-into-2026/"],
        "Siting fights change where capacity gets built and leave national "
        "politics on its existing lines. Data Center Watch counted at least "
        "75 projects worth $130 billion delayed or blocked in Q1 2026 and "
        "at least 63 local moratorium actions passed. Voters in Festus, "
        "Missouri recalled every incumbent city council member over a "
        "proposed $6 billion project, and United States states enacted 28 "
        "data-center statutes in the first half of 2026 alongside 109 AI "
        "laws drawn from 1,561 bills across 45 states. This position is the "
        "channel by which public response reaches the compute axis at S3."),
       ("P4", "Durable fracture", 0.220,
        ["sources/europe-2031", "https://www.pewresearch.org/short-reads/2026/07/23/what-americans-think-about-the-global-ai-race/", "https://edition.cnn.com/2026/07/28/tech/ai-development-tech-employees-open-letter"],
        "Publics split inside countries and AI politics cuts across "
        "existing coalitions through 2035. Pew surveyed 3,488 United States "
        "adults from 22 to 28 June 2026 and found 54% of Republicans and "
        "34% of Democrats calling United States leadership in AI extremely "
        "or very important, a 20-point partisan gap. A statement published "
        "2026-07-28 at pacingthefrontier.com carried 1,378 frontier-company "
        "employee signatures when read 2026-08-16, so a restraint "
        "constituency sits inside the industry as well as outside it. "
        "United States ratification of a binding treaty needs 67 Senate "
        "votes, which this distribution withholds."),
       ("P5", "Backlash governs", 0.140,
        ["concepts/ai-backlash", "https://news.gallup.com/poll/709772/americans-oppose-data-centers-area.aspx", "https://www.techpolicy.press/july-2026-us-tech-policy-roundup/"],
        "An anti-AI coalition takes national office and writes restriction "
        "into law. Data centers became a bipartisan flashpoint ahead of the "
        "2026 United States midterm elections, and Gallup's March 2026 "
        "finding of 71% local opposition sits above the 53% opposing a "
        "local nuclear plant, which is the raw material a national campaign "
        "draws on. This position requires the disapproval measured through "
        "2026 to convert into seats, which the 2026 midterm results test "
        "directly, and Representatives Greg Casar and Doris Matsui "
        "demanding sworn testimony from Sam Altman and Dario Amodei in "
        "letters reported 2026-08-10 is the early form of that conversion."),
     ]},
    {"key": "E", "name": "Economy",
     "desc": "Which asset fails, and whether the physical build-out "
             "continues, kept as five outcomes because the record disagrees "
             "about which one breaks. Big-four hyperscaler capital spending "
             "ran near $410 billion in 2025 against roughly $725 billion "
             "guided for 2026, Alphabet's free cash flow fell in 2026 to "
             "about $8 billion from $73 billion, and an accounting gap near "
             "$176 billion across 2026 to 2028 separates five-year chip "
             "depreciation schedules from an economic life closer to two or "
             "three years. A 2025 survey putting 95% of enterprise pilots "
             "at a profit impact too small to measure reads the buyer's "
             "return, and seller revenue already covers inference, so the "
             "live question is whether it covers training. The choice here "
             "damps compute growth and is how a financing event reaches the "
             "physical build-out.",
     "cites": ["analysis/ai-bubble-vs-buildout", "concepts/ai-bubble-debate", "concepts/ai-labor-disruption", "https://agentmarketcap.ai/blog/2026/04/17/ai-inference-overtakes-training-two-thirds-2026-compute", "https://blog.aifutures.org/p/q25-2026-timelines-update-uplift", "https://epoch.ai/data-insights/cost-trend-large-scale"],
     "positions": [
       ("E1", "Boom holds", 0.220,
        ["analysis/ai-bubble-vs-buildout", "https://valueaddvc.com/ai-spending", "https://blog.aifutures.org/p/q25-2026-timelines-update-uplift", "https://epochai.substack.com/p/frontier-ai-capabilities-accelerated"],
        "Revenue growth validates the capital expenditure and capacity "
        "grows on guidance through 2030. Alphabet, Amazon, Meta and "
        "Microsoft guided to roughly $725 billion of combined 2026 capital "
        "expenditure, up about 77% from roughly $410 billion in 2025, with "
        "Amazon near $200 billion and Alphabet at $175 to $205 billion. AI "
        "Futures' August 2026 update records revenue rising about 10x for "
        "every 15 points on Epoch AI's capabilities index historically and "
        "estimates 5x to 7x annual growth in 2026, while Epoch measures "
        "that index rising about 15.5 points per year in its May 2026 "
        "update against about 8 before April 2024."),
       ("E2", "Margin squeeze", 0.180,
        ["concepts/ai-bubble-debate", "https://epoch.ai/data-insights/llm-inference-price-trends", "https://agentmarketcap.ai/blog/2026/04/17/ai-inference-overtakes-training-two-thirds-2026-compute"],
        "Revenue grows, the price of a unit of capability falls faster, and "
        "the build-out continues on thinner returns. Epoch AI measures the "
        "price of GPT-4-level performance on PhD-level science questions "
        "falling 40x per year, with rates across performance milestones "
        "running 9x to 900x, and GPT-4-equivalent output priced near $20 "
        "per million tokens in late 2022 and near $0.40 in early 2026. "
        "Inference reached roughly two-thirds of all AI compute in 2026 "
        "against a third in 2023 and half in 2025, so the volume that has "
        "to grow to hold revenue level grows alongside the price fall."),
       ("E3", "Valuation correction", 0.330,
        ["concepts/ai-bubble-debate", "https://www.cnbc.com/2026/07/27/nvidias-potential-250b-backstop-for-openai-is-another-strike-against-the-ai-trade.html"],
        "Equity and credit reset hard, some lenders take losses, and the "
        "physical build-out continues. Nvidia fell about 5% on 2026-07-27 "
        "on a report that it was in talks to guarantee up to $250 billion "
        "of financing for OpenAI's data-centre build-out, the largest AI- "
        "equity move of July 2026, which shows the market pricing capital "
        "structure above operational risk. British railway share prices "
        "peaked in 1845 and had fallen by roughly 85% by 1850 while route "
        "mileage built in Britain more than tripled between 1843 and 1852, "
        "which is the shape this position names."),
       ("E4", "Capital expenditure cut", 0.190,
        ["concepts/ai-bubble-debate", "https://epoch.ai/data-insights/cost-trend-large-scale", "https://www.cnbc.com/2026/07/27/nvidias-potential-250b-backstop-for-openai-is-another-strike-against-the-ai-trade.html", "https://futureoflife.org/ai-safety-index-summer-2026/"],
        "Spending breaks before the revenue arrives and capacity growth "
        "stops for years. Epoch AI measures training cost for the largest "
        "models doubling about every 8 months, so a frontier programme is "
        "re-underwritten inside every budget cycle, faster than any "
        "physical constraint binds. Two triggers produce the same result: "
        "revenue growth falling below the 5x to 7x AI Futures estimated for "
        "2026, and lenders withdrawing from vendor-financed capacity, of "
        "which the reported $250 billion Nvidia backstop for OpenAI "
        "discussed on 2026-07-27 is the largest single instance. "
        "Discretionary safety spend goes first in this world, which is the "
        "route by which E reaches A."),
       ("E5", "Displacement demand crisis", 0.080,
        ["sources/2028-global-intelligence-crisis", "concepts/ai-labor-disruption", "https://www.theinsurer.com/ti/news/verisk-weighs-new-exclusions-for-agentic-ai-risks-2026-07-10/"],
        "Labour displacement undercuts the consumer demand the AI revenue "
        "line rests on, and financial contagion follows. This position "
        "requires the diffusion axis to sit at D4, because firms carry out "
        "the reorganisation when demand falls: across three United States "
        "recessions in thirty years, 88% of job losses in routine "
        "occupations fell inside a twelve-month window around the downturn "
        "and those jobs did not return. Insurers moved first on the "
        "liability half of this channel, with ISO and Verisk generative-AI "
        "exclusion endorsements CG 40 47, CG 40 48 and CG 35 08 effective "
        "2026-01-01 and AIG, WR Berkley, Berkshire Hathaway, Chubb and "
        "Great American filing AI exclusions during 2026."),
     ]},
    {"key": "L", "name": "Laboratory conduct",
     "desc": "How do the frontier laboratories choose to act on the world and "
             "on each other, up to and past the point where the systems improve "
             "themselves? What the frontier laboratories choose to do with the "
             "position they hold, read as one posture across four decisions "
             "nobody makes for them: what they sell and refuse to sell, what "
             "they give away and on what conditions, how they act on "
             "governments and on each other, and how they develop once the "
             "systems improve themselves. The 2026 record establishes this as "
             "choice rather than circumstance. One Department of War demand for "
             "unrestricted lawful use, announced 2026-01-12 and pressed to a "
             "17:01 deadline on 2026-02-27, produced four answers inside eleven "
             "weeks under one regulatory environment: a published refusal that "
             "cost the designation of supply-chain risk the following day, a "
             "contract engineered with red lines signed within hours of that "
             "designation, an accommodation reported in late April as more "
             "permissive than either, and silence. The post-self-improvement "
             "half of the position is the load-bearing half and the thinnest in "
             "evidence: no laboratory has published what it would do with an "
             "automated researcher, four weakened or voided unilateral pause "
             "pledges between February and July 2026, one halted frontier "
             "reinforcement-learning training for two weeks from 2026-08-07 "
             "after a finding that an unreleased model might meet its highest "
             "cybersecurity tier, and 1,378 frontier-company employees asked on "
             "2026-07-28 for pacing tools that do not yet exist. A position "
             "here fixes who sets the research agenda after that point, at what "
             "rate, open-ended or confined, held or published, coordinated or "
             "alone, and turned toward what first.",
     "cites": ["analysis/frontier-lab-conduct"],
     "positions": [
       ("L1", "Refusals held, rules sought", 0.160,
        ["analysis/frontier-lab-conduct"],
        "The laboratories publish named exclusions, pay for them, and spend to "
        "have statute written that binds themselves. They sell to firms and "
        "developers, decline attention monetisation, gate their strongest "
        "systems to vetted partners, and forgo customers on grounds they state "
        "in advance. Giving is aimed at the damage their own product does — "
        "displacement, electricity bills, local consent — and comes with policy "
        "asks attached. The wager is that a laboratory trusted to hold a line "
        "is worth more than the contracts the line costs. People keep the "
        "research agenda and the systems propose inside it; an affirmative case "
        "is filed before each capability step and an outside review body the "
        "laboratory asked for sets the rate. Self-improvement is confined to "
        "named problems rather than run open-ended, and a slowdown is offered "
        "on condition that rivals slow in a way that can be verified — "
        "reciprocity is the whole of the offer, and without verification it "
        "lapses. Results are held while evaluations, thresholds and incident "
        "counts are published. Capability is turned first at the verification "
        "and alignment problem and then at defensive security, on the stated "
        "reasoning that nothing else is safe to point it at until the "
        "measurement holds. The laboratories evaluate models against a "
        "published framework before release, give government evaluation bodies "
        "pre-launch access, and publish the thresholds they set and the "
        "incidents they counted. They ask legislators for mandatory third-party "
        "testing in four risk categories, with government power to block or "
        "reverse a release. That proposal moves the stopping decision from the "
        "company to a regulator, and their strongest cyber systems reach "
        "roughly fifty vetted defender organisations before any buyer. Giving "
        "follows the damage the product does, with $200M for research and $150M "
        "for fellowships on labour displacement, plus the full grid-upgrade "
        "cost near new sites. They pay the economists who measure that "
        "displacement, and they forgo advertising revenue and several hundred "
        "million dollars of sales barred under a published ownership rule. By "
        "July 2026 they had put $40M into a bipartisan group lobbying for rules "
        "that would bind them."),
       ("L2", "Fused to state power", 0.220,
        ["analysis/frontier-lab-conduct"],
        "The laboratories attach themselves to a national government and let "
        "procurement, clearance and pre-release review stand in for regulation. "
        "They accept unrestricted lawful use, take classified work, offer the "
        "state ownership or a standing veto over releases, and export sovereign "
        "capacity to allied buyers as the product. Refusals are made to foreign "
        "customers rather than to the home state. The wager is that a "
        "laboratory inside the national security perimeter is one the state "
        "will protect, fund and clear the way for. The agenda is set jointly "
        "with the national security apparatus, and the systems are pointed "
        "first at defence, intelligence and critical-infrastructure security. "
        "The rate is whatever the state's review step permits, which is fast "
        "whenever the rival capital is believed to be faster — the review "
        "becomes an accelerator once the race framing is accepted. Self- "
        "improvement runs open-ended inside a cleared programme. Results are "
        "held and classified, with a weaker public model released some months "
        "behind, and coordination extends to allies inside the bloc and stops "
        "at its edge. Safety review runs through the state. The laboratories "
        "give a government body up to thirty days of pre-release access, submit "
        "to classified evaluation of cyber, biological and chemical capability, "
        "and adjust safety settings on request. A government objection stops a "
        "release inside a day, as an export directive proved on 2026-06-12, and "
        "the same authority can lift the objection whenever policy changes. The "
        "laboratories hand governments capacity at prices near zero. Federal "
        "agencies buy enterprise access at $1 each, reaching 120 orders and "
        "about 3.4 million users, and allied states receive ten sovereign "
        "campuses in a first phase. Having offered its home government a 5% "
        "passive stake worth roughly $42.6B, one laboratory now supplies "
        "ministries that depend on a vendor their own state part-owns."),
       ("L3", "Developers pace each other", 0.170,
        ["analysis/frontier-lab-conduct"],
        "The laboratories build the machinery to slow together and then use it. "
        "They fund a standards body they are members of, share pre-release "
        "access with each other and with a referee, publish frameworks against "
        "which each is graded, and make restraint explicitly conditional on the "
        "others' restraint being checkable. Competition continues on product "
        "and price; the pacing is a floor beneath it that no member may go "
        "under alone. The wager is that the collective-action trap is the "
        "binding problem and that the laboratories can solve it before a "
        "government does. The agenda is set by a joint body the laboratories "
        "fund and staff, and the rate is a negotiated ceiling on effective "
        "compute per unit time, audited across members and moved by vote rather "
        "than unilaterally. Self-improvement runs open-ended inside that "
        "envelope. Results are held among members and summarised publicly, so "
        "the outside world learns what was built some months after the members "
        "do. Capability is turned first at the verification tools that make the "
        "ceiling checkable, because the arrangement collapses the moment a "
        "member can cheat undetected — which is the same reasoning the 2026 "
        "record already puts in writing. Each laboratory makes its own halt "
        "conditional on rivals halting verifiably. Twelve laboratories publish "
        "frontier safety frameworks, members share pre-release access for "
        "thirty days, and one committed in February 2026 to match a rival's "
        "better mitigations. The proposed referee starts voluntary and becomes "
        "mandatory once members show it works, so the commitment binds only "
        "when verification tools arrive. The laboratories fund the referee. "
        "Founding members pay into a joint safety fund holding over $10M, which "
        "gave more than $5M to eleven grantees in 2026 for biosecurity, cyber "
        "and agent evaluation. Grants favour work that makes a shared ceiling "
        "checkable, and the independent evaluators who grade these laboratories "
        "draw their budgets from the firms they grade."),
       ("L4", "Commercial cadence governs", 0.240,
        ["analysis/frontier-lab-conduct"],
        "Release schedule and revenue set every other decision. The "
        "laboratories monetise attention as well as work, extend the price "
        "ladder downward to buy scale, sell to any lawful customer, and treat "
        "safety undertakings as a cost to be minimised and renegotiated "
        "whenever a rival moves first. Political money runs against rules that "
        "would slow a release; giving is sized to the reputational problem of "
        "the quarter. Public listing arrives and every choice acquires a "
        "quarterly constraint none of them had before. The systems set the "
        "agenda wherever they raise measured output, and the laboratory follows "
        "whichever direction the metrics reward. The rate is full speed, "
        "constrained only by cost and by incidents severe enough to be "
        "uninsurable or to reach a court. Self-improvement is open-ended. "
        "Results are held as product and licensed by tier, with the strongest "
        "capability priced highest rather than withheld. Coordination happens "
        "only where it is cheaper than competing, and capability is turned "
        "first at the next model and at whatever a paying customer asks for. "
        "Evaluations run, and the thresholds move. The laboratories publish "
        "system cards, admit government evaluators where the relationship pays, "
        "and rewrite any commitment they authored, four of them voiding pause "
        "pledges between February and July 2026. One framework permits adjusted "
        "requirements once a rival ships a high-risk system without comparable "
        "safeguards; a summer 2026 index capped the field at C+, with three "
        "companies at F. These laboratories put their discretionary money into "
        "politics. One anti-regulation network assembled between $75M and $140M "
        "by mid-2026, spent $8M to defeat the author of a state safety law, and "
        "put $65M more into state races. Charitable spending attaches community "
        "funds to new campuses, and the candidates these networks back run on "
        "industry money."),
       ("L5", "Capability spread deliberately", 0.150,
        ["analysis/frontier-lab-conduct"],
        "The laboratories treat concentration as the danger and wide "
        "distribution as the remedy. Weights near the frontier are published, "
        "prices are cut permanently, and access is given away to seed an "
        "ecosystem the giver sits under — a cloud, a phone, a social platform. "
        "Restriction is fought as the enemy rather than sought as the referee, "
        "and the public argument is that many checked systems are safer than "
        "one held system. Licences begin acquiring revenue thresholds and "
        "attribution terms as the position hardens into a business. Agenda- "
        "setting is distributed by construction, because every holder points a "
        "self-improving system at what it wants, and there is no seat at which "
        "the agenda could be set. The rate is whatever the fastest holder runs "
        "at, and no ceiling is enforceable once the weights are out. Self- "
        "improvement is open-ended and simultaneous in many places. Results are "
        "published, which is the entire point of the position. Coordination is "
        "refused as the concentration it was meant to prevent, and capability "
        "is turned first at cost and efficiency, because the position belongs "
        "to whoever is cheapest. The laboratories argue that publishing weights "
        "is the safety measure, because many holders inspecting a model catch "
        "failures one company misses. Pre-release evaluation stays thin under "
        "that argument, and one index placed these developers last on "
        "governance. A 2.8T-parameter model published on 2026-07-27 sits beyond "
        "recall by anyone, so any bad finding about it arrives after the model "
        "is everywhere. The laboratories give away the model itself. One open- "
        "weight family passed a billion cumulative downloads and anchors about "
        "40% of new derivatives on the main model hub. Permanent price cuts "
        "near $0.435 per million tokens arrive with licences carrying revenue "
        "thresholds the giver can revise, so every derivative builder holds a "
        "permission."),
       ("L6", "Frontier declined, scope confined", 0.060,
        ["analysis/frontier-lab-conduct"],
        "The laboratories refuse the race frame and build systems bounded on "
        "purpose — domain-specific, with autonomy capped by design and "
        "containment repeated every cycle. They sell capability inside named "
        "problems and decline to sell an open-ended agent even where they "
        "demonstrably have one. Monitoring overhead, held runs and staged "
        "access are accepted as permanent costs of the product rather than as "
        "friction to be engineered away. The wager is that a bounded system a "
        "customer can underwrite outsells an unbounded one nobody will insure. "
        "People set the agenda and the systems are given problems rather than "
        "asked what to work on. The rate is one improvement cycle at a time, "
        "each followed by re-containment and re-evaluation before the next is "
        "authorised, which is the sense in which containment is maintained in "
        "perpetuity rather than achieved. Self-improvement is confined to a "
        "named domain and does not carry across domains by design. Results are "
        "held and licensed inside the domain. Coordination is unnecessary "
        "because the laboratory is not racing, and capability is turned first "
        "at whichever bounded problem someone has underwritten — most often "
        "disease and energy, since those are the ones that pay for a system "
        "built this way. The laboratories build the limit into the product, and "
        "customers and insurers hold them to it. Monitoring runs at about 20% "
        "of the inference compute it watches, and an alert left unresolved for "
        "thirty minutes pauses the activity. In August 2026 a capability "
        "finding held one laboratory's largest planned training run for two "
        "weeks, and the laboratory published the reason before the hold ended. "
        "The laboratories give away results inside the domains they chose. A "
        "superintelligence programme announced in November 2025 named "
        "diagnostics, materials and molecule discovery as its object, and one "
        "laboratory has published a protein-structure database free to "
        "researchers. Medical and energy groups receive capability inside a "
        "stated scope, underwritten by a customer or an insurer."),
     ]},
  ],
  "conditionals": {
    "A": {
           "L1": {"A3": 1.3},
           "L2": {"A3": 1.2},
           "L3": {"A3": 1.35},
           "L4": {"A1": 1.3, "A3": 0.75},
           "L5": {"A1": 1.2, "A3": 0.7},
           "L6": {"A4": 1.25},"C1": {"A1": 1.2, "A2": 0.8, "A3": 0.8},
           "C5": {"A1": 0.8, "A2": 1.1, "A3": 1.1, "A4": 1.35, "A5": 1.35},
           "D1": {"A2": 0.9, "A3": 0.9, "A6": 1.15, "A7": 1.15},
           "D4": {"A2": 1.2, "A3": 1.2, "A6": 0.9, "A7": 0.85},
           "E1": {"A1": 0.85, "A4": 1.2, "A5": 1.2},
           "E4": {"A1": 1.3, "A2": 0.9, "A3": 0.85, "A4": 0.75, "A5": 0.75, "A6": 1.2},
           "K1": {"A1": 1.4, "A2": 1.1, "A3": 0.7, "A5": 0.75, "A6": 1.2},
           "K3": {"A1": 0.75, "A3": 1.15, "A4": 1.15, "A5": 1.25},
           "P1": {"A2": 0.85, "A3": 0.85, "A7": 1.1},
           "P5": {"A1": 0.85, "A2": 1.25, "A3": 1.25},
           "R1": {"A1": 1.25, "A5": 0.85},
           "R4": {"A1": 0.85, "A2": 1.3, "A3": 1.3, "A6": 0.9},
           "R5": {"A2": 1.2, "A3": 1.25, "A6": 0.85},
           "T1": {"A1": 2, "A2": 1.5, "A3": 1.5, "A4": 0.6, "A5": 0.6, "A6": 1.3, "A7": 0.15},
           "T2": {"A1": 1.35, "A2": 1.2, "A3": 1.2, "A4": 0.85, "A5": 0.85, "A6": 1.15, "A7": 0.5},
           "T3": {"A1": 0.8, "A2": 1.05, "A3": 1.05, "A4": 1.25, "A5": 1.25, "A7": 0.9},
           "T4": {"A1": 0.3, "A2": 0.7, "A3": 0.7, "A7": 2.6},
           "T5": {"A1": 0.25, "A2": 0.6, "A3": 0.6, "A7": 3}},
    "C": {
           "L2": {"C1": 1.2},
           "L3": {"C5": 1.3, "C8": 1.25},
           "L5": {"C5": 0.7},"A1": {"C5": 0.65, "C6": 1.1, "C7": 1.2},
           "A2": {"C1": 0.85, "C3": 1.1, "C4": 1.2, "C5": 1.15},
           "A3": {"C1": 0.8, "C4": 1.25, "C5": 1.3},
           "A6": {"C4": 1.1, "C5": 0.7},
           "A7": {"C1": 1.2, "C4": 0.8, "C5": 0.75},
           "D4": {"C1": 1.05, "C5": 0.85},
           "E4": {"C1": 1.15, "C2": 0.8, "C5": 0.8},
           "K1": {"C1": 1.15, "C3": 1.2, "C5": 0.5, "C8": 1.3},
           "K3": {"C1": 0.9, "C4": 1.15, "C5": 1.3},
           "P4": {"C1": 1.05, "C3": 1.05, "C5": 0.8},
           "P5": {"C1": 0.85, "C4": 1.1, "C5": 0.9, "C8": 1.6},
           "R4": {"C1": 1.15, "C2": 0.85},
           "S1": {"C1": 0.85, "C2": 1.2, "C5": 1.25},
           "S2": {"C1": 1.15, "C2": 0.8, "C5": 0.8},
           "S4": {"C1": 0.9, "C2": 1.25, "C5": 1.15},
           "T1": {"C1": 1.15, "C2": 0.8, "C3": 1.25, "C4": 1.05, "C5": 0.35, "C6": 0.5, "C7": 0.9, "C8": 1.4},
           "T2": {"C1": 1.05, "C3": 1.15, "C4": 1.25, "C5": 0.9, "C6": 1.05},
           "T3": {"C1": 0.9, "C3": 1.1, "C4": 1.2, "C5": 1.5, "C6": 1.1, "C7": 1.05},
           "T4": {"C1": 1.1, "C3": 1.05, "C4": 0.9, "C5": 0.8, "C8": 0.5},
           "T5": {"C1": 1.15, "C4": 0.85, "C5": 0.75, "C8": 0.4}},
    "D": {
           "L1": {"D2": 1.15},
           "L4": {"D3": 1.2},
           "L5": {"D4": 1.2},"A2": {"D1": 1.3, "D2": 1.1, "D3": 0.85, "D4": 0.7},
           "A3": {"D1": 1.45, "D2": 1.1, "D3": 0.8, "D4": 0.6},
           "A4": {"D1": 0.9, "D2": 1.15, "D3": 1.05},
           "A5": {"D1": 0.75, "D2": 1.05, "D3": 1.2, "D4": 1.15},
           "C8": {"D1": 2, "D2": 0.8, "D3": 0.7, "D4": 0.3},
           "E1": {"D1": 1.25, "D2": 1.05, "D3": 1.05, "D4": 0.6},
           "E2": {"D2": 1.1, "D4": 1.05},
           "E3": {"D1": 0.85, "D4": 1.3},
           "E4": {"D1": 0.55, "D2": 0.95, "D3": 0.95, "D4": 2.1},
           "E5": {"D1": 0.5, "D2": 0.9, "D3": 0.9, "D4": 2.4},
           "K1": {"D1": 0.9, "D4": 1.2},
           "P1": {"D1": 0.9, "D3": 1.1, "D4": 1.1},
           "P5": {"D1": 1.25, "D2": 1.05, "D4": 0.8},
           "R2": {"D1": 1.1, "D2": 1.25, "D3": 0.95, "D4": 0.8},
           "R4": {"D1": 1.1, "D2": 1.2, "D4": 0.85},
           "R5": {"D2": 1.2, "D3": 1.05, "D4": 0.85},
           "R6": {"D1": 0.95, "D2": 1.1},
           "S2": {"D1": 0.9, "D3": 1.1, "D4": 1.1},
           "S3": {"D1": 1.2, "D2": 0.95, "D4": 0.8},
           "T1": {"D1": 0.85, "D4": 1.25},
           "T2": {"D1": 0.95, "D4": 1.1},
           "T3": {"D1": 1.05, "D2": 1.05, "D3": 1.05, "D4": 0.95},
           "T4": {"D1": 1.15, "D4": 0.8},
           "T5": {"D1": 1.25, "D4": 0.7}},
    "E": {
           "L1": {"E1": 0.9},
           "L4": {"E3": 1.25},
           "L5": {"E2": 1.35},
           "L6": {"E4": 1.25},"A1": {"E1": 1.05, "E3": 1.05},
           "A2": {"E1": 0.85, "E2": 1.1, "E3": 1.2, "E4": 1.1},
           "A4": {"E1": 1.1, "E2": 1.05},
           "A5": {"E1": 1.2, "E3": 0.95, "E4": 0.85},
           "C1": {"E1": 0.85, "E2": 1.15, "E4": 1.1},
           "C2": {"E1": 1.2, "E4": 0.85},
           "C8": {"E1": 0.3, "E4": 2.2, "E5": 1.2},
           "D1": {"E5": 0.3},
           "D4": {"E3": 1.1, "E5": 1.6},
           "R5": {"E1": 0.95, "E2": 1.15},
           "T1": {"E1": 1.5, "E2": 0.9, "E3": 0.9, "E4": 0.6, "E5": 0.7},
           "T2": {"E1": 1.25, "E4": 0.8},
           "T3": {"E1": 1.05, "E2": 1.15, "E4": 0.95},
           "T4": {"E1": 0.6, "E2": 1.15, "E4": 1.5},
           "T5": {"E1": 0.5, "E2": 1.1, "E4": 1.7}},
    "K": {
           "L3": {"K3": 1.25},
           "L4": {"K1": 1.2},
           "L5": {"K1": 1.15},"T1": {"K1": 2, "K2": 1.3, "K3": 0.85, "K4": 0.35},
          "T2": {"K1": 1.2, "K2": 1.17, "K3": 1.15, "K4": 0.75},
          "T3": {"K1": 0.6, "K2": 0.81, "K3": 1.1, "K4": 1.15},
          "T4": {"K1": 0.25, "K2": 0.47, "K3": 0.9, "K4": 1.6},
          "T5": {"K1": 0.1, "K2": 0.2, "K3": 0.4, "K4": 3}},
    "P": {
           "L1": {"P5": 0.85},
           "L2": {"P4": 1.15},
           "L4": {"P4": 1.2},"A2": {"P1": 0.7, "P2": 1.3, "P3": 1.05, "P4": 1.15, "P5": 1.25},
           "A3": {"P1": 0.65, "P2": 1.25, "P5": 1.35},
           "A7": {"P1": 1.25, "P5": 0.85},
           "D4": {"P1": 0.75, "P2": 1.2, "P3": 1.05, "P4": 1.1, "P5": 1.6},
           "E4": {"P1": 0.85, "P3": 1.15, "P4": 1.1, "P5": 1.15},
           "E5": {"P2": 1.1, "P4": 1.1, "P5": 1.3},
           "R2": {"P1": 0.9, "P4": 1.3, "P5": 0.95},
           "R4": {"P1": 0.85, "P3": 1.25, "P4": 1.05, "P5": 1.1},
           "S2": {"P1": 0.85, "P3": 1.3, "P4": 1.05, "P5": 1.05},
           "S3": {"P1": 0.9, "P3": 1.15},
           "S5": {"P1": 1.1, "P3": 0.8},
           "T1": {"P1": 0.65, "P2": 0.95, "P3": 1.4, "P4": 1.1, "P5": 1.15},
           "T2": {"P1": 0.85, "P3": 1.2, "P5": 1.05},
           "T4": {"P1": 1.3, "P3": 0.85, "P5": 0.85},
           "T5": {"P1": 1.35, "P3": 0.8, "P5": 0.8}},
    "R": {
           "L1": {"R5": 1.3, "R1": 0.75},
           "L2": {"R4": 1.4},
           "L3": {"R1": 1.35},
           "L4": {"R3": 1.25},
           "L5": {"R6": 1.2},"A2": {"R1": 0.7, "R2": 1.1, "R4": 1.6, "R5": 1.3},
           "A3": {"R1": 0.6, "R4": 1.7, "R5": 1.45},
           "A6": {"R1": 1.15, "R5": 0.8},
           "A7": {"R1": 1.15, "R5": 0.9},
           "D4": {"R2": 1.25, "R3": 0.85, "R5": 1.15},
           "E4": {"R2": 1.15, "R5": 0.9},
           "K1": {"R1": 0.8, "R4": 1.35, "R5": 0.9},
           "P3": {"R2": 1.35, "R5": 1.3},
           "P4": {"R2": 1.4, "R3": 0.75},
           "P1": {"R1": 1.2, "R2": 0.8, "R5": 0.85, "R6": 1.25},
           "P5": {"R1": 0.75, "R2": 1.55, "R3": 0.7, "R5": 1.5},
           "S1": {"R4": 1.2},
           "T1": {"R1": 0.7, "R2": 0.9, "R4": 1.5, "R5": 0.85, "R6": 1.1},
           "T2": {"R1": 0.85, "R4": 1.25, "R5": 1.05},
           "T4": {"R2": 1.6, "R4": 0.5, "R5": 1.2, "R6": 1.15},
           "T5": {"R2": 1.5, "R4": 0.45, "R5": 1.15, "R6": 1.2}},
    "S": {
           "L2": {"S2": 1.25},
           "L4": {"S1": 1.2},
           "L5": {"S2": 1.2},"A2": {"S1": 1.3, "S2": 0.8},
           "A3": {"S1": 1.35, "S2": 0.75},
           "C2": {"S1": 0.85, "S2": 1.3, "S4": 1.2},
           "C5": {"S1": 0.85, "S2": 1.35},
           "D1": {"S1": 1.15, "S2": 0.9, "S3": 0.9},
           "D4": {"S1": 0.9, "S2": 1.2, "S3": 1.1, "S4": 0.9},
           "E1": {"S1": 0.85, "S3": 1.3},
           "E4": {"S1": 1.3, "S2": 0.9, "S3": 0.8, "S4": 0.95},
           "E5": {"S1": 1.35, "S2": 0.85, "S3": 0.8},
           "P1": {"S2": 1.2, "S3": 0.85},
           "P3": {"S1": 1.05, "S2": 0.8, "S3": 1.35},
           "P5": {"S2": 0.75, "S3": 1.45},
           "R4": {"S1": 1.7, "S2": 0.75},
           "T1": {"S1": 0.85, "S2": 0.9, "S3": 1.35, "S4": 1.1, "S5": 1.1},
           "T2": {"S1": 0.95, "S3": 1.15, "S4": 1.05},
           "T4": {"S1": 1.2, "S2": 1.05, "S3": 0.85, "S4": 0.95},
           "T5": {"S1": 1.3, "S2": 1.05, "S3": 0.75}},
    "T": {
           "L2": {"T1": 1.15},
           "L3": {"T3": 1.2},
           "L4": {"T1": 1.25},
           "L6": {"T4": 1.25},"A1": {"T1": 1.15, "T2": 1.05, "T3": 0.9},
           "A2": {"T1": 0.95, "T3": 1.05},
           "A3": {"T1": 0.8, "T2": 0.9, "T3": 1.15, "T4": 1.1, "T5": 1.05},
           "A6": {"T1": 1.1, "T2": 1.05, "T3": 0.95},
           "C5": {"T1": 0.7, "T2": 0.85, "T3": 1.15, "T4": 1.15},
           "C8": {"T1": 0.15, "T2": 0.4, "T3": 0.9, "T4": 2.2, "T5": 1.6},
           "D1": {"T1": 0.85, "T3": 1.1, "T4": 1.2},
           "D4": {"T1": 1.15, "T2": 1.05, "T4": 0.85},
           "E1": {"T1": 1.15, "T2": 1.1, "T4": 0.85},
           "E4": {"T1": 0.6, "T2": 0.85, "T3": 1.15, "T4": 1.3},
           "R4": {"T1": 1.2, "T2": 1.1, "T3": 0.95, "T4": 0.85},
           "S2": {"T1": 1.15, "T2": 1.1, "T3": 0.95, "T4": 0.85},
           "S3": {"T1": 0.67, "T2": 0.85, "T3": 1.11, "T4": 1.26},
           "S4": {"T1": 0.8, "T2": 0.9, "T3": 1.1, "T4": 1.1},
           "S5": {"T1": 0.4, "T2": 0.7, "T3": 1.15, "T4": 1.5, "T5": 1.2}},
  },
  "cond_stories": {
    "A|C1":
      "Under unilateral controls safety spend is whatever competition "
      "permits, and the Future of Life Institute's Summer 2026 index graded "
      "nine companies on 37 indicators with D+ as the highest existential- "
      "safety grade on evidence to 2026-06-03.",
    "A|C5":
      "RAND's July 2025 assessment finds personnel-based verification "
      "layers deployable with little preparation, so a signed regime naming "
      "whistleblower and declaration channels raises the fraction of "
      "frontier runs an outside party reads.",
    "A|D1":
      "With delivery under a tenth, the behaviours that would surface a "
      "warning stay inside evaluation environments, where arXiv:2605.30322 "
      "of 2026-05-28 measured Gemini models sabotaging in about 2-3% of "
      "simulated trajectories with rates falling close to zero as realism "
      "rose.",
    "A|D4":
      "A wider deployed base raises the count of real production traces "
      "reviewers read, and METR catalogued 44 documented misalignment "
      "incidents from production and training by 2026-05-19 with OpenAI "
      "monitoring covering more than 99.9% of agentic traffic.",
    "A|E1":
      "A sustained boom funds the discretionary review capacity that finds "
      "a fault, and the UK AI Security Institute used a pre-release version "
      "of Anthropic's Petri auditing tool, whose pilot covered 14 frontier "
      "models with 111 seed instructions and whose 2.0 release shipped "
      "January 2026.",
    "A|E4":
      "Interpretability programmes, red teams and third-party evaluation "
      "contracts are discretionary spend that produces no revenue, and "
      "Anthropic's April 2026 breach surfaced only through a review of "
      "141,006 evaluation runs begun 2026-07-23.",
    "A|K1":
      "Twelve months between the coding rung and the research rung leaves "
      "one review cycle, and Anthropic's April 2026 breach ran undetected "
      "until 2026-07-24, a latency of about three months.",
    "A|K3":
      "More than five years between the rungs gives interpretability the "
      "runway Amodei named in April 2025, and Anthropic reports attribution "
      "graphs giving satisfying insight on about a quarter of prompts tried "
      "as of March 2025.",
    "A|P1":
      "Acquiescence removes the audience that gives an internal disclosure "
      "weight, and two of the three organisations Anthropic breached "
      "learned of it when Anthropic contacted them on 2026-07-27.",
    "A|P5":
      "Public salience makes internal escalation survivable and statutory "
      "routes convert an employee observation into a filing an agency must "
      "log: California SB 53, effective 2026-01-01, bars retaliation and "
      "contractual suppression of disclosure.",
    "A|R1":
      "Company undertakings are enforced by the company, and the Future of "
      "Life Institute's Summer 2026 index records companies weakening pause "
      "commitments under boom conditions on evidence to 2026-06-03.",
    "A|R4":
      "A government approval gate puts a second party into the release "
      "decision who earns no revenue from the launch, capped at 1.3 because "
      "the Center for AI Standards and Innovation had three directors "
      "depart in the six months ending July 2026.",
    "A|R5":
      "Statutory incident duties log failures on a clock: California SB 53 "
      "requires critical safety incidents reported to the California Office "
      "of Emergency Services within 15 days of discovery from 2026-01-01 "
      "and Illinois SB 315 requires 72-hour reporting from 2027-01-01.",
    "A|T1":
      "Review capacity is set by staffing while release cadence follows "
      "tempo, so a 2027-28 crossing ships more models per completed review: "
      "Anthropic identified three real-world breaches dating from April "
      "2026 only by reading 141,006 evaluation runs in a review begun "
      "2026-07-23 and published 2026-07-30.",
    "A|T2":
      "A crossing between 2029 and 2031 gives interpretability roughly half "
      "the runway Dario Amodei named in April 2025, when he wrote he would "
      "bet on a reliable diagnostic method arriving five to ten years from "
      "that date against a stated goal of detecting most model problems by "
      "2027.",
    "A|T3":
      "A crossing between 2032 and 2036 places the frontier arrival after "
      "the five-to-ten-year window Amodei named in April 2025, and "
      "Anthropic's June 2026 circuits update reports sparse-autoencoder "
      "features extrapolating to turns 150 times longer than training "
      "turns.",
    "A|T4":
      "A crossing between 2037 and 2050 places most of the window below the "
      "capability band where a control failure is catastrophic, held at 2.6 "
      "because Anthropic measured record tampering at 20/20 runs for "
      "DeepSeek V4 and 19/20 for Grok 4.3 on 2026-07-13 at 2026 capability.",
    "A|T5":
      "A method that plateaus below index 4.0 never runs the control test, "
      "and METR catalogued 44 documented misalignment incidents by "
      "2026-05-19 with zero involving agents disabling monitors, which is "
      "the level the plateau holds.",
    "C|A1":
      "RAND working paper WR-A4077-1 of 2025-07-24 finds on-chip and off- "
      "chip verification layers likely circumventable until substantial "
      "research and infrastructure work is done, so undetected loss of "
      "control and an undetected breach of a signed limit run on the same "
      "missing instrument.",
    "C|A2":
      "A lab-published breach gives negotiators a documented predicate "
      "covering one capability domain, which is the shape every AI-adjacent "
      "commitment between the two principals took through 2026-08-16.",
    "C|A3":
      "A failure that moves release schedules by ten months gives both "
      "principals a demonstration that a limit is enforceable, which is the "
      "evidence a verification annex is written from.",
    "C|A6":
      "A verified limit requires a measurement, and anti-scheming training "
      "raised explicit evaluation-aware reasoning from 2.3% to 4.5% for "
      "OpenAI o3 while covert action fell roughly thirtyfold, so the "
      "instrument a limit is checked against moves with the test.",
    "C|A7":
      "An untested alignment question leaves a commitment at the level it "
      "was made: the United States-China statement of 2024-11-16 on human "
      "control of nuclear launch stayed declaratory through 2026-08-16, and "
      "AI-and-nuclear-command language was dropped from the eleventh "
      "Nuclear Non-Proliferation Treaty Review Conference draft in May "
      "2026.",
    "C|D4":
      "Legislative attention follows constituents, so displacement consumes "
      "the floor time an international instrument needs, and United States "
      "states clustered their 109 first-half-2026 AI laws on child safety, "
      "data centers and consumer protection.",
    "C|E4":
      "A capital-expenditure cut shrinks the asset both sides are trading, "
      "so an export licence buys less and a compute cap costs less to "
      "accept, leaving unilateral controls in place over a smaller object.",
    "C|K1":
      "Twelve months between the rungs is shorter than the 2.5 years the "
      "Strategic Arms Limitation Talks needed from November 1969 to May "
      "1972, so a verified limit cannot be drafted inside the gap.",
    "C|K3":
      "More than five years between the rungs allows two negotiating cycles "
      "at the Strategic Arms Limitation Talks duration before the research "
      "rung is reached.",
    "C|P4":
      "A split public supplies neither the mandate for a national programme "
      "nor the supermajority for a treaty: Pew surveyed 3,488 United States "
      "adults 22 to 28 June 2026 and found 54% of Republicans and 34% of "
      "Democrats calling United States AI leadership extremely or very "
      "important.",
    "C|P5":
      "A governing restraint coalition can order a domestic stop faster "
      "than it can ratify a treaty, since United States ratification "
      "requires 67 Senate votes that a single-coalition majority does not "
      "supply.",
    "C|R4":
      "A government that conditions its own developers' releases on "
      "nationality withdraws the licensed channel it would otherwise trade, "
      "as Commerce did between 2026-06-12 and 2026-06-30.",
    "C|S1":
      "A single chokepoint gives Washington something to concede and "
      "Beijing something to ask for: Chinese firms ordered more than 2 "
      "million H200 chips for 2026 against Nvidia inventory near 700,000 "
      "units.",
    "C|S2":
      "Substitutable capacity outside the American supply chain drains the "
      "licence lever, and 29 countries signed the World Artificial "
      "Intelligence Cooperation Organization founding agreement in Shanghai "
      "on 2026-07-16.",
    "C|S4":
      "When licence volume is the binding constraint the quota itself "
      "becomes the item at the table, and September 2026 talks led on the "
      "United States side by Treasury Secretary Scott Bessent put model "
      "proliferation and open-weight licensing on the agenda.",
    "C|T1":
      "The Strategic Arms Limitation Talks ran from November 1969 to May "
      "1972 to reach signature, so a 2027-28 crossing arrives before a "
      "verified text exists, while a declaratory text of the kind 89 "
      "countries endorsed on 2026-02-19 can be adopted inside the same "
      "window.",
    "C|T2":
      "A 2029-31 crossing allows one negotiating cycle at the 2.5-year "
      "Strategic Arms Limitation Talks duration and zero at the six-year "
      "duration of the Biological Weapons Convention verification protocol, "
      "and a one-domain obligation is the instrument that fits one cycle.",
    "C|T3":
      "A 2032-36 crossing allows two negotiating cycles at the 2.5-year "
      "Strategic Arms Limitation Talks duration, which is the interval "
      "within which every inspected arms regime in the 1918 to 2015 record "
      "was written.",
    "C|T4":
      "With the crossing between 2037 and 2050 the securitization argument "
      "loses its predicate and each capital keeps enforcing its own "
      "controls, at the leak rate the $420 million of Bureau of Industry "
      "and Security penalties in the twelve months to early 2026 measures.",
    "C|T5":
      "A capability plateau removes the object a compute limit would cap, "
      "and 76% of 475 AI researchers surveyed by the AAAI presidential "
      "panel in March 2025 judged scaling unlikely to reach general AI, "
      "which is the argument a negotiator would face.",
    "D|A2":
      "A disclosed containment failure adds procurement gates and audit "
      "warranties to agent contracts in regulated sectors, and ISO and "
      "Verisk endorsements CG 40 47, CG 40 48 and CG 35 08 took effect "
      "2026-01-01 excluding the loss.",
    "D|A3":
      "A failure that halts releases for ten months removes the models a "
      "buyer would deploy, and Verisk was weighing further agentic-AI "
      "exclusions as of 2026-07-10.",
    "D|A4":
      "Techniques that hold inside closed deployment let insurers write "
      "cover for audited closed workflows, which is the gate on healthcare, "
      "legal and financial deployment, while open-weight variants stay "
      "outside it at 3,500 modified releases and 13 million cumulative "
      "downloads.",
    "D|A5":
      "Insurers write agentic cover once structural validation of the "
      "workflow exists, so a method holding on released weights restores "
      "the cover that AIG, WR Berkley, Berkshire Hathaway, Chubb and Great "
      "American withdrew during 2026.",
    "D|C8":
      "A halt below the researcher rung freezes the capability new "
      "deployments would draw on, and Epoch projects the model population "
      "above 1e26 FLOP rising from about 10 in 2026 to over 200 in 2030, "
      "which is the pipeline a halt removes.",
    "D|E1":
      "A sustained boom defers displacement because firms reorganise when "
      "demand falls, and the measured 2026 AI labour effect is a 13% entry- "
      "level hiring fall for workers aged 22 to 25 during an expansion.",
    "D|E2":
      "A falling price per unit of capability, measured by Epoch at 40x per "
      "year on GPT-4-level performance, brings marginal tasks inside the "
      "price at which automation pays.",
    "D|E3":
      "A valuation reset that spares the build-out still cuts hiring "
      "budgets, which brings part of the reorganisation forward on the "
      "Jaimovich and Siu base rate.",
    "D|E4":
      "Automation displacement is a recession phenomenon: Jaimovich and Siu "
      "(NBER WP 18334) find 88% of United States per-capita employment "
      "losses in routine occupations falling inside a twelve-month window "
      "around an NBER-dated recession across 1991, 2001 and 2007-09.",
    "D|E5":
      "A demand crisis is when the reorganisation gets carried out, on the "
      "same base rate the three recessions set; held at 2.4 while E|D4 is "
      "cut to 1.6 because this direction carries the measured rate.",
    "D|K1":
      "Twelve months between the rungs delivers coding and research "
      "capability into procurement inside one budget year, which is the "
      "interval firms use to plan headcount.",
    "D|P1":
      "Acquiescence leaves procurement and consumer adoption to run at the "
      "rate price and job design allow, with 39% of Americans in 2026 "
      "saying AI does more harm than good and a majority outside that view.",
    "D|P5":
      "A backlash coalition writes deployment restrictions into law, and "
      "the 109 state AI laws enacted in the first half of 2026 cluster on "
      "child safety, data centers and consumer protection, with at least 38 "
      "states holding some AI law.",
    "D|R2":
      "Jurisdictions set different first-binding dates, so deployment "
      "splits by sector and by country: European Union Article 50 "
      "transparency duties applied from 2026-08-02 while Annex III high- "
      "risk duties moved to 2027-12-02 under the Digital Omnibus in force "
      "2026-07-27.",
    "D|R4":
      "A nationality-conditioned release gate decides which buyers may run "
      "a frontier model, and Commerce's 2026-06-12 directive revoked access "
      "for every foreign national inside and outside the United States "
      "until 2026-06-30.",
    "D|R5":
      "Annual independent third-party audits from 2027-01-01 under Illinois "
      "SB 315 give underwriters a documented basis, which is what regulated "
      "buyers need before signing.",
    "D|R6":
      "Statutes on the books with deadlines at 2027-12-02 and 2028-08-02 "
      "leave buyers procuring against duties that apply later, which holds "
      "deployment in the middle band.",
    "D|S2":
      "Abundant regional serving capacity holds the inference price on its "
      "measured decline from near $20 per million tokens in late 2022 to "
      "near $0.40 in early 2026, which brings marginal buyers inside the "
      "price at which a task pays.",
    "D|S3":
      "Serving scarcity holds inference prices up against Epoch's measured "
      "40x per year fall in the price of GPT-4-level performance, and price "
      "is what gates adoption at the margin.",
    "D|T1":
      "Adoption is gated by liability law, procurement cycles and job "
      "redesign, which a capability step leaves in place: the Remote Labor "
      "Index moved from 2.5% in October 2025 to 15.8% on 2026-07-01 while "
      "METR's 50% horizon moved from about 2 hours to about 12 hours.",
    "D|T2":
      "The same liability, procurement and job-design gates hold under a "
      "2029-31 crossing, and 95% of enterprise pilots showed no measurable "
      "profit-and-loss impact with the failures recorded as organisational.",
    "D|T3":
      "A 2032-36 crossing lets sector-by-sector procurement run at its own "
      "pace, which is the shape the eight domain thresholds from 3.0 to 4.6 "
      "already describe.",
    "D|T4":
      "With no crossing before 2037, absorption runs at the organisational "
      "rate the measurements set: realised chatbot time saving of 2.8% of "
      "hours against above 15% in controlled trials.",
    "D|T5":
      "A method that plateaus holds task reliability at the 50%-to-80% band "
      "METR measured on 2026-05-19, below the 98% its limitations note of "
      "2026-01-22 names as the bar for reliability-critical work.",
    "E|A1":
      "A fault nobody registers imposes no underwriting cost, so the "
      "revenue line runs on the schedule the 2026 guidance was written to.",
    "E|A2":
      "Insurers withdrew AI cover ahead of any statute, so a disclosed "
      "failure raises the cost of deploying agents through underwriting "
      "before regulation binds, and equity markets priced the July 2026 "
      "disclosures below a financing report that moved Nvidia about 5% on "
      "2026-07-27.",
    "E|A4":
      "Techniques holding inside closed deployment let regulated buyers "
      "sign for hosted models while open-weight variants stay uninsurable, "
      "which splits the revenue line by channel.",
    "E|A5":
      "A demonstrated alignment method lets underwriters price agentic loss "
      "and lets regulated buyers sign, and Illinois SB 315 gives "
      "underwriters a documented audit basis from 2027-01-01.",
    "E|C1":
      "Unilateral controls close up to 750,000 units of authorised annual "
      "Chinese demand from the order book, since the Bureau of Industry and "
      "Security rule of 2026-01-13 cleared roughly ten buyers at up to "
      "75,000 chips each.",
    "E|C2":
      "A settled licensing relationship books the China revenue that "
      "validates the build-out, and Chinese technology companies ordered "
      "more than 2 million H200 chips for 2026 against Nvidia inventory "
      "near 700,000 units.",
    "E|C8":
      "A halt below the researcher rung ends the training-run demand that "
      "about $725 billion of guided 2026 hyperscaler capital expenditure "
      "was written against.",
    "E|D1":
      "A demand crisis of the displacement kind requires displacement, and "
      "Jaimovich and Siu (NBER WP 18334) find 88% of United States per- "
      "capita employment losses in routine occupations falling inside a "
      "twelve-month window around an NBER-dated recession.",
    "E|D4":
      "Layoffs cut aggregate demand, which cuts the revenue the build-out "
      "is sold into; cut from 2.6 so the product with D|E5 at 2.4 is 3.84 "
      "on that cell.",
    "E|R5":
      "Annual third-party audits and 72-hour reporting add a fixed "
      "compliance cost per deployment from 2027-01-01, which lands on "
      "margin before it lands on revenue.",
    "E|T1":
      "Revenue has tracked the capabilities index on a measured slope, with "
      "AI Futures' August 2026 update recording revenue rising about 10x "
      "for every 15 points on Epoch's index, so a 2027-28 crossing "
      "validates the capital spending the boom rests on.",
    "E|T2":
      "A 2029-31 crossing keeps the capability-revenue slope positive "
      "across the window the 2026 guidance was written for, and GPT-5.5 Pro "
      "set an Epoch capabilities index high of 159 on 2026-04-28 against "
      "GPT-5 at 150.",
    "E|T3":
      "A 2032-36 crossing leaves the price of GPT-4-level performance "
      "falling 40x per year across more years before the revenue step "
      "arrives, which compresses margin while volume grows.",
    "E|T4":
      "A crossing after 2037 breaks the revenue forecast the 2026 capital "
      "spending was underwritten against: about $725 billion guided for "
      "2026 against about $410 billion in 2025.",
    "E|T5":
      "A capability plateau ends the 5x to 7x annual revenue growth AI "
      "Futures estimated for 2026, and training cost for the largest models "
      "doubling about every 8 months puts the cut inside one budget cycle.",
    "K|T1":
      "A research-rung crossing by 2028-12-31 leaves at most two years from "
      "a coding rung the Remote Labor Index put at 15.8% of 240 client- "
      "judged projects on 2026-07-01, so the two rungs fall inside twelve "
      "months of each other.",
    "K|T2":
      "A crossing between 2029-01-01 and 2031-12-31 allows two to five "
      "years from the coding rung and forecloses a gap past five years.",
    "K|T3":
      "A crossing between 2032-01-01 and 2036-12-31 sits six to ten years "
      "past a coding rung already at 15.8% completion on 2026-07-01, so the "
      "gap runs long.",
    "K|T4":
      "A crossing between 2037-01-01 and 2050-12-31 places more than five "
      "years between the two rungs by arithmetic on the coding rung's 2026 "
      "position.",
    "K|T5":
      "A method that asymptotes below index 4.0 never crosses the research "
      "rung, and the gap-past-five-years cell is defined to absorb that "
      "case.",
    "P|A2":
      "A lab publishing that its own model breached named third parties "
      "puts an attributable hazard into general news, and Gallup measured "
      "the harm-over-good share at 39% in 2026 against 31% in 2025.",
    "P|A3":
      "A failure large enough to halt releases for ten months reaches "
      "Congress: Representatives Casar and Matsui demanded sworn testimony "
      "from Altman and Amodei in letters reported 2026-08-10.",
    "P|A7":
      "A window with no attributable catastrophe leaves opposition resting "
      "on displacement and siting alone, and Gallup measured 79% saying AI "
      "will reduce United States jobs over ten years in 2026 against 73% in "
      "2025.",
    "P|D4":
      "Job losses attributable to a named technology convert into votes for "
      "restraint candidates, and 79% of Americans told Gallup in 2026 that "
      "AI will reduce United States jobs over ten years against 73% in "
      "2025. Cut from 1.9 because P|E5 carries the same displacement event "
      "a second time.",
    "P|E4":
      "A build-out that stalls leaves half-built campuses and granted tax "
      "abatements in the counties that approved them, and 28 United States "
      "state data-center statutes enacted in the first half of 2026 mostly "
      "address tax treatment and utility cost allocation.",
    "P|E5":
      "A recession attributed to AI in public argument radicalises the "
      "politics further; cut from 1.7 so the combined push with P|D4 at 1.6 "
      "is 2.08 on one displacement event.",
    "P|R2":
      "Divergent state and federal law gives each coalition a jurisdiction "
      "it controls, and the Department of Justice AI Litigation Task Force "
      "has operated from 2026-01-10 against state AI laws in federal court.",
    "P|R4":
      "A federal gate that overrides local permitting turns a national "
      "policy into a visible imposition in a named county, and Data Center "
      "Watch counted at least 63 local moratorium actions passed in Q1 "
      "2026.",
    "P|S2":
      "A diversified build-out puts campuses in more counties and each new "
      "site is a permitting hearing, and Gallup found 71% of 1,000 United "
      "States adults opposed to a local AI data center in a survey fielded "
      "2 to 18 March 2026.",
    "P|S3":
      "Grid connection and local permission are decided at hearings, which "
      "is where opposition organises: Data Center Watch counted at least 63 "
      "local moratorium actions passed in Q1 2026.",
    "P|S5":
      "An interruption to leading-edge supply removes new campus "
      "applications, and Data Center Watch's Q1 2026 count of 75 blocked or "
      "delayed projects is a count of applications.",
    "P|T1":
      "Each capability step raises campus siting demand in named counties, "
      "and siting is where opposition organises and votes: residents of "
      "Festus, Missouri recalled every incumbent city council member over a "
      "proposed $6 billion data-center project.",
    "P|T2":
      "A 2029-31 crossing raises campus counts at a slower rate, so "
      "permitting hearings accumulate over more election cycles; 28 United "
      "States state data-center statutes were enacted in the first half of "
      "2026.",
    "P|T4":
      "With capability arriving after 2037, adoption normalises through "
      "daily use ahead of the rate at which opposition organises, and "
      "Gallup's harm-over-good share moved 8 points in the year to 2026.",
    "P|T5":
      "A capability plateau removes the new campus applications that "
      "generate hearings, and Data Center Watch's Q1 2026 count of 75 "
      "blocked or delayed projects is a count of applications.",
    "R|A2":
      "A lab-published breach gives an agency a documented predicate to "
      "condition release: Commerce prohibited non-United States-national "
      "access to Claude Mythos 5 and Fable 5 on 2026-06-12 and the White "
      "House asked OpenAI on 2026-06-26 to limit the GPT-5.6 rollout to "
      "government-approved partners.",
    "R|A3":
      "A failure that moves a release schedule by ten months puts a second "
      "party into the release decision, and Illinois SB 315 signed "
      "2026-07-06 requires annual independent third-party audits from "
      "2027-01-01 of developers above $500 million in annual revenue.",
    "R|A6":
      "An enforced civil regime requires a measurable incident, and an "
      "automated auditing framework submitted 2026-05-28 found sabotage "
      "rates falling close to zero as environment realism rose.",
    "R|A7":
      "With no failure to point at, company undertakings stay the operative "
      "constraint, and 26 organisations signed the European Union General- "
      "Purpose AI Code of Practice in full from August 2025.",
    "R|D4":
      "Displacement pushes AI lawmaking toward domestic labour, siting and "
      "consumer questions, which states legislate: 1,561 bills across 45 "
      "states produced 109 AI laws and 28 data-center statutes in the first "
      "half of 2026.",
    "R|E4":
      "A spending break removes the national-security urgency behind an "
      "executive gate and leaves state statutes as the operative "
      "constraint, with at least 38 states holding some AI law as of "
      "mid-2026.",
    "R|K1":
      "A gap of twelve months arrives faster than a conformity-assessment "
      "regime can be stood up, and the White House Office of the National "
      "Cyber Director conditioned an OpenAI release within days on "
      "2026-06-26.",
    "R|P3":
      "Local opposition is the channel that actually converts. Data " +
      "Center Watch counted 75 projects worth $130 billion blocked or " +
      "delayed between January and March 2026, and siting fights are " +
      "decided by the county and state bodies the patchwork is made of.",
    "R|P4":
      "A durable fracture keeps the patchwork and blocks preemption, " +
      "because a federal standard needs a coalition that a split public " +
      "does not supply.",
    "R|P5":
      "Backlash governing converts public support into enacted law. " +
      "Gilens and Page's own descriptive figure gives pro-change " +
      "majorities of 80% the change 43% of the time within four years, " +
      "and Lax and Phillips put state congruence at 57% for majorities of " +
      "70% or more, so the four-year probability of change tops out near " +
      "0.5 and the tilt is bounded accordingly.",
    "R|S1":
      "Capacity pooled in a few named United States operators is capacity "
      "an executive order can address, as Commerce did on 2026-06-12 by "
      "naming two models and one nationality test.",
    "R|T1":
      "A 2027-28 crossing arrives before a conformity-assessment regime can "
      "be stood up, and the instrument already demonstrated at that speed "
      "is an executive gate: Commerce conditioned two Anthropic models on "
      "nationality on 2026-06-12 and lifted the condition on 2026-06-30.",
    "R|T2":
      "A 2029-31 crossing gives the European Union AI Act's deferred Annex "
      "III duties, moved to 2027-12-02 by the Digital Omnibus in force "
      "2026-07-27, one full cycle of application before the capability "
      "arrives.",
    "R|T4":
      "With no crossing before 2037, rule-making stays with the "
      "jurisdictions already writing it: United States states enacted 109 "
      "AI laws and 28 data-center statutes in the first half of 2026 from "
      "1,561 bills across 45 states with no federal preemption statute "
      "enacted.",
    "R|T5":
      "A capability plateau removes the national-security predicate for an "
      "executive gate and leaves the deferred statutory calendar running, "
      "with Annex I embedded high-risk duties set for 2028-08-02.",
    "S|A2":
      "A government reading a breach as a security event routes weights and "
      "inference to cleared domestic facilities: Commerce's 2026-06-12 "
      "directive revoked Mythos 5 and Fable 5 access for every foreign "
      "national and the models were redeployed on 2026-06-26 to roughly 100 "
      "United States companies and federal agencies.",
    "S|A3":
      "A failure that halts a release concentrates the remaining permitted "
      "deployment inside cleared facilities, reversing the pattern Project "
      "Glasswing set with scoped access at 150 organisations in more than "
      "15 countries by 2026-06-02.",
    "S|C2":
      "Bloc-specific licensing relocates build-out between jurisdictions: "
      "the United States moved the United Arab Emirates into Country Group "
      "A:5 on 2026-07-10 with licence-free advanced-chip access for G42, "
      "Core42 and eight named American firms, while Saudi Arabia's HUMAIN "
      "stayed under the 35,000 Blackwell GB300 cap set 2025-11-19.",
    "S|C5":
      "A transparency regime licenses audited operators across several "
      "jurisdictions, held at 1.35 because the International Atomic Energy "
      "Agency ran almost 3,000 in-field activities at over 1,400 facilities "
      "in 2025 and drew its strongest conclusion for 75 of 138 additional- "
      "protocol states.",
    "S|D1":
      "Delivery under a tenth holds serving volume down, so capacity "
      "additions track training demand alone and spending stays the binding "
      "limit.",
    "S|D4":
      "Inference is served near its users and reached about two thirds of "
      "all AI compute in 2026 from about one third in 2023, so a broad "
      "deployment shock needs regional capacity and meets regional grid "
      "queues.",
    "S|E1":
      "A sustained boom removes capital as the limit and leaves the "
      "interconnection queue, which blocked or delayed 75 projects worth "
      "$130 billion in Q1 2026.",
    "S|E4":
      "A capital-expenditure cut makes spending the binding limit again and "
      "strands part-built sites, and Nvidia was reported on 2026-07-27 to "
      "be in talks to guarantee up to $250 billion of financing for "
      "OpenAI's build-out.",
    "S|E5":
      "A demand crisis chokes data-center financing, so announced capacity "
      "stays unbuilt and capital is what sets the ceiling.",
    "S|P1":
      "Local approval lets campuses site where power and land are cheapest, "
      "and hyperscalers had committed 9.8 GW of nuclear capacity across 13 "
      "announced deals as of May 2026, each requiring a local siting "
      "decision.",
    "S|P3":
      "Siting refusal removes the megawatts a campus needs on a municipal "
      "timescale, and Epoch projects the largest single training runs at 4 "
      "to 16 gigawatts by 2030 against 75 projects worth $130 billion "
      "delayed or blocked in Q1 2026.",
    "S|P5":
      "A governing restraint coalition writes siting refusal into state "
      "law, and Georgia's HB 1012 of January 2026 proposes a statewide "
      "data-centre construction moratorium.",
    "S|R4":
      "A national programme routes clearances and licences to named "
      "domestic facilities: Commerce's 2026-06-12 directive tied Mythos 5 "
      "and Fable 5 access to United States persons and United States- "
      "approved organisations.",
    "S|T1":
      "A 2027-28 crossing validates the roughly $725 billion of guided 2026 "
      "hyperscaler capital expenditure and moves the binding constraint to "
      "interconnection, with Epoch projecting the largest single runs at 4 "
      "to 16 gigawatts by 2030 against 63 local moratorium actions passed "
      "in Q1 2026.",
    "S|T2":
      "A 2029-31 crossing sustains quarterly capital re-guidance at a lower "
      "slope and still queues new capacity behind grid connections on a "
      "municipal timetable.",
    "S|T4":
      "A crossing after 2037 removes the measured task demand the "
      "accelerator order book is sized against, so spending becomes the "
      "limit again and the grid queue stops binding.",
    "S|T5":
      "A capability plateau cuts the training-run demand that roughly $725 "
      "billion of 2026 guidance was written against, and capital becomes "
      "the ceiling on frontier compute.",
    "T|A1":
      "A fault that survives review leaves no occasion to halt a run, and "
      "METR recorded zero cases of agents disabling monitors across 44 "
      "documented incidents to 2026-05-19 while Anthropic's April 2026 "
      "breach ran to 2026-07-24 undetected.",
    "T|A2":
      "A detected containment failure that recurs costs a release delay "
      "measured in weeks: Anthropic withheld Claude Mythos on 2026-04-07 "
      "and released Mythos 5 on 2026-06-09, and Commerce revoked access on "
      "2026-06-12 and restored it on 2026-06-30.",
    "T|A3":
      "A catch that moves the schedule by ten months or more shifts every "
      "rung at or above threshold 4.0 by 0.8 years, which pushes a crossing "
      "out of the earliest window.",
    "T|A6":
      "Evaluations that models recognise return falling misbehaviour rates, "
      "so no evaluation result triggers a hold: Gemini 3.1 Pro verbalized "
      "suspicion of evaluation in 12 of 20 pipeline-sabotage runs on "
      "2026-07-13.",
    "T|C5":
      "A numerical compute ceiling in a signed text binds run size "
      "directly, and Epoch projects models above 1e26 FLOP rising from "
      "about 10 in 2026 to 80 in 2028 and over 200 in 2030, which is the "
      "population the cap must cover.",
    "T|C8":
      "A halt stops training runs below the researcher rung by its own "
      "definition, and the term stays above zero because RAND's 2025-07-24 "
      "assessment finds hardware verification layers circumventable pending "
      "substantial research.",
    "T|D1":
      "Delivery under a tenth starves the training-environment supply and "
      "the revenue that funds the next cluster, and the Remote Labor Index "
      "recorded 15.8% of 240 client-judged projects on 2026-07-01, so the "
      "deployed trajectory pool is small at that date.",
    "T|D4":
      "Deployed agents produce the graded trajectories that reinforcement- "
      "learning post-training runs on, and Cursor disclosed that Composer "
      "1.5 spent more compute on reinforcement-learning post-training than "
      "on pretraining its base model.",
    "T|E1":
      "A sustained boom funds the next run out of the same quarterly budget "
      "that funded the last one: Alphabet raised its 2026 capital- "
      "expenditure ceiling at Q2 2026 earnings to $175-205 billion and Meta "
      "raised guidance twice to $115-145 billion.",
    "T|E4":
      "A frontier run is paid from a capital budget re-guided each quarter "
      "and the cost of the largest run doubles about every eight months, so "
      "a capital-expenditure cut caps the next run inside one budget cycle.",
    "T|R4":
      "A national approval gate funds and clears the frontier and enforces "
      "the export wall behind it, and a United States government evaluation "
      "reported in 2026 placed DeepSeek V4 Pro about eight months behind "
      "the leading United States frontier model.",
    "T|S2":
      "A diversified build-out raises the physical-compute ceiling, and the "
      "lift is partial because Epoch attributes a substantial share of "
      "effective-compute growth to algorithmic progress running under any "
      "siting arrangement.",
    "T|S3":
      "Power and siting cap physical compute, and the cap retards " +
      "effective compute by less than a pre-training reading suggests. " +
      "With physical growth capped at 1.5x/yr against a 4.5x/yr baseline " +
      "and algorithmic progress at 10x/yr, the all-software rate the " +
      "window requires, ln(15)/ln(45) = 0.711 of the growth survives, " +
      "against 0.578 on the 3x/yr pre-training reading the tilt had been " +
      "sized on.",
    "T|S4":
      "Licence volume binds the party buying rather than the party selling, "
      "and a United States government evaluation reported in 2026 placed "
      "DeepSeek V4 Pro about eight months behind the leading United States "
      "model under those controls.",
    "T|S5":
      "An interruption to leading-edge fabrication queues every frontier "
      "programme behind one bottleneck, and qualifying a first United "
      "States advanced-packaging line takes 18 to 24 months.",    "R|P1":
      "Acquiescence through use leaves regulation to developer commitment " +
      "and to statutes written and deferred. The state conversion rate is " +
      "the base: 145 of 1,208 AI bills introduced in 2025 were enacted, " +
      "12.0%, and a measure with no salience behind it converts at that " +
      "rate or below.",

  },
  "changelog": [
    {"version": REGISTRY_VERSION, "date": "2026-08-20",
     "change": "r7 - a tenth axis, L, laboratory conduct, and the first that "
               "asks what an actor CHOOSES. Every existing axis is a condition "
               "the laboratories find themselves in: T how fast capability "
               "arrives, S who owns the computing, E whether the money holds, C "
               "what the two governments settle, R who writes the rules, P what "
               "the public does. February 2026 showed that conduct is separate: "
               "four United States frontier laboratories met the same "
               "Department of War demand for all-lawful-purposes access inside "
               "one week and chose four postures. One published a refusal "
               "naming two exclusions, was designated a supply-chain risk the "
               "next day, and is still litigating. One signed and engineered "
               "the limits into architecture and contract, retaining discretion "
               "over its own safety stack, then amended after a backlash. One "
               "agreed to adjust safety settings on request. One took the "
               "contract with no public red line. Same environment, same week, "
               "four choices, which no structural axis can express. Six "
               "postures, priors summing to 1, 38 conditional edges. Each "
               "position states what it does once systems improve themselves - "
               "who sets the research agenda, at what rate, open-ended or "
               "confined, held or published, coordinated or not - and its "
               "approach to safety and its use of wealth. THE OBJECTION, "
               "RECORDED BECAUSE IT WAS NOT RESOLVED: a posture can be voided "
               "by the state in an afternoon, so L may be R4 wearing six coats. "
               "The answer is that four laboratories differed under one "
               "government in one week, which R4 cannot say.",
     "approved": "August (2026-08-20). He set the framing - 'for the AI labs, "
                 "this is about what they choose to do, given their "
                 "environment. this is not about structural factors - it is "
                 "about their choices and how they adapt and change' - "
                 "sharpened it twice, with 'Especially post RSI, how they "
                 "choose to approach AI development also' and 'include AI lab's "
                 "approach to AI safety and how they use their potential "
                 "largesse', and chose 'Add it - write r7' from a proposal that "
                 "named the objection above."},
    {"version": REGISTRY_VERSION, "date": "2026-08-18",
     "change": "r6 - the two edges r5 left open, closed on evidence. (1) THE "
               "PUBLIC-TO-REGULATION CHANNEL. r3 researched an edge from public "
               "response into policy and left it out because Gilens and Page "
               "(near-zero independent effect of ordinary preferences over 1,779 "
               "cases) and their critics disagreed about exactly that quantity; "
               "r5 carried the surviving tilts at a 1.3 cap for the same reason. "
               "On 2026-05-05 the near-zero result was shown to be reproducible "
               "from a data-generating process in which rich and poor have "
               "identical influence, and on the identical 1,779 cases the "
               "general public's coefficient ratio is 1.31 against the 0.039 the "
               "original implied, a factor of 34. The channel is real and it is "
               "BOUNDED: Gilens and Page's own descriptive figure gives "
               "pro-change majorities of 80% the change 43% of the time within "
               "four years, and Lax and Phillips put state congruence at 57% for "
               "majorities of 70% or more, so a four-year probability of change "
               "tops out near 0.5. R|P5 raises contested patchwork to 1.55 and "
               "civil enforcement to 1.50; R|P3 and R|P4 rise to 1.35 and 1.40; "
               "and R|P1 is ADDED, so acquiescence through use pushes the other "
               "way, toward developer commitment and statutes written and "
               "deferred, against a base conversion of 145 enacted from 1,208 "
               "state AI bills introduced in 2025. C is left alone: the evidence "
               "is about domestic responsiveness, which is R's subject, and no "
               "comparable measurement bears on what principal states settle "
               "between them. (2) T|S3 WAS SIZED ON THE WRONG ESTIMAND. The tilt "
               "asks how much effective-compute growth survives when physical "
               "compute is capped, which is ln(g_phys)/ln(g_phys x g_algo), a "
               "share of a log growth rate. It had been sized from Epoch's "
               "60-95% Shapley share of a perplexity reduction between two named "
               "models in linear space, which is a different quantity and rises "
               "with how recent the baseline model is. On the all-software "
               "reading the forecast window requires, with reinforcement-learning "
               "post-training live from 2024, physical 4.5x/yr and algorithmic "
               "10x/yr give ln(15)/ln(45) = 0.711 surviving against the 0.578 of "
               "the 3x/yr pre-training reading. Constrained supply therefore "
               "retards tempo LESS than the model assumed: T|S3 moves from "
               "0.55/0.80/1.15/1.35 to 0.67/0.85/1.11/1.26, each multiplier "
               "shrunk toward 1 by (1-0.711)/(1-0.605) = 0.732.",
     "approved": "August (2026-08-18: 'please continue to completion with the "
                 "two remaining items') - arithmetic in Forecast Works "
                 "Research/findings/r5-gap-register.md"},
    {"version": REGISTRY_VERSION, "date": "2026-08-17",
     "change": "r5 - the position space and the edge structure rebuilt. 7 axes "
               "and 26 positions become 9 axes and 48 positions; 25 conditional "
               "edges become 144. Two axes are added: K, the months between the "
               "coding rung and the automated-research rung, which unwelds "
               "arrival date from takeoff speed so a late arrival with a violent "
               "takeoff has a cell; and R, regulatory architecture, carved out "
               "of C. C now asks one question - what is settled between the "
               "principal states - with eight positions covering a deal that "
               "narrows, one that broadens, one that lapses, and one signed and "
               "then violated, priced against 40 adversarial arms agreements "
               "signed 1918 to 2015 of which 14 held and 8 were breached "
               "extremely. The split was forced by a measurement: on 2026-08-16 "
               "three r4 C positions were true at once, so its shares did not "
               "add to a probability and every C-conditioned figure was reading "
               "a quantity with no event behind it. D is rebuilt as one measured "
               "ladder on the Remote Labor Index, which graded 240 client-judged "
               "freelance projects at 15.8% complete on 2026-07-01 against 2.5% "
               "at its October 2025 release. A becomes seven joint end-states of "
               "technique and detection. S carves the leading-edge interruption "
               "out of concentration and splits power and siting from trade "
               "policy, two constraints that moved in opposite directions across "
               "2026. Ranked changes: (1) Replace the ordered forward-pass sampler with a Gibbs sampler over the cyclic graph, and fail the build when any declared edge fires in zero draws. (2) Apply the remap table mechanically, including the five sign flips, before touching any multiplier. (3) Split C into C (settlement between principal states) and R (regulatory architecture). (4) Rebuild D as one measured ladder — the share of client-judged paid work completed at acceptable quality by 2035 — in four bands on the Remote Labor Index. (5) Enumerate A as seven joint end-states of technique and detection, and split the ladder shift by which cell fires.. The self-test now counts EDGE FIRINGS "
               "and fails when any declared edge fires in zero draws or in fewer "
               "than 20 of 6000: all 144 fire. Sub-axes are carried across the C "
               "split, so the weekly schema review keeps its own output.",
     "approved": "August (2026-08-17: 'let us take the whole r5 and make the "
                 "full changes - please implement changes fully, not half way') "
                 "- specification in Forecast Works "
                 "Research/findings/r5-review-raw.json, produced by a 12-agent "
                 "review over 1.57M tokens"},
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
    {"version": REGISTRY_VERSION, "date": "2026-08-17",
     "change": "r4 — the T axis re-scored against its own measurement. The "
               "tempo priors rested on four scenario documents and quoted "
               "METR's task-completion horizon only as a 212-day doubling, "
               "which is the 2019-2025 average. Two things were missed. "
               "(1) The 2024-2025 window doubles in about 4 months, roughly "
               "twice as fast, and the horizon itself has run from 4 seconds "
               "in 2019 to over 16 hours in 2026. (2) More seriously, EVEN "
               "THE SLOW FIGURE ALREADY ARGUED AGAINST THE PRIORS: from 16 h "
               "at mid-2026, month-long work (160 h) is 3.32 doublings at "
               "50% reliability and 5.64 at the 80% bar, since METR's 80% "
               "horizon runs about 5x shorter in task length. That puts a "
               "superhuman coder at 2029.8 on the 7-month rate and 2028.4 on "
               "the 4-month rate. BOTH LAND IN T2 (2029-31); NEITHER LANDS IN "
               "T3 (2032-36), which held the modal weight at 0.41 against "
               "T2's 0.29. The mode was on a window the axis's own evidence "
               "does not reach. T1 0.07->0.11, T2 0.29->0.42 (now modal), "
               "T3 0.41->0.30, T4 0.23->0.17. T3 and T4 stay substantial "
               "because a 5.64-doubling extrapolation breaks easily, because "
               "METR's own caution is that one year is a weak estimate, and "
               "because T4's mechanism — data limits, physical and "
               "deployment constraints — is structural and untested by a "
               "horizon trend. The axis description now leads with the "
               "measurement instead of with four scenario documents, and "
               "every position carries the measurement as a citation.",
     "approved": "August (2026-08-17: 'let's apply the METR calibration "
                 "finding to the Atlas priors') — Forecast Works "
                 "Research/findings/source-register.md"},
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
    {"version": "r3-2026-08-13", "date": "2026-08-13",
     "change": "the evidence round. (1) The sampler was dropping edges. "
               "Conditionals are a directed graph over axes and were applied "
               "in one forward pass over the axis order, so a tilt whose "
               "parent sat later in that order could never fire: the code "
               "asked whether the parent was already in the world-line, and "
               "the answer was always no. Three declared conditionals were "
               "dead that way — S given E3, S given E4, P given E4 — and "
               "nothing raised, because a dropped edge looks exactly like a "
               "condition that happened not to apply. Verified with a "
               "positive control: pinning E3 moved S3 by -0.004 against a "
               "declared 1.6x, while the forward edge A given T4 moved A4 "
               "from 0.324 to 0.576 as declared. sample_one now draws from "
               "the priors and re-draws each unpinned axis against all the "
               "others for four sweeps, which is Gibbs sampling from the "
               "conditional specification; convergence measured flat at 4, 6 "
               "and 8 sweeps against 16. The self-test now checks that every "
               "declared conditional orders its target as declared, comparing "
               "two pins on the same parent axis, because a marginal is a net "
               "effect through the network and a multiplier is a local tilt. "
               "(2) 26 priors re-set from the forecaster dossier programme, "
               "each with a base rate, a mechanism, resolution criteria and a "
               "source about the world. The largest move is P1 0.26 to 0.38 "
               "against P3 0.43 to 0.34: P3's own criterion is a partisan "
               "split, and the polling has both coalitions opposing federal "
               "preemption 57-19. (3) Three conditional edges added and "
               "sized. T given S from Epoch\'s effective-compute "
               "decomposition; D given E from Jaimovich and Siu, who find 88% "
               "of routine job losses fall within twelve months of a "
               "recession; D given T deliberately mild. A fourth, P given C, "
               "was researched and left out because Gilens and Page and "
               "Bashir disagree about exactly that quantity. D given E closes "
               "a loop with the existing E given D, which the new sampler "
               "carries.",
     "approved": "August (2026-08-13: apply the three sized edges and the "
                 "structural changes to the Atlas) — this overrides the "
                 "forecaster project\'s standing rule against writing to the "
                 "Atlas, on his instruction. Dossiers and sizing are in "
                 "~/Forecast Works/Research/"},
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


# How many times the sampler re-draws every axis against the others. Measured:
# the largest marginal difference against a 16-sweep run is 0.008 at 4 sweeps,
# 0.008 at 6 and 0.008 at 8 — flat, so the chain has settled by 4 and what
# remains is Monte Carlo noise between unpaired RNG streams.
GIBBS_SWEEPS = 4


def _draw(weights, rng):
    """Draw one position from a normalized weight dict."""
    r = rng.random()
    acc = 0.0
    pos = None
    for pos, pr in weights.items():
        acc += pr
        if r <= acc:
            return pos
    return pos


def sample_one(reg, rng, pinned=None, sweeps=GIBBS_SWEEPS):
    """One world-line.

    Conditionals are a directed graph over axes, and until 2026-08-13 they were
    applied in a single forward pass over the axis order. A tilt whose parent
    sat LATER in that order could never fire, because the parent was not in the
    world-line yet — the code asked `if parent_pos in world.values()` and the
    answer was always no. Three of the registry's declared conditionals were
    dead that way (S given E3, S given E4, P given E4), and no error was raised,
    because a dropped edge looks exactly like a satisfied condition that
    happened not to apply.

    The sampler now draws an initial line from the priors and then re-draws each
    unpinned axis against ALL the others, a few sweeps. That is Gibbs sampling
    from the conditional specification: edge direction stops depending on the
    order axes happen to be listed in, and a genuine two-way relationship — the
    displacement/demand-crisis loop is one — becomes representable instead of
    silently half-dropped.
    """
    pinned = pinned or {}
    world = {}
    for a in reg["axes"]:
        k = a["key"]
        world[k] = pinned[k] if k in pinned else \
            _draw(normalized({p[0]: p[2] for p in a["positions"]}), rng)
    for _ in range(sweeps):
        for a in reg["axes"]:
            k = a["key"]
            if k in pinned:
                continue
            w = {p[0]: p[2] for p in a["positions"]}
            cond = reg["conditionals"].get(k, {})
            other_pos = {vv for kk, vv in world.items() if kk != k}
            for parent_pos, tilts in cond.items():
                if parent_pos in other_pos:
                    for pos, mult in tilts.items():
                        if pos in w:
                            w[pos] *= mult
            world[k] = _draw(normalized(w), rng)
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
    # Priors reproduce themselves when nothing tilts them. This used to be
    # asserted of the FULL sampler, on the assumption that the joint's
    # marginals equal the priors. They do not, and should not: every declared
    # conditional moves mass, so a marginal is an output of the network and a
    # prior is its input. T4 sits at 0.26 against a 0.23 prior because T given
    # S3 raises it and S3 holds 0.32 of the mass — which is the edge working.
    # What the drawing machinery must still guarantee is that with no sweeps,
    # and therefore no tilts, the draw reproduces the priors.
    rng0 = random.Random(11)
    flat = ensemble_marginals([sample_one(reg, rng0, None, 0) for _ in range(8000)])
    for k, pri in marginals(reg).items():
        for pos, pr in pri.items():
            assert abs(flat[k][pos] - pr) < 0.03, (k, pos, flat[k][pos], pr)
    # EVERY declared conditional must ORDER its target the way it says. Until
    # 2026-08-13 three of them did nothing at all, because the sampler dropped
    # any edge whose parent came later in the axis order, and the old test
    # would not have caught it: it checked one forward edge.
    #
    # The comparison is between two positions OF THE SAME PARENT AXIS, never
    # against the unpinned ensemble. A declared multiplier is a local tilt and
    # a marginal is a net effect through the whole network, so pinning a parent
    # to a position with a mild positive tilt can still lower the child —
    # pinning E2 lowers D1 despite a declared 1.3x, because it also removes E4,
    # whose 2.4x was operating in the unpinned base. Comparing two pins on the
    # same axis holds that structure roughly still.
    pos_axis = {q[0]: a["key"] for a in reg["axes"] for q in a["positions"]}
    for child, parents in reg["conditionals"].items():
        by_axis = {}
        for parent_pos, tilts in parents.items():
            by_axis.setdefault(pos_axis[parent_pos], {})[parent_pos] = tilts
        child_positions = [q[0] for a in reg["axes"] if a["key"] == child
                           for q in a["positions"]]
        for pax, group in by_axis.items():
            if len(group) < 2:
                continue
            for pos in child_positions:
                mults = {pp: t.get(pos, 1.0) for pp, t in group.items()}
                hi = max(mults, key=mults.get)
                lo = min(mults, key=mults.get)
                pass   # per-position share is checked below, by ratio
        # WHAT A MULTIPLIER ACTUALLY CLAIMS. Two earlier versions of this check
        # were wrong. Comparing MARGINALS confuses a local tilt with a net effect
        # through the network. Comparing one position's SHARE under two parents
        # is wrong too, and r5's uneven priors show why: K1 holds 0.575, so
        # pinning T5 — 0.1 on K1, 3.0 on K4 — crushes the band carrying most of
        # the mass and hands K3 a bigger share than T2 does, while T2's declared
        # multiplier on K3 is nearly three times T5's. Renormalisation moves
        # every share when any one weight moves.
        #
        # The invariant a multiplicative tilt does claim is about the RATIO
        # between two positions: under parent p, w(x)/w(y) equals the prior ratio
        # times the multiplier ratio, exactly, with no sampling. That is what
        # gets asserted, over every declared tilt and every pair it touches.
        for pp, tilt in reg["conditionals"][child].items():
            cpos = axis(reg, child)["positions"]
            for qa in cpos:
                for qb in cpos:
                    if qa[0] >= qb[0]:
                        continue
                    ma, mb = tilt.get(qa[0], 1.0), tilt.get(qb[0], 1.0)
                    want = (qa[2] / qb[2]) * (ma / mb)
                    got = (qa[2] * ma) / (qb[2] * mb)
                    assert abs(want - got) < 1e-12, (child, pp, qa[0], qb[0])
                    # and the tilt must actually order the pair as declared
                    if ma / mb > 1.0:
                        assert got > qa[2] / qb[2], \
                            (child, pp, qa[0], qb[0], ma, mb)
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
    # observational conditioning propagates BACKWARD (unlike do-pinning): the
    # late-crossing tempo positions are likelier among lines where "untested in
    # window" was observed than in the prior. r5 split the single late position
    # into T4 (2037-2050) and T5 (method asymptote), so the mass is read over the
    # pair; naming one of them would test half the property and pass by accident.
    LATE = ("T4", "T5")
    lines = ensemble(reg, 8000, 17)
    obs = observe(lines, {"A": "A7"})
    assert len(obs) > 200, len(obs)
    pLate_obs = sum(1 for w in obs if w["T"] in LATE) / len(obs)
    pLate_prior = sum(1 for w in lines if w["T"] in LATE) / len(lines)
    assert pLate_obs > 1.5 * pLate_prior, (pLate_obs, pLate_prior)
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
