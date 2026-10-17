"""Lattice and VDB execution is evidence of software behaviour, not engine qualification."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "twins/962-cylinder-head-f0"


class BionicFieldTests(unittest.TestCase):
    def test_changed_lattice_library_blocks_inspection_before_output(self):
        s = importlib.util.spec_from_file_location("bionic", FAMILY / "source/bionic/inspect_and_render.py")
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            with self.assertRaisesRegex(ValueError, "LatticeLibrary differs"):
                m.inspect(p, p, p, p, p / "output")
            self.assertFalse((p / "output").exists())

    def test_native_ribs_and_vdb_roundtrip_remain_unqualified(self):
        r = json.loads((FAMILY / "derived/bionic-report.json").read_text())
        for flag in ("manufacturing_authorized", "is_fitment_validated", "material_qualified",
                     "strength_validated", "wall_thickness_qualified", "hydraulic_performance_validated",
                     "thermal_improvement_validated", "structural_optimisation_executed"):
            self.assertIs(r[flag], False)
        for relative, digest in r["source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)
        self.assertTrue(r["solid"]["watertight"] and r["solid"]["consistent_winding"])
        self.assertEqual(r["solid"]["surface_components"], 1)
        parent = json.loads((FAMILY / "derived/architecture-report.json").read_text())
        for n, digest in r["passage_raw_hashes"].items():
            self.assertEqual(digest, parent["mesh_metrics"][n]["raw_sha256"])
        f = r["native_fields_report"]
        self.assertTrue(f["lattice_library_executed"] and f["vdb_domains_equal"])
        self.assertTrue(f["all_active_values_checked_bidirectionally"])
        self.assertGreater(f["cell_count"], 0)
        self.assertGreater(f["scalar_values_checked_each_direction"], 1_000_000)
        self.assertGreater(f["vector_values_checked_each_direction"], 1_000_000)
        self.assertFalse(f["fluid_solver_executed"])
        self.assertEqual({x["type"] for x in f["fields"]}, {"Voxels", "ScalarField", "VectorField"})
        self.assertEqual(len(f["fields"]), 5)
        for n, item in r["images"].items():
            data = (FAMILY / "derived/bionic-views" / (n + ".png")).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
            self.assertEqual(struct.unpack(">II", data[16:24]), (1600, 1200))


if __name__ == "__main__":
    unittest.main()
