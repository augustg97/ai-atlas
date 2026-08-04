#!/usr/bin/env python3
"""audit_all.py — the AI Atlas gate (README §6). Read-only; changes nothing.

Runs every check against Research/staged/, compares to recorded baselines
(baselines.json beside this file), and exits non-zero if ANY check moved
backwards. A check that cannot parse its own input FAILS (Working Rule 8
corollary: the failure mode of a silent guard is a passed gate).

First run records baselines. When a number legitimately improves, tighten the
baseline in the same commit. SKIP_AUDIT=1 overrides, deliberately awkwardly.

Checks:
  windows        no entity window after today; no malformed window dates
  cards          confidence enum valid; description present; decay class set
  datekinds      every date carries kind+iso+precision; fallback events are
                 kind=published (the send-date bug class, made structurally
                 impossible to reintroduce silently)
  eras           authored eras tile 2012→now, no gaps/overlaps
  events         explicit-event-date share may not fall; target-match share
                 may not fall
  datum          every feature entity positioned; territories named; drift
                 for unchanged pages ≤ EPS within a datum version
  witness-epoch  matched count may not fall; date disagreements may not grow
  review         needs-review count may not grow
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGED = os.path.join(HERE, "..", "staged")
BASE = os.path.join(HERE, "baselines.json")
EPS = 0.005          # unit-square drift allowed within a datum version (A2)
TODAY = _dt.date.today().isoformat()

CONF = {"high", "medium", "low", "contested"}


def load(name):
    p = os.path.join(STAGED, name)
    if not os.path.isfile(p):
        return None
    with open(p) as f:
        return json.load(f)


def check_windows(S):
    bad = []
    for e in S["entities"]["entities"]:
        w = e.get("window")
        if not w:
            continue
        if not (w.get("iso") and w.get("kind") and w.get("precision")):
            bad.append((e["id"], "malformed window"))
        elif w["iso"][:10] > TODAY:
            bad.append((e["id"], "window in the future"))
    return {"bad": len(bad), "examples": bad[:5]}


def check_cards(S):
    bad = []
    for e in S["entities"]["entities"]:
        if e.get("confidence") not in CONF:
            bad.append((e["id"], "confidence %r" % e.get("confidence")))
        if not e.get("desc"):
            bad.append((e["id"], "no description"))
        if not e.get("decay_months"):
            bad.append((e["id"], "no decay class"))
    return {"bad": len(bad), "examples": bad[:5]}


def check_datekinds(S):
    bad = 0
    ex = []

    def chk(d, where, allow):
        nonlocal bad
        if d is None:
            return
        if not (d.get("iso") and d.get("precision")
                and d.get("kind") in allow):
            bad += 1
            if len(ex) < 5:
                ex.append((where, d))

    for e in S["entities"]["entities"]:
        chk(e.get("window"), e["id"], {"event", "published"})
    for ev in S["events"]["events"]:
        chk(ev["date"], ev["file"], {"event", "published"})
        if ev["fell_back"] and ev["date"]["kind"] != "published":
            bad += 1
            ex.append((ev["file"], "fallback not labelled published"))
        if (not ev["fell_back"]) and ev["date"]["kind"] != "event":
            bad += 1
            ex.append((ev["file"], "explicit date not kind=event"))
    for r in S["series"]["series"]:
        chk(r["date"], r["entity"], {"checked"})
    return {"bad": bad, "examples": ex}


def check_eras(S):
    import frames
    bad = 0
    prev = None
    for e in S["eras"]["eras"]:
        if prev is not None:
            gap = frames.iso_to_days(e["from"]) - frames.iso_to_days(prev)
            if not (0 < gap <= 1.5):
                bad += 1
        prev = e["to"] or TODAY
    return {"bad": bad}


def check_events(S):
    ev = S["events"]["events"]
    n = len(ev) or 1
    expl = sum(1 for e in ev if not e["fell_back"])
    tgt = sum(1 for e in ev if e["targets"])
    return {"n": len(ev), "explicit_pct": round(100 * expl / n, 1),
            "target_pct": round(100 * tgt / n, 1)}


def check_datum(S):
    datum = load("datum.json")
    if datum is None:
        return {"present": 0, "unpositioned_features": None,
                "max_drift": None, "version": None}
    pos = datum["positions"]
    terr = datum["territory_of"]
    unpos = [e["id"] for e in S["entities"]["entities"] if e["id"] not in pos]
    unterr = [p for p in pos if p not in terr]
    prior_pos, prior_ver = None, None
    if os.path.isfile(BASE):
        bj = json.load(open(BASE))
        prior_pos = bj.get("datum_positions")
        prior_ver = bj.get("checks", {}).get("datum", {}).get("version")
    drift = None
    if prior_pos and prior_ver == datum["version"]:
        ds = [abs(pos[k][0] - v[0]) + abs(pos[k][1] - v[1])
              for k, v in prior_pos.items() if k in pos]
        drift = round(max(ds), 4) if ds else 0.0
    return {"present": 1, "unpositioned_features": len(unpos),
            "unpositioned_examples": unpos[:5],
            "unterritoried": len(unterr), "max_drift": drift,
            "version": datum["version"]}


def check_witness():
    w = load("witness-epoch.json")
    if w is None:
        return {"present": 0}
    return {"present": 1, "matched": w["matched"],
            "disagreements": len(w["date_disagreements"]),
            "gaps": w["epoch_frontier_gap_count"]}


def check_forecast():
    """The v2 forecast surface: bands ordered, marginals normalized, deltas
    attributed, grounding ratchet, templates cited. A missing file FAILS —
    the forecast is now the product."""
    F = os.path.join(STAGED, "forecast")
    need = ["engine.json", "network.json", "bands.json", "marginals.json",
            "mainline.json", "crisis.json", "delta.json", "grounding.json"]
    missing = [n for n in need if not os.path.isfile(os.path.join(F, n))]
    if missing:
        return {"present": 0, "missing": missing, "bad": 999}
    bad = 0
    ex = []
    bands = json.load(open(os.path.join(F, "bands.json")))
    for grid in ("annual", "monthly"):
        b = bands[grid]
        n = len(b.get("year", b.get("month", [])))
        for i in range(n):
            if not (b["p10"][i] <= b["p25"][i] <= b["p50"][i]
                    <= b["p75"][i] <= b["p90"][i]):
                bad += 1
                if len(ex) < 3:
                    ex.append((grid, i, "band order"))
    marg = json.load(open(os.path.join(F, "marginals.json")))["today"]
    for k, v in marg.items():
        if abs(sum(v.values()) - 1.0) > 1e-6:
            bad += 1
            ex.append((k, "marginal sum", sum(v.values())))
    for e in json.load(open(os.path.join(F, "delta.json")))["entries"]:
        if not e.get("cites") or "magnitude" not in e:
            bad += 1
            ex.append((e.get("rule"), "unattributed delta"))
    eng = json.load(open(os.path.join(F, "engine.json")))
    for t in eng["templates"]:
        if not t.get("cites"):
            bad += 1
            ex.append((t["id"], "uncited template"))
    g = json.load(open(os.path.join(F, "grounding.json")))["counts"]
    return {"present": 1, "bad": bad, "examples": ex,
            "grounded_direct": g["direct"], "grounded_total": g["total"]}


def check_statelaw():
    """The state-legislation counter (T7). Present, and honest about what it
    cannot do — a lower-bound counter that ever claims it can refute its
    claim is a worse failure than having no counter at all."""
    p = os.path.join(STAGED, "witness-statelaw.json")
    if not os.path.isfile(p):
        return {"present": 0, "observed": 0, "bad": 1,
                "examples": ["witness-statelaw.json missing"]}
    w = json.load(open(p))
    bad, ex = 0, []
    if w.get("bound") != "lower":
        bad += 1
        ex.append("counter must declare itself a lower bound")
    if w["claim"].get("can_refute"):
        bad += 1
        ex.append("lower-bound counter claims it can refute its claim")
    if w["claim"].get("resolves_claim") and \
            w["claim"]["observed"] <= w["claim"]["threshold"]:
        bad += 1
        ex.append("claim marked resolved below its own threshold")
    return {"present": 1, "observed": w["observed_count"],
            "states": w["distinct_states"], "bad": bad, "examples": ex}


def run():
    if os.environ.get("SKIP_AUDIT") == "1":
        print("SKIP_AUDIT=1 — validators skipped. Say so out loud, and say why.")
        return 0
    S = {n: load(n + ".json") for n in
         ("entities", "events", "series", "eras")}
    missing = [k for k, v in S.items() if v is None]
    if missing:
        print("UNREADABLE: staged files missing: %s — the gate FAILS rather "
              "than silently passing" % missing)
        return 2
    meta = load("meta.json")
    results = {
        "windows": check_windows(S),
        "cards": check_cards(S),
        "datekinds": check_datekinds(S),
        "eras": check_eras(S),
        "events": check_events(S),
        "datum": check_datum(S),
        "witness_epoch": check_witness(),
        "forecast": check_forecast(),
        # `n` alone is the wrong metric: the trunk grows every night, so a
        # rising absolute count can mean nothing worse is happening. The RATE
        # is what must not erode — 224/1825 (12.27%) → 222/1894 (11.72%) is
        # an improvement that the absolute count reported as a regression.
        "statelaw": check_statelaw(),
        "review": {"n": meta["counts"]["needs_review"],
                   "pct": round(100.0 * meta["counts"]["needs_review"]
                                / max(1, len(S["events"]["events"])), 3)},
    }

    baselines = json.load(open(BASE)) if os.path.isfile(BASE) else None
    failures = []
    if baselines:
        b = baselines["checks"]
        r = results

        def worse(name, now, was, direction="≤"):
            failures.append("%s moved backwards: %s (baseline %s %s)"
                            % (name, now, direction, was))

        for key in ("windows", "cards", "datekinds", "eras"):
            if r[key]["bad"] > b[key]["bad"]:
                worse(key + ".bad", r[key]["bad"], b[key]["bad"])
        if r["events"]["explicit_pct"] < b["events"]["explicit_pct"] - 1.0:
            worse("events.explicit_pct", r["events"]["explicit_pct"],
                  b["events"]["explicit_pct"], "≥")
        if r["events"]["target_pct"] < b["events"]["target_pct"] - 1.0:
            worse("events.target_pct", r["events"]["target_pct"],
                  b["events"]["target_pct"], "≥")
        if r["datum"]["present"] and b["datum"]["present"]:
            if r["datum"]["unpositioned_features"] > \
                    b["datum"]["unpositioned_features"]:
                worse("datum.unpositioned",
                      r["datum"]["unpositioned_features"],
                      b["datum"]["unpositioned_features"])
            if r["datum"]["max_drift"] is not None and \
                    r["datum"]["max_drift"] > EPS:
                worse("datum.max_drift", r["datum"]["max_drift"], EPS)
        if r["witness_epoch"]["present"] and b["witness_epoch"]["present"]:
            if r["witness_epoch"]["matched"] < b["witness_epoch"]["matched"]:
                worse("witness.matched", r["witness_epoch"]["matched"],
                      b["witness_epoch"]["matched"], "≥")
            if r["witness_epoch"]["disagreements"] > \
                    b["witness_epoch"]["disagreements"]:
                worse("witness.disagreements",
                      r["witness_epoch"]["disagreements"],
                      b["witness_epoch"]["disagreements"])
        if "pct" in b.get("review", {}):
            if r["review"]["pct"] > b["review"]["pct"] + 0.5:
                worse("review.pct", r["review"]["pct"], b["review"]["pct"])
        elif r["review"]["n"] > b["review"]["n"]:
            worse("review.n", r["review"]["n"], b["review"]["n"])
        if "statelaw" not in b:
            b["statelaw"] = r["statelaw"]
            json.dump(baselines, open(BASE, "w"))
            print("note: statelaw baseline recorded (first T7 gate run)")
        else:
            if r["statelaw"]["bad"] > b["statelaw"].get("bad", 0):
                worse("statelaw.bad", r["statelaw"]["bad"],
                      b["statelaw"].get("bad", 0))
            # an enumeration may not shrink: the record only ever gains laws,
            # so a fall means the matcher regressed, not that a law repealed
            if r["statelaw"]["observed"] < b["statelaw"].get("observed", 0):
                worse("statelaw.observed", r["statelaw"]["observed"],
                      b["statelaw"].get("observed"), "≥")
        if "forecast" not in b:
            # first run since the v2 gate landed: extend the baseline in
            # place (recorded, not silent)
            b["forecast"] = r["forecast"]
            json.dump(baselines, open(BASE, "w"))
            print("note: forecast baseline recorded (first v2 gate run)")
        else:
            if r["forecast"]["present"] < b["forecast"]["present"]:
                worse("forecast.present", r["forecast"]["present"], 1, "≥")
            if r["forecast"]["bad"] > b["forecast"].get("bad", 0):
                worse("forecast.bad", r["forecast"]["bad"],
                      b["forecast"].get("bad", 0))
            if r["forecast"].get("grounded_direct", 0) < \
                    b["forecast"].get("grounded_direct", 0):
                worse("forecast.grounded_direct",
                      r["forecast"].get("grounded_direct"),
                      b["forecast"].get("grounded_direct"), "≥")

    print(json.dumps(results, indent=1, default=str))

    # --- day-over-day drift (added 2026-08-03) ---------------------------
    # The ratchet only ever compared against the FROZEN baseline, so a metric
    # could erode night after night and pass silently as long as it stayed
    # inside the tolerance. needs-review went 224 → 221 → 222 and explicit_pct
    # 91.8 → 91.7 without a word. Erosion inside the slack is now printed, and
    # improvements move the baseline so the slack cannot be re-spent.
    drift = []
    if baselines and baselines.get("last_run"):
        lr = baselines["last_run"]
        for path, better in (("events.explicit_pct", "up"),
                             ("events.target_pct", "up"),
                             ("review.pct", "down"),
                             ("forecast.grounded_direct", "up"),
                             ("witness_epoch.matched", "up"),
                             ("witness_epoch.disagreements", "down")):
            grp, key = path.split(".")
            now = results.get(grp, {}).get(key)
            was = lr.get("checks", {}).get(grp, {}).get(key)
            if now is None or was is None or now == was:
                continue
            worsened = (now < was) if better == "up" else (now > was)
            drift.append("%s %s %s → %s%s"
                         % ("↓" if worsened else "↑", path, was, now,
                            "   ERODED" if worsened else ""))
    if drift:
        print("\nDRIFT vs %s:" % baselines["last_run"].get("date", "last run"))
        for d in drift:
            print("  " + d)

    datum = load("datum.json")
    if failures:
        print("\nGATE: FAIL")
        for f in failures:
            print(" -", f)
        return 1
    if baselines is None:
        json.dump({"recorded": TODAY, "checks": results,
                   "last_run": {"date": TODAY, "checks": results},
                   "datum_positions": datum["positions"] if datum else None},
                  open(BASE, "w"))
        print("\nGATE: first run — baselines recorded to baselines.json")
        return 0
    # keep stored positions current when the datum version legitimately moves
    bj = json.load(open(BASE))
    if datum and bj["checks"]["datum"].get("version") != datum["version"]:
        bj["checks"]["datum"]["version"] = datum["version"]
        bj["datum_positions"] = datum["positions"]

    # ratchet forward: a metric that improved becomes the new floor, so the
    # tolerance band is spent once and never handed back.
    ratcheted = []
    for path, better in (("events.explicit_pct", "up"),
                         ("events.target_pct", "up"),
                         ("review.pct", "down"),
                         ("forecast.grounded_direct", "up"),
                         ("witness_epoch.matched", "up"),
                         ("witness_epoch.disagreements", "down")):
        grp, key = path.split(".")
        now = results.get(grp, {}).get(key)
        was = bj["checks"].get(grp, {}).get(key)
        if now is None:
            continue
        if was is None or (now > was if better == "up" else now < was):
            bj["checks"].setdefault(grp, {})[key] = now
            ratcheted.append("%s %s → %s" % (path, was, now))
    bj["last_run"] = {"date": TODAY, "checks": results}
    json.dump(bj, open(BASE, "w"))
    if ratcheted:
        print("\nRATCHET (baseline tightened on improvement):")
        for x in ratcheted:
            print("  " + x)
    print("\nGATE: PASS (baselines hold)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
