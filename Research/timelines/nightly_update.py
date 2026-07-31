#!/usr/bin/env python3
"""nightly_update.py — the morning the forecast breathes (register T4).

Runs after the trunk emit. Steps:
  1. load weights.json + the trunk's staged events.json;
  2. select events newer than the last update date;
  3. match each against EVIDENCE_RULES (section + text patterns);
     corroboration = distinct source URLs; novelty = rule applications in
     the trailing 30 days;
  4. apply tiered impacts (axes.apply_evidence) under the 7-day soft squash;
  5. bank unmatched events as RESIDUE — the raw material of the weekly
     schema review, which (Mondays) auto-adds a monitoring sub-axis when a
     residue cluster is large and sustained, logged for August's post-hoc
     review (decision of record: autonomy with attribution, never silence);
  6. write weights.json + a human-readable morning report.

Deterministic given (events, weights). stdlib only.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import axes

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS = os.path.join(HERE, "weights.json")
EVENTS = os.path.join(HERE, "..", "staged", "events.json")
REPORTS = os.path.join(HERE, "..", "nightly-reports")

RESIDUE_CLUSTER_MIN = 12       # unexplained events in one section, 7 days
RESIDUE_WINDOW_DAYS = 7


def rule_matches(rule, ev):
    m = rule["match"]
    if "section" in m and ev.get("section") != m["section"]:
        return False
    if "kind" in m and ev.get("date", {}).get("kind") != m["kind"]:
        return False
    if "text_any" in m:
        txt = (ev.get("text") or "").lower()
        if not any(t.lower() in txt for t in m["text_any"]):
            return False
    return True


def weights_to_reg(weights):
    import copy
    reg = copy.deepcopy(axes.REGISTRY)
    for a in reg["axes"]:
        w = weights["axes"].get(a["key"])
        if w:
            wn = axes.normalized(w)
            a["positions"] = [(p[0], p[1], wn[p[0]], p[3])
                              for p in a["positions"]]
    return reg


def reg_to_weights(reg, weights):
    for a in reg["axes"]:
        weights["axes"][a["key"]] = {p[0]: p[2] for p in a["positions"]}


def weekly_cum(weights, today):
    """Per-axis absolute drift over the trailing 7 days, from the log."""
    cutoff = (today - _dt.timedelta(days=7)).isoformat()
    cum = {}
    for e in weights.get("evidence_log", []):
        if e.get("date", "") >= cutoff:
            for k, v in e.get("applied", {}).items():
                ax = k.split(".")[0]
                cum[ax] = cum.get(ax, 0.0) + abs(v)
    return cum


def repeat_count(weights, rule_id, today):
    cutoff = (today - _dt.timedelta(days=30)).isoformat()
    return sum(1 for e in weights.get("evidence_log", [])
               if e.get("rule") == rule_id and e.get("date", "") >= cutoff)


def schema_review(weights, today):
    """Mondays: cluster the residue; a large sustained cluster becomes a
    monitoring sub-axis on its nearest axis — applied autonomously, origin-
    logged, surfaced in the morning report for review."""
    if today.weekday() != 0:
        return None
    cutoff = (today - _dt.timedelta(days=RESIDUE_WINDOW_DAYS)).isoformat()
    recent = [r for r in weights.get("residue", []) if r["date"] >= cutoff]
    by_sec = {}
    for r in recent:
        by_sec.setdefault(r["section"], []).append(r)
    SECTION_AXIS = {
        "AI Industry & Markets": "E", "Compute, Chips & Infrastructure": "S",
        "Frontier Models & Capabilities": "T",
        "AI Safety, Alignment & Interpretability": "A",
        "AI Litigation, Liability & Enforcement": "C",
        "Federal AI Policy & Agency Action": "C",
        "International AI Regulation": "C",
        "U.S. State AI Legislation": "C",
        "National Security & Geopolitics": "C",
        "Labor, Society & Democratic Institutions": "D",
        "Agentic AI & Coding": "T", "AI Adoption by Industry": "D",
        "AI Standards & Safety Frameworks": "C",
    }
    added = []
    existing = {s["key"] for a in axes.REGISTRY["axes"]
                for s in a.get("subaxes", [])}
    for sec, items in by_sec.items():
        if len(items) < RESIDUE_CLUSTER_MIN:
            continue
        ax = SECTION_AXIS.get(sec)
        if not ax:
            continue
        key = "%s.watch-%s" % (ax, sec.lower().split(" ")[0].strip(".,&"))
        if key in existing:
            continue
        added.append({"axis": ax, "subaxis": {
            "key": key, "name": "monitoring: %s residue" % sec,
            "cites": [], "origin": "auto: weekly schema review %s — %d "
            "unexplained events in %d days; FOR AUGUST'S REVIEW"
            % (today.isoformat(), len(items), RESIDUE_WINDOW_DAYS)}})
    return added or None


def update(today=None):
    today = today or _dt.date.today()
    weights = json.load(open(WEIGHTS)) if os.path.isfile(WEIGHTS) else None
    if weights is None:
        import forecast_emit
        weights = forecast_emit.load_weights()
    events = json.load(open(EVENTS))["events"]
    last = weights.get("date", "2026-07-30")
    fresh = [e for e in events
             if e["date"]["iso"][:10] > last and
             e["date"]["iso"][:10] <= today.isoformat()]
    reg = weights_to_reg(weights)
    log = weights.setdefault("evidence_log", [])
    cum = weekly_cum(weights, today)
    applied_n, residue_n = 0, 0
    for ev in fresh:
        matched = False
        for rule in axes.EVIDENCE_RULES:
            if rule_matches(rule, ev):
                matched = True
                k = repeat_count(weights, rule["id"], today)
                entry_before = len(log)
                axes.apply_evidence(reg, rule, log,
                                    sources=max(1, len(ev.get("urls", []))),
                                    repeat_k=k, weekly_cum=cum)
                for e2 in log[entry_before:]:
                    e2["date"] = today.isoformat()
                    e2["driver"] = ev.get("text", "")[:140]
                    e2["driver_urls"] = ev.get("urls", [])[:3]
                applied_n += 1
                break
        if not matched:
            weights.setdefault("residue", []).append(
                {"date": ev["date"]["iso"][:10],
                 "section": ev.get("section", "?"),
                 "text": ev.get("text", "")[:120]})
            residue_n += 1
    weights["residue"] = weights.get("residue", [])[-500:]
    weights["evidence_log"] = log[-400:]
    reg_to_weights(reg, weights)
    weights["date"] = today.isoformat()

    additions = schema_review(weights, today)
    if additions:
        for add in additions:
            for a in axes.REGISTRY["axes"]:
                if a["key"] == add["axis"]:
                    a.setdefault("subaxes", []).append(add["subaxis"])
        weights.setdefault("schema_log", []).extend(additions)

    json.dump(weights, open(WEIGHTS, "w"), indent=1)
    os.makedirs(REPORTS, exist_ok=True)
    rp = os.path.join(REPORTS, "%s-forecast.md" % today.isoformat())
    with open(rp, "w") as f:
        f.write("# Forecast update — %s\n\n" % today.isoformat())
        f.write("- fresh events considered: %d\n" % len(fresh))
        f.write("- evidence applications: %d\n" % applied_n)
        f.write("- residue (unexplained): %d\n" % residue_n)
        if additions:
            f.write("\n## SCHEMA ADDITIONS (auto — for August's review)\n")
            for add in additions:
                f.write("- %s ← %s\n" % (add["axis"],
                                          add["subaxis"]["origin"]))
        for e in weights["evidence_log"][-applied_n:] if applied_n else []:
            f.write("\n- %s [%s ×%.4f] %s\n" %
                    (e["rule"], e["impact_class"], e["magnitude"],
                     e.get("driver", "")[:100]))
    return {"fresh": len(fresh), "applied": applied_n, "residue": residue_n,
            "schema_additions": len(additions or [])}


def _selftest():
    ev = {"section": "National Security & Geopolitics",
          "text": "China vows to retaliate over export controls",
          "date": {"kind": "event", "iso": "2026-07-30"}, "urls": ["a", "b"]}
    r = [x for x in axes.EVIDENCE_RULES if x["id"] == "ev-export-retaliation"][0]
    assert rule_matches(r, ev)
    assert not rule_matches(r, dict(ev, section="AI Industry & Markets"))
    # weights round-trip preserves normalization, on EVERY axis. The fixture
    # is derived from the registry, never hardcoded: the registry is designed
    # to grow (C5 by hand, sub-axes by the Monday review), and a literal
    # position list here goes stale the moment it does — which is exactly how
    # this selftest broke the 2026-07-31 chain with KeyError: 'C5'.
    w = {"axes": {a["key"]: {p[0]: 1.0 + i
                             for i, p in enumerate(a["positions"])}
                  for a in axes.REGISTRY["axes"]},
         "evidence_log": []}
    reg = weights_to_reg(w)
    reg_to_weights(reg, w)
    for _k, _v in w["axes"].items():
        assert abs(sum(_v.values()) - 1.0) < 1e-9, _k
    # schema review triggers only on clustered sustained residue
    wt = {"residue": [{"date": "2026-07-29", "section":
                       "Agentic AI & Coding", "text": "x"}] * 15}
    adds = schema_review(wt, _dt.date(2026, 8, 3))          # a Monday
    assert adds and adds[0]["axis"] == "T"
    assert "REVIEW" in adds[0]["subaxis"]["origin"]
    assert schema_review(wt, _dt.date(2026, 8, 4)) is None  # not Monday
    return 3


if __name__ == "__main__":
    n = _selftest()
    print("nightly_update selftest: %d groups passed" % n)
    out = update()
    print(json.dumps(out, indent=1))
