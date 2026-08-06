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
import re
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


# --- incidents (r2, 2026-08-06) --------------------------------------------
# The machine could not tell four digests carrying one Illinois signing from
# three unrelated funding rounds landing on one night. Both looked like "the
# same rule fired N times", so novelty decay punished them identically — and
# on 2026-08-06 it discounted SpaceX's Terafab, Mirendil's Google Cloud deal
# and Discovery Loop's round against each other for no reason but arrival
# order. The two cases want opposite treatment: repeated REPORTS are
# corroboration and should raise confidence in one incident; repeated
# INCIDENTS are new evidence and should each move the model.
#
# An INCIDENT is one development in the world. Reports are linked into one
# when they share a source URL, when the trunk marks one as a follow-up
# (`update: true`, 145 of 1942 events — the wiki already knows), or when
# their salient content overlaps enough. Ground truth used to set the
# threshold, both from the record: the three 2026-07-06 reports of Pritzker
# signing SB 315 are ONE incident; the three 2026-08-06 capital commitments
# are THREE.
#
# Two things were measured and both changed the design:
#
#   AGGREGATOR URLS. A shared link is not identity. `newsletter.safe.ai`'s
#   AISN-77 issue is cited by five unrelated events and `transformernews.ai`
#   by four, because a newsletter covers many stories. Linking on any shared
#   URL chained 28 unrelated developments — an OpenAI disclosure, a Gemini
#   release, a court ruling, Illinois SB 315 — into one "incident". Only a
#   url cited by at most URL_DF_MAX events is identity evidence.
#
#   RARITY, NOT OVERLAP. Two independent write-ups of the Pritzker signing
#   share only 0.30 of their salient tokens: different reporters choose
#   different words. What they do share is "pritzker", "315", "illinois" —
#   tokens that are rare in the corpus. A flat Jaccard cannot separate that
#   from two unrelated items that both say "openai" and "2026". Similarity
#   is therefore IDF-weighted: a shared bill number counts, a shared year
#   does not.
#
# And clustering is greedy against cluster REPRESENTATIVES, never transitive.
# Union-find let A~B and B~C drag in A~C; a report now has to look like the
# story it is joining, not merely like something already in it.
#
# WHERE THIS DELIBERATELY STOPS. Two independent write-ups of the Pritzker
# signing score 0.269; an Alphabet chip story and an Alphabet share-price
# story score 0.257. Three hundred characters of prose do not separate those,
# and a threshold that split them would be fitted to two examples. So the
# resolver merges only on evidence it can stand behind — a shared non-digest
# article, the trunk's own follow-up flag, or near-duplicate prose — and
# UNDER-merges by design. Leaving two reports as two incidents costs a little
# double-count, which the novelty floor now handles gracefully; merging two
# real developments into one silently deletes evidence. Every collapse is
# reported each morning so the choice stays auditable.
INCIDENT_WINDOW_DAYS = 14
INCIDENT_SIM = 0.45            # near-duplicate prose, on its own
INCIDENT_SIM_URL = 0.20        # when they also share a non-digest article
INCIDENT_SIM_UPD = 0.36        # when the trunk marks one a follow-up
URL_DF_MAX = 2                 # a link in more events than this is a digest
_STOP = frozenset("""about after also amid among announced been before being
between both could during each first from have into more most other over
said says some such than that their them then there these they this those
through under until were what when where which while will with would year
years company companies report reports reported according including new
would also""".split())


def salient(ev):
    """The tokens that identify WHICH development this is: long words, and
    anything carrying a digit (bill numbers, dollar figures, dates)."""
    txt = (ev.get("text") or "").lower()
    out = set()
    for w in re.findall(r"[a-z0-9][a-z0-9\-\.$]*", txt):
        w = w.strip(".-")
        if any(c.isdigit() for c in w):
            out.add(w)
        elif len(w) >= 5 and w not in _STOP:
            out.add(w)
    return out


def domains(ev):
    """Distinct publishers behind an event. Four links to one newsroom are
    one source; r1 counted them as four and inflated corroboration."""
    out = set()
    for u in (ev.get("urls") or []):
        m = re.match(r"https?://([^/]+)", u)
        if m:
            host = m.group(1).lower()
            if host.startswith("www."):
                host = host[4:]
            out.add(host)
    return out


