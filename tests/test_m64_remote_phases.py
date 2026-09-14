"""Offline checks only; these tests do not execute NVIDIA or validate a head."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock


PHASES = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/remote-simready/phases"
SPEC = importlib.util.spec_from_file_location("m64_phase_common", PHASES / "common.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
try:
    from pxr import Sdf
except ImportError:
    Sdf = None


class RemotePhasesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="m64-phases-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "m64-test"
        self.root.mkdir()
        self.manifest = {"profile": MODULE.PROFILE, "job_id": "m64-test",
                         "deadline_epoch": int(time.time()) + 300, "files": []}
        (self.root / "job-manifest.json").write_text(json.dumps(self.manifest))

    def phase(self, name="preflight", *, preflight=True):
        with mock.patch.object(sys, "argv", ["phase.py", "--job-root", str(self.root)]):
            return MODULE.Phase(name, preflight=preflight)

    def source(self):
        (self.root / "inputs").mkdir()
        asset = self.root / "inputs/assembly.step"
        asset.write_text("synthetic STEP fixture")
        self.manifest["files"] = [{"path": "inputs/assembly.step", "size": asset.stat().st_size,
                                   "sha256": MODULE.sha(asset)}]
        (self.root / "job-manifest.json").write_text(json.dumps(self.manifest))
        return asset

    def reference(self):
        script = self.root / "skill/references/preflight/scripts/preflight.py"
        script.parent.mkdir(parents=True)
        script.write_text("# never executed by this test\n")

    def exports(self, phase):
        path = phase.output / "preflight.env"
        path.write_text("export PHYSICAL_AI_REQUIRE_PREFLIGHT='1'\n"
                        f"export PHYSICAL_AI_PREFLIGHT_MANIFEST='{phase.report}'\n")
        return path

    def receipt(self, phase, **fields):
        result = {"schema_version": "1.0.0", "profile": MODULE.PROFILE,
                  "job_id": self.root.name, "job_manifest_sha256": MODULE.sha(self.root / "job-manifest.json"),
                  "phase": phase.name, "passed": True, "report_sha256": MODULE.sha(phase.report),
                  "simulation_validated": False, "manufacturing_authorized": False}
        result.update(fields)
        (phase.output / "receipt.json").write_text(json.dumps(result))
        return result

    def root_only_dependencies(self, root, asset):
        # Unit-test stub, never substituted in production. Real pxr tests below.
        return [{"path": str(asset.relative_to(root / "results")),
                 "size": asset.stat().st_size, "sha256": MODULE.sha(asset)}]

    def run_mock(self, phase, reference="preflight", *, side_effect=None):
        process = mock.Mock()
        process.wait.return_value = 0
        with mock.patch.object(MODULE.subprocess, "Popen", return_value=process, side_effect=side_effect):
            return phase.invoke(reference, [], script="preflight.py" if reference == "preflight" else "run.py")

    def conversion(self, *, relative="converted/assembly.usda"):
        source = self.source()
        script = self.root / "skill/references/convert-to-usd/scripts/run.py"
        script.parent.mkdir(parents=True)
        script.write_text("# never executed\n")
        phase = self.phase("convert")
        asset = phase.output / relative
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text("#usda 1.0\n")
        phase.report.write_text(json.dumps({"errors": [], "source_asset_path": str(source),
                                           "output_usd_path": str(asset)}))
        return phase, asset

    def test_rejects_parent_escape_and_symlinks(self):
        outside = self.root.parent / "outside"
        outside.write_text("private")
        (self.root / "link").symlink_to(outside)
        for path in ("../outside", "link", str(outside)):
            with self.subTest(path=path), self.assertRaises(ValueError):
                MODULE.safe_path(self.root, path)

    def test_exports_are_parsed_not_executed(self):
        self.assertEqual(MODULE.parse_exports("export PHYSICAL_AI_REQUIRE_PREFLIGHT='1'\n"),
                         {"PHYSICAL_AI_REQUIRE_PREFLIGHT": "1"})
        for text in ("export PATH='$(touch evil)'", "export LD_PRELOAD='/tmp/evil'",
                     "export PATH='/usr/bin'; touch evil", "export PATH='/a'\nexport PATH='/b'",
                     "export OPENAI_API_KEY='secret'"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                MODULE.parse_exports(text)

    def test_input_modification_is_rejected(self):
        asset = self.source()
        phase = self.phase()
        self.assertEqual(phase.input("assembly.step"), asset)
        asset.write_text("modified STEP fixture")
        with self.assertRaises(ValueError):
            phase.input("assembly.step")

    def test_phase_cannot_overwrite_previous_attempt(self):
        self.phase()
        with self.assertRaises(ValueError):
            self.phase()

    def test_expired_job_cannot_spawn_process(self):
        self.reference()
        phase = self.phase()
        phase.manifest["deadline_epoch"] = 1
        with mock.patch.object(MODULE.subprocess, "Popen") as popen:
            with self.assertRaises(ValueError):
                phase.invoke("preflight", [], script="preflight.py")
        popen.assert_not_called()

    def test_success_requires_real_structured_success_even_with_exit_zero(self):
        self.reference()
        phase = self.phase()
        phase.report.write_text(json.dumps({"passed": False, "status": "FAIL"}))
        process = mock.Mock()
        process.wait.return_value = 0
        with mock.patch.object(MODULE.subprocess, "Popen", return_value=process):
            self.assertEqual(phase.invoke("preflight", [], script="preflight.py"), 1)
        receipt = MODULE.load(phase.output / "receipt.json")
        self.assertFalse(receipt["passed"])
        self.assertFalse(receipt["manufacturing_authorized"])
        self.assertFalse(receipt["simulation_validated"])

    def test_preflight_ready_receipt_and_tamper_rejection(self):
        self.reference()
        phase = self.phase()
        phase.report.write_text(json.dumps({"status": "ready"}))
        self.exports(phase)
        process = mock.Mock()
        process.wait.return_value = 0
        with mock.patch.object(MODULE.subprocess, "Popen", return_value=process):
            self.assertEqual(phase.invoke("preflight", [], script="preflight.py"), 0)
        self.assertEqual(phase.require("preflight")["status"], "ready")
        phase.report.write_text(json.dumps({"status": "changed"}))
        with self.assertRaises(ValueError):
            phase.require("preflight")

    def test_conversion_schema_without_passed_uses_specific_success_contract(self):
        phase, asset = self.conversion()
        with mock.patch.object(MODULE, "usd_dependencies", side_effect=self.root_only_dependencies):
            self.assertEqual(self.run_mock(phase, "convert-to-usd"), 0)
            self.assertEqual(phase.asset_from("convert"), asset)

    def test_preflight_health_uses_base_url_not_render_suffix(self):
        self.assertEqual(self.phase().env["RENDER_ENDPOINT"], "http://127.0.0.1:8001")

    def test_isolated_runtime_paths_are_used(self):
        phase = self.phase()
        self.assertEqual(MODULE.PYTHON, "/opt/m64-simready-validate/bin/python")
        self.assertEqual(phase.env["PHYSICAL_AI_SIMREADY_VALIDATE_VENV"], "/opt/m64-simready-validate")
        self.assertEqual(phase.env["SIMREADY_FOUNDATION_ROOT"], "/opt/m64-simready-foundation")
        self.assertTrue(phase.env["PATH"].startswith("/opt/m64-simready-validate/bin:"))

    def test_asset_handoff_requires_matching_recorded_hash(self):
        phase = self.phase("convert")
        asset = phase.output / "assembly.usda"
        asset.write_text("#usda 1.0\n")
        phase.report.write_text(json.dumps({"passed": True, "output_usd_path": str(asset)}))
        self.receipt(phase, output_usd_sha256=MODULE.sha(asset),
                     output_usd_dependencies=self.root_only_dependencies(self.root, asset))
        with mock.patch.object(MODULE, "usd_dependencies", side_effect=self.root_only_dependencies):
            self.assertEqual(phase.asset_from("convert"), asset)
        asset.write_text("#usda 1.0\n#modified")
        with self.assertRaises(ValueError):
            phase.asset_from("convert")

    def test_later_diagnostic_can_read_failed_validator_without_passing_it(self):
        phase = self.phase("asset-validation")
        phase.report.write_text(json.dumps({"passed": False, "issues": ["test"]}))
        self.receipt(phase, passed=False)
        with self.assertRaises(ValueError):
            phase.require("asset-validation")
        self.assertFalse(phase.require("asset-validation", passed=False)["passed"])

    def test_wrong_receipt_identity_is_rejected_even_for_failed_diagnostics(self):
        phase = self.phase("asset-validation")
        phase.report.write_text('{"passed": false}')
        for changed in ({"job_id": "m64-other"}, {"job_manifest_sha256": "0" * 64},
                        {"profile": "other"}, {"schema_version": "0"},
                        {"simulation_validated": True}, {"manufacturing_authorized": True}):
            with self.subTest(changed=changed):
                self.receipt(phase, **changed)
                with self.assertRaises(ValueError):
                    phase.require("asset-validation", passed=False)

    def test_changed_job_manifest_cannot_spawn_or_consume_evidence(self):
        self.reference()
        phase = self.phase()
        (self.root / "job-manifest.json").write_text('{"modified": true}')
        with mock.patch.object(MODULE.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(ValueError, "manifest changed"):
                phase.invoke("preflight", [], script="preflight.py")
            with self.assertRaisesRegex(ValueError, "manifest changed"):
                phase.require("preflight", passed=False)
        popen.assert_not_called()

    def test_preflight_environment_is_hashed_and_tampering_blocks_consumption(self):
        self.reference()
        phase = self.phase()
        phase.report.write_text('{"status": "ready"}')
        env = self.exports(phase)
        self.assertEqual(self.run_mock(phase), 0)
        receipt = MODULE.load(phase.output / "receipt.json")
        self.assertEqual(receipt["preflight_env_sha256"], MODULE.sha(env))
        consumer = self.phase("consumer", preflight=False)
        self.assertEqual(consumer.preflight_env_sha256, MODULE.sha(env))
        env.write_text(env.read_text() + "export PATH='/changed'\n")
        with self.assertRaisesRegex(ValueError, "environment changed"):
            phase.require("preflight")
        with self.assertRaisesRegex(ValueError, "environment changed"):
            self.phase("next", preflight=False)

    def test_missing_environment_prevents_ready_preflight_from_passing(self):
        self.reference()
        phase = self.phase()
        phase.report.write_text('{"status": "ready"}')
        self.assertEqual(self.run_mock(phase), 1)
        self.assertFalse(MODULE.load(phase.output / "receipt.json")["passed"])

    def test_explicit_failure_cannot_be_overridden_by_ready_status(self):
        self.reference()
        phase = self.phase()
        phase.report.write_text('{"status": "ready", "passed": false}')
        self.exports(phase)
        self.assertEqual(self.run_mock(phase), 1)
        self.assertFalse(MODULE.load(phase.output / "receipt.json")["passed"])

    def test_truncated_json_keeps_original_and_writes_failure_receipt(self):
        self.reference()
        phase = self.phase()
        text = '{"passed": true, '
        phase.report.write_text(text)
        self.assertEqual(self.run_mock(phase), 1)
        receipt = MODULE.load(phase.output / "receipt.json")
        self.assertEqual(phase.report.read_text(), text)
        self.assertEqual(receipt["report_sha256"], MODULE.sha(phase.report))
        self.assertEqual(receipt["evidence_errors"], [{"stage": "report", "type": "JSONDecodeError"}])
        self.assertFalse(receipt["manufacturing_authorized"])

    def test_popen_error_writes_failure_receipt_without_exception_text(self):
        self.reference()
        phase = self.phase()
        self.assertEqual(self.run_mock(phase, side_effect=FileNotFoundError("private launch context")), 127)
        receipt = MODULE.load(phase.output / "receipt.json")
        self.assertEqual(receipt["exit_code"], 127)
        self.assertIn({"stage": "launch", "type": "FileNotFoundError"}, receipt["evidence_errors"])
        self.assertNotIn("private launch context", json.dumps(receipt))
        self.assertFalse(receipt["passed"])

    def test_timeout_kills_process_group_and_records_truncated_report(self):
        self.reference()
        phase = self.phase()
        phase.report.write_text('{"passed":')
        process = mock.Mock(pid=987654)
        process.wait.side_effect = [MODULE.subprocess.TimeoutExpired("fixture", 1), 0]
        with mock.patch.object(MODULE.subprocess, "Popen", return_value=process), \
                mock.patch.object(MODULE.os, "killpg") as killpg:
            self.assertEqual(phase.invoke("preflight", [], script="preflight.py"), 124)
        killpg.assert_called_once_with(process.pid, MODULE.signal.SIGTERM)
        receipt = MODULE.load(phase.output / "receipt.json")
        self.assertTrue(receipt["deadline_interrupted"])
        self.assertFalse(receipt["passed"])
        self.assertEqual(receipt["report_sha256"], MODULE.sha(phase.report))

    def test_invalid_output_path_writes_failure_receipt(self):
        phase, _ = self.conversion()
        report = MODULE.load(phase.report)
        report["output_usd_path"] = "/outside/results.usda"
        phase.report.write_text(json.dumps(report))
        self.assertEqual(self.run_mock(phase, "convert-to-usd"), 1)
        receipt = MODULE.load(phase.output / "receipt.json")
        self.assertFalse(receipt["passed"])
        self.assertEqual(receipt["report_sha256"], MODULE.sha(phase.report))

    def test_conversion_cannot_claim_an_asset_outside_converted(self):
        phase, _ = self.conversion(relative="assembly.usda")
        self.assertEqual(self.run_mock(phase, "convert-to-usd"), 1)
        self.assertFalse(MODULE.load(phase.output / "receipt.json")["passed"])

    def test_usdz_is_explicitly_unsupported(self):
        phase, _ = self.conversion(relative="converted/assembly.usdz")
        self.assertEqual(self.run_mock(phase, "convert-to-usd"), 1)
        self.assertFalse(MODULE.load(phase.output / "receipt.json")["passed"])

    def test_symlink_converted_directory_is_rejected(self):
        phase, asset = self.conversion()
        asset.unlink()
        asset.parent.rmdir()
        folder = self.root / "other"
        folder.mkdir()
        (folder / asset.name).write_text("#usda 1.0\n")
        asset.parent.symlink_to(folder, target_is_directory=True)
        self.assertEqual(self.run_mock(phase, "convert-to-usd"), 1)
        self.assertFalse(MODULE.load(phase.output / "receipt.json")["passed"])

    def test_symlink_report_is_not_read_or_hashed(self):
        self.reference()
        phase = self.phase()
        outside = self.root.parent / "private.json"
        outside.write_text('{"status": "ready"}')
        phase.report.symlink_to(outside)
        self.assertEqual(self.run_mock(phase), 1)
        receipt = MODULE.load(phase.output / "receipt.json")
        self.assertIsNone(receipt["report_sha256"])
        self.assertTrue(phase.report.is_symlink())

    def test_dependency_closure_tamper_blocks_handoff(self):
        phase, asset = self.conversion()
        tree = self.root_only_dependencies(self.root, asset)
        with mock.patch.object(MODULE, "usd_dependencies", return_value=tree):
            self.assertEqual(self.run_mock(phase, "convert-to-usd"), 0)
        changed = [*tree, {"path": "material/missing.mdl", "size": 1, "sha256": "0" * 64}]
        with mock.patch.object(MODULE, "usd_dependencies", return_value=changed):
            with self.assertRaisesRegex(ValueError, "dependency handoff mismatch"):
                phase.asset_from("convert")

    def test_dependency_paths_reject_external_identifiers_and_symlink_collapse(self):
        results = self.root / "results"
        results.mkdir()
        (results / "layer.usda").write_text("#usda 1.0\n")
        (results / "link").symlink_to(results, target_is_directory=True)
        for value in ("https://example.invalid/private.usd", "omniverse://server/stage.usd",
                      "../job-manifest.json", "link/../layer.usda", "layer.usdz[part.usda]",
                      "anon:layer", "missing.usda"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.dependency_path(results, value, anchor=results)

    @unittest.skipIf(Sdf is None, "pxr runtime not installed; real USD dependency check not run")
    def test_real_usd_closure_includes_payloads_sublayers_and_texture(self):
        phase, asset = self.conversion()
        payload = asset.parent / "payload.usda"
        child = asset.parent / "child.usda"
        texture = asset.parent / "texture.bin"
        texture.write_bytes(b"synthetic texture")
        payload.write_text('#usda 1.0\ndef Xform "Payload" {}\n')
        child.write_text('#usda 1.0\ndef Scope "Material" {\n asset texture = @texture.bin@\n}\n')
        asset.write_text('#usda 1.0\n( subLayers = [@child.usda@] )\n'
                         'def Xform "Root" ( prepend payload = @payload.usda@</Payload> ) {}\n')
        closure = MODULE.usd_dependencies(self.root, asset)
        self.assertEqual({row["path"] for row in closure},
                         {str(path.relative_to(self.root / "results")) for path in (asset, child, payload, texture)})
        self.assertEqual(self.run_mock(phase, "convert-to-usd"), 0)
        self.assertEqual(phase.asset_from("convert"), asset)
        texture.write_bytes(b"modified texture")
        with self.assertRaisesRegex(ValueError, "dependency handoff mismatch"):
            phase.asset_from("convert")

    @unittest.skipIf(Sdf is None, "pxr runtime not installed; real USD dependency check not run")
    def test_real_usd_relative_reference_between_phase_results_is_allowed(self):
        phase, asset = self.conversion()
        material = self.root / "results/material/scene.usda"
        material.parent.mkdir()
        material.write_text('#usda 1.0\n( subLayers = [@../convert/converted/assembly.usda@] )\n')
        self.assertEqual(len(MODULE.usd_dependencies(self.root, material)), 2)

    @unittest.skipIf(Sdf is None, "pxr runtime not installed; real USD dependency check not run")
    def test_real_usd_external_dependency_is_rejected_before_recursive_resolution(self):
        phase, asset = self.conversion()
        asset.write_text('#usda 1.0\n( subLayers = [@/private/not-allowed.usda@] )\n')
        from pxr import UsdUtils
        with mock.patch.object(UsdUtils, "ComputeAllDependencies") as compute:
            with self.assertRaisesRegex(ValueError, "outside results"):
                MODULE.usd_dependencies(self.root, asset)
        compute.assert_not_called()

    @unittest.skipIf(Sdf is None, "pxr runtime not installed; real USD dependency check not run")
    def test_real_usd_binary_root_and_missing_dependency(self):
        phase, asset = self.conversion(relative="converted/assembly.usdc")
        asset.unlink()
        layer = Sdf.Layer.CreateNew(str(asset))
        Sdf.CreatePrimInLayer(layer, "/Root")
        layer.Save()
        self.assertEqual(len(MODULE.usd_dependencies(self.root, asset)), 1)
        layer.subLayerPaths = ["missing.usda"]
        layer.Save()
        with self.assertRaisesRegex(ValueError, "unresolved USD dependency"):
            MODULE.usd_dependencies(self.root, asset)

    @unittest.skipIf(Sdf is None, "pxr runtime not installed; real USD dependency check not run")
    def test_real_usd_remote_url_and_symlink_are_rejected_before_traversal(self):
        phase, asset = self.conversion()
        outside = self.root.parent / "outside.usda"
        outside.write_text("#usda 1.0\n")
        (asset.parent / "link.usda").symlink_to(outside)
        from pxr import UsdUtils
        for value in ("https://example.invalid/layer.usda", "link.usda"):
            asset.write_text(f'#usda 1.0\n( subLayers = [@{value}@] )\n')
            with self.subTest(value=value), mock.patch.object(UsdUtils, "ComputeAllDependencies") as compute:
                with self.assertRaises(ValueError):
                    MODULE.usd_dependencies(self.root, asset)
                compute.assert_not_called()

    @unittest.skipIf(Sdf is None, "pxr runtime not installed; real USD dependency check not run")
    def test_real_usd_dependency_budget_is_bounded(self):
        phase, asset = self.conversion()
        with mock.patch.object(MODULE, "MAX_DEPENDENCIES", 0):
            with self.assertRaisesRegex(ValueError, "budget exceeded"):
                MODULE.usd_dependencies(self.root, asset)
        with mock.patch.object(MODULE, "MAX_DEPENDENCY_BYTES", 0):
            with self.assertRaisesRegex(ValueError, "budget exceeded"):
                MODULE.usd_dependencies(self.root, asset)


if __name__ == "__main__":
    unittest.main()
