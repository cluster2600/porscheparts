"""Post-export preparation keeps frozen controls and orders cache repair safely."""
import argparse
import ast
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock

SOURCE=Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source"
sys.path.insert(0,str(SOURCE))
import mesh_quality_head as ordinary
spec=importlib.util.spec_from_file_location("head_postexport",SOURCE/"mesh_quality_head_postexport.py")
post=importlib.util.module_from_spec(spec);spec.loader.exec_module(post)


class PostexportPreparation(unittest.TestCase):
    def configured(self):
        with mock.patch.object(post,"require_inputs"):
            return post.configure_core()

    def test_isolated_controller_and_worker_route_preserve_frozen_helpers(self):
        original={n:getattr(ordinary,n) for n in ["__file__","OPTIONS","OUTPUT","save","worker","source_files","require_admission"]}
        first,second=self.configured(),self.configured()
        self.assertIsNot(first,ordinary);self.assertIsNot(first,second)
        self.assertEqual(first.__file__,str(post.WRAPPER_PATH));self.assertEqual(len(first.source_files()),6)
        self.assertEqual(first.source_files()[1],post.CORE_PATH)
        self.assertEqual(first.OPTIONS,post.OPTIONS);self.assertEqual(first.OPTIONS["Mesh.OptimizeThreshold"],.3)
        self.assertEqual(first.DEADLINE,300);self.assertEqual(first.RSS_STOP,8*1024**3)
        self.assertEqual(first.run.__code__.co_filename,str(post.CORE_PATH))
        self.assertEqual(first.claim_worker.__code__.co_filename,str(post.CORE_PATH))
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);admission=root/"admission.json";admission.write_text("mock")
            output=root/"new";first.OUTPUT=output;first.require_admission=mock.Mock()
            process=mock.Mock(pid=12345,returncode=2);process.poll.return_value=2
            args=["--admission",str(admission),"--admission-sha256",ordinary.sha(admission),"--output",str(output)]
            with mock.patch.object(post,"require_inputs"),mock.patch.object(post,"configure_core",return_value=first),\
                 mock.patch.object(post,"PYTHON_SHA256",ordinary.sha(Path(sys.executable).resolve())),\
                 mock.patch.object(subprocess,"Popen",return_value=process) as launch,\
                 mock.patch.object(threading,"Timer"),mock.patch("sys.stdout",new_callable=io.StringIO):
                self.assertEqual(post.main(args),2);launch.assert_called_once()
            receipt=json.loads((output/"receipt.json").read_text())
            self.assertEqual(receipt["command"][1],str(post.WRAPPER_PATH));self.assertIn("--worker",receipt["command"])
            self.assertEqual(len(receipt["source_sha256s"]),6)
            for p in first.source_files():self.assertEqual(ordinary.sha(output/"source-snapshots"/p.name),ordinary.sha(p))
            with mock.patch.object(post,"require_inputs"),mock.patch.object(post,"configure_core",return_value=second),\
                 mock.patch.object(post,"PYTHON_SHA256",ordinary.sha(Path(sys.executable).resolve())),\
                 mock.patch.object(post,"worker",return_value=2) as worker,mock.patch.object(subprocess,"Popen") as launch:
                self.assertEqual(post.main([*args,"--worker"]),2)
                self.assertIs(worker.call_args.args[0],second);self.assertTrue(worker.call_args.args[1].worker)
                launch.assert_not_called()
        for name,value in original.items():self.assertIs(getattr(ordinary,name),value)
        tree=ast.parse(post.WRAPPER_PATH.read_text())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertEqual(sum(n.func.attr=="optimize" for n in calls),1)
        self.assertFalse(any(n.func.attr=="generate" for n in calls))
        optimizer=next(n for n in calls if n.func.attr=="optimize")
        self.assertEqual({k.arg:ast.literal_eval(k.value) for k in optimizer.keywords},{"method":"","force":True})

    def test_optimizer_then_forced_cache_refresh_before_actual_quality_queries(self):
        np=ordinary.np;events=[];refreshed=False
        def optimize(**kwargs):events.append(("optimize",kwargs))
        def cache(flag):
            nonlocal refreshed
            self.assertIs(flag,False);events.append(("cache",flag));refreshed=True
        def qualities(tags,measure):
            self.assertTrue(refreshed);events.append(("quality",measure))
            return np.array([1/6 if measure=="volume" else .2])
        gmsh=SimpleNamespace(model=SimpleNamespace(mesh=SimpleNamespace(
            optimize=optimize,rebuildElementCache=cache,getElementQualities=qualities)))
        points=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        faces=np.array([[0,2,1],[0,1,3],[1,2,3],[2,0,3]])
        core=SimpleNamespace(np=np,tagged_volume=lambda g:(points,np.array([[0,1,2,3]]),np.arange(1,5),np.array([5]),np.array([[1,2,3,4]])),
            surface_roundtrip=mock.Mock(return_value={}),distribution=ordinary.distribution,
            tetra_volumes=ordinary.tetra_volumes,CANDIDATE_VOLUME=1/6,tetra_boundary=ordinary.tetra_boundary,
            internal_face_orientation=ordinary.internal_face_orientation,array_sha=ordinary.array_sha)
        report=dict(optimizer_call_count=0,element_cache_refresh_count=0)
        post.optimize_and_refresh(gmsh,report,lambda:None)
        with mock.patch.object(post,"classifications",return_value={}):
            _,after=post.audit_after(core,gmsh,points,faces)
        self.assertEqual(events[:2],[("optimize",dict(method="",force=True)),("cache",False)])
        self.assertEqual([v for k,v in events if k=="quality"],["minDetJac","volume","minSICN"])
        self.assertEqual(report["optimizer_call_count"],1);self.assertEqual(report["element_cache_refresh_count"],1)
        self.assertTrue(report["element_cache_refresh_completed"])
        self.assertTrue(after["actual_tetra_boundary"]["exact_oriented_tetra_boundary"])

    def test_cache_failure_preserves_return_stage_and_never_queries_quality(self):
        mesh=SimpleNamespace(optimize=mock.Mock(),rebuildElementCache=mock.Mock(side_effect=RuntimeError("cache failure")),getElementQualities=mock.Mock())
        report=dict(element_cache_refresh_completed=False,element_cache_refresh_count=0)
        with self.assertRaisesRegex(RuntimeError,"cache failure"):
            post.optimize_and_refresh(SimpleNamespace(model=SimpleNamespace(mesh=mesh)),report,lambda:None)
        mesh.optimize.assert_called_once_with(method="",force=True);mesh.rebuildElementCache.assert_called_once_with(False)
        mesh.getElementQualities.assert_not_called();self.assertTrue(report["optimizer_returned"])
        self.assertEqual(report["stage"],"refreshing_element_lookup_cache");self.assertFalse(report["element_cache_refresh_completed"])

    def test_input_drift_blocks_both_entrypoints_before_output_or_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);evidence=root/"proof";evidence.write_bytes(b"bound evidence")
            pins={"proof":ordinary.sha(evidence)};output=root/"never-created"
            with mock.patch.object(post,"ROOT",root),mock.patch.object(post,"INPUT_HASHES",pins),\
                 mock.patch.object(post,"configure_core") as configure,mock.patch.object(subprocess,"Popen") as launch:
                post.require_inputs();evidence.write_bytes(b"changed evidence")
                for suffix in [[],["--worker"]]:
                    with self.subTest(worker=bool(suffix)),self.assertRaisesRegex(ValueError,"evidence changed"):
                        post.main(["--admission",str(root/"unused"),"--admission-sha256","a"*64,"--output",str(output),*suffix])
                configure.assert_not_called();launch.assert_not_called();self.assertFalse(output.exists())

    def test_missing_output_or_digest_still_rejected_by_reused_controller(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);admission=root/"admission";admission.write_text("mock")
            for missing in ["mesh","digest"]:
                core=self.configured();output=root/missing;core.OUTPUT=output;core.require_admission=mock.Mock()
                process=mock.Mock(pid=12345,returncode=0);process.poll.return_value=0
                def completed(*args,**kwargs):
                    report=dict(status="completed_geometric_volume_quality_only",qualification=dict(geometric_volume_gate_passed=True))
                    if missing=="mesh":report["mesh_sha256"]="a"*64
                    else:(output/"head-volume.msh").write_bytes(b"nonempty mock")
                    (output/"worker-report.json").write_text(json.dumps(report));return process
                with self.subTest(missing=missing),mock.patch.object(subprocess,"Popen",side_effect=completed),\
                     mock.patch.object(threading,"Timer"),mock.patch("sys.stdout",new_callable=io.StringIO):
                    self.assertEqual(core.run(argparse.Namespace(output=output,admission=admission,admission_sha256=ordinary.sha(admission))),2)
                self.assertFalse(json.loads((output/"receipt.json").read_text())["geometric_volume_gate_passed"])

    def test_inherited_watchdog_setup_failure_kills_and_reaps(self):
        core=self.configured()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);admission=root/"admission";admission.write_text("mock")
            core.OUTPUT=root/"new";core.require_admission=mock.Mock()
            process=mock.Mock(pid=12345,returncode=None);process.poll.return_value=None
            timer=mock.Mock();timer.start.side_effect=RuntimeError("watchdog startup failed")
            with mock.patch.object(subprocess,"Popen",return_value=process),mock.patch.object(threading,"Timer",return_value=timer),\
                 mock.patch.object(core.os,"killpg") as kill:
                with self.assertRaisesRegex(RuntimeError,"watchdog startup failed"):
                    core.run(argparse.Namespace(output=core.OUTPUT,admission=admission,admission_sha256=ordinary.sha(admission)))
            kill.assert_called_once_with(process.pid,core.signal.SIGKILL);process.wait.assert_called_once_with();timer.cancel.assert_called_once_with()

    def test_retained_before_proof_requires_all_four_loaded_arrays_and_repeats_no_face_audit(self):
        np=ordinary.np;state=(np.array([[0.,0.,0.]]),np.array([1]),np.array([2]),np.array([[1,1,1,1]]))
        core=SimpleNamespace(tagged_volume=lambda g:(state[0],None,*state[1:]),array_sha=ordinary.array_sha,
                             surface_roundtrip=mock.Mock(return_value={}),tetra_boundary=mock.Mock(),internal_face_orientation=mock.Mock())
        row={**post.array_identity(core,state),"direct_native_quality_extrema":{},**{k:{} for k in ["quality","tetrahedra","total_mesh_nodes","tetra_referenced_nodes",
            "tetra_referenced_interior_nodes","unreferenced_mesh_nodes","summed_tetra_volume_mm3","volume_relative_error",
            "actual_tetra_boundary","internal_tetra_face_orientation"]}}
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/"retained.json";path.write_text(json.dumps(row))
            with mock.patch.object(post,"ROOT",root),mock.patch.object(post,"INPUT_WORKER",path.name),mock.patch.object(post,"INPUT_READBACK",path.name),\
                 mock.patch.object(post,"INPUT_HASHES",{path.name:ordinary.sha(path)}),mock.patch.object(post,"classifications",return_value={}):
                _,report=post.load_before(core,None,np.zeros((1,3)),np.zeros((0,3),dtype=int))
                self.assertFalse(report["fresh_tetra_face_incidence_audit"]);core.tetra_boundary.assert_not_called();core.internal_face_orientation.assert_not_called()
                row["sorted_coordinates_sha256"]="a"*64;path.write_text(json.dumps(row))
                with self.assertRaisesRegex(ValueError,"tagged arrays differ"):post.load_before(core,None,np.zeros((1,3)),np.zeros((0,3),dtype=int))


if __name__=="__main__":unittest.main()
