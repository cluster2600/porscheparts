#!/usr/bin/env python3
"""Kinematic draping of a woven ply on a mould: the fishnet (pin-jointed net) method.

A balanced woven ply is treated as a net of inextensible yarns pinned at their
crossings: warp and weft keep their length and the ply conforms only by
shearing, the angle between the two yarn families changing from cell to cell.
On a mould that is not developable the shear grows away from the starting
point, and where it reaches the fabric's locking angle the ply wrinkles or
bridges. The method gives, for a starting point and two starting directions:

* where every yarn crossing lands on the mould;
* the shear angle of every cell, which is what limits a woven ply;
* the fibre directions on the mould, and the flat pattern (the net unrolled is
  a regular grid, so the pattern is the set of cells that were placed).

Construction. Two generator yarns leave the starting point along the warp and
weft directions as discrete geodesics: each step lies in the plane of the
previous step and the surface normal, at chord length d. Every other crossing
is the point of the mould at distance d from its two neighbours already placed
(the intersection of two spheres with the surface), taken on the side away
from the diagonal neighbour.

The surface is any function F(p) that is zero on the mould and positive
outside it. A height field z = h(x, y), a sphere, a dome and a tunnel are
provided. Give a mould its fillets: over a sharp crease the net steps across
the corner and lands unevenly, and the shear beyond it is noise.

What it is not. Kinematic draping knows no force: no friction, no bending
stiffness, no blank holder, no gravity. It predicts the shear a pinned net
needs, not whether a real ply reaches it, and not a wrinkle's shape. It applies
to woven or biaxial reinforcement. A unidirectional ply does not shear this
way. It carries no material data: a locking angle is an input that needs its
own source for the actual fabric.

Usage:
  kinematic_draping.py witness --output RESULTS.json
  kinematic_draping.py drape CASE.json --output OUT.json [--nodes NODES.npz] [--plot OUT.png]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

ARC_SAMPLES = 49
BISECTIONS = 60


# --------------------------------------------------------------------------
# surfaces: F(p) = 0 on the mould, positive outside


class Surface:
    def __init__(self, f, description: str):
        self.f, self.description = f, description

    def gradient(self, p: np.ndarray, h: float = 1e-6) -> np.ndarray:
        """Gradient of F by differences: central where both sides exist, one-sided at the edge of a mould."""

        here = self.f(p)
        g = np.empty(3)
        for k, e in enumerate(np.eye(3)):
            ahead, behind = self.f(p + h * e), self.f(p - h * e)
            if np.isfinite(ahead) and np.isfinite(behind):
                g[k] = (ahead - behind) / (2.0 * h)
            elif np.isfinite(ahead):
                g[k] = (ahead - here) / h
            elif np.isfinite(behind):
                g[k] = (here - behind) / h
            else:
                g[k] = float("nan")
        return g

    def normal(self, p: np.ndarray, h: float = 1e-6) -> np.ndarray:
        g = self.gradient(p, h)
        return g / np.linalg.norm(g)

    def project(self, p: np.ndarray) -> np.ndarray:
        """Bring a point onto the surface along the gradient (a few Newton steps)."""

        for _ in range(30):
            value = self.f(p)
            if abs(value) < 1e-12:
                break
            g = self.gradient(p)
            p = p - value * g / float(g @ g)
        return p


def sphere(radius: float) -> Surface:
    return Surface(lambda p: float(np.linalg.norm(p) - radius), f"sphere of radius {radius:g} centred on the origin")


def height_field(h, description: str) -> Surface:
    """Mould z = h(x, y). Outside the domain of h the function returns NaN and the net stops."""

    def f(p):
        with np.errstate(invalid="ignore"):
            return float(p[2] - h(p[0], p[1]))
    return Surface(f, description)


def _filleted_arc(radius: float, fillet: float):
    """Height of a half-circle of the given radius standing on z = 0, with a concave fillet at its foot.

    Returns h(r) for the distance r from the centre line. The fillet is a circle of radius `fillet`
    tangent to the plane and to the arc, so the profile has a continuous slope. Without a fillet the
    arc meets the plane at a right angle, and a net stepping over that crease lands unevenly.
    """

    if fillet <= 0.0:
        return lambda r: math.sqrt(radius * radius - r * r) if r < radius else 0.0
    foot = math.sqrt(radius * radius + 2.0 * radius * fillet)       # where the fillet meets the plane
    touch = foot * radius / (radius + fillet)                        # where it meets the arc

    def h(r):
        if r <= touch:
            return math.sqrt(radius * radius - r * r)
        if r < foot:
            return fillet - math.sqrt(fillet * fillet - (r - foot) ** 2)
        return 0.0
    return h


def tunnel(radius: float, ground: bool = True, fillet: float = 0.0) -> Surface:
    """Half-cylinder of the given radius along x, lying on the plane z = 0 when `ground` is set."""

    profile = _filleted_arc(radius, fillet if ground else 0.0)

    def h(x, y):
        if not ground and abs(y) >= radius:
            return float("nan")
        return profile(abs(y))
    return height_field(h, f"half-cylinder of radius {radius:g} along x" + (" on the plane z = 0" if ground else "")
                        + (f", foot fillet {fillet:g}" if ground and fillet > 0.0 else ""))


def dome(radius: float, fillet: float = 0.0) -> Surface:
    """Hemisphere of the given radius standing on the plane z = 0, with an optional fillet at its foot."""

    profile = _filleted_arc(radius, fillet)
    return height_field(lambda x, y: profile(math.hypot(x, y)),
                        f"hemisphere of radius {radius:g} on the plane z = 0" + (f", foot fillet {fillet:g}" if fillet > 0.0 else ""))


def height_grid(x: np.ndarray, y: np.ndarray, z: np.ndarray, description: str) -> Surface:
    """Mould from heights z[i, j] at x[i], y[j], interpolated bilinearly."""

    def h(px, py):
        if not (x[0] <= px <= x[-1] and y[0] <= py <= y[-1]):
            return float("nan")
        i = min(int(np.searchsorted(x, px, side="right")) - 1, len(x) - 2)
        j = min(int(np.searchsorted(y, py, side="right")) - 1, len(y) - 2)
        a, b = (px - x[i]) / (x[i + 1] - x[i]), (py - y[j]) / (y[j + 1] - y[j])
        return float((1 - a) * (1 - b) * z[i, j] + a * (1 - b) * z[i + 1, j] + (1 - a) * b * z[i, j + 1] + a * b * z[i + 1, j + 1])
    return height_field(h, description)


# --------------------------------------------------------------------------
# the net


def _root_on_arc(point_of, f, lo: float, hi: float):
    """The zero of f(point_of(angle)) nearest to angle 0 in [lo, hi], or None."""

    angles = np.linspace(lo, hi, ARC_SAMPLES)
    values = np.array([f(point_of(a)) for a in angles])
    best = None
    for k in range(len(angles) - 1):
        a, b, fa, fb = angles[k], angles[k + 1], values[k], values[k + 1]
        if not (np.isfinite(fa) and np.isfinite(fb)) or fa * fb > 0.0:
            continue
        for _ in range(BISECTIONS):
            mid = 0.5 * (a + b)
            fm = f(point_of(mid))
            if fa * fm <= 0.0:
                b, fb = mid, fm
            else:
                a, fa = mid, fm
        root = 0.5 * (a + b)
        if best is None or abs(root) < abs(best):
            best = root
    return best


def geodesic_step(surface: Surface, p: np.ndarray, t: np.ndarray, d: float):
    """Next crossing on a generator: chord d from p, in the plane of the direction t and the normal."""

    n = surface.normal(p)
    t = t - (t @ n) * n
    t = t / np.linalg.norm(t)
    point_of = lambda a: p + d * (math.cos(a) * t + math.sin(a) * n)
    angle = _root_on_arc(point_of, surface.f, -0.5 * math.pi, 0.5 * math.pi)
    if angle is None:
        return None, None
    q = point_of(angle)
    return q, (q - p) / d


def corner(surface: Surface, a: np.ndarray, b: np.ndarray, c: np.ndarray, d: float):
    """The crossing at chord d from a and from b, on the mould, away from the diagonal neighbour c."""

    half = 0.5 * np.linalg.norm(b - a)
    if half >= d:
        return None
    e = (b - a) / (2.0 * half)
    m = 0.5 * (a + b)
    rho = math.sqrt(d * d - half * half)
    away = (m - c) - ((m - c) @ e) * e
    if np.linalg.norm(away) < 1e-12:
        return None
    u = away / np.linalg.norm(away)
    v = np.cross(e, u)
    point_of = lambda angle: m + rho * (math.cos(angle) * u + math.sin(angle) * v)
    angle = _root_on_arc(point_of, surface.f, -0.5 * math.pi, 0.5 * math.pi)
    return None if angle is None else point_of(angle)


def drape(surface: Surface, start: np.ndarray, warp: np.ndarray, spacing: float, n_warp: int, n_weft: int) -> np.ndarray:
    """Crossings of a net of (2 n_warp + 1) x (2 n_weft + 1) yarns, NaN where the net could not be placed.

    `start` is projected onto the mould; `warp` is projected onto its tangent plane there, and the weft
    starts at a right angle to it. Index [n_warp + i, n_weft + j] is the crossing i steps along the warp
    and j steps along the weft.
    """

    p0 = surface.project(np.asarray(start, dtype=float))
    n0 = surface.normal(p0)
    t_warp = np.asarray(warp, dtype=float)
    t_warp = t_warp - (t_warp @ n0) * n0
    t_warp /= np.linalg.norm(t_warp)
    t_weft = np.cross(n0, t_warp)
    nodes = np.full((2 * n_warp + 1, 2 * n_weft + 1, 3), np.nan)
    nodes[n_warp, n_weft] = p0
    for axis, direction, count in ((0, t_warp, n_warp), (1, t_weft, n_weft)):
        for sign in (1, -1):
            p, t = p0, sign * direction
            for k in range(1, count + 1):
                p, t = geodesic_step(surface, p, t, spacing)
                if p is None:
                    break
                index = (n_warp + sign * k, n_weft) if axis == 0 else (n_warp, n_weft + sign * k)
                nodes[index] = p
    for si in (1, -1):
        for sj in (1, -1):
            for i in range(1, n_warp + 1):
                for j in range(1, n_weft + 1):
                    a = nodes[n_warp + si * (i - 1), n_weft + sj * j]
                    b = nodes[n_warp + si * i, n_weft + sj * (j - 1)]
                    c = nodes[n_warp + si * (i - 1), n_weft + sj * (j - 1)]
                    if np.isnan(a).any() or np.isnan(b).any() or np.isnan(c).any():
                        continue
                    q = corner(surface, a, b, c, spacing)
                    if q is not None:
                        nodes[n_warp + si * i, n_weft + sj * j] = q
    return nodes


def shear_angles(nodes: np.ndarray) -> np.ndarray:
    """Shear of every cell in radians: pi/2 minus the angle between warp and weft, NaN for a cell not placed.

    The angle is the mean of the two corners that lie on the warp-plus-weft diagonal of the cell, so a
    positive shear closes the cell along that diagonal.
    """

    p00, p10, p01, p11 = nodes[:-1, :-1], nodes[1:, :-1], nodes[:-1, 1:], nodes[1:, 1:]

    def angle(u, v):
        cosine = np.einsum("ijk,ijk->ij", u, v) / (np.linalg.norm(u, axis=2) * np.linalg.norm(v, axis=2))
        return np.arccos(np.clip(cosine, -1.0, 1.0))
    with np.errstate(invalid="ignore"):
        return 0.5 * math.pi - 0.5 * (angle(p10 - p00, p01 - p00) + angle(p01 - p11, p10 - p11))


def summary(surface: Surface, nodes: np.ndarray, spacing: float, thresholds_deg=(20.0, 30.0, 40.0, 50.0)) -> dict:
    gamma = np.degrees(shear_angles(nodes))
    placed = np.isfinite(gamma)
    g = np.abs(gamma[placed])
    if not len(g):                               # not one whole cell fits on the mould from this start
        on_nodes = nodes[np.isfinite(nodes).all(axis=2)]
        return {"crossings_placed": int(len(on_nodes)), "crossings_asked": int(nodes.shape[0] * nodes.shape[1]),
                "cells_placed": 0, "cells_asked": int(gamma.size), "shear_deg": None,
                "share_of_cells_above_deg": {f"{t:g}": None for t in thresholds_deg},
                "flat_pattern_area": 0.0, "area_on_the_mould": 0.0, "largest_fibre_packing_ratio": None,
                "largest_error_of_a_yarn_length": None, "largest_distance_of_a_crossing_from_the_mould": None,
                "note": "no cell was placed: the mould is smaller than one yarn step from this start, or the start is off it"}
    edges = np.concatenate([np.linalg.norm(np.diff(nodes, axis=0), axis=2).ravel(), np.linalg.norm(np.diff(nodes, axis=1), axis=2).ravel()])
    edges = edges[np.isfinite(edges)]
    on_nodes = nodes[np.isfinite(nodes).all(axis=2)]
    off = np.array([abs(surface.f(p)) for p in on_nodes])
    cos_g = np.cos(np.radians(g))
    return {
        "crossings_placed": int(len(on_nodes)), "crossings_asked": int(nodes.shape[0] * nodes.shape[1]),
        "cells_placed": int(placed.sum()), "cells_asked": int(gamma.size),
        "shear_deg": {"median": float(np.median(g)), "p95": float(np.percentile(g, 95)), "largest": float(g.max())},
        "share_of_cells_above_deg": {f"{t:g}": float((g > t).mean()) for t in thresholds_deg},
        "flat_pattern_area": float(placed.sum() * spacing ** 2),
        "area_on_the_mould": float((spacing ** 2 * cos_g).sum()),
        "largest_fibre_packing_ratio": float(1.0 / cos_g.min()),
        "largest_error_of_a_yarn_length": float(np.abs(edges - spacing).max()),
        "largest_distance_of_a_crossing_from_the_mould": float(off.max()),
    }


# --------------------------------------------------------------------------
# reference for the sphere: the Chebyshev net with geodesic generators


def sphere_reference(k_uv: np.ndarray) -> np.ndarray:
    """Shear angle of the continuous net on a sphere, as a function of K u v (u, v arc lengths, K = 1 / R^2).

    The angle w between the yarns of a Chebyshev net obeys w_uv = -K sin w (Servant's equation). With two
    geodesic generators the angle stays at pi/2 along both, so the shear phi = pi/2 - w depends on
    t = K u v alone and solves t phi'' + phi' = cos phi with phi(0) = 0, phi'(0) = 1. Near zero,
    phi = t - t^3 / 18. Integrated here with a fourth-order Runge-Kutta scheme of its own.
    """

    k_uv = np.asarray(k_uv, dtype=float)
    top = float(k_uv.max())
    steps = max(2000, int(top / 1e-4))
    t0 = 1e-4
    ts = np.linspace(t0, max(top, 2 * t0), steps + 1)
    h = ts[1] - ts[0]
    y = np.array([t0 - t0 ** 3 / 18.0, 1.0 - t0 ** 2 / 6.0])
    out = np.empty((steps + 1, 2))
    out[0] = y
    rhs = lambda t, y: np.array([y[1], (math.cos(y[0]) - y[1]) / t])
    for k in range(steps):
        t = ts[k]
        k1 = rhs(t, y)
        k2 = rhs(t + h / 2, y + h / 2 * k1)
        k3 = rhs(t + h / 2, y + h / 2 * k2)
        k4 = rhs(t + h, y + h * k3)
        y = y + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        out[k + 1] = y
    phi = np.interp(k_uv, ts, out[:, 0])
    small = k_uv < t0
    return np.where(small, k_uv - k_uv ** 3 / 18.0, phi)


def witness() -> dict:
    """Checks with answers that do not come from this construction.

    W1 plane: every crossing sits on the square grid, shear zero.
    W2 tunnel without ground, generators along the axis and at 30 degrees to it: a developable mould with
       geodesic generators needs no shear at all.
    W3 sphere of radius 100, generators along two great circles: the shear of every cell against the
       continuous Chebyshev net (sphere_reference) at the cell centre, at two yarn spacings; the error
       must fall with the spacing.
       The net must also be its own mirror image in the two planes of symmetry.
    W4 every yarn segment keeps its length and every crossing lies on the mould, in all cases.
    """

    cases = []

    def add(name, quantity, value, limit):
        cases.append({"witness": name, "quantity": quantity, "value": float(value), "limit": float(limit), "passed": bool(value <= limit)})

    def always(name, surface, nodes, spacing):
        s = summary(surface, nodes, spacing)
        add(name, "largest error of a yarn length, in spacings", s["largest_error_of_a_yarn_length"] / spacing, 1e-9)
        add(name, "largest distance of a crossing from the mould, in spacings", s["largest_distance_of_a_crossing_from_the_mould"] / spacing, 1e-9)
        return s

    plane = height_field(lambda x, y: 0.0, "plane z = 0")
    nodes = drape(plane, np.zeros(3), np.array([math.cos(0.3), math.sin(0.3), 0.0]), 2.0, 12, 9)
    s = always("W1 plane", plane, nodes, 2.0)
    i, j = np.meshgrid(np.arange(-12, 13), np.arange(-9, 10), indexing="ij")
    c, sn = math.cos(0.3), math.sin(0.3)
    exact = np.stack([2.0 * (i * c - j * sn), 2.0 * (i * sn + j * c), np.zeros(i.shape)], axis=2)
    add("W1 plane", "largest distance of a crossing from the square grid, in spacings", np.abs(nodes - exact).max() / 2.0, 1e-9)
    add("W1 plane", "largest shear, degrees", s["shear_deg"]["largest"], 1e-6)

    for label, angle in (("along the axis", 0.0), ("at 30 degrees to the axis", math.radians(30.0))):
        surface = tunnel(100.0, ground=False)
        nodes = drape(surface, np.array([0.0, 0.0, 100.0]), np.array([math.cos(angle), math.sin(angle), 0.0]), 4.0, 14, 14)
        s = always(f"W2 tunnel, generators {label}", surface, nodes, 4.0)
        add(f"W2 tunnel, generators {label}", "largest shear, degrees", s["shear_deg"]["largest"], 0.05)
        add(f"W2 tunnel, generators {label}", "share of the net not placed", 1.0 - s["crossings_placed"] / s["crossings_asked"], 0.0)

    errors = {}
    for spacing, n in ((4.0, 22), (2.0, 44)):
        surface = sphere(100.0)
        nodes = drape(surface, np.array([0.0, 0.0, 100.0]), np.array([1.0, 0.0, 0.0]), spacing, n, n)
        always(f"W3 sphere, spacing {spacing:g}", surface, nodes, spacing)
        gamma = shear_angles(nodes)[n:, n:]                              # the quadrant of positive warp and weft
        centre = (np.arange(n) + 0.5) * spacing
        reference = sphere_reference(np.outer(centre, centre) / 100.0 ** 2)
        placed = np.isfinite(gamma)
        errors[spacing] = float(np.degrees(np.abs(gamma - reference)[placed]).max())
        add(f"W3 sphere, spacing {spacing:g}", "largest shear, degrees (information: limit is the right angle)",
            float(np.degrees(np.nanmax(gamma))), 90.0)
        add(f"W3 sphere, spacing {spacing:g}", "largest difference from the continuous net, degrees", errors[spacing], 0.5 if spacing == 4.0 else 0.15)
        # the sphere and the generators are symmetric about the planes x = 0 and y = 0: so is the net
        mirror = max(np.abs(nodes[::-1] * np.array([-1.0, 1.0, 1.0]) - nodes).max(), np.abs(nodes[:, ::-1] * np.array([1.0, -1.0, 1.0]) - nodes).max())
        add(f"W3 sphere, spacing {spacing:g}", "largest distance between a crossing and its mirror image, in spacings", float(mirror / spacing), 1e-9)
    add("W3 sphere", "error at spacing 2 over error at spacing 4", errors[2.0] / errors[4.0], 0.5)
    series = sphere_reference(np.array([0.05]))[0]
    add("reference", "difference between the integrated reference and its series at K u v = 0.05, radians", abs(series - (0.05 - 0.05 ** 3 / 18.0)), 1e-8)
    return {"schema": "kinematic-draping-witness/1", "date": time.strftime("%Y-%m-%d"),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "numpy": np.__version__, "passed": all(c["passed"] for c in cases), "cases": cases,
            "sphere_error_deg_by_spacing": {f"{k:g}": v for k, v in errors.items()}}


# --------------------------------------------------------------------------
# command line


def surface_from(case: dict, folder: Path) -> Surface:
    kind = case["mould"]["kind"]
    if kind == "sphere":
        return sphere(case["mould"]["radius"])
    if kind == "dome":
        return dome(case["mould"]["radius"], case["mould"].get("fillet", 0.0))
    if kind == "tunnel":
        return tunnel(case["mould"]["radius"], case["mould"].get("ground", True), case["mould"].get("fillet", 0.0))
    if kind == "height_grid":
        data = np.load(folder / case["mould"]["file"])
        return height_grid(data["x"], data["y"], data["z"], f"height grid {case['mould']['file']}")
    raise SystemExit(f"unknown mould kind: {kind}")


def plot(nodes: np.ndarray, spacing: float, title: str, out: Path, top_deg: float | None = None) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    gamma = np.abs(np.degrees(shear_angles(nodes)))
    top = top_deg or float(max(10.0, np.ceil(np.nanmax(gamma) / 10.0) * 10.0))
    cmap = plt.get_cmap("viridis")
    fig = plt.figure(figsize=(13, 5.6))
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    quads, colours = [], []
    for i in range(gamma.shape[0]):
        for j in range(gamma.shape[1]):
            if np.isfinite(gamma[i, j]):
                quads.append([nodes[i, j], nodes[i + 1, j], nodes[i + 1, j + 1], nodes[i, j + 1]])
                colours.append(cmap(min(gamma[i, j] / top, 1.0)))
    ax.add_collection3d(Poly3DCollection(quads, facecolors=colours, edgecolors=(0, 0, 0, 0.25), linewidths=0.2))
    finite = nodes[np.isfinite(nodes).all(axis=2)]
    lo, hi = finite.min(axis=0), finite.max(axis=0)
    size = np.maximum(hi - lo, 1e-9)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(tuple(size))
    ax.set_zticks([lo[2], hi[2]])
    ax.view_init(elev=38, azim=-55)
    ax.set_title("the net on the mould", fontsize=10)
    ax2 = fig.add_subplot(1, 2, 2)
    n_warp, n_weft = (nodes.shape[0] - 1) // 2, (nodes.shape[1] - 1) // 2
    extent = (-n_warp * spacing, n_warp * spacing, -n_weft * spacing, n_weft * spacing)
    image = ax2.imshow(np.ma.masked_invalid(gamma).T, origin="lower", extent=extent, cmap=cmap, vmin=0.0, vmax=top, aspect="equal")
    ax2.set_xlabel("along the warp, flat pattern")
    ax2.set_ylabel("along the weft, flat pattern")
    ax2.set_title("shear of each cell on the flat pattern (white: not placed)", fontsize=10)
    fig.colorbar(image, ax=ax2, label="shear angle, degrees")
    fig.suptitle(title, fontsize=11)
    fig.text(0.5, 0.012, "Kinematic draping: the shear a pinned net needs. No force, no friction, no fabric data. Not a wrinkle prediction.",
             ha="center", fontsize=9, color="#444444")
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(out, dpi=110)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("witness")
    w.add_argument("--output", required=True)
    d = sub.add_parser("drape")
    d.add_argument("case")
    d.add_argument("--output", required=True)
    d.add_argument("--nodes")
    d.add_argument("--plot")
    args = parser.parse_args()
    if args.command == "witness":
        report = witness()
        Path(args.output).write_text(json.dumps(report, indent=1) + "\n")
        print(json.dumps({"passed": report["passed"], "failed": [c for c in report["cases"] if not c["passed"]],
                          "sphere_error_deg_by_spacing": report["sphere_error_deg_by_spacing"]}))
        raise SystemExit(0 if report["passed"] else 1)
    case_path = Path(args.case)
    case = json.loads(case_path.read_text())
    surface = surface_from(case, case_path.parent)
    ply = case["ply"]
    angle = math.radians(ply["warp_angle_deg"])
    nodes = drape(surface, np.array(ply["start"], dtype=float), np.array([math.cos(angle), math.sin(angle), 0.0]),
                  ply["yarn_spacing"], ply["yarns_each_way_along_warp"], ply["yarns_each_way_along_weft"])
    report = {"schema": "kinematic-draping/1", "date": time.strftime("%Y-%m-%d"), "case": case_path.name,
              "case_sha256": hashlib.sha256(case_path.read_bytes()).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "mould": surface.description, "units": case.get("units", "the caller's"),
              "method": "fishnet: geodesic generators from the start point, then sphere-sphere-surface intersections",
              **summary(surface, nodes, ply["yarn_spacing"], tuple(case.get("shear_thresholds_deg", (20.0, 30.0, 40.0, 50.0)))),
              "claims": "the shear a pinned net needs on this surface. No fabric, no locking angle and no forming process are "
                        "modelled; a share above a threshold is information, not a verdict"}
    Path(args.output).write_text(json.dumps(report, indent=1) + "\n")
    if args.nodes:
        np.savez_compressed(args.nodes, nodes=nodes, shear_rad=shear_angles(nodes))
    if args.plot and report["cells_placed"]:
        plot(nodes, ply["yarn_spacing"], f"{case.get('title', case_path.stem)}: {surface.description}", Path(args.plot))
    print(json.dumps({k: report[k] for k in ("crossings_placed", "crossings_asked", "shear_deg", "share_of_cells_above_deg")}))


if __name__ == "__main__":
    main()
