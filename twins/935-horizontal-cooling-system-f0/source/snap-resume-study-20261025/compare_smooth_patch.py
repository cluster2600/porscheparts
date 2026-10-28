"""Compare the pinned 935 snappyHexMesh nSmoothPatch=5 and 10 trials.

Only native mesh-quality evidence may decide CFD admission. Both cases remain
uncalibrated and no simulation result is inferred from their exit codes.
"""

import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile


PARENT_SHA256 = "dec99a42ca61d290d89bf116f83ff583fd4afd4c46d386f7a42d58724be09b41"
CHILD_SHA256 = "05b9405f30e3eec09eed8d02fa6f8e6b86d3afe19930ded9665440762c048d59"
PARENT = "snappy-refine34-spaced3-20261028"
CHILD = "smooth10-case"
ROTOR_SHA256 = "ee9357d46911fc0112342626064f7e731395af9db9a8bc340793cf22effb24a6"
QUALITY_SHA256 = "bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def member_digest(archive: tarfile.TarFile, name: str) -> str:
    stream = archive.extractfile(name)
    if stream is None:
        raise ValueError(f"Missing archive member: {name}")
    h = hashlib.sha256()
    with stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def member_text(archive: tarfile.TarFile, name: str) -> str:
    stream = archive.extractfile(name)
    if stream is None:
        raise ValueError(f"Missing archive member: {name}")
    with stream:
        return stream.read().decode("utf-8")


def integer(log: str, pattern: str) -> int:
    matches = re.findall(pattern, log, flags=re.MULTILINE)
    if len(matches) != 1:
        raise ValueError(f"Expected one native checkMesh result matching {pattern}")
    return int(matches[0])


def metrics(log: str) -> dict:
    return {
        "cells": integer(log, r"^\s+cells:\s+(\d+)\s*$"),
        "concave_cells": integer(log, r"^ \*\*\*Concave cells \(using face planes\) found, number of cells: (\d+)"),
        "failed_mesh_checks": integer(log, r"^Failed (\d+) mesh checks\.\s*$"),
        "small_determinant_cells": int((re.search(
            r"^ \*\*\*Cells with small determinant \(< 0\.001\) found, number of cells: (\d+)",
            log, flags=re.MULTILINE) or [0, 0])[1]),
        "low_weight_faces": int((re.search(
            r"^ \*\*\*Faces with small interpolation weight .*number of faces: (\d+)",
            log, flags=re.MULTILINE) or [0, 0])[1]),
    }


def fixture() -> None:
    sample = "    cells: 42\n ***Concave cells (using face planes) found, number of cells: 7\nFailed 1 mesh checks.\n"
    expected = {"cells": 42, "concave_cells": 7, "failed_mesh_checks": 1,
                "small_determinant_cells": 0, "low_weight_faces": 0}
    if metrics(sample) != expected:
        raise ValueError("Native log parser fixture failed")


def run(parent_path: Path, child_path: Path, output: Path) -> None:
    parent_path, child_path, output = (path.resolve() for path in
                                       (parent_path, child_path, output))
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ report path")
    if digest(parent_path) != PARENT_SHA256 or digest(child_path) != CHILD_SHA256:
        raise ValueError("Pinned trial archive changed")
    fixture()
    with tarfile.open(parent_path, "r:gz") as parent, tarfile.open(child_path, "r:gz") as child:
        common_files = ("system/blockMeshDict", "system/controlDict", "system/fvSchemes",
                        "system/fvSolution", "system/meshQualityDict",
                        "constant/triSurface/rotor.obj")
        common_hashes = {}
        for name in common_files:
            a = member_digest(parent, f"{PARENT}/{name}")
            b = member_digest(child, f"{CHILD}/{name}")
            if a != b:
                raise ValueError(f"Non-smoothing input changed: {name}")
            common_hashes[name] = a
        if (common_hashes["constant/triSurface/rotor.obj"] != ROTOR_SHA256
                or common_hashes["system/meshQualityDict"] != QUALITY_SHA256):
            raise ValueError("Corrected rotor or quality baseline changed")
        parent_dict = member_text(parent, f"{PARENT}/system/snappyHexMeshDict")
        child_dict = member_text(child, f"{CHILD}/system/snappyHexMeshDict")
        if (parent_dict.count("nSmoothPatch 5;") != 1
                or child_dict.count("nSmoothPatch 10;") != 1
                or child_dict.replace("nSmoothPatch 10;", "nSmoothPatch 5;") != parent_dict):
            raise ValueError("Snappy dictionaries differ beyond nSmoothPatch")
        parent_log = member_text(parent, f"{PARENT}/log.checkMesh.full")
        child_log = member_text(child, f"{CHILD}/log.checkMesh.full")
        parent_metrics, child_metrics = metrics(parent_log), metrics(child_log)
        child_snappy = member_text(child, f"{CHILD}/log.snappyHexMesh")
        if child_snappy.count("Finished meshing without any errors") != 1:
            raise ValueError("New snappy run did not finish cleanly")
        duration = re.search(r"Finished meshing in = ([0-9.]+) s\.", child_snappy)
        if duration is None:
            raise ValueError("Native snappy duration missing")
    if (child_metrics["cells"] != parent_metrics["cells"]
            or parent_metrics["failed_mesh_checks"] < 1
            or child_metrics["failed_mesh_checks"] < 1):
        raise ValueError("Unexpected baseline or accepted mesh; review manually")
    result = {"status": "rejected_smoothing_trial_no_CFD",
              "parent_archive_sha256": PARENT_SHA256, "child_archive_sha256": CHILD_SHA256,
              "common_input_sha256": common_hashes, "only_snappy_dictionary_change": "nSmoothPatch 5 -> 10",
              "parent_checkMesh": parent_metrics, "child_checkMesh": child_metrics,
              "delta_concave_cells": child_metrics["concave_cells"] - parent_metrics["concave_cells"],
              "child_snappy_duration_s": float(duration[1]),
              "same_cell_count": True, "full_checkMesh_passed": False,
              "CFD_accepted": False, "source_unit_to_mm_verified": False,
              "manufacturing_authorized": False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    output.chmod(0o600)
    print(json.dumps({"status": result["status"], "report_sha256": digest(output),
                      "delta_concave_cells": result["delta_concave_cells"]}))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: compare_smooth_patch.py PARENT_ARCHIVE CHILD_ARCHIVE NEW_PRIVATE_REPORT")
    run(*(Path(arg) for arg in sys.argv[1:]))
