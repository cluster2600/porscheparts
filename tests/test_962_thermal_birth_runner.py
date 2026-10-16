"""The portable runner must preserve evidence before invoking a native solver."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = (Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0"
          / "source/physics_witness/thermal_birth")


def load_runner():
    with patch.dict(sys.modules):
        for name in ("assess", "assess_refinement", "run_local"):
            spec = importlib.util.spec_from_file_location(name, SOURCE / (name + ".py"))
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        return module


class ThermalBirthRunnerTests(unittest.TestCase):
    def test_wrong_runtime_creates_no_output_and_starts_no_process(self):
        runner = load_runner()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(runner, "sha", return_value="0" * 64), \
                    patch.object(runner.subprocess, "run") as native:
                with self.assertRaisesRegex(ValueError, "Runtime binary"):
                    runner.reproduce(root / "runtime", root / "output")
                native.assert_not_called()
                self.assertFalse((root / "output").exists())

    def test_reused_output_preserves_bytes_and_starts_no_process(self):
        runner = load_runner()
        expected = json.loads((SOURCE / "card.json").read_text())["native_binary_sha256"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            evidence = output / "native.log"
            evidence.write_bytes(b"retained native evidence\n")
            with patch.object(runner, "sha", return_value=expected), \
                    patch.object(runner.subprocess, "run") as native:
                with self.assertRaises(FileExistsError):
                    runner.reproduce(root / "runtime", output)
                native.assert_not_called()
                self.assertEqual(evidence.read_bytes(), b"retained native evidence\n")
                self.assertEqual(list(output.iterdir()), [evidence])
