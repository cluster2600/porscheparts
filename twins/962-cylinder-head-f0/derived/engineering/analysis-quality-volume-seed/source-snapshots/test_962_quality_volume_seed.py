"""The isolated seed entrypoint must self-spawn with pinned source and gates."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source"
sys.path.insert(0, str(SOURCE))
import mesh_quality_head as ordinary
spec = importlib.util.spec_from_file_location("quality_seed", SOURCE / "mesh_quality_head_seed.py")
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


class SeedEntrypoint(unittest.TestCase):
    def test_fresh_controller_worker_options_source_bindings_and_import_isolation_without_native_launch(self):
        original = {name: getattr(ordinary, name) for name in
                    ["__file__", "source_files", "OUTPUT", "OPTIONS", "save"]}
        options = dict(ordinary.OPTIONS)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            admission = root / "admission.json"; admission.write_text("mocked admission")
            output = root / "mocked-output"
            args = ["--admission", str(admission), "--admission-sha256", ordinary.sha(admission),
                    "--output", str(output)]
            created = []
            configure = seed.configure_core
            def isolated_controller():
                core = configure(); created.append(core)
                self.assertIsNot(core, ordinary)
                self.assertEqual(core.OUTPUT, core.ROOT / "work/962-engineering/quality-volume-hxt-seed-001")
                core.OUTPUT = output  # Test-only fresh output, never the reserved head trial.
                core.require_admission = mock.Mock()
                return core
            process = mock.Mock(pid=12345, returncode=2); process.poll.return_value = 2
            with mock.patch.object(seed, "configure_core", side_effect=isolated_controller), \
                    mock.patch.object(subprocess, "Popen", return_value=process) as launch, \
                    mock.patch.object(threading, "Timer"), \
                    mock.patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(seed.main(args), 2)
                launch.assert_called_once()
            controller = created[0]
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(receipt["command"][1], str(seed.WRAPPER_PATH))
            self.assertIn("--worker", receipt["command"])
            self.assertEqual(receipt["options"], {**options, "Mesh.Optimize": 0})
            sources = [seed.WRAPPER_PATH, *ordinary.source_files()]
            expected = {str(p.relative_to(ordinary.ROOT)): ordinary.sha(p) for p in sources}
            self.assertEqual(receipt["source_sha256s"], expected)
            for path in sources:
                self.assertEqual(ordinary.sha(output / "source-snapshots" / path.name), ordinary.sha(path))
            self.assertEqual(receipt["seed_companion"]["frozen_core_sha256"], seed.CORE_SHA256)
            self.assertEqual(receipt["seed_companion"]["actual_minimum_SICN_gate_unchanged"], .1)
            self.assertFalse((output / "head-volume.msh").exists())
            def isolated_worker():
                core = configure(); created.append(core)
                def checked_worker(parsed):
                    self.assertTrue(parsed.worker)
                    self.assertIsNot(core, controller); self.assertIsNot(core, ordinary)
                    self.assertEqual(core.__file__, str(seed.WRAPPER_PATH))
                    self.assertEqual(core.OPTIONS, {**options, "Mesh.Optimize": 0})
                    self.assertEqual(core.source_files(), sources)
                    return 2
                core.worker = mock.Mock(side_effect=checked_worker)
                return core
            with mock.patch.object(seed, "configure_core", side_effect=isolated_worker), \
                    mock.patch.object(subprocess, "Popen") as launch:
                self.assertEqual(seed.main([*args, "--worker"]), 2)
                launch.assert_not_called()
            stage = dict(stage="generating_and_standard_optimizing_HXT")
            created[-1].save(root / "stage.json", stage)
            self.assertEqual(stage["stage"], "generating_HXT_without_standard_optimization")
            self.assertFalse(stage["seed_companion"]["standard_optimization_enabled"])
        self.assertEqual(ordinary.OPTIONS, options)
        for name, value in original.items():
            self.assertIs(getattr(ordinary, name), value)
        self.assertEqual(hashlib.sha256(seed.CORE_PATH.read_bytes()).hexdigest(), seed.CORE_SHA256)

    def test_drifted_core_rejects_before_either_entrypoint_or_output_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); changed = root / "changed-core.py"; changed.write_text("changed")
            output = root / "never-created"
            args = ["--admission", str(root / "unused.json"), "--admission-sha256", "a" * 64,
                    "--output", str(output)]
            with mock.patch.object(seed, "CORE_PATH", changed), \
                    mock.patch.object(seed, "configure_core") as configure, \
                    mock.patch.object(subprocess, "Popen") as launch:
                for suffix in [[], ["--worker"]]:
                    with self.subTest(worker=bool(suffix)), self.assertRaisesRegex(ValueError, "frozen"):
                        seed.main([*args, *suffix])
                configure.assert_not_called(); launch.assert_not_called()
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
