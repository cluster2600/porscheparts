"""Contracts for the amd64 geometry/audit environment; not native execution."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PicoGKGeometryWorkstationTests(unittest.TestCase):
    def test_python_audit_runtime_is_installed_and_witness_is_invoked(self):
        dockerfile = (ROOT / "containers/picogk-m64.Dockerfile").read_text()
        smoke = (ROOT / "containers/m64-leap71/picogk-smoke.sh").read_text()
        self.assertIn("python3 -m venv /opt/geometry-qa", dockerfile)
        self.assertIn("geometry-qa-resolved.txt", dockerfile)
        self.assertIn("/opt/geometry-qa/bin/python /opt/picogk-witness/geometry-python-smoke.py", smoke)

    def test_top_level_requirements_are_exact_versions(self):
        lines = (ROOT / "containers/m64-leap71/geometry-qa-requirements.txt").read_text().splitlines()
        packages = [line for line in lines if line and not line.startswith("#")]
        self.assertEqual(len(packages), 8)
        for package in packages:
            self.assertRegex(package, r"^[a-z0-9_-]+==[0-9]+\.[0-9]+\.[0-9]+$")

    def test_witness_scope_stays_synthetic_and_offline(self):
        source = (ROOT / "containers/m64-leap71/geometry-python-smoke.py").read_text()
        self.assertIn('"head_geometry_tested": False', source)
        self.assertIn('"manufacturing_authorized": False', source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urlopen", source)


if __name__ == "__main__":
    unittest.main()
