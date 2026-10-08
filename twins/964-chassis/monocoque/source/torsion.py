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


def main():
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 0.8
    e = float(sys.argv[2]) if len(sys.argv) > 2 else 210000.0
    s = np.load(SHELL)
    p, tri = s["points"].astype(float), s["triangles"]
    area = np.linalg.norm(np.cross(p[tri[:, 1]] - p[tri[:, 0]], p[tri[:, 2]] - p[tri[:, 0]]), axis=1) / 2
    tri = tri[area > 1.0]                                  # slivers left by the opening clip
    used = np.unique(tri)
    remap = -np.ones(len(p), int)
    remap[used] = np.arange(len(used))
    p, tri = p[used], remap[tri]
    d, y, z = -p[:, 0], p[:, 1], p[:, 2]
    wd = np.interp(d, s["stations_d"], s["half_width"])
    rear = np.where((d > 2050) & (d < 2450) & (z > 450) & (z < 720) & (np.abs(y) > 0.8 * wd))[0]
    band = (d > -200) & (d < 150) & (z > 470) & (z < 640)
    fl = np.where(band & (y > 0.72 * wd))[0]
    fr = np.where(band & (y < -0.72 * wd))[0]
    arm = float(y[fl].mean() - y[fr].mean())
    with tempfile.TemporaryDirectory() as work:
        inp = pathlib.Path(work, "shell.inp")
        with inp.open("w") as f:
            f.write("*NODE, NSET=NALL\n")
            f.writelines(f"{i + 1}, {q[0]:.3f}, {q[1]:.3f}, {q[2]:.3f}\n" for i, q in enumerate(p))
            f.write("*ELEMENT, TYPE=S3, ELSET=SHELL\n")
            f.writelines(f"{i + 1}, {a + 1}, {b + 1}, {c + 1}\n" for i, (a, b, c) in enumerate(tri))
            f.write(f"*SHELL SECTION, ELSET=SHELL, MATERIAL=MAT\n{t}\n*MATERIAL, NAME=MAT\n*ELASTIC\n{e}, 0.3\n")
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
    k = FORCE_N * arm / 1000.0 / np.degrees(theta)
    np.savez_compressed(OUT, points=p.astype(np.float32), triangles=tri.astype(np.int32),
                        von_mises=vm.astype(np.float32), K=k, thickness_mm=t, E_MPa=e, arm_mm=arm,
                        n_rear=len(rear), n_front=(len(fl), len(fr)))
    print(f"K = {k:.0f} N.m/deg  ({len(p)} nodes, {len(tri)} S3, t = {t} mm, E = {e:.0f} MPa, arm {arm:.0f} mm)")


if __name__ == "__main__":
    main()
