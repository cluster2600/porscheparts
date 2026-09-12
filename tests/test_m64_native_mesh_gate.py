import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/source/summarize_native_mesh_gate.py"
SPEC = importlib.util.spec_from_file_location("mesh_gate", SOURCE)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class MeshGateTests(unittest.TestCase):
    def setUp(self):
        self.native = dict(process_completed=True, stages_completed=True,
                           inputs_unchanged=True, independent_PL_geometry_accepted=True,
                           failed_check_count=5, mesh_quality_accepted=False)
        self.comparison = dict(candidate_report_sha256="a" * 64,
                               comparison_completed=True, all_inputs_unchanged=True,
                               baseline34_components_exactly_preserved=True,
                               extra_groups_parent_disjoint_from_protected=True,
                               no_new_native_defects_vs_34_verified=True,
                               unresolved_sets=[], new_failed_families=[],
                               unidentified_failed_families_after=0, newly_flagged_total=0,
                               failed_checks_after=5, native_mesh_quality_accepted=False,
                               comparisons={key: dict(source_flag_count=2,
                                                      candidate_flag_count=1,
                                                      newly_flagged_count=0,
                                                      private_ids=[12345]) for key in GATE.SETS})

    def result(self):
        return GATE.summarize(self.native, self.comparison, "a" * 64, "b" * 64)

    def test_rejection_is_not_hidden_by_completed_commands(self):
        result = self.result()
        self.assertFalse(result["mesh_quality_accepted"])
        self.assertFalse(result["CFD_authorized"])
        self.assertFalse(result["manufacturing_authorized"])
        self.assertNotIn("12345", json.dumps(result))
        self.assertLess(len(json.dumps(result)), 4096)

    def test_missing_or_truthy_flags_are_not_proof(self):
        for value in (None, "true", 1, False):
            self.native["process_completed"] = value
            with self.assertRaises(ValueError):
                self.result()

    def test_unpaired_receipts(self):
        self.comparison["candidate_report_sha256"] = "c" * 64
        with self.assertRaises(ValueError):
            self.result()

    def test_unidentified_families_is_a_strict_count_not_a_list(self):
        for value in ([], None, False, 1, -1):
            self.comparison["unidentified_failed_families_after"] = value
            with self.assertRaises(ValueError):
                self.result()

    def test_unknown_set_and_new_flags(self):
        original = copy.deepcopy(self.comparison)
        self.comparison["comparisons"]["unknown"] = {}
        with self.assertRaises(ValueError):
            self.result()
        self.comparison = original
        self.comparison["comparisons"]["shortEdges"]["newly_flagged_count"] = 1
        with self.assertRaises(ValueError):
            self.result()

    def test_inconsistent_counts_or_acceptance(self):
        self.comparison["failed_checks_after"] = 0
        with self.assertRaises(ValueError):
            self.result()
        self.comparison["failed_checks_after"] = 5
        self.native["mesh_quality_accepted"] = True
        with self.assertRaises(ValueError):
            self.result()

    def test_even_accepted_mesh_does_not_release_physics(self):
        self.native.update(failed_check_count=0, mesh_quality_accepted=True)
        self.comparison.update(failed_checks_after=0, native_mesh_quality_accepted=True)
        result = self.result()
        self.assertTrue(result["mesh_quality_accepted"])
        self.assertFalse(result["CFD_authorized"])
        self.assertFalse(result["manufacturing_authorized"])

    def test_read_hash_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text("{}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(GATE.read_pinned(path, digest), {})
            with self.assertRaises(ValueError):
                GATE.read_pinned(path, "0" * 64)
            link = Path(tmp) / "link"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                GATE.read_pinned(link, digest)


if __name__ == "__main__":
    unittest.main()
