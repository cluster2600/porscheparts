"""Plane sections of a triangle mesh, chained into loops, and loop fits.

Segments are chained by mesh-edge identity (the pair of vertex indices each
section point lies on), not by coordinate tolerance, so no gap is bridged: a
loop is closed only if the mesh surface is closed around it.
"""
from __future__ import annotations

import numpy as np


def section_loops(v: np.ndarray, f: np.ndarray, normal: np.ndarray, offset: float):
    """Cut the mesh with the plane normal.x = offset.

    Returns a list of (points (n, 3), closed bool).
    """
    normal = np.asarray(normal, float)
    normal = normal / np.linalg.norm(normal)
    d = v @ normal - offset
    d = np.where(d == 0.0, 1e-12, d)  # keep vertices off the plane
    pos = d[f] > 0
    cut = pos.any(1) & ~pos.all(1)
    tri = f[cut]
    seg_edges = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        a, b = tri[:, i], tri[:, j]
        crosses = (d[a] > 0) != (d[b] > 0)
        seg_edges.append(np.where(crosses[:, None], np.sort(np.stack([a, b], 1), 1), -1))
    E = np.stack(seg_edges, 1)  # (m, 3, 2)
    has = E[:, :, 0] >= 0
    pairs = np.array([E[k][has[k]] for k in range(len(E))]).reshape(-1, 2, 2)
    if len(pairs) == 0:
        return []
    flat = pairs.reshape(-1, 2)
    keys, ids = np.unique(flat, axis=0, return_inverse=True)
    ids = ids.reshape(-1, 2)
    ka, kb = keys[:, 0], keys[:, 1]
    t = d[ka] / (d[ka] - d[kb])
    kp = v[ka] + t[:, None] * (v[kb] - v[ka])
    adj: dict[int, list[int]] = {}
    for s, (a, b) in enumerate(ids):
        adj.setdefault(int(a), []).append(s)
        adj.setdefault(int(b), []).append(s)
    used = np.zeros(len(ids), bool)
    loops = []
    for s0 in range(len(ids)):
        if used[s0]:
            continue
        used[s0] = True
        start, cur = int(ids[s0, 0]), int(ids[s0, 1])
        chain = [start, cur]
        closed = False
        while True:
            nxt = [s for s in adj[cur] if not used[s]]
            if not nxt:
                break
            s = nxt[0]
            used[s] = True
            a2, b2 = int(ids[s, 0]), int(ids[s, 1])
            cur = b2 if a2 == cur else a2
            if cur == start:
                closed = True
                break
            chain.append(cur)
        if not closed:
            # extend backwards from start
            cur = start
            back = []
            while True:
                nxt = [s for s in adj[cur] if not used[s]]
                if not nxt:
                    break
                s = nxt[0]
                used[s] = True
                a2, b2 = int(ids[s, 0]), int(ids[s, 1])
                cur = b2 if a2 == cur else a2
                back.append(cur)
            chain = back[::-1] + chain
        loops.append((kp[np.asarray(chain)], closed))
    return loops


def polygon_area_2d(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def fit_circle_2d(p: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Algebraic (Kasa) least-squares circle: centre, radius, RMS radial residual."""
    A = np.column_stack([2 * p[:, 0], 2 * p[:, 1], np.ones(len(p))])
    b = (p ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:2]
    r = float(np.sqrt(sol[2] + c @ c))
    res = np.linalg.norm(p - c, axis=1) - r
    return c, r, float(np.sqrt((res ** 2).mean()))
