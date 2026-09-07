"""Offline routing/provenance tests. No renderer, GPU, or engineering validation."""
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/m64-cylinder-head/remote-simready/phases/render.py"
README = ROOT / "twins/m64-cylinder-head/remote-simready/README.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RenderInspectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="m64-inspection-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "m64-fixture"
        self.output = self.root / "results/render"
        self.output.mkdir(parents=True)
        self.asset = self.root / "results/physics/fixture.usda"
        self.asset.parent.mkdir()
        self.asset.write_text("#usda 1.0\n")
        self.profile_path = self.root / "results/profile-initial/reference.json"
        self.profile_path.parent.mkdir()
        self.profile = {"passed": False, "issues": [{"requirement_id": "GSP.001"}]}
        self.profile_path.write_text(json.dumps(self.profile))
        self.original_profile = self.profile_path.read_bytes()
        self.events = []
        self.phase = types.SimpleNamespace(
            root=self.root, output=self.output, manifest_sha256="a" * 64,
            require=mock.Mock(side_effect=self.require),
            asset_from=mock.Mock(side_effect=self.asset_from),
            invoke=mock.Mock(side_effect=self.invoke),
        )
        self.exit_code = 0

    def require(self, name, *, passed=True):
        self.events.append(("require", name, passed))
        self.assertEqual(name, "profile-initial")
        self.assertFalse(passed)
        return self.profile

    def asset_from(self, name):
        self.events.append(("asset", name))
        self.assertEqual(name, "physics")
        return self.asset

    def invoke(self, reference, arguments):
        self.events.append(("invoke", reference))
        self.assertTrue((self.output / "inspection.json").is_file())
        return self.exit_code

    def run_phase(self):
        common = types.ModuleType("common")
        common.Phase = mock.Mock(return_value=self.phase)
        common.sha = sha
        with mock.patch.dict(sys.modules, {"common": common}), self.assertRaises(SystemExit) as caught:
            runpy.run_path(str(SCRIPT), run_name="__main__")
        common.Phase.assert_called_once_with("render")
        return caught.exception.code

    def test_failed_initial_profile_allows_inspection_of_verified_physics_only(self):
        self.assertEqual(self.run_phase(), 0)
        self.assertEqual(self.events, [("require", "profile-initial", False),
                                       ("asset", "physics"), ("invoke", "ovrtx-render-service")])
        self.phase.invoke.assert_called_once_with("ovrtx-render-service", [
            self.asset, self.output / "inspection.png", "--width", "1600", "--height", "1200"])
        self.assertEqual(self.profile_path.read_bytes(), self.original_profile)

    def test_sidecar_binds_scope_to_exact_source_and_does_not_claim_success(self):
        self.run_phase()
        report = json.loads((self.output / "inspection.json").read_text())
        self.assertEqual(report["purpose"], "pre_conformance_static_inspection")
        self.assertEqual(report["job_id"], self.root.name)
        self.assertEqual(report["job_manifest_sha256"], "a" * 64)
        self.assertEqual(report["source_phase"], "physics")
        self.assertEqual(report["source_usd_sha256"], sha(self.asset))
        self.assertEqual(report["profile_initial_report_sha256"], sha(self.profile_path))
        self.assertFalse(report["profile_initial_passed"])
        self.assertFalse(report["is_final_conformed_render"])
        self.assertFalse(report["simulation_validated"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertTrue(report["render_success_not_asserted"])
        self.assertIn("findings remain unchanged", report["warnings"][0])
        self.assertIn("not qualified engineering properties", report["warnings"][1])
        self.assertIn("No engine, thermal, strength or manufacturing validation", report["warnings"][2])
        # The phase must not fabricate or rewrite the common receipt/NVIDIA report.
        self.assertFalse((self.output / "receipt.json").exists())
        self.assertFalse((self.output / "reference.json").exists())

    def test_renderer_failure_stays_failure(self):
        self.exit_code = 1
        self.assertEqual(self.run_phase(), 1)
        report = json.loads((self.output / "inspection.json").read_text())
        self.assertTrue(report["render_success_not_asserted"])
        self.assertFalse(report["manufacturing_authorized"])

    def test_passing_initial_profile_does_not_become_engine_validation(self):
        self.profile = {"passed": True, "issues": []}
        self.profile_path.write_text(json.dumps(self.profile))
        self.assertEqual(self.run_phase(), 0)
        report = json.loads((self.output / "inspection.json").read_text())
        self.assertTrue(report["profile_initial_passed"])
        self.assertFalse(report["simulation_validated"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["is_final_conformed_render"])

    def test_invalid_profile_evidence_prevents_rendering(self):
        self.phase.require.side_effect = ValueError("profile evidence mismatch")
        with self.assertRaisesRegex(ValueError, "profile evidence mismatch"):
            self.run_phase()
        self.phase.asset_from.assert_not_called()
        self.phase.invoke.assert_not_called()
        self.assertFalse((self.output / "inspection.json").exists())

    def test_invalid_physics_handoff_prevents_rendering(self):
        self.phase.asset_from.side_effect = ValueError("USD dependency handoff mismatch")
        with self.assertRaisesRegex(ValueError, "USD dependency handoff mismatch"):
            self.run_phase()
        self.phase.invoke.assert_not_called()
        self.assertFalse((self.output / "inspection.json").exists())

    def test_readme_places_inspection_before_conformance_and_keeps_warning(self):
        text = README.read_text()
        order = text.split("Ordre d'exécution :", 1)[1].split("Chaque appel", 1)[0]
        names = re.findall(r"`([^`]+)`", order)
        self.assertLess(names.index("physics"), names.index("profile-initial"))
        self.assertLess(names.index("profile-initial"), names.index("render"))
        self.assertLess(names.index("render"), names.index("conform"))
        self.assertIn("n'est pas le rendu final d'un USD conforme", text)
        self.assertIn("ne remplace\naucune validation", text)


if __name__ == "__main__":
    unittest.main()
