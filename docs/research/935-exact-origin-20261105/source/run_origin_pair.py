"""Compare two exact coordinate frames using the same native OpenFOAM image.

An unchanged head is repeated first. Native transformPoints must preserve all
expected coordinate bits before the translated case can run. Neither case is
admitted for engine physics by this diagnostic.
"""
import gc
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import time

import numpy as np


DEPENDENCIES = {
    "native_worker.py": "5970289aba4e51a816a1a44668d8c78d0ed3c95c9d3ee97ac2e856e677418fca",
    "native_reader.py": "fbcd4fc8dddb319aeff88131c678e26ccba6ae97decb988fcc185872c67644ae",
    "structured_control.py": "cf9a2aff75790a5b359703daa5baf8c943e2885a8151fe29cde01a03cf700689",
    "certify_translation.py": "811d9e6c11d475fa89cdd965afc91f914a24fdbe6ee386e747b9cc904bf9591f",
}


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, data):
    with path.open("x") as stream:
        stream.write(json.dumps(data, indent=2) + "\n")


def load_module(root, name):
    assert sha(root / name) == DEPENDENCIES[name]
    spec = importlib.util.spec_from_file_location("retained_" + name[:-3], root / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def memory_events():
    path = Path("/sys/fs/cgroup/memory.events")
    return dict((name, int(value)) for name, value in (line.split() for line in path.read_text().splitlines())) if path.exists() else None


def metrics(text):
    patterns = {
        "high_aspect_cells": (r"High aspect ratio cells found, Max aspect ratio: ([^,]+), number of cells (\d+)", (float, int)),
        "negative_volumes": (r"Minimum negative volume: ([^,]+), Number of negative volume cells:\s*(\d+)", (float, int)),
        "nonorthogonality": (r"Mesh non-orthogonality Max:\s*(\S+) average:\s*(\S+)", (float, float)),
        "severe_nonorthogonal_faces": (r"severely non-orthogonal \(> 70 degrees\) faces:\s*(\d+)", (int,)),
        "nonorthogonality_errors": (r"Number of non-orthogonality errors:\s*(\d+)", (int,)),
        "face_pyramids": (r"Error in face pyramids:\s*(\d+) faces", (int,)),
        "skewness": (r"Max skewness = ([^,]+), (\d+) highly skew faces", (float, int)),
        "face_tets": (r"Error in face tets:\s*(\d+) faces", (int,)),
        "small_edges_warning": (r"Edges too small, min/max edge length = ([^ ]+) ([^,]+), number too small: (\d+)", (float, float, int)),
        "cell_determinant": (r"Cell determinant \(wellposedness\) : minimum:\s*(\S+) average:\s*(\S+)", (float, float)),
        "small_determinants": (r"Cells with small determinant \(< ([^)]+)\) found, number of cells:\s*(\d+)", (float, int)),
        "concavity_report": (r"Concave cells \(using face planes\) found, number of cells:\s*(\d+)", (int,)),
        "interpolation_weight": (r"Face interpolation weight : minimum:\s*(\S+) average:\s*(\S+)", (float, float)),
        "small_interpolation_weights": (r"Faces with small interpolation weight \(< ([^)]+)\) found, number of faces:\s*(\d+)", (float, int)),
        "volume_ratio": (r"Face volume ratio : minimum:\s*(\S+) average:\s*(\S+)", (float, float)),
        "small_volume_ratios": (r"Faces with small volume ratio \(< ([^)]+)\) found, number of faces:\s*(\d+)", (float, int)),
        "failed_categories": (r"Failed (\d+) mesh checks\.", (int,)),
    }
    result = {}
    for name, (pattern, casts) in patterns.items():
        match = re.search(pattern, text)
        # A disappearing warning is recorded as absent, not silently replaced
        # by an assumed numerical zero; the raw complete log stays authoritative.
        result[name] = [cast(value) for cast, value in zip(casts, match.groups())] if match else None
        if result[name] is not None:
            assert all(math.isfinite(value) for value in result[name])
    assert "\nEnd\n" in text and (result["failed_categories"] is not None or "Mesh OK." in text)
    return result


def main(root):
    assert not (root / "pair-pid.json").exists()
    write(root / "pair-pid.json", {"pid": os.getpid(), "epoch": time.time()})
    plan = json.loads((root / "pair-plan.json").read_text())
    manifest = json.loads((root / "input-manifest.json").read_text())
    for row in manifest["files"]:
        assert sha(root / row["path"]) == row["sha256"]
    for name, expected in DEPENDENCIES.items():
        assert sha(root / name) == expected
    assert plan["foam_setup"] == "/opt/openfoam13/etc/bashrc"
    assert plan["translation"] == [-10, -10, -10] and plan["field_solve_permitted"] is False
    assert sha(root / "parent-native-manifest.json") == "91fbc0ecc6dfdeb2b95949676698f0ea9a1a8605d783efdfa61e2fe3722ed64d"
    parent_index = {row["path"]: row["sha256"] for row in json.loads((root / "parent-native-manifest.json").read_text())["files"]}
    reader = load_module(root, "native_reader.py")
    certificate = load_module(root, "certify_translation.py")
    helper = load_module(root, "structured_control.py")
    write(root / "runtime.json", {"python": sys.version.split()[0], "numpy": np.__version__,
        "machine": os.uname().machine, "source_sha256": sha(Path(__file__)),
        "foam_setup_sha256": sha(Path(plan["foam_setup"])),
        "image_scope": plan["image"], "memory_events_before": memory_events()})

    def run(name, argv, seconds, gib=48):
        def limit():
            resource.setrlimit(resource.RLIMIT_AS, (gib * 1024**3, gib * 1024**3))
        before = memory_events()
        started = time.monotonic()
        shell = 'source "' + plan["foam_setup"] + '" >/dev/null 2>&1 || exit 91; "$@"'
        with (root / (name + ".log")).open("x") as stream:
            child = subprocess.Popen(["bash", "-c", shell, "origin-step", *argv], cwd=root,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=limit)
            timeout = False
            try:
                code = child.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timeout = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    code = child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    code = child.wait()
        result = {"argv": argv, "exit_code": code, "timeout": timeout,
            "seconds": time.monotonic() - started, "address_space_gib": gib,
            "memory_events_before": before, "memory_events_after": memory_events(),
            "log_sha256": sha(root / (name + ".log"))}
        write(root / (name + "-execution.json"), result)
        return code == 0 and not timeout

    def prepare_case(name, with_head):
        case = root / name
        case.mkdir()
        shutil.copyfile(root / "native_worker.py", case / "run_native_geometry.py")
        shutil.copyfile(root / "structured_control.py", case / "structured_control.py")
        helper.prepare(case / "control", root / "precision-source/system/controlDict")
        if with_head:
            shutil.copytree(root / "native-head", case / "head")
        return case

    def finish_case(case, with_head):
        value = {"run_head": with_head, "foam_setup": plan["foam_setup"],
            "head_address_space_gib": 48, "head_timeout_seconds": 600,
            "control_helper_sha256": DEPENDENCIES["structured_control.py"],
            "field_solve_permitted": False, "upstream_head_admission": "diagnostic_only"}
        write(case / "geometry-plan.json", value)
        rows = [{"path": str(path.relative_to(case)), "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(case.rglob("*")) if path.is_file()]
        write(case / "input-manifest.json", {"files": rows})
        assert run(case.name + "-worker", [sys.executable, "-B", str(case / "run_native_geometry.py")], 1000 if with_head else 420)
        result = json.loads((case / "terminal-state.json").read_text())
        assert result.get("controls_passed") and result.get("all_original_inputs_rehashed_unchanged")
        if with_head:
            execution = json.loads((case / "head-geometry-execution.json").read_text())
            assert execution["exit_code"] == 0 and not execution["timeout"], "Native head diagnostic incomplete; paired continuation refused"
            return metrics((case / "head-geometry.log").read_text())
        return None

    assert run("version", ["foamVersion"], 30, gib=1)
    assert run("transform-help", ["transformPoints", "-help"], 30, gib=1)
    assert "translate=<vector>" in (root / "transform-help.log").read_text()
    controls = prepare_case("control-suite", False)
    finish_case(controls, False)
    # This fixture requires 17 significant digits to preserve its x=100+2^-46.
    with np.load(root / "precision-reference.npz", allow_pickle=False) as data:
        expected_precision = data["nodes"]
    assert sha(root / "precision-reference.npz") == "aa34b174bccae6cef41478a1e84d491b39d82817f5cc34b89ad2dd2a43b55107"
    precision = root / "precision-good"
    shutil.copytree(root / "precision-source", precision)
    assert run("precision-identity", ["transformPoints", "translate=(0 0 0)", "-case", str(precision)], 60, gib=1)
    actual = reader.values(precision / "constant/polyMesh/points", 3, np.float64)
    assert np.array_equal(actual.view(np.uint64), expected_precision.view(np.uint64))
    assert run("precision-shift", ["transformPoints", "translate=(-10 -10 -10)", "-case", str(precision)], 60, gib=1)
    actual = reader.values(precision / "constant/polyMesh/points", 3, np.float64)
    expected = expected_precision - 10.
    assert np.array_equal(actual.view(np.uint64), expected.view(np.uint64))
    wrong = root / "precision-wrong-frame"
    shutil.copytree(root / "precision-source", wrong)
    assert run("precision-wrong-frame", ["transformPoints", "translate=(-9 -10 -10)", "-case", str(wrong)], 60, gib=1)
    actual_wrong = reader.values(wrong / "constant/polyMesh/points", 3, np.float64)
    assert not np.array_equal(actual_wrong.view(np.uint64), expected.view(np.uint64))
    write(root / "precision-io-admission.json", {"native_identity_bit_exact": True,
        "native_minus10_transform_bit_exact": True, "wrong_frame_rejected": True,
        "write_precision": 17, "coordinates_checked_per_positive_case": 15})
    result = {"terminal": "native_origin_controls_completed", "controls_passed": True,
        "head_pair_started": bool(plan["run_head_pair"]), "head_pair_complete": False}
    if plan["run_head_pair"]:
        for path in sorted((root / "native-head").rglob("*")):
            if path.is_file():
                relative = str(path.relative_to(root / "native-head"))
                assert sha(path) == parent_index["cloud-import-001/recovered/head/" + relative]
        assert sha(root / "native-head/constant/polyMesh/points") == "19a955aa7ff335da8adffa0e892cc236c356b61c1cdabfe8ea7dbe30280a0c84"
        proof = json.loads((root / "translation-proof.json").read_text())
        assert proof["source_sha256"] == DEPENDENCIES["certify_translation.py"]
        assert proof["integer_lattice_comparison_passed_for_every_coordinate"]
        assert sha(root / "expected-translated-points.npz") == proof["expected_translated_points_sha256"]
        with np.load(root / "expected-translated-points.npz", allow_pickle=False) as data:
            expected_head = data["nodes"]
        original = reader.values(root / "native-head/constant/polyMesh/points", 3, np.float64)
        assert certificate.exact_translation(original, expected_head)
        assert np.array_equal((expected_head + 10.).view(np.uint64), original.view(np.uint64))
        del original, expected_head
        gc.collect()
        baseline = prepare_case("baseline", True)
        baseline_metrics = finish_case(baseline, True)
        shifted = prepare_case("translated", True)
        assert run("head-transform", ["transformPoints", "translate=(-10 -10 -10)", "-case", str(shifted / "head")], 180)
        actual_head = reader.values(shifted / "head/constant/polyMesh/points", 3, np.float64)
        with np.load(root / "expected-translated-points.npz", allow_pickle=False) as data:
            expected_head = data["nodes"]
        assert actual_head.shape == expected_head.shape == (4181299, 3)
        assert np.array_equal(actual_head.view(np.uint64), expected_head.view(np.uint64)), "Native head coordinate transform lost source bits"
        del actual_head, expected_head
        gc.collect()
        unchanged = []
        for path in sorted((shifted / "head").rglob("*")):
            if path.is_file() and path.relative_to(shifted / "head") != Path("constant/polyMesh/points"):
                assert sha(path) == sha(root / "native-head" / path.relative_to(shifted / "head"))
                unchanged.append(str(path.relative_to(shifted / "head")))
        write(root / "head-native-transform-admission.json", {"all_12543897_coordinate_bits_match_exact_prediction": True,
            "unchanged_other_native_head_files": unchanged,
            "native_transformed_points_sha256": sha(shifted / "head/constant/polyMesh/points"),
            "explicit_source_to_trial_frame": proof["source_to_trial_frame"],
            "exact_geometry_change_after_inverse_transform": 0})
        translated_metrics = finish_case(shifted, True)
        differences = {key: {"baseline": baseline_metrics[key], "translated": translated_metrics[key]}
            for key in baseline_metrics if baseline_metrics[key] != translated_metrics[key]}
        write(root / "frame-comparison.json", {"same_image_runtime_and_thresholds": True,
            "baseline": baseline_metrics, "translated": translated_metrics,
            "observed_differences": differences, "exact_geometry_changed": False,
            "intrinsic_conditioning_or_uncoupled_stencil_rank_improved": False,
            "frame_sensitivity_observed": bool(differences),
            "invariance_tolerance_or_error_bound_not_established": True,
            "field_solve_admitted": False})
        result.update(terminal="native_origin_pair_completed", head_pair_complete=True,
                      frame_sensitivity_observed=bool(differences))
    for row in manifest["files"]:
        assert sha(root / row["path"]) == row["sha256"], "An original input changed"
    result.update(all_original_inputs_rehashed_unchanged=True, field_solve_executed=False,
                  physics_admitted=False, manufacturing_qualified=False)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    try:
        result = main(root)
    except Exception as error:
        result = {"terminal": "worker_failed_closed", "exception_type": type(error).__name__,
            "error": str(error), "field_solve_executed": False,
            "physics_admitted": False, "manufacturing_qualified": False}
    write(root / "terminal-state.json", result)
    inputs = json.loads((root / "input-manifest.json").read_text())["files"]
    lookup = {(row["sha256"], row["bytes"]): row["path"] for row in inputs}
    rows, duplicates = [], []
    for path in sorted(root.rglob("*")):
        assert not path.is_symlink()
        if not path.is_file() or path.name == "inputs.tar.gz":
            continue
        row = {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        key = (row["sha256"], row["bytes"])
        if key in lookup:
            duplicates.append({**row, "matching_owner_input": lookup[key]})
        else:
            rows.append(row)
    write(root / "result-manifest.json", {"files": rows, "verified_input_copies": duplicates})
