"""Which CalculiX shell element to trust: the Scordelis-Lo roof.

The standard shell benchmark (MacNeal and Harder, 1985): a cylindrical roof,
R 25, L 50, t 0.25, E 4.32e8, Poisson 0, half angle 40 degrees, self weight
90 per unit area, rigid diaphragms at the curved ends, free straight edges.
The vertical deflection at the middle of a free edge is 0.3024. Membrane and
bending both matter, as on a car body.

The roof is triangulated like the car shell (each grid cell split in two)
and solved as S3 and as S6 (mid-side nodes from shell_s6.to_s6, moved
onto the cylinder), at 8x8, 16x16 and 32x32, on one SPOOLES thread. CalculiX expands S3 into linear wedges, which lock in bending; S6
does not. Result: ../derived/element-check.json.

    python3 element_check.py
"""
import json
import pathlib
import sys
import os
import subprocess
import tempfile

import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import shell_s6 as s6  # noqa: E402

OUT = HERE.parent / "derived" / "element-check.json"
R, L, T, E, WEIGHT, HALF_DEG, REFERENCE = 25.0, 50.0, 0.25, 4.32e8, 90.0, 40.0, 0.3024
GRIDS = (8, 16, 32)


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


def main():
    out = {"benchmark": "Scordelis-Lo roof (MacNeal and Harder 1985)", "reference_deflection": REFERENCE,
           "grids": list(GRIDS), "ratio_to_reference": {}}
    for shell in ("S3", "S6"):
        out["ratio_to_reference"][shell] = [round(deflection(n, shell) / REFERENCE, 3) for n in GRIDS]
        print(shell, out["ratio_to_reference"][shell])
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
