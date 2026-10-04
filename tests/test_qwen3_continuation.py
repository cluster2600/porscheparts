"""Integrity attacks and synthetic paired-review fixtures; no model dependencies."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "training/qwen3-continuation-20261003"
SPEC = importlib.util.spec_from_file_location("qwen3_continuation_audit", PACKAGE / "audit.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class DataIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".qwen3-audit-test-", dir=ROOT / "training")
        self.directory = Path(self.temporary.name)
        shutil.copytree(PACKAGE / "data", self.directory / "data")
        shutil.copyfile(PACKAGE / "protocol.json", self.directory / "protocol.json")
        self.data = self.directory / "data"
        self.records = audit.rows(self.data / "train-records.jsonl")
        self.ledger = audit.load(self.data / "source-ledger.json")
        self.manifest = audit.load(self.data / "manifest.json")
        for row in self.records:
            row["provenance"]["retained_license_notice"] = str(
                (self.data / "licenses" / (row["source_id"] + ".txt")).relative_to(ROOT))
        self.save()

    def tearDown(self):
        self.temporary.cleanup()

    def save(self):
        """Rehash mutations so semantic assertions are tested beyond hash checks."""
        (self.data / "train-records.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in self.records), encoding="utf-8")
        write_json(self.data / "source-ledger.json", self.ledger)
        self.manifest["row_sha256"] = {row["id"]: audit.object_sha256(row) for row in self.records}
        self.manifest["files_sha256"] = {name: audit.file_sha256(self.data / name)
                                          for name in self.manifest["files_sha256"]}
        write_json(self.data / "manifest.json", self.manifest)

    def verify(self):
        return audit.verify_data(ROOT, self.directory)

    def test_real_prepared_package_and_profile_equivalence(self):
        report = self.verify()
        self.assertEqual(report["train_rows"], 20)
        self.assertEqual(report["unique_passages"], 10)
        self.assertEqual(report["source_families"], 6)
        self.assertFalse(report["heldout_claim"])
        self.assertFalse(report["independent_expert_validated"])

    def test_rejects_nontraining_source_despite_rehashed_package(self):
        self.ledger["training_sources"][0]["split"] = "development"
        self.save()
        with self.assertRaisesRegex(ValueError, "not assigned to training"):
            self.verify()

    def test_rejects_excerpt_not_contiguous_in_frozen_source(self):
        passage = self.ledger["training_sources"][0]["passages"][0]
        passage["text"] += " Invented dimension 42 mm."
        passage["excerpt_sha256"] = audit.text_sha256(passage["text"])
        self.save()
        with self.assertRaisesRegex(ValueError, "Excerpt differs"):
            self.verify()

    def test_rejects_retired_fidelity_passage_even_from_training_source(self):
        self.ledger["training_sources"][0]["passages"][0]["id"] = "[MET001:p34]"
        self.save()
        with self.assertRaisesRegex(ValueError, "retired"):
            self.verify()

    def test_rejects_unrecorded_or_changed_licence(self):
        self.ledger["training_sources"][0]["license"] = "unknown"
        self.save()
        with self.assertRaisesRegex(ValueError, "licence"):
            self.verify()

    def test_rejects_licence_evidence_hash_change(self):
        self.ledger["training_sources"][0]["license_evidence_sha256"] = "0" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "Licence evidence hash"):
            self.verify()

    def test_rejects_modified_notice_despite_rehashed_files(self):
        (self.data / "licenses/MET001.txt").write_text("Unverified replacement notice\n")
        self.save()
        with self.assertRaisesRegex(ValueError, "Retained licence notice changed"):
            self.verify()

    def test_rejects_duplicate_messages_under_distinct_record_ids(self):
        duplicate = copy.deepcopy(self.records[0])
        duplicate["id"] = "distinct-id-same-messages"
        self.records.append(duplicate)
        self.save()
        with self.assertRaisesRegex(ValueError, "Duplicate training message pair"):
            self.verify()

    def test_rejects_training_profile_drift(self):
        self.records[0]["messages"][0]["content"] += " New policy."
        self.save()
        with self.assertRaisesRegex(ValueError, "Training/inference messages differ"):
            self.verify()

    def test_rejects_raw_question_excerpt_drift(self):
        self.records[0]["raw_messages"][0]["content"] += " Training-only hint."
        self.save()
        with self.assertRaisesRegex(ValueError, "Raw training question"):
            self.verify()

    def test_rejects_false_unseen_claim(self):
        self.records[0]["prior_exposure"] = "unseen_test"
        self.save()
        with self.assertRaisesRegex(ValueError, "Unseen/test claim"):
            self.verify()

    def test_rejects_false_manifest_holdout_claim(self):
        self.manifest["heldout_claim"] = True
        self.save()
        with self.assertRaisesRegex(ValueError, "unseen/test"):
            self.verify()

    def test_rejects_additional_unseen_claim_and_expert_claim(self):
        self.records[0]["unseen_test_claimed"] = True
        self.save()
        with self.assertRaisesRegex(ValueError, "unseen/test"):
            self.verify()
        del self.records[0]["unseen_test_claimed"]
        self.ledger["training_sources"][0]["scientific_approval"] = True
        self.save()
        with self.assertRaisesRegex(ValueError, "scientific validation"):
            self.verify()

    def test_rejects_file_hash_change(self):
        with (self.data / "train-records.jsonl").open("a") as output:
            output.write("\n")
        with self.assertRaisesRegex(ValueError, "Changed pinned file"):
            self.verify()

    def test_rejects_row_hash_change_even_when_file_hash_updated(self):
        self.manifest["row_sha256"][self.records[0]["id"]] = "0" * 64
        write_json(self.data / "manifest.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "Training row hash differs"):
            self.verify()

    def test_rejects_missing_historical_source_pin(self):
        protocol = audit.load(self.directory / "protocol.json")
        del protocol["data_inputs_sha256"]["training/qwen-metal-additive-20261002/grounded-v3/sources.json"]
        write_json(self.directory / "protocol.json", protocol)
        with self.assertRaisesRegex(ValueError, "Required file hashes"):
            self.verify()

    def test_rejects_changed_source_locator(self):
        self.records[0]["provenance"]["locator"]["paragraph_index"] += 1
        self.save()
        with self.assertRaisesRegex(ValueError, "paragraph locator"):
            self.verify()

    def test_rejects_unsafe_manifest_file_path(self):
        self.manifest["files_sha256"]["../outside.txt"] = "0" * 64
        write_json(self.data / "manifest.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "Unsafe relative path"):
            self.verify()


class PairedScientificReviewTest(unittest.TestCase):
    def setUp(self):
        self.protocol = audit.load(PACKAGE / "protocol.json")
        self.protocol_hash = audit.object_sha256(self.protocol)
        roster, generated = [], []
        for index in range(24):
            family = "FIXTURE_A" if index < 16 else "FIXTURE_B"
            messages = [{"role": "user", "content": "Synthetic audit fixture; EXCERPT [" + family + ":p1]: fixture text."}]
            item = {"id": "fixture-" + str(index), "suite": "primary" if index < 16 else "supplemental",
                    "critical": index < 8, "source_family": family,
                    "input_sha256": audit.object_sha256(messages)}
            roster.append(item)
            response = "Synthetic response fixture " + str(index)
            generated.append({**item, "source_id": family, "messages": messages, "response": response,
                              "response_sha256": audit.text_sha256(response), "budget_hit": False})
        self.reservation = {"schema_version": 1, "experiment_id": self.protocol["experiment_id"],
                            "suite": "reserved", "independent_custodian": True,
                            "custodian_id": "synthetic-test-custodian", "roster": roster,
                            "roster_sha256": audit.object_sha256(roster)}
        self.reservation_hash = audit.object_sha256(self.reservation)
        self.base = self.make_run("base", generated)
        self.adapter = self.make_run("adapter", generated)
        self.reviews = self.make_reviews(self.base, set(range(20))) + self.make_reviews(self.adapter, set(range(22)))

    def make_run(self, role, generated):
        return {"schema_version": 1, "status": "completed", "model_role": role, "suite": "reserved",
                "model_id": self.protocol["model_id"], "revision": self.protocol["revision"],
                "profile_name": self.protocol["inference_profile"], "decoding": self.protocol["decoding"],
                "protocol_sha256": self.protocol_hash, "reservation_sha256": self.reservation_hash,
                "model_files_sha256": {"synthetic-weight.bin": "e" * 64, "synthetic-tokenizer.json": "f" * 64},
                "adapter_sha256": "c" * 64, "selection_receipt_sha256": "d" * 64,
                "runtime_sha256": "a" * 64, "roster_sha256": self.reservation["roster_sha256"],
                "rows": copy.deepcopy(generated)}

    def make_reviews(self, run, acceptable):
        return [{"reviewer_id": "synthetic-reviewer-" + str(reviewer), "assistant_independent": True,
                 "run_sha256": audit.object_sha256(run), "rows": [
                     {"id": row["id"], "response_sha256": row["response_sha256"],
                      "acceptable": index in acceptable, "unbacked_citation": False,
                      "unit_condition_failure": False, "causal_failure": False, "critical_failure": False,
                      "reason": "Synthetic integrity assertion; not a scientific grade."}
                     for index, row in enumerate(run["rows"])]} for reviewer in range(2)]

    def aggregate(self):
        return audit.aggregate(self.protocol, self.reservation, self.base, self.adapter, self.reviews,
                               protocol_sha256=self.protocol_hash, reservation_sha256=self.reservation_hash)

    def refresh_run_review_pins(self):
        for review in self.reviews[:2]:
            review["run_sha256"] = audit.object_sha256(self.base)
        for review in self.reviews[2:]:
            review["run_sha256"] = audit.object_sha256(self.adapter)

    def test_registered_pilot_threshold_retains_uncertainty_and_source_groups(self):
        report = self.aggregate()
        self.assertTrue(report["accepted"])
        self.assertEqual(report["counts"]["candidate_acceptable"], 22)
        self.assertEqual(report["counts"]["net_gain"], 2)
        self.assertEqual(report["mcnemar_exact_two_sided_p"], 0.5)
        self.assertIn("no statistically significant", report["mcnemar_scope"])
        self.assertFalse(report["independent_expert_validated"])
        self.assertEqual(report["source_family_counts"]["FIXTURE_B"]["net_gain"], 2)

    def test_acceptance_needs_gain_not_just_candidate_score(self):
        self.reviews = self.make_reviews(self.base, set(range(22))) + self.make_reviews(self.adapter, set(range(22)))
        self.assertIn("minimum_net_gain", self.aggregate()["failures"])

    def test_rejects_missing_base_supplemental(self):
        self.base["rows"] = self.base["rows"][:16]
        with self.assertRaisesRegex(ValueError, "roster is incomplete"):
            self.aggregate()

    def test_rejects_missing_supplemental_reservation(self):
        self.reservation["roster"] = self.reservation["roster"][:16]
        self.reservation["roster_sha256"] = audit.object_sha256(self.reservation["roster"])
        with self.assertRaisesRegex(ValueError, "supplemental"):
            self.aggregate()

    def test_rejects_reordered_pair(self):
        self.adapter["rows"].reverse()
        with self.assertRaisesRegex(ValueError, "reordered"):
            self.aggregate()

    def test_rejects_actual_input_mismatch_even_with_matching_claimed_hash(self):
        self.adapter["rows"][0]["messages"][0]["content"] += " Changed input."
        with self.assertRaisesRegex(ValueError, "Executed input hash"):
            self.aggregate()

    def test_rejects_false_source_group_assignment(self):
        self.adapter["rows"][0]["source_id"] = "ARBITRARY"
        with self.assertRaisesRegex(ValueError, "Source family"):
            self.aggregate()

    def test_rejects_different_runtime_or_decoding(self):
        self.adapter["runtime_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "Paired runtime differs"):
            self.aggregate()
        self.adapter["runtime_sha256"] = self.base["runtime_sha256"]
        self.adapter["decoding"] = {"do_sample": True, "max_new_tokens": 192}
        with self.assertRaisesRegex(ValueError, "Decoding differs"):
            self.aggregate()

    def test_rejects_different_weights_or_missing_reserved_selection(self):
        for field, changed in (("adapter_sha256", "0" * 64),
                               ("model_files_sha256", {"synthetic-other-weight.bin": "0" * 64}),
                               ("selection_receipt_sha256", "0" * 64)):
            with self.subTest(field=field):
                original = self.adapter[field]
                self.adapter[field] = changed
                with self.assertRaisesRegex(ValueError, "weight/selection identity differs"):
                    self.aggregate()
                self.adapter[field] = original
        del self.adapter["selection_receipt_sha256"]
        with self.assertRaisesRegex(ValueError, "Missing reserved weight/selection pin"):
            self.aggregate()

    def test_rejects_empty_or_incomplete_or_duplicate_reviews(self):
        for reviews in ([], self.reviews[:3], [self.reviews[0], self.reviews[0], *self.reviews[2:]]):
            with self.subTest(count=len(reviews)):
                self.reviews = reviews
                with self.assertRaises(ValueError):
                    self.aggregate()

    def test_rejects_review_response_hash_mismatch(self):
        self.reviews[0]["rows"][0]["response_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "another response"):
            self.aggregate()

    def test_rejects_partial_reviews_and_missing_scientific_dimension(self):
        self.reviews[0]["rows"].pop()
        with self.assertRaisesRegex(ValueError, "Incomplete or reordered review"):
            self.aggregate()
        self.reviews = self.make_reviews(self.base, set(range(20))) + self.make_reviews(self.adapter, set(range(22)))
        del self.reviews[0]["rows"][0]["causal_failure"]
        with self.assertRaisesRegex(ValueError, "scientific review flags"):
            self.aggregate()

    def test_disagreement_is_per_response_conservative_failure(self):
        self.reviews = self.make_reviews(self.base, set(range(20))) + self.make_reviews(self.adapter, set(range(24)))
        self.reviews[2]["rows"][18]["acceptable"] = False
        report = self.aggregate()
        self.assertTrue(report["accepted"])
        self.assertEqual(report["counts"]["candidate_review_disagreements"], 1)
        self.assertEqual(report["counts"]["candidate_acceptable"], 23)
        self.assertFalse(report["decisions"]["adapter"][18]["acceptable"])

    def test_critical_disagreement_rejects_even_with_enough_total_passes(self):
        self.reviews = self.make_reviews(self.base, set(range(20))) + self.make_reviews(self.adapter, set(range(24)))
        self.reviews[2]["rows"][0]["acceptable"] = False
        report = self.aggregate()
        self.assertIn("maximum_critical_regressions", report["failures"])
        self.assertIn("maximum_critical_failures", report["failures"])

    def test_scientific_flags_override_acceptable_vote_and_reject(self):
        for flag, maximum in (("unbacked_citation", "maximum_unsupported_citations"),
                              ("unit_condition_failure", "maximum_unit_condition_failures"),
                              ("causal_failure", "maximum_causal_failures")):
            with self.subTest(flag=flag):
                self.reviews = self.make_reviews(self.base, set(range(20))) + self.make_reviews(self.adapter, set(range(24)))
                for review in self.reviews[2:]:
                    review["rows"][19][flag] = True
                report = self.aggregate()
                self.assertIn(maximum, report["failures"])
                self.assertFalse(report["decisions"]["adapter"][19]["acceptable"])

    def test_budget_hit_in_either_arm_blocks_acceptance(self):
        self.base["rows"][23]["budget_hit"] = True
        self.refresh_run_review_pins()
        self.assertIn("maximum_budget_hits", self.aggregate()["failures"])

    def test_rejects_generation_partial_status_and_empty_response(self):
        self.adapter["status"] = "partial"
        with self.assertRaisesRegex(ValueError, "Incomplete generation"):
            self.aggregate()
        self.adapter["status"] = "completed"
        self.adapter["rows"][0]["response"] = ""
        with self.assertRaisesRegex(ValueError, "Empty generated response"):
            self.aggregate()

    def test_rejects_nonindependent_custodian_or_reviewer(self):
        self.reservation["independent_custodian"] = False
        with self.assertRaisesRegex(ValueError, "custodian"):
            self.aggregate()
        self.reservation["independent_custodian"] = True
        self.reviews[0]["assistant_independent"] = False
        with self.assertRaisesRegex(ValueError, "independence"):
            self.aggregate()

    def test_exact_mcnemar_diagnostic_handles_ties_and_symmetry(self):
        self.assertEqual(audit.mcnemar_exact(0, 0), 1)
        self.assertEqual(audit.mcnemar_exact(2, 0), 0.5)
        self.assertEqual(audit.mcnemar_exact(0, 2), 0.5)
        self.assertEqual(audit.mcnemar_exact(3, 3), 1)

    def test_rejects_nonnumeric_protocol_requirement(self):
        self.protocol["evaluation"]["minimum_rows"] = True
        with self.assertRaisesRegex(ValueError, "numeric protocol requirement"):
            self.aggregate()

    def amendment_fixture(self):
        self.reservation['experiment_id'] = 'preserved-initial-experiment'
        self.reservation['questions_sha256'] = '1' * 64
        self.reservation_hash = audit.object_sha256(self.reservation)
        amendment = {'original_reservation_sha256': self.reservation_hash,
                     'protocol_sha256': self.protocol_hash, 'experiment_id': self.protocol['experiment_id'],
                     'roster_sha256': self.reservation['roster_sha256'],
                     'questions_sha256': self.reservation['questions_sha256'],
                     'acceptance_rules_sha256': audit.object_sha256(self.protocol['evaluation']),
                     'runner_sha256': '9' * 64}
        for run in (self.base, self.adapter):
            run.update(reservation_sha256=self.reservation_hash, runner_sha256='9' * 64,
                       reservation_amendment_sha256='8' * 64)
        self.refresh_run_review_pins()
        return amendment

    def aggregate_amended(self, amendment):
        return audit.aggregate(self.protocol, self.reservation, self.base, self.adapter, self.reviews,
                               protocol_sha256=self.protocol_hash, reservation_sha256=self.reservation_hash,
                               reservation_amendment=amendment, reservation_amendment_sha256='8' * 64)

    def test_numerical_amendment_preserves_original_reservation(self):
        amendment = self.amendment_fixture()
        original = copy.deepcopy(self.reservation)
        self.assertTrue(self.aggregate_amended(amendment)['accepted'])
        self.assertEqual(self.reservation, original)
        with self.assertRaisesRegex(ValueError, 'another experiment'):
            self.aggregate()

    def test_amendment_cannot_change_questions_roster_or_acceptance_rules(self):
        amendment = self.amendment_fixture()
        for key in ('questions_sha256', 'roster_sha256', 'acceptance_rules_sha256', 'original_reservation_sha256'):
            with self.subTest(key=key):
                altered = {**amendment, key: '0' * 64}
                with self.assertRaisesRegex(ValueError, 'amendment changed'):
                    self.aggregate_amended(altered)

    def test_amendment_binds_both_executed_runners(self):
        amendment = self.amendment_fixture()
        self.adapter['runner_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Run differs'):
            self.aggregate_amended(amendment)


if __name__ == "__main__":
    unittest.main()
