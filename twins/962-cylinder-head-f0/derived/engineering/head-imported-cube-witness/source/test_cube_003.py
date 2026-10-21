"""Prepared stdlib arithmetic/refusal/cleanup tests; no actual process or solver."""
import json
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import unittest
from unittest import mock
import assess_cube_002 as check
import run_cube as runner

SOURCE = Path(__file__).resolve().parent


class CubeWitness(unittest.TestCase):
    def samples(self):
        reference=json.loads((SOURCE/'cube-reference.json').read_text())
        rows=[dict(id=str(50+7*i),x=str(p[0]),y=str(p[1]),z=str(p[2]),w=str(.25 if p==[0,0,0] else 0.)) for i,p in enumerate(reference['coordinates_mm'])]
        return reference,list(reversed(rows))

    def test_actual_spatial_and_reference_P1_implementation(self):
        reference,rows=self.samples(); values,field=check.spatial(rows,reference)
        result=check.p1_reference_checks(values,reference)
        self.assertEqual(field['center_w_mm2'],.25)
        self.assertAlmostEqual(result['energy_mm5'],.5,places=14)
        self.assertAlmostEqual(result['integral_w_mm5'],.5,places=14)
        self.assertEqual(result['raw_reference_triangle_fluxes_mm3'],[.5]*12)
        self.assertAlmostEqual(result['boundary_reaction_sum_mm3'],-8,places=13)
        self.assertFalse(result['imported_connectivity_read_back'])
        for variant in ['missing','duplicate','interior','nonfinite']:
            altered=[dict(row) for row in rows]
            if variant=='missing':altered.pop()
            if variant=='duplicate':altered[-1]=dict(altered[0])
            if variant=='interior':altered[0]['w']='.251'
            if variant=='nonfinite':altered[0]['w']='nan'
            with self.subTest(variant=variant),self.assertRaises(ValueError):check.spatial(altered,reference)

    def test_nonspatial_algebraic_row_and_numeric_refusals(self):
        A=[[float(i==j) for j in range(9)] for i in range(9)];free=4
        A[free]=[-1.]*9;A[free][free]=8.;b=[0.]*9;b[free]=-2.;y=[0.]*9;y[free]=-.25
        result=check.algebra(A,A,b,y);self.assertEqual(result['free_row'],4)
        self.assertFalse(result['row_equals_spatial_node_assumed'])
        self.assertEqual(result['post_update_free_w_mm2'],.25)
        with self.assertRaisesRegex(ValueError,'Newton residual/direction'):
            check.algebra(A,A,[-v for v in b],[-v for v in y])
        changed=y.copy();changed[free]+=.01
        with self.assertRaises(ValueError):check.algebra(A,A,b,changed)
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'operator.m';good='A = [\n'+''.join(f'{i} {i} 1\n' for i in range(1,10))+'];\n'
            p.write_text(good);self.assertEqual(len(check.matrix(p)),9)
            for value in [good+'B = [\n1 1 2',good.replace('1 1 1','1 1 NaN',1),good+good]:
                p.write_text(value)
                with self.assertRaises(ValueError):check.matrix(p)

    def setup_case(self,root):
        root=root.resolve()
        sources=root/'sources';sources.mkdir();runtime=root/'runtime';runtime.mkdir();(runtime/'binary').write_bytes(b'fake unexecuted runtime')
        for name in ['run_cube.py','assess_cube.py','imported-cube.i','cube-reference.json']:shutil.copyfile(SOURCE/name,sources/name)
        (sources/'imported-cube.msh').write_bytes(b'fake mesh only for mocked controller guards')
        old=dict(required_rootfs=str(runtime),runtime_sha256s={'binary':runner.sha(runtime/'binary')})
        (sources/'old-runtime-contract.json').write_text(json.dumps(old))
        pins={p.name:runner.sha(p) for p in sources.iterdir()};output=root/'output'
        contract=root/'contract.json';contract.write_text(json.dumps(dict(native_launch_authorized=True,root_and_peer_review_complete=True,
            resources=runner.RESOURCES,source_sha256s=pins,mesh_sha256=pins['imported-cube.msh'],reserved_remote_output=str(output),**old)))
        return sources,runtime,output,contract

    def test_before_output_mesh_drift_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            sources,runtime,output,contract=self.setup_case(Path(folder));(sources/'imported-cube.msh').write_bytes(b'changed')
            with mock.patch.object(runner,'SOURCE',sources),mock.patch.object(runner.subprocess,'Popen') as launch,self.assertRaisesRegex(ValueError,'source/input changed'):
                runner.run(runtime,output,contract,runner.sha(contract))
            self.assertFalse(output.exists());launch.assert_not_called()

    def test_timeout_and_SIGTERM_during_Popen_assignment_kill_and_reap(self):
        for mode in ['timeout','pending_SIGTERM']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                sources,runtime,output,contract=self.setup_case(Path(folder));process=mock.Mock();process.pid=731;process.returncode=None;handlers={};calls=[]
                process.poll.side_effect=lambda:process.returncode
                def wait(timeout=None):
                    calls.append(timeout)
                    if timeout is not None:raise subprocess.TimeoutExpired('mocked',timeout)
                    process.returncode=-9;return -9
                process.wait.side_effect=wait
                def set_handler(sig,handler):handlers[sig]=handler
                def launch(*args,**kwargs):
                    if mode=='pending_SIGTERM':handlers[signal.SIGTERM](signal.SIGTERM,None)
                    return process
                expected=subprocess.TimeoutExpired if mode=='timeout' else InterruptedError
                with mock.patch.object(runner,'SOURCE',sources),mock.patch.object(runner.signal,'signal',side_effect=set_handler),mock.patch.object(runner.subprocess,'Popen',side_effect=launch),mock.patch.object(runner.os,'killpg') as kill,self.assertRaises(expected):
                    runner.run(runtime,output,contract,runner.sha(contract))
                kill.assert_called_once_with(731,signal.SIGKILL);self.assertEqual(calls[-1],None)
                receipt=json.loads((output/'native-execution.json').read_text())
                self.assertTrue(receipt['process_reaped']);self.assertFalse(receipt['native_execution_completed'])
                self.assertFalse(receipt['passed']);self.assertFalse((output/'assessment.json').exists())


if __name__=='__main__':unittest.main()
