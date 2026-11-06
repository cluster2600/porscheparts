"""Baseline 2026-11-06 of the bionic turbo F1 (issue #394).

These tests run no OpenFOAM, Docker or turbo case. They check that the committed
baseline is current and that a stale or mismatched binary or configuration hash
cannot open a gate.
"""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "twins/bionic-turbo-f1/baseline-20261106"
SPEC = importlib.util.spec_from_file_location("bionic_turbo_baseline_20261106", BASE / "baseline.py")
baseline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(baseline)

IMAGE = "docker.io/opencfd/openfoam-run@sha256:" + "1" * 64
SOLVER = "2" * 64
OTHER = "3" * 64


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SyntheticGate(unittest.TestCase):
    """A self-contained repository where one gate can be opened by an exact attestation."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "cfg").mkdir()
        self.config = self.repo / "cfg/case.dict"
        self.config.write_bytes(b"writePrecision 16;\n")
        self.run_receipt = self.repo / "cfg/run-receipt.json"
        self.run_receipt.write_bytes(b'{"exit_code": 0}\n')
        self.review = self.repo / "cfg/review.json"
        self.review.write_bytes(b'{"reviewer": "synthetic"}\n')
        self.matrix = {"rows": [
            {"id": "rt", "variant": "OpenCFD", "version": "v2406", "platform": "linux/arm64",
             "identity": {"image": IMAGE}, "executables": {"solver": SOLVER, "mesher": "unknown"},
             "qualification": "historical_evidence_runtime_not_qualified_for_turbo_cfd"},
            {"id": "foundation", "variant": "OpenFOAM Foundation", "version": "13", "platform": "linux/amd64",
             "identity": {"image": "local/cadsim@sha256:" + "4" * 64}, "executables": {"solver": SOLVER},
             "qualification": "prohibited_for_turbo_substitution"},
        ]}
        receipt = {"path": "cfg/run-receipt.json", "sha256": sha(self.run_receipt.read_bytes())}
        self.ledger = {"gates": [
            {"id": "P", "kind": "software", "state": "engineering_passed", "prerequisites": [],
             "required_bindings": [], "config_pins": [], "receipts": [receipt], "blockers": []},
            {"id": "G", "kind": "numerical", "state": "not_started", "prerequisites": ["P"],
             "required_bindings": [{"runtime": "rt", "field": "identity.image"},
                                   {"runtime": "rt", "field": "executables.solver"}],
             "config_pins": [{"path": "cfg/case.dict", "sha256": sha(self.config.read_bytes())}],
             "receipts": [], "blockers": []},
            {"id": "C", "kind": "physical_correlation", "state": "not_started", "prerequisites": ["P"],
             "required_bindings": [], "config_pins": [], "receipts": [], "blockers": []},
        ]}
        self.attestation = {
            "gate": "G",
            "runtime": {"rt": {"variant": "OpenCFD", "version": "v2406", "platform": "linux/arm64",
                               "identity": {"image": IMAGE}, "executables": {"solver": SOLVER}}},
            "config_sha256": {"cfg/case.dict": sha(self.config.read_bytes())},
            "receipts": [receipt],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def evaluate(self, gate="G", ledger=None, matrix=None, attestation=None):
        return baseline.evaluate_gate(gate, ledger or self.ledger, matrix or self.matrix,
                                      attestation or self.attestation, self.repo)

    def assertRefused(self, result, fragment):
        may_open, reasons = result
        self.assertFalse(may_open)
        self.assertTrue(any(fragment in r for r in reasons), reasons)

    def test_exact_attestation_opens_the_gate(self):
        self.assertEqual(self.evaluate(), (True, []))

    def test_mismatched_binary_hash_cannot_open(self):
        attestation = copy.deepcopy(self.attestation)
        attestation["runtime"]["rt"]["executables"]["solver"] = OTHER
        self.assertRefused(self.evaluate(attestation=attestation), "rt.executables.solver mismatch")

    def test_mismatched_image_digest_cannot_open(self):
        attestation = copy.deepcopy(self.attestation)
        attestation["runtime"]["rt"]["identity"]["image"] = IMAGE[:-1] + "f"
        self.assertRefused(self.evaluate(attestation=attestation), "rt.identity.image mismatch")

    def test_stale_configuration_cannot_open_even_with_the_pinned_hash(self):
        self.config.write_bytes(b"writePrecision 12;\n")
        self.assertRefused(self.evaluate(), "cfg/case.dict is stale")

    def test_mismatched_configuration_hash_cannot_open(self):
        attestation = copy.deepcopy(self.attestation)
        attestation["config_sha256"]["cfg/case.dict"] = OTHER
        self.assertRefused(self.evaluate(attestation=attestation), "cfg/case.dict mismatch")

    def test_unattested_configuration_cannot_open(self):
        attestation = copy.deepcopy(self.attestation)
        attestation["config_sha256"] = {}
        self.assertRefused(self.evaluate(attestation=attestation), "not attested")

    def test_silent_foundation_substitution_cannot_open(self):
        attestation = copy.deepcopy(self.attestation)
        attestation["runtime"]["rt"].update(variant="OpenFOAM Foundation", version="13", platform="linux/amd64")
        self.assertRefused(self.evaluate(attestation=attestation), "substituted")

    def test_unknown_pinned_identity_cannot_open(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["gates"][1]["required_bindings"].append({"runtime": "rt", "field": "executables.mesher"})
        attestation = copy.deepcopy(self.attestation)
        attestation["runtime"]["rt"]["executables"]["mesher"] = OTHER
        self.assertRefused(self.evaluate(ledger=ledger, attestation=attestation), "unpinned identity")

    def test_prohibited_runtime_cannot_open(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["gates"][1]["required_bindings"] = [{"runtime": "foundation", "field": "executables.solver"}]
        attestation = copy.deepcopy(self.attestation)
        attestation["runtime"] = {"foundation": copy.deepcopy(self.matrix["rows"][1])}
        self.assertRefused(self.evaluate(ledger=ledger, attestation=attestation), "prohibited")

    def test_stale_or_missing_execution_receipt_cannot_open(self):
        self.run_receipt.write_bytes(b'{"exit_code": 1}\n')
        self.assertRefused(self.evaluate(), "is stale")
        attestation = copy.deepcopy(self.attestation)
        attestation["receipts"] = []
        self.assertRefused(self.evaluate(attestation=attestation), "no execution receipt")

    def test_prerequisite_must_be_engineering_passed(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["gates"][0]["state"] = "investigated"
        self.assertRefused(self.evaluate(ledger=ledger), "prerequisite P is investigated")

    def test_open_blocker_and_failed_state_refuse(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["gates"][1]["blockers"] = [{"id": "missing-measurement"}]
        self.assertRefused(self.evaluate(ledger=ledger), "open blocker: missing-measurement")
        ledger["gates"][1].update(state="failed", blockers=[])
        self.assertRefused(self.evaluate(ledger=ledger), "failed gate stays failed")

    def test_physical_correlation_requires_review(self):
        attestation = copy.deepcopy(self.attestation)
        attestation["gate"] = "C"
        self.assertRefused(self.evaluate(gate="C", attestation=attestation), "professional engineering review")
        attestation["review"] = {"path": "cfg/review.json", "sha256": sha(self.review.read_bytes())}
        self.assertEqual(self.evaluate(gate="C", attestation=attestation), (True, []))

    def test_claims_need_a_verified_receipt_or_explicit_unknown(self):
        good = {"claim": "x", "receipts": [{"path": "cfg/case.dict", "sha256": sha(self.config.read_bytes())}]}
        unknown = {"claim": "y", "unknown": {"reason": "host not reachable"}}
        self.assertEqual(baseline.check_claims([good, unknown], "t", self.repo), [])
        self.assertTrue(baseline.check_claims([{"claim": "z"}], "t", self.repo))
        self.assertTrue(baseline.check_claims([{"claim": "z", "unknown": {"reason": ""}}], "t", self.repo))
        stale = copy.deepcopy(good)
        stale["receipts"][0]["sha256"] = OTHER
        self.assertTrue(any("stale" in e for e in baseline.check_claims([stale], "t", self.repo)))

    def test_ledger_rejects_unsupported_passes(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["gates"].append({"id": "R", "kind": "manufacturing_release", "state": "not_started",
                                "prerequisites": [], "required_bindings": [], "config_pins": [],
                                "receipts": [], "blockers": []})
        self.assertEqual(baseline.check_ledger(ledger, self.matrix, self.repo), [])
        bad = copy.deepcopy(ledger)
        bad["gates"][1]["state"] = "engineering_passed"
        bad["gates"][0]["state"] = "investigated"
        errors = baseline.check_ledger(bad, self.matrix, self.repo)
        self.assertTrue(any("without receipts" in e for e in errors), errors)
        self.assertTrue(any("before prerequisite P" in e for e in errors), errors)
        self.assertTrue(any("must name its blockers" in e for e in errors), errors)
        bad = copy.deepcopy(ledger)
        bad["gates"][2].update(state="engineering_passed", receipts=bad["gates"][0]["receipts"])
        self.assertTrue(any("professional review" in e for e in baseline.check_ledger(bad, self.matrix, self.repo)))


class SyntheticInventory(unittest.TestCase):
    def test_changed_evidence_file_makes_the_inventory_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            package = repo / baseline.EVIDENCE / "airflow-x-20261013"
            package.mkdir(parents=True)
            (package / "archive-receipt.json").write_text(json.dumps(
                {"archive_sha256": "5" * 64, "manifest_sha256": "6" * 64, "files": 1, "scopes": []}))
            (package / "README.md").write_text("frozen\n")
            inventory = baseline.build_inventory(repo, releases=[
                {"tag_name": "x", "assets": [{"digest": "sha256:" + "6" * 64}]}])
            self.assertEqual(baseline.check_inventory(inventory, repo), [])
            (package / "README.md").write_text("edited\n")
            self.assertTrue(any("evidence tree changed" in e for e in baseline.check_inventory(inventory, repo)))


class CommittedBaseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = baseline.load_baseline(BASE)

    def test_committed_baseline_is_current(self):
        self.assertEqual(baseline.check_all(BASE, ROOT), [])

    def test_no_committed_gate_opens_even_with_an_exact_attestation(self):
        matrix, ledger = self.data["matrix"], self.data["ledger"]
        rows = {row["id"]: row for row in matrix["rows"]}
        for gate in ledger["gates"]:
            attestation = {
                "gate": gate["id"],
                "runtime": {b["runtime"]: copy.deepcopy(rows[b["runtime"]]) for b in gate["required_bindings"]},
                "config_sha256": {p["path"]: p["sha256"] for p in gate["config_pins"]},
                "receipts": gate["receipts"] or [{"path": "twins/bionic-turbo-f1/baseline-20261106/host-observations-20261106.json",
                                                  "sha256": baseline.sha256_file(BASE / "host-observations-20261106.json")}],
            }
            may_open, reasons = baseline.evaluate_gate(gate["id"], ledger, matrix, attestation, ROOT)
            self.assertFalse(may_open, gate["id"])
            self.assertTrue(reasons)
        self.assertFalse(any(g["state"] == "engineering_passed" for g in ledger["gates"]))

    def test_execution_contract_binds_unknown_executables(self):
        gate = next(g for g in self.data["ledger"]["gates"] if g["id"] == "G01-execution-contract")
        rows = {row["id"]: row for row in self.data["matrix"]["rows"]}
        attestation = {"gate": gate["id"], "runtime": {"opencfd-v2406-runtime": copy.deepcopy(rows["opencfd-v2406-runtime"])},
                       "config_sha256": {p["path"]: p["sha256"] for p in gate["config_pins"]}, "receipts": gate["receipts"]}
        _, reasons = baseline.evaluate_gate(gate["id"], self.data["ledger"], self.data["matrix"], attestation, ROOT)
        for executable in ("rhoSimpleFoam", "blockMesh", "snappyHexMesh", "checkMesh"):
            self.assertIn(f"opencfd-v2406-runtime.executables.{executable} pinned identity is 'unknown'; "
                          "an unpinned identity cannot open a gate", reasons)

    def test_historical_runtime_matches_the_case_generator(self):
        row = next(r for r in self.data["matrix"]["rows"] if r["id"] == "opencfd-v2406-runtime")
        image = baseline.python_constant(ROOT / "twins/bionic-turbo-f1/cfd/prepare_case.py", "IMAGE")
        self.assertEqual(row["identity"]["image"], image)
        foundation = [r for r in self.data["matrix"]["rows"] if r["variant"] == "OpenFOAM Foundation"]
        self.assertEqual(len(foundation), 2)
        self.assertTrue(all(r["qualification"].startswith("prohibited_for_turbo") for r in foundation))

    def test_tampered_matrix_or_manifest_is_rejected(self):
        matrix = copy.deepcopy(self.data["matrix"])
        next(r for r in matrix["rows"] if r["id"] == "opencfd-v2406-runtime")["identity"]["image"] = IMAGE
        self.assertTrue(any("prepare_case.py IMAGE" in e for e in baseline.check_matrix(matrix, ROOT)))
        manifest = copy.deepcopy(self.data["manifest"])
        block = next(p for p in manifest["prohibitions"] if p["id"] == "never-execute-pr229-blockmeshdict")
        block["archive_member"]["sha256"] = OTHER
        errors = baseline.check_manifest(manifest, self.data["inventory"], ROOT)
        self.assertIn("PR229 blockMeshDict hash differs from its committed file manifest", errors)
        manifest = copy.deepcopy(self.data["manifest"])
        manifest["prohibitions"] = [p for p in manifest["prohibitions"] if p["id"] != "never-touch-case-084"]
        self.assertTrue(any("lacks prohibitions" in e for e in baseline.check_manifest(manifest, self.data["inventory"], ROOT)))

    def test_unreachable_hosts_stay_unknown(self):
        row = next(r for r in self.data["matrix"]["rows"] if r["id"] == "opencfd-v2406-runtime")
        for host in ("mac_host_2026-11-06", "kali_host_2026-11-06"):
            self.assertIn("host not reachable from the WSL host on 2026-11-06",
                          row["availability"][host]["unknown"]["reason"])
        jobs = self.data["manifest"]["running_jobs"]
        self.assertIn("unknown", jobs["mac_host_2026-11-06"])
        self.assertIn("unknown", jobs["kali_host_2026-11-06"])


if __name__ == "__main__":
    unittest.main()
