#!/usr/bin/env python3
"""Contrôles fail-closed des preuves géométriques et LPBF F38."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f38-brep-lpbf"
REPORT_PATH = EVIDENCE / "f38-brep-lpbf-report.json"
CONTRACT_PATH = ROOT / "twins/reference-917-engine/f38-brep-lpbf-contract.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class F38BrepLpbfEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_contract_is_scan_conforming_and_not_boxy(self) -> None:
        strategy = self.contract["geometry_strategy"]
        self.assertEqual(strategy["master"], "exact_F37_topology_plus_vertex_normal_offset")
        self.assertFalse(strategy["external_boxes_or_synthetic_fin_stack"])
        self.assertFalse(strategy["faceted_brep_is_production_cad"])

    def test_report_binds_contract_and_generator(self) -> None:
        self.assertEqual(self.report["contract"]["sha256"], sha256(CONTRACT_PATH))
        generator = ROOT / "twins/reference-917-engine/source/build_f38_brep_lpbf.py"
        self.assertEqual(self.report["generator"]["sha256"], sha256(generator))

    def test_published_artifact_hashes(self) -> None:
        expected = {}
        proxy = self.report["geometry_hierarchy"]["faceted_brep_proxy"]
        self.assertEqual(proxy["step"]["repository_policy"], "local_only_not_published")
        self.assertEqual(proxy["stl"]["repository_policy"], "local_only_not_published")
        for image in self.report["images"]:
            expected[image["path"]] = image["sha256"]
        for relative, digest in expected.items():
            path = EVIDENCE / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(sha256(path), digest, relative)

    def test_full_head_geometry_is_not_published(self) -> None:
        forbidden = {"917-head-f38-faceted-proxy.step", "917-head-f38-faceted-proxy.stl"}
        self.assertTrue(forbidden.isdisjoint({path.name for path in EVIDENCE.iterdir()}))

    def test_master_is_local_and_high_resolution(self) -> None:
        master = self.report["geometry_hierarchy"]["authoritative_surface_master"]
        self.assertEqual(master["repository_policy"], "local_only_derived_scan_mesh")
        self.assertEqual(master["triangles"], 857330)
        self.assertTrue(master["watertight"])
        self.assertFalse(master["external_boxes_or_synthetic_fin_stack"])

    def test_faceted_step_roundtrip_is_not_cae_release(self) -> None:
        proxy = self.report["geometry_hierarchy"]["faceted_brep_proxy"]
        self.assertTrue(proxy["occt_build123d_roundtrip"]["valid"])
        self.assertEqual(proxy["occt_build123d_roundtrip"]["solid_count"], 1)
        self.assertFalse(proxy["production_brep"])
        self.assertFalse(self.report["independent_screens"]["gmsh_volume_mesh"]["success"])
        self.assertFalse(self.report["release_gates"]["faceted_brep_gmsh_volume_meshable"])

    def test_minimum_wall_gate_fails(self) -> None:
        wall = self.report["independent_screens"]["minimum_wall_sample"]
        self.assertLess(wall["minimum_mm"], wall["requirement_mm"])
        self.assertLess(wall["p01_mm"], wall["requirement_mm"])
        self.assertFalse(wall["passes"])

    def test_void_screen_has_three_resolutions_and_fails(self) -> None:
        voids = self.report["independent_screens"]["trapped_void_voxel_resolution_study"]
        self.assertEqual([item["pitch_mm"] for item in voids["results"]], [2.0, 1.5, 1.0])
        self.assertGreater(voids["results"][-1]["trapped_volume_mm3"], 0.0)
        self.assertFalse(voids["resolution_converged"])
        self.assertFalse(voids["passes"])

    def test_support_gate_uses_reopened_master_and_fails(self) -> None:
        lpbf = self.report["independent_screens"]["lpbf_overhang_screen"]
        self.assertEqual(lpbf["geometry"], "reopened_authoritative_master_STL")
        self.assertGreater(lpbf["support_area_fraction"], lpbf["requirement_fraction"])
        self.assertFalse(lpbf["is_virtual_build_process_simulation"])
        self.assertFalse(lpbf["passes"])

    def test_safety_gates_remain_closed(self) -> None:
        gates = self.report["release_gates"]
        self.assertEqual(self.report["material_status"]["candidate_only"], "EOS Aluminium Constellium CP1")
        self.assertEqual(self.contract["material"]["candidate_only"], "EOS Aluminium Constellium CP1")
        self.assertFalse(gates["whole_head_production_brep"])
        self.assertFalse(gates["virtual_lpbf_process_simulation_complete"])
        self.assertFalse(gates["hot_material_card_qualified"])
        self.assertFalse(gates["metal_print_authorized"])
        self.assertFalse(gates["engine_start_authorized"])


if __name__ == "__main__":
    unittest.main()
