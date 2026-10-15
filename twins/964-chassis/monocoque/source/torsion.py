"""Torsion load case on the plate-50-05a shell, CalculiX.

Same load case as the box cell of ../../fea/run_fea.py, on the 911-shaped
shell built by build_shell.py: rear suspension area clamped, equal and
opposite vertical forces at the front wheel-house tops, stiffness
K = torque / twist. Quadratic S6 shells (see ELEMENT), uniform thickness
and isotropic material (defaults: steel, 0.8 mm).

The shell has open door and window apertures, no glass, no sill box section
and no wheel houses in the calculation (they are not connected node to node).
K is therefore the stiffness of this surface model under this load, not of a
964 body shell; the stress field shows where an open 911 shell carries
torsion. Both go to ../derived/torsion-snapshot.npz for the banner and the
figures.

    python3 torsion.py [thickness_mm] [E_MPa]
"""
import os
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

HERE = pathlib.Path(__file__).parent
SHELL = HERE.parent / "derived" / "monocoque-shell-structural.npz"
OUT = HERE.parent / "derived" / "torsion-snapshot.npz"
FORCE_N = 1000.0
# Quadratic shells. CalculiX's S3 (expanded to linear wedges) locks in
# bending: on the Scordelis-Lo roof it finds 7-21% of the reference
# deflection at 8x8 to 32x32, S6 82-100% (element_check.py). S6 needs the
# needles of the aperture clip collapsed first (Q_MIN): at 0.05 a 0.25 mm
# high sliver in a 97 degree fold still inverted once its wall was 2.5 mm.
ELEMENT, Q_MIN = "S6", 0.1


def quality(p, tri):
    """Triangle shape quality, 1 for equilateral, 0 for degenerate, and
    the shortest edge's two corners."""
    e = [p[tri[:, (k + 1) % 3]] - p[tri[:, k]] for k in range(3)]
    sq = np.c_[[(v ** 2).sum(1) for v in e]].T
    area = np.linalg.norm(np.cross(e[0], -e[2]), axis=1) / 2
    k = sq.argmin(1)
    short = np.c_[tri[np.arange(len(tri)), k], tri[np.arange(len(tri)), (k + 1) % 3]]
    return 4 * np.sqrt(3) * area / np.maximum(sq.sum(1), 1e-12), short


def collapse_needles(p, tri, q_min, passes=10):
    """Merge the two corners of the shortest edge of every triangle under
    q_min (at their midpoint) and drop what degenerates. The clip of the
    apertures leaves needles that S3 tolerates and S6 does not (its
    expansion inverts on them)."""
    p = p.copy()
    for _ in range(passes):
        q, short = quality(p, tri)
        bad = np.where(q < q_min)[0]
        if not len(bad):
            break
        to = np.arange(len(p))
        taken = np.zeros(len(p), bool)
        for i, j in short[bad[np.argsort(q[bad])]]:
            if taken[i] or taken[j]:
                continue
            taken[i] = taken[j] = True
            p[i] = 0.5 * (p[i] + p[j])
            to[j] = i
        tri = to[tri]
        tri = tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 2] != tri[:, 0])]
        _, first = np.unique(np.sort(tri, axis=1), axis=0, return_index=True)
        tri = tri[np.sort(first)]
    return p, tri


def load_shell(s=None, q_min=Q_MIN):
    """Structural shell without the slivers left by the opening clip; s is
    a build_shell.structural() dict, the published shell by default.
    Needles under q_min are collapsed (S6 inverts on them)."""
    s = np.load(SHELL) if s is None else s
    p, tri = s["points"].astype(float), s["triangles"]
    area = np.linalg.norm(np.cross(p[tri[:, 1]] - p[tri[:, 0]], p[tri[:, 2]] - p[tri[:, 0]]), axis=1) / 2
    tri = tri[area > 1.0]
    if q_min > 0:
        p, tri = collapse_needles(p, tri, q_min)
    used = np.unique(tri)
    remap = -np.ones(len(p), int)
    remap[used] = np.arange(len(used))
    return s, p[used], remap[tri]


def supports(s, p):
    """Node sets of the load case: rear clamp, front left and right loads."""
    d, y, z = -p[:, 0], p[:, 1], p[:, 2]
    wd = np.interp(d, s["stations_d"], s["half_width"])
    rear = np.where((d > 2050) & (d < 2450) & (z > 450) & (z < 720) & (np.abs(y) > 0.8 * wd))[0]
    band = (d > -200) & (d < 150) & (z > 470) & (z < 640)
    return rear, np.where(band & (y > 0.72 * wd))[0], np.where(band & (y < -0.72 * wd))[0]


