#!/usr/bin/env python3
"""wiki_grounding.py — the deep-wiki pass (decision of record: "more wiki
pages should be referenced and used"). Maps the corpus onto the engine in two
honest tiers:

  DIRECT — the page is cited on a specific axis, position, rule, template or
           parameter (the seed registry's citations, plus the structured
           folder/tag mapping below where the mapping is a real mechanism:
           an industry page genuinely parameterizes that sector's diffusion).
  CORPUS — the page feeds the trunk (events, series, calibration) without a
           named engine hook yet.

Outputs Research/staged/forecast/grounding.json:
  {direct: {page: [hooks]}, corpus: [pages], counts, thin_axes}
Thin axes (fewest DIRECT pages) → prior-widening factors consumed by
forecast_emit (thin grounding renders as wider bands, never hidden
confidence). The gate ratchets the counts.
"""

from __future__ import annotations

import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "modeling"))
import axes
import worldlines
from frames import WIKI, FOLDERS, SlugIndex, parse_frontmatter

STAGED_F = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "staged", "forecast")

# folder → engine hook (a real mechanism, stated)
FOLDER_HOOKS = {
    "industries": ["axis:D", "dynamics:REV_G", "dynamics:JOBS_RATE"],
    "litigation": ["template:copyright-settles", "layer:law"],
    "legislation": ["axis:C", "dynamics:LAWS_RATE"],
    "models": ["axis:T", "dynamics:capability_path", "trunk:calibration"],
    "standards": ["axis:C", "layer:law"],
    "government": ["axis:C", "layer:geopolitics"],
}
# tag → engine hook, for concepts/analysis/entities/companies/sources
# deliberately narrow: a tag maps only where the mechanism is real. ("us"
# alone mapped 1,032 pages onto axis C on the first run — coverage-washing,
# removed. Generic region tags ground nothing by themselves.)
TAG_HOOKS = {
    "compute": ["axis:S"],
    "national-security": ["axis:C", "layer:geopolitics"],
    "safety": ["axis:A"], "alignment": ["axis:A"],
    "workforce": ["axis:D"],
    "competition": ["axis:E"],
    "open-source": ["axis:S"],
    "eu": ["strand:EU"],
    "copyright": ["template:copyright-settles", "layer:law"],
    "liability": ["layer:law"],
    "frontier-models": ["axis:T"],
    "ethics": ["axis:P"], "surveillance": ["axis:P"],
}


def registry_direct():
    """Pages the engine cites by name (registry + rules + templates)."""
    direct = collections.defaultdict(set)
    for p in axes.coverage(axes.REGISTRY):
        direct[p].add("registry")
    for t in worldlines.TEMPLATES:
        for p in t["cites"]:
            direct[p].add("template:%s" % t["id"])
    return direct


def scan():
    idx = SlugIndex()
    direct = registry_direct()
    corpus = set()
    for folder, slug in sorted(idx.by_path):
        pid = "%s/%s" % (folder, slug)
        hooks = set()
        if folder in FOLDER_HOOKS:
            hooks.update(FOLDER_HOOKS[folder])
        path = os.path.join(WIKI, folder, slug + ".md")
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                head = f.read(2500)
            fm, _, _ = parse_frontmatter(head)
            tags = fm.get("tags") or []
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, str) and t in TAG_HOOKS:
                        hooks.update(TAG_HOOKS[t])
        except OSError:
            pass
        if pid in direct:
            hooks.add("cited")
        if hooks:
            direct[pid].update(hooks)
        else:
            corpus.add(pid)
    return direct, corpus


def thin_axes(direct, axis_keys=None):
    """DIRECT pages per REGISTRY axis (absent axes count 0 and rank
    thinnest). Widening: up to +25% prior spread on the thinnest axes —
    thin grounding renders as wider bands, never hidden confidence."""
    axis_keys = axis_keys or [a["key"] for a in axes.REGISTRY["axes"]]
    per_axis = {k: 0 for k in axis_keys}
    for hooks in direct.values():
        for h in hooks:
            if h.startswith("axis:") and h[5:] in per_axis:
                per_axis[h[5:]] += 1
    widen = {}
    ref = sorted(per_axis.values())[len(per_axis) // 2] or 1   # median
    for ax, n in per_axis.items():
        deficit = max(0.0, (ref - n) / ref)
        widen[ax] = round(1.0 + 0.25 * min(1.0, deficit), 3)
    return per_axis, widen


def build():
    os.makedirs(STAGED_F, exist_ok=True)
    direct, corpus = scan()
    per_axis, widen = thin_axes(direct)
    out = {
        "direct": {k: sorted(v) for k, v in sorted(direct.items())},
        "corpus_count": len(corpus),
        "counts": {"direct": len(direct), "corpus": len(corpus),
                   "total": len(direct) + len(corpus)},
        "per_axis": per_axis,
        "widen": widen,
    }
    with open(os.path.join(STAGED_F, "grounding.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"))
    return out


def _selftest():
    d = registry_direct()
    assert "sources/ai-2027" in d and "concepts/agi-timelines" in d
    assert any(h.startswith("template:") for h in d["sources/ai-2040-plan-a"])
    per, widen = thin_axes({"a": {"axis:T"}, "b": {"axis:T"},
                            "c": {"axis:P"}})
    assert per["T"] == 2 and per["P"] == 1
    assert widen["P"] >= widen["T"] >= 1.0
    return 2


if __name__ == "__main__":
    n = _selftest()
    print("wiki_grounding selftest: %d groups passed" % n)
    out = build()
    print("grounding: direct %d · corpus %d · total %d" %
          (out["counts"]["direct"], out["counts"]["corpus"],
           out["counts"]["total"]))
    print("direct pages per axis:", dict(sorted(out["per_axis"].items())))
    print("widening factors (thin axes):",
          {k: v for k, v in out["widen"].items() if v > 1.0})
