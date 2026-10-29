#!/usr/bin/env python3
"""Audit frozen S6 replays; changing output requests never qualifies the geometry."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

HERE = Path(__file__).resolve().parent
REPLAY = HERE.parent / "s6-replay-20261028"
IMAGE = "sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4"
TOLERANCE = 1e-4  # Numerical screen only; not a vehicle acceptance criterion.


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def expanded_deck(text):
    """Change only the two FRD requests; retain every DAT request unchanged."""
    old = "*NODE FILE, OUTPUT=2D\nU\n*EL FILE, OUTPUT=2D\nS\n"
    new = "*NODE FILE, OUTPUT=3D\nU, RF\n*EL FILE, OUTPUT=3D\nS\n"
    if text.count(old) != 1:
        raise ValueError("Expected exactly one original S6 output block")
    result = text.replace(old, new)
    if result.replace(new, old) != text:
        raise ValueError("Mechanical input changed")
    return result


def read_deck(path):
    """Read the admitted replay's nodes, explicit CLOAD rows and boundary cards."""
    xyz, loads, boundaries = {}, [], []
    block = None
    with Path(path).open() as stream:
        for line in stream:
            line = line.strip()
            if line.startswith("*"):
                block = line.split(",")[0].upper()
                continue
            words = [v.strip() for v in line.split(",") if v.strip()]
            if not words:
                continue
            if block == "*NODE":
                node = int(words[0])
                if node in xyz or len(words) != 4:
                    raise ValueError("Duplicate or malformed node")
                xyz[node] = [float(v) for v in words[1:]]
            elif block == "*CLOAD":
                node, dof = map(int, words[:2])
                if dof not in (1, 2, 3):
                    raise ValueError("Only the admitted translational CLOADs are supported")
                loads.append((node, dof, float(words[2])))
            elif block == "*BOUNDARY":
                boundaries.append(words)
    if not xyz or not loads:
        raise ValueError("Missing coordinates or loads")
    ids = sorted(xyz)
    points = np.array([xyz[n] for n in ids])
    force = np.zeros_like(points)
    lookup = {n: i for i, n in enumerate(ids)}
    for node, dof, value in loads:
        force[lookup[node], dof - 1] += value
    if not np.isfinite(points).all() or not np.isfinite(force).all():
        raise ValueError("Nonfinite deck")
    return ids, points, force, boundaries


def read_dat_vectors(path, expected_ids):
    """Single-step U/RF only; stream past large integration-point blocks."""
    fields = {"u": {}, "rf": {}}
    block = None
    with Path(path).open() as stream:
        for line in stream:
            lower = line.strip().lower()
            if "for set" in lower:
                block = "u" if lower.startswith("displacements") else "rf" if lower.startswith("forces") else None
            elif lower and block:
                words = lower.split()
                if not words[0].isdigit():
                    block = None
                    continue
                node = int(words[0])
                values = [float(v.replace("d", "e")) for v in words[1:]]
                if node in fields[block] or len(values) != 3 or not np.isfinite(values).all():
                    raise ValueError("Duplicate or malformed DAT vector")
                fields[block][node] = values
    if any(set(f) != set(expected_ids) for f in fields.values()):
        raise ValueError("DAT node coverage differs from the admitted input")
    return tuple(np.array([fields[k][n] for n in expected_ids]) for k in ("u", "rf"))


def printed_number(token):
    """Value and half the last printed decimal unit; serialization, not metrology."""
    token = token.strip().lower().replace("d", "e")
    mantissa, exponent = token.split("e")
    decimals = len(mantissa.split(".")[1])
    value = float(token)
    bound = 0.5 * 10.0 ** (int(exponent) - decimals)
    if not np.isfinite(value) or not np.isfinite(bound):
        raise ValueError("Nonfinite printed value")
    return value, bound


