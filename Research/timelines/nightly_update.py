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
import hashlib
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

# --- the day boundary (fixed 2026-08-03) -----------------------------------
# The selector used to be a WATERMARK: `event.date > weights["date"]`, with
# weights["date"] advanced to today on every run. The wiki, however, ingests
# all day, and the run fires at 10:47. Any event whose EVENT date was already
# past when it arrived was therefore skipped permanently. Measured over the
# first four mornings: 41 of 49 events on settled days (84%) were never
# offered to the rules — including Illinois HB 5511, the only item in the
# machine's operating life that satisfied a rule outright.
#
# It is now a LEDGER: an event is fresh if we have never considered it, and
# its event date is inside the lookback window. Late arrivals get picked up
# by the next run instead of vanishing.
LOOKBACK_DAYS = 14             # how long a late arrival stays eligible
NIGHTLY_EPOCH = "2026-07-31"   # the first nightly run; events before it
#                                informed the priors through wiki_grounding,
#                                so replaying them would double-count.
SEEN_CAP = 3000                # >> events per lookback window (~25/day × 14)


def fingerprint(ev):
    """Stable identity for an event. The trunk carries no id, so this is
    (event date, section, opening prose) — verified collision-free across
    all 1,894 events in the 2026-08-03 trunk."""
    raw = "%s|%s|%s" % (ev["date"]["iso"][:10], ev.get("section", ""),
                        (ev.get("text") or "")[:200])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def select_fresh(events, weights, today):
    """Every event we have not already considered, inside the window."""
    seen = set(weights.get("seen", []))
    floor = max((today - _dt.timedelta(days=LOOKBACK_DAYS)).isoformat(),
                NIGHTLY_EPOCH)
    out = []
    for e in events:
        d = e["date"]["iso"][:10]
        if d < floor or d > today.isoformat():
            continue
        if fingerprint(e) in seen:
            continue
        out.append(e)
    return out


def rule_matches(rule, ev):
    """Delegates to the structured matcher in axes.py (r1). Kept as a name
    so callers and selftests have one entry point."""
    return axes.match_event(rule, ev)


def weights_to_reg(weights):
    import copy
    reg = copy.deepcopy(axes.REGISTRY)
    axes.apply_schema_log(reg, weights.get("schema_log"))
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
    # the log is the durable record of past additions; without consulting it
    # the review would re-propose the same sub-axis every Monday forever.
    existing = {s["key"] for a in axes.REGISTRY["axes"]
                for s in a.get("subaxes", [])}
    existing |= {e["subaxis"]["key"] for e in weights.get("schema_log", [])}
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

    # one-time migration off the watermark selector. The events the old
    # selector dropped are still inside the lookback window, so they are
    # recovered on this run rather than staying lost — and the r0 residue is
    # ARCHIVED, not deleted, because it was banked by a matcher that has
    # since been repaired and will be re-derived below.
    migrated = "seen" not in weights
    if migrated:
        weights["seen"] = []
        weights["residue_r0"] = weights.get("residue", [])
        weights["residue"] = []
        weights["version"] = axes.REGISTRY_VERSION
        weights["migration"] = {
            "date": today.isoformat(),
            "from": "watermark selector + r0 substring matcher",
            "to": "seen-ledger selector + r1 structured matcher",
            "archived_residue": len(weights["residue_r0"])}

    fresh = select_fresh(events, weights, today)
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
                 "section": axes.canon_section(ev.get("section")) or "?",
                 "text": ev.get("text", "")[:120],
                 "fp": fingerprint(ev)})
            residue_n += 1

    # mark everything considered — matched or not — so a late arrival is
    # picked up exactly once and never re-applied on a later night.
    seen = list(weights.get("seen", []))
    seen.extend(fingerprint(e) for e in fresh)
    weights["seen"] = seen[-SEEN_CAP:]

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
        # late arrivals are the whole point of the ledger — name them, so a
        # silent day-boundary loss can never look like a quiet night again.
        late = [e for e in fresh
                if e["date"]["iso"][:10] < today.isoformat()]
        f.write("- of which late arrivals recovered (event date < today): "
                "%d\n" % len(late))
        if late:
            span = sorted(e["date"]["iso"][:10] for e in late)
            f.write("  - recovered event dates: %s … %s\n"
                    % (span[0], span[-1]))
        if migrated:
            f.write("\n## SELECTOR MIGRATION (one-time, for August's "
                    "review)\n")
            f.write("- watermark → seen-ledger; r0 substring matcher → r1 "
                    "structured matcher\n")
            f.write("- %d r0 residue entries archived to `residue_r0` in "
                    "weights.json (not deleted); residue re-derived under "
                    "the repaired matcher\n"
                    % weights["migration"]["archived_residue"])
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
            "recovered_late": len([e for e in fresh
                                   if e["date"]["iso"][:10] <
                                   today.isoformat()]),
            "seen_ledger": len(weights["seen"]),
            "migrated": bool(migrated),
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

    # --- the day boundary: regression test for the Illinois HB 5511 loss ---
    # Reproduce the exact shape of the failure. An event dated 07-31 arrives
    # in the trunk only after the 07-31 run has finished; the 08-01 run must
    # still see it. Under the watermark selector it was gone forever.
    hb = {"date": {"iso": "2026-07-31", "kind": "event"},
          "section": "U.S. State AI Legislation",
          "text": "Illinois Gov. JB Pritzker signed House Bill 5511, the "
                  "Children's Social Media Safety Act, on July 31, 2026.",
          "urls": ["a", "b"]}
    w0 = {"date": "2026-07-31", "seen": []}
    assert select_fresh([hb], w0, _dt.date(2026, 8, 1)) == [hb], \
        "late arrival must survive the day boundary"
    # and it fires the repaired rule rather than banking as residue
    law = [r for r in axes.EVIDENCE_RULES
           if r["id"] == "ev-state-law-enacted"][0]
    assert rule_matches(law, hb)
    # considered exactly once: after it is marked seen, it is not fresh again
    w1 = {"date": "2026-08-01", "seen": [fingerprint(hb)]}
    assert select_fresh([hb], w1, _dt.date(2026, 8, 2)) == []
    # the lookback floor bounds replay in both directions
    assert select_fresh([hb], w0, _dt.date(2026, 9, 1)) == []   # too old
    old = {"date": {"iso": "2026-07-01", "kind": "event"},
           "section": "U.S. State AI Legislation", "text": "x", "urls": []}
    assert select_fresh([old], w0, _dt.date(2026, 7, 5)) == [], \
        "nothing before the nightly epoch may replay into the priors"
    future = {"date": {"iso": "2026-08-09", "kind": "event"},
              "section": "U.S. State AI Legislation", "text": "y",
              "urls": []}
    assert select_fresh([future], w0, _dt.date(2026, 8, 3)) == []
    # fingerprints separate near-identical events and are stable
    a1 = dict(hb); a2 = dict(hb, section="AI Industry & Markets")
    assert fingerprint(a1) != fingerprint(a2)
    assert fingerprint(a1) == fingerprint(dict(hb))
    return 5


if __name__ == "__main__":
    n = _selftest()
    print("nightly_update selftest: %d groups passed" % n)
    out = update()
    print(json.dumps(out, indent=1))
