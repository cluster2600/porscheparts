"""Focused private mesh-only guards; no real meshing or solve."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

import caps_mesh_preflight as m


class MeshPreflight(unittest.TestCase):
    def test_unpinned_coarse_prevents_outputs_and_spawn(self):
        with tempfile.TemporaryDirectory() as d,patch.object(m,'COARSE_SHA',None),patch.object(m.subprocess,'Popen') as spawn:
            output=Path(d)/'never-created'
            with self.assertRaises(ValueError):m.control(output,1.5)
            self.assertFalse(output.exists());spawn.assert_not_called()

    def test_bound_coarse_success_and_rejections(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);proof={'fixture':'not physical evidence'};variant={'step_sha256':'step'}
            row={'direction':'x','numerical_crosscheck_passed':True,'mechanics':{'equilibrium_passed':True,
                'journal_weighted_displacement_mm':{'intake':[.038,0,0],'exhaust':[.03,0,0]}}}
            result=dict(id=m.c.IDENT,step_sha256='step',proof=proof,mesh={'size_mm':2.},complete=True,
                numerically_qualified=True,cases=[row,dict(copy.deepcopy(row),direction='minus_z')],maximum_journal_motion_mm=.038)
            summary=dict(status='completed',returncode=0,error=None,numerically_qualified=True,id=m.c.IDENT,
                mesh_mm=2.,step_sha256='step',proof=proof,result='case.json',maximum_journal_motion_mm=.038)
            def fixture():
                (folder/'case.json').write_text(json.dumps(result))
                summary['retained_artifacts_sha256']={'case.json':m.c.g8.sha256(folder/'case.json')}
                (folder/'summary.json').write_text(json.dumps(summary))
                return m.c.g8.sha256(folder/'summary.json')
            with patch.object(m,'COARSE',folder),patch.object(m.c,'trust',return_value=({},variant,proof)):
                with patch.object(m,'COARSE_SHA',fixture()):self.assertEqual(m.inputs()[2]['coarse_maximum_journal_motion_mm'],.038)
                result['cases'][0]['mechanics']['journal_weighted_displacement_mm']['intake']=[.05,0,0]
                result['maximum_journal_motion_mm']=summary['maximum_journal_motion_mm']=.05
                with patch.object(m,'COARSE_SHA',fixture()):
                    with self.assertRaisesRegex(ValueError,'above 0.040'):m.inputs()
                with patch.object(m,'COARSE_SHA',fixture()):
                    (folder/'case.json').write_text('{}')
                    with self.assertRaisesRegex(ValueError,'artifact changed'):m.inputs()

    def test_worker_only_mesh_and_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'mesh';proof={'fixture':'not physical evidence'}
            baseline={'values':{'rocker_pivot_radius':6.,'carrier_journal_radial_clearance':.29}}
            variant={'step_path':Path(d)/'fake.step','step_sha256':'step','journal_width_mm':11}
            def fake_mesh(step,size,p,variant,directory):
                (directory/'mesh.msh').write_text('test fixture, not a real mesh')
                return {1:(0,0,0),2:(1,0,0)},[],[1],{'intake':{2:1},'exhaust':{2:1}},dict(size_mm=size,nodes=2,elements=0)
            with patch.object(m,'inputs',return_value=(baseline,variant,proof)),patch.object(m.sys,'platform','darwin'),\
                    patch.dict(os.environ,m.c.THREAD_ENV),patch.object(m.c.g11,'mesh',side_effect=fake_mesh) as mesh,\
                    patch.object(m.c.g8,'solve') as solve,patch.object(m.c.g9,'audit') as audit:
                self.assertEqual(m.worker(output,1.5),0)
                report=json.loads((output/'mesh.json').read_text())
                self.assertEqual(report['kinematic_free_dofs'],3);self.assertTrue(report['complete'])
                self.assertFalse(report['FEA_executed']);self.assertFalse(report['mesh_convergence_qualified'])
                self.assertEqual(report['artifacts_sha256']['mesh.msh'],m.c.g8.sha256(output/'mesh.msh'))
                mesh.assert_called_once();solve.assert_not_called();audit.assert_not_called()
                with self.assertRaises(FileExistsError):m.worker(output,1.5)

    def test_combined_memory_guard_kills_only_own_group_and_waits(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'mesh';process=Mock(pid=123456,returncode=-9)
            process.poll.return_value=None
            rows=f'123456 123456 {10*1024**2}\n8345 8345 {20*1024**2}\n'
            with patch.object(m,'inputs',return_value=({}, {}, {})),patch.object(m.subprocess,'Popen',return_value=process),\
                    patch.object(m.subprocess,'check_output',return_value=rows),patch.object(m.os,'killpg') as kill:
                self.assertEqual(m.control(output,1.5),2)
                receipt=json.loads(output.with_name(output.name+'-controller.json').read_text())
                self.assertEqual(receipt['error'],'observed_28GiB_combined_RSS_limit')
                self.assertFalse(receipt['complete']);self.assertTrue(receipt['worker_reaped'])
                kill.assert_called_once_with(123456,m.signal.SIGKILL);process.wait.assert_called_once()


if __name__=='__main__':unittest.main()
