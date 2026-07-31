#!/usr/bin/env python3
"""emit.py — August's Vault → staged data for AI Atlas (read-only against the
vault; SCOPE §10). Produces Research/staged/*.json + needs-review.md.

Every date leaves here with a KIND (frames.py); every unparseable value is
reported, never guessed; the vault is never written (Working Rule / SCOPE
rule 2.11 — the queue loop lives in the audits, not here).

Run:  python3 emit.py            full emit, prints stats
      python3 emit.py --selftest selftests only
"""

from __future__ import annotations

import collections
import datetime as _dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frames
from frames import (VAULT, WIKI, FOLDERS, EVENT, PUBLISHED, INGESTED, CHECKED,
                    norm_date, extract_event_date, parse_frontmatter,
                    SlugIndex, WIKILINK, jurisdiction, state_from_title)

STAGED = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "staged")
DEVLOG = os.path.join(VAULT, "New Developments Log")
LOGMD = os.path.join(WIKI, "_meta", "log.md")

# Decay windows (months) per folder — CLAUDE.md v4.x claim classes, mapped to
# page families (3: fast-moving financial/capability; 6: positions/strategy;
# 12: foundational/enacted text).
DECAY = {"models": 3, "companies": 3, "litigation": 3,
         "entities": 6, "concepts": 6, "analysis": 6, "government": 6,
         "industries": 6,
         "standards": 12, "legislation": 12, "sources": 12,
         "policy-briefs": 6, "primers": 6}

# Entity-class folders that become map features (people are cards only —
# SCOPE rule 2.14 — and sources are the citation layer, not features).
FEATURE_FOLDERS = ["companies", "models", "legislation", "litigation",
                   "entities", "concepts", "government", "industries",
                   "standards", "analysis"]

REL_LINE = re.compile(r"^\s*-\s+\*\*([a-z][a-z0-9 _-]*?):?\*\*:?\s*(.+)$", re.I)
SUP_URL = re.compile(r"<sup>\[\d+\]\((https?://[^)]+)\)</sup>")
MONEY = re.compile(r"\$([\d.,]+)\s*(T|B|M|trillion|billion|million)\b", re.I)
H2 = re.compile(r"^## +(.+?)\s*$", re.M)
LOG_ENTRY = re.compile(r"^### +(\d{4}-\d{2}-\d{2})\s*—\s*(.+?)\s*$")
PAGES_LINE = re.compile(r"^\*\*Pages (created|updated):\*\*\s*(.*)$")

# ---------------------------------------------------------------------------
# Authored eras (SCOPE §3: authored, grounded in wiki analysis; final naming
# pending August's sign-off — register B2). Confidence moderate throughout.
# ---------------------------------------------------------------------------
ERAS = [
    {"id": "deep-learning", "name": "Deep Learning Spring",
     "from": "2012-09-30", "to": "2017-06-11",
     "note": "AlexNet to the eve of the transformer: vision, seq2seq, GANs, "
             "AlphaGo.", "cite": ["sources/attention-is-all-you-need"]},
    {"id": "transformer", "name": "The Transformer Era",
     "from": "2017-06-12", "to": "2020-05-27",
     "note": "Attention Is All You Need through GPT-2: architecture and "
             "scaling laws take shape.",
     "cite": ["sources/attention-is-all-you-need"]},
    {"id": "scaling", "name": "The Scaling Era",
     "from": "2020-05-28", "to": "2022-11-29",
     "note": "GPT-3 to the eve of ChatGPT: scale as strategy; labs "
             "consolidate.", "cite": ["models/gpt-3"]},
    {"id": "chatgpt-shock", "name": "The ChatGPT Shock",
     "from": "2022-11-30", "to": "2023-10-29",
     "note": "Deployment meets the public; capability debate goes "
             "mainstream.", "cite": ["companies/openai"]},
    {"id": "regulatory-response", "name": "The Regulatory Response",
     "from": "2023-10-30", "to": "2024-12-31",
     "note": "EO 14110 and Bletchley through the EU AI Act's adoption and "
             "the first state-law wave.", "cite": ["legislation/eu-ai-act"]},
    {"id": "agentic", "name": "The Agentic Turn",
     "from": "2025-01-01", "to": "2026-04-12",
     "note": "Agents, coding models, compute build-out; governance "
             "fragments across jurisdictions.", "cite": []},
    {"id": "convergence", "name": "Convergence",
     "from": "2026-04-13", "to": None,
     "note": "The wiki's dense window: IPO-era economics, "
             "government-coordinated releases, doctrine forming in the "
             "courts. Observed daily.", "cite": ["companies/anthropic",
                                                 "models/gpt-56"]},
]


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Wiki pages → entities, arcs, links, series
# ---------------------------------------------------------------------------

