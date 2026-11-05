"""Check reason-specific chart-verifier refusals without changing frozen inputs."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("arrays", "parent", "plan", "audit", "verifier", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    expected = {
        "changed_original_face": "Stored chart differs from original source",
        "changed_uv": "Stored chart differs from original source",
        "lost_candidate": "Candidate pair census mismatch",
        "forged_boundary_count": "Aggregate audit mismatch: boundary_edges",
        "forged_admission": "Unsupported admission state",
    }
    passed = {}
    for name, reason in expected.items():
        case = a.output / name
        shutil.copytree(a.audit, case)
        report_path = case / "audit.json"
        report = json.loads(report_path.read_text())
        if name in ("changed_original_face", "changed_uv", "lost_candidate"):
            chart = case / "region-0-chart.npz"
            with np.load(chart, allow_pickle=False) as d:
                data = {k: d[k].copy() for k in d.files}
            if name == "changed_original_face":
                data["original_face_ids"][0] = data["original_face_ids"][1]
            elif name == "changed_uv":
                data["uv"][0, 0] += .001
            else:
                data["aabb_pairs"] = data["aabb_pairs"][:-1]
            np.savez_compressed(chart, **data)
            report["regions"][0]["private_chart_sha256"] = sha(chart)
        elif name == "forged_boundary_count":
            report["regions"][0]["boundary_edges"] += 1
        else:
            report["regions"][0]["native_smooth_surface_admitted"] = True
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        output = case / "forbidden-success.json"
        argv = [sys.executable, str(a.verifier), "--arrays", str(a.arrays),
                "--parent", str(a.parent), "--plan", str(a.plan),
                "--audit", str(case), "--output", str(output)]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=600)
        (case / "verifier.log").write_text(result.stdout + result.stderr)
        if result.returncode == 0 or output.exists() or reason not in result.stderr:
            raise AssertionError("Refusal control failed: " + name)
        passed[name] = {"refused": True, "reason": reason, "no_success_output": True}
    (a.output / "controls.json").write_text(json.dumps(passed, indent=2) + "\n")
    print(json.dumps(passed))


if __name__ == "__main__":
    main()
