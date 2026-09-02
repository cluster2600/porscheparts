"""Tests fail-closed des faits FIA soupapes, cames et conduit F20."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "twins/reference-917-engine/valvetrain-flow-inputs-f20.json"
BUILDER = ROOT / "twins/reference-917-engine/source/build_valvetrain_flow_inputs_f20.py"


def load_module():
    spec = importlib.util.spec_from_file_location("valvetrain_flow_inputs_f20", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ValvetrainFlowInputs917F20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.document = json.loads(OUTPUT.read_text(encoding="utf-8"))

    def evaluate(self, document: dict) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "f20.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            return self.module.evaluate(ROOT, path)

    def facts(self, section: str) -> dict[str, dict]:
        return {item["id"]: item for item in self.document[section]}

    def test_committed_document_matches_canonical_generation(self):
        expected = self.module.build_document(ROOT)
        self.assertEqual(self.document, expected)
        report = self.module.evaluate(ROOT, OUTPUT)
        self.assertEqual(report["report_status"], "passed", report["errors"])
        self.assertEqual(report["fact_count"], 15)
        self.assertEqual(report["branch_count"], 2)
        self.assertEqual(report["declared_tolerance_count"], 1)
        self.assertEqual(report["unresolved_input_count"], 4)
        self.assertTrue(report["all_release_gates_blocked"])
        self.assertFalse(report["external_pdf_verified"])

    def test_pdf_and_upstream_records_are_digest_bound_without_redistribution(self):
        source = self.document["source_contract"]
        self.assertEqual(source["f13_registry_sha256"], self.module.EXPECTED_F13_SHA256)
        self.assertEqual(source["catalog_record_sha256"], self.module.EXPECTED_SOURCE_SHA256)
        self.assertEqual(source["pdf"]["sha256"], self.module.EXPECTED_PDF_SHA256)
        self.assertEqual(source["pdf"]["bytes"], 9_430_508)
        self.assertEqual(source["pdf"]["page_count"], 17)
        self.assertEqual(source["pdf"]["reviewed_pdf_pages"], [8, 9, 10, 14])
        self.assertEqual(
            source["pdf"]["review_method"],
            "manual_visual_review_of_rendered_scanned_pages",
        )
        self.assertFalse(source["pdf"]["ocr_used_as_authority"])
        self.assertFalse(source["pdf"]["repository_copy_allowed"])
        self.assertFalse(
            (ROOT / "catalog/sources/homologation_form_number_250_group_4.pdf").exists()
        )
        self.assertNotIn("/tmp/", OUTPUT.read_text(encoding="utf-8"))

    def test_valve_cam_port_and_timing_values_keep_exact_pages(self):
        topology = self.facts("topology_candidates")
        cad = self.facts("cad_dimension_candidates")
        boundary = self.facts("boundary_condition_candidates")

        self.assertEqual(topology["F20-CAMSHAFT-COUNT"]["candidate"], {"kind": "published_point", "value": 4, "unit": "count"})
        self.assertEqual(topology["F20-CAMSHAFT-DRIVE"]["candidate"]["value"], "gears")
        self.assertEqual(topology["F20-VALVE-ACTUATION"]["candidate"]["value"], "bucket_tappets")
        self.assertTrue(all(item["source_evidence"]["pdf_page"] == 9 for item in topology.values()))

        self.assertEqual(cad["F20-INTAKE-VALVE-OUTER-DIAMETER"]["candidate"]["value"], 47.5)
        self.assertEqual(cad["F20-INTAKE-VALVE-OUTER-DIAMETER"]["source_evidence"]["form_position"], 181)
        self.assertEqual(cad["F20-EXHAUST-VALVE-OUTER-DIAMETER"]["candidate"]["value"], 40.5)
        self.assertEqual(cad["F20-EXHAUST-VALVE-OUTER-DIAMETER"]["source_evidence"]["form_position"], 196)
        self.assertEqual(cad["F20-INTAKE-PORT-DIAMETER"]["candidate"], {"kind": "published_point", "value": 41.0, "unit": "mm"})
        self.assertEqual(cad["F20-INTAKE-PORT-DIAMETER"]["source_evidence"]["pdf_page"], 10)
        self.assertEqual(cad["F20-INTAKE-PORT-DIAMETER"]["source_evidence"]["form_position"], 225)

        expected_boundary_values = {
            "F20-INTAKE-VALVE-MAX-LIFT": (12.1, "mm", 182),
            "F20-EXHAUST-VALVE-MAX-LIFT": (10.5, "mm", 197),
            "F20-INTAKE-COLD-CLEARANCE": (0.1, "mm", 186),
            "F20-EXHAUST-COLD-CLEARANCE": (0.1, "mm", 201),
            "F20-INTAKE-OPENS-BTDC": (104.0, "deg_crank_btdc", 187),
            "F20-INTAKE-CLOSES-ABDC": (104.0, "deg_crank_abdc", 188),
            "F20-EXHAUST-OPENS-BBDC": (105.0, "deg_crank_bbdc", 202),
            "F20-EXHAUST-CLOSES-ATDC": (75.0, "deg_crank_atdc", 203),
        }
        for fact_id, (value, unit, position) in expected_boundary_values.items():
            with self.subTest(fact_id=fact_id):
                self.assertEqual(boundary[fact_id]["candidate"]["value"], value)
                self.assertEqual(boundary[fact_id]["candidate"]["unit"], unit)
                self.assertEqual(boundary[fact_id]["source_evidence"]["pdf_page"], 9)
                self.assertEqual(boundary[fact_id]["source_evidence"]["form_position"], position)

    def test_declared_tolerance_is_separate_and_not_manufacturing_authority(self):
        port = self.facts("cad_dimension_candidates")["F20-INTAKE-PORT-DIAMETER"]
        tolerance = self.document["declared_tolerances"][0]
        self.assertEqual(port["declared_tolerance_ref"], tolerance["id"])
        self.assertEqual(tolerance["plus_minus"], {"value": 0.8, "unit": "mm"})
        self.assertEqual(tolerance["source_evidence"]["pdf_page"], 10)
        self.assertEqual(tolerance["source_evidence"]["form_position"], 225)
        self.assertEqual(
            tolerance["semantics"],
            "homologation_declared_tolerance_not_manufacturing_tolerance",
        )
        self.assertFalse(tolerance["manufacturing_tolerance"])
        self.assertFalse(tolerance["design_lock"])
        reconciliation = self.document["upstream_reconciliation"][0]
        self.assertEqual(
            reconciliation["observed_fia_fact"],
            "intake_port_diameter_41_plus_minus_0_8_mm",
        )
        self.assertTrue(reconciliation["blocks_release"])
        self.assertFalse(reconciliation["upstream_edit_required_in_this_phase"])

    def test_4494_is_direct_and_4907_is_only_inherited_candidate(self):
        branches = {item["variant_id"]: item for item in self.document["branch_bindings"]}
        base = branches[self.module.BASE_VARIANT]
        extension = branches[self.module.EXTENSION_VARIANT]

        self.assertEqual(base["identity_anchor"]["displacement_cm3"], 4494.2)
        self.assertEqual(base["identity_anchor"]["source_evidence"]["pdf_page"], 8)
        self.assertEqual(base["binding_mode"], "direct_base_homologation_form")
        self.assertEqual(len(base["direct_fact_refs"]), 15)
        self.assertEqual(base["candidate_inherited_fact_refs"], [])

        self.assertEqual(extension["identity_anchor"]["displacement_cm3"], 4907.28)
        self.assertEqual(extension["identity_anchor"]["source_evidence"]["pdf_page"], 14)
        self.assertEqual(
            extension["identity_anchor"]["f13_fact_refs"],
            ["FACT-4907-BORE", "FACT-4907-STROKE", "FACT-4907-DISPLACEMENT"],
        )
        self.assertEqual(extension["direct_fact_refs"], [])
        self.assertEqual(len(extension["candidate_inherited_fact_refs"]), 15)
        self.assertTrue(extension["inheritance_requires_measurement_confirmation"])
        for branch in branches.values():
            self.assertFalse(branch["adoption_as_cad_authorized"])
            self.assertFalse(branch["adoption_as_boundary_conditions_authorized"])

    def test_unknown_pressures_and_missing_profiles_remain_null_and_blocking(self):
        missing = {item["id"]: item for item in self.document["unresolved_required_inputs"]}
        self.assertEqual(
            missing["F20-MISSING-INJECTION-PRESSURE"]["reviewed_evidence"]["pdf_page"],
            10,
        )
        self.assertEqual(
            missing["F20-MISSING-OIL-PRESSURE"]["reviewed_evidence"]["pdf_page"],
            8,
        )
        for item in missing.values():
            self.assertIsNone(item["value"])
            self.assertIsNone(item["unit"])
            self.assertTrue(item["default_forbidden"])
            self.assertIn("physicsnemo", item["blocks"])

    def test_every_authority_and_release_gate_remains_closed(self):
        authority = self.document["authority_boundary"]
        self.assertTrue(authority["source_fact_registration_only"])
        for key, value in authority.items():
            if key != "source_fact_registration_only":
                self.assertIs(value, False, key)
        self.assertEqual(set(self.document["release_gates"]), set(self.module.REQUIRED_FALSE_GATES))
        self.assertTrue(all(value is False for value in self.document["release_gates"].values()))

    def test_mutated_value_page_branch_pressure_or_gate_is_rejected(self):
        mutations = []

        changed_value = copy.deepcopy(self.document)
        changed_value["cad_dimension_candidates"][0]["candidate"]["value"] = 48.0
        mutations.append(changed_value)

        changed_page = copy.deepcopy(self.document)
        changed_page["boundary_condition_candidates"][0]["source_evidence"]["pdf_page"] = 8
        mutations.append(changed_page)

        direct_extension = copy.deepcopy(self.document)
        direct_extension["branch_bindings"][1]["direct_fact_refs"] = direct_extension["branch_bindings"][1]["candidate_inherited_fact_refs"]
        direct_extension["branch_bindings"][1]["candidate_inherited_fact_refs"] = []
        mutations.append(direct_extension)

        invented_pressure = copy.deepcopy(self.document)
        invented_pressure["unresolved_required_inputs"][0]["value"] = 5.0
        invented_pressure["unresolved_required_inputs"][0]["unit"] = "bar"
        mutations.append(invented_pressure)

        opened_gate = copy.deepcopy(self.document)
        opened_gate["release_gates"]["cfd_ready"] = True
        mutations.append(opened_gate)

        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                report = self.evaluate(mutation)
                self.assertEqual(report["report_status"], "failed")
                self.assertTrue(report["errors"])

    def test_external_pdf_verifier_fails_closed_on_wrong_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            fake = Path(temporary) / "fia250.pdf"
            fake.write_bytes(b"not the official FIA PDF")
            errors = self.module.verify_external_pdf(fake)
        self.assertIn("external_pdf_size_mismatch", errors)
        self.assertIn("external_pdf_sha256_mismatch", errors)
        self.assertIn("pdfinfo_unavailable_or_failed", errors)

    def test_cli_generation_requires_the_external_official_pdf(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "generated.json"
            completed = subprocess.run(
                [sys.executable, str(BUILDER), "--generate", "--output", str(output)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            report = json.loads(completed.stdout)
            self.assertFalse(output.exists())
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(report["report_status"], "failed")
        self.assertEqual(report["errors"], ["generate_requires_external_source_pdf"])


if __name__ == "__main__":
    unittest.main()
