"""Vérifie le diagnostic VG.007 et son candidat F37 fail-closed."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPAIR_SOURCE = ROOT / "twins/reference-917-engine/source/repair_f37_head_mesh_for_nvidia.py"
ANALYSIS_SOURCE = ROOT / "twins/reference-917-engine/source/analyze_f37_nvidia_usd_topology.py"
ATTEST_SOURCE = ROOT / "twins/reference-917-engine/source/attest_f37_nvidia_validation.py"
ENRICH_SOURCE = ROOT / "twins/reference-917-engine/source/enrich_f37_head_mesh_nvidia.py"
MAKEFILE = ROOT / "Makefile"
CONTRACT = ROOT / "twins/reference-917-engine/f37-manufacturing-definition.json"
CAD_REPORT = ROOT / "work/917-scan-conforming-f37/cad/f37-cad-report.json"
HEAD_PROOF = ROOT / "work/917-scan-conforming-f37/head-mesh-proof"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot_import:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NvidiaMeshRepairSourceTests(unittest.TestCase):
    def test_sources_are_parseable_and_keep_release_fail_closed(self):
        repair = REPAIR_SOURCE.read_text(encoding="utf-8")
        analysis = ANALYSIS_SOURCE.read_text(encoding="utf-8")
        attest = ATTEST_SOURCE.read_text(encoding="utf-8")
        for source in (repair, analysis, attest):
            ast.parse(source)
            self.assertIn('"metal_print_authorized": False', source)
            self.assertIn('"engine_start_authorized": False', source)
        self.assertIn('"candidate_promotion_authorized": False', repair)
        self.assertIn('"candidate_promotion_authorized": False', analysis)

    def test_repair_requires_hash_linked_external_nvidia_evidence(self):
        source = REPAIR_SOURCE.read_text(encoding="utf-8")
        for flag in (
            "--usd-topology-analysis",
            "--official-stl-geometry-report",
            "--official-obj-geometry-report",
            "--direct-usda-geometry-report",
            "--validation-attestation",
            "--validated-usda-sha256",
        ):
            self.assertIn(flag, source)
        self.assertIn("uniform per-face normals", source)
        self.assertIn("faceVertexIndices", source)
        self.assertIn("command_matches_report_asset_path", source)
        self.assertIn("container_image_digest_pinned", source)

        attest = ATTEST_SOURCE.read_text(encoding="utf-8")
        for flag in ("--source-stl", "--source-converted-usd", "--source-geometry-report"):
            self.assertIn(flag, attest)
        self.assertIn("source_report_matches_converted_usd", attest)

    def test_validated_usda_is_written_from_the_reloaded_candidate_stl(self):
        source = REPAIR_SOURCE.read_text(encoding="utf-8")
        export_position = source.index("candidate.export(output_stl)")
        reload_position = source.index(
            'reloaded = load_mesh(output_stl, "candidate_stl")',
            export_position,
        )
        usda_position = source.index(
            "write_indexed_usda(output_usda, reloaded)",
            reload_position,
        )
        self.assertLess(export_position, reload_position)
        self.assertLess(reload_position, usda_position)
        self.assertNotIn("write_indexed_usda(output_usda, candidate)", source)

    def test_make_has_a_second_pass_that_derives_vg007_from_attestation(self):
        source = ENRICH_SOURCE.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn(
            '"source_official_conversion_vg007_non_manifold_vertices"', source
        )
        self.assertNotIn("8047", source)
        for flag in ("--preview", "--oil-core", "--contract", "--geometry-report"):
            self.assertIn(flag, source)
        self.assertIn("preview_inputs_incomplete", source)
        self.assertIn("render(head, oil, head_pads, report, preview_path)", source)
        makefile = MAKEFILE.read_text(encoding="utf-8")
        self.assertIn("917-manufacturing-f37-head-mesh-enrich:", makefile)
        self.assertIn("enrich_f37_head_mesh_nvidia.py", makefile)

    def test_enrichment_derives_count_and_rejects_another_head(self):
        module = load_module(ENRICH_SOURCE, "f37_nvidia_enrichment")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            head = root / "head.local.stl"
            report_path = root / "report.json"
            attestation_path = root / "attestation.json"
            output_path = root / "enriched.json"
            head.write_bytes(b"head")
            report = {
                "phase": "F37",
                "status": "local_mesh_boolean_proof_complete_physical_and_manufacturing_release_blocked",
                "local_only_artifacts": {
                    head.name: {"sha256": sha256(head), "bytes": head.stat().st_size}
                },
                "strict_vertex_manifold_audit": {"strict_vertex_manifold": True},
                "gates": {
                    "all_declared_accesses_cross_parent_skin": True,
                    "all_four_mount_planes_detected": True,
                    "oil_to_gas_flow_collision_absent": True,
                    "metal_printability_demonstrated": False,
                    "metal_print_authorized": False,
                    "engine_start_authorized": False,
                },
            }
            report_path.write_text(json.dumps(report), encoding="utf-8")
            attestation = {
                "phase": "F37_nvidia_geometry_validation_attestation",
                "linkage": {
                    "source_stl": {"sha256": sha256(head), "bytes": head.stat().st_size}
                },
                "result": {
                    "source_official_conversion_vg007_non_manifold_vertices": 7
                },
                "gates": {
                    "nvidia_geometry_clear": True,
                    "source_official_conversion_vg007_observed": True,
                },
            }
            attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
            enriched = module.enrich_report(
                report_path, head, attestation_path, output_path
            )
            self.assertEqual(
                enriched["nvidia_asset_validator_observation"][
                    "non_manifold_vertex_count"
                ],
                7,
            )
            self.assertEqual(
                enriched["nvidia_asset_validator_observation"]["evidence"]["path"],
                attestation_path.name,
            )
            self.assertFalse(
                enriched["gates"]["independent_topology_validators_agree"]
            )
            attestation["linkage"]["source_stl"]["sha256"] = "0" * 64
            attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "attestation_head_hash_mismatch"):
                module.enrich_report(report_path, head, attestation_path, output_path)

    def test_usd_analysis_reproduces_nvidia_border_edge_definition(self):
        source = ANALYSIS_SOURCE.read_text(encoding="utf-8")
        self.assertIn("border_degree > 2", source)
        self.assertIn("np.unique", source)
        self.assertIn('"conversion_indexing_cause_confirmed"', source)


class NvidiaMeshRepairEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("F37_NVIDIA_REPAIR_DIR")
        cls.evidence = (
            Path(configured)
            if configured
            else ROOT / "work/917-scan-conforming-f37/nvidia-repair-candidate"
        )
        report_path = cls.evidence / "f37-nvidia-mesh-repair-report.json"
        if not report_path.is_file():
            raise unittest.SkipTest("preuve de réparation NVIDIA F37 absente")
        cls.report = json.loads(report_path.read_text(encoding="utf-8"))
        cls.analysis = json.loads(
            (cls.evidence / "f37-nvidia-usd-topology-analysis.json").read_text(encoding="utf-8")
        )
        cls.attestation = json.loads(
            (cls.evidence / "f37-nvidia-geometry-validation-attestation.json").read_text(encoding="utf-8")
        )

    def test_all_local_artifacts_match_recorded_hashes(self):
        for name, record in self.report["local_only_artifacts"].items():
            path = self.evidence / name
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.stat().st_size, record["bytes"], name)
            self.assertEqual(sha256(path), record["sha256"], name)

    def test_indexing_cause_is_numerically_reproduced(self):
        official = self.analysis["official_conversion_indexing"]
        welded = self.analysis["after_exact_coordinate_weld"]
        self.assertEqual(official["point_count"], 843308)
        self.assertEqual(official["vertices_with_more_than_two_border_edges"], 8047)
        self.assertEqual(welded["point_count"], 427985)
        self.assertEqual(welded["border_edge_count"], 0)
        self.assertEqual(welded["vertices_with_more_than_two_border_edges"], 0)
        self.assertTrue(self.analysis["conclusion"]["conversion_indexing_cause_confirmed"])

    def test_candidate_preserves_geometry_and_interfaces(self):
        topology = self.report["candidate"]["topology"]
        comparison = self.report["comparison_to_source"]
        interfaces = self.report["interfaces"]
        self.assertTrue(topology["watertight"])
        self.assertEqual(topology["body_count"], 1)
        self.assertEqual(comparison["vertex_set_hausdorff"]["symmetric_max_mm"], 0.0)
        self.assertLessEqual(comparison["relative_volume_delta"], 1.0e-7)
        self.assertLessEqual(interfaces["oil_to_gas_collision_mm3"], 0.01)
        self.assertLessEqual(interfaces["oil_to_candidate_solid_collision_mm3"], 0.01)
        self.assertTrue(all(item["planar_surface_detected"] for item in interfaces["mount_pad_planes"]))

    def test_report_is_bound_to_current_contract_cad_and_head_proof(self):
        contract_hash = sha256(CONTRACT)
        cad_hash = sha256(CAD_REPORT)
        head_report_path = HEAD_PROOF / "f37-printable-head-mesh-report.json"
        head_path = HEAD_PROOF / "917-head-f37-printable-proof.local.stl"
        head_preview = HEAD_PROOF / "917-head-f37-printable-proof.png"
        head_report = json.loads(head_report_path.read_text(encoding="utf-8"))
        cad_report = json.loads(CAD_REPORT.read_text(encoding="utf-8"))
        self.assertEqual(cad_report["inputs"]["contract_sha256"], contract_hash)
        self.assertEqual(head_report["inputs"]["contract_sha256"], contract_hash)
        self.assertEqual(head_report["inputs"]["cad_report_sha256"], cad_hash)
        self.assertEqual(self.report["inputs"]["contract_sha256"], contract_hash)
        self.assertEqual(self.report["inputs"]["source_report"]["sha256"], sha256(head_report_path))
        self.assertEqual(self.report["inputs"]["source_report"]["bytes"], head_report_path.stat().st_size)
        self.assertEqual(self.report["inputs"]["source_head"]["sha256"], sha256(head_path))
        self.assertEqual(
            head_report["local_only_artifacts"][head_path.name]["sha256"],
            self.report["inputs"]["source_head"]["sha256"],
        )
        self.assertEqual(
            head_report["local_only_artifacts"][head_preview.name],
            {"bytes": head_preview.stat().st_size, "sha256": sha256(head_preview)},
        )
        nvidia = head_report["nvidia_asset_validator_observation"]
        self.assertEqual(nvidia["exact_stl_sha256"], sha256(head_path))
        self.assertEqual(nvidia["non_manifold_vertex_count"], 8047)
        self.assertEqual(
            nvidia["evidence"]["sha256"],
            sha256(self.evidence / "f37-nvidia-geometry-validation-attestation.json"),
        )
        self.assertFalse(head_report["gates"]["independent_topology_validators_agree"])

    def test_nvidia_pass_is_hash_linked_but_does_not_release_manufacturing(self):
        linkage = self.attestation["linkage"]
        usda = self.evidence / linkage["asset"]["path"]
        self.assertEqual(sha256(usda), linkage["asset"]["sha256"])
        self.assertEqual(
            linkage["normalized_report"]["sha256"],
            self.report["inputs"]["nvidia_evidence"]["direct_indexed_usda"]["sha256"],
        )
        self.assertTrue(self.attestation["result"]["geometry_clear"])
        self.assertEqual(sum(self.attestation["result"]["issue_counts"].values()), 0)
        self.assertTrue(linkage["command_matches_report_asset_path"])
        self.assertEqual(
            linkage["source_stl"]["sha256"],
            self.report["inputs"]["source_head"]["sha256"],
        )
        self.assertTrue(linkage["source_report_matches_converted_usd"])
        self.assertTrue(self.attestation["gates"]["container_image_digest_pinned"])
        self.assertTrue(self.attestation["gates"]["geometry_category_requested"])
        self.assertEqual(
            self.attestation["result"]["source_official_conversion_vg007_non_manifold_vertices"],
            8047,
        )
        gates = self.report["gates"]
        self.assertTrue(gates["nvidia_explicit_index_usda_geometry_clear"])
        self.assertFalse(gates["official_stl_or_obj_conversion_geometry_clear"])
        self.assertFalse(gates["candidate_promotion_authorized"])
        self.assertFalse(gates["metal_print_authorized"])
        self.assertFalse(gates["engine_start_authorized"])
        self.assertEqual(
            self.report["status"],
            "nvidia_direct_usda_geometry_pass_official_conversion_and_manufacturing_release_blocked",
        )


if __name__ == "__main__":
    unittest.main()
