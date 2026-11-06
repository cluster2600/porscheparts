"""Issue #510: specimen, observation and state contract of the 993 Turbo cooling-fan slice."""
import contextlib
import copy
import io
import json
import subprocess
import sys
import unittest

from scripts import validate_operational_twin as v

GENERATOR = v.TWIN_DIR / "source" / "make_synthetic_observations.py"


class OperationalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = v.load_bundle()
        cls.schema = v.load_json(v.SCHEMA_PATH)

    def test_committed_bundle_is_valid(self) -> None:
        self.assertEqual(v.validate_documents(self.bundle), [])

    def test_every_invalid_fixture_is_rejected_with_its_declared_codes(self) -> None:
        fixtures = sorted(v.INVALID_FIXTURES.glob("*.json"))
        self.assertGreaterEqual(len(fixtures), 20)
        for path in fixtures:
            fixture = v.load_json(path)
            with self.subTest(fixture=path.name):
                self.assertEqual(fixture["data_class"], "synthetic")
                errors = v.run_invalid_fixture(fixture, self.bundle)
                self.assertTrue(errors)
                self.assertEqual(v.error_codes(errors), sorted(fixture["expected_codes"]))

    def test_cli_passes(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(v.main([]), 0)

    def test_schema_uses_only_implemented_keywords(self) -> None:
        validator = v.SchemaValidator(self.schema)
        for name, definition in self.schema["$defs"].items():
            with self.subTest(definition=name):
                validator.errors(None, definition)  # raises SchemaError on an unknown keyword
        with self.assertRaises(v.SchemaError):
            validator.errors(1, {"multipleOf": 2})

    def test_schema_dispatch_rejects_unknown_kind(self) -> None:
        validator = v.SchemaValidator(self.schema)
        self.assertTrue(validator.validate_kind({"document_kind": "replay_report"}))
        self.assertTrue(validator.validate_kind({"document_kind": "sample"}))

    def test_booleans_are_not_numbers(self) -> None:
        validator = v.SchemaValidator(self.schema)
        self.assertTrue(validator.errors(True, {"type": "number"}))
        self.assertTrue(validator.errors(1, {"const": True}))

    def test_fixture_is_reproduced_by_its_generator(self) -> None:
        result = subprocess.run([sys.executable, str(GENERATOR), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_claim_ceiling_and_synthetic_labels(self) -> None:
        contract = self.bundle["slice_contract"]
        self.assertEqual(contract["claim_limits"]["max_validation_status"], "digitally_checked")
        self.assertEqual(contract["claim_limits"]["physical_correlation"], "not_claimed")
        self.assertEqual(contract["synchronisation_modes"]["live_synchronisation"]["status"], "not_implemented")
        self.assertEqual(contract["specimen"]["identity_class"], "synthetic_placeholder")
        observations = self.bundle["observation_set"]
        self.assertEqual(observations["provenance"]["data_class"], "synthetic")
        self.assertIn("SYNTHETIC", observations["provenance"]["label"])
        self.assertEqual(self.bundle["parameter_set"]["data_class"], "synthetic")
        self.assertEqual(self.bundle["calibration_register"]["data_class"], "synthetic")

    def test_measured_observations_reference_private_samples_only(self) -> None:
        documents = copy.deepcopy(self.bundle)
        register, parameters = documents["calibration_register"], documents["parameter_set"]
        register["data_class"] = "measured"
        register["statement"] = "Measured register held privately; only hashes are public."
        for instrument in register["instruments"]:
            instrument["certificate_status"] = "private_certificate_hashed"
            instrument["certificate_sha256"] = "a" * 64
        parameters["data_class"] = "measured"
        observations = documents["observation_set"]
        observations["provenance"].update({
            "data_class": "measured", "label": "Contributed observation set", "generator": None,
            "raw_data": {"storage": "private_evidence_release", "note": "samples held privately"},
        })
        observations["provenance"]["source_rights"].update(
            {"contributor_consent_ref": "CONSENT-0001", "publication": "derived_results_only"})
        for channel in observations["channels"]:
            count = len(channel.pop("samples"))
            channel["samples_ref"] = {"sha256": "b" * 64, "count": count}
        observations["model_binding"]["parameter_set_sha256"] = v.canonical_sha256(parameters)
        observations["calibration_register"]["sha256"] = v.canonical_sha256(register)
        self.assertEqual(v.validate_documents(documents), [])
        observations["channels"][0]["samples"] = [[0, 0.0, 0.1, 800.0, "ok"]]
        self.assertIn("SCHEMA", v.error_codes(v.validate_documents(documents)))

    def test_frame_transform_places_outlet_probe(self) -> None:
        mount = next(c for c in self.bundle["observation_set"]["channels"] if c["channel_id"] == "T_OUT")["mount"]
        placed = v.mount_in_parent(mount)
        self.assertEqual([round(x, 9) for x in placed["position_mm"]], [0.0, 150.0, 80.0])
        tach = next(c for c in self.bundle["observation_set"]["channels"] if c["channel_id"] == "N_FAN")["mount"]
        self.assertEqual(v.mount_in_parent(tach)["axis"], [0.0, 0.0, -1.0])

    def test_vin_pattern_ignores_hashes_and_ids(self) -> None:
        self.assertFalse(v.privacy_errors({"a": "f" * 64, "b": "SPEC-993T-FAN-SYN-0001", "c": "96410601522"}, "x"))
        self.assertTrue(v.privacy_errors({"a": "see AAAAAAAAA00000000 here"}, "x"))
        self.assertTrue(v.privacy_errors({"nested": [{"VIN": "redacted"}]}, "x"))

    def test_canonical_hash_ignores_layout(self) -> None:
        a = {"b": [1, 2.5], "a": "é"}
        b = json.loads('{\n  "a": "\\u00e9",\n  "b": [1, 2.5]\n}')
        self.assertEqual(v.canonical_sha256(a), v.canonical_sha256(b))


if __name__ == "__main__":
    unittest.main()
