import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-917-engine/source/validate_variant_authority_f43.py"
CONTRACT = ROOT / "twins/reference-917-engine/variant-authority-f43.json"
EXPECTED_CONTRACT_SHA256 = "021be0be4412f8bd16301af2b3c0536d56e6211d2fef56f94e88b7e9a0f1e15d"
EXPECTED_SOURCE_SHA256 = {
    "ams_917_engine_technical_analysis": "87669cfbda481b816acb880f54c37e3cc73dffd6e753fd8b695248c9c9765a37",
    "porsche_newsroom_91730_turbo": "beffabf935be3baec242bb134a50b6a112c038564c8664f803778cae5f219e55",
    "classical_solver_facts_f13": "1ec8a0c49e95f8f2c8185d4c0f4074d1ed4b36477996ba590cc9f92eccf42a97",
    "dimensional_skeleton_f14": "2824eb0aeb9bfa5f16d7720ade0ba05236d2e4319ef6cbb97b11ff2e0e28b00e",
    "dual_variant_parametric_contract_f28": "920b8c022676a9941c8764fb1f0f178da47220798dd6fa7e96ba6d410aee5abb",
    "clean_sheet_turbo_screening_f32": "485a381b26f4d02da82d66b277e9e4ab16dbeaf7f72b5eb341b02304355ddfb4",
}
EXPECTED_CONFLICT_SHA256 = {
    "f33_na_uses_turbo_bore": "6bbd5a5373660641c50e85dce6b45ac23222751d77f9f86783d82bd72530e73b",
    "f37_na_bench_uses_legacy_4_5_identity": "44241ab4b756f0308ab811e91e8b5c2f5bf5aca20eec8871221c3e6348ea6f4f",
    "f38_na_bench_lineage_uses_legacy_4_5_identity": "e52c7e7910f0263578e4197276a2abbafc36e83460f9bd55346af4a497c51c1d",
    "f39_na_uses_turbo_bore": "c62d1dffcd57a13dce569eb1af05e61c84b893b27613f77c01b0878831743432",
}


def load_module():
    specification = importlib.util.spec_from_file_location("validate_f43", SCRIPT)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class VariantAuthorityF43Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_tracked_contract_passes_and_is_digest_locked(self):
        self.assertEqual(self.module.validate(ROOT, CONTRACT), [])
        self.assertEqual(sha256(CONTRACT), EXPECTED_CONTRACT_SHA256)

    def test_source_and_conflict_snapshots_are_path_and_digest_bound(self):
        sources = {record["id"]: record for record in self.contract["source_bindings"]}
        self.assertEqual(set(sources), set(EXPECTED_SOURCE_SHA256))
        for source_id, expected_digest in EXPECTED_SOURCE_SHA256.items():
            self.assertEqual(sources[source_id]["sha256"], expected_digest)
            self.assertEqual(sha256(ROOT / sources[source_id]["path"]), expected_digest)
            self.assertFalse(sources[source_id]["geometry_transfer_authorized"])

        conflicts = {record["id"]: record for record in self.contract["downstream_conflict_register"]}
        self.assertEqual(set(conflicts), set(EXPECTED_CONFLICT_SHA256))
        for conflict_id, expected_digest in EXPECTED_CONFLICT_SHA256.items():
            self.assertEqual(conflicts[conflict_id]["sha256"], expected_digest)
            self.assertEqual(sha256(ROOT / conflicts[conflict_id]["path"]), expected_digest)
            self.assertFalse(conflicts[conflict_id]["conforms_to_f43"])
            self.assertFalse(conflicts[conflict_id]["results_reusable_as_f43_product_evidence"])

    def test_two_2026_products_have_distinct_source_bound_displacements(self):
        variants = {record["variant_id"]: record for record in self.contract["product_variants"]}
        self.assertEqual(
            set(variants),
            {
                "917_2026_flat12_na_candidate",
                "917_2026_flat12_twin_turbo_1600hp_target",
            },
        )
        na = variants["917_2026_flat12_na_candidate"]
        turbo = variants["917_2026_flat12_twin_turbo_1600hp_target"]
        self.assertEqual((na["bore_mm"], na["stroke_mm"], na["documented_displacement_cm3"]), (86.8, 70.4, 4999.0))
        self.assertEqual((turbo["bore_mm"], turbo["stroke_mm"], turbo["documented_displacement_cm3"]), (90.0, 70.4, 5374.0))
        self.assertEqual(na["source_fact_variant_id"], "type_912_5_0_na")
        self.assertEqual(turbo["source_fact_variant_id"], "917_30_1973_turbo_5374")
        self.assertIsNone(na["requested_power"])
        self.assertEqual(turbo["requested_power"]["value"], 1600.0)
        self.assertFalse(turbo["requested_power"]["simulated"])
        self.assertFalse(turbo["requested_power"]["proven"])

    def test_f10_4_5_l_branch_is_explicitly_excluded(self):
        legacy = self.contract["legacy_branch_exclusions"]
        self.assertEqual(legacy["excluded_na_variant_id"], "type_912_4_5_na")
        self.assertEqual((legacy["excluded_na_bore_mm"], legacy["excluded_na_stroke_mm"]), (85.0, 66.0))
        self.assertEqual(legacy["excluded_na_documented_displacement_cm3"], 4494.0)
        self.assertFalse(legacy["silent_na_inheritance_allowed"])
        self.assertIn("no_product_identity_dimension_geometry_or_solver_input_transfer", legacy["allowed_reuse_scope"])

    def test_all_geometry_solver_performance_and_release_gates_remain_closed(self):
        scope = self.contract["authority_scope"]
        self.assertTrue(scope["variant_parameter_authority"])
        self.assertFalse(scope["geometry_authority"])
        self.assertFalse(scope["performance_authority"])
        self.assertFalse(scope["manufacturing_authority"])
        self.assertFalse(scope["consumer_migration_complete"])
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))

    def test_validator_rejects_na_turbo_bore_and_invented_na_power(self):
        mutated = copy.deepcopy(self.contract)
        na = next(record for record in mutated["product_variants"] if record["configuration"] == "naturally_aspirated")
        na["bore_mm"] = 90.0
        na["requested_power"] = {"value": 800.0, "unit": "mechanical_hp"}
        errors = self.module.validate(ROOT, self._write_contract(mutated))
        self.assertTrue(any("bore_mm" in error for error in errors), errors)
        self.assertTrue(any("requested_power must remain null" in error for error in errors), errors)

    def test_validator_rejects_forged_source_hash_and_open_release_gate(self):
        mutated = copy.deepcopy(self.contract)
        mutated["source_bindings"][0]["sha256"] = "0" * 64
        mutated["release_gates"]["manufacturing_authorized"] = True
        errors = self.module.validate(ROOT, self._write_contract(mutated))
        self.assertTrue(any("declared sha256 mismatch" in error for error in errors), errors)
        self.assertTrue(any("every gate must be explicitly false" in error for error in errors), errors)

    def test_cli_validation_passes(self):
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--project-root",
                str(ROOT),
                "--contract",
                str(CONTRACT),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("F43 variant authority validation passed", result.stdout)

    def _write_contract(self, payload):
        directory = tempfile.TemporaryDirectory(prefix="f43-variant-authority-")
        self.addCleanup(directory.cleanup)
        target = Path(directory.name) / "contract.json"
        target.write_text(json.dumps(payload), encoding="utf-8")
        return target


if __name__ == "__main__":
    unittest.main()
