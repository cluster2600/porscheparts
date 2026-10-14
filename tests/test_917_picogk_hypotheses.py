import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/"models/917-engine-reconstruction/hypothesis"
SPEC = importlib.util.spec_from_file_location("hypothesis917",HERE/"run.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HypothesisTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((HERE/"assumptions.json").read_text())

    def test_motion_closes_and_rejects_two_coverage_hypotheses(self):
        result = MODULE.motion_report(self.config)
        self.assertLess(result["maximum_rod_closure_error_mm"],1e-9)
        self.assertEqual([b["travel_mm"] for b in result["banks"]],[66,66])
        self.assertEqual([b["hypothesis_consistent_with_full_skirt_coverage"] for b in result["rod_length_sensitivity"]],[False,True,False])
        self.assertEqual([b["minimum_axial_skirt_coverage_residual_mm"] for b in result["rod_length_sensitivity"]],[-5,5,-7])

    def test_shared_crankpin_uses_same_phase_for_opposed_banks(self):
        d = self.config["dimensions_mm"]
        for angle in (0,30,90,127,180,240,360):
            positive, negative = MODULE.position(d,angle,1),MODULE.position(d,angle,-1)
            self.assertEqual(positive[:2],negative[:2])
            self.assertAlmostEqual(positive[2]+negative[2],2*positive[0])
            self.assertAlmostEqual(-negative[2],MODULE.position(d,angle+180,1)[2])

    def test_exact_acceleration_agrees_with_independent_finite_difference(self):
        d = self.config["dimensions_mm"]
        step = .01
        for sign in (-1,1):
            for angle in (0,37,90,151,180,270):
                finite = (MODULE.position(d,angle+step,sign)[2]-2*MODULE.position(d,angle,sign)[2]
                          +MODULE.position(d,angle-step,sign)[2])/math.radians(step)**2
                self.assertAlmostEqual(MODULE.acceleration(d,angle,sign),finite,delta=2e-5)

    def test_invalid_dimensions_and_nonfinite_loads_are_rejected(self):
        for key,value in (("rod_length",20),("pin_inner_diameter",25),("cylinder_outer_diameter",80),("fin_thickness",20),
                          ("piston_crown_thickness",45),("piston_skirt_thickness",50),("piston_boss_inner_x",5),
                          ("bore",True),("stroke",float("nan"))):
            c = copy.deepcopy(self.config);c["dimensions_mm"][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):MODULE.validate(c)
        c = copy.deepcopy(self.config);c["rpm_cases"]=[float("inf")]
        with self.assertRaises(ValueError):MODULE.validate(c)

    def test_geometry_probe_detects_missing_wristpin_hole(self):
        try:
            import trimesh
            import rtree
            import scipy.spatial
        except ImportError:
            self.skipTest("scientific mesh QA dependencies absent")
        solid = trimesh.creation.box(extents=[80,40,80])
        with self.assertRaisesRegex(ValueError,"probe rejection"):
            MODULE.inspect(solid,"piston",self.config["dimensions_mm"],8)

    def test_countertrial_removes_only_zero_faces_and_rejects_inverted_volume(self):
        try:
            import numpy as np
            import trimesh
        except ImportError:
            self.skipTest("scientific mesh QA dependencies absent")
        cube = trimesh.creation.box()
        raw = trimesh.Trimesh(cube.vertices,np.vstack([cube.faces,[0,0,1]]),process=False)
        candidate,trial = MODULE.exact_zero_candidate(raw)
        self.assertEqual(trial["removed_zero_cross_product_faces"],1)
        self.assertEqual(trial["vertex_displacement"],0)
        self.assertTrue(candidate.is_watertight)
        inverted = trimesh.Trimesh(cube.vertices,cube.faces[:,::-1],process=False)
        with self.assertRaises(ValueError):MODULE.exact_zero_candidate(inverted)

    def test_record_matches_sources_without_promoting_sampled_clearance_to_release(self):
        record = json.loads((HERE/"execution-20261010.json").read_text())
        digest = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(record["assumptions_sha256"],digest(HERE/"assumptions.json"))
        for name,value in record["source_sha256"].items():
            self.assertEqual(value,digest(HERE/name))
        for name,value in record["reused_witness_sha256"].items():
            self.assertEqual(value,digest(MODULE.WITNESS/name))
        self.assertEqual(record["existing_slider_helper_sha256"],digest(ROOT/"twins/reference-917-engine/source/kinematics_f2_math.py"))
        self.assertFalse(any(record["release_gates"].values()))
        self.assertFalse(record["piston_clearance_resolved_by_voxel_grid"])
        self.assertTrue(record["interference"]["assembly_interference_screen_pass"])
        self.assertEqual(len(record["interference"]["witnesses"]),16)
        self.assertFalse(any(w["rod_small_end_inside_piston_material"] for w in record["interference"]["witnesses"]))
        self.assertEqual(record["assembly_instances"],48)
        self.assertEqual(len(record["load_cases"]),18)


if __name__ == "__main__":
    unittest.main()
