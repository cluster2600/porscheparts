"""Synthetic arithmetic and fail-closed guard tests; never invoke native MOOSE."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import assess_affine as check
import run_local as runner

SOURCE=Path(__file__).resolve().parent


class AffineWitness(unittest.TestCase):
    def samples(self):
        return [dict(id=str(i+4*j+16*k),x=str(1+i/3),y=str(1+j/3),z=str(1+k/3),
            w=str((1+i/3)+2*(1+j/3)+3*(1+k/3))) for k in range(4) for j in range(4) for i in range(4)]

    def test_all_spatial_nodes_and_every_Q1_face_flux(self):
        report=check.spatial(self.samples())
        self.assertEqual(report['genuine_interior_nodes'],8);self.assertEqual(report['outer_cell_face_integrals'],54)
        for name,expected in check.SIDES.items():self.assertAlmostEqual(report['reconstructed_Q1_face_fluxes'][name],expected,places=13)
        for changed in ['missing','interior','boundary','duplicate']:
            rows=self.samples()
            if changed=='missing':rows.pop()
            if changed=='interior':rows[21]['w']=str(float(rows[21]['w'])+.01)
            if changed=='boundary':rows[0]['w']=str(float(rows[0]['w'])+.01)
            if changed=='duplicate':rows[-1]=rows[0]
            with self.subTest(changed=changed),self.assertRaises(ValueError):check.spatial(rows)

    def test_true_algebraic_residual_and_actual_row_strategy(self):
        A=[[0.]*64 for _ in range(64)]
        for i in range(56):A[i][i]=1
        for i in range(56,64):
            A[i][i]=2;A[i][0]=-.25
            if i>56:A[i][i-1]=-.5
            if i<63:A[i][i+1]=-.5
        y=[float(i+1) for i in range(64)];b=[sum(v*w for v,w in zip(row,y)) for row in A]
        report=check.algebra(A,A,b,y)
        self.assertEqual(len(report['identity_rows']),56);self.assertGreater(report['full_symmetry_relative_Frobenius'],0)
        self.assertEqual(report['free_symmetry_relative_Frobenius'],0);self.assertFalse(report['row_equals_node_assumed'])
        self.assertFalse(report['native_free_vs_geometric_P1_matrix_equality_established'])
        bad=y.copy();bad[-1]+=.01
        with self.assertRaises(ValueError):check.algebra(A,A,b,bad)
        with self.assertRaises(ValueError):check.algebra(A,A,[0.]*64,y)

    def test_finite_inputs_with_overflowing_derived_arithmetic_are_rejected(self):
        A=[[0.]*64 for _ in range(64)]
        for i in range(64):A[i][i]=1. if i<56 else 1e308
        with self.assertRaisesRegex(ValueError,'Finite nonzero'):
            check.algebra(A,A,[1e308]*64,[1e308]*56+[0.]*8)

    def test_actual_BoomerAMG_profile_requires_one_V_cycle_and_zero_tolerance(self):
        profile='type: gmres\ntype: hypre\nHYPRE BoomerAMG preconditioning\nCycle type V\nMaximum number of iterations PER hypre call 1\nConvergence tolerance PER hypre call 0\n'
        self.assertEqual(check.actual_settings(profile)['maximum_iterations_per_PC_call'],1)
        for text in [profile.replace('call 1','call 2'),profile.replace('Cycle type V','Cycle type W'),
                     profile.replace('call 0','call nan'),'type: gmres\ntype: hypre\nboomeramg',profile+profile]:
            with self.assertRaises(ValueError):check.actual_settings(text)

    def test_missing_changed_or_symlink_export_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            names=['operator.m','preconditioner.m','rhs.m','correction.m','ksp.txt','true_residual.txt','native.log',
                   'affine.csv','affine_nodes_0000.csv','affine.i','frozen-contract.json']
            for name in names:(root/name).write_bytes(b'unit manifest payload')
            receipt=dict(artifact_sha256={name:check.sha(root/name) for name in names})
            self.assertEqual(check.bound_exports(root,receipt),receipt['artifact_sha256'])
            with self.assertRaisesRegex(ValueError,'manifest missing'):check.bound_exports(root,{})
            (root/'operator.m').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'bytes changed'):check.bound_exports(root,receipt)
            (root/'operator.m').write_bytes(b'unit manifest payload');(root/'rhs.m').unlink()
            with self.assertRaisesRegex(ValueError,'inventory'):check.bound_exports(root,receipt)
            (root/'rhs.m').symlink_to(root/'operator.m')
            with self.assertRaisesRegex(ValueError,'symlink'):check.bound_exports(root,receipt)

    def test_torn_nonfinite_or_missing_numeric_matrix_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary)/'operator.m'
            good='A = [\n'+''.join(f'{i} {i} 1\n' for i in range(1,65))+'];\n'
            p.write_text(good);self.assertEqual(len(check.matrices(p)[0]),64)
            for text in [good+'B = [\n1 1 2',good.replace('1 1 1','1 1 NaN',1),'A = [\n1 1 1\n];\n','matrix-free operator']:
                p.write_text(text)
                with self.assertRaises(ValueError):check.matrices(p)

    def test_changed_actual_solver_input_refused_even_with_rehashed_receipt_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'output';output.mkdir();snapshots=output/'source-snapshots';snapshots.mkdir()
            original=(SOURCE/'affine.i').read_bytes();(snapshots/'affine.i').write_bytes(original)
            (output/'affine.i').write_bytes(original+b'\n# changed after solve\n')
            contract=root/'contract.json';contract.write_text(json.dumps(dict(source_sha256s={'affine.i':check.sha(SOURCE/'affine.i')})))
            (output/'frozen-contract.json').write_bytes(contract.read_bytes())
            receipt=dict(returncode=0,process_reaped=True,binary_and_runtime_unchanged=True,inputs_unchanged=True,
                artifact_sha256={'affine.i':check.sha(output/'affine.i')})
            (output/'native-execution.json').write_text(json.dumps(receipt))
            with mock.patch.object(check,'matrices') as parse,self.assertRaisesRegex(ValueError,'Actual solver input changed'):
                check.assess(output,contract,check.sha(contract))
            parse.assert_not_called()

    def test_one_solve_and_reaped_integer_success_required_before_assessment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'output';output.mkdir();snapshots=output/'source-snapshots';snapshots.mkdir()
            original=(SOURCE/'affine.i').read_bytes()
            for path in [snapshots/'affine.i',output/'affine.i']:path.write_bytes(original)
            contract=root/'contract.json';contract.write_text(json.dumps(dict(source_sha256s={'affine.i':check.sha(SOURCE/'affine.i')})))
            (output/'frozen-contract.json').write_bytes(contract.read_bytes())
            receipt=dict(returncode=0,process_reaped=True,binary_and_runtime_unchanged=True,inputs_unchanged=True)
            for changed in [dict(returncode=False),dict(process_reaped=False)]:
                (output/'native-execution.json').write_text(json.dumps(dict(receipt,**changed)))
                with mock.patch.object(check,'matrices') as parse,self.assertRaisesRegex(ValueError,'Completed source-bound'):
                    check.assess(output,contract,check.sha(contract))
                parse.assert_not_called()
            (output/'native-execution.json').write_text(json.dumps(receipt))
            with mock.patch.object(check,'bound_exports',return_value={}),mock.patch.object(check,'matrices',return_value=[[],[]]),mock.patch.object(check,'vectors',return_value=[[],[]]),self.assertRaisesRegex(ValueError,'Exactly one actual KSP solve'):
                check.assess(output,contract,check.sha(contract))

    def test_wrapper_is_read_only_network_isolated_and_bounded(self):
        command=runner.command(Path('/owned/rootfs'),Path('/owned/output'))
        for option in ['MemoryMax=2G','MemorySwapMax=0','CPUQuota=200%','RuntimeMaxSec=45','--unshare-net','--die-with-parent','--clearenv']:
            self.assertIn(option,command)
        i=command.index('--ro-bind');self.assertEqual(command[i+1:i+3],['/owned/rootfs','/'])
        self.assertEqual(command[-1],'. /environment; exec /opt/moose/bin/moose-opt -i affine.i --n-threads=1')

    def test_source_drift_rejected_before_output_or_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);contract=root/'contract.json';output=root/'never-created'
            contract.write_text(json.dumps(dict(source_sha256s={'affine.i':'0'*64})))
            with mock.patch.object(subprocess,'Popen') as launch,self.assertRaisesRegex(ValueError,'source changed'):
                runner.run(root/'unused-runtime',output,contract,check.sha(contract))
            self.assertFalse(output.exists());launch.assert_not_called()

    def test_timeout_kills_reaps_and_retains_failed_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);runtime=root/'runtime';runtime.mkdir();binary=runtime/'binary';binary.write_bytes(b'unit runtime')
            output=root/'new';contract=root/'contract.json'
            contract.write_text(json.dumps(dict(required_rootfs=str(runtime.resolve()),reserved_remote_output=str(output.resolve()),
                runtime_sha256s={'binary':check.sha(binary)},source_sha256s={name:check.sha(SOURCE/name) for name in ['affine.i','run_local.py']})))
            process=mock.Mock(pid=12345,returncode=-9);process.poll.side_effect=[None,-9]
            process.wait.side_effect=[subprocess.TimeoutExpired('mock native',40),None]
            with mock.patch.object(subprocess,'Popen',return_value=process),mock.patch.object(runner.os,'killpg') as kill:
                with self.assertRaises(subprocess.TimeoutExpired):runner.run(runtime,output,contract,check.sha(contract))
            kill.assert_called_once_with(process.pid,runner.signal.SIGKILL);self.assertEqual(process.wait.call_count,2)
            receipt=json.loads((output/'native-execution.json').read_text())
            self.assertTrue(receipt['process_reaped']);self.assertTrue(receipt['inputs_unchanged']);self.assertEqual(receipt['returncode'],-9)


if __name__=='__main__':unittest.main()