def read_frd(path):
    fields = {"coordinates": {}, "FORC": {}}
    block = None
    with Path(path).open() as stream:
        for line in stream:
            if line.startswith("    2C"):
                block = "coordinates"
            elif line.startswith(" -4"):
                block = line.split()[1]
            elif line.startswith(" -3"):
                block = None
            elif line.startswith(" -1") and block in fields:
                node = int(line[3:13])
                if node in fields[block]:
                    raise ValueError("Duplicate FRD node or multiple result steps")
                fields[block][node] = [printed_number(line[13+12*k:25+12*k]) for k in range(3)]
    if not fields["coordinates"] or fields["coordinates"].keys() != fields["FORC"].keys():
        raise ValueError("FRD coordinate/force coverage mismatch")
    ids = sorted(fields["coordinates"])
    xyz = np.array([fields["coordinates"][n] for n in ids])
    rf = np.array([fields["FORC"][n] for n in ids])
    return xyz[:, :, 0], rf[:, :, 0], xyz[:, :, 1], rf[:, :, 1]


def resultants(points, forces, origin, coordinate_bounds=None, force_bounds=None):
    points, forces, origin = (np.asarray(a, dtype=float) for a in (points, forces, origin))
    if (points.ndim != 2 or points.shape[1] != 3 or forces.shape != points.shape
            or origin.shape != (3,) or not all(np.isfinite(a).all() for a in (points, forces, origin))):
        raise ValueError("Invalid vector arrays")
    dp = np.zeros_like(points) if coordinate_bounds is None else np.asarray(coordinate_bounds)
    df = np.zeros_like(forces) if force_bounds is None else np.asarray(force_bounds)
    if any(a.shape != points.shape or not np.isfinite(a).all() or (a < 0).any() for a in (dp, df)):
        raise ValueError("Invalid printing bounds")
    r = points - origin
    moment_bound = []
    for a, b in ((1, 2), (2, 0), (0, 1)):
        bound = abs(r[:, a])*df[:, b] + abs(forces[:, b])*dp[:, a] + dp[:, a]*df[:, b]
        bound += abs(r[:, b])*df[:, a] + abs(forces[:, a])*dp[:, b] + dp[:, b]*df[:, a]
        moment_bound.append(float(bound.sum()))
    return {"force_N": forces.sum(axis=0).tolist(),
            "moment_Nmm": np.cross(r, forces).sum(axis=0).tolist(),
            "force_printing_bound_N": df.sum(axis=0).tolist(),
            "moment_printing_bound_Nmm": moment_bound}


def balance(result, force_scale, moment_scale):
    """The raw residual must meet the fixed tolerance; printing bounds remain diagnostic."""
    if not all(np.isfinite(v) and v > 0 for v in (force_scale, moment_scale)):
        raise ValueError("Positive finite reference scales required")
    out = {}
    for quantity, unit, scale in (("force", "N", force_scale), ("moment", "Nmm", moment_scale)):
        values = np.array(result[f"{quantity}_{unit}"])
        bound = np.array(result[f"{quantity}_printing_bound_{unit}"])
        excess = np.maximum(abs(values) - bound, 0.)
        out[quantity] = {
            "relative_residual_before_printing_bound": float(np.linalg.norm(values)/scale),
            "printing_interval_contains_zero": bool((abs(values) <= bound).all()),
            "relative_unexplained_residual": float(np.linalg.norm(excess)/scale),
            "numerical_screen_passed": bool(np.linalg.norm(values)/scale <= TOLERANCE)}
    return out


