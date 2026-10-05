"""Research training-pack invariants: provenance and failed-closed corruption."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "training/993-turbo-20261002"
SPEC = importlib.util.spec_from_file_location("verify_993_training", PACK / "verify.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class ResearchTrainingPackTests(unittest.TestCase):
    def copy_pack(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        destination = Path(temporary.name) / "training/pack"
        shutil.copytree(PACK, destination)
        return destination

    def update_output_hash(self, root, filename):
        manifest = VERIFY.read_json(root / "manifest.json")
        for entry in manifest["outputs"]:
            if entry["path"] == filename:
                entry["sha256"] = VERIFY.digest((root / filename).read_bytes())
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_pack_closes_provenance_and_keeps_hypothesis_out(self):
        result = VERIFY.verify()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["counts"]["cpt"], {"train": 237, "valid": 3, "test": 8})
        ids = {record["id"] for record in VERIFY.read_jsonl(PACK / "passages.jsonl")}
        self.assertNotIn("ENGINE-D163", ids)
        self.assertTrue(all(f"UNKNOWN-{number:03d}" in ids for number in range(1, 20)))
        self.assertFalse(result["tokenization_or_model_quality_assessed"])

    def test_altered_dataset_fails_hash_check(self):
        root = self.copy_pack()
        with (root / "cpt_text/train.jsonl").open("a", encoding="utf-8") as stream:
            stream.write('{"text":"unreviewed invented operating speed"}\n')
        with self.assertRaisesRegex(ValueError, "Output hash mismatch"):
            VERIFY.verify(root, check_input_hashes=False)

    def test_source_reused_across_holdouts_is_rejected_even_with_fresh_hash(self):
        root = self.copy_pack()
        ledger = VERIFY.read_json(root / "split-ledger.json")
        train = next(entry for entry in ledger["records"] if entry["split"] == "train")
        valid = next(entry for entry in ledger["records"] if entry["split"] == "valid")
        valid["source_ids"].append(train["source_ids"][0])
        (root / "split-ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
        self.update_output_hash(root, "split-ledger.json")
        with self.assertRaisesRegex(ValueError, "Cross-partition source leakage"):
            VERIFY.verify(root, check_input_hashes=False)

    def test_invalid_message_roles_fail_independently_of_file_hash(self):
        root = self.copy_pack()
        path = root / "sft_messages/valid.jsonl"
        rows = VERIFY.read_jsonl(path)
        rows[0]["messages"][2]["role"] = "user"
        path.write_text("".join(VERIFY.canonical(row) + "\n" for row in rows), encoding="utf-8")
        self.update_output_hash(root, "sft_messages/valid.jsonl")
        with self.assertRaisesRegex(ValueError, "Invalid native message roles"):
            VERIFY.verify(root, check_input_hashes=False)


if __name__ == "__main__":
    unittest.main()
