"""Exercise semantic atlas refusals and actual native-file/units refusals."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, output, log, expected):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    log.write_text(result.stdout + result.stderr)
    if result.returncode == 0 or output.exists() or expected not in result.stderr:
        raise AssertionError("Expected refusal was not obtained: " + expected)
    return {"refused": True, "reason": expected, "no_success_result": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("arrays", "parent", "plan", "atlas", "verification", "native", "source", "inspector", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    expected = {
        "original_membership": "Frozen original membership changed",
        "boundary_cycle": "Stored domain boundary is not one simple source cycle",
        "growth_seed": "Minimum-original-ID domain seed changed",
        "source_edge_cut": "Cuts are not the exact existing source edges",
        "admission_flag": "Atlas aggregate or admission changed",
    }
    checks = {}
    for case, reason in expected.items():
        directory = a.output / case
        shutil.copytree(a.atlas, directory)
        report_path = directory / "atlas.json"
        report = json.loads(report_path.read_text())
        path = directory / "region-0-atlas.npz"
        if case == "admission_flag":
            report["regions"][0]["native_export_admitted"] = True
        else:
            with np.load(path, allow_pickle=False) as d:
                data = {k: d[k].copy() for k in d.files}
            if case == "original_membership":
                data["original_face_ids"][0] = data["original_face_ids"][1]
            elif case == "boundary_cycle":
                data["boundary_vertices"][1] = data["boundary_vertices"][0]
            elif case == "growth_seed":
                assert data["growth_offsets"][1] >= 2
                data["growth_trace"][:2] = data["growth_trace"][:2][::-1]
            else:
                data["cut_edges"][0, 0] += 1
            np.savez_compressed(path, **data)
            report["regions"][0]["private_atlas_sha256"] = sha(path)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        output = directory / "forbidden-success.json"
        argv = [sys.executable, "-B", str(a.source / "verify_atlas.py"),
                "--arrays", str(a.arrays), "--parent", str(a.parent), "--plan", str(a.plan),
                "--atlas", str(directory), "--output", str(output)]
        checks[case] = run(argv, output, directory / "refusal.log", reason)
    for case, reason in (("native_units", "Native BREP units sidecar mismatch"),
                         ("wrong_actual_native", "Global original vertex sharing was changed")):
        directory = a.output / case
        directory.mkdir()
        for path in a.native.iterdir():
            if path.is_file():
                (directory / path.name).symlink_to(path.resolve())
        if case == "native_units":
            target = directory / "shared-edge-fixture.units.json"
            target.unlink()
            units = json.loads((a.native / target.name).read_text())
            units["units"] = "inch"
            target.write_text(json.dumps(units))
        else:
            for suffix in ("brep", "units.json"):
                target = directory / f"observed-chamber-region-0.{suffix}"
                target.unlink()
                shutil.copy2(a.native / f"shared-edge-fixture.{suffix}", target)
        output_dir = directory / "inspection"
        argv = [sys.executable, "-B", str(a.source / "native_reference.py"), "verify",
                "--format", "brep", "--arrays", str(a.arrays), "--plan", str(a.plan),
                "--atlas", str(a.atlas), "--verification", str(a.verification),
                "--helper", str(a.inspector), "--steps", str(directory), "--output", str(output_dir)]
        checks[case] = run(argv, output_dir / "result.json", directory / "refusal.log", reason)
    (a.output / "controls.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks))


if __name__ == "__main__":
    main()
