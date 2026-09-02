"""Contrats expurgés et fixture synthétique du workpack F23."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-917-engine/source/build_boundary_review_workpack_f23.py"
CONTRACT = ROOT / "twins/reference-917-engine/boundary-review-workpack-f23.json"
DOC = ROOT / "docs/917_BOUNDARY_REVIEW_WORKPACK_F23.md"


def load_module():
    spec = importlib.util.spec_from_file_location("f23_workpack", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F23 = load_module()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_component(
    rank: int, review_class: str, size: float, point_count: int = 16
) -> dict:
    candidate = review_class == "candidate"
    return {
        "boundary_edge_count": point_count,
        "boundary_vertex_count": point_count,
        "minimum_source_vertex_index_1_based": rank * point_count + 1,
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


def write_fixture(
    directory: Path, *, points_per_component: int = 16
) -> tuple[Path, str, Path, str]:
    components = [
        synthetic_component(
            rank,
            "candidate" if rank <= 3 else "unclassified",
            float(rank),
            points_per_component,
        )
        for rank in range(1, 10)
    ]
    ply = directory / "boundary-components-f18.ply"
    records = []
    for component in components:
        rank = component["component_rank"]
        size = float(rank)
        for point_index in range(points_per_component):
            side = point_index % 4
            layer = point_index // 4
            x = size if side in (1, 2) else 0.0
            y = size if side in (2, 3) else 0.0
            z = size * 0.01 * layer
            records.append(
                F23.PLY_RECORD.pack(
                    x,
                    y,
                    z,
                    30,
                    180,
                    220,
                    255,
                    rank,
                    int(component["review_class"] == "candidate"),
                )
            )
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        "comment synthetic F23 fixture\n"
        f"element vertex {len(records)}\n"
        + "\n".join(F23.PLY_PROPERTIES)
        + "\nend_header\n"
    ).encode("ascii")
    ply.write_bytes(header + b"".join(records))
    ply_hash = digest(ply)
    report = {
        "schema": "porsche-917-boundary-human-review/f18-v1",
        "phase": "F18",
        "status": "complete_geometric_inventory_pending_human_review",
        "source": {"mode": "synthetic_self_test"},
        "coordinate_policy": {
            "reported_units": "input coordinate units",
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
        "release_gates": dict(F23.RELEASE_GATES),
        "limitations": [],
    }
    report_path = directory / "boundary-review-f18.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path, digest(report_path), ply, ply_hash


def generation_command(
    report: Path, report_hash: str, ply: Path, ply_hash: str, output: Path
) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT),
        "--report",
        str(report),
        "--report-sha256",
        report_hash,
        "--ply",
        str(ply),
        "--ply-sha256",
        ply_hash,
        "--expected-component-count",
        "9",
        "--expected-candidate-count",
        "3",
        "--secondary-count",
        "3",
        "--output",
        str(output),
    ]


def validation_command(
    report: Path,
    report_hash: str,
    ply: Path,
    ply_hash: str,
    review: Path,
) -> list[str]:
    command = generation_command(report, report_hash, ply, ply_hash, Path("unused"))
    output_index = command.index("--output")
    del command[output_index : output_index + 2]
    command.extend(["--validate-review-file", str(review)])
    return command


class BoundaryReviewWorkpackF23Tests(unittest.TestCase):
    def test_tracked_contract_is_redacted_and_fail_closed(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["phase"], "F23")
        self.assertEqual(contract["selection_contract"]["primary"]["count"], 19)
        self.assertEqual(contract["selection_contract"]["secondary"]["count"], 19)
        self.assertFalse(contract["selection_contract"]["secondary"]["circularity_used"])
        self.assertEqual(
            contract["review_contract"]["allowed_states"],
            ["artifact", "physical_boundary", "undetermined"],
        )
        self.assertTrue(all(value is False for value in contract["release_gates"].values()))
        tracked = CONTRACT.read_text(encoding="utf-8")
        for forbidden in (
            "boundary_0001",
            "centroid_obj_units",
            "bounds_min_obj_units",
            "normal_unoriented_scan_coordinates",
            '"vertices": [',
        ):
            self.assertNotIn(forbidden, tracked)

    def test_documentation_explains_control_cohort_locality_and_gates(self):
        document = DOC.read_text(encoding="utf-8")
        for fragment in (
            "```mermaid",
            "19 candidats circulaires",
            "19 grandes frontières non classées",
            "artifact",
            "physical_boundary",
            "undetermined",
            "hors Git",
            "SHA-256",
            "PhysicsNeMo",
            "boundary-review-atlas-f23.svg",
            "--validate-review-file",
        ):
            self.assertIn(fragment, document)

    def test_fixture_generates_two_deterministic_cohorts_and_three_formats(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            report, report_hash, ply, ply_hash = write_fixture(root)
            first = root / "first"
            second = root / "second"
            completed = subprocess.run(
                generation_command(report, report_hash, ply, ply_hash, first),
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertIn('"selected_count": 6', completed.stdout)
            subprocess.run(
                generation_command(report, report_hash, ply, ply_hash, second),
                check=True,
                text=True,
                capture_output=True,
            )
            workpack = json.loads(
                (first / F23.REPORT_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(workpack["summary"]["primary_circular_candidate_count"], 3)
            self.assertEqual(workpack["summary"]["secondary_large_unclassified_count"], 3)
            self.assertEqual(workpack["summary"]["confirmed_interface_count"], 0)
            primary = [
                item["component_rank"]
                for item in workpack["items"]
                if item["selection_tier"] == "primary_circular_candidate"
            ]
            secondary = [
                item["component_rank"]
                for item in workpack["items"]
                if item["selection_tier"] == "secondary_large_unclassified"
            ]
            self.assertEqual(primary, [3, 2, 1])
            self.assertEqual(secondary, [9, 8, 7])
            for item in workpack["items"]:
                self.assertEqual(item["review"]["state"], "undetermined")
                self.assertEqual(item["review"]["evidence"], [])
                self.assertFalse(item["semantic_interface_confirmed"])
                self.assertFalse(item["release_authority"])
            self.assertTrue(all(value is False for value in workpack["release_gates"].values()))

            with (first / F23.CSV_NAME).open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 6)
            self.assertTrue(all(row["review_state"] == "undetermined" for row in rows))
            svg = (first / F23.SVG_NAME).read_text(encoding="utf-8")
            for label in ("XY scan", "XZ scan", "YZ scan", "aucune interface confirmée"):
                self.assertIn(label, svg)
            first_ids = [item["component_id"] for item in workpack["items"]]
            second_document = json.loads(
                (second / F23.REPORT_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(first_ids, [item["component_id"] for item in second_document["items"]])
            self.assertEqual(
                (first / F23.REPORT_NAME).read_bytes(),
                (second / F23.REPORT_NAME).read_bytes(),
            )
            self.assertEqual(
                (first / F23.CSV_NAME).read_bytes(), (second / F23.CSV_NAME).read_bytes()
            )
            self.assertEqual(
                (first / F23.SVG_NAME).read_bytes(), (second / F23.SVG_NAME).read_bytes()
            )

    def test_hash_and_existing_output_guards_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            report, report_hash, ply, ply_hash = write_fixture(root)
            output = root / "output"
            command = generation_command(report, report_hash, ply, ply_hash, output)
            subprocess.run(command, check=True, text=True, capture_output=True)
            repeated = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("output already exists", repeated.stderr)
            wrong_hash = list(command)
            wrong_hash[wrong_hash.index("--report-sha256") + 1] = "0" * 64
            mismatch = subprocess.run(wrong_hash, text=True, capture_output=True)
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("report SHA-256 mismatch", mismatch.stderr)

    def test_decided_review_requires_reviewer_evidence_and_closed_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            report, report_hash, ply, ply_hash = write_fixture(root)
            output = root / "output"
            subprocess.run(
                generation_command(report, report_hash, ply, ply_hash, output),
                check=True,
                text=True,
                capture_output=True,
            )
            review_path = output / F23.REPORT_NAME
            document = json.loads(review_path.read_text(encoding="utf-8"))
            review = document["items"][0]["review"]
            review["state"] = "artifact"
            review["reviewer"] = {
                "name": "Synthetic Reviewer",
                "organization": None,
                "reviewed_at_utc": "2026-09-02T12:00:00Z",
            }
            review["evidence"] = [
                {
                    "kind": "scan_observation",
                    "reference": "synthetic-view-01",
                    "sha256": None,
                    "notes": "fixture only",
                }
            ]
            review_path.write_text(json.dumps(document), encoding="utf-8")
            valid = subprocess.run(
                validation_command(report, report_hash, ply, ply_hash, review_path),
                text=True,
                capture_output=True,
            )
            self.assertEqual(valid.returncode, 0, valid.stderr)
            document["items"][0]["review"]["evidence"] = []
            review_path.write_text(json.dumps(document), encoding="utf-8")
            invalid = subprocess.run(
                validation_command(report, report_hash, ply, ply_hash, review_path),
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("requires at least one evidence", invalid.stderr)
            document["items"][0]["review"]["evidence"] = review["evidence"]
            document["release_gates"]["cad_reconstruction_released"] = True
            review_path.write_text(json.dumps(document), encoding="utf-8")
            gate = subprocess.run(
                validation_command(report, report_hash, ply, ply_hash, review_path),
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(gate.returncode, 0)
            self.assertIn("release gates", gate.stderr)

    def test_review_validation_is_source_bound_and_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            report, report_hash, ply, ply_hash = write_fixture(root)
            output = root / "output"
            subprocess.run(
                generation_command(report, report_hash, ply, ply_hash, output),
                check=True,
                text=True,
                capture_output=True,
            )
            review_path = output / F23.REPORT_NAME
            original = review_path.read_text(encoding="utf-8")

            missing_sources = subprocess.run(
                [sys.executable, str(SCRIPT), "--validate-review-file", str(review_path)],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(missing_sources.returncode, 0)
            self.assertIn("--report is required", missing_sources.stderr)

            document = json.loads(original)
            document["items"][0]["component_id"] = "boundary_9999"
            review_path.write_text(json.dumps(document), encoding="utf-8")
            forged = subprocess.run(
                validation_command(report, report_hash, ply, ply_hash, review_path),
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(forged.returncode, 0)
            self.assertIn("immutable content differs", forged.stderr)

            duplicated = original.replace(
                '"phase": "F23",',
                '"phase": "ignored",\n  "phase": "F23",',
                1,
            )
            review_path.write_text(duplicated, encoding="utf-8")
            duplicate = subprocess.run(
                validation_command(report, report_hash, ply, ply_hash, review_path),
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn("duplicate JSON object keys", duplicate.stderr)

    def test_generation_rejects_unsafe_ids_missing_gates_and_output_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            unsafe_root = root / "unsafe-id"
            unsafe_root.mkdir()
            report, _report_hash, ply, ply_hash = write_fixture(unsafe_root)
            document = json.loads(report.read_text(encoding="utf-8"))
            document["components"][0]["component_id"] = "=1+1"
            report.write_text(json.dumps(document), encoding="utf-8")
            unsafe = subprocess.run(
                generation_command(report, digest(report), ply, ply_hash, unsafe_root / "out"),
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(unsafe.returncode, 0)
            self.assertIn("boundary_####", unsafe.stderr)

            gate_root = root / "missing-gate"
            gate_root.mkdir()
            report, _report_hash, ply, ply_hash = write_fixture(gate_root)
            document = json.loads(report.read_text(encoding="utf-8"))
            del document["release_gates"]["engine_start_released"]
            report.write_text(json.dumps(document), encoding="utf-8")
            missing_gate = subprocess.run(
                generation_command(report, digest(report), ply, ply_hash, gate_root / "out"),
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(missing_gate.returncode, 0)
            self.assertIn("exactly match", missing_gate.stderr)

            link_root = root / "symlink"
            link_root.mkdir()
            report, report_hash, ply, ply_hash = write_fixture(link_root)
            output = link_root / "out"
            output.mkdir()
            victim = link_root / "victim.json"
            (output / F23.REPORT_NAME).symlink_to(victim)
            linked = subprocess.run(
                generation_command(report, report_hash, ply, ply_hash, output),
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(linked.returncode, 0)
            self.assertIn("overwriting is forbidden", linked.stderr)
            self.assertFalse(victim.exists())

    def test_large_selected_components_are_sampled_while_streaming(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            report, report_hash, ply, ply_hash = write_fixture(
                root, points_per_component=1000
            )
            output = root / "output"
            subprocess.run(
                generation_command(report, report_hash, ply, ply_hash, output),
                check=True,
                text=True,
                capture_output=True,
            )
            workpack = json.loads((output / F23.REPORT_NAME).read_text(encoding="utf-8"))
            self.assertTrue(
                all(
                    0 < item["rendered_point_count"] <= F23.MAX_RENDER_POINTS_PER_COMPONENT
                    for item in workpack["items"]
                )
            )

    def test_ply_header_lines_and_coordinates_are_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            report_path, _report_hash, ply_path, _ply_hash = write_fixture(root)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            components = F23.validate_f18_report(report, 3, 9)
            selected = F23.select_review_cohorts(components, 3)
            selected_ranks = {
                item["component"]["component_rank"] for item in selected
            }

            long_header = ply_path.read_bytes().replace(
                b"comment synthetic F23 fixture\n",
                b"comment " + b"x" * F23.MAX_PLY_HEADER_LINE_BYTES + b"\n",
                1,
            )
            report["visualization"]["sha256"] = hashlib.sha256(long_header).hexdigest()
            report["visualization"]["bytes"] = len(long_header)
            with self.assertRaisesRegex(F23.WorkpackError, "header line"):
                F23.read_selected_ply_points(
                    long_header,
                    report["visualization"]["sha256"],
                    report,
                    components,
                    selected_ranks,
                )

            coordinate_payload = bytearray(ply_path.read_bytes())
            payload_offset = coordinate_payload.index(b"end_header\n") + len(b"end_header\n")
            record = list(F23.PLY_RECORD.unpack_from(coordinate_payload, payload_offset))
            record[0] = F23.MAX_ABS_COORDINATE * 2.0
            F23.PLY_RECORD.pack_into(coordinate_payload, payload_offset, *record)
            coordinate_bytes = bytes(coordinate_payload)
            coordinate_hash = hashlib.sha256(coordinate_bytes).hexdigest()
            report["visualization"]["sha256"] = coordinate_hash
            report["visualization"]["bytes"] = len(coordinate_bytes)
            with self.assertRaisesRegex(F23.WorkpackError, "out-of-range coordinates"):
                F23.read_selected_ply_points(
                    coordinate_bytes,
                    coordinate_hash,
                    report,
                    components,
                    selected_ranks,
                )


if __name__ == "__main__":
    unittest.main()
