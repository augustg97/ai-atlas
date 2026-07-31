#!/usr/bin/env python3
"""datum_build.py — cut and freeze datum v1 (register A2; SCOPE §5).

Reads the vault's LanceDB embedding store (voyage-3-large, 1024-d, chunk
level), builds page vectors, reduces to 50 dims (PCA), lays out 2-D with a
deterministic seeded refinement (PCA-2 init → kNN attraction + sampled
repulsion), assigns territories from the dev-log's own 13-section usage, and
writes:

  Research/staged/datum.json      positions + territories (shipped)
  Research/staged/anchors50.json  int8 50-d anchors + PCA basis (shipped;
                                  powers place_new for post-freeze pages and
                                  the chat index)

The method is numpy-only ON PURPOSE: no sklearn/umap version can drift a
future rebase. Same inputs + same seed = same map, forever.

Determinism: seed 20260731. Layout params recorded in the datum meta.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frames import VAULT, FOLDERS
from emit import FEATURE_FOLDERS

HERE = os.path.dirname(os.path.abspath(__file__))
STAGED = os.path.join(HERE, "..", "staged")
LANCE = os.path.join(VAULT, "embeddings", "lance")

SEED = 20260731
K_NN = 12
ITERS = 300
DIM_R = 50

SECTIONS = [
    "AI Industry & Markets", "Federal AI Policy & Agency Action",
    "Compute, Chips & Infrastructure", "Frontier Models & Capabilities",
    "AI Safety, Alignment & Interpretability",
    "AI Litigation, Liability & Enforcement",
    "Labor, Society & Democratic Institutions", "Agentic AI & Coding",
    "National Security & Geopolitics", "International AI Regulation",
    "AI Adoption by Industry", "U.S. State AI Legislation",
    "AI Standards & Safety Frameworks",
]


def load_page_vectors():
    import lancedb
    db = lancedb.connect(LANCE)
    t = db.open_table("wiki")
    rows = t.search().limit(200000).select(
        ["id", "source", "kind", "vector"]).to_list()
    by_page = {}
    for r in rows:
        src, kind = r["source"], r["kind"]
        if kind == "wiki" and src.startswith("Wiki/"):
            parts = src.split("/")
            if len(parts) == 3 and parts[1] in FOLDERS:
                pid = "%s/%s" % (parts[1], parts[2][:-3])
                by_page.setdefault(pid, []).append(
                    np.asarray(r["vector"], dtype=np.float32))
    pages = {pid: np.mean(vs, axis=0) for pid, vs in by_page.items()}
    protos, proto_counts = section_prototypes(pages)
    return pages, protos, proto_counts


def section_prototypes(pages):
    """A section's prototype = tf-idf-weighted mean of the page vectors its
    dev-log events actually target (staged/events.json). First attempt used
    'dev-log chunks containing exactly one section header' — but files chunk
    whole, so 12 of 13 sections got <3 chunks and every page fell into the
    one surviving territory. Event targets are per-item ground truth."""
    ev = json.load(open(os.path.join(STAGED, "events.json")))["events"]
    sec_counts = {s: {} for s in SECTIONS}
    tot_counts = {}
    for e in ev:
        if e["section"] not in sec_counts:
            continue
        for t in e["targets"]:
            if t in pages:
                sec_counts[e["section"]][t] = \
                    sec_counts[e["section"]].get(t, 0) + 1
                tot_counts[t] = tot_counts.get(t, 0) + 1
    protos, counts = {}, {}
    for s, tc in sec_counts.items():
        counts[s] = len(tc)
        if len(tc) < 5:
            continue
        vs, ws = [], []
        for t, c in tc.items():
            vs.append(pages[t])
            ws.append(c / tot_counts[t])          # distinctive targets weigh
        W = np.asarray(ws)[:, None]
        protos[s] = (np.stack(vs) * W).sum(0) / (W.sum() + 1e-9)
    return protos, counts


def pca(X, k):
    mean = X.mean(axis=0)
    Xc = X - mean
    # economy SVD on (n × 1024)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    comps = Vt[:k]
    return mean, comps, Xc @ comps.T


def layout(X50, seed=SEED, k=K_NN, iters=ITERS):
    """Deterministic 2-D refinement: PCA-2 init, kNN attraction in 50-d,
    sampled repulsion. Small, owned, reproducible."""
    rng = np.random.default_rng(seed)
    n = X50.shape[0]
    # cosine kNN in 50-d
    Xn = X50 / (np.linalg.norm(X50, axis=1, keepdims=True) + 1e-9)
    sims = Xn @ Xn.T
    np.fill_diagonal(sims, -1)
    nbr = np.argsort(-sims, axis=1)[:, :k]
    # init from first two PCA comps, scaled to unit-ish box
    P = X50[:, :2].copy()
    P = (P - P.mean(0)) / (P.std(0) + 1e-9) * 0.18
    lr = 0.06
    for it in range(iters):
        f = np.zeros_like(P)
        # attraction to kNN
        for j in range(k):
            d = P[nbr[:, j]] - P
            dist = np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
            w = sims[np.arange(n), nbr[:, j]][:, None].clip(0.05, None)
            f += w * d * np.clip(dist, 0, 0.3) / dist
        # sampled repulsion (8 negatives per point per iter)
        neg = rng.integers(0, n, size=(n, 8))
        for j in range(8):
            d = P - P[neg[:, j]]
            dist2 = (d * d).sum(1, keepdims=True) + 1e-4
            f += 0.012 * d / dist2
        P += lr * f
        lr *= 0.995
    # normalise into [0.05, 0.95] with equal aspect
    span = (P.max(0) - P.min(0)).max() + 1e-9
    P = (P - P.min(0)) / span
    P = 0.05 + 0.90 * (P + (0.90 - 0.90 * (P.max(0) - P.min(0)) / 1.0) / 2
                       * 0)  # keep proportional; centre below
    off = (0.95 - P.max(0) - (0.05 - P.min(0))) / 2
    P += off
    return P


def build():
    pages, protos, proto_counts = load_page_vectors()
    ids = sorted(pages.keys())
    X = np.stack([pages[i] for i in ids])
    mean, comps, X50 = pca(X, DIM_R)
    P = layout(X50)

    # territories: nearest section prototype in full 1024-d space
    pnames = sorted(protos.keys())
    PV = np.stack([protos[s] for s in pnames])
    PVn = PV / (np.linalg.norm(PV, axis=1, keepdims=True) + 1e-9)
    Xn = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    terr_idx = np.argmax(Xn @ PVn.T, axis=1)
    territory_of = {ids[i]: pnames[terr_idx[i]] for i in range(len(ids))}
    centroids = {}
    for s in pnames:
        member = [i for i in range(len(ids)) if territory_of[ids[i]] == s]
        if member:
            centroids[s] = [round(float(P[member, 0].mean()), 4),
                            round(float(P[member, 1].mean()), 4)]
    positions = {ids[i]: [round(float(P[i, 0]), 4),
                          round(float(P[i, 1]), 4)]
                 for i in range(len(ids))}

    version = "v1-" + _dt.date.today().isoformat()
    datum = {
        "version": version,
        "method": {"backend": "voyage-3-large/1024", "page_vec": "chunk mean",
                   "reduce": "pca%d" % DIM_R,
                   "layout": "pca2init+knn%d-attract+neg8-repulse×%d"
                             % (K_NN, ITERS),
                   "seed": SEED,
                   "territory": "argmax cos vs dev-log section prototypes "
                                "(chunks containing exactly one section "
                                "header; counts %s)" % proto_counts},
        "positions": positions,
        "territory_of": territory_of,
        "territory_centroids": centroids,
        "section_territory": {s: s for s in pnames},
    }
    os.makedirs(STAGED, exist_ok=True)
    json.dump(datum, open(os.path.join(STAGED, "datum.json"), "w"),
              separators=(",", ":"))

    # anchors: int8-quantised 50-d + PCA basis (for place_new + chat index)
    scale = float(np.abs(X50).max()) / 127.0
    anchors = {
        "version": version, "scale": scale,
        "pca_mean": [round(float(v), 5) for v in mean],
        "pca_comps": [[round(float(v), 5) for v in row] for row in comps],
        "pages": {ids[i]: {
            "v": [int(x) for x in np.round(X50[i] / scale)],
            "pos": positions[ids[i]]} for i in range(len(ids))},
    }
    json.dump(anchors, open(os.path.join(STAGED, "anchors50.json"), "w"),
              separators=(",", ":"))

    # quantisation recall check (register E1): top-8 cosine neighbours in
    # float50 vs int8-50 — how many of the true 8 survive quantisation?
    Q = np.round(X50 / scale) * scale
    Xn50 = X50 / (np.linalg.norm(X50, axis=1, keepdims=True) + 1e-9)
    Qn = Q / (np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9)
    sub = np.random.default_rng(SEED).integers(0, len(ids), 200)
    recall = []
    S_true = Xn50[sub] @ Xn50.T
    S_q = Qn[sub] @ Qn.T
    for r in range(len(sub)):
        t8 = set(np.argsort(-S_true[r])[1:9])
        q8 = set(np.argsort(-S_q[r])[1:9])
        recall.append(len(t8 & q8) / 8.0)
    rec = float(np.mean(recall))

    return {"pages": len(ids), "territories": {s: int((terr_idx ==
            pnames.index(s)).sum()) for s in pnames},
            "proto_counts": proto_counts, "version": version,
            "int8_top8_recall": round(rec, 3),
            "datum_kb": os.path.getsize(os.path.join(STAGED, "datum.json"))
            // 1024,
            "anchors_kb": os.path.getsize(os.path.join(STAGED,
                                          "anchors50.json")) // 1024}


def _selftest():
    rng = np.random.default_rng(1)
    X = np.vstack([rng.normal(0, 1, (30, 8)) + off
                   for off in ([0] * 8, [6] + [0] * 7, [0, 6] + [0] * 6)])
    mean, comps, Xr = pca(X, 4)
    assert Xr.shape == (90, 4)
    P = layout(Xr[:, :4] if Xr.shape[1] >= 4 else Xr, iters=80)
    assert P.shape == (90, 2)
    assert P.min() > 0.0 and P.max() < 1.0
    # the three clusters must separate: mean intra-cluster distance far below
    # mean inter-cluster distance
    c = [P[:30], P[30:60], P[60:]]
    intra = np.mean([np.linalg.norm(g - g.mean(0), axis=1).mean() for g in c])
    inter = np.mean([np.linalg.norm(c[a].mean(0) - c[b].mean(0))
                     for a in range(3) for b in range(a + 1, 3)])
    assert inter > 2.5 * intra, (intra, inter)
    # determinism
    P2 = layout(Xr[:, :4], iters=80)
    assert np.allclose(P, P2)
    return 1


if __name__ == "__main__":
    _selftest()
    print("datum_build selftest passed (clusters separate, deterministic)")
    if "--selftest" in sys.argv:
        sys.exit(0)
    stats = build()
    print(json.dumps(stats, indent=1))