def corpus_stats(corpus):
    """Token IDF and URL document-frequency over a reference corpus."""
    import math
    n = max(1, len(corpus))
    tdf, udf = {}, {}
    for e in corpus:
        for t in salient(e):
            tdf[t] = tdf.get(t, 0) + 1
        for u in {u.split("?")[0] for u in (e.get("urls") or [])}:
            udf[u] = udf.get(u, 0) + 1
    idf = {t: math.log(n / float(c)) for t, c in tdf.items()}
    return {"idf": idf, "udf": udf, "n": n, "default": math.log(n)}


def similarity(a, b, stats):
    """IDF-weighted Jaccard. A shared bill number or company name carries
    weight; a shared "2026" or "openai" barely moves it."""
    sa, sb = salient(a), salient(b)
    if not sa or not sb:
        return 0.0
    idf, dflt = stats["idf"], stats["default"]
    inter = sum(idf.get(t, dflt) for t in (sa & sb))
    union = sum(idf.get(t, dflt) for t in (sa | sb))
    return inter / union if union else 0.0


def anchors(ev, stats):
    """The rarest tokens in a report — bill numbers, prices, proper nouns.
    Two accounts of one development share several; two items that merely
    both mention OpenAI and 2026 share none."""
    import math
    cut = math.log(stats["n"] / 30.0)
    return {t for t in salient(ev)
            if stats["idf"].get(t, stats["default"]) >= cut}


def same_incident(a, b, stats):
    """Two reports describe one development."""
    da = abs((_dt.date.fromisoformat(a["date"]["iso"][:10])
              - _dt.date.fromisoformat(b["date"]["iso"][:10])).days)
    if da > INCIDENT_WINDOW_DAYS:
        return False
    # nothing merges without agreeing on who and what. Cheap, and it is the
    # guard that keeps a shared date or a shared company name from ever being
    # enough on its own.
    if len(anchors(a, stats) & anchors(b, stats)) < 2:
        return False
    s = similarity(a, b, stats)
    ua = {u.split("?")[0] for u in (a.get("urls") or [])}
    ub = {u.split("?")[0] for u in (b.get("urls") or [])}
    shared = {u for u in (ua & ub) if stats["udf"].get(u, 99) <= URL_DF_MAX}
    # a shared non-digest article is strong evidence, but not on its own:
    # the trunk sometimes splits one source into two entries about different
    # things, so the content still has to agree a little.
    if shared and s >= INCIDENT_SIM_URL:
        return True
    if s >= INCIDENT_SIM:
        return True
    # the trunk marks follow-ups explicitly (`update: true`), and a follow-up
    # legitimately shares less prose with its referent than two independent
    # write-ups of one event share with each other.
    return bool(a.get("update") or b.get("update")) and s >= INCIDENT_SIM_UPD


def resolve_incidents(events, corpus=None):
    """Group reports into incidents.

    Greedy against cluster REPRESENTATIVES, in input order — deterministic,
    and non-transitive by construction, which is what keeps one shared token
    from chaining a month of unrelated news into a single incident.

    Returns [{"id", "events", "rep", "sources", "urls", "reports"}]."""
    stats = corpus_stats(corpus if corpus is not None else events)
    clusters = []                 # [{"anchor": ev, "events": [...]}]
    for ev in events:
        best, best_s = None, 0.0
        for c in clusters:
            # against the ANCHOR — the event that opened the cluster, which
            # never changes. Matching against a representative that is
            # recomputed as the cluster grows lets its identity drift, and
            # drift is chaining by another name: it merged a Microsoft
            # /Mistral deal with an Anduril round that share nothing.
            if not same_incident(c["anchor"], ev, stats):
                continue
            s = similarity(c["anchor"], ev, stats)
            if best is None or s > best_s:
                best, best_s = c, s
        if best is None:
            clusters.append({"anchor": ev, "events": [ev]})
        else:
            best["events"].append(ev)
    out = []
    for c in clusters:
        doms, urls = set(), []
        for e in c["events"]:
            doms |= domains(e)
            for u in (e.get("urls") or []):
                if u not in urls:
                    urls.append(u)
        # the quoted driver should be the fullest first-hand report, so the
        # log describes the development rather than a revision to it.
        rep = sorted(c["events"], key=lambda e: (bool(e.get("update")),
                                                 -len(e.get("text") or "")))[0]
        out.append({"id": fingerprint(rep), "events": c["events"],
                    "rep": rep, "sources": max(1, len(doms)),
                    "urls": urls, "reports": len(c["events"])})
    return out


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
    """r1: a hard count inside a 30-day box. Kept for the selftest that
    documents what changed; no longer used by the chain."""
    cutoff = (today - _dt.timedelta(days=30)).isoformat()
    return sum(1 for e in weights.get("evidence_log", [])
               if e.get("rule") == rule_id and e.get("date", "") >= cutoff)


