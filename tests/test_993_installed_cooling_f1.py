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


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


R2=STUDY/"results/cfd/r2-admission-20261112"
BLENDS={"study-r2a.json":{"reentrant_blend_mm":12},
        "study-r2b.json":{"reentrant_blend_mm":12,"alternator_subtraction_blend_mm":12}}


class InstalledCoolingR2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=runpy.run_path(str(STUDY/"source/audit_mesh_admission_r2.py"))

    def test_r2_cards_add_only_the_blends(self):
        base=json.loads((STUDY/"study.json").read_text())
        for name,blends in BLENDS.items():
            card=json.loads((STUDY/name).read_text())
            self.assertEqual(card["parent_revision"],base["revision"])
            self.assertEqual(card["geometry"],{**base["geometry"],**blends})
            rest={k:v for k,v in card.items() if k not in ("revision","parent_revision","r2_basis","geometry")}
            self.assertEqual(rest,{k:v for k,v in base.items() if k not in ("revision","geometry")})
            self.assertIn("owner's veto",card["r2_basis"])

    def test_r2_model_without_blends_is_the_r1_model(self):
        g=json.loads((STUDY/"study.json").read_text())["geometry"]
        p=np.random.default_rng(452).uniform((-290,-210,5),(290,320,325),(4000,3))
        r1=self.audit["load_base"]()
        r2=self.audit["bind_r2_model"](self.audit["load_base"](),g)
        np.testing.assert_array_equal(r2.fluid_sdf(r2.constituents(p,g)[0]),r1.fluid_sdf(r1.constituents(p,g)[0]))
        blended=self.audit["bind_r2_model"](self.audit["load_base"](),{**g,**BLENDS["study-r2b.json"]})
        far=np.array([[0,125,225],[0,200,155],[g["outlet_x_mm"],0,g["outlet_z_mm"]+30]],float)
        np.testing.assert_allclose(blended.fluid_sdf(blended.constituents(far,g)[0]),r1.fluid_sdf(r1.constituents(far,g)[0]))

    def test_admission_rule_returns_the_r1_verdict(self):
        report=json.loads((STUDY/"results/cfd/audit-20261110/mesh-audit.json").read_text())
        base=self.audit["load_base"]()
        admissible,hard,creases=self.audit["admission"](base,report["analysis_surface"])
        self.assertFalse(admissible)
        self.assertEqual(hard,report["verdict"]["hard_re_entrant_length_mm"])
        self.assertEqual(creases,report["verdict"]["decimation_creases"])
        admissible,hard,creases=self.audit["admission"](base,report["native_voxel_surface"])
        self.assertFalse(admissible)
        self.assertEqual(creases["edges"],0)

    def test_r2_record_binds_its_sources_and_keeps_the_mesh_unadmitted(self):
        runtime=json.loads((R2/"runtime.json").read_text())
        for name,digest in runtime["files"].items():self.assertEqual(sha(R2/name),digest)
        self.assertFalse(runtime["verdict"]["input_admissible_for_settings_sweep"])
        self.assertFalse(runtime["verdict"]["mesh_trial_run"])
        self.assertFalse(runtime["verdict"]["flow_solver_started"])
        r1=json.loads((R2/"generation-r1.json").read_text())
        self.assertEqual(r1["study"]["sha256"],sha(STUDY/"study.json"))
        self.assertEqual(r1["generation"]["geometry_revision"],"R1")
        attempt=json.loads((STUDY/"results/cfd/attempt-005/preparation.json").read_text())
        self.assertEqual(r1["outputs"]["delivery-fluid-domain.stl"],attempt["native_surface_sha256"])
        for tag in ("r2a","r2b"):
            generation=json.loads((R2/f"generation-{tag}.json").read_text())
            preparation=json.loads((R2/f"preparation-{tag}.json").read_text())
            audit=json.loads((R2/f"audit-{tag}.json").read_text())
            for path,digest in generation["source_hashes"].items():self.assertEqual(sha(ROOT/path),digest)
            self.assertEqual(generation["study"]["sha256"],sha(STUDY/f"study-{tag}.json"))
            self.assertEqual(generation["outputs"]["delivery-fluid-domain.stl"],audit["native_surface_sha256"])
            self.assertEqual(preparation["source_sha256"],sha(STUDY/"source/prepare_duct_cfd_r2.py"))
            self.assertEqual(preparation["decimation"],"none")
            self.assertEqual(preparation["explicit_feature_edges"]["closed_loops"],8)
            self.assertEqual(audit["auditor_sha256"],sha(STUDY/"source/audit_mesh_admission_r2.py"))
            self.assertEqual(audit["criteria"]["pinned_auditor"]["sha256"],sha(STUDY/"source/audit_mesh_admission.py"))
            self.assertEqual(audit["generator"]["sha256"],sha(STUDY/"source-r2/Program.cs"))
            self.assertEqual(audit["analysis_surface"]["sha256"],preparation["files"]["constant/triSurface/duct.stl"])
            self.assertLess(audit["analysis_surface"]["constructive_model_residual_mm"]["max"],json.loads(
                (STUDY/f"study-{tag}.json").read_text())["geometry"]["voxel_mm"])
            verdict=audit["verdict"]
            self.assertEqual(verdict["creases_off_constructive_junctions"]["edges"],0)
            self.assertTrue(any(verdict["hard_re_entrant_length_mm"].values()))
            self.assertFalse(verdict["input_admissible_for_settings_sweep"])
            self.assertFalse(verdict["mesh_admitted"])
            self.assertEqual(runtime["results"][tag]["hard_re_entrant_length_mm"],verdict["hard_re_entrant_length_mm"])

    def test_r2_background_block_is_whole_cells(self):
        prepare=runpy.run_path(str(STUDY/"source/prepare_duct_cfd_r2.py"))
        self.assertEqual(prepare["block_cells"](5.0),[116,106,64])
        with self.assertRaises(ValueError):prepare["block_cells"](3.0)


