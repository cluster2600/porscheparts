"""Check analytic curve bounds and reason-specific disk-fit refusals."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def imported(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("arrays", "parent", "plan", "study", "source", "evaluator", "chart_verifier", "output"):
        p.add_argument("--" + key.replace("_", "-"), dest=key, type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    producer = imported(a.source / "study_disk_fits.py", "current_curve_producer")
    verifier = imported(a.source / "verify_disk_fits.py", "current_curve_verifier")
    evaluator = imported(a.evaluator, "frozen_polynomial_evaluator")
    curves = {}
    for name, c, origin, frame, expected in [
        ("exact_source_plane", [0, 0, 0, 0, 0, 0], np.zeros(3), np.eye(3), (0., 0.)),
        ("constant_offset", [.02, 0, 0, 0, 0, 0], np.zeros(3), np.eye(3), (.02, .02)),
        ("zero_endpoints_interior_bubble", [0, 4, 0, -4, 0, 0], np.zeros(3), np.eye(3), (2., 1.)),
        ("rigidly_transformed_bubble", [0, 4, 0, -4, 0, 0], np.array([10., -3., 7.]),
         np.array([[0., 1., 0.], [-1., 0., 0.], [0., 0., 1.]]), (2., 1.)),
    ]:
        model = {"origin": origin, "frame": frame, "uv_scale": np.ones(2), "coefficients": np.array([c, c])}
        first, last = origin, origin + frame[0]
        power = producer.curve_power(first, last, model, 1) - producer.curve_power(first, last, None, 1)
        produced = producer.curve_bounds(power)
        inspected = verifier.curve_certificate(first, last, model, None, 1, evaluator)
        if not np.allclose(produced, expected, atol=1e-12, rtol=0) or not np.allclose(inspected, expected, atol=1e-12, rtol=0):
            raise AssertionError("Analytic curve fixture failed: " + name)
        curves[name] = {"upper_mm": produced[0], "sample_max_mm": produced[1], "independently_checked": True}
    report = json.loads((a.study / "study.json").read_text())
    region, domain = next((r["region"], d["domain"]) for r in report["regions"] for d in r["domains"] if d["state"] == "fitted_for_diagnostics")
    cases = {
        "source_split": "Fixed source-ID split or source coverage changed",
        "coefficient": "Training-only normal equations changed",
        "boundary_curve": "Source boundary curve certificate changed",
        "cut_curve": "Seam Bernstein curve certificate changed",
        "native_admission": "Unsupported digital/boundary/native admission",
    }
    refusals = {}
    for name, expected in cases.items():
        directory = a.output / name
        shutil.copytree(a.study, directory)
        output_report = json.loads((directory / "study.json").read_text())
        record = output_report["regions"][region]["domains"][domain]
        if name == "source_split":
            record["training_vertices"] += 1
        elif name == "native_admission":
            record["models"][0]["eligible_for_native_export_screen"] = True
        else:
            suffix = "-boundary" if name == "boundary_curve" else ""
            path = directory / (f"region-{region}-seams.npz" if name == "cut_curve" else f"region-{region}-domain-{domain:03d}{suffix}.npz")
            with np.load(path, allow_pickle=False) as d:
                data = {k: d[k].copy() for k in d.files}
            if name == "coefficient":
                data["coefficients"][0, 0] += .02
            elif name == "boundary_curve":
                data["upper_mm"][0] *= .5
            else:
                data["upper_mm"][0, 0] += .01
            np.savez_compressed(path, **data)
            if name == "cut_curve":
                output_report["regions"][region]["seam_certificate_sha256"] = sha(path)
            else:
                record["boundary_certificate_sha256" if name == "boundary_curve" else "model_sha256"] = sha(path)
        (directory / "study.json").write_text(json.dumps(output_report, indent=2) + "\n")
        target = directory / "forbidden-success.json"
        argv = [sys.executable, "-B", str(a.source / "verify_disk_fits.py"),
                "--arrays", str(a.arrays), "--parent", str(a.parent), "--plan", str(a.plan),
                "--study", str(directory), "--evaluator", str(a.evaluator),
                "--chart-verifier", str(a.chart_verifier), "--output", str(target)]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=600)
        (directory / "refusal.log").write_text(result.stdout + result.stderr)
        if result.returncode == 0 or target.exists() or expected not in result.stderr:
            raise AssertionError("Reason-specific refusal failed: " + name)
        refusals[name] = {"refused": True, "reason": expected, "no_success_output": True}
    result = {"analytic_curves": curves, "refusals": refusals}
    (a.output / "controls.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
