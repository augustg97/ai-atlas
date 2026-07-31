#!/usr/bin/env python3
"""witness_epoch.py — the models-layer independent witness (register C1).

Compares the wiki's Wiki/models/ pages against Epoch AI's notable-AI-models
dataset (CC-BY 4.0, data/witness/epoch-notable-models.csv). The wiki is never
its own witness; disagreements are findings, not silent fixes.

Checks, both directions:
  W1  matched wiki models whose release date disagrees with Epoch by >14 days
      at day precision (month/year precision compares at that precision)
  W2  wiki models with no Epoch match (counted; the wiki tracks policy-notable
      systems, Epoch tracks training-notable ones — overlap is partial by
      design, so this is a monitored count, not an error)
  W3  Epoch "frontier language model" rows since 2020-11 with no wiki page —
      coverage-gap candidates for the queue loop

stdlib only. Run: python3 witness_epoch.py
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frames
from frames import norm_date, EVENT

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "..", "..", "data", "witness",
                   "epoch-notable-models.csv")
STAGED = os.path.join(HERE, "..", "staged")

# wiki-slug → Epoch model-name aliases — ONLY where the two names denote the
# SAME artifact. A near-version alias (llama-3 → "Llama 3.1-405B") creates a
# false date disagreement and indicts the wiki for the witness's unit choice;
# three such aliases did exactly that on first run and were removed.
ALIASES = {}


def norm_name(s):
    s = s.lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9.]+", " ", s)
    return " ".join(s.split())


def load_epoch():
    rows = []
    with open(CSV, encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            name = (r.get("Model") or "").strip()
            date = (r.get("Publication date") or "").strip()
            if not name:
                continue
            rows.append({
                "name": name, "norm": norm_name(name), "date": date,
                "org": (r.get("Organization") or "").strip(),
                "notability": (r.get("Notability criteria") or "").strip(),
                "domain": (r.get("Domain") or "").strip(),
            })
    return rows


def compare(entities_path=None):
    entities = json.load(open(entities_path or
                              os.path.join(STAGED, "entities.json")))
    wiki_models = [e for e in entities["entities"] if e["folder"] == "models"]
    epoch = load_epoch()
    by_norm = {}
    for r in epoch:
        by_norm.setdefault(r["norm"], r)

    date_disagreements, unmatched_wiki, matched = [], [], 0
    for m in wiki_models:
        cand = norm_name(m["title"])
        row = by_norm.get(cand) or by_norm.get(
            norm_name(ALIASES.get(m["slug"], "")))
        if row is None:
            # try relaxed: wiki title tokens ⊂ epoch name or vice versa
            toks = set(cand.split())
            row = next((r for r in epoch if toks and
                        (set(r["norm"].split()) == toks)), None)
        if row is None:
            unmatched_wiki.append(m["slug"])
            continue
        matched += 1
        wd = m.get("window")
        ed, _ = norm_date(row["date"], EVENT)
        if wd and ed:
            if wd["precision"] == "day" and ed["precision"] == "day":
                a = _dt.date.fromisoformat(wd["iso"])
                b = _dt.date.fromisoformat(ed["iso"])
                if abs((a - b).days) > 14:
                    date_disagreements.append(
                        {"slug": m["slug"], "wiki": wd["iso"],
                         "epoch": ed["iso"], "delta_days": (a - b).days})
            elif wd["iso"][:7] != ed["iso"][:7] and \
                    wd["precision"] != "year" and ed["precision"] != "year":
                date_disagreements.append(
                    {"slug": m["slug"], "wiki": wd["iso"],
                     "epoch": ed["iso"], "delta_days": None})

    # W3: high-notability Epoch rows since 2020-11 with no wiki page.
    # Epoch's vocabulary (measured 2026-07-31): SOTA improvement 578, Highly
    # cited 297, Historical significance 135, Significant use 84, Training
    # cost 78, Discretionary 64 — "frontier" appears nowhere, so the filter
    # uses their terms.
    W3_CRITERIA = ("historical significance", "significant use",
                   "training cost")
    wiki_norms = {norm_name(m["title"]) for m in wiki_models}
    gaps = []
    for r in epoch:
        nb = r["notability"].lower()
        if not any(c in nb for c in W3_CRITERIA):
            continue
        d, _ = norm_date(r["date"], EVENT)
        if not d or d["iso"] < "2020-11":
            continue
        if r["norm"] not in wiki_norms and not any(
                r["norm"] in w or w in r["norm"] for w in wiki_norms):
            gaps.append({"name": r["name"], "org": r["org"],
                         "date": d["iso"]})
    return {
        "wiki_models": len(wiki_models), "epoch_rows": len(epoch),
        "matched": matched, "unmatched_wiki": len(unmatched_wiki),
        "unmatched_wiki_slugs": sorted(unmatched_wiki)[:20],
        "date_disagreements": date_disagreements,
        "epoch_frontier_gaps": gaps[:25],
        "epoch_frontier_gap_count": len(gaps),
    }


def _selftest():
    assert norm_name("GPT-5.6 (Sol, Terra, Luna)") == "gpt 5.6"
    assert norm_name("Claude 3 Opus") == "claude 3 opus"
    assert norm_name("LLaMA-3") == "llama 3"
    assert norm_name("GPT 5.6") == norm_name("GPT-5.6")
    d, _ = norm_date("2020-05-28", EVENT)
    assert d["precision"] == "day"
    return 1


if __name__ == "__main__":
    _selftest()
    print("witness_epoch selftest passed")
    if not os.path.isfile(CSV):
        print("Epoch CSV missing at", CSV)
        sys.exit(1)
    res = compare()
    print(json.dumps({k: v for k, v in res.items()
                      if not isinstance(v, list)}, indent=1))
    print("date disagreements:", res["date_disagreements"][:6])
    print("frontier gaps (first 6):",
          [g["name"] for g in res["epoch_frontier_gaps"][:6]])
    out = os.path.join(STAGED, "witness-epoch.json")
    json.dump(res, open(out, "w"), indent=1)
    print("written:", out)
