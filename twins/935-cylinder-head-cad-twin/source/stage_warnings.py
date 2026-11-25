#!/usr/bin/env python3
"""What the two NVIDIA warnings on the CAD-body stage are, and whether a repair can clear them.

The NVIDIA validator reports two warnings on ``/Head935/BareHead`` (issue #707):

  ZeroAreaFaceChecker (VG.019)  a face whose single-precision cross product is exactly zero;
  WeldChecker (VG.016)          points whose single-precision coordinates are identical.

An OpenUSD ``points`` attribute holds float32. The body behind the stage is written in double
precision by the loft union (``v2-loft-s025.npz``), and the stage holds exactly its float32 cast.
``audit`` counts what the rules see on the stage and sorts it by what it is in double precision.

``trials`` then tries three repairs that keep the surface closed and consistently wound, each
under the tolerance TOL_MM fixed here before any of them ran on the body:

  broad     collapse every edge shorter than TOL_MM and flip every cap lower than TOL_MM;
  float32   collapse an edge whose ends are one float32 point or are closer than TOL_MM, and flip
            only a face that is flat in float32;
  manifold  manifold3d's own simplification at TOL_MM, which keeps a manifold by construction.

A collapse is allowed only under the link condition (the two ends share exactly the two opposite
corners) and if no remaining face turns over or loses its area. A flip swaps the longest edge of a
cap (its third corner strictly between the ends) for the edge to the far corner of the neighbour,
only if that edge does not exist and both new faces keep the neighbour's orientation. Deleting a
face would open the surface and welding points that share no edge would pinch it, so neither is
tried. A repair clears a warning only if nothing of it remains; anything left is reported.

Interpreter: numpy, usd-core and manifold3d (the ~/cad-env of this host).
Usage: stage_warnings.py STAGE.usdc BODY.npz OUT.json
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

TOL_MM = 1.0e-4   # the weld tolerance of simready_check.py: 0.1 micrometre


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _normal(p: np.ndarray) -> np.ndarray:
    return np.cross(p[1] - p[0], p[2] - p[0])


def flat_in_float32(v: np.ndarray, f: np.ndarray) -> np.ndarray:
    """Faces whose float32 cross product is exactly zero, as ZeroAreaFaceChecker computes it."""
    t = np.asarray(v, dtype=np.float32)[f]
    return ~np.any(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]) != 0, axis=1)


def colocated_groups(v: np.ndarray) -> list[list[int]]:
    """Groups of points with identical float32 coordinates, as WeldChecker sees them."""
    p = np.asarray(v, dtype=np.float32)
    _, inverse, count = np.unique(p, axis=0, return_inverse=True, return_counts=True)
    inverse = inverse.reshape(-1)
    groups: dict[int, list[int]] = {}
    for i in np.where(count[inverse] > 1)[0]:
        groups.setdefault(int(inverse[i]), []).append(int(i))
    return list(groups.values())


def signed_volume(v: np.ndarray, f: np.ndarray) -> float:
    t = np.asarray(v, dtype=np.float64)[f]
    return float(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0)


def topology(f: np.ndarray) -> dict:
    """Closed and consistently wound: every directed edge once, and its reverse once."""
    half = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]).astype(np.int64)
    n = int(half.max()) + 1
    key, rev = half[:, 0] * n + half[:, 1], half[:, 1] * n + half[:, 0]
    unique, count = np.unique(key, return_counts=True)
    paired = np.isin(rev, unique)
    return {"closed_and_consistently_wound": bool((count == 1).all() and paired.all()),
            "directed_edges_repeated": int((count > 1).sum()), "edges_without_reverse": int((~paired).sum())}


class Surface:
    """Indexed triangles with a vertex-to-face map that the local operations keep current."""

    def __init__(self, v, f):
        self.v = np.asarray(v, dtype=np.float64)
        self.f = np.array(f, dtype=np.int64)
        self.alive = np.ones(len(self.f), dtype=bool)
        flat = self.f.ravel()
        order = np.argsort(flat, kind="stable")
        self._face_of = order // 3
        self._start = np.searchsorted(flat[order], np.arange(len(self.v) + 1))
        self._faces: dict[int, set[int]] = {}
        self.moved_mm = 0.0
        self.surface_change_mm = 0.0

    def faces(self, i: int) -> set[int]:
        s = self._faces.get(i)
        if s is None:
            s = {int(k) for k in self._face_of[self._start[i]:self._start[i + 1]] if self.alive[k]}
            self._faces[i] = s
        return s

    def ring(self, i: int) -> set[int]:
        return {int(x) for k in self.faces(i) for x in self.f[k]} - {i}

    def collapse(self, a: int, b: int, tol: float) -> bool:
        keep, drop = min(a, b), max(a, b)
        length = float(np.linalg.norm(self.v[keep] - self.v[drop]))
        if length >= tol:
            return False
        shared = self.faces(keep) & self.faces(drop)
        if len(shared) != 2:
            return False
        opposite = set()
        for k in shared:
            opposite |= {int(x) for x in self.f[k]} - {keep, drop}
        if len(opposite) != 2 or (self.ring(keep) & self.ring(drop)) != opposite:
            return False
        moved = self.faces(drop) - shared
        for k in moved:
            before = _normal(self.v[self.f[k]])
            tri = self.f[k].copy()
            tri[tri == drop] = keep
            after = _normal(self.v[tri])
            if not np.any(after) or (np.any(before) and float(before @ after) <= 0.0):
                return False
        self.alive[list(shared)] = False
        for k in moved:
            self.f[k][self.f[k] == drop] = keep
        self._faces[keep] = (self.faces(keep) | moved) - shared
        for o in opposite:
            self._faces[o] = self.faces(o) - shared
        self._faces[drop] = set()
        self.moved_mm = max(self.moved_mm, length)
        return True

    def flip(self, k: int, tol: float) -> bool:
        tri = [int(x) for x in self.f[k]]
        p = self.v[tri]
        j = int(np.argmax([np.linalg.norm(p[(i + 1) % 3] - p[i]) for i in range(3)]))
        a, b, c = tri[j], tri[(j + 1) % 3], tri[(j + 2) % 3]
        ab = self.v[b] - self.v[a]
        s = float((self.v[c] - self.v[a]) @ ab / (ab @ ab))
        height = float(np.linalg.norm(self.v[c] - self.v[a] - s * ab))
        if not (0.0 < s < 1.0) or height >= tol:
            return False
        across = (self.faces(a) & self.faces(b)) - {k}
        if len(across) != 1:
            return False
        k2 = across.pop()
        t2 = [int(x) for x in self.f[k2]]
        i = t2.index(b)
        if t2[(i + 1) % 3] != a:
            return False
        d = t2[(i + 2) % 3]
        if d == c or d in self.ring(c):
            return False
        n_old = _normal(self.v[[b, a, d]])
        n1, n2 = _normal(self.v[[b, c, d]]), _normal(self.v[[c, a, d]])
        if not np.any(n_old) or float(n1 @ n_old) <= 0.0 or float(n2 @ n_old) <= 0.0:
            return False
        self.f[k], self.f[k2] = (b, c, d), (c, a, d)
        self._faces[a] = self.faces(a) - {k}
        self._faces[b] = self.faces(b) - {k2}
        self._faces[c] = self.faces(c) | {k2}
        self._faces[d] = self.faces(d) | {k}
        self.surface_change_mm = max(self.surface_change_mm, height)
        return True

    def compact(self) -> tuple[np.ndarray, np.ndarray]:
        keep = self.f[self.alive]
        used = np.unique(keep)
        remap = -np.ones(len(self.v), dtype=np.int64)
        remap[used] = np.arange(len(used))
        return self.v[used], remap[keep]


def repair(v, f, mode: str, tol: float = TOL_MM, rounds: int = 20):
    """One of the local-operation trials ('broad' or 'float32'); returns (v, f, counts)."""
    s = Surface(v, f)
    collapses = flips = 0
    for _ in range(rounds):
        changed = 0
        ids = np.where(s.alive)[0]
        tri = s.f[ids]
        p64 = s.v[tri]
        p32 = s.v.astype(np.float32)[tri]
        pairs = {}
        for j in range(3):
            length = np.linalg.norm(p64[:, j] - p64[:, (j + 1) % 3], axis=1)
            short = length < tol
            if mode == "float32":
                short |= np.all(p32[:, j] == p32[:, (j + 1) % 3], axis=1)
            for a, b, ln in zip(tri[short, j], tri[short, (j + 1) % 3], length[short]):
                pairs[(min(int(a), int(b)), max(int(a), int(b)))] = float(ln)
        for (a, b), _ in sorted(pairs.items(), key=lambda item: item[1]):
            if b in s.ring(a) and s.collapse(a, b, tol):
                changed += 1
                collapses += 1
        ids = np.where(s.alive)[0]
        if mode == "float32":
            candidates = ids[flat_in_float32(s.v, s.f[ids])]
        else:
            p = s.v[s.f[ids]]
            area2 = np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
            longest = np.max([np.linalg.norm(p[:, (j + 1) % 3] - p[:, j], axis=1) for j in range(3)], axis=0)
            height = area2 / np.where(longest > 0, longest, 1.0)
            candidates = ids[np.argsort(height)[: int((height < tol).sum())]]
        for k in candidates:
            if s.alive[k] and s.flip(int(k), tol):
                changed += 1
                flips += 1
        if not changed:
            break
    v2, f2 = s.compact()
    return v2, f2, {"edges_collapsed": collapses, "caps_flipped": flips,
                    "largest_vertex_move_mm": float(f"{s.moved_mm:.3e}"),
                    "largest_surface_change_mm": float(f"{s.surface_change_mm:.3e}")}


def classify_groups(v: np.ndarray, f: np.ndarray, groups: list[list[int]]) -> dict:
    """Where the co-located points sit relative to each other on the surface."""
    s = Surface(v, f)
    kinds: Counter = Counter()
    for g in groups:
        a, b = g[0], g[1]
        if b in s.ring(a):
            kinds["joined_by_an_edge"] += 1
            continue
        common = s.ring(a) & s.ring(b)
        double_cap = any(
            {int(c) for k in s.faces(x) & s.faces(y) for c in s.f[k]} - {x, y} == {a, b}
            for x in common for y in common if x < y and y in s.ring(x))
        if double_cap:
            kinds["far_corners_of_the_two_faces_on_one_edge"] += 1
        elif common:
            kinds["share_a_neighbour_only"] += 1
        else:
            frontier, seen, hops = {a}, {a}, 0
            while frontier and b not in seen and hops < 4:
                frontier = {y for x in frontier for y in s.ring(x)} - seen
                seen |= frontier
                hops += 1
            kinds["more_than_four_edges_apart" if b not in seen else "two_to_four_edges_apart"] += 1
    return dict(sorted(kinds.items()))


def findings(v: np.ndarray, f: np.ndarray, reference_volume: float) -> dict:
    groups = colocated_groups(v)
    return {"faces": int(len(f)), "points": int(len(v)),
            "faces_flat_in_float32": int(flat_in_float32(v, f).sum()),
            "colocated_float32_groups": len(groups), "colocated_float32_points": int(sum(len(g) for g in groups)),
            "volume_change_mm3": float(f"{signed_volume(v, f) - reference_volume:.3e}"),
            **topology(f)}


def audit(stage: Path, body: Path) -> dict:
    from pxr import Usd, UsdGeom

    opened = Usd.Stage.Open(str(stage))
    mesh = UsdGeom.Mesh(opened.GetPrimAtPath("/Head935/BareHead"))
    p32 = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float32)
    fs = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64).reshape(-1, 3)
    d = np.load(body)
    v, f = np.asarray(d["v"], dtype=np.float64), np.asarray(d["f"], dtype=np.int64)
    flat = np.where(flat_in_float32(p32, fs))[0]
    t = v[f]
    cross64 = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
    caps, min_edge = 0, []
    for k in flat:
        q = v[f[k]]
        e = [np.linalg.norm(q[(i + 1) % 3] - q[i]) for i in range(3)]
        j = int(np.argmax(e))
        a, b, c = q[j], q[(j + 1) % 3], q[(j + 2) % 3]
        s = float((c - a) @ (b - a) / ((b - a) @ (b - a)))
        caps += int(min(e) > 0 and 0.0 < s < 1.0)
        min_edge.append(min(e))
    groups = colocated_groups(p32)
    separation = [max(float(np.linalg.norm(v[i] - v[g[0]])) for i in g) for g in groups]
    spacing = float(np.spacing(np.abs(np.array([p32[g[0]] for g in groups])).max())) if groups else None
    return {
        "stage_sha256": sha256(stage), "body_sha256": sha256(body),
        "stage_points_are_float32_of_body": bool(np.array_equal(v.astype(np.float32), p32)),
        "stage_faces_are_body_faces": bool(np.array_equal(f, fs)),
        "zero_area_face_checker": {
            "faces_flat_in_float32": int(len(flat)),
            "faces_below_1e-12_mm2_in_double": int((cross64 < 1.0e-12).sum()),
            "faces_exactly_flat_in_double": int((cross64 == 0).sum()),
            "flat_faces_that_are_caps": caps,
            "shortest_edge_of_a_flat_face_mm": [float(f"{min(min_edge):.2e}"), float(f"{max(min_edge):.2e}")],
        },
        "weld_checker": {
            "colocated_float32_groups": len(groups),
            "colocated_float32_points": int(sum(len(g) for g in groups)),
            "groups_distinct_in_double": int(sum(x > 0 for x in separation)),
            "groups_coincident_in_double": int(sum(x == 0 for x in separation)),
            "largest_separation_in_double_mm": float(f"{max(separation):.3e}"),
            "float32_spacing_at_these_points_mm": spacing,
            "where_they_sit": classify_groups(v, f, groups),
        },
    }


def trials(body: Path, tol: float = TOL_MM) -> dict:
    import manifold3d as m3

    d = np.load(body)
    v, f = np.asarray(d["v"], dtype=np.float64), np.asarray(d["f"], dtype=np.int64)
    volume = signed_volume(v, f)
    out = {"tol_mm": tol}
    for mode in ("broad", "float32"):
        started = time.monotonic()
        v2, f2, counts = repair(v, f, mode, tol)
        left = findings(v2, f2, volume)
        left["where_the_remaining_groups_sit"] = classify_groups(v2, f2, colocated_groups(v2))
        out[mode] = {**counts, "after": left, "seconds": round(time.monotonic() - started, 1)}
    started = time.monotonic()
    mesh = m3.Manifold(m3.Mesh64(v, f.astype(np.uint64))).simplify(tol).to_mesh64()
    v3, f3 = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3], np.asarray(mesh.tri_verts, dtype=np.int64)
    out["manifold"] = {"after": findings(v3, f3, volume), "seconds": round(time.monotonic() - started, 1)}
    cleared = [m for m in ("broad", "float32", "manifold")
               if out[m]["after"]["faces_flat_in_float32"] == 0 and out[m]["after"]["colocated_float32_groups"] == 0
               and out[m]["after"]["closed_and_consistently_wound"]]
    out["a_trial_clears_both_warnings"] = bool(cleared)
    return out


def main(stage, body, out) -> None:
    stage, body, out = Path(stage), Path(body), Path(out)
    report = {"schema": "935-cad-twin-stage-warnings/1", "tol_mm": TOL_MM, "audit": audit(stage, body),
              "trials": trials(body)}
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"audit": report["audit"], "cleared": report["trials"]["a_trial_clears_both_warnings"]}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
