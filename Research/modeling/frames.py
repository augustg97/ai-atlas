#!/usr/bin/env python3
"""frames.py — the canonical frame for AI Atlas (SCOPE §5).

Everything that crosses from August's Vault into the model passes through here:

  - tolerant frontmatter parsing (the vault's real defects are the selftest);
  - dates: ISO-8601 + a mandatory KIND (event/published/ingested/checked) and a
    PRECISION (day/month/year). Unparseable values return None and a reason —
    never a guess (Working Rule 10);
  - wikilink/slug resolution, ported from the vault's own build_backlinks logic
    (bin/build-dashboard.py) so the two agree, plus the trailing-backslash and
    bare-slug artifacts the lint report catalogues;
  - jurisdiction mapping to ISO 3166-1 alpha-2 and US-XX;
  - the datum placement rule for pages that arrive after datum v1 is frozen.

stdlib only, so build/ can import it without a new dependency.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import os
import re
import sys

VAULT = os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs/August's Vault")
WIKI = os.path.join(VAULT, "Wiki")

# Wiki folders that hold content pages (SCOPE §5: slugs are canonical IDs).
FOLDERS = ["sources", "entities", "companies", "models", "legislation",
           "litigation", "concepts", "government", "industries", "standards",
           "analysis", "policy-briefs", "primers"]
# Bare-slug collisions resolve by this priority (same order the dashboard uses:
# content categories before sources, so "anthropic" hits companies/ first).
FOLDER_PRIORITY = ["companies", "models", "legislation", "litigation",
                   "entities", "concepts", "government", "industries",
                   "standards", "analysis", "sources", "policy-briefs",
                   "primers"]

EVENT, PUBLISHED, INGESTED, CHECKED = "event", "published", "ingested", "checked"
DATE_KINDS = (EVENT, PUBLISHED, INGESTED, CHECKED)

TODAY = _dt.date.today()


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

_INLINE_COMMENT = re.compile(r"\s+#\s.*$")


def parse_frontmatter(text):
    """Parse a page's YAML-ish frontmatter tolerantly.

    Returns (fm, body, warnings). Handles the vault's real defects:
    duplicate keys (last wins, warned), inline `# comments` on unquoted values,
    inline [a, b] lists, block lists, quoted strings. Never throws on a
    malformed line — it warns and skips.
    """
    warnings = []
    if not text.startswith("---"):
        return {}, text, ["no frontmatter"]
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text, ["unterminated frontmatter"]
    raw = text[3:end].strip("\n")
    body = text[end + 4:]
    if body.startswith("\n"):
        body = body[1:]
    fm = {}
    key = None
    for line in raw.split("\n"):
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and key:
            s = line.strip()
            if s.startswith("- "):                      # block list item
                if not isinstance(fm.get(key), list):
                    fm[key] = [] if fm.get(key) in (None, "") else [fm[key]]
                fm[key].append(_scalar(s[2:], warnings))
            continue                                     # nested maps: ignored
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not m:
            if line.strip().startswith("- ") and key:
                if not isinstance(fm.get(key), list):
                    fm[key] = [] if fm.get(key) in (None, "") else [fm[key]]
                fm[key].append(_scalar(line.strip()[2:], warnings))
                continue
            warnings.append("unparsed line: %r" % line[:60])
            continue
        key, val = m.group(1), m.group(2).strip()
        if key in fm:
            warnings.append("duplicate key %r (last wins)" % key)
        if val == "":
            fm[key] = ""                                 # may become block list
        else:
            fm[key] = _scalar(val, warnings)
    return fm, body, warnings


def _scalar(val, warnings):
    v = val.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [] if not inner else [_scalar(x, warnings)
                                     for x in _split_list(inner)]
    quoted = (len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'")
    if quoted:
        return v[1:-1]
    stripped = _INLINE_COMMENT.sub("", v).strip()
    if stripped != v:
        warnings.append("inline comment stripped from %r" % v[:40])
    return stripped


def _split_list(inner):
    out, cur, depth, q = [], "", 0, None
    for ch in inner:
        if q:
            cur += ch
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            cur += ch
        elif ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            if ch in "[{":
                depth += 1
            if ch in "]}":
                depth -= 1
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


# ---------------------------------------------------------------------------
# Dates — ISO + kind + precision, never a guess
# ---------------------------------------------------------------------------

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
_MON_ABBR = {m[:3]: n for m, n in MONTHS.items()}

_ISO_D = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_ISO_M = re.compile(r"^(\d{4})-(\d{2})$")
_YEAR = re.compile(r"^(\d{4})\b")
_TEXTUAL = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|"
    r"Nov|Dec)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", re.I)
_TEXTUAL_MY = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(\d{4})", re.I)

SENTINELS = {"1970-01-01"}
PLAUSIBLE = (1940, TODAY.year + 1)


def norm_date(raw, kind):
    """Normalise one date value → dict or (None, reason).

    Returns ({iso, kind, precision, raw}, None) on success, (None, reason)
    otherwise. Suffixed ISO ("2026-07-19 (preview)") parses at day precision.
    Sentinels and implausible years are rejected with a reason.
    """
    assert kind in DATE_KINDS, kind
    if raw is None:
        return None, "empty"
    s = str(raw).strip()
    if not s:
        return None, "empty"
    m = _ISO_D.match(s)
    if m:
        iso = "%s-%s-%s" % m.groups()
        if iso in SENTINELS:
            return None, "sentinel date %s" % iso
        try:
            d = _dt.date(*map(int, m.groups()))
        except ValueError:
            return None, "invalid calendar date %r" % s
        if not (PLAUSIBLE[0] <= d.year <= PLAUSIBLE[1]):
            return None, "implausible year %d" % d.year
        return {"iso": iso, "kind": kind, "precision": "day", "raw": s}, None
    m = _ISO_M.match(s)
    if m and 1 <= int(m.group(2)) <= 12:
        return {"iso": "%s-%s" % m.groups(), "kind": kind,
                "precision": "month", "raw": s}, None
    m = _TEXTUAL.search(s)
    if m:
        mon = MONTHS.get(m.group(1).lower()) or _MON_ABBR.get(
            m.group(1).lower()[:3])
        try:
            d = _dt.date(int(m.group(3)), mon, int(m.group(2)))
        except (ValueError, TypeError):
            return None, "invalid textual date %r" % s
        if not (PLAUSIBLE[0] <= d.year <= PLAUSIBLE[1]):
            return None, "implausible year %d" % d.year
        return {"iso": d.isoformat(), "kind": kind, "precision": "day",
                "raw": s}, None
    m = _YEAR.match(s)
    if m:
        # a value that LEADS with a year ("2018 (district court); decided
        # March 2026") means the year — trailing prose never outranks it
        y = int(m.group(1))
        if not (PLAUSIBLE[0] <= y <= PLAUSIBLE[1]):
            return None, "implausible year %d" % y
        return {"iso": "%d" % y, "kind": kind, "precision": "year",
                "raw": s}, None
    m = _TEXTUAL_MY.search(s)
    if m:
        return {"iso": "%d-%02d" % (int(m.group(2)),
                                    MONTHS[m.group(1).lower()]),
                "kind": kind, "precision": "month", "raw": s}, None
    return None, "unparseable date %r" % s[:60]


def extract_event_date(item_text, file_date_iso):
    """Event date for a dev-log item (SCOPE §5: event-date primacy).

    Looks for an explicit textual or ISO date in the item's opening (the
    vault's source-fidelity rule keeps these curated). Falls back to the
    digest's own date with kind=published — honestly labelled, never upgraded.
    Returns (date_dict, fell_back: bool).
    """
    head = item_text[:280]
    m = _TEXTUAL.search(head)
    if m:
        d, err = norm_date(m.group(0), EVENT)
        if d:
            return d, False
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", head)
    if m:
        d, err = norm_date(m.group(1), EVENT)
        if d:
            return d, False
    d, err = norm_date(file_date_iso, PUBLISHED)
    return d, True


def iso_to_days(iso):
    """Timeline coordinate: days since 2012-01-01 (float; month/year land at
    their midpoint so imprecise dates never sort spuriously early)."""
    epoch = _dt.date(2012, 1, 1)
    parts = iso.split("-")
    if len(parts) == 3:
        d = _dt.date(*map(int, parts))
        return (d - epoch).days
    if len(parts) == 2:
        d = _dt.date(int(parts[0]), int(parts[1]), 15)
        return (d - epoch).days
    return (_dt.date(int(parts[0]), 7, 1) - epoch).days


# ---------------------------------------------------------------------------
# Slug resolution (ported semantics of bin/build-dashboard.py resolve_wikilink)
# ---------------------------------------------------------------------------

class SlugIndex:
    def __init__(self, wiki_root=WIKI, folders=None):
        self.by_path = set()
        self.by_slug = {}
        for folder in (folders or FOLDERS):
            d = os.path.join(wiki_root, folder)
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                if name.endswith(".md"):
                    slug = name[:-3]
                    self.by_path.add((folder, slug))
                    self.by_slug.setdefault(slug, []).append((folder, slug))

    def resolve(self, target):
        """'[[…]]' inner text → (folder, slug) or None. Handles |display,
        #anchor, .md, trailing / and the corpus's trailing-\\ artifact."""
        t = target.split("|")[0].strip()
        if "#" in t:
            t = t.split("#", 1)[0].strip()
        t = t.rstrip("\\").rstrip("/").strip()
        if t.endswith(".md"):
            t = t[:-3]
        if not t:
            return None
        if "/" in t:
            folder, slug = t.rsplit("/", 1)
            folder = folder.split("/")[-1]        # "Wiki/companies" → companies
            if (folder, slug) in self.by_path:
                return (folder, slug)
            t = slug
        cands = self.by_slug.get(t)
        if not cands:
            return None
        if len(cands) == 1:
            return cands[0]
        return sorted(cands, key=lambda fs: FOLDER_PRIORITY.index(fs[0])
                      if fs[0] in FOLDER_PRIORITY else 99)[0]


WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")


# ---------------------------------------------------------------------------
# Jurisdictions — ISO 3166-1 alpha-2 + US-XX
# ---------------------------------------------------------------------------

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}
COUNTRY = {
    "us": "US", "usa": "US", "u.s.": "US", "united states": "US",
    "uk": "GB", "u.k.": "GB", "united kingdom": "GB", "britain": "GB",
    "eu": "EU", "european union": "EU",           # EU kept as a bloc code
    "china": "CN", "prc": "CN", "japan": "JP", "south korea": "KR",
    "korea": "KR", "france": "FR", "germany": "DE", "canada": "CA",
    "india": "IN", "israel": "IL", "singapore": "SG", "taiwan": "TW",
    "netherlands": "NL", "switzerland": "CH", "australia": "AU",
    "uae": "AE", "saudi arabia": "SA", "brazil": "BR", "russia": "RU",
    "italy": "IT", "spain": "ES", "sweden": "SE", "norway": "NO",
    "denmark": "DK", "finland": "FI", "ireland": "IE", "belgium": "BE",
    "austria": "AT", "poland": "PL", "global": None, "international": None,
}


def jurisdiction(value):
    """Free-text country/state → code, or (None, reason). 'global' → None
    deliberately (a real answer: everywhere), unknown strings → review."""
    if value is None:
        return None, "empty"
    s = str(value).strip().lower()
    if not s:
        return None, "empty"
    if s in COUNTRY:
        return COUNTRY[s], None
    if s in US_STATES:
        return "US-" + US_STATES[s], None
    if re.fullmatch(r"[a-z]{2}", s):
        return s.upper(), None
    return None, "unmapped jurisdiction %r" % value


