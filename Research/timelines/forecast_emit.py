#!/usr/bin/env python3
"""forecast_emit.py — today's distribution → the app's data surface.

Reads weights.json (the evolving state; seeded from the registry priors on
first run) + grounding.json (thin-axis widening), then writes
Research/staged/forecast/:

  network.json    axes with TODAY's weights + provenance, conditionals,
                  impact classes, registry changelog
  bands.json      capability percentile envelopes: annual 2026-2100 +
                  monthly 2026-2032 (the near field deserves月 resolution)
  marginals.json  today's per-axis marginals + 45-day history
  mainline.json   exact argmax line + tracks + waypoints + joint p
  exemplars.json  120 sampled lines (tracks + waypoints) for narrative
  ensemble2k.json 2,000 world-lines for client-side observational filtering
  crisis.json     the named branch questions with current probabilities
  delta.json      the latest evidence applications (attributed)
  claims.json     resolvable near-term claims register (calibration)

Widening: thin grounding spreads an axis's weights toward uniform by
temperature (w^(1/widen), renormalized) — uncertainty inherited, never
hidden. Deterministic per (weights, seed).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import axes
import worldlines

HERE = os.path.dirname(os.path.abspath(__file__))
STAGED_F = os.path.join(HERE, "..", "staged", "forecast")
WEIGHTS = os.path.join(HERE, "weights.json")
SEED = 20260731

CRISES = [
    {"id": "deal-window", "q": "US-China transparency deal by 2032",
     "kind": "axis", "axis": "C", "pos": "C3",
     "cites": ["sources/ai-2040-plan-a"]},
    {"id": "explosive-takeoff", "q": "Explosive tempo (SC by 2028)",
     "kind": "axis", "axis": "T", "pos": "T1", "cites": ["sources/ai-2027"]},
    {"id": "no-sc-window", "q": "No superintelligence this window",
     "kind": "axis", "axis": "T", "pos": "T4",
     "cites": ["sources/ai-as-normal-technology"]},
    {"id": "alignment-fails", "q": "Alignment fails undetected",
     "kind": "axis", "axis": "A", "pos": "A1", "cites": ["sources/ai-2027"]},
    {"id": "hard-deflate", "q": "The bubble deflates hard",
     "kind": "axis", "axis": "E", "pos": "E3",
     "cites": ["concepts/ai-bubble-debate"]},
    {"id": "researcher-by-2035", "q": "Superhuman AI researcher by 2035",
     "kind": "band", "year": 2035, "level": 4.0, "cites":
     ["concepts/agi-timelines"]},
]

CLAIMS = [
    {"id": "cl-sc-2027", "text": "superhuman-coder milestone crossed",
     "by": "2027-12-31", "axis_support": {"T": ["T1"]},
     "cites": ["sources/ai-2027"]},
    {"id": "cl-deal-2029", "text": "US-CN AI agreement concluded",
     "by": "2029-12-31", "axis_support": {"C": ["C3"]},
     "cites": ["sources/ai-2040-plan-a"]},
    {"id": "cl-correction-2027", "text": "major AI capex correction",
     "by": "2027-12-31", "axis_support": {"E": ["E2", "E3"]},
     "cites": ["analysis/ai-bubble-vs-buildout"]},
    {"id": "cl-state-laws-2026", "text": "state AI-law count exceeds 90",
     "by": "2026-12-31", "axis_support": {"C": ["C4"]},
     "cites": ["analysis/eu-vs-us-ai-regulation"]},
]


def load_weights():
    if os.path.isfile(WEIGHTS):
        return json.load(open(WEIGHTS))
    w = {"version": axes.REGISTRY["version"],
         "date": _dt.date.today().isoformat(),
         "axes": {a["key"]: {p[0]: p[2] for p in a["positions"]}
                  for a in axes.REGISTRY["axes"]},
         "history": [], "evidence_log": [], "residue": []}
    json.dump(w, open(WEIGHTS, "w"), indent=1)
    return w


def widened_registry(weights, widen):
    """Registry copy carrying today's weights, spread by thin-axis
    temperature."""
    import copy
    reg = copy.deepcopy(axes.REGISTRY)
    # sub-axes added autonomously by the Monday schema review live in
    # weights["schema_log"]; replay them so the addition actually reaches
    # what gets published (it never did before 2026-08-03).
    axes.apply_schema_log(reg, weights.get("schema_log"))
    for a in reg["axes"]:
        k = a["key"]
        # registry may have GROWN since weights were stored (it is designed
        # to): new positions enter at their seed prior, stored positions
        # keep their evolved weight, then renormalize
        w = {p[0]: p[2] for p in a["positions"]}
        for pos, v in (weights["axes"].get(k) or {}).items():
            if pos in w:
                w[pos] = v
        temp = widen.get(k, 1.0)
        if temp > 1.0:
            w = {pos: v ** (1.0 / temp) for pos, v in w.items()}
        w = axes.normalized(w)
        a["positions"] = [(p[0], p[1], w[p[0]], p[3]) for p in a["positions"]]
    return reg


def monthly_bands(reg, n=6000, seed=SEED):
    lines = axes.ensemble(reg, n, seed)
    months = [2026 + 7 / 12.0 + i / 12.0 for i in range(int((2032 - 2026.58) * 12))]
    paths = []
    for wl in lines:
        k = worldlines.capability_path(wl)
        paths.append([worldlines.cap_at(k, m) for m in months])
    out = {"month": [round(m, 3) for m in months]}
    for p in (10, 25, 50, 75, 90):
        out["p%d" % p] = []
    for col in range(len(months)):
        vals = sorted(pth[col] for pth in paths)
        for p in (10, 25, 50, 75, 90):
            out["p%d" % p].append(round(vals[int(len(vals) * p / 100)], 3))
    return out


def emit():
    os.makedirs(STAGED_F, exist_ok=True)
    weights = load_weights()
    grounding = json.load(open(os.path.join(STAGED_F, "grounding.json"))) \
        if os.path.isfile(os.path.join(STAGED_F, "grounding.json")) else \
        {"widen": {}, "counts": {"direct": 0, "corpus": 0}}
    reg = widened_registry(weights, grounding.get("widen", {}))
    today = _dt.date.today().isoformat()

    marg = axes.marginals(reg)
    # Attribute the night's movement BEFORE history is stamped.
    #
    # Two forces move what the app draws and only one of them is evidence.
    # The grounding widener spreads a thin axis, and it moves whenever the
    # corpus grows ANYWHERE — on 2026-08-06 it supplied 41% of the visible
    # motion, all of D's and all of P's, on a morning when neither axis had a
    # single new page or a single application. It even inverted E4's sign
    # against the evidence. That is legitimate design (thin grounding renders
    # as width, SCOPE §11b) but the app said nothing, so a reader could not
    # tell "the model learned something about the economy" from "the wiki
    # gained ten pages about capability". Now it can.
    raw = axes.marginals(widened_registry(weights, {}))
    # the last entry for a PREVIOUS day. history[-1] is today's own entry on
    # any re-run, and comparing today with itself reports that nothing moved.
    prev = next((h for h in reversed(weights.get("history") or [])
                 if h.get("date") != today), {})
    prev_m = prev.get("marginals") or {}
    prev_raw = prev.get("raw")
    # The split needs YESTERDAY's unwidened marginals, and history only began
    # carrying them today. Without them the arithmetic would charge the whole
    # night's motion to grounding — a fallback wearing a measurement's
    # clothes. Standing rule 10: return unknown, and say so on screen.
    attributable = bool(prev_raw) and bool(prev_m)
    moved = {}
    for ax, poss in marg.items():
        for pos, v in poss.items():
            dm = v - (prev_m.get(ax, {}).get(pos, v))
            if not attributable:
                if abs(dm) >= 5e-7:
                    moved["%s.%s" % (ax, pos)] = {"shown": round(dm, 7)}
                continue
            dr = raw[ax][pos] - prev_raw.get(ax, {}).get(pos, raw[ax][pos])
            if abs(dm) < 5e-7 and abs(dr) < 5e-7:
                continue
            moved["%s.%s" % (ax, pos)] = {
                "shown": round(dm, 7), "evidence": round(dr, 7),
                "grounding": round(dm - dr, 7)}
    hist = weights.get("history", [])
    # r2 (2026-08-06): this used to APPEND only when the last entry was not
    # today, which meant the first run of a calendar day won and every later
    # run of that day was silently dropped from the record. On 2026-08-04 the
    # published 10:49 state was C1 0.40548 while history kept the 01:24 run's
    # 0.40618, so the next morning's report had to be reconstructed from a git
    # commit — and measured against the stale point, that morning's largest C
    # component appeared to move the OPPOSITE way to the evidence that caused
    # it. history is what the 30-day drift on screen is computed against, so
    # the error ages into position rather than showing up at once. The last
    # run of a day is the one that is served; it is the one that is recorded.
    if hist and hist[-1]["date"] == today:
        hist[-1]["marginals"] = marg
        hist[-1]["raw"] = raw
    else:
        hist.append({"date": today, "marginals": marg, "raw": raw})
    weights["history"] = hist[-60:]
    json.dump(weights, open(WEIGHTS, "w"), indent=1)

    ml, p_ml = worldlines.mainline(reg)
    kn = worldlines.capability_path(ml)
    mainline_out = {"wl": ml, "p": p_ml,
                    "tracks": worldlines.tracks(ml, kn),
                    "events": worldlines.instantiate(ml, kn, SEED),
                    "layers": worldlines.layer_states(ml, kn)}
    ex, _ = worldlines.exemplars(reg, k=120, seed=SEED)
    for e in ex:
        e["layers"] = worldlines.layer_states(
            e["wl"], worldlines.capability_path(e["wl"]))
    ens = axes.ensemble(reg, 2000, SEED + 7)
    b_year = worldlines.bands(reg, n=8000, seed=SEED)
    b_month = monthly_bands(reg)

    crises = []
    for c in CRISES:
        if c["kind"] == "axis":
            p = marg[c["axis"]].get(c["pos"], 0.0)
        else:
            yi = b_year["year"].index(c["year"])
            n_hit = 0
            lines = axes.ensemble(reg, 3000, SEED + 11)
            for wl in lines:
                k2 = worldlines.capability_path(wl)
                if worldlines.cap_at(k2, c["year"]) >= c["level"]:
                    n_hit += 1
            p = n_hit / 3000.0
        crises.append(dict(c, p=round(p, 3)))

    # Registration dates are the spine of a Brier score: a claim registered
    # long before it resolves is worth more than one registered yesterday.
    # This used to stamp `registered=today` on every claim every night, so
    # the artefact always said each claim was minted that morning. The true
    # dates survived only in git. They are now held in weights.json, written
    # once on first sight and never overwritten — and back-filled from the
    # first nightly commit so nothing is invented.
    reg_dates = weights.setdefault("claims_registered", {})
    BACKFILL = {"cl-sc-2027": "2026-07-31", "cl-deal-2029": "2026-07-31",
                "cl-correction-2027": "2026-07-31",
                "cl-state-laws-2026": "2026-07-31"}
    claims = []
    for cl in CLAIMS:
        if cl["id"] not in reg_dates:
            reg_dates[cl["id"]] = BACKFILL.get(cl["id"], today)
        claims.append(dict(cl, status="open",
                           registered=reg_dates[cl["id"]]))
    json.dump(weights, open(WEIGHTS, "w"), indent=1)

    # engine constants as data — the client implements functions against
    # THIS, never mirrored literals (single source of truth)
    engine = {
        "ladder": worldlines.LADDER,
        "tempo_knots": worldlines.TEMPO_KNOTS,
        "track_params": {"COMPUTE_G": worldlines.COMPUTE_G,
                         "E_DAMP": worldlines.E_DAMP,
                         "REV_G": worldlines.REV_G,
                         "JOBS_RATE": worldlines.JOBS_RATE,
                         "LAWS_RATE": worldlines.LAWS_RATE,
                         "APPROVAL0": worldlines.APPROVAL0},
        "templates": worldlines.TEMPLATES,
        "domains": worldlines.DOMAINS,
        "y0": worldlines.Y0, "y1": worldlines.Y1,
        # authored explainer cards for the interactive layer — every hover/
        # click reveal cites its grounding (decision of record 2026-07-31:
        # "hovering and clicking … should reveal more information,
        # explanatory cards")
        "explainers": {
            "milestones": [
                {"k": 1, "t": "Unreliable agent", "b": "Computer-using "
                 "assistants that impress and fail — scoring ~65% OSWorld in "
                 "the literature's 2025 readings. The trunk's 2025 record.",
                 "cites": ["sources/ai-2027"]},
                {"k": 2, "t": "Reliable agent", "b": "Agents trusted with "
                 "real tasks end-to-end; specialized coding/research agents "
                 "transform their professions first.",
                 "cites": ["sources/ai-2027", "concepts/agi-timelines"]},
                {"k": 3, "t": "Superhuman coder", "b": "AI outperforms the "
                 "best human engineers at software itself — the literature's "
                 "hinge milestone, because it compounds AI R&D.",
                 "cites": ["sources/ai-2027", "sources/ai-2040-plan-a"]},
                {"k": 4, "t": "Superhuman AI researcher", "b": "AI research "
                 "is automated end to end. Plan A's schedule pauses HERE "
                 "(top-expert level, 2035-2040) to keep humans in control.",
                 "cites": ["sources/ai-2040-plan-a"]},
                {"k": 5, "t": "Generally superintelligent", "b": "Beyond "
                 "expert range across domains; the takeoff-length debate "
                 "(6 years under the deal vs ~1 year racing) is about the "
                 "climb from 4 to here.",
                 "cites": ["sources/ai-2040-plan-a", "sources/ai-2027"]},
                {"k": 6, "t": "Wildly superintelligent", "b": "The ladder's "
                 "ceiling — everything above is off-scale. Most sampled "
                 "futures saturate here by the 2040s; the T4 fraction never "
                 "arrives.", "cites": ["sources/ai-2027",
                 "sources/ai-as-normal-technology"]},
            ],
            "instruments": {
                "pills": {"t": "Capability domains", "b": "Which domains the "
                 "active world-line's capability index has crossed at this "
                 "date (illustrative thresholds on the ladder, modelled — "
                 "the AI 2027 dashboard's grammar, generalized).",
                 "cites": ["sources/ai-2027"]},
                "donut": {"t": "Compute shares", "b": "US/CN/EU shares of "
                 "modelled global AI compute under the active world-line — "
                 "drift mechanisms per coordination position; the EU share "
                 "is Europe 2031's GW-gap arithmetic.",
                 "cites": ["sources/europe-2031",
                           "concepts/compute-governance"]},
                "copies": {"t": "Agent copies × speed", "b": "The AI 2027 "
                 "copies-counter: how many frontier-agent copies run, at "
                 "what multiple of human speed — derived from the capability "
                 "index and compute track (22K@13× in their Apr-2026 frame; "
                 "10M@600× in their Race ending).",
                 "cites": ["sources/ai-2027"]},
                "stats": {"t": "The stat strip", "b": "AI revenue (trunk "
                 "run-rates grown by diffusion×capability, saturating), "
                 "jobs delta (displacement-vs-augmentation, shock rate "
                 "calibrated to the 2028 crisis memo's ~10% path), laws in "
                 "force (state-wave velocity by coordination), approval "
                 "(backlash dynamics).",
                 "cites": ["sources/2028-global-intelligence-crisis",
                           "concepts/ai-labor-disruption",
                           "concepts/ai-backlash"]},
            },
            "axes_note": {"t": "What an axis probability is", "b": "The "
             "model's current weight on each position — seeded priors with "
             "provenance, moved by the tiered evidence methodology every "
             "morning, spread wider where wiki grounding is thin. Not a "
             "measurement; graded in public.", "cites": []},
            "world_note": {"t": "The World view", "b": "The active "
             "world-line's state on real geography: regime tint strength ∝ "
             "modelled compute share; site glow ∝ modelled GW at authored "
             "locations from the trunk's own reporting.", "cites": []},
            "why_shape": {"t": "Why the river has this shape",
             "b": "The forecast is a MIXTURE of tempos, not one path. The "
             "wide 2027-2040 fan is the tempo axis itself: a {t1}% "
             "explosive tail pulls the p90 edge to the ceiling by the early "
             "2030s, the {t2}% fast and {t3}% gradual mass carries the "
             "median through superhuman-coder around 2032 and "
             "researcher-level mid-decade, and the {t4}% no-SC floor is why "
             "p10 stays below the researcher line into the 2050s. The "
             "ceiling plateau past 2045 is saturation — most sampled "
             "futures max the ladder; what still differs there is "
             "OUTCOMES, which is what the Outcomes panel and the far-field "
             "waypoints track. Shelves inside the band are policy, not "
             "physics: the C3 deal pause holds lines at expert level "
             "2035-2040, the C5 tail freezes below the researcher line. "
             "Every number here re-derives each morning from the network "
             "the axis cards document.", "cites":
             ["concepts/agi-timelines", "sources/ai-2040-plan-a",
              "sources/ai-as-normal-technology"]},
            "stats_each": {
              "rev": {"t": "AI revenue", "b": "Trunk run-rates grown by "
               "diffusion × capability lift, saturating against world "
               "output; bands come from the ensemble.",
               "cites": ["analysis/ai-bubble-vs-buildout"]},
              "jobs": {"t": "Jobs delta", "b": "Cumulative employment "
               "impact; the shock rate (−2.6pp/yr under D1) is calibrated "
               "to the 2028 crisis memo's ~10% path, capability-gated.",
               "cites": ["sources/2028-global-intelligence-crisis",
                         "concepts/ai-labor-disruption"]},
              "laws": {"t": "Laws in force", "b": "Tracked-statute count "
               "growing at the coordination position's velocity — the "
               "fragmented-blocs world legislates fastest.",
               "cites": ["analysis/eu-vs-us-ai-regulation"]},
              "appr": {"t": "Public approval", "b": "Backlash dynamics by "
               "public-response position; shocks depress, the deal's "
               "stability recovers.", "cites": ["concepts/ai-backlash"]},
              "gw": {"t": "Compute", "b": "Global AI power draw; growth by "
               "supply position, damped by the economy path, saturating "
               "against build-out ceilings.",
               "cites": ["concepts/compute-governance"]},
              "co2": {"t": "AI emissions", "b": "Load (GW × utilization) × "
               "grid intensity, which declines faster under coordinated or "
               "diversified build-outs; the mid-century question is "
               "whether AI-designed energy repays the carbon debt.",
               "cites": ["industries/energy",
                         "concepts/compute-governance"]},
            },
        },
        # authored compute-site table for the World view (locations from the
        # trunk's own reporting; capacities are shares of the modelled GW
        # track, labelled modelled)
        "sites": [
            {"n": "N. Virginia cluster", "lat": 39.0, "lon": -77.5, "r": "us", "w": 0.16},
            {"n": "Columbus corridor", "lat": 40.0, "lon": -83.0, "r": "us", "w": 0.07},
            {"n": "Abilene (Stargate)", "lat": 32.4, "lon": -99.7, "r": "us", "w": 0.13},
            {"n": "Memphis (Colossus)", "lat": 35.1, "lon": -90.0, "r": "us", "w": 0.10},
            {"n": "Phoenix fabs+DCs", "lat": 33.4, "lon": -112.1, "r": "us", "w": 0.08},
            {"n": "Pacific NW hydro", "lat": 45.8, "lon": -119.7, "r": "us", "w": 0.06},
            {"n": "Texas Gulf build-out", "lat": 29.8, "lon": -95.4, "r": "us", "w": 0.06},
            {"n": "Tianwan CDZ", "lat": 34.7, "lon": 119.5, "r": "cn", "w": 0.30},
            {"n": "Beijing-Tianjin", "lat": 39.9, "lon": 116.4, "r": "cn", "w": 0.22},
            {"n": "Guizhou DC zone", "lat": 26.6, "lon": 106.6, "r": "cn", "w": 0.18},
            {"n": "Shanghai corridor", "lat": 31.2, "lon": 121.5, "r": "cn", "w": 0.15},
            {"n": "Paris/Nordics grid", "lat": 48.9, "lon": 2.3, "r": "eu", "w": 0.35},
            {"n": "Nordic hydro belt", "lat": 60.2, "lon": 10.7, "r": "eu", "w": 0.30},
            {"n": "Netherlands hub", "lat": 52.3, "lon": 4.8, "r": "eu", "w": 0.20},
            {"n": "Gulf sovereign DCs", "lat": 24.5, "lon": 54.4, "r": "row", "w": 0.5},
            {"n": "Japan-Korea build", "lat": 35.8, "lon": 137.0, "r": "row", "w": 0.5},
        ],
    }
    outputs = {
        "engine.json": engine,
        "network.json": {"version": weights["version"], "date": today,
                         "axes": [{"key": a["key"], "name": a["name"],
                                   "desc": a.get("desc", ""),
                                   "cites": a.get("cites", []),
                                   "positions": [[p[0], p[1],
                                                  round(p[2], 5), p[3],
                                                  axes.POSITION_STORIES
                                                  .get(p[0], "")]
                                                 for p in a["positions"]],
                                   "subaxes": a.get("subaxes", [])}
                                  for a in reg["axes"]],
                         "cond_stories": {"%s|%s" % k: v for k, v in
                                          axes.CONDITIONAL_STORIES.items()},
                         "conditionals": {k: {pp: t for pp, t in v.items()}
                                          for k, v in
                                          reg["conditionals"].items()},
                         "impact_classes": axes.IMPACT_CLASS,
                         "changelog": reg["changelog"]},
        "bands.json": {"annual": b_year, "monthly": b_month},
        "marginals.json": {"today": marg, "history": weights["history"]},
        "mainline.json": mainline_out,
        "exemplars.json": {"lines": ex},
        "ensemble2k.json": {"lines": ens},
        "crisis.json": {"crises": crises},
        "delta.json": {"date": today,
                       "entries": weights.get("evidence_log", [])[-40:],
                       "moved": moved, "attributable": attributable},
        "claims.json": {"claims": claims},
    }
    for name, data in outputs.items():
        with open(os.path.join(STAGED_F, name), "w") as f:
            json.dump(data, f, separators=(",", ":"))
    sizes = {n: os.path.getsize(os.path.join(STAGED_F, n)) // 1024
             for n in outputs}
    return {"date": today, "kb": sizes, "mainline": ml,
            "grounding": grounding["counts"]}


def _selftest():
    import copy, tempfile
    # widening spreads toward uniform and preserves normalization
    w = {"axes": {"T": {"T1": 0.6, "T2": 0.3, "T3": 0.08, "T4": 0.02}}}
    reg = widened_registry({"axes": w["axes"], "version": "x"},
                          {"T": 1.25})
    pri = {p[0]: p[2] for p in axes.axis(reg, "T")["positions"]}
    assert abs(sum(pri.values()) - 1.0) < 1e-9
    assert pri["T1"] < 0.6 and pri["T4"] > 0.02
    # unmentioned axes keep seed priors
    priC = {p[0]: p[2] for p in axes.axis(reg, "C")["positions"]}
    assert abs(sum(priC.values()) - 1.0) < 1e-6
    return 1


if __name__ == "__main__":
    n = _selftest()
    print("forecast_emit selftest: %d groups passed" % n)
    out = emit()
    print(json.dumps(out, indent=1))
