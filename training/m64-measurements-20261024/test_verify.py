"""Focused metadata preservation, partition, corruption and rebuild checks."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


class M64MeasurementTrainingTests(unittest.TestCase):
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

    def refresh_input_hash(self, root, filename):
        import hashlib
        repository = root.parents[1]
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["inputs"]:
            if entry["path"] == filename:
                entry["sha256"] = hashlib.sha256((repository / filename).read_bytes()).hexdigest()
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_qualified_scope_citations_exclusions_and_missing_grade_survive(self):
        result = self.command(ROOT, "verify.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertTrue(parsed["combined_prior_partition_isolation"])
        self.assertEqual(parsed["frozen_prior_packs"], ["993-turbo-20261002", "mezger-turbo-materials-20261003", "mezger-german-sources-20261003"])
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
                metadata = fact["measurement_metadata"]
                self.assertEqual(passages[fact["id"]]["measurement_metadata"], metadata)
                canonical = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                self.assertIn(canonical, text)
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

    def test_second_frozen_pack_partition_change_is_rejected_with_refreshed_input_hash(self):
        root = self.copy_pack()
        filename = "training/mezger-turbo-materials-20261003/split-ledger.json"
        path = root.parents[1] / filename
        ledger = json.loads(path.read_text(encoding="utf-8"))
        record = next(row for row in ledger["records"] if "porsche-factory-and-archive" in row["source_families"])
        record["split"] = "valid"
        path.write_text(json.dumps(ledger), encoding="utf-8")
        self.refresh_input_hash(root, filename)
        result = self.command(root, "verify.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("conflicting", result.stderr)

    def test_publisher_and_retailer_mirrors_use_conservative_families(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("measurement_builder_policy_test", ROOT / "prepare.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        policy = builder.prior_policy()
        examples = [
            ({"source_id": "SRC-TEST-MELETT-DIRECT", "title": "Turbo dimensions", "publisher": "Melett Ltd",
              "url": "https://www.melett.com/catalogue.pdf", "source_type": "manufacturer"}, "melett.com"),
            ({"source_id": "SRC-TEST-MELETT-MIRROR", "title": "Melett technical dimensions", "publisher": "Turbo retailer",
              "url": "https://retailer.example/media/catalogue.pdf", "source_type": "manufacturer"}, "melett.com"),
            ({"source_id": "SRC-TEST-FIA", "title": "Homologation form", "publisher": "FIA",
              "url": "https://historicdb.fia.com/form.pdf", "source_type": "official"}, "fia-homologation"),
            ({"source_id": "SRC-TEST-TTE-DE", "title": "TTE650", "publisher": "TTE24",
              "url": "https://tte24.net/product", "source_type": "marketplace"}, "tte-products"),
            ({"source_id": "SRC-TEST-RUF-DE", "title": "RUF engine", "publisher": "RUF",
              "url": "https://ruf-automobile.de/model", "source_type": "manufacturer"}, "ruf-993"),
            ({"source_id": "SRC-TEST-MAHLE-DE", "title": "Pistons", "publisher": "MAHLE",
              "url": "https://mahle-aftermarket.com/data.pdf", "source_type": "manufacturer"}, "us.mahle.com"),
            ({"source_id": "SRC-TEST-PORSCHE-MIRROR", "title": "Repair manual", "publisher": "Porsche AG",
              "url": "https://archive.example/manual.pdf", "source_type": "official"}, "porsche-factory-and-archive"),
        ]
        for source, expected in examples:
            with self.subTest(source=source["source_id"]):
                self.assertEqual(builder.source_family(source, policy), expected)

    def test_third_frozen_pack_partition_change_is_rejected_with_refreshed_hash(self):
        root = self.copy_pack()
        filename = "training/mezger-german-sources-20261003/split-ledger.json"
        path = root.parents[1] / filename
        ledger = json.loads(path.read_text(encoding="utf-8"))
        record = next(row for row in ledger["records"] if "porsche-factory-and-archive" in row["source_families"])
        record["split"] = "valid"
        path.write_text(json.dumps(ledger), encoding="utf-8")
        self.refresh_input_hash(root, filename)
        result = self.command(root, "verify.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("conflicting", result.stderr)

    def test_provenance_cannot_drop_measurement_tolerance_with_fresh_hash(self):
        root = self.copy_pack()
        path = root / "provenance.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["measurement_metadata"].pop("tolerance")
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        self.refresh_output_hash(root, "provenance.jsonl")
        result = self.command(root, "verify.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Provenance measurement metadata changed", result.stderr)

    def test_cpt_cannot_omit_measurement_metadata_even_with_rehashed_payload_and_provenance(self):
        import hashlib
        root = self.copy_pack()
        provenance_path = root / "provenance.jsonl"
        provenance = [json.loads(line) for line in provenance_path.read_text().splitlines()]
        record = next(row for row in provenance if row["dataset"] == "cpt")
        filename = "cpt_text/" + record["split"] + ".jsonl"
        path = root / filename
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        target = rows[record["row_index"]]
        canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        target["text"] = target["text"].replace(" Measurement metadata: " + canonical(record["measurement_metadata"]) + ".", "")
        record["content_sha256"] = hashlib.sha256(canonical(target).encode()).hexdigest()
        path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")
        provenance_path.write_text("".join(canonical(row) + "\n" for row in provenance), encoding="utf-8")
        self.refresh_output_hash(root, filename)
        self.refresh_output_hash(root, "provenance.jsonl")
        result = self.command(root, "verify.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CPT content or schema mismatch", result.stderr)

    def test_unknown_extra_measurement_definitions_survive_authored_text(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("measurement_builder_metadata_test", ROOT / "prepare.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        metadata = {"measurement_kind": "service_limit", "datum": "First internal shoulder", "conditions": "Documented check only",
                    "tolerance": {"minimum_mm": 33, "maximum_mm": None}, "variant_basis": "Specific documented engine revision",
                    "additional_manufacturer_definition": {"repair_permission": "Do not machine bore", "sign_convention": "positive depth"}}
        fact = {"id": "M64-TEST-METADATA", "application": "Fixture only", "component": "bore", "parameter": "minimum depth",
                "value": 33, "unit": "mm", "evidence_status": "fixture", "training_eligibility": "qualified_only", "caveat": "Not a physical measurement",
                "measurement_metadata": metadata}
        self.assertIn(builder.canonical(metadata), builder.record_text(fact))
        missing = dict(fact, measurement_metadata={key: value for key, value in metadata.items() if key != "tolerance"})
        with self.assertRaisesRegex(ValueError, "Missing measurement metadata fields"):
            builder.record_text(missing)

    def test_new_ledger_cannot_forge_an_independent_source_family(self):
        root = self.copy_pack()
        path = root / "split-ledger.json"
        ledger = json.loads(path.read_text(encoding="utf-8"))
        record = ledger["records"][0]
        record["source_families"] = ["forged-independent-document"]
        record["component"] = "forged-independent-document"
        path.write_text(json.dumps(ledger), encoding="utf-8")
        self.refresh_output_hash(root, "split-ledger.json")
        result = self.command(root, "verify.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue("Source-family policy mismatch" in result.stderr
                        or "Reviewed claim connected component mismatch" in result.stderr, result.stderr)

    def test_accepted_ids_from_third_frozen_pack_remain_reserved(self):
        root = self.copy_pack()
        repository = root.parents[1]
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        filename = next(entry["path"] for entry in manifest["inputs"] if entry["path"].endswith("/facts.json"))
        path = repository / filename
        facts = json.loads(path.read_text(encoding="utf-8"))
        prior = json.loads((repository / "training/mezger-german-sources-20261003/split-ledger.json").read_text())["records"]
        facts["records"][0]["id"] = prior[0]["record_id"]
        path.write_text(json.dumps(facts), encoding="utf-8")
        self.refresh_input_hash(root, filename)
        result = self.command(root, "prepare.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate record ID in combined packs", result.stderr)

    def test_trainer_train_alias_cannot_be_redirected_to_holdout_with_refreshed_hash(self):
        root = self.copy_pack()
        path = root / "dataset_info.json"
        registration = json.loads(path.read_text(encoding="utf-8"))
        registration["m64_measurements_sft_train"]["file_name"] = "sft_messages/test.jsonl"
        registration["m64_measurements_cpt_train"]["file_name"] = "cpt_text/test.jsonl"
        path.write_text(json.dumps(registration), encoding="utf-8")
        self.refresh_output_hash(root, "dataset_info.json")
        result = self.command(root, "verify.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Trainer dataset registration mismatch", result.stderr)

    def test_output_hash_manifest_cannot_omit_a_generated_artifact(self):
        root = self.copy_pack()
        path = root / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["outputs"] = [entry for entry in manifest["outputs"] if entry["path"] != "dataset_info.json"]
        path.write_text(json.dumps(manifest), encoding="utf-8")
        result = self.command(root, "verify.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Generated-output closure mismatch", result.stderr)

    def test_previously_excluded_ids_remain_reserved(self):
        root = self.copy_pack()
        repository = root.parents[1]
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        filename = next(entry["path"] for entry in manifest["inputs"] if entry["path"].endswith("/facts.json"))
        path = repository / filename
        facts = json.loads(path.read_text(encoding="utf-8"))
        old_exclusions = json.loads((repository / "training/mezger-turbo-materials-20261003/excluded.json").read_text())["records"]
        facts["records"][0]["id"] = old_exclusions[0]["record_id"]
        path.write_text(json.dumps(facts), encoding="utf-8")
        self.refresh_input_hash(root, filename)
        result = self.command(root, "prepare.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate record ID in combined packs", result.stderr)


if __name__ == "__main__":
    unittest.main()
