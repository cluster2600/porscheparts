import copy
import json
from pathlib import Path
import tempfile
import unittest

import parser_validator as pv


class FidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(__file__).parent
        cls.rows = [pv.strict_json(line) for line in
                    (cls.directory / "corpus/inputs.jsonl").read_text().splitlines()]

    def test_pinned_project_spans_and_separate_golds(self):
        root = self.directory.parents[1]
        golds = [pv.strict_json(line) for line in
                 (self.directory / "gold/expected.jsonl").read_text().splitlines()]
        self.assertEqual(len(self.rows), 4)
        self.assertEqual(sum(len(g["records"]) for g in golds), 7)
        for row, gold in zip(self.rows, golds):
            pv.verify_source(row, root)
            self.assertTrue(pv.validate(row, gold))
            self.assertEqual(gold["measured_records"], 0)

    def test_assumed_units_and_exact_normalization(self):
        result = pv.extract(self.rows[2])
        e, nu, density = result["records"]
        self.assertEqual((e["source_value"], e["source_unit"], e["value"], e["unit"]),
                         (70, "GPa", 70000, "MPa"))
        self.assertEqual((nu["value"], nu["source_unit"], nu["unit"]), (0.33, None, "1"))
        self.assertEqual((density["value"], density["unit"]), (2670, "kg/m3"))
        wrong = copy.deepcopy(result)
        wrong["records"][0]["unit"] = "Pa"
        with self.assertRaises(pv.Rejected):
            pv.validate(self.rows[2], wrong)

    def test_unknown_null_cannot_be_zero_or_implied_equivalence(self):
        result = pv.extract(self.rows[1])
        self.assertIsNone(result["records"][0]["value"])
        for invented in (0, True, "interchangeable"):
            wrong = copy.deepcopy(result)
            wrong["records"][0]["value"] = invented
            with self.assertRaises(pv.Rejected):
                pv.validate(self.rows[1], wrong)

    def test_forum_or_third_party_provenance_rejected(self):
        for field, value in (("authority", "forum"), ("ownership", "third_party"),
                             ("third_party_payload", True)):
            wrong = copy.deepcopy(self.rows[0])
            wrong["source"][field] = value
            with self.assertRaises(pv.Rejected):
                pv.extract(wrong)

    def test_measurement_qualification_and_causality_cannot_be_promoted(self):
        result = pv.extract(self.rows[2])
        for field, value in (("status", "measured_traceable"), ("causal_claim", True),
                             ("accepted_for", ["manufacturing_release"]),
                             ("variant", "qualified_AlSi10Mg")):
            wrong = copy.deepcopy(result)
            wrong["records"][0][field] = value
            with self.assertRaises(pv.Rejected):
                pv.validate(self.rows[2], wrong)

    def test_drop_conditions_or_merge_routes_rejected(self):
        result = pv.extract(self.rows[3])
        wrong = copy.deepcopy(result)
        wrong["records"][1]["conditions"]["required_join_keys"] = ["scenario"]
        with self.assertRaises(pv.Rejected):
            pv.validate(self.rows[3], wrong)

    def test_forged_span_hash_and_nonfinite_duplicate_json_rejected(self):
        wrong = copy.deepcopy(self.rows[2])
        wrong["excerpt"] = wrong["excerpt"].replace("70 GPa", "70 MPa")
        with self.assertRaises(pv.Rejected):
            pv.extract(wrong)
        for text in ('{"value":NaN}', '{"value":1e309}', '{"value":null,"value":0}'):
            with self.assertRaises(pv.Rejected):
                pv.strict_json(text)

    def test_rebound_unapproved_source_span_rejected(self):
        wrong = copy.deepcopy(self.rows[2])
        wrong["excerpt"] = wrong["excerpt"].replace("70 GPa", "80 GPa")
        wrong["source"]["excerpt_sha256"] = pv.sha(wrong["excerpt"].encode())
        with self.assertRaises(pv.Rejected):
            pv.extract(wrong)

    def test_absolute_unadmitted_and_symlink_sources_rejected_before_read(self):
        for path in ("/tmp/not_an_admitted_source", "../not_an_admitted_source",
                     pv.SOURCE_BASE + "corpus/forums/forum_corpus.json"):
            wrong = copy.deepcopy(self.rows[0])
            wrong["source"]["path"] = path
            with self.assertRaises(pv.Rejected):
                pv.verify_source(wrong, Path("/not_a_real_repository"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / self.rows[0]["source"]["path"]
            path.parent.mkdir(parents=True)
            target = root / "owned_synthetic_target.txt"
            target.write_text("Not a real source")
            path.symlink_to(target)
            with self.assertRaisesRegex(pv.Rejected, "symlink"):
                pv.read_public_file(root, self.rows[0]["source"]["path"])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(pv.Rejected, "repository_root"):
                pv.verify_source(self.rows[0], Path(directory))

    def test_bool_is_not_numeric_zero_in_candidate(self):
        wrong = pv.extract(self.rows[0])
        wrong["measured_records"] = False
        with self.assertRaises(pv.Rejected):
            pv.validate(self.rows[0], wrong)

    def test_public_manifest_and_unadmitted_output_budget(self):
        manifest = pv.strict_json((self.directory / "manifest.json").read_text())
        for entry in manifest["files"]:
            data = (self.directory / entry["path"]).read_bytes()
            self.assertEqual(pv.sha(data), entry["sha256"])
            self.assertEqual(len(data), entry["utf8_bytes"])
        audit = pv.strict_json((self.directory / "content-token-audit.json").read_text())
        self.assertEqual(audit["model_calls"], 0)
        self.assertIsNone(audit["cloud_tokens_avoided"])
        self.assertIsNone(audit["actual_human_correction_seconds"])
        self.assertEqual([r["case_id"] for r in audit["rows"]], [r["id"] for r in self.rows])
        for row in audit["rows"]:
            self.assertEqual(row["canonical_gold_plus_one_eos_fits_512"],
                             row["canonical_gold_content_tokens"] + 1 <= 512)
        self.assertFalse(audit["rows"][2]["canonical_gold_plus_one_eos_fits_512"])
        protocol = pv.strict_json((self.directory / "protocol.json").read_text())
        self.assertFalse(protocol["readiness"])
        self.assertFalse(protocol["prospective_runtime"]["candidate_schema_fits_512_tokens"])
        self.assertEqual(protocol["prospective_runtime"]["model_calls_needed_by_current_deterministic_results"], 0)


if __name__ == "__main__":
    unittest.main()
