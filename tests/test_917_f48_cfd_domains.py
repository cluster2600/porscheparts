#!/usr/bin/env python3
"""Tests autonomes du paquet public F48, sans Gmsh ni artefact BREP/MSH."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/cfd-domain-contract-f48.json"
BUILDER = ROOT / "twins/reference-917-engine/source/build_cfd_domains_f48.py"
RENDERER = ROOT / "twins/reference-917-engine/source/render_cfd_domains_f48.py"
PUBLISHER = ROOT / "twins/reference-917-engine/source/publish_cfd_domains_f48.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f48-cfd-domains"
REPORT = EVIDENCE / "f48-cfd-domain-report.json"
MANIFEST = EVIDENCE / "publication.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F48CFDDomainsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_geometry_source_is_native_circular_and_has_no_scan_import(self) -> None:
        tree = ast.parse(BUILDER.read_text(encoding="utf-8"))
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("addCylinder", calls)
        self.assertIn("fuse", calls)
        self.assertTrue(
            calls.isdisjoint(
                {
                    "addEllipse",
                    "addDisk",
                    "addBox",
                    "addCone",
                    "addSphere",
                    "addTorus",
                    "importShapes",
                    "merge",
                }
            )
        )
        policy = self.contract["geometry_policy"]
        self.assertFalse(policy["outer_scan_or_skin_imported"])
        self.assertFalse(policy["solid_head_or_fin_geometry_generated"])
        self.assertFalse(policy["ellipse_or_oval_profile_or_surface_primitive_used"])
        self.assertFalse(policy["proxy_envelope_used"])
        self.assertTrue(policy["OCC_generated_conic_intersection_edges_may_be_named_Ellipse"])

    def test_three_comparable_meshes_per_variant_pass_quality(self) -> None:
        expected_sizes = {"coarse": 6.0, "medium": 4.0, "fine": 2.5}
        for variant in ("2V", "4V"):
            meshes = self.report["gas_domains"][variant]
            self.assertEqual(set(meshes), set(expected_sizes))
            volumes = []
            tetrahedra = []
            for level, expected_size in expected_sizes.items():
                mesh = meshes[level]
                self.assertEqual(mesh["characteristic_length_max_scan_units"], expected_size)
                self.assertTrue(mesh["one_volume"])
                self.assertTrue(mesh["all_boundary_surfaces_assigned_once"])
                self.assertEqual(mesh["patch_surface_coverage_count"], mesh["boundary_surface_count"])
                self.assertEqual(mesh["count_minSICN_le_0"], 0)
                self.assertEqual(mesh["count_minSICN_lt_0_1"], 0)
                self.assertGreater(mesh["minimum_minSICN"], 0.0)
                self.assertGreaterEqual(mesh["p01_minSICN"], 0.1)
                self.assertTrue(mesh["quality_gates"]["pass"])
                self.assertEqual(mesh["symmetry_patch"], "not_applicable_full_domain")
                volumes.append(mesh["volume_scan_units_cubed"])
                tetrahedra.append(mesh["tetrahedron_count"])
            self.assertEqual(max(volumes) - min(volumes), 0.0)
            self.assertLess(tetrahedra[0], tetrahedra[1])
            self.assertLess(tetrahedra[1], tetrahedra[2])

    def test_named_gas_patches_are_complete_and_nonempty(self) -> None:
        required = set(self.contract["patch_policy"]["required_gas_patches"])
        self.assertNotIn("symmetry", required)
        for variant in ("2V", "4V"):
            for mesh in self.report["gas_domains"][variant].values():
                self.assertEqual(set(mesh["patches"]), required)
                for patch in mesh["patches"].values():
                    self.assertGreater(patch["surface_count"], 0)
                    self.assertGreater(patch["surface_area_scan_units_squared"], 0.0)
                    self.assertGreater(patch["triangle_count"], 0)

    def test_oil_is_separate_open_lubrication_domain_not_coolant(self) -> None:
        oil = self.report["oil_domain"]
        self.assertTrue(oil["one_volume"])
        self.assertTrue(oil["all_boundary_surfaces_assigned_once"])
        self.assertEqual(set(oil["patches"]), set(self.contract["patch_policy"]["required_oil_patches"]))
        self.assertEqual(oil["count_minSICN_le_0"], 0)
        self.assertGreaterEqual(oil["p01_minSICN"], 0.1)
        self.assertTrue(oil["separate_lubrication_domain_only"])
        self.assertFalse(oil["liquid_coolant_jacket"])

    def test_only_CFD_geometry_mesh_gate_is_open(self) -> None:
        self.assertTrue(self.report["CFD_domain_gate"]["pass"])
        self.assertEqual(self.report["status"], "CFD_DOMAIN_MESH_GATE_PASS_RESEARCH_ONLY")
        self.assertFalse(self.report["interpretation"]["flow_solution_executed"])
        repeatability = self.report["repeatability"]
        self.assertTrue(repeatability["complete_build_reports_bit_identical"])
        self.assertEqual(repeatability["BREP_and_MSH_hashes_checked"], 10)
        self.assertEqual(repeatability["BREP_and_MSH_hash_mismatch_count"], 0)
        for gate in (
            "fitment_OEM_certified",
            "solid_head_BRep_validated",
            "wall_thickness_validated",
            "solid_FEA_validated",
            "thermal_CHT_validated",
            "metal_print_authorized",
            "engine_start_authorized",
        ):
            self.assertFalse(self.report["release_gates"][gate], gate)

    def test_publication_hashes_and_no_geometry_leak(self) -> None:
        expected = {
            "contract": CONTRACT,
            "builder": BUILDER,
            "renderer": RENDERER,
            "publisher": PUBLISHER,
            "report": REPORT,
            "overview": EVIDENCE / "917-f48-cfd-domain-overview.png",
            "sections": EVIDENCE / "917-f48-cfd-domain-sections.png",
        }
        for name, path in expected.items():
            entry = self.manifest["files"][name]
            self.assertEqual(ROOT / entry["path"], path)
            self.assertEqual(entry["sha256"], sha256(path))
        forbidden = {".brep", ".step", ".stp", ".stl", ".msh", ".obj"}
        leaked = [path for path in EVIDENCE.rglob("*") if path.is_file() and path.suffix.lower() in forbidden]
        self.assertEqual(leaked, [])
        self.assertFalse(self.report["repository_policy"]["raw_scan_committed"])
        self.assertFalse(self.report["repository_policy"]["scan_derived_STEP_or_mesh_committed"])


if __name__ == "__main__":
    unittest.main()
