import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/source/run_cad_specialist_inference.py"
SPEC = importlib.util.spec_from_file_location("specialist_inference", SOURCE)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class SpecialistInferenceTests(unittest.TestCase):
    def test_pinned_models(self):
        self.assertEqual(set(runner.MODELS), {"cadrille", "cad-recode"})
        for model in runner.MODELS.values():
            for field in ("revision", "source_revision", "processor_revision"):
                self.assertRegex(model[field], r"^[a-f0-9]{40}$")
            self.assertRegex(model["source_sha256"], r"^[a-f0-9]{64}$")

    def test_extract_excludes_notebook_demo_and_unused_imports(self):
        source = "import cadquery\nclass FourierPointEncoder: pass\nclass CADRecode: pass\nexec('bad')\n"
        raw = json.dumps({"cells": [{"cell_type": "code", "source": [source]}]}).encode()
        extracted = runner.extract_recode_architecture(raw).decode()
        self.assertNotIn("exec(", extracted)
        self.assertNotIn("cadquery", extracted)
        self.assertEqual([node.name for node in ast.parse(extracted).body if isinstance(node, ast.ClassDef)],
                         ["FourierPointEncoder", "CADRecode"])

    def test_changed_class_set_rejected(self):
        raw = json.dumps({"cells": [{"cell_type": "code", "source": ["class Surprise: pass"]}]}).encode()
        with self.assertRaisesRegex(ValueError, "class_set"):
            runner.extract_recode_architecture(raw)

    def test_license_acknowledgment_and_budgets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "points.npy"
            path.touch()
            common = ["--model", "cadrille", "--points", str(path), "--output", directory+"/out"]
            with self.assertRaisesRegex(ValueError, "acknowledgment"):
                runner.parse_args(common)
            args = runner.parse_args(common+["--noncommercial-research"])
            self.assertEqual(args.max_tokens, 768)
            self.assertEqual(args.device, "cuda")
            cpu = runner.parse_args(common+["--noncommercial-research", "--device", "cpu", "--cpu-threads", "4"])
            self.assertEqual((cpu.device, cpu.cpu_threads), ("cpu", 4))
            mps = runner.parse_args(common+["--noncommercial-research", "--device", "mps"])
            self.assertEqual(mps.device, "mps")
            for extra in (["--max-tokens", "1537"], ["--timeout-seconds", "1201"],
                          ["--generation-seconds", "301"], ["--seed", "-1"], ["--cpu-threads", "9"],
                          ["--cpu-threads", "0"]):
                with self.assertRaises(ValueError):
                    runner.parse_args(common+["--noncommercial-research"]+extra)

    def test_generated_code_is_only_saved(self):
        tree = ast.parse(SOURCE.read_text())
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                             and node.func.id in {"exec", "eval", "compile"} for node in ast.walk(tree)))
        self.assertIn('"generated.py.txt"', SOURCE.read_text())


    def test_points_shape_dtype_and_normalization(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "points.npy"
            points = np.linspace(-1, 1, 768, dtype=np.float32).reshape(256, 3)
            np.save(path, points)
            np.testing.assert_equal(runner.load_points(path), points)
            for bad in (points.astype(np.float64), points[:255], points*2,
                        np.full((256, 3), np.nan, dtype=np.float32),
                        np.zeros((256, 3), dtype=np.float32)):
                np.save(path, bad)
                with self.assertRaises(ValueError):
                    runner.load_points(path)

    def test_point_cast_only_adapted_for_non_cuda(self):
        raw = b"point_embeds = self.point_encoder(points).bfloat16()"
        self.assertEqual(runner.adapt_point_cast(raw, "cuda"), raw)
        for device in ("cpu", "mps"):
            changed = runner.adapt_point_cast(raw, device)
            self.assertIn(b"dtype=self.model.embed_tokens.weight.dtype", changed)
            self.assertNotIn(b".bfloat16()", changed)
            with self.assertRaisesRegex(ValueError, "point_cast_changed"):
                runner.adapt_point_cast(b"unknown_source", device)

    def test_mps_watermarks_default_and_preserved_valid_pair(self):
        env = {}
        runner.configure_mps_environment(env)
        self.assertEqual(env, {"PYTORCH_MPS_HIGH_WATERMARK_RATIO": "0.5",
                               "PYTORCH_MPS_LOW_WATERMARK_RATIO": "0.4",
                               "PYTORCH_ENABLE_MPS_FALLBACK": "0"})
        env.update(PYTORCH_MPS_HIGH_WATERMARK_RATIO="0.75", PYTORCH_MPS_LOW_WATERMARK_RATIO="0.6")
        runner.configure_mps_environment(env)
        self.assertEqual(env["PYTORCH_MPS_HIGH_WATERMARK_RATIO"], "0.75")
        self.assertEqual(env["PYTORCH_MPS_LOW_WATERMARK_RATIO"], "0.6")

    def test_invalid_mps_watermarks_rejected(self):
        for low, high in (("1.4", "0.5"), ("0", "0.5"), ("-0.1", "0.5"),
                          ("0.5", "0.5"), ("0.4", "1.01"), ("nan", "0.5"),
                          ("0.4", "inf"), ("bad", "0.5")):
            with self.assertRaises(ValueError):
                runner.configure_mps_environment({"PYTORCH_MPS_LOW_WATERMARK_RATIO": low,
                                                  "PYTORCH_MPS_HIGH_WATERMARK_RATIO": high})

    def test_driver_snapshot_survives_later_source_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "source.py"
            source.write_bytes(b"original")
            path, digest = runner.snapshot_driver(source, directory)
            source.write_bytes(b"later edit")
            self.assertEqual(path.read_bytes(), b"original")
            self.assertEqual(digest, runner.sha(b"original"))


if __name__ == "__main__":
    unittest.main()
