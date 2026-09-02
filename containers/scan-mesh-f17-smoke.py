#!/usr/bin/env python3
"""Smoke F17 sur fixtures synthétiques dans un espace réseau isolé."""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path


PIPELINE_ROOT = Path("/opt/3dprinting993/twins/reference-917-engine/source")
PREPARE_SCAN = PIPELINE_ROOT / "prepare_scan.py"
ANALYZE_BOUNDARIES = PIPELINE_ROOT / "analyze_boundaries.py"
SEGMENT_ENGINE = PIPELINE_ROOT / "segment_engine.py"
EXPECTED_PACKAGES = {
    "numpy": "2.5.2",
    "scipy": "1.18.1",
    "trimesh": "5.1.0",
    "pymeshlab": "2025.7.post1",
    "rtree": "1.4.1",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"f17_{path.stem}", path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def open_cylinder(np, trimesh, sections: int = 32, radius: float = 50.0, height: float = 20.0):
    angles = np.linspace(0.0, 2.0 * np.pi, sections, endpoint=False)
    lower = np.column_stack(
        (radius * np.cos(angles), radius * np.sin(angles), np.full(sections, -height / 2.0))
    )
    upper = lower.copy()
    upper[:, 2] = height / 2.0
    vertices = np.vstack((lower, upper))
    faces = []
    for index in range(sections):
        following = (index + 1) % sections
        faces.append((index, following, sections + following))
        faces.append((index, sections + following, sections + index))
    return trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=False)


def segmentation_fixture(np, trimesh):
    centres = (
        (0.0, 0.0, 0.0),
        (0.0, 150.0, 0.0),
        (0.0, -150.0, 0.0),
        (250.0, 180.0, 0.0),
    )
    vertices = []
    faces = []
    for centre_x, centre_y, centre_z in centres:
        start = len(vertices)
        vertices.extend(
            (
                (centre_x - 1.0, centre_y, centre_z - 1.0),
                (centre_x + 1.0, centre_y, centre_z - 1.0),
                (centre_x, centre_y, centre_z + 2.0),
            )
        )
        faces.append((start, start + 1, start + 2))
    return trimesh.Trimesh(
        vertices=np.asarray(vertices, dtype=np.float64),
        faces=np.asarray(faces, dtype=np.int64),
        process=False,
    )


def face_signatures(np, mesh) -> set[tuple[tuple[float, float, float], ...]]:
    signatures = set()
    vertices = np.asarray(mesh.vertices)
    for face in np.asarray(mesh.faces):
        triangle = tuple(sorted(tuple(float(value) for value in np.round(vertices[index], 6)) for index in face))
        signatures.add(triangle)
    return signatures