def solve(directory):
    command = ["docker", "run", "--rm", "--network", "none", "--cpus=2",
               "--memory=12g", "--memory-swap=12g", "--pids-limit=128", "--read-only",
               "--tmpfs", "/tmp:rw,size=128m", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1",
               "--mount", f"type=bind,src={directory.resolve()},dst=/work", "--workdir", "/work",
               "--entrypoint", "/usr/bin/timeout", IMAGE, "900", "ccx", "-i", "shell"]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=930)
    (directory / "solver.log").write_text(completed.stdout + completed.stderr)
    if completed.returncode or "Job finished" not in completed.stdout:
        raise RuntimeError("Solver failed; retain the private solver log")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--torsion-source", type=Path, required=True)
    ap.add_argument("--bending-source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a new private output directory")
    admitted = []
    for case, source, receipt_dir in (("torsion", args.torsion_source, REPLAY),
                                      ("bending", args.bending_source, REPLAY / "bending")):
        receipt = json.loads((receipt_dir / "result-after-2.json").read_text())
        hashes = receipt["runs"][0].get("file_hashes", receipt["runs"][0].get("files_sha256"))
        for name in ("shell.inp", "shell.dat"):
            if sha(source / "run-1" / name) != hashes[name]:
                raise ValueError(f"Unadmitted retained {case} file: {name}")
        original = (source / "run-1/shell.inp").read_text()
        changed = expanded_deck(original)
        admitted.append((case, source, hashes, changed))
    args.output.mkdir(parents=True, mode=0o700)
    upstream = {
        "verdict": "admitted_for_output_completeness_audit_only",
        "exact_retained_bytes_verified": True, "geometry_and_loads_changed": False,
        "geometry_status": "drawing-derived envelope with modeled sections and synthetic load/support patches",
        "vehicle_interface_admissible": False, "geometry_parameter_sweep_admissible": False,
        "strength_or_manufacturing_admissible": False,
        "blockers": ["No measured XYZ anchors", "Two unresolved P14 model-year families",
                     "Tunnel internal and moving envelopes unknown", "Unqualified isotropic carbon surrogate",
                     "Unconverged mesh and local stress concentrations", "No complete 1200 kg vehicle load case"],
        "numerical_tolerance": TOLERANCE,
        "printing_policy": "Componentwise half-last-digit bounds propagated through r cross RF and reported separately; the raw residual must pass the numerical tolerance",
        "script_sha256": sha(__file__), "solver_image": IMAGE,
        "inputs": {case: {n: hashes[n] for n in ("shell.inp", "shell.dat")} for case, _, hashes, _ in admitted}}
    write_json(args.output / "admissibility.json", upstream)  # Before either solver launch.
    report = {"admissibility_sha256": sha(args.output / "admissibility.json"),
              "versions": {"python": platform.python_version(), "numpy": np.__version__}, "cases": {}}
    for case, source, hashes, changed in admitted:
        target = args.output / case
        target.mkdir()
        (target / "shell.inp").write_text(changed)
        print(f"Running unchanged {case} mechanics with expanded RF output", flush=True)
        solve(target)
        if sha(target / "shell.dat") != hashes["shell.dat"]:
            raise ValueError("DAT differs: original displacements, forces and stresses must remain byte-identical")
        ids, points, loads, boundaries = read_deck(target / "shell.inp")
        u, original_rf = read_dat_vectors(target / "shell.dat", ids)
        origin = points.mean(axis=0)
        force_scale = float(np.linalg.norm(loads, axis=1).sum())
        moment_scale = float(np.linalg.norm(np.cross(points-origin, loads), axis=1).sum())
        p3, f3, dp3, df3 = read_frd(target / "shell.frd")
        old = resultants(points, original_rf, origin)
        new = resultants(p3, f3, origin, dp3, df3)
        screen = balance(new, force_scale, moment_scale)
        row = {"original_nodes": len(ids), "expanded_nodes": len(p3), "origin_mm": origin.tolist(),
               "force_reference_N": force_scale, "moment_reference_Nmm": moment_scale,
               "boundary_cards": boundaries, "dat_byte_identical_to_retained": True,
               "original_node_force_resultants": old, "expanded_resultants": new, "balance": screen,
               "external_work_Nmm": float((loads*u).sum()),
               "energy_correlation_passed": None,
               "files_sha256": {p.name: sha(p) for p in target.iterdir() if p.is_file()}}
        report["cases"][case] = row
        write_json(args.output / f"{case}-audit.json", row)
        print(json.dumps({"case": case, "expanded_nodes": len(p3), "balance": screen}), flush=True)
    for case, source, hashes, _ in admitted:
        for name in ("shell.inp", "shell.dat"):
            if sha(source / "run-1" / name) != hashes[name]:
                raise ValueError("Retained source changed during execution")
    report.update({"source_unchanged": True, "numerical_screens_passed": all(
        item["numerical_screen_passed"] for row in report["cases"].values() for item in row["balance"].values()),
        "physical_validation": False, "mesh_converged": False, "strength_pass": None,
        "manufacturing_authorized": False})
    write_json(args.output / "audit.json", report)
    if not report["numerical_screens_passed"]:
        raise SystemExit("Expanded force/moment screen rejected; retain all outputs")


if __name__ == "__main__":
    main()
