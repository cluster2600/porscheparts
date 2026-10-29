#!/usr/bin/env python3
"""Synthetic 100 x 10 x 2 mm cantilever, not Porsche or qualified CFRP data."""
import argparse
from pathlib import Path
import numpy as np
import audit


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a new private witness directory")
    p = np.array([[x, y, 0.] for x in np.linspace(0, 100, 5) for y in (0., 10.)])
    t = np.array([[2*i, 2*i+2, 2*i+3] for i in range(4)] +
                 [[2*i, 2*i+3, 2*i+1] for i in range(4)])
    edges = np.sort(np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]]), axis=1)
    unique, inv = np.unique(edges, axis=0, return_inverse=True)
    t = np.column_stack([t, len(p) + inv.reshape(3, len(t)).T])
    p = np.vstack([p, p[unique].mean(axis=1)])
    base = '*NODE,NSET=NALL\n' + ''.join(f'{i+1},{x},{y},{z}\n' for i, (x,y,z) in enumerate(p))
    base += '*ELEMENT,TYPE=S6,ELSET=EALL\n' + ''.join(str(i+1)+','+','.join(str(n+1) for n in tri)+'\n' for i,tri in enumerate(t))
    base += '*SHELL SECTION,ELSET=EALL,MATERIAL=M\n2.\n*MATERIAL,NAME=M\n*ELASTIC\n70000.,0.3\n*BOUNDARY\n'
    base += ''.join(f'{i+1},1,6\n' for i in np.flatnonzero(p[:, 0] == 0))
    base += '*STEP\n*STATIC,SOLVER=SPOOLES\n*CLOAD\n9,3,-0.5\n10,3,-0.5\n'
    args.output.mkdir(parents=True, mode=0o700)
    receipt = {"classification": "synthetic_output_completeness_witness",
               "geometry_admissible_for_this_witness": True,
               "physical_validation": False, "solver_image": audit.IMAGE,
               "script_sha256": audit.sha(__file__), "audit_script_sha256": audit.sha(audit.__file__),
               "known_tip_force_N": [0., 0., -1.],
               "known_tip_moment_about_origin_Nmm": [-5., 100., 0.], "cases": {}}
    audit.write_json(args.output / "prepared.json", receipt)
    for output in ("2D", "3D"):
        dst = args.output / output
        dst.mkdir()
        (dst/'shell.inp').write_text(base + f'*NODE FILE,OUTPUT={output}\nU,RF\n*NODE PRINT,NSET=NALL\nU,RF\n*END STEP\n')
        audit.solve(dst)
        xyz, rf, dp, df = audit.read_frd(dst / "shell.frd")
        result = audit.resultants(xyz, rf, [0, 0, 0], dp, df)
        receipt["cases"][output] = {"nodes": len(xyz), "resultants": result,
                                   "balance": audit.balance(result, 1., np.sqrt(10025.)),
                                   "files_sha256": {f.name: audit.sha(f) for f in dst.iterdir() if f.is_file()}}
    a, b = receipt["cases"]["2D"], receipt["cases"]["3D"]
    receipt["dat_identical"] = a["files_sha256"]["shell.dat"] == b["files_sha256"]["shell.dat"]
    receipt["known_missing_2d_moment_demonstrated"] = (
        abs(a["resultants"]["moment_Nmm"][1] - 100.) < 1e-3
        and b["balance"]["moment"]["printing_interval_contains_zero"])
    audit.write_json(args.output / "witness.json", receipt)
    if not receipt["dat_identical"] or not receipt["known_missing_2d_moment_demonstrated"]:
        raise SystemExit("Output completeness witness failed")
    print("Known missing 2D reaction moment recovered in expanded 3D output")


if __name__ == "__main__":
    main()
