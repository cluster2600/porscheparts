"""Focused failures for a compressible concept comparison, without CFD solves."""
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"twins/bionic-turbo-f1/cfd"
sys.path.insert(0,str(SOURCE))
import prepare_case
import audit_case
import run_case


def surface():
    points=((0,.08,.044),(.01,.08,.044),(0,.07,.044),(0,.08,.034))
    faces=((0,2,1),(0,1,3),(0,3,2),(1,2,3))
    text=[]
    for name,face in zip(prepare_case.PATCHES,faces):
        text += ["solid "+name,"facet normal 0 0 0","outer loop"]
        text += ["vertex "+" ".join(map(str,points[i])) for i in face]
        text += ["endloop","endfacet","endsolid "+name]
    return "\n".join(text)+"\n"


def series():
    data={}
    for p,value in (("inlet",-1),("outlet",1),("rotor",0),("stator",0)):
        data["mass_"+p]=[[i,value] for i in range(201)]
        data["magnitude_"+p]=[[i,abs(value)] for i in range(201)]
    data["energy_inlet"]=[[i,-300000] for i in range(201)]
    data["energy_outlet"]=[[i,300100] for i in range(201)]
    data["torque"]=[[i,-10] for i in range(201)]
    data["minima"]=[[i,101325,298.15] for i in range(201)]
    return data


