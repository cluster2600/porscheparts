"""Contrats du générateur local de contexte topologique F26."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any
import unittest
import xml.etree.ElementTree as ElementTree

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "twins/reference-917-engine/source/build_topology_context_f26.py"
F18_PIPELINE = ROOT / "twins/reference-917-engine/source/review_boundary_components_f18.py"
CONTRACT = ROOT / "twins/reference-917-engine/topology-context-contract-f26.json"
DOC = ROOT / "docs/917_TOPOLOGY_CONTEXT_F26.md"

NUMPY_AVAILABLE = importlib.util.find_spec("numpy") is not None
if NUMPY_AVAILABLE:
    import numpy as np
else:
    np = None

requires_numpy = unittest.skipUnless(
    NUMPY_AVAILABLE,
    "les tests géométriques F26 s'exécutent dans l'image NumPy épinglée",
)


def load_module(path: Path, name: str) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


F26 = load_module(PIPELINE, "build_topology_context_f26_test")
F18 = load_module(F18_PIPELINE, "review_boundary_components_f18_test_f26")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_fixture(root: Path) -> tuple[Path, Path, str, str]:
    segment_count, level_count = 16, 7
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    lines = ["# synthetic F26 open cylinder"]
    for level in range(level_count):
        z = level * 0.35
        radius = 1.0 + 0.04 * math.sin(level * 0.7)
        for segment in range(segment_count):
            angle = 2.0 * math.pi * segment / segment_count
            vertex = [radius * math.cos(angle), radius * math.sin(angle), z]
            vertices.append(vertex)
            lines.append(f"v {vertex[0]:.12f} {vertex[1]:.12f} {vertex[2]:.12f}")
    for level in range(level_count - 1):
        for segment in range(segment_count):
            following = (segment + 1) % segment_count
            ll = level * segment_count + segment
            lr = level * segment_count + following
            ul = (level + 1) * segment_count + segment
            ur = (level + 1) * segment_count + following
            faces.extend(([ll, lr, ur], [ll, ur, ul]))
            lines.extend((f"f {ll + 1} {lr + 1} {ur + 1}", f"f {ll + 1} {ur + 1} {ul + 1}"))
    mesh = root / "fixture.obj"
    mesh.write_text("\n".join(lines) + "\n", encoding="ascii")
    vertices_array = np.asarray(vertices, dtype=np.float64)
    faces_array = np.asarray(faces, dtype=np.int64)
    analysis = F18.analyze_boundary_components(vertices_array, faces_array, np)
    if len(analysis["components"]) != 2:
        raise AssertionError("fixture must expose exactly two boundaries")
    ply = root / "fixture.ply"
    F18.write_colored_ply(
        ply,
        vertices_array[analysis["active_vertices"]],
        analysis["stable_ranks"],
        analysis["candidate_flags"],
        np,
    )
    mesh_hash = sha256(mesh)
    report = F18.build_report(
        analysis,
        {
            "mode": "synthetic_unit_test",
            "input_path": None,
            "actual_sha256": mesh_hash,
            "expected_sha256": mesh_hash,
            "provenance_hash_matched": True,
            "raw_geometry_embedded_in_report": False,
        },
        ply,
    )
    report_path = root / "fixture-f18.json"
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return mesh, report_path, mesh_hash, sha256(report_path)


def generated_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class TopologyContextF26Tests(unittest.TestCase):
    def setUp(self):
        self.contract_payload = CONTRACT.read_bytes()
        self.contract = F26._load_json(self.contract_payload, label="contract")
        self.contract_hash = hashlib.sha256(self.contract_payload).hexdigest()

    def build(self, root: Path, output_name: str = "output") -> tuple[Path, dict[str, Any]]:
        mesh, report, mesh_hash, report_hash = write_fixture(root)
        output = root / output_name
        summary = F26.build_context(
            contract=self.contract,
            contract_sha256=self.contract_hash,
            report=F26._load_json(report.read_bytes(), label="F18 report"),
            report_sha256=report_hash,
            report_name=report.name,
            mesh_path=mesh,
            mesh_sha256=mesh_hash,
            expected_components=2,
            batch_size=1,
            fixture_mode=True,
            output=output,
            np=np,
        )
        return output, summary

    def test_contract_is_fail_closed_and_has_exact_views_and_two_rings(self):
        F26._validate_contract(self.contract, expected_components=2, fixture_mode=True)
        self.assertEqual(self.contract["phase"], "F26")
        self.assertEqual(self.contract["topology_context"]["topological_ring_count"], 2)
        self.assertEqual(
            self.contract["visualization"]["canonical_orthographic_views"],
            list(F26.CANONICAL_VIEWS),
        )
        self.assertEqual(self.contract["visualization"]["maximum_components_per_batch"], 48)
        self.assertFalse(self.contract["review_policy"]["automatic_semantic_classification"])
        self.assertFalse(self.contract["review_policy"]["automatic_interface_confirmation"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        self.assertIsNone(self.contract["image"]["immutable_digest"])
        self.assertIn("not_authorized_for_canonical_scan", self.contract["image"]["verification_status"])
        with self.assertRaisesRegex(F26.ContextError, "exactly 944"):
            F26._validate_contract(self.contract, expected_components=2, fixture_mode=False)
        F26._validate_contract(self.contract, expected_components=944, fixture_mode=False)

    @requires_numpy
    def test_synthetic_pipeline_outputs_hashed_deterministic_bounded_workpacks(self):
        with tempfile.TemporaryDirectory(prefix="f26-test-") as temporary:
            root = Path(temporary)
            mesh, report, mesh_hash, report_hash = write_fixture(root)

            def build(output: Path) -> dict[str, Any]:
                return F26.build_context(
                    contract=self.contract,
                    contract_sha256=self.contract_hash,
                    report=F26._load_json(report.read_bytes(), label="F18 report"),
                    report_sha256=report_hash,
                    report_name=report.name,
                    mesh_path=mesh,
                    mesh_sha256=mesh_hash,
                    expected_components=2,
                    batch_size=1,
                    fixture_mode=True,
                    output=output,
                    np=np,
                )

            first, second = root / "first", root / "second"
            summary = build(first)
            build(second)
            self.assertEqual(generated_files(first), generated_files(second))
            self.assertEqual(summary["component_count"], 2)
            self.assertEqual(summary["batch_count"], 2)
            self.assertEqual(summary["maximum_components_per_batch"], 1)
            self.assertEqual(summary["confirmed_interface_count"], 0)
            manifest = json.loads((first / F26.MANIFEST_NAME).read_text(encoding="utf-8"))
            self.assertEqual(manifest["topology_policy"]["topological_ring_count"], 2)
            self.assertEqual(len(manifest["batches"]), 2)
            self.assertTrue(all(batch["component_count"] == 1 for batch in manifest["batches"]))
            self.assertTrue(all(batch["component_count"] <= 48 for batch in manifest["batches"]))
            self.assertTrue(manifest["hash_coverage"]["every_component_json_svg_and_inventory_csv_hashed"])
            self.assertTrue(all(value is False for value in manifest["release_gates"].values()))
            self.assertEqual(manifest["source_binding"]["f18_report_name"], report.name)
            self.assertLessEqual(
                manifest["output_bounds"]["payload_bytes_excluding_root_manifest"],
                manifest["output_bounds"]["maximum_total_output_bytes"],
            )
            for artifact in manifest["artifacts"]:
                payload = (first / artifact["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), artifact["sha256"])
                self.assertEqual(len(payload), artifact["bytes"])
            with (first / F26.INVENTORY_NAME).open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 2)
            for row in rows:
                self.assertEqual(row["review_state"], "undetermined")
                self.assertEqual(row["semantic_interface_confirmed"], "false")
                self.assertEqual(row["release_authority"], "false")
                self.assertGreater(int(row["incident_face_count"]), 0)
                self.assertGreater(int(row["ring_1_face_count"]), 0)
                self.assertGreater(int(row["ring_2_face_count"]), 0)

    @requires_numpy
    def test_each_svg_has_four_canonical_orthographic_views_and_global_locators(self):
        with tempfile.TemporaryDirectory(prefix="f26-svg-") as temporary:
            output, _ = self.build(Path(temporary))
            paths = sorted(output.glob("batch_*/*.svg"))
            self.assertEqual(len(paths), 2)
            for path in paths:
                text = path.read_text(encoding="utf-8")
                self.assertTrue(ElementTree.fromstring(text).tag.endswith("svg"))
                self.assertEqual(text.count('class="orthographic-view"'), 4)
                self.assertEqual(text.count('class="global-locator"'), 4)
                for name in F26.CANONICAL_VIEWS:
                    self.assertIn(f'data-view="{name}"', text)
                self.assertIn("axes scan non qualifiés", text)
                self.assertIn("Aucune interface confirmée", text)
                namespace = {"svg": "http://www.w3.org/2000/svg"}
                root_element = ElementTree.fromstring(text)
                locators = [
                    item
                    for item in root_element.findall(".//svg:g", namespace)
                    if item.attrib.get("class") == "global-locator"
                ]
                self.assertEqual(len(locators), 4)
                for locator in locators:
                    rectangles = locator.findall("svg:rect", namespace)
                    self.assertEqual(len(rectangles), 2)
                    outer, inner = rectangles
                    ox, oy = float(outer.attrib["x"]), float(outer.attrib["y"])
                    ow, oh = float(outer.attrib["width"]), float(outer.attrib["height"])
                    ix, iy = float(inner.attrib["x"]), float(inner.attrib["y"])
                    iw, ih = float(inner.attrib["width"]), float(inner.attrib["height"])
                    self.assertTrue(all(math.isfinite(value) for value in (ox, oy, ow, oh, ix, iy, iw, ih)))
                    self.assertGreaterEqual(ix, ox)
                    self.assertGreaterEqual(iy, oy)
                    self.assertLessEqual(ix + iw, ox + ow + 1e-6)
                    self.assertLessEqual(iy + ih, oy + oh + 1e-6)

    def test_duplicate_json_and_resource_bounds_fail_closed_without_numpy(self):
        with self.assertRaisesRegex(F26.ContextError, "duplicate JSON key"):
            F26._load_json(b'{"phase":"F26","phase":"unsafe"}', label="contract")
        with self.assertRaisesRegex(F26.ContextError, "non-finite JSON constant"):
            F26._load_json(b'{"unsafe":NaN}', label="contract")
        with self.assertRaisesRegex(F26.ContextError, "context face count"):
            F26._require_bounded_context_face_count(F26.MAX_CONTEXT_FACES_PER_COMPONENT + 1)
        with self.assertRaisesRegex(F26.ContextError, "total output byte bound"):
            F26._reserve_output_bytes(F26.MAX_TOTAL_OUTPUT_BYTES, 1, label="test")

    @requires_numpy
    def test_wrong_hash_and_existing_output_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="f26-fail-") as temporary:
            root = Path(temporary)
            mesh, report, mesh_hash, report_hash = write_fixture(root)
            with self.assertRaisesRegex(F26.ContextError, "SHA-256 mismatch"):
                F26._read_small_bound_file(report, "0" * 64, maximum_bytes=F26.MAX_REPORT_BYTES, label="F18 report")
            output = root / "existing"
            output.mkdir()
            with self.assertRaisesRegex(F26.ContextError, "output already exists"):
                F26.build_context(
                    contract=self.contract,
                    contract_sha256=self.contract_hash,
                    report=F26._load_json(report.read_bytes(), label="F18 report"),
                    report_sha256=report_hash,
                    report_name=report.name,
                    mesh_path=mesh,
                    mesh_sha256=mesh_hash,
                    expected_components=2,
                    batch_size=1,
                    fixture_mode=True,
                    output=output,
                    np=np,
                )

    def test_exclusive_publication_never_replaces_a_racing_destination(self):
        with tempfile.TemporaryDirectory(prefix="f26-publish-") as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / F26.MANIFEST_NAME).write_text("{}\n", encoding="utf-8")
            destination = root / "destination"
            parent_descriptor, parent_identity = F26._open_private_output_parent(destination)
            source_identity = F26._directory_identity(source)
            destination.mkdir()
            marker = destination / "belongs-to-other-writer.txt"
            marker.write_text("preserve\n", encoding="utf-8")
            try:
                with self.assertRaisesRegex(F26.ContextError, "refusing to replace"):
                    F26._publish_directory_exclusive(
                        source,
                        destination,
                        temporary_identity=source_identity,
                        parent_descriptor=parent_descriptor,
                        parent_identity=parent_identity,
                    )
            finally:
                import os
                os.close(parent_descriptor)
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve\n")

    @requires_numpy
    def test_f18_source_binding_requires_both_hashes_and_explicit_custody_flags(self):
        with tempfile.TemporaryDirectory(prefix="f26-source-") as temporary:
            root = Path(temporary)
            mesh, report_path, mesh_hash, _ = write_fixture(root)
            del mesh
            baseline = F26._load_json(report_path.read_bytes(), label="F18 report")
            F26._validate_f18_report(baseline, mesh_hash, 2, fixture_mode=True)
            mutations = (
                ("actual_sha256", "0" * 64, "does not bind"),
                ("expected_sha256", "0" * 64, "expected SHA-256"),
                ("provenance_hash_matched", False, "provenance hash"),
                ("raw_geometry_embedded_in_report", True, "exclude embedded raw geometry"),
            )
            for field, value, message in mutations:
                changed = json.loads(json.dumps(baseline))
                changed["source"][field] = value
                with self.subTest(field=field):
                    with self.assertRaisesRegex(F26.ContextError, message):
                        F26._validate_f18_report(changed, mesh_hash, 2, fixture_mode=True)

    def test_private_parent_and_guarded_cleanup_reject_replacement(self):
        with tempfile.TemporaryDirectory(prefix="f26-parent-") as temporary:
            root = Path(temporary)
            public_parent = root / "public"
            public_parent.mkdir(mode=0o755)
            os.chmod(public_parent, 0o755)
            with self.assertRaisesRegex(F26.ContextError, "mode 0700"):
                F26._open_private_output_parent(public_parent / "output")

            output = root / "output"
            descriptor, parent_identity = F26._open_private_output_parent(output)
            guarded, guarded_identity = F26._create_private_temporary_sibling(
                output,
                parent_descriptor=descriptor,
                parent_identity=parent_identity,
            )
            displaced = root / "displaced"
            guarded.rename(displaced)
            guarded.mkdir(mode=0o700)
            try:
                with self.assertRaisesRegex(F26.ContextError, "replaced directory"):
                    F26._cleanup_guarded_directory(
                        guarded,
                        expected_identity=guarded_identity,
                        parent_descriptor=descriptor,
                        parent_identity=parent_identity,
                    )
                self.assertTrue(guarded.is_dir())
                self.assertTrue(displaced.is_dir())
            finally:
                os.close(descriptor)

    @requires_numpy
    def test_obj_line_and_svg_estimate_are_bounded_before_construction(self):
        with tempfile.TemporaryDirectory(prefix="f26-bounds-") as temporary:
            root = Path(temporary)
            mesh = root / "long-line.obj"
            mesh.write_bytes(b"#" + b"x" * F26.MAX_OBJ_LINE_BYTES + b"\n")
            with self.assertRaisesRegex(F26.ContextError, "OBJ line exceeds"):
                F26._load_mesh(mesh, sha256(mesh), np)
            estimate = F26._estimate_svg_bytes(100, 20)
            self.assertGreater(estimate, 0)
            with self.assertRaisesRegex(F26.ContextError, "context face count"):
                F26._estimate_svg_bytes(F26.MAX_CONTEXT_FACES_PER_COMPONENT + 1, 1)

    @requires_numpy
    def test_synthetic_face_layer_ids_and_non_manifold_rejection(self):
        with tempfile.TemporaryDirectory(prefix="f26-layers-") as temporary:
            root = Path(temporary)
            mesh, _, mesh_hash, _ = write_fixture(root)
            vertices, faces, _ = F26._load_mesh(mesh, mesh_hash, np)
            analysis = F18.analyze_boundary_components(vertices, faces, np)
            boundary_edges, owners, neighbours = F26._build_face_adjacency(faces, np)
            ranks = np.zeros(len(vertices), dtype=np.int64)
            ranks[analysis["active_vertices"]] = analysis["stable_ranks"]
            edge_ranks = ranks[boundary_edges[:, 0]]
            _, incident_1, ring_1_1, ring_2_1 = F26._component_topology_layers(
                1, boundary_edges, owners, edge_ranks, neighbours, np
            )
            _, incident_2, ring_1_2, ring_2_2 = F26._component_topology_layers(
                2, boundary_edges, owners, edge_ranks, neighbours, np
            )
            np.testing.assert_array_equal(incident_1, np.arange(0, 32, 2))
            np.testing.assert_array_equal(ring_1_1, np.arange(1, 32, 2))
            np.testing.assert_array_equal(ring_2_1, np.arange(32, 64, 2))
            np.testing.assert_array_equal(incident_2, np.arange(161, 192, 2))
            np.testing.assert_array_equal(ring_1_2, np.arange(160, 192, 2))
            np.testing.assert_array_equal(ring_2_2, np.arange(129, 160, 2))

            non_manifold_faces = np.asarray(
                [[0, 1, 2], [1, 0, 3], [0, 1, 4]],
                dtype=np.int64,
            )
            with self.assertRaisesRegex(F26.ContextError, "non-manifold"):
                F26._build_face_adjacency(non_manifold_faces, np)

    def test_documentation_keeps_image_and_physical_authority_separate(self):
        document = DOC.read_text(encoding="utf-8").lower()
        for fragment in (
            "exactement deux",
            "quatre vues orthographiques",
            "locator global",
            "48 composantes par lot",
            "20 lots",
            "linux/amd64",
            "numpy 2.2.6",
            "non-root",
            "digest public immuable",
            "lock f26",
            "scan canonique ne doit pas être monté",
            "ne prouve ni l'identité",
            "physicsnemo",
            "fabrication",
            "mermaid",
        ):
            self.assertIn(fragment, document)


if __name__ == "__main__":
    unittest.main()
