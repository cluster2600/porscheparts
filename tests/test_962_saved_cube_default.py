"""Default optimizer preparation preserves isolation and separates quality outcomes."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

SOURCE=Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source"
sys.path.insert(0,str(SOURCE))
import check_hxt_size_cap_002 as ordinary
spec=importlib.util.spec_from_file_location("saved_default",SOURCE/"check_saved_cube_default.py")
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


class DefaultPreparation(unittest.TestCase):
    def test_isolated_frozen_launcher_one_default_call_and_no_generation(self):
        original={n:getattr(ordinary,n) for n in ["__file__","options","source_files","DEADLINE","RSS_STOP","DISK_STOP"]}
        first,second=fixture.configure(),fixture.configure()
        self.assertIsNot(first,second);self.assertIsNot(first,ordinary)
        self.assertEqual(first.__file__,str(fixture.WRAPPER));self.assertEqual(len(first.source_files()),7)
        self.assertEqual(first.DEADLINE,30);self.assertEqual(first.RSS_STOP,1024**3);self.assertEqual(first.DISK_STOP,16*1024**2)
        self.assertEqual(fixture.OPTIMIZE,dict(method="",force=True))
        self.assertEqual(first.options(fixture.CASE)["Mesh.OptimizeThreshold"],.3)
        self.assertEqual(first.options(fixture.CASE)["Mesh.Renumber"],0)
        calls=[n for n in ast.walk(ast.parse(fixture.WRAPPER.read_text())) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertEqual(sum(n.func.attr=="optimize" for n in calls),1)
        self.assertFalse(any(n.func.attr=="generate" for n in calls))
        for name,value in original.items():self.assertIs(getattr(ordinary,name),value)

    def test_classification_and_periodic_scope_fail_closed_without_native_calls(self):
        np=ordinary.np;queried=[];state={"periodic":False,"bad_boundary":False}
        def periodic(dim,tags):
            self.assertIn(dim,(1,2));queried.append(dim)
            return [tags[0]+1] if state["periodic"] else tags
        def nodes(dim,tag,*unused):
            if state["bad_boundary"]:tags=[] if dim==2 else list(range(1,43))
            else:tags=list(range(1,9)) if dim==2 else list(range(9,43))
            return (np.array(tags),[],[])
        gmsh=SimpleNamespace(model=SimpleNamespace(getEntities=lambda:[(2,1),(3,1)],mesh=SimpleNamespace(
            getPeriodic=periodic,getPeriodicNodes=lambda dim,tag,*unused:(tag,[],[],[]),getNodes=nodes)))
        report=fixture.classification(gmsh,np,np.arange(1,43))
        self.assertEqual(queried,[2]);self.assertEqual(report["node_counts_by_classification_dimension"],{"0":0,"1":0,"2":8,"3":34})
        state["periodic"]=True
        with self.assertRaisesRegex(ValueError,"periodic"):fixture.classification(gmsh,np,np.arange(1,43))
        state.update(periodic=False,bad_boundary=True)
        with self.assertRaisesRegex(ValueError,"boundary"):fixture.classification(gmsh,np,np.arange(1,43))

    def test_real_connectivity_changes_and_quality_success_are_distinct(self):
        np=ordinary.np
        a=np.array([[1,2,3,4],[2,3,4,5]])
        b=np.array([[5,4,3,2],[4,1,3,2]])
        self.assertTrue(np.array_equal(fixture.canonical_cells(np,a),fixture.canonical_cells(np,b)))
        for before,after,moved,topology in [(.15,.15,0,False),(.2,.15,1,True),(.027,.08,1,True),(.027,.15,0,False)]:
            self.assertFalse(fixture.quality_assessment(before,after,moved,topology)["optimizer_quality_success"])
        self.assertTrue(fixture.quality_assessment(.027,.15,0,True)["optimizer_quality_success"])

    def test_changed_threshold_refuses_before_output_or_native_launcher(self):
        base=fixture.configure();contract=fixture.specification(base);contract["options"]=dict(contract["options"],**{"Mesh.OptimizeThreshold":.2})
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/"contract.json";path.write_text(json.dumps(contract));output=root/"never-created"
            with mock.patch.object(base,"launch_case") as launch,mock.patch.object(fixture,"configure",return_value=base):
                with self.assertRaisesRegex(ValueError,"specification changed"):
                    fixture.main(["--contract",str(path),"--contract-sha256",base.mesh.sha(path),"--output",str(output)])
                launch.assert_not_called();self.assertFalse(output.exists())

    def test_controller_rechecks_saved_mesh_after_successful_worker(self):
        base=fixture.configure()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/"contract.json";path.write_text("{}")
            output=root/"fresh-output";runtime={str(Path(sys.executable).resolve()):base.mesh.sha(Path(sys.executable).resolve())}
            case=dict(software_mesh_passed=True,worker_report=dict(mesh_sha256="0"*64))
            with mock.patch.object(fixture,"configure",return_value=base),mock.patch.object(fixture,"OUTPUT",output),\
                 mock.patch.object(fixture,"require_contract",return_value=dict(source_sha256s={})),\
                 mock.patch.object(base,"RUNTIME_FILES",runtime),mock.patch.object(base,"bound_sources",return_value=True),\
                 mock.patch.object(base,"launch_case",return_value=case):
                self.assertEqual(fixture.main(["--contract",str(path),"--contract-sha256",base.mesh.sha(path),"--output",str(output)]),2)
            report=json.loads((output/"receipt.json").read_text())
            self.assertFalse(report["software_mesh_passed"])
            self.assertFalse((output/fixture.CASE/"cube.msh").exists())


if __name__=="__main__":unittest.main()