class BionicTurboCfdTests(unittest.TestCase):
    def test_medium_gap_refinement_is_local_bounded_and_same_surface(self):
        files=prepare_case.case_files({"bounds_m":[[-.06,-.06,-.015],[.064,.08,.044]]},"medium",100000,1,1.2,200)
        text=files["system/snappyHexMeshDict"]
        gap=re.search(r"gapLevel\s*\((\d+) (\d+) (\d+)\);",text)
        self.assertIsNotNone(gap)
        target,minimum,maximum=map(int,gap.groups())
        self.assertEqual((target,minimum,maximum),(4,1,3))
        self.assertGreaterEqual(.0005/(prepare_case.LEVELS["medium"]/2**maximum),3)
        self.assertIn("gapMode mixed; gapSelf true;",text)
        self.assertIn("levels ((1e15 1))",text)
        self.assertIn("maxGlobalCells 6000000",text)
        self.assertIn("strictRegionSnap true",text)
        self.assertIn("minTetQuality 1e-12",text)

    def test_preparation_retains_surface_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            mesh=root/"surface.stl"
            mesh.write_text(surface())
            manifest=prepare_case.prepare(mesh,root/"case","coarse",100000,1,1.2,200)
            self.assertEqual(manifest["surface"]["region_triangles"],dict.fromkeys(prepare_case.PATCHES,1))
            self.assertEqual(manifest["surface"]["boundary_topology"]["surface_components"],1)
            self.assertEqual((root/"case/constant/triSurface/domain.stl").read_bytes(),mesh.read_bytes())
            self.assertFalse(manifest["performance_ranking_authorized"])
            self.assertIn("div(phiMRF,p)",(root/"case/system/fvSchemes").read_text())
            self.assertIn("fields (h UMagSqr)",(root/"case/system/controlDict").read_text())
            with self.assertRaises(FileExistsError):
                prepare_case.prepare(mesh,root/"case","coarse",100000,1,1.2,200)

    def test_surface_rejects_wrong_regions_and_unclosed_or_degenerate_faces(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"surface.stl"
            for malformed in (surface().replace("solid rotor","solid rotorWrong"),
                              surface().replace("vertex 0.01 0.08 0.044","vertex 0.011 0.08 0.044",1),
                              surface().replace("vertex 0.01 0.08 0.044","vertex 0 0.08 0.044")):
                path.write_text(malformed)
                with self.assertRaises(ValueError):
                    prepare_case.surface_info(path)

    def test_input_tamper_rejected_before_runtime_and_criteria_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            mesh=root/"surface.stl"
            mesh.write_text(surface())
            case=root/"case"
            manifest=prepare_case.prepare(mesh,case,"coarse",100000,1,1.2,200)
            (case/"0/p").write_text((case/"0/p").read_text()+"// changed\n")
            with self.assertRaisesRegex(ValueError,"Prepared input changed"):
                run_case.run(case,"config",10,1,1)
            manifest["criteria"]=dict(manifest["criteria"],relative_energy_imbalance_max=1e6)
            (case/"case-manifest.json").write_text(json.dumps(manifest))
            (case/"run-mesh.json").write_text("{}")
            (case/"run-solve.json").write_text("{}")
            with self.assertRaisesRegex(ValueError,"acceptance criteria"):
                audit_case.audit(case)

    def test_balanced_synthetic_history_passes_only_numerical_history(self):
        result=audit_case.evaluate(series(),200,10,prepare_case.CRITERIA)
        self.assertTrue(result["numerical_history_gate_passed"])
        self.assertEqual(result["metrics"]["shaft_input_power_w"]["mean"],100)

    def test_missing_shaft_work_is_rejected(self):
        data=series()
        data["energy_outlet"]=[[i,300000] for i in range(201)]
        result=audit_case.evaluate(data,200,10,prepare_case.CRITERIA)
        self.assertFalse(result["numerical_history_gate_passed"])
        self.assertFalse(result["checks"]["shaft_work_energy_balance"])

    def test_cancelling_wall_leak_is_rejected(self):
        data=series()
        data["magnitude_stator"]=[[i,.02] for i in range(201)]
        result=audit_case.evaluate(data,200,10,prepare_case.CRITERIA)
        self.assertFalse(result["checks"]["impermeable_walls"])

    def test_wrong_torque_sign_is_not_hidden_by_absolute_value(self):
        data=series()
        data["torque"]=[[i,10] for i in range(201)]
        result=audit_case.evaluate(data,200,10,prepare_case.CRITERIA)
        self.assertFalse(result["checks"]["positive_shaft_power_and_enthalpy_rise"])

    def test_missing_sample_and_nonphysical_gross_flux_rejected(self):
        data=series()
        data["mass_inlet"].pop(100)
        with self.assertRaises(ValueError):
            audit_case.evaluate(data,200,10,prepare_case.CRITERIA)
        data=series()
        data["magnitude_outlet"][-1][1]=.5
        with self.assertRaises(ValueError):
            audit_case.evaluate(data,200,10,prepare_case.CRITERIA)

    def test_residual_gate_needs_all_equations_and_complete_window(self):
        logs="\n".join("Time = "+str(i)+"\n"+"\n".join(f"smoothSolver: Solving for {f}, Initial residual = 1e-6, Final residual = 1e-10, No Iterations 2" for f in ("p","Ux","Uy","Uz","h","k","omega")) for i in range(1,201))
        self.assertTrue(audit_case.residual_check(logs,200,100,1e-4)["passed"])
        self.assertFalse(audit_case.residual_check(logs.replace("Solving for h,","Solving for other,"),200,100,1e-4)["passed"])

    def test_mrf_rotor_coverage_and_port_exclusion(self):
        with tempfile.TemporaryDirectory() as temp:
            case=Path(temp)
            mesh=case/"constant/polyMesh"
            mesh.mkdir(parents=True)
            (mesh/"boundary").write_text("\n".join(f"{p} {{type {'patch' if p in ('inlet','outlet') else 'wall'}; nFaces 1; startFace {i};}}" for i,p in enumerate(prepare_case.PATCHES)))
            (mesh/"owner").write_text("FoamFile {format ascii;}\n4\n(0 1 2 3)\n")
            (mesh/"faces").write_text("FoamFile {format ascii; class faceList;}\n4\n(3(0 2 1) 3(0 1 3) 3(0 3 2) 3(1 2 3))\n")
            topology={"surface_components":1,"component_patch_sets":[sorted(prepare_case.PATCHES)],"euler_characteristic":2,
                      "component_invariants":[{"patches":sorted(prepare_case.PATCHES),"euler_characteristic":2}]}
            zones=mesh/"cellZones"
            zones.write_text("rotorZone {type cellZone; cellLabels List<label> 1(2);}")
            self.assertTrue(run_case.inspect_mesh(case,topology)["rotor_owner_cells_all_in_zone"])
            with self.assertRaisesRegex(ValueError,"shell count"):
                run_case.inspect_mesh(case,dict(topology,surface_components=2))
            with self.assertRaisesRegex(ValueError,"patch provenance"):
                run_case.inspect_mesh(case,dict(topology,component_patch_sets=[["rotor"]]))
            torus=[]
            for y in range(3):
                for x in range(3):
                    a=y*3+x; b=y*3+(x+1)%3; c=((y+1)%3)*3+(x+1)%3; d=((y+1)%3)*3+x
                    torus.extend(((a,b,c),(a,c,d)))
            torus_topology=prepare_case.closed_boundary_topology((face,prepare_case.PATCHES[i%4]) for i,face in enumerate(torus))
            self.assertEqual(torus_topology["surface_components"],topology["surface_components"])
            self.assertEqual(torus_topology["component_patch_sets"],topology["component_patch_sets"])
            self.assertEqual(torus_topology["euler_characteristic"],0)
            with self.assertRaisesRegex(ValueError,"Euler"):
                run_case.inspect_mesh(case,torus_topology)
            zones.write_text("rotorZone {type cellZone; cellLabels List<label> 1(1);}")
            with self.assertRaises(ValueError):
                run_case.inspect_mesh(case,topology)

    def test_boundary_shells_count_by_edges_not_shared_points(self):
        tetra=((0,2,1),(0,1,3),(0,3,2),(1,2,3))
        second=((0,5,4),(0,4,6),(0,6,5),(4,5,6))
        result=prepare_case.closed_boundary_topology([(f,"stator") for f in tetra]+[(f,"rotor") for f in second])
        self.assertEqual(result["surface_components"],2)
        self.assertEqual(result["component_patch_sets"],[["rotor"],["stator"]])
        with self.assertRaisesRegex(ValueError,"two faces per edge"):
            prepare_case.closed_boundary_topology([(f,"rotor") for f in tetra[:-1]])

    def test_face_list_rejects_comments_bad_counts_and_residual_text(self):
        header="FoamFile {format ascii; class faceList;}\n"
        valid="1(3(0 1 2))"
        self.assertEqual(list(run_case.ascii_faces(header+valid)),[(0,1,2)])
        self.assertEqual(list(run_case.ascii_faces(header+"/*1(3(0 1 2))*/ 0()")),[])
        for body in ("999(3(0 1 2))","1(/*3(0 1 2)*/)","1(3(0 1 2) extra)",valid+" extra"):
            with self.assertRaises(ValueError):
                list(run_case.ascii_faces(header+body))

    def test_cli_imports_do_not_shadow_standard_library(self):
        for script in ("prepare_case.py","run_case.py","audit_case.py"):
            result=subprocess.run([sys.executable,"-B",str(SOURCE/script),"--help"],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
