#!/usr/bin/env python3
"""build_site.py — the only deploy route (README §6).

    python3 build/build_site.py          gate → stamp → assemble web/ → docs/
    python3 build/build_site.py --dev    assemble web/data + web/fields only
                                         (no gate, no stamp, no docs/) — for
                                         local iteration; never deploy from it

Order matters: the gate runs FIRST and refuses to publish on any regression;
DATA_V is stamped BEFORE index.html is copied (a static host can serve stale
JSON after a successful push — the stamp is the only way to see it).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGED = os.path.join(ROOT, "Research", "staged")
WEB = os.path.join(ROOT, "web")
DOCS = os.path.join(ROOT, "docs")
MODELING = os.path.join(ROOT, "Research", "modeling")

# v2: trunk strip + counts, plus the T7 state-law counter that
# cl-state-laws-2026 is scored against (shipped so the claim's evidence
# travels with the claim; rendering it in the app is still open)
DATA_FILES = ["events.json", "meta.json", "witness-statelaw.json"]
FORECAST_DIR = os.path.join(STAGED, "forecast")


def assemble():
    os.makedirs(os.path.join(WEB, "data"), exist_ok=True)
    for n in DATA_FILES:
        src = os.path.join(STAGED, n)
        if not os.path.isfile(src):
            sys.exit("missing staged file: %s — run emit.py first" % n)
        shutil.copy2(src, os.path.join(WEB, "data", n))
    # v2: the forecast surface is the product
    if not os.path.isdir(FORECAST_DIR):
        sys.exit("missing staged/forecast — run forecast_emit.py first")
    fdst = os.path.join(WEB, "data", "forecast")
    os.makedirs(fdst, exist_ok=True)
    for n in os.listdir(FORECAST_DIR):
        shutil.copy2(os.path.join(FORECAST_DIR, n), os.path.join(fdst, n))
    # world-view geometry (ISC-licensed world-atlas; root data/ is gitignored
    # so the shipped copy lives in web/data)
    topo = os.path.join(ROOT, "data", "witness", "countries-110m.json")
    if os.path.isfile(topo):
        shutil.copy2(topo, os.path.join(WEB, "data", "countries-110m.json"))
    # v1 terrain retired (decision of record): drop stale v1 payloads
    for stale in ["arcs.json", "anchors50.json", "entities.json",
                  "series.json", "eras.json", "wikitime.json",
                  "territories.json"]:
        p = os.path.join(WEB, "data", stale)
        if os.path.isfile(p) and stale not in DATA_FILES:
            os.remove(p)
    fields_dst = os.path.join(WEB, "fields")
    if os.path.isdir(fields_dst):
        shutil.rmtree(fields_dst)
    print("assembled web/data (%d trunk files + forecast/%d + topo)"
          % (len(DATA_FILES), len(os.listdir(fdst))))


def main():
    dev = "--dev" in sys.argv
    if not dev:
        if os.environ.get("SKIP_AUDIT") == "1":
            print("SKIP_AUDIT=1 — validators skipped. Say so out loud, and "
                  "say why.")
        else:
            rc = subprocess.call([sys.executable,
                                  os.path.join(MODELING, "audit_all.py")])
            if rc != 0:
                sys.exit("audit gate FAILED (rc=%d) — refusing to publish" % rc)
    assemble()
    if dev:
        print("dev assembly done — serve the repo and open /web/")
        return
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M")
    # in-app update log: one line per build, shipped as data (Tectonic's
    # pattern) so a returning viewer sees the model breathing
    ul_path = os.path.join(WEB, "data", "updatelog.json")
    ul = json.load(open(ul_path)) if os.path.isfile(ul_path) else {"entries": []}
    meta = json.load(open(os.path.join(STAGED, "meta.json")))
    c = meta["counts"]
    ul["entries"].insert(0, {
        "stamp": stamp,
        "line": "%d entities · %d dated developments · %d relationships · "
                "datum %s" % (c["entities"], c["events"], c["arcs"],
                              meta.get("datum_version") or "v1")})
    ul["entries"] = ul["entries"][:30]
    json.dump(ul, open(ul_path, "w"))
    idx = open(os.path.join(WEB, "index.html")).read()
    idx2, n = re.subn(r'const DATA_V = "[^"]*"',
                      'const DATA_V = "%s"' % stamp, idx)
    if n != 1:
        sys.exit("DATA_V stamp point not found exactly once in web/index.html")
    open(os.path.join(WEB, "index.html"), "w").write(idx2)
    # docs/ = the built site
    os.makedirs(DOCS, exist_ok=True)
    for item in os.listdir(DOCS):
        p = os.path.join(DOCS, item)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for item in os.listdir(WEB):
        s = os.path.join(WEB, item)
        d = os.path.join(DOCS, item)
        shutil.copytree(s, d) if os.path.isdir(s) else shutil.copy2(s, d)
    open(os.path.join(DOCS, ".nojekyll"), "w").write("")
    print("built docs/ · DATA_V=%s" % stamp)
    print("after push, verify the live stamp:")
    print("  curl -s https://augustg97.github.io/ai-atlas/ | grep -o "
          "'DATA_V = \"[^\"]*\"'")


if __name__ == "__main__":
    main()