R2C=STUDY/"results/cfd/r2c-admission-20261118"


class InstalledCoolingR2cTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=runpy.run_path(str(STUDY/"source/audit_mesh_admission_r2c.py"))
        cls.r2=cls.audit["load_r2"]()
        cls.g=json.loads((STUDY/"study-r2c.json").read_text())["geometry"]

    def test_r2c_card_adds_only_the_corner_blend(self):
        base=json.loads((STUDY/"study.json").read_text())
        r2b=json.loads((STUDY/"study-r2b.json").read_text())
        card=json.loads((STUDY/"study-r2c.json").read_text())
        self.assertEqual(card["parent_revision"],base["revision"])
        self.assertEqual(card["geometry"],{**r2b["geometry"],"three_surface_corner_blend_mm":12})
        rest=lambda c:{k:v for k,v in c.items() if k not in ("revision","parent_revision","r2_basis","geometry")}
        self.assertEqual(rest(card),rest(r2b))
        self.assertIn("owner's veto",card["r2_basis"])
        g=card["geometry"]
        self.assertEqual(g["reentrant_blend_mm"],g["alternator_subtraction_blend_mm"])
        self.assertEqual(g["reentrant_blend_mm"],g["three_surface_corner_blend_mm"])
        self.assertEqual(g["alternator_rear_y_mm"],base["geometry"]["alternator_rear_y_mm"])

    def test_one_step_mean_is_the_r2_blend_on_each_two_surface_edge(self):
        mean,smin=self.audit["plane_mean"],self.r2.smin
        rng=np.random.default_rng(1118);u,b,side=rng.uniform(-20,20,(3,5000));c=12.0
        far=np.full_like(u,1e3)
        np.testing.assert_allclose(mean(u,b,far,c),smin(u,b,c),atol=1e-9)              # union seam at the cap
        np.testing.assert_allclose(mean(u,-far,side,c),-self.r2.smax(side,u,c),atol=1e-9) # alternator rim
        t=(np.arange(20000)+.5)/20000*2*c-c                                             # brute-force mean
        brute=self.audit["corner"](u[:200,None]-t[None,:],b[:200,None],side[:200,None]).mean(axis=1)
        np.testing.assert_allclose(mean(u[:200],b[:200],side[:200],c),brute,atol=1e-4)

    def test_r2c_model_changes_only_the_alternator_corner(self):
        p=np.random.default_rng(452).uniform((-290,-210,5),(290,320,325),(20000,3))
        r2b={**self.g};r2b.pop("three_surface_corner_blend_mm")
        without=self.audit["bind_r2c_model"](self.r2,self.r2.load_base(),r2b)
        old=self.r2.bind_r2_model(self.r2.load_base(),r2b)
        f_old=old.fluid_sdf(old.constituents(p,r2b)[0])
        np.testing.assert_array_equal(without.fluid_sdf(without.constituents(p,r2b)[0]),f_old)
        new=self.audit["bind_r2c_model"](self.r2,self.r2.load_base(),self.g)
        f_new=new.fluid_sdf(new.constituents(p,self.g)[0])
        zone=(np.abs(p[:,0])<90)&(p[:,1]>-40)&(p[:,1]<30)&(p[:,2]>190)&(p[:,2]<290)
        np.testing.assert_array_equal(np.sign(f_new[~zone]),np.sign(f_old[~zone]))
        near=~zone&(np.abs(f_old)<3)
        np.testing.assert_allclose(f_new[near],f_old[near],atol=1e-9)
        self.assertLess(self.audit["rims_unchanged"](self.r2,self.g)[0],1e-9)
        with self.assertRaises(ValueError):
            self.audit["bind_r2c_model"](self.r2,self.r2.load_base(),{**self.g,"alternator_subtraction_blend_mm":0})

    def test_r2c_record_binds_its_sources_and_keeps_the_mesh_unadmitted(self):
        runtime=json.loads((R2C/"runtime.json").read_text())
        for name,digest in runtime["files"].items():self.assertEqual(sha(R2C/name),digest)
        for key in ("input_admissible_for_settings_sweep","mesh_admitted","mesh_trial_run","flow_solver_started"):
            self.assertFalse(runtime["verdict"][key])
        for tag in ("r1","r2a","r2b"):
            again=json.loads((R2C/f"generation-{tag}-by-r2c.json").read_text())
            first=json.loads((R2/f"generation-{tag}.json").read_text())
            self.assertEqual(again["outputs"],first["outputs"])
            self.assertEqual(again["study"],first["study"])
            for path,digest in again["source_hashes"].items():self.assertEqual(sha(ROOT/path),digest)
        generation=json.loads((R2C/"generation-r2c.json").read_text())
        preparation=json.loads((R2C/"preparation-r2c.json").read_text())
        audit=json.loads((R2C/"audit-r2c.json").read_text())
        for path,digest in generation["source_hashes"].items():self.assertEqual(sha(ROOT/path),digest)
        self.assertIn("twins/993-installed-cooling-f1/source-r2c/Program.cs",generation["source_hashes"])
        self.assertEqual(generation["generation"]["geometry_revision"],"R2c")
        self.assertEqual(generation["study"]["sha256"],sha(STUDY/"study-r2c.json"))
        self.assertEqual(generation["outputs"]["delivery-fluid-domain.stl"],audit["native_surface_sha256"])
        self.assertEqual(preparation["source_sha256"],sha(STUDY/"source/prepare_duct_cfd_r2.py"))
        self.assertEqual(preparation["explicit_feature_edges"]["constructive_model"]["auditor_sha256"],
                         sha(STUDY/"source/audit_mesh_admission_r2.py"))
        self.assertEqual(preparation["decimation"],"none")
        self.assertEqual(audit["auditor_sha256"],sha(STUDY/"source/audit_mesh_admission_r2c.py"))
        self.assertEqual(audit["criteria"]["pinned_auditor"]["sha256"],sha(STUDY/"source/audit_mesh_admission.py"))
        self.assertEqual(audit["criteria"]["pinned_r2_auditor"]["sha256"],sha(STUDY/"source/audit_mesh_admission_r2.py"))
        self.assertEqual(audit["generator"]["sha256"],sha(STUDY/"source-r2c/Program.cs"))
        self.assertEqual(audit["analysis_surface"]["sha256"],preparation["files"]["constant/triSurface/duct.stl"])
        self.assertLess(audit["analysis_surface"]["constructive_model_residual_mm"]["max"],self.g["voxel_mm"])
        verdict=audit["verdict"]
        self.assertEqual(verdict["creases_off_constructive_junctions"]["edges"],0)
        self.assertTrue(any(verdict["hard_re_entrant_length_mm"].values()))
        self.assertFalse(verdict["input_admissible_for_settings_sweep"])
        self.assertEqual(runtime["results"]["r2c"]["hard_re_entrant_length_mm"],verdict["hard_re_entrant_length_mm"])
        self.assertLess(sum(verdict["hard_re_entrant_length_mm"].values()),
                        sum(runtime["results"]["r2b_for_comparison"]["hard_re_entrant_length_mm"].values()))


if __name__=="__main__":unittest.main()
