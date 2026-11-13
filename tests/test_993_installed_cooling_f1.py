import gzip
import hashlib
import json
import math
from pathlib import Path
import runpy
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/"twins/993-installed-cooling-f1"
MODEL=runpy.run_path(str(STUDY/"source/screen_flow.py"))


class InstalledCoolingTests(unittest.TestCase):
    def test_parallel_branches_conserve_mass_and_share_pressure(self):
        ks=[1,4,9,16,25,36]
        qs,pressure=MODEL["branches"](3,ks)
        self.assertAlmostEqual(sum(qs),3)
        for k,q in zip(ks,qs):self.assertAlmostEqual(k*q*q,pressure)
        self.assertAlmostEqual(qs[0]/qs[-1],6)
        qs,p=MODEL["branches"](6,[3]*6)
        for q in qs:self.assertAlmostEqual(q,1)
        self.assertAlmostEqual(p,3)

    def test_invalid_flow_and_release_claims_are_rejected(self):
        for q,ks in ((math.nan,[1]*6),(-1,[1]*6),(1,[0]*6),(1,[1]*5)):
            with self.assertRaises(ValueError):MODEL["branches"](q,ks)
        card=json.loads((STUDY/"study.json").read_text())
        MODEL["validate"](card)
        card["airflow_gain_verified"]=True
        with self.assertRaises(ValueError):MODEL["validate"](card)

    def test_missing_independent_interfaces_keep_acceptance_blocked(self):
        contract=json.loads((STUDY/"interface-contract.json").read_text())
        self.assertFalse(contract["functional_acceptance"])
        self.assertEqual(len(contract["interfaces"]),6)
        for item in contract["interfaces"]:
            self.assertIsNone(item["measured_geometry"])
            self.assertEqual(item["evidence"],[])
            self.assertTrue(item["load_path"])

    def test_retained_sensitivity_has_balanced_energy_and_mass(self):
        report=json.loads((STUDY/"results/flow-screen.json").read_text())
        self.assertEqual(len(report["cases"]),18)
        for path,digest in report["source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
        for case in report["cases"]:
            self.assertAlmostEqual(sum(case["branch_flows_m3_s"]),case["flow_m3_s"])
            self.assertLess(abs(case["pressure_balance_residual_pa"]),.001)
            self.assertFalse(case["performance_accepted"])
            self.assertFalse(case["cfd_computed"])
            if case["hypothetical_equal_branch_resistance"]:self.assertLess(case["branch_flow_cv"],1e-12)
        base=next(c for c in report["cases"] if c["id"]==report["baseline"])
        large=next(c for c in report["cases"] if c["id"]=="twist0_core700x500_balance0")
        self.assertLess(large["core_pressure_loss_pa"],base["core_pressure_loss_pa"])

    def test_native_geometry_hashes_and_review_outputs(self):
        report=json.loads((STUDY/"derived/geometry-review.json").read_text())
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["measured_fit"])
        for path,digest in report["source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
        for path,digest in report["output_hashes"].items():
            self.assertEqual(hashlib.sha256((STUDY/"derived"/path).read_bytes()).hexdigest(),digest)
        self.assertEqual(len(report["parts"]),17)
        for part in report["parts"]:
            raw=gzip.decompress((STUDY/"derived/native"/(part["name"]+".stl.gz")).read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(),part["cleaned_stl_sha256"])
            self.assertTrue(part["watertight"])
            self.assertEqual(part["bodies"],1)

    def test_failed_meshes_never_claim_flow_results(self):
        report=json.loads((STUDY/"results/cfd/receipt.json").read_text())
        self.assertEqual(len(report["attempts"]),6)
        self.assertFalse(report["flow_solver_started"])
        self.assertFalse(report["converged_cfd"])
        self.assertIsNone(report["winner"])
        self.assertEqual(report["current_preparer_sha256"],hashlib.sha256((STUDY/"source/prepare_duct_cfd.py").read_bytes()).hexdigest())
        for path,digest in report["files"].items():
            self.assertEqual(hashlib.sha256((STUDY/"results/cfd"/path).read_bytes()).hexdigest(),digest)
        for case in report["attempts"]:
            log=gzip.decompress((STUDY/f'results/cfd/attempt-{case["attempt"]:03d}/log.checkMesh.gz').read_bytes()).decode()
            self.assertIn(f'Failed {case["failed_extended_checks"]} mesh checks.',log)
            self.assertFalse(case["accepted"])

    def test_mesh_audit_keeps_the_attempt_5_input_inadmissible(self):
        folder=STUDY/"results/cfd/audit-20261110"
        runtime=json.loads((folder/"runtime.json").read_text())
        for path,digest in runtime["files"].items():
            self.assertEqual(hashlib.sha256((folder/path).read_bytes()).hexdigest(),digest)
        self.assertFalse(runtime["mesh_admitted"])
        report=json.loads((folder/"mesh-audit.json").read_text())
        auditor=STUDY/"source/audit_mesh_admission.py"
        self.assertEqual(report["auditor_sha256"],hashlib.sha256(auditor.read_bytes()).hexdigest())
        self.assertTrue(report["reproduction"]["all_compared_metrics_identical"])
        verdict=report["verdict"]
        self.assertFalse(verdict["input_admissible_for_settings_sweep"])
        self.assertFalse(verdict["mesh_admitted"])
        self.assertFalse(verdict["flow_solver_started"])
        self.assertTrue(verdict["concave_cells_at_designed_sharp_edges"])
        self.assertEqual(len(report["concave_cells"]),report["reproduction"]["reproduced"]["concave_cells"])
        native=report["native_voxel_surface"]["sharp_edges_by_construction"]
        self.assertNotIn("smooth_surface_no_constructive_edge",native)
        audit=runpy.run_path(str(auditor))
        inputs=STUDY/"results/cfd/reproduction-inputs"
        g=json.loads((inputs/"study.json").read_text())["geometry"]
        centres=np.array([cell["centre_mm"] for cell in report["concave_cells"]])
        rows=audit["nearest_junctions"](centres,g,audit["CELL_TOL_MM"])
        self.assertEqual([r["construction"] for r in rows],[c["construction"] for c in report["concave_cells"]])
        _,mesh,regions,region=audit["load_analysis_surface"](inputs/"duct.stl.gz")
        recorded=dict(report["analysis_surface"]);recorded.pop("preparation")
        self.assertEqual(json.loads(json.dumps(audit["surface_audit"](mesh,g,regions,region))),recorded)

    def test_mesh_audit_junction_rule_on_known_points(self):
        audit=runpy.run_path(str(STUDY/"source/audit_mesh_admission.py"))
        g=json.loads((STUDY/"study.json").read_text())["geometry"]
        zf=g["fan_centre_z_mm"];r=g["fan_radius_mm"]+g["tip_gap_mm"]
        points=np.array([
            [r,-50,zf],                                     # cylinder side meets the plenum front face
            [0,g["alternator_rear_y_mm"],zf-g["alternator_radius_mm"]],  # alternator rear rim inside the plenum
            [0,125,225],                                    # middle of the plenum top: smooth
            [g["outlet_x_mm"]-6,0,g["outlet_z_mm"]],        # outlet disc interior, away from its rim
        ],float)
        rows=audit["nearest_junctions"](points,g,audit["SURFACE_TOL_MM"])
        self.assertEqual([row["construction"] for row in rows],[
            "fan_cylinder_plenum_hard_union_seam","alternator_rear_rim_hard_subtraction",
            "smooth_surface_no_constructive_edge","smooth_surface_no_constructive_edge"])


if __name__=="__main__":unittest.main()