def window_from(folder, fm, review):
    """Existence window start, honestly. None = undated (drawn as background
    presence; the knowledge-horizon layer supplies 'when known')."""
    key = {"models": "release_date", "companies": "founded",
           "litigation": "filed", "sources": "date"}.get(folder)
    if not key or fm.get(key) in (None, ""):
        return None
    kind = EVENT if key != "date" else PUBLISHED
    d, err = norm_date(fm.get(key), kind)
    if err:
        review.append("%s/%s: %s (%s)" % (folder, fm.get("_slug", "?"), err, key))
    return d


def parse_relationships(body, idx, review, src):
    arcs = []
    m = re.search(r"^## Relationships\s*$(.*?)(?=^## |\Z)", body,
                  re.M | re.S)
    if not m:
        return arcs
    for line in m.group(1).split("\n"):
        lm = REL_LINE.match(line)
        if not lm:
            continue
        rtype = lm.group(1).strip().lower().replace(" ", "-")
        for wl in WIKILINK.finditer(lm.group(2)):
            tgt = idx.resolve(wl.group(1))
            if tgt:
                arcs.append({"type": rtype, "dst": "%s/%s" % tgt})
            else:
                review.append("%s: dangling relationship target %r"
                              % (src, wl.group(1)[:50]))
    return arcs


