"""Retained torsion/bending verification; stress demand, not CFRP strength.

Uses the published 420-section F0 shell and equivalent QI elastic material.
No geometry, material allowables or ply failure criterion is introduced.
Run with ccx on PATH: python3 strength_audit.py --output work/964-audit
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import torsion as tr  # noqa: E402

TOLERANCE = 1e-4  # numerical linearity only; not a structural safety margin


def read_dat(path):
    """Single-step ASCII NODE PRINT and EL PRINT; reject missing/duplicate data."""
    fields = {name: {} for name in ("u", "rf", "stress", "coord")}
    block = None
    for line in Path(path).read_text().splitlines():
        lower = line.strip().lower()
        if "for set" in lower:
            block = next((value for key, value in (("displacements", "u"), ("forces", "rf"),
                         ("stresses", "stress"), ("global coordinates", "coord")) if lower.startswith(key)), None)
            continue
        if not lower or block is None:
            continue
        words = lower.split()
        if not words[0].isdigit():
            block = None
            continue
        n_ids = 2 if block in ("stress", "coord") else 1
        key = tuple(int(x) for x in words[:n_ids])
        if block == "stress" and words[-1].startswith("_shell_") and words[-1][7:].isdigit():
            words = words[:-1]
        values = [float(x.replace("d", "e")) for x in words[n_ids:]]
        if len(values) != (6 if block == "stress" else 3) or not np.isfinite(values).all():
            raise ValueError(f"invalid {block} row: {key}")
        if key in fields[block]:
            raise ValueError(f"duplicate {block} row: {key}")
        fields[block][key] = values
    if any(not field for field in fields.values()):
        raise ValueError("missing displacement, force, stress or integration-point coordinate block")
    if fields["stress"].keys() != fields["coord"].keys():
        raise ValueError("stress and coordinate integration points differ")
    if fields["u"].keys() != fields["rf"].keys():
        raise ValueError("displacement and force nodes differ")
    return fields


def stress_summary(stress, coord):
    """Six GLOBAL integration-point stresses; von Mises is a display scalar only."""
    a = np.asarray(stress)
    xx, yy, zz, xy, zx, yz = a.T  # .dat order differs from the .frd stress order
    tensor = np.array([[xx, xy, zx], [xy, yy, yz], [zx, yz, zz]]).transpose(2, 0, 1)
    principal = np.linalg.eigvalsh(tensor)
    vm = np.sqrt(((xx - yy)**2 + (yy - zz)**2 + (zz - xx)**2) / 2 + 3 * (xy**2 + yz**2 + zx**2))
    peak = int(np.argmax(vm))
    return {"integration_points": len(a), "max_principal_MPa": float(principal.max()),
            "min_principal_MPa": float(principal.min()), "von_mises_max_MPa": float(vm[peak]),
            "von_mises_p95_MPa": float(np.percentile(vm, 95)),
            "von_mises_peak_xyz_mm": np.asarray(coord)[peak].tolist(),
            "allowable_MPa": None, "reserve_factor": None, "strength_pass": None}


def relative_error(actual, expected):
    return float(np.max(np.abs(actual - expected)) / max(float(np.max(np.abs(expected))), 1e-30))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    import bending as bend
    import torsion_monocoque as tm

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    rep = json.loads(tm.REPORT.read_text())
    profiles = json.loads(tm.bs.PROFILES.read_text())
    s, p, tri = tr.load_shell()
    pts, triangles, kind, *_ = tm.build(s, p, tri, lambda q, st: tm.picogk_bands(q, st, rep, profiles))
    sections, mass = tm.cases(kind, tm.areas(pts, triangles))["monocoque, CFRP layup"]
    rear, fl, fr = tr.supports(s, p)
    arm = float(p[fl, 1].mean() - p[fr, 1].mean())
    torsion_loads = [(fl, 3, np.full(len(fl), tr.FORCE_N / len(fl))),
                     (fr, 3, np.full(len(fr), -tr.FORCE_N / len(fr)))]
    fixed, at, force, *_ = bend.load_case(s, p, tri, rep, profiles)
    cases = {"torsion": ([(rear, 1, 6)], torsion_loads), "bending": (fixed, [(at, 3, force)])}
    doc = {"classification": "prohibited_pending_engineering", "source_revision": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_sha256": {str(x.relative_to(HERE.parent)): sha(x) for x in (
            Path(__file__), HERE / "torsion.py", HERE / "torsion_monocoque.py", HERE / "bending.py",
            HERE / "build_shell.py", tr.SHELL, tm.REPORT, tm.bs.PROFILES)},
        "laminate_sha256": sha(HERE.parents[1] / "fea/laminate.py"),
        "runtime": {"python": sys.version, "numpy": np.__version__, "platform": sys.platform,
                    "solver_image": os.environ.get("MONOCOQUE_SOLVER_IMAGE"),
                    "threads": int(os.environ.get("OMP_NUM_THREADS", "1"))},
        "model": {"sections": 420, "nodes": len(pts), "triangles": len(triangles), "mass_kg": mass,
                  "material": "assumed equivalent isotropic QI carbon, not a layered composite",
                  "target_vehicle_mass_kg": 1200, "target_weight_N": 1200 * 9.80665,
                  "vehicle_mass_applied_as_load": False},
        "tolerance": TOLERANCE, "runs": {}, "checks": {},
        "limits": ["No measured mounting interfaces or 993 fitment validation.",
                   "No ply failure, buckling, fatigue, delamination, crash or manufacturing validation.",
                   "Integration-point peaks are mesh-dependent; this run is not a stress-convergence study.",
                   "RF is external force including CLOAD, not reaction alone; moment balance not qualified.",
                   "Repeated or linearly scaled answers do not establish physical correctness."]}
    for name, (fixed, loads) in cases.items():
        reference = None
        for factor in (1, -1, 2):
            label = f"{name}_{factor:+d}"
            run_dir = a.output / label
            applied = [(nodes, dof, values * factor) for nodes, dof, values in loads]
            print(f"running {label}: {len(pts)} nodes / {len(triangles)} S3", flush=True)
            try:
                tr.run(pts, triangles, sections, fixed, applied, output_dir=run_dir)
            except (SystemExit, OSError) as error:
                doc.update(numerical_checks_passed=False, product_strength_validated=False,
                           failed_run=label, failure=str(error))
                (a.output / "report.json").write_text(json.dumps(doc, indent=2, allow_nan=False) + "\n")
                raise
            data = read_dat(run_dir / "shell.dat")
            nodes = sorted(data["u"])
            ip = sorted(data["stress"])
            if nodes != [(i + 1,) for i in range(len(pts))]:
                raise ValueError("incomplete original-node output")
            if {i for i, _ in ip} != set(range(1, len(triangles) + 1)):
                raise ValueError("incomplete element stress output")
            u = np.array([data["u"][i] for i in nodes])
            rf = np.array([data["rf"][i] for i in nodes])
            stress = np.array([data["stress"][i] for i in ip])
            coord = np.array([data["coord"][i] for i in ip])
            scale = sum(float(np.abs(values).sum()) for _, _, values in applied)
            force_error = float(np.linalg.norm(rf.sum(axis=0)) / scale)
            boundary_error = max(float(np.abs(u[ids, start - 1:min(end, 3)]).max())
                                 for ids, start, end in fixed if start <= 3)
            row = {"factor": factor, "force_balance_relative_error": force_error,
                   "fixed_translation_max_mm": boundary_error, "external_force_sum_N": rf.sum(axis=0).tolist(),
                   "max_displacement_mm": float(np.linalg.norm(u, axis=1).max()),
                   "stress": stress_summary(stress, coord),
                   "files_sha256": {f.name: sha(f) for f in sorted(run_dir.iterdir()) if f.is_file()},
                   "warning_lines": [line.strip() for line in (run_dir / "solver.log").read_text().splitlines()
                                     if "warning" in line.lower() or "error" in line.lower()]}
            if name == "torsion":
                theta = float(np.degrees((u[fl, 2].mean() - u[fr, 2].mean()) / arm))
                row.update(torque_Nm=factor * tr.FORCE_N * arm / 1000,
                           twist_deg=theta, K_Nm_per_deg=factor * tr.FORCE_N * arm / 1000 / theta)
            else:
                delta = -float((u[at, 2] * force).sum() / force.sum())
                row.update(force_N=factor * bend.FORCE_N, deflection_mm=delta,
                           K_N_per_mm=factor * bend.FORCE_N / delta)
            doc["checks"][label + "_force_balance"] = force_error <= TOLERANCE
            doc["checks"][label + "_fixed_translation"] = boundary_error <= 1e-6
            if reference is None:
                reference = (u, stress, ip)
            else:
                if ip != reference[2]:
                    raise ValueError("integration-point identity changed")
                row["displacement_linearity_error"] = relative_error(u, factor * reference[0])
                row["stress_linearity_error"] = relative_error(stress, factor * reference[1])
                doc["checks"][label + "_linearity"] = max(row["displacement_linearity_error"], row["stress_linearity_error"]) <= TOLERANCE
            doc["runs"][label] = row
            (a.output / "report.json").write_text(json.dumps(doc, indent=2, allow_nan=False) + "\n")
            print(label, {k: v for k, v in row.items() if k.startswith("K_")}, row["stress"], flush=True)
    doc["numerical_checks_passed"] = all(doc["checks"].values())
    doc["product_strength_validated"] = False
    (a.output / "report.json").write_text(json.dumps(doc, indent=2, allow_nan=False) + "\n")
    if not doc["numerical_checks_passed"]:
        raise SystemExit("numerical audit failed; inspect retained runs, do not select a favourable repeat")


if __name__ == "__main__":
    main()
