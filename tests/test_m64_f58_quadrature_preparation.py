import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("prepare_f58", Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/source/prepare_f58_quadrature.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source, self.historical = self.root / "case", self.root / "historical"
        self.source.mkdir()
        self.historical.mkdir()
        self.reference, self.output = self.root / "inputs" / "reference.json", self.root / "out"
        self.reference.parent.mkdir()
        self.payload = {f"constant/field{i}": f"fixture{i}\n".encode() for i in range(26)}
        self.payload.update({"system/controlDict": b"startFrom startTime;\nstartTime 0;\nstopAt endTime;\nendTime 0.00012;\ndeltaT 2.5e-08;\nadjustTimeStep no;\nwriteInterval 0.00004;\n",
            "system/fvSolution": b"nOuterCorrectors 0;\nexplicitSolve true;\nTmax 3300.0;\n",
            "constant/heatSourceDict": b"nPoints     (10 10 10);\n"})
        self.paths = {}
        for name, data in self.payload.items():
            path = self.historical / Path(name).name if name in m.HISTORICAL else self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self.paths[name] = path
        self.repin()

    def repin(self):
        self.reference.write_text(json.dumps({"source_inputs_sha256": {k: m.digest(v) for k, v in self.payload.items()}}))
        self.pin = m.digest(self.reference.read_bytes())

    def run_prepare(self):
        with patch.object(m, "REFERENCE_SHA", self.pin):
            return m.prepare(self.reference, self.source, self.historical, self.output)

    def test_success_two_decks_exact_minimal_changes(self):
        (self.source / "unlisted-result").write_text("not copied")
        before = {k: p.read_bytes() for k, p in self.paths.items()}
        result = self.run_prepare()
        self.assertEqual(result["expected_steps"], 1600)
        self.assertFalse(result["native_executed"])
        self.assertFalse(result["ready_for_execution"])
        self.assertTrue(result["source_inputs_unchanged"])
        self.assertEqual(result["cases"]["q10"]["changed_from_source"], ["system/controlDict"])
        self.assertEqual(result["cases"]["q20"]["changed_from_source"], ["constant/heatSourceDict", "system/controlDict"])
        for name in self.payload:
            q10, q20 = ((self.output / case / name).read_bytes() for case in ("q10", "q20"))
            if name == "constant/heatSourceDict":
                self.assertEqual(q20, q10.replace(b"(10 10 10)", b"(20 20 20)"))
            else:
                self.assertEqual(q10, q20)
            self.assertEqual(self.paths[name].read_bytes(), before[name])
        self.assertFalse((self.output / "q10" / "unlisted-result").exists())

    def test_existing_output_refused(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, "output_must_be_new"):
            self.run_prepare()

    def test_nested_function_write_interval_is_not_top_level_interval(self):
        name = "system/controlDict"
        self.payload[name] += b"functions\n{\n diagnostic\n {\n writeInterval 1;\n }\n}\n"
        self.paths[name].write_bytes(self.payload[name])
        self.repin()
        result = self.run_prepare()
        self.assertEqual(result["expected_steps"], 1600)

    def test_reference_corruption_refused(self):
        self.reference.write_bytes(self.reference.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "reference_sha_mismatch"):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_historical_control_corruption_refused(self):
        self.paths["system/fvSolution"].write_text("nOuterCorrectors 1;")
        with self.assertRaisesRegex(ValueError, "source_sha_mismatch"):
            self.run_prepare()

    def test_duplicate_end_time_refused(self):
        name = "system/controlDict"
        self.payload[name] += b"endTime 0.00012;\n"
        self.paths[name].write_bytes(self.payload[name])
        self.repin()
        with self.assertRaisesRegex(ValueError, "ambiguous_or_missing"):
            self.run_prepare()

    def test_thermal_contract_refused(self):
        name = "system/fvSolution"
        self.payload[name] = self.payload[name].replace(b"nOuterCorrectors 0", b"nOuterCorrectors 1")
        self.paths[name].write_bytes(self.payload[name])
        self.repin()
        with self.assertRaisesRegex(ValueError, "unexpected_thermal"):
            self.run_prepare()

    def test_traversal_refused(self):
        self.payload["../outside"] = self.payload.pop("constant/field0")
        self.repin()
        with self.assertRaisesRegex(ValueError, "invalid_whitelist_path"):
            self.run_prepare()

    def test_symlink_refused(self):
        path = self.paths["constant/field0"]
        saved = path.with_suffix(".saved")
        path.rename(saved)
        path.symlink_to(saved)
        with self.assertRaisesRegex(ValueError, "symlink_input"):
            self.run_prepare()

    def test_source_change_during_preparation_refused(self):
        original_write = Path.write_bytes
        fired = False
        def interfering_write(path, data):
            nonlocal fired
            count = original_write(path, data)
            if self.output in path.parents and not fired:
                fired = True
                original_write(self.paths["constant/field0"], b"changed")
            return count
        with patch.object(Path, "write_bytes", interfering_write):
            with self.assertRaisesRegex(ValueError, "source_changed_during"):
                self.run_prepare()
        self.assertFalse((self.output / "preparation-report.json").exists())


if __name__ == "__main__":
    unittest.main()
