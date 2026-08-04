#!/usr/bin/env python3
"""witness_statelaw.py — the state-legislation counter (register T7).

Why this exists: the calibration claim `cl-state-laws-2026` ("state AI-law
count exceeds 90", deadline 2026-12-31) had NOTHING in the model to resolve
against. series.json holds 432 rows across 71 groups and every one of them is
corporate, financial or capability — not a single row counts laws. A claim
that cannot be scored is not a forecast, it is a slogan.

What this is, exactly:

  An ENUMERATION of distinct state AI laws whose enactment appears in the
  wiki record, deduped across the several digests that report the same law,
  with the state, the bill, the date and the sources for each. It is a real,
  auditable series and it is a LOWER BOUND.

What this is NOT:

  A census. The wiki tracks policy-notable developments, not all fifty
  states' legislative output, so this counter observes a fraction of the
  universe the claim is about. It can therefore only ever CONFIRM
  `cl-state-laws-2026` (if the observed count alone passes 90) and can never
  REFUTE it. `resolves_claim` is emitted as false with that reason attached,
  and the app must render the gap rather than the number alone.

  The one aggregate figure in the whole trunk — "12 states enacting such
  legislation since January 2026, per the National Conference of State
  Legislatures" (2026-04-30) — is scoped to healthcare-and-AI laws, so it is
  recorded as context and deliberately NOT treated as comparable to the
  claim's universe. Closing this properly needs NCSL ingested as a named
  witness; a queue task asks for exactly that.

"Enacted" is not defined here. It is read from ev-state-law-enacted in
axes.py, so the counter and the forecast can never drift apart on what counts.

stdlib only. Run: python3 witness_statelaw.py
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "timelines"))
import axes  # noqa: E402

STAGED = os.path.join(HERE, "..", "staged")
EVENTS = os.path.join(STAGED, "events.json")
CLAIM_ID = "cl-state-laws-2026"
CLAIM_THRESHOLD = 90

STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming", "District of Columbia",
]
BILL_RE = re.compile(
    r"\b(?:(?:house|senate|assembly)\s+bill\s*|HB\s*|SB\s*|AB\s*|LB\s*|LD\s*)"
    r"(\d{1,5})\b", re.I)


def enactment_rule():
    return next(r for r in axes.EVIDENCE_RULES
                if r["id"] == "ev-state-law-enacted")


# An event's prose routinely names states it is NOT reporting an enactment
# for — comparisons, surveys of what other legislatures are merely
# considering, semicolon-joined second facts. Counting every state mentioned
# inflated the first build of this counter from 8 real laws to 18, which for
# a LOWER BOUND is not conservative, it is invented. The enacting state is
# therefore bound to the enactment verb by proximity: the nearest state name
# in the window immediately before it.
ENACT_RE = re.compile(
    r"\b(signed\s+(?:into\s+law|the|house\s+bill|senate\s+bill|hb|sb)|"
    r"enacted|became\s+law|was\s+enacted|overrode)", re.I)
LOOKBACK = 140          # chars before the verb to search for the actor
LOOKAHEAD = 110         # chars after the verb to search for the bill number


def states_in(text):
    """Every state named anywhere in the prose, with its position."""
    out = []
    for s in STATES:
        for m in re.finditer(r"\b" + re.escape(s) + r"\b", text):
            out.append((m.start(), s))
    return sorted(out)


def law_keys(ev):
    """Distinct (state, bill) identities ENACTED by this event.

    Falls back to (state, year) when the report gives no bill number, which
    merges two unnumbered reports of the same state in the same year — the
    conservative direction for a lower bound, and stated as such."""
    text = " ".join((ev.get("text") or "").split())
    positions = states_in(text)
    year = ev["date"]["iso"][:4]
    keys = []
    for verb in ENACT_RE.finditer(text):
        at = verb.start()
        before = [(p, s) for p, s in positions if p < at and p >= at - LOOKBACK]
        if not before:
            continue
        state = before[-1][1]                       # nearest preceding actor
        bill = BILL_RE.search(text[at:at + LOOKAHEAD])
        # tags are explicitly marked: "#315" is a bill, "y2026" is the year
        # fallback. Inferring the difference from the digits silently deleted
        # Illinois HB 5511 — a four-digit bill number read as a year.
        key = "%s|%s" % (state,
                         "#" + bill.group(1) if bill else "y" + year)
        if key not in keys:
            keys.append(key)
    return keys


def merge_year_fallbacks(laws):
    """A state with both a numbered law and a same-year unnumbered entry is
    one law reported twice, not two. Collapse toward the numbered record."""
    have_numbered = {k.split("|", 1)[0] for k in laws
                     if k.split("|", 1)[1].startswith("#")}
    for k in list(laws):
        state, tag = k.split("|", 1)
        if tag.startswith("y") and state in have_numbered:
            laws.pop(k)
    return laws


def build():
    events = json.load(open(EVENTS))["events"]
    rule = enactment_rule()
    laws = {}
    for ev in events:
        if not axes.match_event(rule, ev):
            continue
        for key in law_keys(ev):
            rec = laws.setdefault(key, {
                "key": key, "state": key.split("|")[0],
                "bill": key.split("|")[1],
                "first_seen": ev["date"]["iso"][:10], "urls": [],
                "text": (ev.get("text") or "")[:180]})
            if ev["date"]["iso"][:10] < rec["first_seen"]:
                rec["first_seen"] = ev["date"]["iso"][:10]
            for u in (ev.get("urls") or []):
                if u not in rec["urls"]:
                    rec["urls"].append(u)
    laws = merge_year_fallbacks(laws)
    rows = sorted(laws.values(), key=lambda r: (r["first_seen"], r["key"]))
    series, n = [], 0
    for r in rows:
        n += 1
        series.append({"date": {"iso": r["first_seen"], "kind": "event"},
                       "count": n, "state": r["state"], "bill": r["bill"]})
    observed = len(rows)
    return {
        "observed_count": observed,
        "distinct_states": len(sorted({r["state"] for r in rows})),
        "laws": rows,
        "series": series,
        "bound": "lower",
        "basis": "wiki-observed enactments matched by ev-state-law-enacted",
        "claim": {
            "id": CLAIM_ID, "threshold": CLAIM_THRESHOLD,
            "observed": observed,
            # honest resolution logic: only a confirm is reachable
            "resolves_claim": observed > CLAIM_THRESHOLD,
            "can_refute": False,
            "why": "The wiki tracks policy-notable developments, not the "
                   "full legislative output of fifty states, so this count "
                   "is a lower bound on the claim's universe. It can confirm "
                   "the claim if it alone passes the threshold; it can never "
                   "refute it. Resolving the claim needs NCSL (or an "
                   "equivalent named tracker) ingested as a witness.",
            "context_only": {
                "date": "2026-04-30",
                "figure": "12 states enacting healthcare-and-AI legislation "
                          "since January 2026, per NCSL",
                "comparable": False,
                "why": "domain-scoped to healthcare; the claim is not"},
        },
    }


def _selftest():
    ev = {"section": "U.S. State AI Legislation",
          "date": {"iso": "2026-07-06", "kind": "event"},
          "text": "Illinois Gov. JB Pritzker signed SB 315 into law on "
                  "July 6, 2026.", "urls": ["a"]}
    assert axes.match_event(enactment_rule(), ev)
    assert law_keys(ev) == ["Illinois|#315"]
    # the same law reported by a second digest collapses to one key
    ev2 = dict(ev, text="On July 6, 2026, Illinois Governor JB Pritzker "
                        "signed Senate Bill 315, the Artificial "
                        "Intelligence Safety Measures Act.")
    assert law_keys(ev2) == ["Illinois|#315"]
    # a sentence naming several enacting states yields one key per state
    ev3 = dict(ev, text="Idaho enacted a chatbot referral law and Tennessee "
                        "enacted its own in 2026.")
    assert set(law_keys(ev3)) == {"Idaho|y2026", "Tennessee|y2026"}
    # an enforcement action is not an enactment and must not be counted
    ev4 = dict(ev, text="The California Privacy Protection Agency opened a "
                        "compliance audit.")
    assert not axes.match_event(enactment_rule(), ev4)

    # --- the inflation regressions, each from a real trunk event ----------
    # states merely CONSIDERING bills are not enacting states
    ev5 = dict(ev, text="The Local Solutions Support Center reported that "
                        "nine states are considering 12 bills to preempt "
                        "local AI regulation, including bills in New "
                        "Hampshire, Ohio, South Carolina, and Virginia; "
                        "Montana enacted a Right to Compute law.")
    assert law_keys(ev5) == ["Montana|y2026"], law_keys(ev5)
    # a chamber passing a bill is not an enactment; the second clause is
    ev6 = dict(ev, text="The New York State Senate passed a five-year "
                        "moratorium on AI chatbot toys; separately, "
                        "Nebraska enacted LB 525 earlier in 2026.")
    assert law_keys(ev6) == ["Nebraska|#525"], law_keys(ev6)
    # states named as comparisons must not each become a law
    ev7 = dict(ev, text="Maryland Gov. Wes Moore signed the Protection from "
                        "Predatory Pricing Act into law, the first such ban; "
                        "California, Colorado and Massachusetts have "
                        "considered similar measures.")
    assert law_keys(ev7) == ["Maryland|y2026"], law_keys(ev7)
    # numbered and unnumbered reports of one state's law are one law
    merged = merge_year_fallbacks({"Illinois|#315": {}, "Illinois|y2026": {}})
    assert list(merged) == ["Illinois|#315"], list(merged)
    # the counter must never claim it can refute
    assert build()["claim"]["can_refute"] is False
    return 4


if __name__ == "__main__":
    n = _selftest()
    print("witness_statelaw selftest: %d groups passed" % n)
    res = build()
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("laws", "series")}, indent=1))
    print("laws observed (%d):" % res["observed_count"])
    for r in res["laws"]:
        print("  %s  %-16s %-6s  %s"
              % (r["first_seen"], r["state"], r["bill"], r["text"][:70]))
    out = os.path.join(STAGED, "witness-statelaw.json")
    json.dump(res, open(out, "w"), indent=1)
    print("written:", out)
