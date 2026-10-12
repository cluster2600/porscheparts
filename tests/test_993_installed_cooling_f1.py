import gzip
import hashlib
import json
import math
from pathlib import Path
import runpy
import unittest

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
        self.assertEqual(len(report["attempts"]),5)
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


if __name__=="__main__":unittest.main()
