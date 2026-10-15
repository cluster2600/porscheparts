import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "models/917-engine-reconstruction/assembly"
sys.path.insert(0,str(HERE))
SPEC = importlib.util.spec_from_file_location("engine_assembly",HERE/"run.py")
ASSEMBLY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ASSEMBLY)
LAYOUT = sys.modules["engine_layout"]
try:
    import numpy as np
    import trimesh
    SCIENCE = True
except ImportError:
    SCIENCE = False


class EngineAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((HERE/"design.json").read_text())
        self.lock=json.loads((HERE/"imports.json").read_text())
        self.f1=json.loads((ROOT/"twins/reference-917-engine/complete-engine-f1.json").read_text())

    def test_new_barrel_is_only_an_explicit_hypothesis_and_covers_symmetric_piston(self):
        recipe,parts,instances,xs=LAYOUT.build(self.config,self.f1)
        self.assertEqual(len(recipe["parts"]),64)
        self.assertEqual(len(parts),67)
        self.assertEqual(len(instances),895)
        self.assertEqual(xs,[-322.5,-204.5,-86.5,86.5,204.5,322.5])
        rows=LAYOUT.HYP.motion_report(self.config["core_assumptions"])["rod_length_sensitivity"]
        actual=next(row for row in rows if row["rod_length_mm"]==132)
        self.assertEqual(actual["minimum_axial_skirt_coverage_residual_mm"],2)
        self.assertFalse(self.config["manufacturing_authorized"])
        self.assertTrue(any("not factory" in row for row in self.config["assumptions"]))

    def test_source_variant_release_and_datum_mismatch_are_rejected(self):
        for field,value in [("classification","factory_replica"),("manufacturing_authorized",True),
                            ("engine_start_authorized",True),("head_deck_mm",209)]:
            config=copy.deepcopy(self.config);config[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):LAYOUT.build(config,self.f1)
        config=copy.deepcopy(self.config);config["core_assumptions"]["dimensions_mm"]["bore"]=90
        with self.assertRaises(ValueError):LAYOUT.build(config,self.f1)

    @unittest.skipUnless(SCIENCE,"NumPy and Trimesh required")
    def test_inherited_head_and_turbo_component_counts_and_rigid_frames(self):
        _,parts,instances,xs=LAYOUT.build(self.config,self.f1)
        ASSEMBLY.add_imports(self.config,self.lock,parts,instances,xs)
        self.assertEqual(len(parts),119);self.assertEqual(len(instances),1129)
        self.assertEqual(parts["individual_head"]["quantity"],12)
        self.assertEqual(sum(parts[f"head_component_{i:02d}"]["quantity"] for i in (1,4,7,10)),48)
        self.assertEqual(sum(p["quantity"] for p in parts.values() if p.get("import_group")=="turbo"),78)
        for item in instances:
            r=np.asarray(item["matrix_mm"])[:3,:3]
            np.testing.assert_allclose(r.T@r,np.eye(3),atol=1e-12)
            self.assertAlmostEqual(np.linalg.det(r),1)
        recipe,_,_,_=LAYOUT.build(self.config,self.f1)
        for bank,suffix in [(-1,"negative"),(1,"positive")]:
            turbo=next(item for item in instances if item["family"]=="turbo_turbine_housing" and item["bank"]==bank)
            for domain,local in [("exhaust",[43,56.25,-99.75,1]),("intake",[49,42.25,0,1])]:
                terminal=(np.asarray(turbo["matrix_mm"])@local)[:3]
                duct=next(item for item in recipe["parts"] if item["id"]==domain+"_"+suffix)
                np.testing.assert_allclose(duct["add"][-1]["b"],terminal,atol=1e-12)
                self.assertFalse(duct["add"][-1]["round"])
        self.assertEqual(len(ASSEMBLY.coverage(parts)),44)
        del parts["turbo_turbine_housing"]
        with self.assertRaises(ValueError):ASSEMBLY.coverage(parts)

    def test_inherited_mesh_hashes_are_bound_to_published_head_delivery(self):
        manifest=json.loads((ROOT/self.lock["head"]["manifest"]).read_text())
        files={row["path"]:row["sha256"] for row in manifest["files"]}
        for row in self.lock["head"]["files"]:
            self.assertEqual(files["cad/"+row["file"]],row["sha256"])
            self.assertEqual(ASSEMBLY.sha256(ROOT/row["source"]),row["sha256"])
        broken=copy.deepcopy(self.lock);broken["head"]["files"][0]["sha256"]="0"*64
        with self.assertRaises(ValueError):ASSEMBLY.validate_imports(broken,Path("missing"))

    def test_committed_execution_is_source_bound_and_cannot_release_the_engine(self):
        receipt=json.loads((HERE/"execution-20261011.json").read_text())
        for path,digest in receipt["source_sha256"].items():
            self.assertEqual(ASSEMBLY.sha256(ROOT/path),digest,path)
        self.assertEqual(receipt["definitions"],119)
        self.assertEqual(receipt["assembly_occurrences"],1129)
        self.assertFalse(receipt["manufacturing_authorized"])
        self.assertFalse(receipt["engine_start_authorized"])
        self.assertFalse(receipt["functional_assembly_accepted"])
        self.assertGreater(receipt["independent_valve_footprint_screen"]["intake_maximum_radial_excess_mm"],6)

    @unittest.skipUnless(SCIENCE,"NumPy and Trimesh required")
    def test_independent_mesh_screen_rejects_open_and_multiple_bodies(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"fixture.stl"
            left=trimesh.creation.box();right=left.copy();right.apply_translation([3,0,0])
            trimesh.util.concatenate([left,right]).export(path)
            _,report=ASSEMBLY.inspect(path)
            self.assertFalse(report["passed"]);self.assertEqual(report["components"],2)
            left.update_faces(np.arange(len(left.faces)-1));left.export(path)
            _,report=ASSEMBLY.inspect(path);self.assertFalse(report["passed"])

    @unittest.skipUnless(SCIENCE,"NumPy and Trimesh required")
    def test_glb_retains_instancing_units_and_faces(self):
        with tempfile.TemporaryDirectory() as temp:
            instances=[{"family":"fixture","matrix_mm":LAYOUT.transform((123,-42,80),(90,0,0)).tolist()},
                       {"family":"fixture","matrix_mm":LAYOUT.transform((-300,0,0)).tolist()}]
            report=ASSEMBLY.export_scene(Path(temp),{"fixture":trimesh.creation.box(extents=[10,20,30])},instances)
            self.assertEqual(report["prototypes"],1);self.assertEqual(report["instances"],2)
            self.assertEqual(report["millimetre_to_metre_scale"],.001)
            self.assertLess(report["max_coordinate_or_transform_error_m"],1e-6)


if __name__=="__main__":unittest.main()