def novelty_k(weights, rule_id, today):
    """Recency-weighted count of PRIOR incidents of this class.

    Two problems with the r1 box. It had a cliff — an incident 30 days old
    counted fully and one 31 days old counted zero — and no gradient inside
    it, so a class that fired eight times last week and a class that fired
    eight times last month were treated identically. The design note asks for
    "a DROUGHT-then-return carries weight", which needs a gradient.

    Prior nights only. Incidents from tonight are handled by `spread`, so
    that the third funding round of an evening is not worth a quarter of the
    first because of the order the trunk happened to list them in."""
    k = 0.0
    for e in weights.get("evidence_log", []):
        if e.get("rule") != rule_id:
            continue
        d = e.get("date")
        if not d or d >= today.isoformat():
            continue
        age = (today - _dt.date.fromisoformat(d)).days
        k += 0.5 ** (age / axes.NOVELTY_HALFLIFE_DAYS)
    return k


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

    # r2: resolve reports into incidents, then classify each incident ONCE.
    inc = resolve_incidents(fresh)
    plan = []                     # (incident, rule, contested) for matches
    unmatched = []
    for g in inc:
        rule, contested, _all = axes.classify(g["rep"])
        if rule is None:
            # an incident is unexplained only if NO report in it matched;
            # the representative is the fullest report, but a shorter one
            # can still carry the term the rule needs.
            for ev in g["events"]:
                rule, contested, _all = axes.classify(ev)
                if rule is not None:
                    break
        if rule is None:
            unmatched.append(g)
        else:
            plan.append((g, rule, contested))

    # how many DISTINCT incidents of each class landed tonight; every one of
    # them gets the same weight and the class total grows as sqrt(n).
    per_rule = {}
    for g, rule, _c in plan:
        per_rule[rule["id"]] = per_rule.get(rule["id"], 0) + 1

    applied_n, residue_n = 0, 0
    for g, rule, contested in plan:
        n = per_rule[rule["id"]]
        k = novelty_k(weights, rule["id"], today)
        entry_before = len(log)
        axes.apply_evidence(reg, rule, log, sources=g["sources"],
                            repeat_k=k, weekly_cum=cum,
                            spread=(n ** 0.5) / n, contested=contested,
                            incident=g["id"])
        for e2 in log[entry_before:]:
            e2["date"] = today.isoformat()
            e2["event_date"] = g["rep"]["date"]["iso"][:10]
            e2["driver"] = (g["rep"].get("text") or "")[:140]
            e2["driver_urls"] = g["urls"][:3]
            e2["reports"] = g["reports"]
        applied_n += 1
    for g in unmatched:
        ev = g["rep"]
        weights.setdefault("residue", []).append(
            {"date": ev["date"]["iso"][:10],
             "section": axes.canon_section(ev.get("section")) or "?",
             "text": (ev.get("text") or "")[:120],
             "reports": g["reports"],
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
    # the stored version must track the code that wrote the state, or a
    # future reader dates these weights to the wrong methodology. r1 set it
    # only inside the one-time migration, so it froze at r1 the moment the
    # migration stopped running.
    weights["version"] = axes.REGISTRY_VERSION

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
        f.write("- distinct incidents resolved: %d (%d reports collapsed)\n"
                % (len(inc), len(fresh) - len(inc)))
        f.write("- evidence applications: %d\n" % applied_n)
        f.write("- residue (unexplained): %d\n" % residue_n)
        multi = [g for g in inc if g["reports"] > 1]
        if multi:
            f.write("- multi-report incidents: %d\n" % len(multi))
            for g in multi[:8]:
                f.write("  - %d reports · %d sources · %s\n"
                        % (g["reports"], g["sources"],
                           " ".join((g["rep"].get("text") or "").split())[:70]))
        contested_n = sum(1 for _g, _r, c in plan if c)
        if contested_n:
            f.write("- contested classifications (damped and named): %d\n"
                    % contested_n)
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
            f.write("\n- %s [%s ×%.5f k=%.2f spread=%.2f reports=%d "
                    "src=%d]%s %s\n" %
                    (e["rule"], e["impact_class"], e["magnitude"],
                     e.get("repeat_k", 0), e.get("spread", 1.0),
                     e.get("reports", 1), e.get("sources", 1),
                     (" CONTESTED by %s" % ",".join(e["contested"]))
                     if e.get("contested") else "",
                     e.get("driver", "")[:100]))
    return {"fresh": len(fresh), "incidents": len(inc),
            "applied": applied_n, "residue": residue_n,
            "collapsed": len(fresh) - len(inc),
            "contested": sum(1 for _g, _r, c in plan if c),
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

    # --- incidents (r2): reports of one event vs events of one kind --------
    def _ev(txt, day="2026-08-06", urls=(), upd=False,
            sec="AI Industry & Markets"):
        return {"date": {"iso": day, "kind": "event"}, "section": sec,
                "text": txt, "urls": list(urls), "update": upd}
    # one development, three write-ups, three publishers
    one = [_ev("Illinois Gov. JB Pritzker signed SB 315 into law on July 6, "
               "2026, the first state law requiring annual independent "
               "third-party audits of frontier AI developers.",
               "2026-07-06", ["https://govtech.com/a"]),
           _ev("Illinois Gov. JB Pritzker signed SB 315 into law on July 6, "
               "2026, the first state law requiring annual independent "
               "third-party audits of frontier AI developers and reporting.",
               "2026-07-06", ["https://govtech.com/a"]),
           _ev("On July 6, 2026 Illinois Governor Pritzker signed SB 315, "
               "requiring independent third-party audits, Pritzker said.",
               "2026-07-06", ["https://capitolnewsillinois.com/b"])]
    got = resolve_incidents(one, one)
    assert len(got) < len(one), "repeated reports must collapse"
    assert got[0]["reports"] >= 2 and got[0]["sources"] >= 1
    # three unrelated developments of ONE class stay three
    three = [_ev("SpaceX said on August 6, 2026 that it and Tesla will "
                 "initially invest $16.8 billion to build Terafab in Grimes "
                 "County, Texas.", urls=["https://reuters.com/x"]),
             _ev("Mirendil signed a multi-year Google Cloud partnership "
                 "worth more than $100 million to source compute.",
                 urls=["https://techcrunch.com/y"]),
             _ev("Khosla Ventures and Radical Ventures invested alongside "
                 "Alphabet in the Discovery Loop founding round.",
                 urls=["https://implicator.ai/z"])]
    got3 = resolve_incidents(three, three)
    assert len(got3) == 3, [g["reports"] for g in got3]
    # a digest URL cited by many events is not identity
    st = corpus_stats(three + one)
    assert not same_incident(three[0], three[1], st)
    # novelty_k: recency-weighted, prior nights only, and it RECOVERS
    wk = {"evidence_log": [{"rule": "r", "date": "2026-08-05"},
                           {"rule": "r", "date": "2026-08-05"},
                           {"rule": "r", "date": "2026-08-06"}]}
    k_today = novelty_k(wk, "r", _dt.date(2026, 8, 6))
    # two priors, one day old, half-life 7 → 2 × 0.5**(1/7) = 1.811. Tonight's
    # own entry is excluded: within-night incidents are handled by `spread`.
    assert abs(k_today - 2 * 0.5 ** (1 / 7.0)) < 1e-9, k_today
    k_later = novelty_k(wk, "r", _dt.date(2026, 8, 20))
    assert k_later < k_today / 2, (k_today, k_later)   # two half-lives on
    assert axes.novelty(k_later) > axes.novelty(k_today) * 1.2, \
        "a fortnight of silence must buy a class real weight back"
    # r1's box could not do this: inside 30 days it counted both the same
    assert repeat_count(wk, "r", _dt.date(2026, 8, 6)) == \
        repeat_count(wk, "r", _dt.date(2026, 8, 20)) == 3
    assert axes.novelty(99) >= axes.NOVELTY_FLOOR
    return 7


if __name__ == "__main__":
    n = _selftest()
    print("nightly_update selftest: %d groups passed" % n)
    out = update()
    print(json.dumps(out, indent=1))
