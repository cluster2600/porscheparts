"""Quadratic S6 shells and linear buckling for the monocoque studies.

CalculiX's S3 (expanded to linear wedges) locks in bending: on the
Scordelis-Lo roof it finds 7-21% of the reference deflection at 8x8 to
32x32, S6 82-100% (element_check.py). Every stiffness of this folder is
therefore solved in S6 since 2026-10-12.

torsion.py, torsion_monocoque.py and bending.py are pinned by SHA-256 in
../derived/strength-audit-20261012.json (the S3 strength audit of
2026-10-12) and stay byte-identical, so the S6 machinery lives here:

- load_shell(): torsion.load_shell() with the needles of the aperture clip
  collapsed first (Q_MIN): S6's expansion inverts on them. At 0.05 a
  0.25 mm high sliver in a 97 degree fold still inverted once its wall
  was 2.5 mm;
- run(): torsion.run() in S6 (mid-side nodes added here, clamp sets
  extended to the mid-side nodes of their edges), or with buckle = n a
  *BUCKLE step returning the n lowest factors and their mode shapes;
- installed(): a context in which torsion.run and torsion.load_shell are
  these, and the repeated solves of torsion_monocoque and bending take
  REPEATS solves. Every study script of this folder runs its main() in it;
  outside it the pinned modules are untouched (S3, as audited).

The outputs of the three pinned scripts are produced in S6 by this
module's command line, which runs their main() inside installed():

    python3 shell_s6.py torsion [thickness_mm] [E_MPa]
    python3 shell_s6.py torsion_monocoque [--quick]
    python3 shell_s6.py bending [--members | --pruned]

Running torsion.py, torsion_monocoque.py or bending.py directly gives
the superseded S3 values.
"""
import contextlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from contextlib import nullcontext

import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[1] / "fea"))          # after source/: fea has its own build_shell
import torsion as tr  # noqa: E402

ELEMENT, Q_MIN = "S6", 0.1
# Solves per value at least, two of which must agree. Three while
# multi-threaded SPOOLES now and then returned a wrong K (+2% to +60% on
# the same input); single-threaded it repeats exactly, and the check stays
# as a guard.
REPEATS = 2
MESH_NOTE_S6 = ("K lists are at the densities of 'meshes', coarsest first, each the value two of K_repeats agree on; "
                "S6 shells, K rises with refinement")


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
    """torsion.load_shell(), with the needles under q_min collapsed."""
    s = np.load(tr.SHELL) if s is None else s
    p, tri = s["points"].astype(float), s["triangles"]
    area = np.linalg.norm(np.cross(p[tri[:, 1]] - p[tri[:, 0]], p[tri[:, 2]] - p[tri[:, 0]]), axis=1) / 2
    tri = tri[area > 1.0]
    if q_min > 0:
        p, tri = collapse_needles(p, tri, q_min)
    used = np.unique(tri)
    remap = -np.ones(len(p), int)
    remap[used] = np.arange(len(used))
    return s, p[used], remap[tri]


def to_s6(p, tri):
    """Quadratic triangles: a mid-side node on every edge, shared between
    neighbours. Returns the points (originals first) and (n, 6) connectivity."""
    e = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    key, inv = np.unique(e, axis=0, return_inverse=True)
    mid = len(p) + inv.reshape(3, len(tri)).T
    return np.vstack([p, 0.5 * (p[key[:, 0]] + p[key[:, 1]])]), np.c_[tri, mid]


def with_midside(nodes, tri6):
    """A node set of the linear mesh with the mid-side nodes of its edges:
    a clamp on the corner nodes alone leaves the edges between them free."""
    inside = np.zeros(max(int(tri6.max()), int(np.max(nodes))) + 1, bool)
    inside[nodes] = True
    extra = [tri6[inside[tri6[:, i]] & inside[tri6[:, j]], m] for i, j, m in ((0, 1, 3), (1, 2, 4), (2, 0, 5))]
    return np.unique(np.concatenate([np.asarray(nodes)] + extra))


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
    if not factors or len(modes) < len(factors) + 1:
        sys.exit(f"buckling output incomplete: {len(factors)} factors, {len(modes)} DISP blocks")
    return np.array(factors), np.array(modes[-len(factors):])