def state_from_title(title):
    """'California SB 1047 …' → US-CA, for state-legislation pages."""
    t = title.lower()
    for name, code in US_STATES.items():
        if t.startswith(name + " ") or (" " + name + " ") in t:
            return "US-" + code
    return None


# ---------------------------------------------------------------------------
# The datum — placement of pages that postdate the frozen projection
# ---------------------------------------------------------------------------

def place_new(vec, anchor_vecs, anchor_pos, k=8):
    """Datum v1 rule (SCOPE §5): a new page sits at the similarity-weighted
    centroid of its k nearest frozen anchors (cosine in embedding space).
    Pure function; deterministic; no dependency on the projection method."""
    sims = []
    for key, av in anchor_vecs.items():
        dot = sum(a * b for a, b in zip(vec, av))
        na = math.sqrt(sum(a * a for a in vec)) or 1.0
        nb = math.sqrt(sum(b * b for b in av)) or 1.0
        sims.append((dot / (na * nb), key))
    sims.sort(reverse=True)
    top = [(max(s, 0.0), key) for s, key in sims[:k]]
    tot = sum(s for s, _ in top)
    if tot <= 0:
        return None                                    # unknown is legitimate
    x = sum(s * anchor_pos[key][0] for s, key in top) / tot
    y = sum(s * anchor_pos[key][1] for s, key in top) / tot
    return (x, y)


# ---------------------------------------------------------------------------
# Selftest — the survey's real defects, as the contract
# ---------------------------------------------------------------------------

