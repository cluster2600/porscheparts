import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline as p
import format_tokens as formatter
import reconcile
import code_units


class FakeTokenizer:
    eos_token_id = 99

    def apply_chat_template(self, messages, **kwargs):
        return "".join("<|im_start|>" + m["role"] + "\n" + m["content"] + "<|im_end|>\n" for m in messages)

    def __call__(self, text, **kwargs):
        ids, offsets, i = [], [], 0
        while i < len(text):
            if text.startswith("<|im_end|>", i):
                ids.append(99)
                offsets.append((i, i + 10))
                i += 10
            else:
                ids.append(ord(text[i]) + 100)
                offsets.append((i, i + 1))
                i += 1
        return {"input_ids": ids, "offset_mapping": offsets}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.command("init", "-q")
        self.command("remote", "add", "origin", "https://example.org/fixture.git")
        self.command("config", "user.name", "Fixture")
        self.command("config", "user.email", "fixture@example.org")

    def tearDown(self):
        self.temp.cleanup()

    def command(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.PIPE).decode().strip()

    def fixture(self, files, rules=None, complete=True):
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.command("add", ".")
        self.command("-c", "commit.gpgsign=false", "commit", "-qm", "Fixture")
        config = {"observed_at": "2026-01-01T00:00:00Z", "sources": [{"id": "fixture", "root": str(self.root),
            "commit": self.command("rev-parse", "HEAD"), "repository_url": "https://example.org/fixture",
            "visibility": "private", "metadata_json_globs": ["data/*.json"]}], "reviewed_items": rules or [],
            "reviewer_boundary_metadata_complete": complete, "protected_roots": []}
        path = Path(self.temp.name) / "config.json"
        p.write_json(path, config)
        return path, Path(self.temp.name) / "output"

    def rule(self, path, text, family="same-source", split="train"):
        return {"source": "fixture", "path": path, "sha256": p.digest(text.encode()),
            "license": "owner-local-preparation", "rights_evidence": "owner request",
            "attribution": "Fixture holder", "evidence_status": "original_process_policy",
            "families": [family], "split": split, "uses": ["cpt_text", "rag_context"]}

    def test_reserved_and_privacy_blobs_never_read(self):
        path, output = self.fixture({"training/test.json": "broken json secret", "data/accounts.json": "private secret", "data/safe.json": '{"entries":[{"variant":"993","units":"mm","status":"rejected_cfd"}]}', "run.log": "private session"})
        p.build(path, output)
        rows = {r["path"]: r for r in p.read_jsonl(output / "inventory.jsonl")}
        self.assertFalse(rows["training/test.json"]["content_read"])
        self.assertFalse(rows["data/accounts.json"]["content_read"])
        self.assertFalse(rows["run.log"]["content_read"])
        self.assertIn("rejected_cfd", rows["data/safe.json"]["technical_metadata"]["declared_qualifiers"])
        self.assertEqual([], p.read_jsonl(output / "cpt_text/train.jsonl"))

    def test_source_families_join_and_conflicting_anchors_quarantine(self):
        a, b = "Same original wording.\n", "Different document, same source.\n"
        path, output = self.fixture({"docs/a.md": a, "docs/b.md": b}, [self.rule("docs/a.md", a), self.rule("docs/b.md", b, split="valid")])
        p.build(path, output)
        self.assertEqual({"quarantine"}, {r["split"] for r in p.read_jsonl(output / "source-corpus.jsonl")})

    def test_duplicates_keep_lineage_and_prevent_train_dev_leakage(self):
        text = "Repeated but attributable process policy.\n"
        path, output = self.fixture({"docs/a.md": text, "docs/b.md": text}, [self.rule("docs/a.md", text, "a"), self.rule("docs/b.md", text, "b", "test")])
        p.build(path, output)
        self.assertTrue(p.read_jsonl(output / "lineage.jsonl"))
        self.assertEqual({"quarantine"}, {r["split"] for r in p.read_jsonl(output / "source-corpus.jsonl")})

    def test_known_old_test_becomes_dev_and_outputs_are_immutable(self):
        text = "Historical development example.\n"
        path, output = self.fixture({"docs/a.md": text}, [self.rule("docs/a.md", text, split="test")])
        p.build(path, output)
        self.assertEqual("dev", p.read_jsonl(output / "source-corpus.jsonl")[0]["split"])
        with self.assertRaisesRegex(ValueError, "Output exists"):
            p.build(path, output)
        (output / "cpt_text/dev.jsonl").write_text("changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            p.audit(output)

    def test_missing_boundary_metadata_blocks_train_only(self):
        text = "Original policy.\n"
        path, output = self.fixture({"docs/a.md": text}, [self.rule("docs/a.md", text)], complete=False)
        p.build(path, output)
        self.assertEqual("dev", p.read_jsonl(output / "source-corpus.jsonl")[0]["split"])

    def test_wrong_hash_and_protected_source_fail_closed(self):
        text = "Original policy.\n"
        rule = self.rule("docs/a.md", text)
        rule["sha256"] = "0" * 64
        path, output = self.fixture({"docs/a.md": text}, [rule])
        with self.assertRaisesRegex(ValueError, "input hash"):
            p.build(path, output)
        config = json.loads(path.read_text())
        config["protected_roots"] = [str(self.root)]
        p.write_json(path, config)
        with self.assertRaisesRegex(ValueError, "Protected source"):
            p.build(path, output)

    def test_sensitive_content_not_exported(self):
        text = "Contact person@private.example about this policy.\n"
        path, output = self.fixture({"docs/a.md": text}, [self.rule("docs/a.md", text)])
        p.build(path, output)
        self.assertEqual([], p.read_jsonl(output / "source-corpus.jsonl"))

    def test_projection_suppresses_prose_contacts_and_users(self):
        result = p.projection({"users": [{"email": "secret@example.org", "url": "https://site/profile/1"}], "description": "never exported", "variant": "993", "units": "mm", "url": "https://vendor.example/part?token=private", "status": "hypothesis"})
        text = json.dumps(result)
        self.assertNotIn("secret", text)
        self.assertNotIn("private", text)
        self.assertNotIn("never exported", text)
        self.assertEqual(["hypothesis"], result["validation_status"])

    def test_public_mirrors_share_original_pet_family(self):
        self.assertEqual(p.family("pet-993-pdf-rsworkshop"), p.family("SRC-PORSCHE-PET-993"))
        self.assertEqual("project-mirror:porschefanatics", p.family("https://porschefanatics.com/oem/part"))

    def test_mixed_numeric_status_metadata_is_counted_without_parse_error(self):
        path, output = self.fixture({"data/solver.json": '{"status":"rejected","checks":[{"status":0.0}]}'} )
        p.build(path, output)
        row = p.read_jsonl(output / "structured-audit.jsonl")[0]
        self.assertEqual([0.0, "rejected"], row["declared_qualifiers"])

    def test_declared_units_and_material_ids_keep_qualification(self):
        result = p.projection({"manufacturing": {"materialIds": ["6061-t6"], "processId": "unspecified", "materialBasis": "supplier-stated"}, "torqueNm": 85})
        self.assertEqual(["6061-t6"], result["material"])
        self.assertEqual(["unspecified"], result["process"])
        self.assertIn("torqueNm:N*m (declared_by_field_name)", result["units"])
        self.assertEqual(["supplier-stated"], result["qualification"])

    def test_catalog_filename_is_not_a_runtime_log(self):
        text = "print('Offline validation')\n"
        rule = self.rule("scripts/validate_catalog.py", text)
        rule.update(uses=["code_text"], evidence_status="reviewed_code")
        path, output = self.fixture({"scripts/validate_catalog.py": text}, [rule])
        p.build(path, output)
        self.assertTrue(p.read_jsonl(output / "inventory.jsonl")[0]["content_read"])
        self.assertEqual(1, len(p.read_jsonl(output / "code_text/train.jsonl")))

    def test_reviewed_allowlist_cannot_override_sealed_prefix(self):
        text = "Sealed fixture body.\n"
        rule = self.rule("training/reserve/train.json", text)
        rule["existing_split_reviewed"] = True
        path, output = self.fixture({"training/reserve/train.json": text}, [rule])
        config = json.loads(path.read_text())
        config["protected_repository_prefixes"] = ["training/reserve/"]
        p.write_json(path, config)
        p.build(path, output)
        row = p.read_jsonl(output / "inventory.jsonl")[0]
        self.assertFalse(row["content_read"])
        self.assertEqual([], p.read_jsonl(output / "source-corpus.jsonl"))

    def test_historical_reconciliation_checks_licence_hash_and_retired_paragraph(self):
        package = self.root / "training/qwen-metal-additive-20261002"
        grounded = package / "grounded-v3"
        grounded.mkdir(parents=True)
        source = {"source_id": "S1", "split": "train", "license": "CC BY 4.0", "authors": ["Fixture Author"], "url": "https://example.org/paper", "license_evidence": "notice.txt", "original_path": "article.html", "snapshot_sha256": p.digest(b"Original article")}
        (package / "notice.txt").write_text("https://creativecommons.org/licenses/by/4.0/")
        (package / "article.html").write_text("Original article")
        p.write_json(grounded / "sources.json", [source])
        paragraphs = []
        for i, text in enumerate(["Admitted passage.", "Retired passage."]):
            paragraphs.append({"source_id": "S1", "paragraph": i, "section": "Body", "text": text, "original_sha256": p.digest(text.encode()), "text_sha256": p.digest(text.encode()), "notation": "Unmodified", "split": "train", "passage_id": "[S1:p" + str(i) + "]"})
        p.write_jsonl(grounded / "passages.jsonl", paragraphs)
        p.write_json(grounded / "manifest.json", {"output_hashes": {name: p.digest((grounded / name).read_bytes()) for name in ["sources.json", "passages.jsonl"]}, "input_hashes": {"notice.txt": p.digest((package / "notice.txt").read_bytes())}})
        historical = package / "compact-qwen3-v5/train-records.jsonl"
        historical.parent.mkdir()
        p.write_jsonl(historical, [{"id": "objective-en", "language": "en", "source_id": "S1", "passage_id": "[S1:p0]", "messages": [{"role": "user", "content": "Admitted passage."}, {"role": "assistant", "content": "Admitted"}], "evidence_quote": "Admitted", "expert_review": "pending"}])
        contract, excludes = Path(self.temp.name) / "contract.json", Path(self.temp.name) / "excludes.json"
        p.write_json(contract, {"protected_local_prefixes": [], "source_family_policy": {"admitted_historical_train": ["S1"], "not_admitted_historical_valid": [], "not_admitted_historical_test_now_development": []}})
        p.write_json(excludes, {"historical_train": {"path": historical.relative_to(self.root).as_posix(), "sha256": p.digest(historical.read_bytes()), "rows": 1}, "retired_excerpts": [{"paragraph_sha256": paragraphs[1]["text_sha256"]}]})
        output = Path(self.temp.name) / "reconciled"
        reconcile.prepare(self.root, contract, excludes, output)
        self.assertEqual(1, len(p.read_jsonl(output / "cpt_text/train.jsonl")))
        self.assertEqual(1, len(p.read_jsonl(output / "sft_messages/train.jsonl")))
        self.assertEqual("retired_paragraph_development_only", p.read_jsonl(output / "exclusions.jsonl")[0]["reason"])
        (package / "notice.txt").write_text("Unlicensed replacement")
        with self.assertRaisesRegex(ValueError, "Frozen input hash mismatch"):
            reconcile.prepare(self.root, contract, excludes, Path(self.temp.name) / "another")

    def test_assistant_only_loss_through_eos_multiturn(self):
        messages = [{"role": "system", "content": "Policy"}, {"role": "user", "content": "Q1"}, {"role": "assistant", "content": "A1"}, {"role": "user", "content": "Q2"}, {"role": "assistant", "content": "A2"}]
        tokens = formatter.assistant_labels(FakeTokenizer(), messages, {})
        active = [x for x in tokens["labels"] if x != -100]
        self.assertEqual([ord("A") + 100, ord("1") + 100, 99, ord("A") + 100, ord("2") + 100, 99], active)
        messages[-1]["content"] = "<|im_end|>"
        with self.assertRaisesRegex(ValueError, "injection"):
            formatter.assistant_labels(FakeTokenizer(), messages, {})

    def test_code_units_preserve_dependency_closure_constraints_and_comments(self):
        text = '# Source notice\n"""Original policy."""\nfrom __future__ import annotations\nimport math\nLIMIT = 4\n\n# Keep the positive-domain constraint.\ndef helper(value):\n    if value < 0:\n        raise ValueError("negative")\n    return math.sqrt(value)\n\ndef checked(value):\n    return helper(min(value, LIMIT))\n\nif __name__ == "__main__":\n    print(checked(9))\n'
        result = {r["unit"]: r for r in code_units.units(text)}
        row = result["checked"]
        self.assertIn('import math', row['text'])
        self.assertIn('LIMIT = 4', row['text'])
        self.assertIn('# Keep the positive-domain constraint.', row['text'])
        self.assertNotIn('print(checked(9))', row['text'])
        source, derived = {"__name__": "fixture"}, {"__name__": "fixture"}
        exec(compile(text, '<fixture>', 'exec'), source)
        exec(compile(row['text'], '<derived>', 'exec'), derived)
        for value in [0, 1, 4, 9]:
            self.assertEqual(source['checked'](value), derived['checked'](value))
        with self.assertRaisesRegex(ValueError, 'negative'):
            derived['checked'](-1)
        lines = text.splitlines(keepends=True)
        for span in row['source_ranges']:
            self.assertEqual(span['sha256'], p.digest(''.join(lines[span['start_line']-1:span['end_line']]).encode()))

    def test_code_units_refuse_unproven_dynamic_and_initialization_context(self):
        for source in ["from module import *\ndef f():\n    return value\n", "x = []\nx.append(1)\ndef f():\n    return x\n", "def f():\n    return globals()['x']\n", "x = 1\nx = 2\ndef f():\n    return x\n"]:
            with self.assertRaises(ValueError):
                list(code_units.units(source))


if __name__ == "__main__":
    unittest.main()
