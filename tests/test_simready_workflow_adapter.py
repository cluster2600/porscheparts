"""Régressions du pont entre le skill NVIDIA et le paquet usd-convert-cad."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "containers/simready-preflight"


class SimReadyWorkflowAdapterTests(unittest.TestCase):
    def _load_adapter(self):
        source = PREFLIGHT / "convert.py"
        spec = importlib.util.spec_from_file_location("simready_convert_test", source)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_capability_manifest_exposes_only_step(self):
        tree = ast.parse((PREFLIGHT / "formats.py").read_text(encoding="utf-8"))
        assignments = {
            node.targets[0].id: node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        }
        supported = assignments["SUPPORTED_FORMATS"]
        self.assertIsInstance(supported, ast.Tuple)
        self.assertEqual(ast.literal_eval(supported.elts[0].args[0]), (".step", ".stp"))

    def test_adapter_translates_checkout_cli_to_packaged_cli(self):
        source = (PREFLIGHT / "convert.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("input", type=Path)', source)
        self.assertIn('parser.add_argument("output", type=Path)', source)
        self.assertIn('parser.add_argument("--report", type=Path)', source)
        self.assertIn('parser.add_argument("--log", type=Path)', source)
        self.assertIn(
            'parser.add_argument("--up-axis", choices=("y", "z"), default="y")',
            source,
        )
        self.assertIn('parser.add_argument("--quiet", action="store_true")', source)
        self.assertIn('"-i",', source)
        self.assertIn('"-o",', source)
        self.assertIn('"--instancing-style",', source)
        self.assertIn('"--up-axis",', source)
        self.assertNotIn("os.execv", source)

    def test_adapter_commits_atomically_and_seals_source_and_output(self):
        adapter = self._load_adapter()
        with tempfile.TemporaryDirectory(prefix="simready-adapter-test-") as temporary:
            root = Path(temporary)
            converter = root / "fake-converter.py"
            converter.write_text(
                f"#!{sys.executable}\n"
                "import pathlib, sys\n"
                "output = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
                "output.write_bytes(b'fresh-usd-crate')\n",
                encoding="utf-8",
            )
            converter.chmod(0o755)
            adapter.CONVERTER = converter
            source = root / "part.step"
            source.write_bytes(b"STEP-F35")
            output = root / "part.usdc"
            report = root / "conversion-report.json"
            canonical = {
                "canonical_namespace": True,
                "canonical_default_prim_path": "/part",
                "pre_normalization_default_prim_path": "/part",
                "flattened_for_namespace_stability": False,
                "stable_temporary_output_basename": True,
            }
            with mock.patch.object(
                adapter, "_validate_canonical_namespace", return_value=canonical
            ) as validate_namespace:
                result = adapter.main(
                    [
                        str(source),
                        str(output),
                        "--report",
                        str(report),
                        "--up-axis",
                        "z",
                        "--quiet",
                    ]
                )
            self.assertEqual(result, 0)
            temporary_input, final_output = validate_namespace.call_args.args
            self.assertNotEqual(temporary_input.parent, output.parent)
            self.assertEqual(temporary_input.name, output.name)
            self.assertEqual(final_output, output.resolve())
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "passed")
            self.assertIs(payload["atomic_output_commit"], True)
            self.assertIs(payload["source_stable_during_conversion"], True)
            self.assertEqual(payload["requested_up_axis"], "Z")
            self.assertTrue(payload["canonical_namespace"])
            self.assertEqual(payload["canonical_default_prim_path"], "/part")
            self.assertTrue(payload["stable_temporary_output_basename"])
            self.assertEqual(
                payload["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest()
            )
            self.assertEqual(
                payload["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest()
            )
            self.assertFalse(list(root.glob(".part.*.tmp")))

    def test_failed_conversion_cannot_overwrite_the_previous_output(self):
        adapter = self._load_adapter()
        with tempfile.TemporaryDirectory(prefix="simready-adapter-failure-") as temporary:
            root = Path(temporary)
            converter = root / "failing-converter.py"
            converter.write_text(
                f"#!{sys.executable}\n"
                "raise SystemExit(7)\n",
                encoding="utf-8",
            )
            converter.chmod(0o755)
            adapter.CONVERTER = converter
            source = root / "part.step"
            source.write_bytes(b"STEP-F35")
            output = root / "part.usdc"
            output.write_bytes(b"previous-sealed-output")
            previous = output.read_bytes()
            report = root / "conversion-report.json"
            result = adapter.main(
                [
                    str(source),
                    str(output),
                    "--report",
                    str(report),
                    "--up-axis",
                    "z",
                    "--quiet",
                ]
            )
            self.assertNotEqual(result, 0)
            self.assertEqual(output.read_bytes(), previous)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "failed")
            self.assertIs(payload["atomic_output_commit"], False)
            self.assertIsNone(payload["output_sha256"])
            self.assertFalse(list(root.glob(".part.*.tmp")))

    def test_failed_namespace_validation_cannot_overwrite_the_previous_output(self):
        adapter = self._load_adapter()
        with tempfile.TemporaryDirectory(prefix="simready-adapter-normalize-") as temporary:
            root = Path(temporary)
            converter = root / "fake-converter.py"
            converter.write_text(
                f"#!{sys.executable}\n"
                "import pathlib, sys\n"
                "output = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
                "output.write_bytes(b'fresh-usd-crate')\n",
                encoding="utf-8",
            )
            converter.chmod(0o755)
            adapter.CONVERTER = converter
            source = root / "part.step"
            source.write_bytes(b"STEP-F35")
            output = root / "part.usdc"
            output.write_bytes(b"previous-sealed-output")
            previous = output.read_bytes()
            report = root / "conversion-report.json"
            with mock.patch.object(
                adapter,
                "_validate_canonical_namespace",
                side_effect=RuntimeError("synthetic namespace failure"),
            ):
                result = adapter.main(
                    [str(source), str(output), "--report", str(report), "--quiet"]
                )
            self.assertEqual(result, 2)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "failed")
            self.assertFalse(payload["canonical_namespace"])
            self.assertFalse(payload["atomic_output_commit"])
            self.assertIsNone(payload["output_sha256"])
            self.assertIn("USD namespace validation failed", payload["errors"][0])
            self.assertEqual(output.read_bytes(), previous)
            self.assertFalse(list(root.glob(".part.*.tmp")))

    def test_image_build_executes_a_real_step_to_usd_smoke(self):
        dockerfile = (ROOT / "containers/simready-workflow.Dockerfile").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "COPY containers/simready-preflight/formats.py "
            "/opt/usd-convert-cad-preflight/src/usd_convert_cad/formats.py",
            dockerfile,
        )
        self.assertIn("37024.013-interface-proxy.step", dockerfile)
        self.assertIn("smoke-a/smoke.usdc", dockerfile)
        self.assertIn("smoke-b/smoke.usdc", dockerfile)
        self.assertIn("Sdf.Path('/smoke')", dockerfile)
        self.assertIn("GetPseudoRoot().GetChildren()", dockerfile)
        self.assertIn("GetRootLayer().documentation", dockerfile)
        self.assertIn("GetRelationships()", dockerfile)
        self.assertIn("GetConnections()", dockerfile)
        self.assertIn("GetObjectAtPath(target)", dockerfile)
        self.assertNotIn("GetPrimAtPath(target.GetPrimPath())", dockerfile)
        self.assertIn("sha256(path.read_bytes())", dockerfile)
        adapter = (PREFLIGHT / "convert.py").read_text(encoding="utf-8")
        self.assertIn("return directory / output.name, directory", adapter)
        self.assertNotIn("BatchNamespaceEdit", adapter)
        self.assertNotIn("stage.Flatten", adapter)


if __name__ == "__main__":
    unittest.main()
