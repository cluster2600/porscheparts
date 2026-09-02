#!/usr/bin/env python3
"""Smoke F26 hors ligne sur un maillage OBJ entièrement synthétique."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from typing import Any
import xml.etree.ElementTree as ElementTree

import numpy as np


sys.dont_write_bytecode = True


APPLICATION_ROOT = Path("/opt/3dprinting993")
SOURCE_ROOT = APPLICATION_ROOT / "twins/reference-917-engine/source"
PIPELINE = SOURCE_ROOT / "build_topology_context_f26.py"
F18_PIPELINE = SOURCE_ROOT / "review_boundary_components_f18.py"
CONTRACT = APPLICATION_ROOT / "twins/reference-917-engine/topology-context-contract-f26.json"
MANIFEST_NAME = "topology-context-manifest-f26.json"
INVENTORY_NAME = "topology-context-inventory-f26.csv"
RELEASE_GATES = {
    "engine_identity_confirmed": False,
    "scale_confirmed": False,
    "units_confirmed": False,
    "axis_semantics_confirmed": False,
    "semantic_interfaces_confirmed": False,
    "cad_reconstruction_released": False,
    "classical_solver_released": False,
    "physicsnemo_dataset_released": False,
    "physicsnemo_training_released": False,
    "omniverse_simready_released": False,
    "fabrication_released": False,
    "engine_start_released": False,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def network_isolation_evidence() -> dict[str, Any]:
    network_root = Path("/sys/class/net")
    route_file = Path("/proc/net/route")
    ipv6_route_file = Path("/proc/net/ipv6_route")
    require(network_root.is_dir() and route_file.is_file(), "Linux network evidence is unavailable")
    interfaces = sorted(path.name for path in network_root.iterdir())
    ipv4_rows = [line.split() for line in route_file.read_text().splitlines()[1:] if line.strip()]
    ipv6_rows = (
        [line.split() for line in ipv6_route_file.read_text().splitlines() if line.strip()]
        if ipv6_route_file.is_file()
        else []
    )
    routed_interfaces = sorted(
        {row[0] for row in ipv4_rows if row} | {row[-1] for row in ipv6_rows if row}
    )
    external = [name for name in routed_interfaces if name != "lo"]
    default_ipv4 = any(
        len(row) > 7 and row[0] != "lo" and row[1] == "00000000" and row[7] == "00000000"
        for row in ipv4_rows
    )
    default_ipv6 = any(
        len(row) > 1 and row[-1] != "lo" and row[0] == "0" * 32 and row[1] == "00"
        for row in ipv6_rows
    )
    require(not external and not default_ipv4 and not default_ipv6, "smoke requires --network=none")
    return {
        "verified": True,
        "scope": "container_network_namespace",
        "kernel_interfaces": interfaces,
        "routed_interfaces": routed_interfaces,
        "external_routed_interfaces": external,
        "default_ipv4_external_route": default_ipv4,
        "default_ipv6_external_route": default_ipv6,
        "network_calls_attempted": False,
    }


def audit_bundle() -> dict[str, Any]:
    expected = {
        "twins/reference-917-engine/topology-context-contract-f26.json",
        "twins/reference-917-engine/source/build_topology_context_f26.py",
        "twins/reference-917-engine/source/review_boundary_components_f18.py",
    }
    files = sorted(
        str(path.relative_to(APPLICATION_ROOT))
        for path in APPLICATION_ROOT.rglob("*")
        if path.is_file()
    )
    require(set(files) == expected, f"unexpected F26 application bundle: {files}")
    forbidden_suffixes = {
        ".obj", ".ply", ".stl", ".3mf", ".step", ".stp", ".usd", ".usda",
        ".usdc", ".usdz", ".parquet", ".h5", ".hdf5", ".npz", ".bin",
        ".ckpt", ".onnx", ".pt", ".pth", ".safetensors",
    }
    forbidden_assets = sorted(path for path in files if Path(path).suffix.lower() in forbidden_suffixes)
    secret_named = sorted(
        path
        for path in files
        if Path(path).name.lower() == ".env"
        or Path(path).suffix.lower() in {".key", ".pem", ".p12", ".pfx"}
        or any(marker in Path(path).name.lower() for marker in ("credential", "secret", "token"))
    )
    require(not forbidden_assets and not secret_named, "forbidden content found in F26 bundle")
    return {
        "scope": str(APPLICATION_ROOT),
        "expected_files": sorted(expected),
        "unexpected_files": [],
        "forbidden_asset_files": forbidden_assets,
        "secret_named_files": secret_named,
        "dependency_policy": "python_3.12.14_plus_exact_numpy_2.2.6_only",
    }


def load_f18() -> Any:
    specification = importlib.util.spec_from_file_location("review_boundary_components_f18", F18_PIPELINE)
    require(specification is not None and specification.loader is not None, "cannot load F18")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def write_open_cylinder_obj(path: Path) -> tuple[Any, Any]:
    segment_count = 16
    level_count = 7
    lines = ["# synthetic open cylinder for F26 smoke"]
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    for level in range(level_count):
        z = float(level) * 0.35
        radius = 1.0 + 0.04 * math.sin(level * 0.7)
        for segment in range(segment_count):
            angle = 2.0 * math.pi * segment / segment_count
            vertex = [radius * math.cos(angle), radius * math.sin(angle), z]
            vertices.append(vertex)
            lines.append(f"v {vertex[0]:.12f} {vertex[1]:.12f} {vertex[2]:.12f}")
    for level in range(level_count - 1):
        for segment in range(segment_count):
            following = (segment + 1) % segment_count
            lower_left = level * segment_count + segment + 1
            lower_right = level * segment_count + following + 1
            upper_left = (level + 1) * segment_count + segment + 1
            upper_right = (level + 1) * segment_count + following + 1
            lines.append(f"f {lower_left} {lower_right} {upper_right}")
            lines.append(f"f {lower_left} {upper_right} {upper_left}")
            faces.append([lower_left - 1, lower_right - 1, upper_right - 1])
            faces.append([lower_left - 1, upper_right - 1, upper_left - 1])
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return np.asarray(vertices, dtype=np.float64), np.asarray(faces, dtype=np.int64)


def write_f18_report(mesh: Path, report_path: Path, scratch_ply: Path, vertices: Any, faces: Any) -> None:
    f18 = load_f18()
    analysis = f18.analyze_boundary_components(vertices, faces, np)
    require(len(analysis["components"]) == 2, "synthetic mesh must expose two boundaries")
    f18.write_colored_ply(
        scratch_ply,
        vertices[analysis["active_vertices"]],
        analysis["stable_ranks"],
        analysis["candidate_flags"],
        np,
    )
    mesh_hash = sha256(mesh)
    source = {
        "mode": "synthetic_container_smoke",
        "input_path": None,
        "input_bytes": mesh.stat().st_size,
        "actual_sha256": mesh_hash,
        "expected_sha256": mesh_hash,
        "provenance_hash_matched": True,
        "raw_geometry_embedded_in_report": False,
    }
    report = f18.build_report(analysis, source, scratch_ply)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def command(mesh: Path, report: Path, output: Path, *, report_hash: str | None = None) -> list[str]:
    return [
        sys.executable,
        str(PIPELINE),
        "--contract", str(CONTRACT),
        "--contract-sha256", sha256(CONTRACT),
        "--mesh", str(mesh),
        "--mesh-sha256", sha256(mesh),
        "--f18-report", str(report),
        "--f18-report-sha256", report_hash or sha256(report),
        "--expected-components", "2",
        "--batch-size", "1",
        "--fixture-mode",
        "--output", str(output),
    ]


def run(arguments: list[str], *, success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        arguments,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "PYTHONHASHSEED": "0",
            "PIP_NO_INDEX": "1",
            "NO_PROXY": "*",
            "no_proxy": "*",
        },
    )
    if success:
        require(completed.returncode == 0, completed.stdout + completed.stderr)
    else:
        require(completed.returncode != 0, "invalid F26 invocation was accepted")
    return completed


def tree_payloads(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def exercise_pipeline() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="topology-context-f26-") as temporary:
        root = Path(temporary)
        mesh = root / "synthetic-open-cylinder.obj"
        report = root / "synthetic-f18.json"
        scratch_ply = root / "synthetic-f18.ply"
        vertices, faces = write_open_cylinder_obj(mesh)
        write_f18_report(mesh, report, scratch_ply, vertices, faces)
        first, second = root / "first", root / "second"
        generated = run(command(mesh, report, first), success=True)
        run(command(mesh, report, second), success=True)
        first_payloads, second_payloads = tree_payloads(first), tree_payloads(second)
        require(first_payloads == second_payloads, "F26 outputs are not byte-for-byte deterministic")
        manifest = json.loads(first_payloads[MANIFEST_NAME])
        require(manifest["phase"] == "F26", "wrong manifest phase")
        require(manifest["review_policy"]["component_count"] == 2, "wrong component count")
        require(manifest["review_policy"]["confirmed_interface_count"] == 0, "an interface was confirmed")
        require(len(manifest["batches"]) == 2, "batch-size=1 must produce two batches")
        require(all(item["component_count"] == 1 for item in manifest["batches"]), "batch bound changed")
        require(manifest["topology_policy"]["topological_ring_count"] == 2, "wrong ring count")
        require(manifest["release_gates"] == RELEASE_GATES, "release gates changed")
        artifacts = manifest["artifacts"]
        require(len(artifacts) == 5, "two JSON, two SVG and one CSV payload are required")
        for artifact in artifacts:
            payload = first_payloads[artifact["path"]]
            require(hashlib.sha256(payload).hexdigest() == artifact["sha256"], "artifact hash mismatch")
            require(len(payload) == artifact["bytes"], "artifact byte count mismatch")
        with (first / INVENTORY_NAME).open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == 2, "inventory row count mismatch")
        require(all(row["review_state"] == "undetermined" for row in rows), "review was decided")
        require(all(row["semantic_interface_confirmed"] == "false" for row in rows), "interface was decided")
        require(all(int(row["incident_face_count"]) > 0 for row in rows), "incident faces missing")
        require(all(int(row["ring_1_face_count"]) > 0 for row in rows), "ring 1 missing")
        require(all(int(row["ring_2_face_count"]) > 0 for row in rows), "ring 2 missing")
        svg_paths = sorted(first.glob("batch_*/*.svg"))
        require(len(svg_paths) == 2, "wrong SVG count")
        for svg_path in svg_paths:
            svg_text = svg_path.read_text(encoding="utf-8")
            svg_root = ElementTree.fromstring(svg_text)
            require(svg_root.tag.endswith("svg"), "invalid SVG root")
            require(svg_text.count('class="orthographic-view"') == 4, "SVG must have four orthographic views")
            require(svg_text.count('class="global-locator"') == 4, "every view must have a locator")
            require("Aucune interface confirmée" in svg_text, "SVG safety label missing")
        existing = run(command(mesh, report, first), success=False)
        require("output already exists" in existing.stderr, "overwrite guard did not fail closed")
        wrong_hash = run(command(mesh, report, root / "wrong", report_hash="0" * 64), success=False)
        require("F18 report SHA-256 mismatch" in wrong_hash.stderr, "report hash mismatch did not fail closed")
        summary = json.loads(generated.stdout)
        require(summary["component_count"] == 2 and summary["batch_count"] == 2, "wrong CLI summary")
        return {
            "synthetic_components": 2,
            "incident_faces_present": True,
            "ring_1_present": True,
            "ring_2_present": True,
            "topological_ring_count": 2,
            "orthographic_views_per_component": 4,
            "global_locators_per_component": 4,
            "batch_count": 2,
            "maximum_components_per_batch": 1,
            "payload_file_count": len(artifacts),
            "all_payload_hashes_verified": True,
            "deterministic_tree_byte_identical": True,
            "confirmed_interfaces": 0,
            "rejected_existing_output": True,
            "rejected_wrong_report_hash": True,
        }


def export_fixture(directory: Path) -> dict[str, Any]:
    require(directory.is_dir() and not directory.is_symlink(), "fixture export target must be a directory")
    information = directory.stat(follow_symlinks=False)
    require(information.st_uid == os.geteuid(), "fixture export target must belong to the runtime uid")
    require((information.st_mode & 0o777) == 0o700, "fixture export target must be mode 0700")
    require(not any(directory.iterdir()), "fixture export target must be empty")
    mesh = directory / "synthetic-open-cylinder.obj"
    report = directory / "synthetic-f18.json"
    ply = directory / "synthetic-f18.ply"
    vertices, faces = write_open_cylinder_obj(mesh)
    write_f18_report(mesh, report, ply, vertices, faces)
    evidence = {
        "schema_version": "1.0.0",
        "status": "synthetic_bind_fixture_exported",
        "component_count": 2,
        "mesh_name": mesh.name,
        "mesh_sha256": sha256(mesh),
        "report_name": report.name,
        "report_sha256": sha256(report),
        "contract_sha256": sha256(CONTRACT),
        "raw_or_derived_fixture_committed": False,
        "release_gates": dict(RELEASE_GATES),
    }
    evidence_path = directory / "synthetic-bind-fixture-f26.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


def run_smoke() -> dict[str, Any]:
    require(sys.version_info[:2] == (3, 12), "Python 3.12 is required")
    require(np.__version__ == "2.2.6", "NumPy 2.2.6 is required")
    require(platform.machine().lower() in {"amd64", "x86_64"}, "linux/amd64 is required")
    require(os.geteuid() != 0, "smoke must run as a non-root user")
    require(not Path("/dev/nvidia0").exists(), "a GPU device must not be exposed")
    require(PIPELINE.is_file() and F18_PIPELINE.is_file() and CONTRACT.is_file(), "F26 bundle is incomplete")
    return {
        "schema_version": "1.0.0",
        "status": "passed_synthetic_fixture_only",
        "offline": True,
        "non_root": True,
        "gpu": False,
        "platform": "linux/amd64-cpu",
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "network_isolation_evidence": network_isolation_evidence(),
        "bundled_content_audit": audit_bundle(),
        "checks": exercise_pipeline(),
        "release_gates": dict(RELEASE_GATES),
        "claim_scope": (
            "synthetic fixtures verify the deterministic local topology-context software path only; "
            "no canonical scan, physical interface, CAD, CAE, PhysicsNeMo, fabrication or engine function"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-fixture", type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.export_fixture is not None:
            require(sys.version_info[:2] == (3, 12), "Python 3.12 is required")
            require(np.__version__ == "2.2.6", "NumPy 2.2.6 is required")
            require(platform.machine().lower() in {"amd64", "x86_64"}, "linux/amd64 is required")
            require(os.geteuid() == 9174, "fixture export must run as uid 9174")
            require(not Path("/dev/nvidia0").exists(), "a GPU device must not be exposed")
            network_isolation_evidence()
            audit_bundle()
            report = export_fixture(arguments.export_fixture)
        else:
            report = run_smoke()
    except Exception as error:
        print(json.dumps({"schema_version": "1.0.0", "status": "failed", "error": str(error)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
