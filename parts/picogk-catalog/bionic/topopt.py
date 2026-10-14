#!/usr/bin/env python3
"""Load-driven (bionic) material layout for a catalogue part: 3D SIMP topology
optimization on a voxel grid.

    python topopt.py <PART_ID>

Reads parts/<id>/source/bionic.json and writes parts/picogk-catalog/out/bionic/
<PART_ID>.density.bin (float32, x fastest) + .density.json (grid, history).
PicoGK (generator "bionic") turns the density into a smooth body, fused with
the exact functional features.

The problem: minimise the summed compliance of the load cases for a volume
fraction of the design domain. Material is penalised (SIMP, p = 3), densities
are filtered (radius rmin, mesh independence), updated by optimality criteria.
Regions:
  design   - where material may grow (union of shapes); everything else is void
  solid    - forced solid (bosses, flanges, seats, functional surfaces)
             "analysis_only": true marks a solid that stiffens the analysis but
             is not printed from the grid (a thin skin or wall that the coarse
             grid would thicken; supply its exact geometry via shaping.base_stl).
             "stiffness_scale" (default 1) scales its modulus, e.g. real wall
             thickness / element size. In the output its elements take the
             largest neighbouring free density, so members reach into the band;
             cut anything beyond the real wall with a "void" shape.
  void     - forced empty (bores, passages, clearances)
  supports - nodes fixed in x, y, z
  loads    - forces in N distributed over the nodes of a region, per case
Shapes: box {min,max}, cyl {a,b,r}, sphere {c,r}, capsule {a,b,r}, stl {path}
(closed STL, inside = region). Every load and support is a stated assumption
in bionic.json: no interface of these parts is measured.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyamg
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.ndimage import convolve

CATALOG = Path(__file__).resolve().parents[1]
ROOT = CATALOG.parents[1]


# --- element stiffness: 8-node hexahedron, unit edge, E = 1 ------------------
def hex8_ke(nu=0.3):
    g = 1 / np.sqrt(3)
    pts = [(a, b, c) for a in (-g, g) for b in (-g, g) for c in (-g, g)]
    nodes = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                      [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float)
    lam, mu = nu / ((1 + nu) * (1 - 2 * nu)), 1 / (2 * (1 + nu))
    D = np.zeros((6, 6))
    D[:3, :3] = lam
    D[np.arange(3), np.arange(3)] += 2 * mu
    D[np.arange(3, 6), np.arange(3, 6)] = mu
    KE = np.zeros((24, 24))
    for xi, eta, zeta in pts:
        dN = np.zeros((3, 8))
        for i, (a, b, c) in enumerate(nodes):
            dN[0, i] = a * (1 + b * eta) * (1 + c * zeta) / 8
            dN[1, i] = b * (1 + a * xi) * (1 + c * zeta) / 8
            dN[2, i] = c * (1 + a * xi) * (1 + b * eta) / 8
        J = dN @ nodes * 0.5                      # element edge 1 => coordinates scaled by 0.5
        dNx = np.linalg.solve(J, dN)
        B = np.zeros((6, 24))
        B[0, 0::3], B[1, 1::3], B[2, 2::3] = dNx[0], dNx[1], dNx[2]
        B[3, 0::3], B[3, 1::3] = dNx[1], dNx[0]
        B[4, 1::3], B[4, 2::3] = dNx[2], dNx[1]
        B[5, 0::3], B[5, 2::3] = dNx[2], dNx[0]
        KE += B.T @ D @ B * np.linalg.det(J)
    return KE


# --- regions -------------------------------------------------------------------
def inside(shape, P):
    k = shape["type"]
    if k == "box":
        lo, hi = np.array(shape["min"]), np.array(shape["max"])
        return np.all((P >= lo) & (P <= hi), axis=1)
    if k in ("cyl", "capsule"):
        a, b, r = np.array(shape["a"]), np.array(shape["b"]), shape["r"]
        ab = b - a
        t = (P - a) @ ab / (ab @ ab)
        tc = np.clip(t, 0, 1)
        d = np.linalg.norm(P - (a + np.outer(tc, ab)), axis=1)
        return (d <= r) & ((t >= 0) & (t <= 1) if k == "cyl" else True)
    if k == "sphere":
        return np.linalg.norm(P - np.array(shape["c"]), axis=1) <= shape["r"]
    if k == "stl":
        import trimesh
        mesh = trimesh.load_mesh(ROOT / shape["path"])
        return mesh.contains(P)
    raise ValueError(f"unknown shape {k}")


def region(shapes, P):
    m = np.zeros(len(P), bool)
    for s in shapes:
        m |= inside(s, P)
    return m


def main(part_id):
    spec_path = ROOT / "parts" / part_id.lower() / "source" / "bionic.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    opt = spec["optimization"]
    h = float(opt["element_mm"])
    lo, hi = np.array(opt["grid_min"], float), np.array(opt["grid_max"], float)
    nel = np.maximum(np.ceil((hi - lo) / h).astype(int), 1)
    nx, ny, nz = nel
    n = nx * ny * nz
    t0 = time.time()

    # element centres, x fastest
    ix, iy, iz = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
    order = lambda a: a.transpose(2, 1, 0).ravel()     # (z, y, x) flatten => x fastest
    C = lo + (np.stack([order(ix), order(iy), order(iz)], 1) + 0.5) * h
    design = region(opt["design"], C)
    solid = region(opt.get("solid", []), C)
    void = region(opt.get("void", []), C)
    stiff = np.ones(n)                               # per-element modulus scale
    analysis_only = np.zeros(n, bool)
    for s in opt.get("solid", []):
        if s.get("analysis_only"):
            inside = region([s], C)
            analysis_only |= inside
            stiff[inside] = float(s.get("stiffness_scale", 1.0))
    analysis_only &= ~region([s for s in opt.get("solid", []) if not s.get("analysis_only")], C)
    active = (design | solid) & ~void

    # nodes and connectivity
    nnx, nny, nnz = nx + 1, ny + 1, nz + 1
    nid = lambda i, j, k: i + nnx * (j + nny * k)
    ex, ey, ez = order(ix), order(iy), order(iz)
    corners = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    en = np.stack([nid(ex + a, ey + b, ez + c) for a, b, c in corners], 1)
    edof = np.repeat(en * 3, 3, axis=1) + np.tile([0, 1, 2], 8)
    edof = edof[active]
    act_idx = np.flatnonzero(active)
    used_nodes = np.unique(en[active])
    NP = lo + np.stack([used_nodes % nnx, (used_nodes // nnx) % nny, used_nodes // (nnx * nny)], 1) * h
    ndof = 3 * nnx * nny * nnz

    KE = hex8_ke() * h                               # 3-D stiffness scales with edge length
    E0, Emin, pen = 1.0, 1e-9, 3.0
    iK = np.repeat(edof, 24, axis=1).ravel()
    jK = np.tile(edof, 24).ravel()

    fixed_nodes = used_nodes[region(opt["supports"], NP)]
    fixed = np.concatenate([fixed_nodes * 3 + d for d in range(3)])
    free = np.setdiff1d(np.unique(edof), fixed)
    cases = []
    for case in opt["load_cases"]:
        F = np.zeros(ndof)
        for load in case["loads"]:
            nodes = used_nodes[region(load["region"], NP)]
            if not len(nodes):
                raise SystemExit(f"load region of {case['name']} touches no active node")
            for d in range(3):
                F[nodes * 3 + d] += load["force_N"][d] / len(nodes)
        cases.append((case["name"], F))
    if not len(fixed_nodes):
        raise SystemExit("supports touch no active node")

    # density filter on the full grid (cone weights), applied on active elements
    r = float(opt.get("filter_radius_mm", 2.5 * h)) / h
    R = int(np.ceil(r))
    g = np.mgrid[-R:R + 1, -R:R + 1, -R:R + 1]
    Wk = np.maximum(0.0, r - np.sqrt((g ** 2).sum(0)))
    act_grid = active.reshape(nz, ny, nx).astype(float)
    Hs = np.maximum(convolve(act_grid, Wk, mode="constant"), 1e-12)

    def filt(x_act):
        full = np.zeros(n)
        full[act_idx] = x_act
        out = convolve(full.reshape(nz, ny, nx), Wk, mode="constant") / Hs
        return out.ravel()[act_idx]

    def filt_t(d_act):                               # adjoint of filt
        full = np.zeros(n)
        full[act_idx] = d_act
        out = convolve(full.reshape(nz, ny, nx) / Hs, Wk, mode="constant")
        return out.ravel()[act_idx]

    # rigid-body modes of the free dofs: the near-nullspace AMG needs for elasticity
    all_nodes = np.arange(nnx * nny * nnz)
    XYZ = lo + np.stack([all_nodes % nnx, (all_nodes // nnx) % nny, all_nodes // (nnx * nny)], 1) * h
    XYZ = XYZ - XYZ.mean(0)
    Bfull = np.zeros((ndof, 6))
    for d in range(3):
        Bfull[d::3, d] = 1.0
    Bfull[0::3, 3], Bfull[1::3, 3] = -XYZ[:, 1], XYZ[:, 0]
    Bfull[1::3, 4], Bfull[2::3, 4] = -XYZ[:, 2], XYZ[:, 1]
    Bfull[0::3, 5], Bfull[2::3, 5] = XYZ[:, 2], -XYZ[:, 0]
    Bfree = Bfull[free]

    # Heaviside projection (eta 0.5) with beta continuation: crisp, organic members
    eta = 0.5

    def project(xt, beta):
        return (np.tanh(beta * eta) + np.tanh(beta * (xt - eta))) / (np.tanh(beta * eta) + np.tanh(beta * (1 - eta)))

    def dproject(xt, beta):
        return beta * (1 - np.tanh(beta * (xt - eta)) ** 2) / (np.tanh(beta * eta) + np.tanh(beta * (1 - eta)))

    na = len(act_idx)
    fixed_solid = solid[act_idx]
    stiff_a = stiff[act_idx]
    stiff_a[~analysis_only[act_idx]] = 1.0
    volfrac = float(opt["volume_fraction"])
    x = np.full(na, volfrac)
    x[fixed_solid] = 1.0
    history = []
    U_prev = {}
    beta, ml = 1.0, None
    iterations = int(opt.get("iterations", 60))
    for it in range(iterations):
        if it and it % 12 == 0 and beta < 8:
            beta *= 2.0
        xt = filt(x)
        xp = project(xt, beta)
        xp[fixed_solid] = 1.0
        Ee = Emin + xp ** pen * (E0 * stiff_a - Emin)
        K = sp.coo_matrix(((KE.ravel()[None, :] * Ee[:, None]).ravel(), (iK, jK)), shape=(ndof, ndof)).tocsr()
        Kf = K[free][:, free]
        # rebuild the AMG hierarchy every iteration: a stale one costs ~10x more CG
        # iterations than its setup (measured on the self-test)
        ml = pyamg.smoothed_aggregation_solver(Kf, B=Bfree, max_coarse=500)
        comp, dc = 0.0, np.zeros(na)
        for name, F in cases:
            U = np.zeros(ndof)
            u, info = spla.cg(Kf, F[free], x0=U_prev.get(name), rtol=float(opt.get("cg_rtol", 1e-3)), maxiter=400, M=ml.aspreconditioner())
            U[free] = u
            U_prev[name] = u
            ue = U[edof]
            ce = np.einsum("ij,jk,ik->i", ue, KE, ue)
            comp += float((Ee * ce).sum())
            dc += -pen * (E0 * stiff_a - Emin) * xp ** (pen - 1) * ce
        dp = dproject(xt, beta)
        dc = filt_t(dc * dp)
        dv = filt_t(dp)
        # optimality criteria (free elements only)
        l1, l2, move = 1e-9, 1e9, 0.2
        target = volfrac * na
        while (l2 - l1) / (l1 + l2) > 1e-4:
            lm = 0.5 * (l1 + l2)
            xn = np.clip(x * np.sqrt(np.maximum(-dc, 0) / (dv * lm)), np.maximum(0, x - move), np.minimum(1, x + move))
            xn[fixed_solid] = 1.0
            l1, l2 = (lm, l2) if xn.sum() > target else (l1, lm)
        change = float(np.abs(xn - x).max())
        x = xn
        history.append({"it": it, "beta": beta, "compliance": round(comp, 6), "volume": round(float(project(filt(x), beta).mean()), 4), "change": round(change, 4)})
        print(f"it {it:3d}  compliance {comp:.4e}  vol {history[-1]['volume']:.3f}  change {change:.3f}", flush=True)
        if beta >= 8 and change < 0.01:
            break

    rho = np.zeros(n, np.float32)
    xp = project(filt(x), beta)
    xp[fixed_solid] = 1.0
    rho[act_idx] = xp
    if analysis_only.any():
        # analysis-only bands are not printed: members continue into them by the
        # largest face-neighbour density outside the band (one pass per element layer)
        g3 = rho.reshape(nz, ny, nx)
        band = analysis_only.reshape(nz, ny, nx)
        g3[band] = 0.0
        for _ in range(int(opt.get("analysis_only_layers", 2))):
            nb = np.zeros_like(g3)
            for ax in range(3):
                for sh in (1, -1):
                    rolled = np.roll(g3, sh, axis=ax)
                    edge = [slice(None)] * 3
                    edge[ax] = 0 if sh == 1 else -1
                    rolled[tuple(edge)] = 0.0
                    nb = np.maximum(nb, rolled)
            g3[band] = np.maximum(g3[band], nb[band])
        rho = g3.ravel()
    out = CATALOG / "out" / "bionic"
    out.mkdir(parents=True, exist_ok=True)
    rho.tofile(out / f"{spec['part_id']}.density.bin")
    meta = {"part_id": spec["part_id"], "origin_mm": lo.tolist(), "element_mm": h, "shape_xyz": [int(nx), int(ny), int(nz)],
            "order": "x fastest, then y, then z", "active_elements": int(na), "free_dofs": int(len(free)),
            "volume_fraction": volfrac, "history": history, "seconds": round(time.time() - t0, 1)}
    (out / f"{spec['part_id']}.density.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"done: {na} elements, {len(free)} dofs, {len(history)} iterations, {meta['seconds']} s")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