def parse_snapshot(body, src, review):
    """### <metric-group> tables under ## Snapshot → dated rows."""
    rows = []
    m = re.search(r"^## Snapshot\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    if not m:
        return rows
    group = None
    for line in m.group(1).split("\n"):
        h = re.match(r"^### +(.+)$", line)
        if h:
            group = h.group(1).strip()
            continue
        if not line.strip().startswith("|") or set(line.strip()) <= set("|- :"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in ("date", ""):
            continue
        d, err = norm_date(cells[0], CHECKED)
        if err:
            continue                      # non-dated snapshot rows are prose
        amount = cells[1]
        mv = MONEY.search(amount)
        val = None
        if mv:
            n = float(mv.group(1).replace(",", ""))
            unit = mv.group(2).lower()[0]
            val = n * {"t": 1000.0, "b": 1.0, "m": 0.001}[unit]
        rows.append({"date": d, "group": group or "Snapshot",
                     "text": amount[:160], "usd_b": val})
    return rows


def load_pages(idx):
    entities, arcs, series, review = [], [], [], []
    links = collections.Counter()
    indeg = collections.Counter()
    for folder in FOLDERS:
        d = os.path.join(WIKI, folder)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".md"):
                continue
            slug = name[:-3]
            pid = "%s/%s" % (folder, slug)
            fm, body, warns = parse_frontmatter(_read(os.path.join(d, name)))
            fm["_slug"] = slug
            for w in warns:
                if "duplicate" in w or "inline comment" in w:
                    review.append("%s: %s" % (pid, w))
            out_targets = set()
            for wl in WIKILINK.finditer(body):
                t = idx.resolve(wl.group(1))
                if t:
                    out_targets.add("%s/%s" % t)
            links[pid] = len(out_targets)
            for t in out_targets:
                indeg[t] += 1
            page_arcs = parse_relationships(body, idx, review, pid)
            for a in page_arcs:
                arcs.append({"src": pid, "dst": a["dst"], "type": a["type"]})
            snap = parse_snapshot(body, pid, review)
            for r in snap:
                series.append(dict(r, entity=pid))
            if folder == "sources":
                continue                       # citation layer, not entities
            juris = None
            if folder in ("companies",):
                juris, jerr = jurisdiction(fm.get("hq_country"))
            elif folder == "legislation":
                juris = state_from_title(fm.get("title", "") or slug)
                if not juris:
                    tags = fm.get("tags") or []
                    for t in (tags if isinstance(tags, list) else [tags]):
                        j, _ = jurisdiction(t)
                        if j:
                            juris = j
                            break
            ent = {
                "id": pid, "folder": folder, "slug": slug,
                "title": fm.get("title") or slug,
                "desc": (fm.get("description") or "")[:280],
                "confidence": fm.get("confidence") or "medium",
                "status": fm.get("status") or "active",
                "updated": fm.get("last_updated") or None,
                "decay_months": DECAY.get(folder, 6),
                "tags": fm.get("tags") if isinstance(fm.get("tags"), list)
                        else [],
                "window": window_from(folder, fm, review),
                "juris": juris,
                "fact": {k: fm.get(k) for k in
                         ("company_type", "founded", "hq_country", "developer",
                          "release_date", "parameters", "open_weights",
                          "entity_type", "court", "filed", "source_type",
                          "last_status_check", "superseded_by")
                         if fm.get(k) not in (None, "")},
            }
            entities.append(ent)
    for e in entities:
        e["outdeg"] = links.get(e["id"], 0)
        e["indeg"] = indeg.get(e["id"], 0)
    return entities, arcs, series, review


# ---------------------------------------------------------------------------
# Dev-log → events
# ---------------------------------------------------------------------------

def _mk_event(raw, section, fdate, fname, titles, review):
    is_update = raw.startswith("📌")
    is_new = raw.startswith("🆕")
    text_clean = raw.lstrip("🆕📌 ").strip()
    if not text_clean or len(text_clean) < 40:
        return None
    d, fell_back = extract_event_date(text_clean, fdate)
    if d is None:
        review.append("%s: item with no usable date" % fname)
        return None
    urls = SUP_URL.findall(raw)[:6]
    plain = re.sub(r"<sup>.*?</sup>", "", text_clean)
    plain = re.sub(r"[*_]", "", plain)
    return {"date": d, "fell_back": fell_back, "section": section,
            "update": is_update and not is_new, "text": plain[:300],
            "urls": urls, "targets": match_targets(plain, titles)[:4],
            "file": fname}


def parse_devlog_file(text, fname, titles, review):
    """Items are single lines in every era of the corpus; April-era files
    stack them without blank lines, so the parse is line-wise. Files with no
    emoji markers (17 of 201) fall back to paragraph blocks under sections."""
    fm, body, _ = parse_frontmatter(text)
    fdate = fm.get("date") or (re.match(r"(\d{4}-\d{2}-\d{2})", fname)
                               and re.match(r"(\d{4}-\d{2}-\d{2})",
                                            fname).group(1))
    events = []
    section = None
    for line in body.split("\n"):
        b = line.strip()
        if not b:
            continue
        h = H2.match(b)
        if h:
            section = h.group(1)
            if section.lower().startswith("sources"):
                break                       # the footnote list ends the items
            continue
        if section is None or b.startswith("#") or b.startswith("_"):
            continue
        if b.startswith("🆕") or b.startswith("📌"):
            ev = _mk_event(b, section, fdate, fname, titles, review)
            if ev:
                events.append(ev)
    if events:
        return events
    # fallback: no emoji markers — one item per paragraph block per section
    section = None
    for block in re.split(r"\n\n+", body):
        b = block.strip()
        if not b:
            continue
        h = H2.match(b)
        if h:
            section = h.group(1)
            if section.lower().startswith("sources"):
                break
            b = b[h.end():].strip()
            if not b:
                continue
        if section is None or b.startswith("#") or b.startswith("_"):
            continue
        if re.match(r"^\d+\.\s", b):
            break
        ev = _mk_event(b, section, fdate, fname, titles, review)
        if ev:
            events.append(ev)
    return events


def match_targets(text, titles):
    """Entity ids whose title appears in the item text (longest first)."""
    found = []
    low = " " + re.sub(r"[^a-z0-9 ]", " ", text.lower()) + " "
    for tl, pid in titles:
        if (" " + tl + " ") in low:
            found.append(pid)
            if len(found) >= 6:
                break
    return found


def build_title_index(entities):
    pairs = []
    for e in entities:
        t = re.sub(r"\s*\(.*?\)\s*", " ", e["title"]).strip().lower()
        t = re.sub(r"[^a-z0-9 ]", " ", t).strip()
        if len(t) >= 4 and t not in ("analysis", "overview"):
            pairs.append((t, e["id"]))
    pairs.sort(key=lambda p: -len(p[0]))
    return pairs


def load_devlog(titles):
    events, review = [], []
    if not os.path.isdir(DEVLOG):
        return events, ["dev-log folder missing"]
    for name in sorted(os.listdir(DEVLOG)):
        if not name.endswith(".md") or "SCHEMA" in name or "backfill" in name:
            continue
        try:
            evs = parse_devlog_file(_read(os.path.join(DEVLOG, name)), name,
                                    titles, review)
            events.extend(evs)
        except Exception as ex:                     # a bad file is a report,
            review.append("%s: parse error %s" % (name, ex))   # not a crash
    return events, review


# ---------------------------------------------------------------------------
# log.md → wiki-time
# ---------------------------------------------------------------------------

def load_wikitime(idx):
    ops, review = [], []
    for path in [LOGMD] + sorted(
            _globdir(os.path.join(WIKI, "_meta", "log-archive"))):
        if not os.path.isfile(path):
            continue
        cur = None
        for line in _read(path).split("\n"):
            m = LOG_ENTRY.match(line)
            if m:
                if cur:
                    ops.append(cur)
                d, err = norm_date(m.group(1), INGESTED)
                cur = {"date": d, "op": m.group(2)[:60], "created": [],
                       "updated": []}
                continue
            if cur is None:
                continue
            pm = PAGES_LINE.match(line.strip())
            if pm:
                key = "created" if pm.group(1) == "created" else "updated"
                for wl in WIKILINK.finditer(pm.group(2)):
                    t = idx.resolve(wl.group(1))
                    if t:
                        cur[key].append("%s/%s" % t)
        if cur:
            ops.append(cur)
    return ops, review


def _globdir(d):
    return [os.path.join(d, n) for n in os.listdir(d)] if os.path.isdir(d) else []


# ---------------------------------------------------------------------------
# Main emit
# ---------------------------------------------------------------------------

def emit():
    os.makedirs(STAGED, exist_ok=True)
    idx = SlugIndex()
    entities, arcs, series, review = load_pages(idx)
    feat = [e for e in entities if e["folder"] in FEATURE_FOLDERS
            and not (e["folder"] == "entities"
                     and e["fact"].get("entity_type") == "person")]
    people = [e for e in entities if e["folder"] == "entities"
              and e["fact"].get("entity_type") == "person"]
    titles = build_title_index(entities)
    events, rev2 = load_devlog(titles)
    wikitime, rev3 = load_wikitime(idx)
    review += rev2 + rev3

    # attach datum positions if the datum exists (round-1 step 2 creates it)
    datum_path = os.path.join(STAGED, "datum.json")
    datum_version = None
    if os.path.isfile(datum_path):
        datum = json.load(open(datum_path))
        datum_version = datum.get("version")
        pos = datum.get("positions", {})
        terr_of = datum.get("territory_of", {})
        for e in entities:
            e["pos"] = pos.get(e["id"])
            e["territory"] = terr_of.get(e["id"])
        by_id = {e["id"]: e for e in entities}
        tcent = datum.get("territory_centroids", {})
        for ev in events:
            p = None
            for t in ev["targets"]:
                te = by_id.get(t)
                if te and te.get("pos"):
                    p = te["pos"]
                    ev["position_mode"] = "entity"
                    break
            if p is None:
                sec = datum.get("section_territory", {}).get(ev["section"])
                if sec and sec in tcent:
                    p = tcent[sec]
                    ev["position_mode"] = "territory"
            ev["pos"] = p

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M")
    out = {
        "entities.json": {"entities": feat, "people": people},
        "events.json": {"events": events},
        "arcs.json": {"arcs": arcs},
        "series.json": {"series": [dict(r) for r in series]},
        "wikitime.json": {"ops": wikitime},
        "eras.json": {"eras": ERAS},
        "meta.json": {
            "generated": stamp, "datum_version": datum_version,
            "counts": {"entities": len(feat), "people": len(people),
                       "events": len(events), "arcs": len(arcs),
                       "series_rows": len(series),
                       "wikitime_ops": len(wikitime),
                       "needs_review": len(review)},
        },
    }
    for name, data in out.items():
        with open(os.path.join(STAGED, name), "w") as f:
            json.dump(data, f, separators=(",", ":"), default=str)
    with open(os.path.join(STAGED, "needs-review.md"), "w") as f:
        f.write("# Emit needs-review — %s\n\n%d items. Unparseable values are"
                " reported here, never guessed.\n\n" % (stamp, len(review)))
        for r in review[:400]:
            f.write("- %s\n" % r)
        if len(review) > 400:
            f.write("\n…and %d more.\n" % (len(review) - 400))
    return out["meta.json"]["counts"], review


# ---------------------------------------------------------------------------
# Selftest — synthetic copies of the real formats
# ---------------------------------------------------------------------------

def _selftest():
    idx = SlugIndex.__new__(SlugIndex)
    idx.by_path = {("companies", "anthropic"), ("companies", "openai"),
                   ("models", "gpt-56")}
    idx.by_slug = {"anthropic": [("companies", "anthropic")],
                   "openai": [("companies", "openai")],
                   "gpt-56": [("models", "gpt-56")]}
    review = []

    # relationships
    body = ("Intro\n\n## Relationships\n\n- **supports:** [[companies/openai]]\n"
            "- **contradicts:** [[anthropic]] and [[no-such]]\n\n## Next\n")
    arcs = parse_relationships(body, idx, review, "t")
    assert {(a["type"], a["dst"]) for a in arcs} == {
        ("supports", "companies/openai"), ("contradicts", "companies/anthropic")}
    assert any("dangling" in r for r in review)

    # snapshot rows: money extraction incl. T/M, undated rows skipped
    body = ("## Snapshot\n\n### Valuation\n"
            "| Date | Amount | Notes | Source |\n|---|---|---|---|\n"
            "| 2026-05-28 | $965B post-money — Series H | x | A |\n"
            "| 2026-04 | $380B | Series G. | (wiki) |\n"
            "| — | prose only | y | B |\n"
            "### Revenue (ARR / annualized)\n"
            "| Date | Amount | Notes | Source |\n|---|---|---|---|\n"
            "| 2026-05-28 | $47B run-rate | z | C |\n\n## Other\n")
    rows = parse_snapshot(body, "t", review)
    assert len(rows) == 3
    assert rows[0]["usd_b"] == 965.0 and rows[0]["date"]["precision"] == "day"
    assert rows[1]["usd_b"] == 380.0 and rows[1]["date"]["precision"] == "month"
    assert rows[2]["group"].startswith("Revenue")

    # dev-log items: emoji items, event dates, sup URLs, section attribution,
    # sources list terminates, intro/italic skipped
    text = """---
title: "AI Developments — July 30, 2026"
date: 2026-07-30
---

# AI Developments — July 30, 2026

_Italic preamble that must be skipped._

Overview paragraph before any section is skipped too.

## AI Litigation, Liability & Enforcement

🆕 The Third Circuit reversed the dismissal of *Cornish-Adebiyi v. Caesars* on July 29, 2026, allowing a class action about Anthropic pricing to proceed.<sup>[1](https://example.com/a)</sup> More sentences follow with detail to pass the length gate.

## National Security & Geopolitics

📌 Update: reporting published July 30, 2026 describes the FCC measures as capturing ground robots broadly, with inconsistent weight thresholds across outlets.<sup>[2](https://example.com/b)</sup>

## Sources

1. **NJ.com** — [t](https://example.com/a) — 2026-07-29
"""
    titles = [("anthropic", "companies/anthropic")]
    evs = parse_devlog_file(text, "2026-07-30-0805-ai-developments.md",
                            titles, review)
    assert len(evs) == 2
    assert evs[0]["date"]["iso"] == "2026-07-29" and not evs[0]["fell_back"]
    assert evs[0]["section"].startswith("AI Litigation")
    assert evs[0]["urls"] == ["https://example.com/a"]
    assert evs[0]["targets"] == ["companies/anthropic"]
    assert not evs[0]["update"] and evs[1]["update"]
    assert evs[1]["date"]["iso"] == "2026-07-30"

    # eras tile 2012→now with no gaps or overlaps (Working audit for B3)
    prev_to = None
    for e in ERAS:
        if prev_to is not None:
            gap = (frames.iso_to_days(e["from"]) - frames.iso_to_days(prev_to))
            assert 0 < gap <= 1.5, (e["id"], gap)
        prev_to = e["to"] or _dt.date.today().isoformat()
    assert ERAS[0]["from"] == "2012-09-30" and ERAS[-1]["to"] is None

    return 4


if __name__ == "__main__":
    n = _selftest()
    print("emit.py selftest: %d groups passed" % n)
    if "--selftest" in sys.argv:
        sys.exit(0)
    counts, review = emit()
    print("emit:", json.dumps(counts))
    print("needs-review: %d (see Research/staged/needs-review.md)" % len(review))
