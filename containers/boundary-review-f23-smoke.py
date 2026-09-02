#!/usr/bin/env python3
"""Smoke F23 hors ligne sur un rapport F18 et un PLY entièrement synthétiques."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import tempfile
from typing import Any
import xml.etree.ElementTree as ElementTree


PIPELINE_ROOT = Path("/opt/3dprinting993/twins/reference-917-engine/source")
PIPELINE = PIPELINE_ROOT / "build_boundary_review_workpack_f23.py"
EXPECTED_OUTPUTS = {
    "boundary-review-atlas-f23.svg",
    "boundary-review-queue-f23.csv",
    "boundary-review-workpack-f23.json",
}
EXPECTED_STDLIB_IMPORTS = {
    "__future__",
    "argparse",
    "csv",
    "datetime",
    "hashlib",
    "html",
    "io",
    "json",
    "math",
    "os",
    "pathlib",
    "re",
    "stat",
    "struct",
    "typing",
}
PLY_PROPERTIES = (
    "property double x",
    "property double y",
    "property double z",
    "property uchar red",
    "property uchar green",
    "property uchar blue",
    "property uchar alpha",
    "property uint component_rank",
    "property uchar candidate",
)
PLY_RECORD = struct.Struct("<dddBBBBIB")
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    external_routed_interfaces = [name for name in routed_interfaces if name != "lo"]
    default_ipv4 = any(
        len(row) > 7
        and row[0] != "lo"
        and row[1] == "00000000"
        and row[7] == "00000000"
        for row in ipv4_rows
    )
    default_ipv6 = any(
        len(row) > 1
        and row[-1] != "lo"
        and row[0] == "0" * 32
        and row[1] == "00"
        for row in ipv6_rows
    )
    isolated = not external_routed_interfaces and not default_ipv4 and not default_ipv6
    require(isolated, "smoke requires --network=none (no externally routed interface)")
    return {
        "verified": True,
        "scope": "container_network_namespace",
        "kernel_interfaces": interfaces,
        "routed_interfaces": routed_interfaces,
        "external_routed_interfaces": external_routed_interfaces,
        "default_ipv4_external_route": default_ipv4,
        "default_ipv6_external_route": default_ipv6,
        "network_calls_attempted": False,
    }


def audit_pipeline_source() -> dict[str, Any]:
    tree = ast.parse(PIPELINE.read_text(encoding="utf-8"), filename=str(PIPELINE))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    unexpected_imports = sorted(imports - EXPECTED_STDLIB_IMPORTS)
    require(not unexpected_imports, f"non-stdlib imports in F23 pipeline: {unexpected_imports}")

    expected_files = {str(PIPELINE.relative_to(PIPELINE_ROOT.parent.parent.parent))}
    scope = Path("/opt/3dprinting993")
    files = sorted(str(path.relative_to(scope)) for path in scope.rglob("*") if path.is_file())
    require(set(files) == expected_files, f"unexpected application bundle: {files}")
    forbidden_suffixes = {
        ".obj", ".ply", ".stl", ".3mf", ".step", ".stp",
        ".usd", ".usda", ".usdc", ".usdz", ".parquet", ".h5",
        ".hdf5", ".npz", ".bin", ".ckpt", ".onnx", ".pt", ".pth",
        ".safetensors",
    }
    forbidden_files = sorted(path for path in files if Path(path).suffix.lower() in forbidden_suffixes)
    secret_named_files = sorted(
        path
        for path in files
        if Path(path).name.lower() == ".env"
        or Path(path).suffix.lower() in {".key", ".pem", ".p12", ".pfx"}
        or any(marker in Path(path).name.lower() for marker in ("credential", "secret", "token"))
    )
    require(not forbidden_files and not secret_named_files, "forbidden content found in F23 bundle")
    return {
        "scope": str(scope),
        "expected_files": sorted(expected_files),
        "unexpected_files": [],
        "forbidden_asset_files": forbidden_files,
        "secret_named_files": secret_named_files,
        "pipeline_imports": sorted(imports),
        "dependency_policy": "python_standard_library_only_no_packages_installed_by_f23",
    }


def synthetic_component(rank: int, review_class: str, size: float) -> dict[str, Any]:
    candidate = review_class == "candidate"
    return {
        "boundary_edge_count": 16,
        "boundary_vertex_count": 16,
        "minimum_source_vertex_index_1_based": rank * 16 + 1,
        "endpoint_count": 0,
        "branched_vertex_count": 0,
        "closed_loop": True,
        "centroid_obj_units": [size, 0.0, 0.0],
        "bounds_min_obj_units": [0.0, 0.0, 0.0],
        "bounds_max_obj_units": [size, size * 0.8, size * 0.2],
        "bbox_extent_obj_units": [size, size * 0.8, size * 0.2],
        "perimeter_obj_units": size * 4.0,
        "projected_area_obj_units_squared": size * size,
        "projected_area_method": "closed_loop_pca_plane_shoelace",
        "planarity": {
            "normal_unoriented_scan_coordinates": [0.0, 0.0, 1.0],
            "plane_rms_obj_units": 0.0,
            "planarity_ratio": 0.0,
        },
        "circularity": {
            "fit_center_obj_units": [0.0, 0.0, 0.0],
            "diameter_obj_units": size,
            "circle_fit_rms_obj_units": 0.01,
            "circle_fit_p95_obj_units": 0.01,
            "relative_circle_fit_p95": 0.01 if candidate else 0.3,
            "angular_coverage": 0.9,
            "circularity_factor": 0.9,
        },
        "candidate_score": 0.9 + rank / 1000.0 if candidate else 0.4,
        "candidate_gates": {},
        "review_class": review_class,
        "semantic_label": None,
        "interface_confirmed": False,
        "human_review_state": "pending",
        "component_id": f"boundary_{rank:04d}",
        "component_rank": rank,
        "source_graph_component_id": rank - 1,
    }


def write_fixture(directory: Path) -> tuple[Path, str, Path, str]:
    components = [
        synthetic_component(rank, "candidate" if rank <= 3 else "unclassified", float(rank))
        for rank in range(1, 10)
    ]
    ply = directory / "synthetic-boundaries.ply"
    records: list[bytes] = []
    for component in components:
        rank = component["component_rank"]
        size = float(rank)
        for point_index in range(16):
            side = point_index % 4
            layer = point_index // 4
            x = size if side in (1, 2) else 0.0
            y = size if side in (2, 3) else 0.0
            z = size * 0.01 * layer
            records.append(
                PLY_RECORD.pack(
                    x, y, z, 30, 180, 220, 255, rank,
                    int(component["review_class"] == "candidate"),
                )
            )
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        "comment synthetic F23 smoke fixture\n"
        f"element vertex {len(records)}\n"
        + "\n".join(PLY_PROPERTIES)
        + "\nend_header\n"
    ).encode("ascii")
    ply.write_bytes(header + b"".join(records))
    ply_hash = sha256(ply)
    report = {
        "schema": "porsche-917-boundary-human-review/f18-v1",
        "phase": "F18",
        "status": "complete_geometric_inventory_pending_human_review",
        "source": {"mode": "synthetic_container_smoke"},
        "coordinate_policy": {
            "reported_units": "synthetic coordinate units",
            "metric_conversion_applied": False,
            "scale_inference_applied": False,
            "axis_semantics_inferred": False,
        },
        "topology": {
            "boundary_edges": len(records),
            "boundary_vertices": len(records),
            "boundary_components": len(components),
            "reported_boundary_components": len(components),
            "boundary_components_truncated": False,
        },
        "classification_policy": {},
        "summary": {
            "candidate_count": 3,
            "unclassified_count": 6,
            "confirmed_interface_count": 0,
            "human_review_pending_count": 9,
        },
        "components": components,
        "visualization": {
            "path": ply.name,
            "sha256": ply_hash,
            "bytes": ply.stat().st_size,
            "point_count": len(records),
        },
        "release_gates": dict(RELEASE_GATES),
        "limitations": ["synthetic fixture only"],
    }
    report_path = directory / "synthetic-f18.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path, sha256(report_path), ply, ply_hash


def generation_command(
    report: Path, report_hash: str, ply: Path, ply_hash: str, output: Path
) -> list[str]:
    return [
        sys.executable,
        str(PIPELINE),
        "--report", str(report),
        "--report-sha256", report_hash,
        "--ply", str(ply),
        "--ply-sha256", ply_hash,
        "--expected-component-count", "9",
        "--expected-candidate-count", "3",
        "--secondary-count", "3",
        "--output", str(output),
    ]


def run_command(arguments: list[str], *, expected_success: bool) -> subprocess.CompletedProcess[str]:
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
    if expected_success:
        require(completed.returncode == 0, completed.stdout + completed.stderr)
    else:
        require(completed.returncode != 0, "invalid F23 input was accepted")
    return completed


def exercise_pipeline() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="boundary-review-f23-") as temporary:
        root = Path(temporary)
        report, report_hash, ply, ply_hash = write_fixture(root)
        first = root / "first"
        second = root / "second"
        command = generation_command(report, report_hash, ply, ply_hash, first)
        generated = run_command(command, expected_success=True)
        generation_report = json.loads(generated.stdout)
        run_command(generation_command(report, report_hash, ply, ply_hash, second), expected_success=True)

        produced = {path.name for path in first.iterdir() if path.is_file()}
        require(produced == EXPECTED_OUTPUTS, f"unexpected F23 outputs: {sorted(produced)}")
        workpack_path = first / "boundary-review-workpack-f23.json"
        csv_path = first / "boundary-review-queue-f23.csv"
        svg_path = first / "boundary-review-atlas-f23.svg"
        workpack = json.loads(workpack_path.read_text(encoding="utf-8"))
        require(workpack["summary"]["selected_for_current_workpack"] == 6, "wrong queue size")
        require(workpack["summary"]["primary_circular_candidate_count"] == 3, "wrong primary size")
        require(workpack["summary"]["secondary_large_unclassified_count"] == 3, "wrong control size")
        require(workpack["summary"]["confirmed_interface_count"] == 0, "interface was confirmed")
        require(all(item["review"]["state"] == "undetermined" for item in workpack["items"]), "review was decided")
        require(all(item["semantic_interface_confirmed"] is False for item in workpack["items"]), "semantic interface was opened")
        require(all(item["release_authority"] is False for item in workpack["items"]), "release authority was opened")
        require(workpack["release_gates"] == RELEASE_GATES, "release gates changed")

        with csv_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == 6, "CSV row count mismatch")
        require(all(row["review_state"] == "undetermined" for row in rows), "CSV review was decided")
        require(all(row["semantic_interface_confirmed"] == "false" for row in rows), "CSV interface was confirmed")
        require(all(row["release_authority"] == "false" for row in rows), "CSV release was opened")
        svg_root = ElementTree.fromstring(svg_path.read_text(encoding="utf-8"))
        require(svg_root.tag.endswith("svg"), "SVG root is invalid")

        require(csv_path.read_bytes() == (second / csv_path.name).read_bytes(), "CSV is not deterministic")
        require(svg_path.read_bytes() == (second / svg_path.name).read_bytes(), "SVG is not deterministic")
        require(
            workpack_path.read_bytes() == (second / workpack_path.name).read_bytes(),
            "JSON is not byte-for-byte deterministic",
        )

        validated = run_command(
            [
                sys.executable,
                str(PIPELINE),
                "--validate-review-file", str(workpack_path),
                "--report", str(report),
                "--report-sha256", report_hash,
                "--ply", str(ply),
                "--ply-sha256", ply_hash,
                "--expected-component-count", "9",
                "--expected-candidate-count", "3",
                "--secondary-count", "3",
            ],
            expected_success=True,
        )
        validation_report = json.loads(validated.stdout)
        require(validation_report["status"] == "valid_review_workpack", "review validation failed")

        repeated = run_command(command, expected_success=False)
        require("output already exists" in repeated.stderr, "overwrite guard did not fail closed")
        wrong_hash = generation_command(report, "0" * 64, ply, ply_hash, root / "wrong-hash")
        mismatch = run_command(wrong_hash, expected_success=False)
        require("report SHA-256 mismatch" in mismatch.stderr, "hash mismatch did not fail closed")

        return {
            "synthetic_components": 9,
            "selected_components": 6,
            "primary_components": 3,
            "control_components": 3,
            "confirmed_interfaces": 0,
            "outputs": sorted(produced),
            "csv_rows": len(rows),
            "svg_xml_valid": True,
            "deterministic_outputs": {
                "csv_byte_identical": True,
                "svg_byte_identical": True,
                "json_byte_identical": True,
            },
            "review_validation_exercised": True,
            "rejected_existing_output": True,
            "rejected_wrong_report_hash": True,
            "generation_status": generation_report["status"],
        }


def run_smoke() -> dict[str, Any]:
    require(sys.version_info[:2] == (3, 12), "Python 3.12 is required")
    require(platform.machine().lower() in {"amd64", "x86_64"}, "linux/amd64 is required")
    require(os.geteuid() != 0, "smoke must run as a non-root user")
    require(not Path("/dev/nvidia0").exists(), "a GPU device must not be exposed")
    require(PIPELINE.is_file(), "F23 pipeline is missing")
    network = network_isolation_evidence()
    bundle = audit_pipeline_source()
    checks = exercise_pipeline()
    return {
        "schema_version": "1.0.0",
        "status": "passed_synthetic_fixture_only",
        "offline": True,
        "non_root": True,
        "gpu": False,
        "platform": "linux/amd64-cpu",
        "python": sys.version.split()[0],
        "network_isolation_evidence": network,
        "bundled_content_audit": bundle,
        "checks": checks,
        "release_gates": dict(RELEASE_GATES),
        "claim_scope": (
            "synthetic fixtures validate the local SVG/JSON/CSV review-workpack software path only; "
            "no scan identity, physical interface, CAD, simulation, manufacturing or engine function"
        ),
    }


def main() -> int:
    try:
        report = run_smoke()
    except Exception as error:
        print(
            json.dumps(
                {"schema_version": "1.0.0", "status": "failed", "error": str(error)},
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
