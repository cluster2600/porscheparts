"""Focused corruption, partition, uncertainty and reproducibility checks."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


class MaterialsTrainingTests(unittest.TestCase):
    def copy_pack(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        repository = Path(directory.name) / "repository"
        destination = repository / ROOT.relative_to(REPO)
        shutil.copytree(ROOT, destination, ignore=shutil.ignore_patterns("__pycache__"))
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["inputs"]:
            path = repository / entry["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / entry["path"], path)
        return destination

    def command(self, root, name):
        return subprocess.run([sys.executable, str(root / name)], capture_output=True, text=True, check=False)

    def refresh_output_hash(self, root, filename):
        import hashlib
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["outputs"]:
            if entry["path"] == filename:
                entry["sha256"] = hashlib.sha256((root / filename).read_bytes()).hexdigest()
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_qualified_scope_citations_exclusions_and_missing_grade_survive(self):
        result = self.command(ROOT, "verify.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertTrue(parsed["combined_prior_partition_isolation"])
        self.assertFalse(parsed["model_or_token_quality_assessed"])
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        facts_path = next(entry["path"] for entry in manifest["inputs"] if entry["path"].endswith("/facts.json"))
        facts = json.loads((REPO / facts_path).read_text(encoding="utf-8"))["records"]
        passages = {row["id"]: row for row in [json.loads(line) for line in (ROOT / "passages.jsonl").read_text().splitlines()]}
        for fact in facts:
            if fact["training_eligibility"] == "exclude":
                self.assertNotIn(fact["id"], passages)
            else:
                text = passages[fact["id"]]["text"]
                self.assertIn(fact["application"], text)
                if fact.get("caveat"):
                    self.assertIn(fact["caveat"], text)
                if fact["value"] is None:
                    self.assertIn("not established in this review", text)
                    self.assertNotIn(" as None", text)

    def test_modified_target_fails_input_independent_hash_check(self):
        root = self.copy_pack()
        with (root / "cpt_text/train.jsonl").open("a", encoding="utf-8") as stream:
            stream.write('{"text":"Unsupported factory alloy claim"}\n')
        result = self.command(root, "verify.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outputs hash mismatch", result.stderr)

    def test_frozen_factory_family_cannot_be_moved_to_holdout_even_with_fresh_hash(self):
        root = self.copy_pack()
        ledger = json.loads((root / "split-ledger.json").read_text(encoding="utf-8"))
        record = next(row for row in ledger["records"] if "porsche-factory-and-archive" in row["source_families"])
        record["split"] = "valid"
        (root / "split-ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
        self.refresh_output_hash(root, "split-ledger.json")
        result = self.command(root, "verify.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("conflicting", result.stderr)

    def test_rebuild_is_byte_identical_in_an_isolated_export(self):
        root = self.copy_pack()
        paths = [path for path in root.rglob("*") if path.is_file() and path.suffix in {".json", ".jsonl"}]
        before = {path.relative_to(root): path.read_bytes() for path in paths}
        result = self.command(root, "prepare.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, {relative: (root / relative).read_bytes() for relative in before})
        check = self.command(root, "verify.py")
        self.assertEqual(check.returncode, 0, check.stderr)


if __name__ == "__main__":
    unittest.main()