def _selftest():
    ok = 0

    # frontmatter: duplicate key, inline comment, inline list, quoted scalar
    fm, body, warns = parse_frontmatter(
        "---\ntitle: \"Musk v. Altman\"\nstatus: active\n"
        "entity_type: nonprofit  # placeholder — SoftBank is for-profit\n"
        "tags: [us, litigation]\nparties_plaintiff: [\"Elon Musk\", \"xAI\"]\n"
        "status: judgment-defendant\n---\nBody [[companies/openai]] text\n")
    assert fm["status"] == "judgment-defendant"
    assert any("duplicate key 'status'" in w for w in warns)
    assert fm["entity_type"] == "nonprofit"
    assert any("inline comment" in w for w in warns)
    assert fm["tags"] == ["us", "litigation"]
    assert fm["parties_plaintiff"] == ["Elon Musk", "xAI"]
    assert fm["title"] == "Musk v. Altman"
    assert body.startswith("Body")
    ok += 1

    # dates: every survey defect class
    d, e = norm_date("2026-07-19 (preview)", EVENT)
    assert d and d["iso"] == "2026-07-19" and d["precision"] == "day"
    d, e = norm_date("2019", PUBLISHED)
    assert d and d["precision"] == "year"
    d, e = norm_date("2018 (district court); decided March 2026", EVENT)
    assert d and d["iso"] == "2018" and d["precision"] == "year"
    d, e = norm_date("not specified in available reporting", EVENT)
    assert d is None and "unparseable" in e
    d, e = norm_date("1970-01-01", PUBLISHED)
    assert d is None and "sentinel" in e
    d, e = norm_date("2026-05", CHECKED)
    assert d and d["precision"] == "month"
    d, e = norm_date("May 18, 2026", EVENT)
    assert d and d["iso"] == "2026-05-18"
    d, e = norm_date("3026-01-01", EVENT)
    assert d is None and "implausible" in e
    ok += 1

    # event extraction: explicit beats fallback; fallback is labelled published
    d, fb = extract_event_date(
        "The Third Circuit reversed the dismissal on July 29, 2026, splitting "
        "from the Ninth Circuit.", "2026-07-30")
    assert d["iso"] == "2026-07-29" and d["kind"] == EVENT and not fb
    d, fb = extract_event_date("A development with no stated date.",
                               "2026-07-30")
    assert d["kind"] == PUBLISHED and fb
    ok += 1

    # timeline coordinate: precision midpoints keep ordering sane
    assert iso_to_days("2012-01-01") == 0
    assert iso_to_days("2022-11-30") > iso_to_days("2022-11")  #月中 < 月末
    assert abs(iso_to_days("2020") - iso_to_days("2020-07-01")) < 1
    ok += 1

    # slug resolution against a fake tree
    idx = SlugIndex.__new__(SlugIndex)
    idx.by_path = {("companies", "anthropic"), ("sources", "anthropic"),
                   ("models", "gpt-56"), ("entities", "metr")}
    idx.by_slug = {"anthropic": [("companies", "anthropic"),
                                 ("sources", "anthropic")],
                   "gpt-56": [("models", "gpt-56")],
                   "metr": [("entities", "metr")]}
    assert idx.resolve("companies/anthropic") == ("companies", "anthropic")
    assert idx.resolve("anthropic") == ("companies", "anthropic")  # priority
    assert idx.resolve("companies/anthropic\\") == ("companies", "anthropic")
    assert idx.resolve("gpt-56|GPT-5.6") == ("models", "gpt-56")
    assert idx.resolve("metr#Relationships") == ("entities", "metr")
    assert idx.resolve("Wiki/models/gpt-56.md") == ("models", "gpt-56")
    assert idx.resolve("no-such-page") is None
    ok += 1

    # jurisdictions
    assert jurisdiction("US") == ("US", None)
    assert jurisdiction("United Kingdom") == ("GB", None)
    assert jurisdiction("global") == (None, None)
    j, e = jurisdiction("Atlantis")
    assert j is None and "unmapped" in e
    assert state_from_title("California SB 1047 (Frontier AI Models)") == "US-CA"
    assert state_from_title("EU AI Act") is None
    ok += 1

    # datum placement: new page lands between its neighbours, weighted
    av = {"a": [1.0, 0.0], "b": [0.0, 1.0], "c": [-1.0, 0.0]}
    ap = {"a": (0.2, 0.2), "b": (0.8, 0.8), "c": (0.5, 0.9)}
    p = place_new([1.0, 0.2], av, ap, k=2)
    assert p and 0.2 <= p[0] <= 0.8 and abs(p[0] - 0.2) < abs(p[0] - 0.8)
    assert place_new([0.0, 0.0], {"a": [0.0, 0.0]}, {"a": (0.5, 0.5)}) is None
    ok += 1

    return ok


if __name__ == "__main__":
    n = _selftest()
    print("frames.py selftest: %d groups passed" % n)
    idx = SlugIndex()
    print("live vault: %d pages indexed across %d folders"
          % (len(idx.by_path), len({f for f, _ in idx.by_path})))
    d, fb = extract_event_date(
        "🆕 The U.S. Court of Appeals for the Third Circuit reversed the "
        "dismissal of Cornish-Adebiyi v. Caesars Entertainment, No. 24-3006, "
        "on July 29, 2026", "2026-07-30")
    print("worked example: event date %s (kind=%s, fallback=%s)"
          % (d["iso"], d["kind"], fb))