def solve(p, tri, sections, rear, fl, fr, beams=(), equations=()):
    """Linear static torsion run: rear clamped, +/-FORCE_N vertical at the
    front left and right node sets. sections, beams, equations: see run().
    Returns K (N.m/deg), nodal displacements, nodal von Mises (MPa) and the
    moment arm (mm)."""
    arm = float(p[fl, 1].mean() - p[fr, 1].mean())
    u, vm = run(p, tri, sections, [(rear, 1, 6)],
                [(fl, 3, np.full(len(fl), FORCE_N / len(fl))), (fr, 3, np.full(len(fr), -FORCE_N / len(fr)))],
                beams=beams, equations=equations)
    theta = (u[fl, 2].mean() - u[fr, 2].mean()) / arm
    return FORCE_N * arm / 1000.0 / np.degrees(theta), u, vm, arm


def run(p, tri, sections, fixed, loads, beams=(), equations=(), shell=ELEMENT, buckle=0):
    """Linear static CalculiX run, or with buckle = n the n lowest linear
    buckling factors of the loads. sections: list of (element mask,
    thickness mm, E MPa, Poisson). fixed: list of (nodes, first DOF, last
    DOF) held at zero. loads: list of (nodes, DOF, force per node N). beams: list of
    (B32 connectivity (n, 3), section diameter mm, E MPa, Poisson), solid
    circular sections; a tube is passed as its equivalent (see
    tube_equivalent). equations: list of (node, [(node, weight), ...])
    tying the first node's translations to the weighted sum of the others'
    (a bond). tri is linear (n, 3); with shell S6 it gets mid-side nodes
    here, and the fixed sets the mid-side nodes of their edges. Returns
    displacements and von Mises (MPa) at the nodes of p; with buckle, the
    buckling factors and the mode shapes (n, nodes, 3) instead."""
    n0 = len(p)
    if shell == "S6":
        p, tri = to_s6(p, tri)
        fixed = [(with_midside(nodes, tri), a, b) for nodes, a, b in fixed]
    with tempfile.TemporaryDirectory() as work:
        inp = pathlib.Path(work, "shell.inp")
        with inp.open("w") as f:
            f.write("*NODE, NSET=NALL\n")
            f.writelines(f"{i + 1}, {q[0]:.3f}, {q[1]:.3f}, {q[2]:.3f}\n" for i, q in enumerate(p))
            for k, (mask, t, e, nu) in enumerate(sections):
                ids = np.where(mask)[0]
                f.write(f"*ELEMENT, TYPE={shell}, ELSET=E{k}\n")
                f.writelines(f"{i + 1}, " + ", ".join(str(int(n) + 1) for n in row) + "\n" for i, row in zip(ids, tri[ids]))
                f.write(f"*SHELL SECTION, ELSET=E{k}, MATERIAL=M{k}\n{t}\n*MATERIAL, NAME=M{k}\n*ELASTIC\n{e}, {nu}\n")
            for k, (el, dia, e, nu) in enumerate(beams):
                axis = p[el[:, 2]] - p[el[:, 0]]
                ref = np.argmin(np.abs(axis) / np.linalg.norm(axis, axis=1, keepdims=True), axis=1)
                for j in range(3):                   # section 1-direction: the axis least aligned with the beam
                    ids = np.where(ref == j)[0]
                    if not len(ids):
                        continue
                    f.write(f"*ELEMENT, TYPE=B32, ELSET=B{k}{j}\n")
                    f.writelines(f"{len(tri) + 1 + sum(len(b[0]) for b in beams[:k]) + i}, "
                                 + ", ".join(str(int(n) + 1) for n in el[i]) + "\n" for i in ids)
                    f.write(f"*BEAM SECTION, ELSET=B{k}{j}, MATERIAL=BM{k}, SECTION=CIRC\n{dia}, {dia}\n"
                            + ", ".join("1." if a == j else "0." for a in range(3)) + "\n")
                f.write(f"*MATERIAL, NAME=BM{k}\n*ELASTIC\n{e}, {nu}\n")
            if len(equations):
                f.write("*EQUATION\n")
                for n, terms in equations:
                    for dof in (1, 2, 3):
                        f.write(f"{1 + len(terms)}\n{int(n) + 1},{dof},1."
                                + "".join(f",{int(m) + 1},{dof},{-w:.6f}" for m, w in terms) + "\n")
            for k, (nodes, *_) in enumerate(fixed):
                f.write(f"*NSET, NSET=FIX{k}\n")
                f.writelines(", ".join(str(int(x) + 1) for x in nodes[i:i + 8]) + ",\n" for i in range(0, len(nodes), 8))
            f.write("*BOUNDARY\n" + "".join(f"FIX{k}, {a}, {b}\n" for k, (_, a, b) in enumerate(fixed)))
            f.write("*STEP\n" + (f"*BUCKLE, SOLVER=SPOOLES\n{buckle}\n" if buckle else "*STATIC, SOLVER=SPOOLES\n") + "*CLOAD\n")
            for nodes, dof, force in loads:
                f.writelines(f"{int(n) + 1}, {dof}, {v:.6f}\n" for n, v in zip(nodes, np.broadcast_to(force, len(nodes))))
            f.write("*NODE FILE, OUTPUT=2D\nU\n" + ("" if buckle else "*EL FILE, OUTPUT=2D\nS\n") + "*END STEP\n")
        # One thread: multi-threaded SPOOLES now and then returns a wrong
        # solution on the same input (a K up to 60% high, spurious buckling
        # factors 0.6 against 15.5); single-threaded it repeats exactly, for
        # about 25% more time (2026-10-12).
        run = subprocess.run(["ccx", "-i", "shell"], cwd=work, capture_output=True, text=True,
                             env=dict(os.environ, OMP_NUM_THREADS="1"))
        if "Job finished" not in run.stdout:
            sys.exit(run.stdout[-800:] + run.stderr[-800:])
        if buckle:
            return buckling_results(work, n0)
        u, vm, block = np.zeros((n0, 3)), np.zeros(n0), None
        for line in pathlib.Path(work, "shell.frd").read_text().splitlines():
            if line.startswith(" -4"):
                block = line.split()[1]
            elif line.startswith(" -3"):
                block = None
            elif line.startswith(" -1") and block in ("DISP", "STRESS"):
                n = int(line[3:13])
                if n > n0:
                    continue
                vals = [float(line[13 + 12 * k:25 + 12 * k]) for k in range((len(line) - 13) // 12)]
                if block == "DISP":
                    u[n - 1] = vals[:3]
                else:
                    sx, sy, sz, sxy, syz, szx = vals[:6]
                    vm[n - 1] = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (sxy ** 2 + syz ** 2 + szx ** 2))
    return u, vm


def buckling_results(work, n0):
    """Buckling factors from shell.dat, mode shapes from shell.frd (whose
    first DISP block is the static base state, not a mode)."""
    dat = pathlib.Path(work, "shell.dat").read_text().split("BUCKLING")[-1]
    factors = [float(m.split()[1]) for m in dat.splitlines() if len(m.split()) == 2 and m.split()[0].isdigit()]
    modes, u = [], None
    for line in pathlib.Path(work, "shell.frd").read_text().splitlines():
        if line.startswith(" -4"):
            u = np.zeros((n0, 3)) if line.split()[1] == "DISP" else None
            if u is not None:
                modes.append(u)
        elif line.startswith(" -1") and u is not None:
            n = int(line[3:13])
            if n <= n0:
                u[n - 1] = [float(line[13 + 12 * k:25 + 12 * k]) for k in range(3)]
    return np.array(factors), np.array(modes[-len(factors):])


def to_s6(p, tri):
    """Quadratic triangles: a mid-side node on every edge, shared between
    neighbours. Returns the points (originals first) and (n, 6) connectivity."""
    e = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    key, inv = np.unique(e, axis=0, return_inverse=True)
    mid = len(p) + inv.reshape(3, len(tri)).T
    return np.vstack([p, 0.5 * (p[key[:, 0]] + p[key[:, 1]])]), np.c_[tri, mid]


def with_midside(nodes, tri6):
    """A node set of the S3 mesh with the mid-side nodes of its edges: a
    clamp on the corner nodes alone leaves the edges between them free."""
    inside = np.zeros(max(int(tri6.max()), int(np.max(nodes))) + 1, bool)
    inside[nodes] = True
    extra = [tri6[inside[tri6[:, i]] & inside[tri6[:, j]], m] for i, j, m in ((0, 1, 3), (1, 2, 4), (2, 0, 5))]
    return np.unique(np.concatenate([np.asarray(nodes)] + extra))


def tube_equivalent(od, wall, e):
    """Solid circular section with the tube's area, bending and torsion
    stiffness: diameter and modulus to pass to solve(). This CalculiX reads
    CIRC dimensions as diameters (checked on a cantilever: 2.175 mm against
    2.177 analytic)."""
    ro, ri = od / 2.0, od / 2.0 - wall
    return 2.0 * float(np.sqrt(ro ** 2 + ri ** 2)), e * (ro ** 2 - ri ** 2) / (ro ** 2 + ri ** 2)


def main():
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 0.8
    e = float(sys.argv[2]) if len(sys.argv) > 2 else 210000.0
    s, p, tri = load_shell()
    rear, fl, fr = supports(s, p)
    k, u, vm, arm = solve(p, tri, [(np.ones(len(tri), bool), t, e, 0.3)], rear, fl, fr)
    np.savez_compressed(OUT, points=p.astype(np.float32), triangles=tri.astype(np.int32),
                        von_mises=vm.astype(np.float32), K=k, thickness_mm=t, E_MPa=e, arm_mm=arm,
                        n_rear=len(rear), n_front=(len(fl), len(fr)))
    print(f"K = {k:.0f} N.m/deg  ({len(p)} nodes, {len(tri)} {ELEMENT}, t = {t} mm, E = {e:.0f} MPa, arm {arm:.0f} mm)")


if __name__ == "__main__":
    main()
