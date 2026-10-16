"""Which CalculiX shell element to trust: the Scordelis-Lo roof.

The standard shell benchmark (MacNeal and Harder, 1985): a cylindrical roof,
R 25, L 50, t 0.25, E 4.32e8, Poisson 0, half angle 40 degrees, self weight
90 per unit area, rigid diaphragms at the curved ends, free straight edges.
The vertical deflection at the middle of a free edge is 0.3024. Membrane and
bending both matter, as on a car body.

The roof is triangulated like the car shell (each grid cell split in two)
and solved as S3 and as S6 (mid-side nodes from shell_s6.to_s6, moved
onto the cylinder), at 8x8, 16x16 and 32x32, on one SPOOLES thread.
CalculiX expands S3 into linear wedges, which lock in bending; S6 does not.

The buckling path of shell_s6.run (*BUCKLE, base state left out) is
checked on a simply supported square plate in uniaxial compression,
a 100 mm, t 1 mm, E 70,000 MPa, Poisson 0.3, 16x16 S6: the first two
factors against N_cr = k pi^2 D / a^2 with k = 4 and 6.25 (one and two
half-waves). Result: ../derived/element-check.json.

    python3 element_check.py
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import shell_s6 as s6  # noqa: E402

OUT = HERE.parent / "derived" / "element-check.json"
R, L, T, E, WEIGHT, HALF_DEG, REFERENCE = 25.0, 50.0, 0.25, 4.32e8, 90.0, 40.0, 0.3024
GRIDS = (8, 16, 32)
PLATE_A, PLATE_T, PLATE_E, PLATE_NU, PLATE_N, PLATE_FORCE = 100.0, 1.0, 70000.0, 0.3, 16, 1000.0


def roof(n):
    xs, th = np.linspace(-L / 2, L / 2, n + 1), np.radians(np.linspace(-HALF_DEG, HALF_DEG, n + 1))
    X, A = np.meshgrid(xs, th, indexing="ij")
    p = np.c_[X.ravel(), R * np.sin(A.ravel()), R * np.cos(A.ravel())]
    idx = lambda i, j: i * (n + 1) + j                      # noqa: E731
    tri = [t for i in range(n) for j in range(n)
           for t in ((idx(i, j), idx(i + 1, j), idx(i + 1, j + 1)), (idx(i, j), idx(i + 1, j + 1), idx(i, j + 1)))]
    return p, np.array(tri), idx(n // 2, n)


def deflection(n, shell):
    """Deflection at the middle of a free edge. The self weight goes in as
    a GRAV load, which run() does not take, so the deck is written here."""
    p, tri, target = roof(n)
    if shell == "S6":
        p, tri = s6.to_s6(p, tri)
        r = np.hypot(p[:, 1], p[:, 2])
        p[:, 1:] *= (R / r)[:, None]                          # mid-side nodes on the cylinder
    ends = np.where(np.isclose(np.abs(p[:, 0]), L / 2))[0]
    crown = np.where(np.isclose(p[:, 0], 0) & np.isclose(p[:, 1], 0))[0][0]
    with tempfile.TemporaryDirectory() as work:
        with open(pathlib.Path(work, "roof.inp"), "w") as f:
            f.write("*NODE, NSET=NALL\n" + "".join(f"{k + 1},{q[0]:.9f},{q[1]:.9f},{q[2]:.9f}\n" for k, q in enumerate(p)))
            f.write(f"*ELEMENT, TYPE={shell}, ELSET=E\n" + "".join(f"{k + 1}," + ",".join(str(x + 1) for x in e) + "\n" for k, e in enumerate(tri)))
            f.write(f"*SHELL SECTION, ELSET=E, MATERIAL=M\n{T}\n*MATERIAL, NAME=M\n*ELASTIC\n{E},0.0\n*DENSITY\n{WEIGHT / T}\n")
            f.write("*NSET, NSET=ENDS\n" + "".join(f"{k + 1},\n" for k in ends))
            f.write(f"*BOUNDARY\nENDS,2,3\n{crown + 1},1,1\n*STEP\n*STATIC\n*DLOAD\nE,GRAV,1.,0.,0.,-1.\n"
                    "*NODE FILE, OUTPUT=2D\nU\n*END STEP\n")
        run = subprocess.run(["ccx", "-i", "roof"], cwd=work, capture_output=True, text=True,
                             env=dict(os.environ, OMP_NUM_THREADS=os.environ.get("OMP_NUM_THREADS", "1")))
        if run.returncode != 0 or "Job finished" not in run.stdout:
            sys.exit(run.stdout[-800:])
        block = None
        for line in pathlib.Path(work, "roof.frd").read_text().splitlines():
            if line.startswith(" -4"):
                block = line.split()[1]
            elif line.startswith(" -1") and block == "DISP" and int(line[3:13]) == target + 1:
                return -float(line[37:49])
    sys.exit("target node not in the results")


def plate_buckling():
    """First two buckling loads (N/mm) of the simply supported plate, S6,
    against plate theory, and whether a second solve repeats them."""
    a, n = PLATE_A, PLATE_N
    xs = np.linspace(0, a, n + 1)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    p = np.c_[X.ravel(), Y.ravel(), np.zeros(X.size)]
    idx = lambda i, j: i * (n + 1) + j                      # noqa: E731
    tri = np.array([t for i in range(n) for j in range(n)
                    for t in ((idx(i, j), idx(i + 1, j), idx(i + 1, j + 1)), (idx(i, j), idx(i + 1, j + 1), idx(i, j + 1)))])
    edge = np.where(np.isclose(p[:, 0], 0) | np.isclose(p[:, 0], a) | np.isclose(p[:, 1], 0) | np.isclose(p[:, 1], a))[0]
    q6, _ = s6.to_s6(p, tri)                                 # the loaded edge's corner and mid-side nodes
    right = np.where(np.isclose(q6[:, 0], a))[0]
    right = right[np.argsort(q6[right, 1])]
    w, h = np.zeros(len(right)), a / n
    for k in range(n):                                       # consistent loads of a quadratic edge: 1/6, 4/6, 1/6
        w[2 * k:2 * k + 3] += np.array([1, 4, 1]) * h / 6
    fixed = [(edge, 3, 3), (np.where(np.isclose(p[:, 0], 0))[0], 1, 1), (np.array([idx(0, 0)]), 2, 2)]
    args = (p, tri, [(np.ones(len(tri), bool), PLATE_T, PLATE_E, PLATE_NU)], fixed,
            [(right, 1, -PLATE_FORCE * w / a)])
    f1, _ = s6.run(*args, buckle=4)
    f2, _ = s6.run(*args, buckle=4)
    d = PLATE_E * PLATE_T ** 3 / (12 * (1 - PLATE_NU ** 2))
    theory = [k * np.pi ** 2 * d / a ** 2 for k in (4.0, 6.25)]
    return {"benchmark": "simply supported square plate, uniaxial compression, S6 16x16",
            "a_mm": a, "t_mm": PLATE_T, "E_MPa": PLATE_E, "nu": PLATE_NU,
            "theory_N_per_mm": [round(x, 3) for x in theory],
            "S6_N_per_mm": [round(float(x) * PLATE_FORCE / a, 3) for x in f1[:2]],
            "ratio_to_theory": [round(float(x) * PLATE_FORCE / a / y, 4) for x, y in zip(f1[:2], theory)],
            "repeats": bool(np.allclose(f1, f2, rtol=1e-4))}


def main():
    out = {"benchmark": "Scordelis-Lo roof (MacNeal and Harder 1985)", "reference_deflection": REFERENCE,
           "grids": list(GRIDS), "ratio_to_reference": {}}
    for shell in ("S3", "S6"):
        out["ratio_to_reference"][shell] = [round(deflection(n, shell) / REFERENCE, 3) for n in GRIDS]
        print(shell, out["ratio_to_reference"][shell])
    out["plate_buckling"] = plate_buckling()
    print("plate buckling, S6 / theory:", out["plate_buckling"]["ratio_to_theory"])
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
