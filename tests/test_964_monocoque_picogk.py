import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "twins/964-chassis/monocoque/picogk-rings"


class MonocoquePicogkTests(unittest.TestCase):
    def test_parameters_carry_basis_and_status_stays_prohibited(self):
        spec = json.loads((STUDY / "params/monocoque-f0.json").read_text(encoding="utf-8"))
        self.assertIn("prohibited_pending_engineering", spec["status"])
        for name, p in spec["parameters"].items():
            self.assertIn(p["basis"], {"main_model", "assumption", "published", "measured"}, name)
            self.assertTrue(p.get("note") or p.get("source"), name)
        # Every parameter that places geometry and comes from the shell model cites it.
        for name, p in spec["parameters"].items():
            if p["basis"] == "main_model":
                self.assertIn("build_shell.py", p["source"], name)

    @unittest.skipIf(any(importlib.util.find_spec(m) is None for m in ("numpy", "scipy", "matplotlib")),
                     "numpy, scipy and matplotlib required by build_shell.py")
    def test_member_paths_are_symmetric_and_inside_the_body(self):
        spec = importlib.util.spec_from_file_location("prepare", STUDY / "prepare.py")
        prepare = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prepare)
        with tempfile.TemporaryDirectory() as tmp:
            geo = prepare.main(STUDY / "params/monocoque-f0.json", tmp)
            self.assertTrue((Path(tmp) / "body-closed.stl").stat().st_size > 1_000_000)
        st = geo["stations"]
        xs, w, top = st["x"], st["half_width"], st["top"]
        for name, path in geo["paths"].items():
            for x, y, z in path["points"]:
                i = min(range(len(xs)), key=lambda k: abs(xs[k] - x))
                self.assertLessEqual(abs(y), w[i] + 1.0, name)          # inside the plan outline
                self.assertLessEqual(z, top[i] + 1.0, name)             # under the roof line
            if name.endswith("_L"):
                mirror = geo["paths"][name[:-2] + "_R"]["points"]
                for (x1, y1, z1), (x2, y2, z2) in zip(path["points"], mirror):
                    self.assertAlmostEqual(x1, x2, places=6)
                    self.assertAlmostEqual(y1, -y2, places=6)
                    self.assertAlmostEqual(z1, z2, places=6)
        # The front ring closes: cowl and header cross members span both A-pillars.
        self.assertIn("windscreen_header", geo["paths"])
        self.assertIn("windscreen_cowl", geo["paths"])


if __name__ == "__main__":
    unittest.main()
