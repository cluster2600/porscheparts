import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-917-engine/source/build_scan_segmentation_f15.py"
CONTRACT = ROOT / "twins/reference-917-engine/scan-segmentation-f15.json"


def load_module():
    spec = importlib.util.spec_from_file_location("scan_segmentation_917_f15", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_obj(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def mixed_fixture() -> str:
    return """
    # Two topological components: one open square and one closed tetrahedron.
    mtllib engine.mtl
    o crankcase_candidate
    g left_bank scan_region
    usemtl aluminium_candidate
    v 0 0 0
    v 1 0 0
    v 1 1 0
    v 0 1 0
    v 2 0 0
    v 3 0 0
    v 2 1 0
    v 2 0 1
    f 1 2 3
    f 1 3 4
    o detached_candidate
    g hardware_candidate
    usemtl steel_candidate
    f 5 7 6
    f 5 6 8
    f 6 7 8
    f 7 5 8
    """


class ScanSegmentation917F15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def evaluate_fixture(self, obj_text: str):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        source = root / "fixture.obj"
        output = root / "output"
        write_obj(source, obj_text)
        report = self.module.evaluate(
            CONTRACT, source, output, synthetic_fixture_mode=True
        )
        return temporary, source, output, report

    def test_two_components_declarations_bbox_and_boundaries(self):
        temporary, _source, _output, report = self.evaluate_fixture(mixed_fixture())
        self.addCleanup(temporary.cleanup)

        self.assertEqual(report["report_status"], "passed_synthetic_fixture_only")
        self.assertEqual(report["format_inventory"]["vertices"], 8)
        self.assertEqual(report["format_inventory"]["polygon_faces"], 6)
        self.assertEqual(report["format_inventory"]["triangle_faces"], 6)
        self.assertEqual(report["topology"]["surface_component_count"], 2)
        self.assertEqual(report["topology"]["unique_edges"], 11)
        self.assertEqual(report["topology"]["edge_occurrences"], 18)
        self.assertEqual(report["topology"]["boundary_edges"], 4)
        self.assertEqual(report["topology"]["non_manifold_edges"], 0)
        self.assertEqual(report["topology"]["boundary_component_count"], 1)
        self.assertEqual(report["topology"]["closed_boundary_loop_candidate_count"], 1)
        self.assertFalse(report["topology"]["watertight"])
        self.assertEqual(
            report["raw_coordinate_metrology"]["bounds_min_obj_units"], [0.0, 0.0, 0.0]
        )
        self.assertEqual(
            report["raw_coordinate_metrology"]["bounds_max_obj_units"], [3.0, 1.0, 1.0]
        )
        self.assertFalse(report["raw_coordinate_metrology"]["units_confirmed"])
        self.assertFalse(report["raw_coordinate_metrology"]["metric_conversion_applied"])

        objects = {
            item["name"]: item["face_statement_count"]
            for item in report["declaration_inventory"]["objects"]
        }
        materials = {
            item["name"]: item["face_statement_count"]
            for item in report["declaration_inventory"]["materials"]
        }
        self.assertEqual(objects, {"crankcase_candidate": 2, "detached_candidate": 4})
        self.assertEqual(materials, {"aluminium_candidate": 2, "steel_candidate": 4})

    def test_closed_tetrahedron_is_watertight(self):
        temporary, _source, _output, report = self.evaluate_fixture(
            """
            v 0 0 0
            v 1 0 0
            v 0 1 0
            v 0 0 1
            f 1 3 2
            f 1 2 4
            f 2 3 4
            f 3 1 4
            """
        )
        self.addCleanup(temporary.cleanup)

        self.assertEqual(report["topology"]["surface_component_count"], 1)
        self.assertEqual(report["topology"]["boundary_edges"], 0)
        self.assertEqual(report["topology"]["non_manifold_edges"], 0)
        self.assertTrue(report["topology"]["watertight"])

    def test_negative_indices_and_polygon_face_are_supported(self):
        temporary, _source, _output, report = self.evaluate_fixture(
            """
            v 0 0 0
            v 1 0 0
            v 1 1 0
            v 0 1 0
            f -4 -3 -2 -1
            """
        )
        self.addCleanup(temporary.cleanup)

        self.assertEqual(report["report_status"], "passed_synthetic_fixture_only")
        self.assertEqual(report["format_inventory"]["face_arity_histogram"], {"4": 1})
        self.assertEqual(report["format_inventory"]["triangulated_face_equivalent"], 2)
        self.assertEqual(report["format_inventory"].get("triangle_faces", 0), 0)
        self.assertEqual(report["topology"]["boundary_edges"], 4)
        self.assertEqual(
            report["declaration_inventory"]["objects"],
            [{"name": "default", "face_statement_count": 1}],
        )

    def test_non_manifold_edge_incidence_is_detected(self):
        temporary, _source, _output, report = self.evaluate_fixture(
            """
            v 0 0 0
            v 1 0 0
            v 0 1 0
            v 0 -1 0
            v 0 0 1
            f 1 2 3
            f 2 1 4
            f 1 2 5
            """
        )
        self.addCleanup(temporary.cleanup)

        self.assertEqual(report["topology"]["non_manifold_edges"], 1)
        self.assertEqual(report["topology"]["maximum_edge_incidence"], 3)
        self.assertFalse(report["topology"]["watertight"])
        self.assertTrue(all(value is False for value in report["release"].values()))

    def test_collinear_face_is_counted_as_zero_area_without_metric_claim(self):
        temporary, _source, _output, report = self.evaluate_fixture(
            """
            v 0 0 0
            v 1 0 0
            v 2 0 0
            f 1 2 3
            """
        )
        self.addCleanup(temporary.cleanup)

        self.assertEqual(report["format_inventory"]["zero_area_faces"], 1)
        self.assertFalse(report["release"]["fabrication_release_authorized"])
        self.assertFalse(report["release"]["scale_confirmed"])

    def test_invalid_vertex_reference_fails_closed(self):
        temporary, _source, _output, report = self.evaluate_fixture(
            """
            v 0 0 0
            v 1 0 0
            v 0 1 0
            f 1 2 0
            """
        )
        self.addCleanup(temporary.cleanup)

        self.assertEqual(report["report_status"], "failed")
        self.assertTrue(report["parse_errors"])
        self.assertEqual(report["format_inventory"]["invalid_faces"], 1)
        self.assertTrue(all(value is False for value in report["release"].values()))

    def test_noncanonical_hash_requires_explicit_fixture_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "not-the-canonical-scan.obj"
            output = root / "output"
            write_obj(source, mixed_fixture())
            report = self.module.evaluate(CONTRACT, source, output)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "source_sha256_does_not_match_canonical_scan",
            report["source_custody_errors"],
        )
        self.assertFalse(report["source_custody"]["expected_sha256_matches"])
        self.assertTrue(all(value is False for value in report["release"].values()))

    def test_contract_cannot_enable_metric_conversion_or_release(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            modified = copy.deepcopy(self.contract)
            modified["metrology_policy"]["metric_conversion_allowed"] = True
            modified["release_authority"]["fabrication_release_authorized"] = True
            contract_path = root / "forged-contract.json"
            contract_path.write_text(json.dumps(modified), encoding="utf-8")
            report = self.module.evaluate(
                contract_path,
                root / "source-does-not-need-to-exist.obj",
                root / "output",
                synthetic_fixture_mode=True,
            )

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "contract_metrology_metric_conversion_allowed_must_remain_false",
            report["contract_integrity_errors"],
        )
        self.assertIn(
            "contract_release_authority_must_remain_exactly_fail_closed",
            report["contract_integrity_errors"],
        )
        self.assertTrue(all(value is False for value in report["release"].values()))

    def test_outputs_are_lightweight_inventories_and_temporary_runs_are_removed(self):
        temporary, source, output, report = self.evaluate_fixture(mixed_fixture())
        self.addCleanup(temporary.cleanup)

        expected = {
            "scan-segmentation-f15-report.json",
            "surface-components-f15.csv",
            "boundary-components-f15.csv",
            "obj-declarations-f15.json",
        }
        self.assertEqual({path.name for path in output.iterdir()}, expected)
        self.assertFalse(any(path.suffix.lower() == ".obj" for path in output.iterdir()))
        self.assertFalse(any(path.is_dir() for path in output.iterdir()))
        self.assertFalse(report["source_custody"]["source_copy_created"])
        self.assertFalse(report["source_custody"]["raw_geometry_in_report"])
        self.assertEqual(source.read_text(encoding="utf-8"), mixed_fixture().strip() + "\n")

    def test_report_is_deterministic_for_the_same_bytes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "fixture.obj"
            write_obj(source, mixed_fixture())
            first = self.module.evaluate(
                CONTRACT, source, root / "first", synthetic_fixture_mode=True
            )
            second = self.module.evaluate(
                CONTRACT, source, root / "second", synthetic_fixture_mode=True
            )

        self.assertEqual(first, second)

    def test_cli_exit_codes_are_zero_for_fixture_and_one_for_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "fixture.obj"
            write_obj(source, mixed_fixture())
            common = [
                sys.executable,
                str(SCRIPT),
                "--contract",
                str(CONTRACT),
                "--source",
                str(source),
            ]
            fixture = subprocess.run(
                common + ["--output", str(root / "fixture-output"), "--synthetic-fixture-mode"],
                check=False,
                capture_output=True,
                text=True,
            )
            canonical = subprocess.run(
                common + ["--output", str(root / "canonical-output")],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(fixture.returncode, 0, fixture.stderr)
        self.assertEqual(canonical.returncode, 1, canonical.stdout)


if __name__ == "__main__":
    unittest.main()