def run(p, tri, sections, fixed, loads, beams=(), equations=(), output_dir=None, shell=ELEMENT, buckle=0,
        print_sections=None):
    """torsion.run(), in S6 shells by default (tri stays linear (n, 3): the
    mid-side nodes are added here and the fixed sets get the mid-side
    nodes of their edges), or with buckle = n a linear buckling step
    returning the n lowest factors of the loads and the mode shapes
    (n, nodes of p, 3). output_dir keeps the run and adds U/RF of every
    node and the integration-point stresses (GLOBAL) to shell.dat, as
    torsion.run() does (print_sections: only those sections' stresses).
    Static: displacements and von Mises (MPa,
    OUTPUT=2D, which leaves out the bending stresses) at the nodes of p.
    One SPOOLES thread unless OMP_NUM_THREADS says otherwise: several
    threads now and then returned a wrong solution on the same input (a K
    up to 60% high, buckling factors 0.6 against 15.5)."""
    n0 = len(p)
    if shell == "S6":
        p, tri = to_s6(p, tri)
        fixed = [(with_midside(nodes, tri), a, b) for nodes, a, b in fixed]
    if output_dir is not None:
        output_dir = pathlib.Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory() if output_dir is None else nullcontext(output_dir) as work:
        with pathlib.Path(work, "shell.inp").open("w") as f:
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
            f.write("*NODE FILE, OUTPUT=2D\nU\n" + ("" if buckle else "*EL FILE, OUTPUT=2D\nS\n"))
            if output_dir is not None and not buckle:
                f.write("*NODE PRINT, NSET=NALL\nU, RF\n")
                for k in range(len(sections)) if print_sections is None else print_sections:
                    f.write(f"*EL PRINT, ELSET=E{k}, GLOBAL=YES\nS, COORD\n")
            f.write("*END STEP\n")
        solver = subprocess.run(["ccx", "-i", "shell"], cwd=work, capture_output=True, text=True,
                                env=dict(os.environ, OMP_NUM_THREADS=os.environ.get("OMP_NUM_THREADS", "1")))
        if output_dir is not None:
            pathlib.Path(work, "solver.log").write_text(solver.stdout + solver.stderr)
        if solver.returncode != 0 or "Job finished" not in solver.stdout:
            sys.exit(solver.stdout[-800:] + solver.stderr[-800:])
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


def _with_n(f, n):
    """f.__defaults__ with its parameter n set to n."""
    names = f.__code__.co_varnames[:f.__code__.co_argcount]
    defaults = list(f.__defaults__)
    defaults[names.index("n") - (len(names) - len(defaults))] = n
    return tuple(defaults)


@contextlib.contextmanager
def installed():
    """torsion.run and torsion.load_shell in S6, REPEATS solves per value
    in torsion_monocoque and bending; everything restored on exit."""
    import bending as bd
    import torsion_monocoque as tm
    saved = (tr.run, tr.load_shell, tm.solve_repeated.__defaults__, bd.solve_repeated.__defaults__)
    try:
        tr.run, tr.load_shell = run, load_shell
        tm.solve_repeated.__defaults__ = _with_n(tm.solve_repeated, REPEATS)
        bd.solve_repeated.__defaults__ = _with_n(bd.solve_repeated, REPEATS)
        yield
    finally:
        tr.run, tr.load_shell, tm.solve_repeated.__defaults__, bd.solve_repeated.__defaults__ = saved


def torsion_main():
    """torsion.main() in S6: the open 0.8 mm steel shell, torsion-snapshot.npz."""
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 0.8
    e = float(sys.argv[2]) if len(sys.argv) > 2 else 210000.0
    s, p, tri = load_shell()
    rear, fl, fr = tr.supports(s, p)
    k, u, vm, arm = tr.solve(p, tri, [(np.ones(len(tri), bool), t, e, 0.3)], rear, fl, fr)
    np.savez_compressed(tr.OUT, points=p.astype(np.float32), triangles=tri.astype(np.int32),
                        von_mises=vm.astype(np.float32), K=k, thickness_mm=t, E_MPa=e, arm_mm=arm,
                        n_rear=len(rear), n_front=(len(fl), len(fr)))
    print(f"K = {k:.0f} N.m/deg  ({len(p)} nodes, {len(tri)} {ELEMENT}, t = {t} mm, E = {e:.0f} MPa, arm {arm:.0f} mm)")


def main():
    studies = ("torsion", "torsion_monocoque", "bending")
    if len(sys.argv) < 2 or sys.argv[1] not in studies:
        sys.exit(f"usage: shell_s6.py {{{','.join(studies)}}} [arguments of that script]")
    name = sys.argv.pop(1)
    sys.argv[0] = f"{name}.py"
    with installed():
        if name == "torsion":
            torsion_main()
        elif name == "torsion_monocoque":
            import torsion_monocoque as tm
            tm.main()
            doc = json.loads(tm.OUT_JSON.read_text())        # its note describes S3
            doc["mesh_note"] = MESH_NOTE_S6
            tm.OUT_JSON.write_text(json.dumps(doc, indent=1) + "\n")
        else:
            import bending as bd
            bd.main()


if __name__ == "__main__":
    main()
