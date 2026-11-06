"""Issue #511: deterministic offline replay and prediction residuals of the 993 Turbo fan slice."""
import copy
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import replay_operational_twin as replay
from scripts import validate_operational_twin as contract

RUN_PATH = replay.DEFAULT_RUN
FRESH_COPY = [
    "scripts/__init__.py", "scripts/replay_operational_twin.py", "scripts/validate_operational_twin.py",
    "catalog/schemas/operational-twin.schema.json", "catalog/schemas/operational-replay.schema.json",
    "catalog/twins/twin-993-engine-cooling-fan-system-f0.json", "twins/m64-engine-system/program.json",
    "twins/993-turbo-cooling-fan-operational-f0",
]


def load_generator():
    path = contract.TWIN_DIR / "source" / "make_synthetic_observations.py"
    spec = importlib.util.spec_from_file_location("make_synthetic_observations", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Case:
    """A mutable copy of the committed run and its inputs, read through an in-memory reader."""

    def __init__(self) -> None:
        self.run = contract.load_json(RUN_PATH)
        self.docs = {kind: contract.load_json(contract.ROOT / bound["path"]) for kind, bound in self.run["inputs"].items()}

    def reader(self, path: str):
        for kind, bound in self.run["inputs"].items():
            if bound["path"] == path:
                return self.docs[kind]
        return replay.read_repo_json(path)

    def rebind(self, observations: bool = True, run: bool = True, frames: bool = False) -> "Case":
        """Recompute bindings after a deliberate edit, as a maintainer would after review."""
        obs = self.docs["observation_set"]
        if observations:
            obs["model_binding"]["model_card_sha256"] = contract.canonical_sha256(self.docs["model_card"])
            obs["model_binding"]["parameter_set_sha256"] = contract.canonical_sha256(self.docs["parameter_set"])
            obs["calibration_register"]["sha256"] = contract.canonical_sha256(self.docs["calibration_register"])
        if run:
            for kind, bound in self.run["inputs"].items():
                bound["sha256"] = contract.canonical_sha256(self.docs[kind])
        if frames:
            self.run["geometry"]["frames_sha256"] = replay.frames_sha256(self.docs["slice_contract"])
        return self

    def channel(self, name: str) -> dict:
        return next(c for c in self.docs["observation_set"]["channels"] if c["channel_id"] == name)

    def execute(self, external=None) -> dict:
        return replay.replay(self.run, read=self.reader, external=external)


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = Case().execute()
        cls.committed_text = contract.ROOT.joinpath(contract.load_json(RUN_PATH)["report"]).read_text(encoding="utf-8")

    def assertRejected(self, case: Case, code: str, detail: str | None = None) -> None:
        with self.assertRaises(replay.ReplayRejected) as caught:
            case.execute()
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        if detail is not None:
            self.assertIn(detail, contract.error_codes(caught.exception.details))

    # ---------------------------------------------------------------- determinism

    def test_committed_report_is_reproduced_byte_for_byte(self) -> None:
        self.assertEqual(replay.render(self.report), self.committed_text)

    def test_fresh_copy_reproduces_the_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fresh-checkout"
            for item in FRESH_COPY:
                source, target = contract.ROOT / item, root / item
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    shutil.copytree(source, target, ignore=shutil.ignore_patterns("derived", "__pycache__"))
                else:
                    shutil.copy2(source, target)
            outputs = []
            for seed, cwd in (("0", tmp), ("4242", str(root))):
                out = Path(tmp) / f"report-{seed}.json"
                env = dict(os.environ, PYTHONHASHSEED=seed)
                result = subprocess.run(
                    [sys.executable, str(root / "scripts/replay_operational_twin.py"),
                     "--run", str(root / RUN_PATH.relative_to(contract.ROOT)), "--out", str(out)],
                    cwd=cwd, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs.append(out.read_text(encoding="utf-8"))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], self.committed_text)

    def test_report_has_no_host_or_absolute_path(self) -> None:
        self.assertNotIn(str(contract.ROOT), self.committed_text)
        self.assertNotIn("physically_correlated", self.committed_text)

    def test_cli_check(self) -> None:
        result = subprocess.run([sys.executable, str(contract.ROOT / "scripts/replay_operational_twin.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    # ---------------------------------------------------------------- claim ceiling

    def test_status_never_exceeds_digitally_checked(self) -> None:
        self.assertEqual(self.report["status"], "digitally_checked")
        self.assertEqual(self.report["physical_correlation"], "not_claimed")
        self.assertEqual(self.report["live_twin"], "not_claimed")
        self.assertEqual(self.report["synchronisation_mode"], "offline_replay")
        self.assertEqual(self.report["data_class"], "synthetic")
        self.assertTrue(self.report["label"].startswith("SYNTHETIC"))
        validator = contract.SchemaValidator(contract.load_json(replay.REPLAY_SCHEMA))
        forged = copy.deepcopy(self.report)
        forged["status"] = "physically_correlated"
        self.assertTrue(validator.errors(forged, validator.root["$defs"]["replay_report"]))

    def test_binding_records_specimen_revisions_and_hashes(self) -> None:
        binding = self.report["binding"]
        self.assertEqual(binding["specimen_id"], "SPEC-993T-FAN-SYN-0001")
        self.assertEqual(binding["inputs"]["model_card"]["revision"], "1.0.0")
        self.assertEqual(set(binding["inputs"]), set(replay.INPUT_KINDS))
        self.assertEqual(set(binding["implementation"]["files"]), set(replay.IMPLEMENTATION))
        self.assertEqual(binding["run_sha256"], contract.canonical_sha256(contract.load_json(RUN_PATH)))

    # ---------------------------------------------------------------- binding negatives

    def test_rejects_mismatched_specimen(self) -> None:
        case = Case()
        case.run["specimen_id"] = "SPEC-993T-FAN-SYN-0002"
        self.assertRejected(case, "SPECIMEN_MISMATCH")
        case = Case()
        case.docs["observation_set"]["specimen_id"] = "SPEC-993T-FAN-SYN-0002"
        case.run["specimen_id"] = "SPEC-993T-FAN-SYN-0002"
        self.assertRejected(case.rebind(), "CONTRACT_INVALID", "SPECIMEN_MISMATCH")

    def test_rejects_mismatched_timebase(self) -> None:
        case = Case()
        case.run["timebase_id"] = "TB-SYN-DAQ-0002"
        self.assertRejected(case, "TIMEBASE_MISMATCH")
        case = Case()
        case.channel("T_OUT")["timebase_id"] = "TB-SYN-DAQ-0002"
        self.assertRejected(case.rebind(), "CONTRACT_INVALID", "TIMEBASE_MISMATCH")

    def test_rejects_mismatched_calibration(self) -> None:
        case = Case()
        case.docs["calibration_register"]["instruments"][3]["standard_uncertainty_rel"] = 0.0
        self.assertRejected(case, "CALIBRATION_HASH_MISMATCH")
        case = Case()
        case.docs["calibration_register"]["instruments"][3]["standard_uncertainty_rel"] = 0.0
        self.assertRejected(case.rebind(observations=False), "CONTRACT_INVALID", "CALIBRATION_REGISTER_MISMATCH")
        case = Case()
        case.channel("N_FAN")["calibration_id"] = "CALREC-SYN-OPT-04-R2"
        self.assertRejected(case.rebind(), "CONTRACT_INVALID", "CALIBRATION_UNKNOWN")

    def test_rejects_mismatched_model_and_parameter_hashes(self) -> None:
        case = Case()
        case.run["inputs"]["model_card"]["sha256"] = "0" * 64
        self.assertRejected(case, "MODEL_HASH_MISMATCH")
        case = Case()
        case.docs["model_card"]["assumptions"].append("an unreviewed edit")
        self.assertRejected(case, "MODEL_HASH_MISMATCH")
        self.assertRejected(case.rebind(observations=False), "CONTRACT_INVALID", "MODEL_BINDING_MISMATCH")
        case = Case()
        case.docs["parameter_set"]["parameters"][0]["value"] = 1.7
        self.assertRejected(case, "PARAMETER_HASH_MISMATCH")
        case = Case()
        case.run["inputs"]["model_card"]["revision"] = "1.0.1"
        self.assertRejected(case, "INPUT_ID_MISMATCH")

    def test_rejects_edited_observations_and_frames(self) -> None:
        case = Case()
        case.channel("T_IN")["samples"][5][3] += 0.01
        self.assertRejected(case, "OBSERVATION_HASH_MISMATCH")
        case = Case()
        case.docs["slice_contract"]["stations"][1]["z_range_mm"] = [20.0, 160.0]
        self.assertRejected(case.rebind(), "GEOMETRY_MISMATCH")
        self.assertEqual(case.rebind(frames=True).execute()["status"], "digitally_checked")

    def test_rejects_live_mode(self) -> None:
        case = Case()
        case.run["synchronisation_mode"] = "live_synchronisation"
        self.assertRejected(case, "RUN_INVALID")
        case = Case()
        case.docs["observation_set"]["synchronisation_mode"] = "live_synchronisation"
        self.assertRejected(case.rebind(), "CONTRACT_INVALID", "MODE_NOT_IMPLEMENTED")

    # ---------------------------------------------------------------- ingest negatives

    def test_rejects_contradictory_duplicates(self) -> None:
        case = Case()
        samples = case.channel("N_CRANK")["samples"]
        copy_ = list(samples[10])
        copy_[2] += 0.1
        copy_[3] += 5.0
        samples.append(copy_)
        self.assertRejected(case.rebind(), "CONTRADICTORY_DUPLICATE")
        case = Case()
        samples = case.channel("N_CRANK")["samples"]
        samples.append([9999, samples[10][1], samples[10][2], samples[10][3], "ok"])
        self.assertRejected(case.rebind(), "CONTRADICTORY_DUPLICATE")

    def test_rejects_sequence_time_contradiction(self) -> None:
        case = Case()
        samples = sorted(case.channel("DP_FAN")["samples"])
        samples[20][1:3], samples[21][1:3] = samples[21][1:3], samples[20][1:3]
        case.channel("DP_FAN")["samples"] = samples
        self.assertRejected(case.rebind(), "SEQUENCE_TIME_CONTRADICTION")

    def test_rejects_samples_outside_session_or_before_arrival(self) -> None:
        case = Case()
        case.channel("P_AMB")["samples"].append([999, 171.0, 171.1, 985.0, "ok"])
        self.assertRejected(case.rebind(), "SAMPLE_OUTSIDE_SESSION")
        case = Case()
        sample = case.channel("P_AMB")["samples"][3]
        sample[2] = sample[1] - 0.01
        self.assertRejected(case.rebind(), "ARRIVAL_BEFORE_SAMPLE")

    # ---------------------------------------------------------------- tolerated anomalies

    def test_ingest_counts_duplicates_reordering_late_and_flags(self) -> None:
        ingest = self.report["ingest"]
        self.assertEqual(ingest["N_CRANK"]["exact_duplicates_dropped"], 1)
        self.assertEqual(ingest["N_CRANK"]["out_of_order_arrivals"], 1)
        self.assertEqual(ingest["T_IN"]["late_excluded"], 2)
        self.assertEqual(ingest["N_FAN"]["flagged"], {"sensor_fault": 3})
        self.assertEqual(ingest["DP_FAN"]["flagged"], {"source_outlier": 1})
        self.assertEqual(ingest["T_OUT"]["flagged"], {"missing": 1})

    def test_no_claim_states_are_explicit(self) -> None:
        frames = {f["t_s"]: f for f in self.report["frames"]}
        self.assertEqual(frames[20.0]["outputs"]["T_OUT"]["reasons"], ["T_OUT:missing"])
        self.assertEqual(frames[31.0]["channels"]["T_IN"]["status"], "stale")
        self.assertIn("frame:input_unavailable", frames[31.0]["outputs"]["N_FAN"]["reasons"])
        self.assertEqual(frames[75.0]["outputs"]["DP_FAN"]["reasons"], ["DP_FAN:source_outlier"])
        self.assertEqual(frames[90.0]["outputs"]["N_FAN"]["reasons"], ["N_FAN:sensor_fault"])
        for t in (97.0, 98.0, 99.0):
            self.assertEqual(frames[t]["outputs"]["T_OUT"]["reasons"], ["T_OUT:stale"])
        self.assertEqual(frames[45.0]["outputs"]["N_FAN"]["reasons"], ["frame:transient"])
        self.assertIsNotNone(frames[45.0]["outputs"]["N_FAN"]["residual"])  # computed, never judged
        for frame in self.report["frames"]:
            for state in frame["outputs"].values():
                self.assertEqual(state["verdict"] == "no_claim", bool(state["reasons"]))

    def test_injected_slip_discrepancy_is_rejected_only_where_injected(self) -> None:
        summary = self.report["summary"]
        self.assertEqual(summary["N_FAN"]["verdict"], "model_rejected")
        windows = summary["N_FAN"]["windows"]
        self.assertEqual([w["discrepant"] for w in windows[:2]], [0, 0])
        self.assertGreater(windows[2]["discrepant"], 0.9 * windows[2]["evaluated"])
        self.assertLess(windows[2]["mean_residual"], 0)
        self.assertEqual(summary["DP_FAN"]["verdict"], "consistent")
        self.assertEqual(summary["T_OUT"]["verdict"], "consistent")

    def test_calibration_expiry_declines_claims_without_rejecting(self) -> None:
        case = Case()
        case.docs["calibration_register"]["instruments"][5]["valid_until_utc"] = "2026-11-06T09:01:00Z"
        report = case.rebind().execute()
        frames = {f["t_s"]: f for f in report["frames"]}
        self.assertEqual(frames[30.0]["outputs"]["T_OUT"]["verdict"], "consistent")
        self.assertEqual(frames[61.0]["outputs"]["T_OUT"]["reasons"], ["T_OUT:calibration_invalid"])

    def test_outside_envelope_declines_claims(self) -> None:
        case = Case()
        for sample in case.channel("P_AMB")["samples"]:
            sample[3] = 700.0
        report = case.rebind().execute()
        frame = report["frames"][20]
        self.assertIn("P_AMB:outside_envelope", frame["outputs"]["DP_FAN"]["reasons"])
        self.assertEqual(report["summary"]["DP_FAN"]["verdict"], "no_claim")

    # ---------------------------------------------------------------- conversions and model

    def test_unit_and_frame_conversion_are_invariant(self) -> None:
        case = Case()
        t_in = case.channel("T_IN")
        t_in["unit"] = "K"
        for sample in t_in["samples"]:
            sample[3] = round(sample[3] + 273.15, 6)
        case.docs["calibration_register"]["instruments"][1]["unit"] = "K"
        case.docs["calibration_register"]["instruments"][1]["range"] = [233.15, 393.15]
        n_fan = case.channel("N_FAN")
        n_fan["mount"]["rotation_parent_from_sensor"] = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        for sample in n_fan["samples"]:
            sample[3] = -sample[3] if sample[3] else sample[3]
        report = case.rebind().execute()
        self.assertEqual(report["ingest"]["N_FAN"]["frame_sign"], 1)
        for ours, theirs in zip(report["frames"], self.report["frames"]):
            for name in ("N_FAN", "DP_FAN", "T_OUT"):
                a, b = ours["outputs"][name], theirs["outputs"][name]
                self.assertEqual(a["verdict"], b["verdict"])
                if a["z"] is not None:
                    self.assertAlmostEqual(a["z"], b["z"], places=6)
        self.assertEqual(self.report["ingest"]["T_IN"]["offset"], 273.15)
        frame = self.report["frames"][20]["channels"]["T_IN"]
        self.assertAlmostEqual(frame["u"], 0.15, places=12)  # the offset never enters an uncertainty

    def test_prediction_matches_an_independent_implementation(self) -> None:
        generator = load_generator()
        parameters = {p["name"]: p for p in Case().docs["parameter_set"]["parameters"]}
        for t in (10.0, 80.0, 100.0):
            truth = generator.truth(t)
            inputs = {"N_CRANK": (truth["N_CRANK"] * math.pi / 30.0, 1.0),
                      "T_IN": (truth["T_IN"] + 273.15, 0.1), "P_AMB": (truth["P_AMB"] * 100.0, 10.0)}
            predicted = replay.predict(inputs, parameters)
            self.assertAlmostEqual(predicted["N_FAN"][0] / -truth["N_FAN"], 1.0, places=12)
            self.assertAlmostEqual(predicted["DP_FAN"][0] / (truth["DP_FAN"] * 1000.0), 1.0, places=12)
            self.assertAlmostEqual(predicted["T_OUT"][0] - 273.15, truth["T_OUT"], places=9)

    def test_uncertainty_propagation_matches_finite_differences(self) -> None:
        parameters = {p["name"]: p for p in Case().docs["parameter_set"]["parameters"]}
        inputs = {"N_CRANK": (314.159, 0.2), "T_IN": (295.0, 0.15), "P_AMB": (98500.0, 50.0)}
        analytic = replay.predict(inputs, parameters)
        for name in ("N_FAN", "DP_FAN"):
            variance = 0.0
            for key, (value, u) in inputs.items():
                shifted = dict(inputs, **{key: (value + u * 1e-6, u)})
                variance += ((replay.predict(shifted, parameters)[name][0] - analytic[name][0]) / 1e-6) ** 2
            for key, item in parameters.items():
                if item["standard_uncertainty"]:
                    shifted = copy.deepcopy(parameters)
                    shifted[key]["value"] += item["standard_uncertainty"] * 1e-6
                    variance += ((replay.predict(inputs, shifted)[name][0] - analytic[name][0]) / 1e-6) ** 2
            self.assertAlmostEqual(variance ** 0.5 / analytic[name][1], 1.0, places=4)

    # ---------------------------------------------------------------- private samples

    def measured_case(self, folder: Path) -> Case:
        case = Case()
        register, parameters, obs = (case.docs[k] for k in ("calibration_register", "parameter_set", "observation_set"))
        register["data_class"] = parameters["data_class"] = "measured"
        register["statement"] = "Measured register held privately; only hashes are public."
        for instrument in register["instruments"]:
            instrument["certificate_status"] = "private_certificate_hashed"
            instrument["certificate_sha256"] = "a" * 64
        obs["provenance"].update({"data_class": "measured", "label": "Contributed observation set", "generator": None,
                                  "raw_data": {"storage": "private_evidence_release", "note": "held privately"}})
        obs["provenance"]["source_rights"].update({"contributor_consent_ref": "CONSENT-0001",
                                                   "publication": "derived_results_only"})
        for channel in obs["channels"]:
            samples = channel.pop("samples")
            digest = contract.canonical_sha256(samples)
            (folder / f"{digest}.json").write_text(json.dumps(samples), encoding="utf-8")
            channel["samples_ref"] = {"sha256": digest, "count": len(samples)}
        return case.rebind()

    def test_private_samples_are_read_from_outside_the_repository_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = self.measured_case(Path(tmp))
            report = case.execute(external=Path(tmp))
            self.assertEqual(report["data_class"], "measured")
            self.assertEqual(report["status"], "digitally_checked")
            self.assertEqual(report["frames"], self.report["frames"])
            with self.assertRaises(replay.ReplayRejected) as caught:
                case.execute()
            self.assertEqual(caught.exception.code, "EXTERNAL_SAMPLES_REQUIRED")
            with self.assertRaises(replay.ReplayRejected) as caught:
                case.execute(external=contract.TWIN_DIR)
            self.assertEqual(caught.exception.code, "RAW_DATA_IN_REPOSITORY")
            first = next(Path(tmp).glob("*.json"))
            first.write_text("[]", encoding="utf-8")
            with self.assertRaises(replay.ReplayRejected) as caught:
                case.execute(external=Path(tmp))
            self.assertEqual(caught.exception.code, "EXTERNAL_SAMPLES_MISMATCH")


if __name__ == "__main__":
    unittest.main()
