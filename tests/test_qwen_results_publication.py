"""Protect immutable judgments and distinctions in the public negative-result report."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "training/qwen-results-20261003"
spec = importlib.util.spec_from_file_location("publication_check", PACKAGE / "check_publication.py")
CHECK = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CHECK)


class PublicationEvidenceTests(unittest.TestCase):
    def test_original_grades_and_separate_correction_recompute(self):
        result = CHECK.e_scores(PACKAGE)
        self.assertEqual(result["paired_wins"], 0)
        self.assertEqual(result["paired_losses"], 0)
        for scores in result["arms"].values():
            self.assertEqual(scores, {"individual": [15, 16], "initial": 15, "post_claim": 14})

    def test_original_blind_acceptance_cannot_be_silently_corrected(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "publication"
            shutil.copytree(PACKAGE, copy)
            p = copy / "e/blind/reviewer-1.json"
            value = json.loads(p.read_text())
            for row in value["rows"]:
                if row["id"] == "fidelity-09":
                    row["acceptable"] = False
            p.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "correction was not additional"):
                CHECK.e_scores(copy)

    def test_binding_disagreement_is_not_scored(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "publication"
            shutil.copytree(PACKAGE, copy)
            p = copy / "e/blind/reviewer-2.json"
            value = json.loads(p.read_text())
            value["rows"][0]["response_sha256"] = "0" * 64
            p.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "response binding"):
                CHECK.e_scores(copy)

    def test_source_or_model_payload_keys_are_rejected(self):
        for key in CHECK.FORBIDDEN_PAYLOAD_KEYS:
            with self.subTest(key=key), self.assertRaises(ValueError):
                CHECK.check_payload_keys({"nested": [{key: "withheld"}]})

    def test_hash_only_response_metadata_is_permitted(self):
        CHECK.check_payload_keys({"response_sha256": "0" * 64, "reason": "An original assistant judgment."})

    def test_public_closed_manifest_and_scope_pass(self):
        result = CHECK.check(PACKAGE)
        self.assertFalse(result["coder_static_pass"])
        self.assertFalse(result["control_strict_cpu_pass"])
        self.assertFalse(result["model_or_native_execution"])


if __name__ == "__main__":
    unittest.main()
