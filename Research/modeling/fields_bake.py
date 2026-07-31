#!/usr/bin/env python3
"""fields_bake.py — bake the substrate fields from staged data (WP-01 §5).

Reads Research/staged/{entities,events,datum}.json and writes:

  staged/fields/terrain.png       R bedrock density · G territory id ·
                                  B territory margin (soft boundary)
  staged/fields/heat_<date>.png   R attention (14-day) · G settlement
                                  (existing entities, prominence-weighted) ·
                                  B freshness (3-day)
  staged/fields/manifest.json     keyframe dates, global scales, cadence

Cadence follows the evidence density (SCOPE §2): monthly keyframes from
2012-01 to 2026-03, weekly from the wiki horizon 2026-04-13 to today.
Settlement/attention use FIXED global scales so growth across time is real,
never per-frame renormalised (a per-frame normalisation would erase the
ChatGPT shock by making every era equally bright).

numpy + Pillow. Deterministic.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frames

HERE = os.path.dirname(os.path.abspath(__file__))
STAGED = os.path.join(HERE, "..", "staged")
FIELDS = os.path.join(STAGED, "fields")

N = 512
HORIZON = _dt.date(2026, 4, 13)
START = _dt.date(2012, 1, 1)


def _blur(H, sigma):
    """FFT gaussian blur, wrap-free (padded)."""
    pad = int(sigma * 3)
    Hp = np.pad(H, pad, mode="constant")
    n = Hp.shape[0]
    fx = np.fft.fftfreq(n)
    g = np.exp(-2 * (math.pi * sigma) ** 2 * (fx ** 2))
    K = np.outer(g, g)
    out = np.real(np.fft.ifft2(np.fft.fft2(Hp) * K))
    return out[pad:-pad, pad:-pad] if pad else out


def _splat(points, weights, sigma):
    H = np.zeros((N, N))
    if len(points):
        xs = np.clip((np.array([p[0] for p in points]) * N).astype(int), 0, N - 1)
        ys = np.clip((np.array([p[1] for p in points]) * N).astype(int), 0, N - 1)
        np.add.at(H, (ys, xs), np.asarray(weights, dtype=float))
    return _blur(H, sigma)


def _date_of(iso):
    p = iso.split("-")
    if len(p) == 3:
        return _dt.date(*map(int, p))
    if len(p) == 2:
        return _dt.date(int(p[0]), int(p[1]), 15)
    return _dt.date(int(p[0]), 7, 1)


def keyframe_dates(today):
    dates = []
    d = START
    while d < _dt.date(2026, 4, 1):
        dates.append(d)
        d = (d.replace(day=1) + _dt.timedelta(days=32)).replace(day=1)
    d = HORIZON
    while d <= today:
        dates.append(d)
        d += _dt.timedelta(days=7)
    if dates[-1] != today:
        dates.append(today)
    return dates


def prominence(e, usd_at):
    p = 1.0 + math.log1p(e.get("indeg", 0))
    v = usd_at.get(e["id"], 0.0)
    if v:
        p += math.log1p(v) / 2.0
    return p


def bake():
    ents = json.load(open(os.path.join(STAGED, "entities.json")))["entities"]
    evs = json.load(open(os.path.join(STAGED, "events.json")))["events"]
    datum = json.load(open(os.path.join(STAGED, "datum.json")))
    series = json.load(open(os.path.join(STAGED, "series.json")))["series"]
    pos = datum["positions"]
    terr_of = datum["territory_of"]
    tnames = sorted(datum["territory_centroids"].keys())
    os.makedirs(FIELDS, exist_ok=True)

    # ---- terrain (static per datum version) ----
    all_pts = [pos[p] for p in pos]
    bedrock = _splat(all_pts, [1.0] * len(all_pts), 16)
    bedrock = bedrock / (np.percentile(bedrock, 99.5) + 1e-9)
    planes = []
    for t in tnames:
        pts = [pos[p] for p in pos if terr_of.get(p) == t]
        planes.append(_splat(pts, [1.0] * len(pts), 20))
    P = np.stack(planes)                                  # (T, N, N)
    tid = np.argmax(P, axis=0)
    top2 = np.sort(P, axis=0)[-2:]
    margin = (top2[1] - top2[0]) / (top2[1] + top2[0] + 1e-9)
    img = np.zeros((N, N, 3), dtype=np.uint8)
    img[..., 0] = np.clip(np.sqrt(np.clip(bedrock, 0, 1)) * 255, 0, 255)
    img[..., 1] = (tid * (255 // max(len(tnames) - 1, 1))).astype(np.uint8)
    img[..., 2] = np.clip(margin * 255, 0, 255)
    Image.fromarray(img).save(os.path.join(FIELDS, "terrain.png"))

    # ---- prepare dated inputs: the WHOLE dated record feeds attention ----
    # (dev-log items · entity window-starts · source publications — one
    #  mechanism, stated in About; dev-log coverage alone would render the
    #  pre-horizon era dark and fail the ChatGPT-shock test, and did)
    ev_pts = [(e["pos"], _date_of(e["date"]["iso"]), 1.0,
               e["date"].get("precision", "day")) for e in evs if e.get("pos")]
    spine = json.load(open(os.path.join(STAGED, "spine.json")))["sources"]
    for s in spine:
        if s.get("pos") and s.get("date"):
            ev_pts.append((s["pos"], _date_of(s["date"]["iso"]), 0.55,
                           s["date"].get("precision", "day")))
    for e in ents:
        p = pos.get(e["id"])
        if p and e.get("window"):
            ev_pts.append((p, _date_of(e["window"]["iso"]), 2.2,
                           e["window"].get("precision", "day")))
    usd_rows = {}
    for r in series:
        if r.get("usd_b"):
            usd_rows.setdefault(r["entity"], []).append(
                (_date_of(r["date"]["iso"]), r["usd_b"]))
    for k in usd_rows:
        usd_rows[k].sort()
    ent_list = [(e, pos.get(e["id"]),
                 _date_of(e["window"]["iso"]) if e.get("window") else None)
                for e in ents if pos.get(e["id"])]

    today = _dt.date.today()
    dates = keyframe_dates(today)

    # fixed global scales measured at the busiest frame (the last weekly one)
    def frame_arrays(kd):
        att_pts, att_w = [], []
        # attention window widens pre-horizon (monthly cadence, sparser
        # record): 45 days before, 14 after — matching keyframe spacing
        span = 14 if kd >= HORIZON else 45
        for p, d, w0, prec in ev_pts:
            if prec == "day":
                dd = (kd - d).days
                if 0 <= dd <= span:
                    att_pts.append(p)
                    att_w.append(w0 * (1.0 - dd / (span + 1.0)))
            elif prec == "month":
                # "sometime that month": flat, diluted across ~2 keyframes
                if 0 <= (kd - d).days <= max(span, 31):
                    att_pts.append(p)
                    att_w.append(w0 * 0.45)
            else:
                # "sometime that year": a smear, never a July-1 spike —
                # unsmeared year-dates were the top-6 phantom bursts
                if d.year == kd.year:
                    att_pts.append(p)
                    att_w.append(w0 * 0.10)
        fresh_pts = [p for p, d, w0, prec in ev_pts
                     if prec == "day" and 0 <= (kd - d).days <= 3]
        usd_at = {}
        for eid, rows in usd_rows.items():
            best = 0.0
            for d, v in rows:
                if d <= kd:
                    best = v
            if best:
                usd_at[eid] = best
        set_pts, set_w = [], []
        for e, p, wfrom in ent_list:
            if wfrom is None:
                w = 0.30 * (1.0 + math.log1p(e.get("indeg", 0)))
            elif wfrom <= kd:
                w = prominence(e, usd_at)
            else:
                continue
            set_pts.append(p)
            set_w.append(w)
        A = _splat(att_pts, att_w, 7)
        S = _splat(set_pts, set_w, 10)
        F = _splat(fresh_pts, [1.0] * len(fresh_pts), 4)
        return A, S, F

    A_ref, S_ref, F_ref = frame_arrays(dates[-1])
    sA = np.percentile(A_ref, 99.8) + 1e-9
    sS = np.percentile(S_ref, 99.8) + 1e-9
    sF = np.percentile(F_ref, 99.8) + 1e-9

    manifest = {"terrain": "terrain.png", "territories": tnames,
                "scales": {"attention": float(sA), "settlement": float(sS),
                           "freshness": float(sF)},
                "keyframes": []}
    for kd in dates:
        A, S, F = frame_arrays(kd)
        img = np.zeros((N, N, 3), dtype=np.uint8)
        img[..., 0] = np.clip(np.sqrt(np.clip(A / sA, 0, 1)) * 255, 0, 255)
        img[..., 1] = np.clip(np.sqrt(np.clip(S / sS, 0, 1)) * 255, 0, 255)
        img[..., 2] = np.clip(np.sqrt(np.clip(F / sF, 0, 1)) * 255, 0, 255)
        name = "heat_%s.png" % kd.isoformat()
        Image.fromarray(img).save(os.path.join(FIELDS, name))
        manifest["keyframes"].append({"date": kd.isoformat(), "file": name})
    json.dump(manifest, open(os.path.join(FIELDS, "manifest.json"), "w"))
    total = sum(os.path.getsize(os.path.join(FIELDS, f))
                for f in os.listdir(FIELDS))
    return {"keyframes": len(dates), "fields_kb": total // 1024,
            "scales": manifest["scales"]}


def _selftest():
    H = _splat([(0.5, 0.5)], [1.0], 5)
    assert H.shape == (N, N)
    cy, cx = np.unravel_index(np.argmax(H), H.shape)
    assert abs(cx - N // 2) <= 1 and abs(cy - N // 2) <= 1
    assert H[0, 0] < H[N // 2, N // 2] / 100
    ds = keyframe_dates(_dt.date(2026, 7, 31))
    assert ds[0] == _dt.date(2012, 1, 1)
    assert _dt.date(2026, 4, 13) in ds
    monthly = [d for d in ds if d < _dt.date(2026, 4, 1)]
    assert 170 <= len(monthly) <= 172
    return 1


if __name__ == "__main__":
    _selftest()
    print("fields_bake selftest passed")
    if "--selftest" in sys.argv:
        sys.exit(0)
    print(json.dumps(bake(), indent=1))
