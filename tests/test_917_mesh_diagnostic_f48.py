#!/usr/bin/env python3
"""Tests du diagnostic de maillage F48 sur les STEP privés F47."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/mesh-diagnostic-f48.json"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f48-mesh-diagnostic"
REPORT = EVIDENCE / "diagnostic-report.json"
SUMMARY = EVIDENCE / "summary.json"
MANIFEST = EVIDENCE / "manifest.json"
SCRIPT = ROOT / "twins/reference-917-engine/source/publish_mesh_diagnostic_f48.py"
DIAGNOSTIC_SCRIPT = ROOT / "twins/reference-917-engine/source/diagnose_private_f47_step_mesh_f48.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module():
    spec = importlib.util.spec_from_file_location("f48_mesh_diagnostic", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MeshDiagnosticF48Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load(CONTRACT)
        cls.report = load(REPORT)
        cls.summary = load(SUMMARY)
        cls.manifest = load(MANIFEST)

    def test_cli_check_and_fail_closed_verdict(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--project-root", str(ROOT), "--check"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("F48 private STEP mesh diagnostic evidence: OK", result.stdout)
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        self.assertEqual(
            self.report["verdict"],
            "F47_STEP_MESH_REJECTED_INTERNAL_GAS_PCURVES_REPAIR_REQUIRED",
        )
        self.assertFalse(self.report["claims"]["CAE_executed"])
        self.assertFalse(self.report["claims"]["printability_validated"])

    def test_exact_occt_counts_localize_gas_not_oil(self) -> None:
        expected = {"2v": (4, 0, 8, 3, 4, 5, 8), "4v": (22, 0, 32, 10, 18, 17, 28)}
        for variant, values in expected.items():
            occt = self.contract["observations"][variant]["occt"]
            actual = (
                occt["gas_core"]["BOPAlgo_fault_count"],
                occt["oil_core"]["BOPAlgo_fault_count"],
                occt["head_after_subtraction"]["BOPAlgo_fault_count"],
                occt["gas_core"]["faulty_face_count"],
                occt["gas_core"]["faulty_edge_count"],
                occt["head_after_subtraction"]["faulty_face_count"],
                occt["head_after_subtraction"]["faulty_edge_count"],
            )
            self.assertEqual(actual, values)
            for item in occt.values():
                self.assertTrue(item["BRepCheck_exact_valid"])
                self.assertEqual(
                    len(item["opaque_entity_refs"]),
                    item["faulty_face_count"] + item["faulty_edge_count"],
                )
            self.assertEqual(
                occt["gas_core"]["BOPAlgo_status_counts"],
                {"BOPAlgo_InvalidCurveOnSurface": values[0]},
            )

    def test_gmsh_failure_classes_are_not_promoted_to_meshes(self) -> None:
        self.assertEqual(
            self.contract["observations"]["2v"]["gmsh"]["error_class"],
            "PLC_segment_facet_intersection",
        )
        self.assertEqual(
            self.contract["observations"]["4v"]["gmsh"]["error_class"],
            "PLC_facet_facet_intersection",
        )
        for variant in ("2v", "4v"):
            gmsh = self.contract["observations"][variant]["gmsh"]
            self.assertTrue(gmsh["surface_mesh_completed_before_failure"])
            self.assertFalse(gmsh["volume_mesh_completed"])

    def test_private_coordinates_and_geometry_are_absent(self) -> None:
        private = self.contract["private_evidence"]
        self.assertRegex(private["coordinate_bearing_localization_receipt_sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(private["coordinates_published"])
        self.assertFalse(private["entity_indices_published"])
        suffixes = {".step", ".stp", ".stl", ".obj", ".msh", ".brep", ".iges", ".igs"}
        for path in EVIDENCE.rglob("*"):
            if path.is_file():
                self.assertNotIn(path.suffix.lower(), suffixes)
        payload = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (CONTRACT, REPORT, SUMMARY)
        )
        self.assertNotRegex(payload, r'"(?:bbox|centre|coordinates?|private_index)"\s*:')

    def test_external_skin_and_shape_policy_is_absolute(self) -> None:
        policy = self.contract["locked_geometry_policy"]
        self.assertTrue(policy["same_f43_outer_bytes_used_for_2v_and_4v"])
        for key in (
            "external_scan_skin_modification_allowed",
            "global_healing_allowed",
            "proxy_geometry_allowed",
            "oval_or_ellipse_allowed",
            "geometry_created_by_f48",
            "mesh_committed_by_f48",
        ):
            self.assertFalse(policy[key])
        plan_text = json.dumps(self.contract["surgical_correction_plan"])
        self.assertIn("internal_gas_core_junctions_only", plan_text)
        self.assertIn("byte-locked F43", plan_text)

    def test_public_entity_refs_are_opaque_unique_and_complete(self) -> None:
        refs = []
        for variant in ("2v", "4v"):
            for item in self.contract["observations"][variant]["occt"].values():
                refs.extend(item["opaque_entity_refs"])
        self.assertEqual(len(refs), 93)
        self.assertEqual(len(refs), len(set(refs)))
        self.assertTrue(all(re.fullmatch(r"(?:gas|head)-(?:face|edge)-[0-9a-f]{16}", ref) for ref in refs))

    def test_manifest_hashes_and_reproducibility(self) -> None:
        self.assertEqual(self.manifest["generator"]["sha256"], sha256(SCRIPT))
        self.assertEqual(
            self.manifest["private_diagnostic_harness"]["sha256"],
            sha256(DIAGNOSTIC_SCRIPT),
        )
        self.assertEqual(
            self.report["private_diagnostic_harness"]["sha256"],
            sha256(DIAGNOSTIC_SCRIPT),
        )
        self.assertEqual(
            {item["path"] for item in self.manifest["artifacts"]},
            {
                "twins/reference-917-engine/evidence/f48-mesh-diagnostic/diagnostic-report.json",
                "twins/reference-917-engine/evidence/f48-mesh-diagnostic/summary.json",
            },
        )
        for item in self.manifest["artifacts"]:
            path = ROOT / item["path"]
            self.assertEqual(path.stat().st_size, item["bytes"])
            self.assertEqual(sha256(path), item["sha256"])

    def test_validator_rejects_geometry_or_release_claims(self) -> None:
        module = load_module()
        mutations = []
        changed = copy.deepcopy(self.contract)
        changed["locked_geometry_policy"]["oval_or_ellipse_allowed"] = True
        mutations.append(changed)
        changed = copy.deepcopy(self.contract)
        changed["locked_geometry_policy"]["external_scan_skin_modification_allowed"] = True
        mutations.append(changed)
        changed = copy.deepcopy(self.contract)
        changed["release_gates"]["metal_print_authorized"] = True
        mutations.append(changed)
        changed = copy.deepcopy(self.contract)
        changed["observations"]["4v"]["gmsh"]["volume_mesh_completed"] = True
        mutations.append(changed)
        for mutation in mutations:
            with self.assertRaises(ValueError):
                module.validate_contract(mutation)

    def test_private_diagnostic_script_refuses_repository_output(self) -> None:
        spec = importlib.util.spec_from_file_location("f48_private_diagnostic", DIAGNOSTIC_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with self.assertRaisesRegex(ValueError, "outside_repository"):
            module.safe_output(ROOT, ROOT / "work/private-f48.json")
        source = DIAGNOSTIC_SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("/private/tmp", source)
        self.assertNotIn("oval", source.lower())
        self.assertNotIn("ellipse", source.lower())


if __name__ == "__main__":
    unittest.main()
