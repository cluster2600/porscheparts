import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONO = ROOT / "twins/964-chassis/monocoque"
PICOGK = MONO / "picogk"
GROUPS = ("skin", "sections", "panels", "tubs")


class ZesadMonocoquePicoGKTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = json.loads((MONO / "derived/zesad-monocoque.report.json").read_text(encoding="utf-8"))

    def test_report_is_a_design_envelope_from_the_pinned_kernel(self) -> None:
        self.assertIn("prohibited_pending_engineering", self.report["model"])
        self.assertTrue(self.report["kernel"].startswith("PicoGK"))
        # The native image imports picogk.26.2.so: the run must come from that runtime.
        self.assertIn("26.2", self.report["kernel"])
        self.assertLessEqual(self.report["voxel_mm"], 3.0)
        self.assertIn("ASSUMED", self.report["mass_basis"])

    def test_every_member_group_is_built_and_weighed(self) -> None:
        total = 0.0
        for g in GROUPS:
            group = self.report["groups"][g]
            self.assertGreater(group["volume_dm3"], 0.0, g)
            self.assertGreater(group["area_m2_estimate"], 0.0, g)
            self.assertTrue(group["assumed_layup"], g)
            total += group["mass_kg_estimate"]
        self.assertAlmostEqual(total, self.report["mass_kg_estimate"], delta=0.2)

    def test_envelope_is_the_plate_50_05a_shell(self) -> None:
        length, width, height = self.report["envelope"]["size_mm"]
        self.assertAlmostEqual(length, 3780, delta=15)        # d from -700 to 3080
        self.assertAlmostEqual(width, 1700, delta=15)         # twice the traced half width
        self.assertAlmostEqual(height, 1310 - 140, delta=15)  # roof at the published height, floor at the trace

    def test_project_uses_the_pinned_kernel_and_versions_no_voxel_output(self) -> None:
        csproj = (PICOGK / "ZesadMonocoque.csproj").read_text(encoding="utf-8")
        self.assertIn("$(UpstreamRoot)/PicoGK/PicoGK.csproj", csproj)
        self.assertIn("porscheparts-picogk-native", (PICOGK / "run.sh").read_text(encoding="utf-8"))
        self.assertEqual((PICOGK / ".gitignore").read_text(encoding="utf-8").split(), ["work/"])
        lock = (ROOT / "containers/m64-leap71/sources.lock").read_text(encoding="utf-8")
        self.assertRegex(lock, re.compile(r"^PicoGK [0-9a-f]{40}$", re.M))

    def test_evidence_files_exist(self) -> None:
        for name in ("zesad-monocoque-views.png", "zesad-monocoque-sections.png", "zesad-monocoque-turntable.gif"):
            self.assertGreater((MONO / "evidence" / name).stat().st_size, 10_000, name)
        self.assertLess((MONO / "derived/zesad-monocoque.vtp").stat().st_size, 8_000_000)


if __name__ == "__main__":
    unittest.main()
