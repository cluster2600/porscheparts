"""Torsion load case on the plate-50-05a shell, CalculiX.

Same load case as the box cell of ../../fea/run_fea.py, on the 911-shaped
shell built by build_shell.py: rear suspension area clamped, equal and
opposite vertical forces at the front wheel-house tops, stiffness
K = torque / twist. Linear S3 shells, uniform thickness and isotropic
material (defaults: steel, 0.8 mm).

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


def load_shell(s=None):
    """Structural shell without the slivers left by the opening clip; s is
    a build_shell.structural() dict, the published shell by default."""
    s = np.load(SHELL) if s is None else s
    p, tri = s["points"].astype(float), s["triangles"]
    area = np.linalg.norm(np.cross(p[tri[:, 1]] - p[tri[:, 0]], p[tri[:, 2]] - p[tri[:, 0]]), axis=1) / 2
    tri = tri[area > 1.0]
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


def solve(p, tri, sections, rear, fl, fr, beams=()):
    """Linear static torsion run. sections: list of (element mask, thickness
    mm, E MPa, Poisson). beams: list of (B32 connectivity (n, 3), section
    diameter mm, E MPa, Poisson), solid circular sections; a tube is passed
    as its equivalent (see tube_equivalent). Returns K (N.m/deg), nodal
    displacements, nodal von Mises (MPa) and the moment arm (mm)."""
    arm = float(p[fl, 1].mean() - p[fr, 1].mean())
    with tempfile.TemporaryDirectory() as work:
        inp = pathlib.Path(work, "shell.inp")
        with inp.open("w") as f:
            f.write("*NODE, NSET=NALL\n")
            f.writelines(f"{i + 1}, {q[0]:.3f}, {q[1]:.3f}, {q[2]:.3f}\n" for i, q in enumerate(p))
            for k, (mask, t, e, nu) in enumerate(sections):
                ids = np.where(mask)[0]
                f.write(f"*ELEMENT, TYPE=S3, ELSET=E{k}\n")
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
            for name, nodes in (("REAR", rear), ("FRL", fl), ("FRR", fr)):
                f.write(f"*NSET, NSET={name}\n")
                f.writelines(", ".join(str(int(x) + 1) for x in nodes[i:i + 8]) + ",\n" for i in range(0, len(nodes), 8))
            f.write("*BOUNDARY\nREAR, 1, 6\n*STEP\n*STATIC, SOLVER=SPOOLES\n")
            f.write(f"*CLOAD\nFRL, 3, {FORCE_N / len(fl):.6f}\nFRR, 3, {-FORCE_N / len(fr):.6f}\n")
            f.write("*NODE FILE, OUTPUT=2D\nU\n*EL FILE, OUTPUT=2D\nS\n*END STEP\n")
        run = subprocess.run(["ccx", "-i", "shell"], cwd=work, capture_output=True, text=True,
                             env=dict(os.environ, OMP_NUM_THREADS="4"))
        if "Job finished" not in run.stdout:
            sys.exit(run.stdout[-800:] + run.stderr[-800:])
        u, vm, block = np.zeros((len(p), 3)), np.zeros(len(p)), None
        for line in pathlib.Path(work, "shell.frd").read_text().splitlines():
            if line.startswith(" -4"):
                block = line.split()[1]
            elif line.startswith(" -3"):
                block = None
            elif line.startswith(" -1") and block in ("DISP", "STRESS"):
                n = int(line[3:13])
                if n > len(p):
                    continue
                vals = [float(line[13 + 12 * k:25 + 12 * k]) for k in range((len(line) - 13) // 12)]
                if block == "DISP":
                    u[n - 1] = vals[:3]
                else:
                    sx, sy, sz, sxy, syz, szx = vals[:6]
                    vm[n - 1] = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (sxy ** 2 + syz ** 2 + szx ** 2))
    theta = (u[fl, 2].mean() - u[fr, 2].mean()) / arm
    return FORCE_N * arm / 1000.0 / np.degrees(theta), u, vm, arm


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
    print(f"K = {k:.0f} N.m/deg  ({len(p)} nodes, {len(tri)} S3, t = {t} mm, E = {e:.0f} MPa, arm {arm:.0f} mm)")


if __name__ == "__main__":
    main()