def run_json_script(arguments: list[str]) -> dict:
    environment = os.environ.copy()
    environment.update(
        {
            "PIP_NO_INDEX": "1",
            "NO_PROXY": "*",
            "no_proxy": "*",
        }
    )
    completed = subprocess.run(
        [sys.executable, *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return json.loads(completed.stdout)


def run_script_expect_failure(arguments: list[str], expected_message: str) -> None:
    completed = subprocess.run(
        [sys.executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PIP_NO_INDEX": "1", "NO_PROXY": "*", "no_proxy": "*"},
    )
    combined = completed.stdout + completed.stderr
    require(completed.returncode != 0, "invalid interface contract was accepted")
    require(expected_message in combined, f"unexpected validation failure: {combined}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def network_isolation_evidence() -> dict[str, object]:
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


def audit_bundled_pipeline_tree() -> dict[str, object]:
    scope = Path("/opt/3dprinting993")
    expected = {
        str(PREPARE_SCAN.relative_to(scope)),
        str(ANALYZE_BOUNDARIES.relative_to(scope)),
        str(SEGMENT_ENGINE.relative_to(scope)),
    }
    files = sorted(str(path.relative_to(scope)) for path in scope.rglob("*") if path.is_file())
    file_set = set(files)
    unexpected = sorted(file_set - expected)
    missing = sorted(expected - file_set)
    suffix_groups = {
        "forbidden_geometry_files": {".obj", ".ply", ".stl", ".3mf", ".step", ".stp", ".usd", ".usda", ".usdc", ".usdz"},
        "dataset_files": {".csv", ".parquet", ".h5", ".hdf5", ".npz"},
        "model_weight_files": {".bin", ".ckpt", ".onnx", ".pt", ".pth", ".safetensors"},
    }
    findings = {
        name: sorted(path for path in files if Path(path).suffix.lower() in suffixes)
        for name, suffixes in suffix_groups.items()
    }
    secret_named = sorted(
        path
        for path in files
        if Path(path).name.lower() == ".env"
        or Path(path).suffix.lower() in {".key", ".pem", ".p12", ".pfx"}
        or any(marker in Path(path).name.lower() for marker in ("credential", "secret", "token"))
    )
    require(not unexpected and not missing, f"unexpected application bundle: {unexpected}; missing: {missing}")
    require(not any(findings.values()) and not secret_named, "forbidden file found in application bundle")
    return {
        "scope": str(scope),
        "expected_files": sorted(expected),
        "unexpected_files": unexpected,
        "missing_files": missing,
        **findings,
        "secret_named_files": secret_named,
        "limitation": "filename and suffix audit of the application bundle only",
    }


def run_smoke() -> dict:
    require(sys.version_info[:2] == (3, 12), "Python 3.12 is required")
    require(platform.machine().lower() in {"amd64", "x86_64"}, "linux/amd64 is required")
    require(os.geteuid() != 0, "smoke must run as a non-root user")
    require(not Path("/dev/nvidia0").exists(), "a GPU device must not be exposed")
    network_evidence = network_isolation_evidence()
    for script in (PREPARE_SCAN, ANALYZE_BOUNDARIES, SEGMENT_ENGINE):
        require(script.is_file(), f"missing bundled pipeline script: {script}")

    versions = {name: importlib.metadata.version(name) for name in EXPECTED_PACKAGES}
    require(versions == EXPECTED_PACKAGES, f"unexpected dependency versions: {versions}")
    subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PIP_NO_INDEX": "1"},
    )

    import numpy as np
    import rtree  # noqa: F401 - import explicitement vérifié avant le calcul de proximité
    import trimesh

    prepare = load_module(PREPARE_SCAN)
    with tempfile.TemporaryDirectory(prefix="scan-mesh-f17-") as temporary:
        root = Path(temporary)

        cylinder = open_cylinder(np, trimesh)
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=20.0)
        sphere.apply_translation((0.0, 200.0, 0.0))
        compound = trimesh.util.concatenate((sphere, cylinder))
        labels, component_sizes = prepare.component_labels(compound)
        topology = prepare.topology(compound)
        require(len(component_sizes) == 2, "component_labels did not find two components")
        require(len(labels) == len(compound.vertices), "component label cardinality mismatch")
        require(topology["boundary_edges"] == 64, "unexpected compound boundary count")
        require(topology["non_manifold_edges"] == 0, "synthetic fixture is non-manifold")
        require(topology["watertight"] is False, "open synthetic fixture reported watertight")

        decimation_source = root / "decimation-source.ply"
        decimation_output = root / "decimation-output.ply"
        compound.export(decimation_source, file_type="ply", encoding="binary")
        prepare.simplify(decimation_source, decimation_output, 160)
        decimated = trimesh.load_mesh(decimation_output, process=False)
        require(0 < len(decimated.faces) < len(compound.faces), "real decimation did not reduce faces")
        deviation = prepare.deviation(compound, decimated)
        require(deviation["samples"] == 50_000, "deviation did not sample 50,000 points")
        for key in ("median_obj_units", "p95_obj_units", "max_obj_units"):
            require(np.isfinite(deviation[key]) and deviation[key] >= 0.0, f"invalid deviation {key}")

        boundary_source = root / "two-open-rims.ply"
        boundary_report_path = root / "boundary-report.json"
        cylinder.export(boundary_source, file_type="ply", encoding="binary")
        boundary_report = run_json_script(
            [str(ANALYZE_BOUNDARIES), str(boundary_source), str(boundary_report_path)]
        )
        require(boundary_report["boundary_edges"] == 64, "unexpected boundary edge count")
        require(boundary_report["boundary_components"] == 2, "expected two boundary loops")
        require(
            len(boundary_report["likely_circular_interfaces"]) == 2,
            "both synthetic circular boundary loops must pass screening",
        )

        segmentation_source = root / "segmentation-source.ply"
        interface_path = root / "synthetic-interfaces.json"
        segmentation_output = root / "segmentation-output"
        fixture = segmentation_fixture(np, trimesh)
        fixture.export(segmentation_source, file_type="ply", encoding="binary")
        synthetic_interfaces = {
            "centroid_scan_coordinates": [0.0, 0.0, 0.0],
            "frame_rows_longitudinal_bank_axis_vertical": [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            "banks": {
                "positive": [{"center_longitudinal_vertical": [0.0, 0.0]}],
                "negative": [{"center_longitudinal_vertical": [0.0, 0.0]}],
            },
        }
        interface_path.write_text(json.dumps(synthetic_interfaces, indent=2) + "\n")
        segmentation_report = run_json_script(
            [
                str(SEGMENT_ENGINE),
                str(segmentation_source),
                str(interface_path),
                str(segmentation_output),
                "--synthetic-fixture-mode",
            ]
        )
        validation = segmentation_report["interface_validation"]
        require(validation["mode"] == "synthetic_fixture", "synthetic mode was not reported")
        require(
            validation["provenance_hashes_matched_external_expectations"] is False,
            "synthetic hashes must not be reported as externally verified",
        )
        input_mesh = trimesh.load_mesh(segmentation_source, process=False)
        input_signatures = face_signatures(np, input_mesh)
        part_signatures = []
        for part in segmentation_report["parts"].values():
            require(part["triangles"] == 1, "each synthetic region must contain one face")
            require(part["watertight"] is False, "segmentation region must remain open")
            part_mesh = trimesh.load_mesh(part["path"], process=False)
            part_signatures.append(face_signatures(np, part_mesh))
        require(sum(len(item) for item in part_signatures) == len(input_signatures), "face loss detected")
        for index, signatures in enumerate(part_signatures):
            for other in part_signatures[index + 1 :]:
                require(signatures.isdisjoint(other), "overlapping segmentation regions detected")
        require(set().union(*part_signatures) == input_signatures, "segmentation does not conserve faces")

        invalid_finite = json.loads(json.dumps(synthetic_interfaces))
        invalid_finite["centroid_scan_coordinates"][0] = float("nan")
        invalid_finite_path = root / "invalid-finite.json"
        invalid_finite_path.write_text(json.dumps(invalid_finite) + "\n")
        run_script_expect_failure(
            [
                str(SEGMENT_ENGINE),
                str(segmentation_source),
                str(invalid_finite_path),
                str(root / "rejected-finite"),
                "--synthetic-fixture-mode",
            ],
            "must contain finite numbers",
        )

        invalid_direct = json.loads(json.dumps(synthetic_interfaces))
        invalid_direct["frame_rows_longitudinal_bank_axis_vertical"][2][2] = -1.0
        invalid_direct_path = root / "invalid-direct.json"
        invalid_direct_path.write_text(json.dumps(invalid_direct) + "\n")
        run_script_expect_failure(
            [
                str(SEGMENT_ENGINE),
                str(segmentation_source),
                str(invalid_direct_path),
                str(root / "rejected-direct"),
                "--synthetic-fixture-mode",
            ],
            "must be direct (determinant +1)",
        )

        invalid_count_path = root / "invalid-canonical-count.json"
        invalid_count_path.write_text(json.dumps(synthetic_interfaces) + "\n")
        run_script_expect_failure(
            [
                str(SEGMENT_ENGINE),
                str(segmentation_source),
                str(invalid_count_path),
                str(root / "rejected-count"),
                "--input-sha256",
                sha256(segmentation_source),
                "--interfaces-sha256",
                sha256(invalid_count_path),
            ],
            "must contain exactly six centres in canonical mode",
        )

        canonical_interfaces = json.loads(json.dumps(synthetic_interfaces))
        for bank in ("positive", "negative"):
            canonical_interfaces["banks"][bank] = [
                {"center_longitudinal_vertical": [float(index * 10), 0.0]}
                for index in range(6)
            ]
        invalid_hash_path = root / "invalid-canonical-hash.json"
        invalid_hash_path.write_text(json.dumps(canonical_interfaces) + "\n")
        run_script_expect_failure(
            [
                str(SEGMENT_ENGINE),
                str(segmentation_source),
                str(invalid_hash_path),
                str(root / "rejected-hash"),
                "--input-sha256",
                sha256(segmentation_source),
                "--interfaces-sha256",
                "0" * 64,
            ],
            "interfaces SHA-256 mismatch",
        )

    bundled_content_audit = audit_bundled_pipeline_tree()
    return {
        "status": "passed_synthetic_fixture_only",
        "offline": bool(network_evidence["verified"]),
        "network_isolation_evidence": network_evidence,
        "platform": "linux/amd64-cpu",
        "python": platform.python_version(),
        "non_root": True,
        "gpu": False,
        "packages": versions,
        "checks": {
            "component_labels_components": 2,
            "topology_boundary_edges": 64,
            "decimation_source_faces": int(len(compound.faces)),
            "decimation_output_faces": int(len(decimated.faces)),
            "deviation_samples": int(deviation["samples"]),
            "rtree_proximity_path": True,
            "boundary_loops": 2,
            "segmentation_input_faces": int(len(input_signatures)),
            "segmentation_output_faces": int(sum(len(item) for item in part_signatures)),
            "segmentation_overlap_faces": 0,
            "rejected_invalid_interface_contracts": 4,
        },
        "bundled_content_audit": bundled_content_audit,
        "release_gates": {
            "semantic_segmentation": False,
            "scan_identity_verified": False,
            "physical_scale_verified": False,
            "watertight_geometry": False,
            "cad_master": False,
            "cfd_ready": False,
            "physicsnemo_ready": False,
            "manufacturing_ready": False,
            "print_ready": False,
            "functional_engine": False,
            "cryptographic_signature_verified": False,
            "vast_launch_authorized": False,
        },
        "claim_scope": "synthetic fixtures validate software paths only",
    }


if __name__ == "__main__":
    print(json.dumps(run_smoke(), indent=2, sort_keys=True))
