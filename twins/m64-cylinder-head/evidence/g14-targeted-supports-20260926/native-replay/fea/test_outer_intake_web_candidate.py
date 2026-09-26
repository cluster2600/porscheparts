"""Private intake-web input and resource guards; no mesh or solver execution."""
import copy
import inspect
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import outer_intake_web_candidate as c


class OuterIntakeWebTrust(unittest.TestCase):
    def test_actual_chain_interfaces_and_nonaggravation_not_service_release(self):
        _, row, proof = c.inputs(c.IDENT)
        self.assertEqual((row['journal_width_mm'],row['journal_diameter_mm']),(8,12.58))
        self.assertTrue(proof['outer_mirror']['accepted'])
        self.assertFalse(proof['outer_mirror']['negative_FE_executed'])
        self.assertTrue(proof['combined_geometry']['pairwise_no_intersection'])
        self.assertTrue(proof['service_nonaggravation_only'])
        self.assertFalse(proof['service_removal_qualified'])
        self.assertFalse(proof['mounting_and_maintenance_qualified'])
        self.assertTrue(row['support_bounds_unchanged'])
        self.assertEqual(proof['prior_cad']['cad_receipt_sha256'],c.inner_entry.CAD_SHA)
        self.assertTrue(proof['plug_removal_nonaggravation_only'])
        self.assertFalse(proof['plug_removal_qualified'])
        self.assertEqual(proof['plug_removal_checks']['1']['new_material_overlap_mm3'],0.)
        self.assertAlmostEqual(proof['plug_removal_checks']['1']['baseline_overlap_mm3'],1756.1586918195221)
        self.assertEqual(proof['plug_removal_checks'],row['plug_removal_checks'])
        self.assertGreater(proof['new_material_service_checks']['intake_shaft_vertical_lift']['baseline_overlap_mm3'],700)
        self.assertGreater(proof['functional_tool_checks']['mount_tool_access_-1']['baseline_overlap_mm3'],500)

    def test_modified_receipt_or_coexistence_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory)/'changed.json'
            changed.write_text(c.CAD.read_text()+' ')
            with self.assertRaises(ValueError): c.inputs(c.IDENT,changed)
            changed.write_text(c.COMBINED.read_text()+' ')
            with self.assertRaises(ValueError): c.combined_gate(json.loads(c.CAD.read_text()),changed)

    def test_service_gates_fail_closed(self):
        actual = json.loads(c.CAD.read_text())['variants'][0]
        for mode in ('empty_cam','missing_service','nan','overlap','fake_release'):
            row = copy.deepcopy(actual)
            if mode == 'empty_cam': row['cam_bore_and_split_difference'] = {}
            if mode == 'missing_service': row['new_material_service_checks'].pop('intake_shaft_vertical_lift')
            if mode in ('nan','overlap'):
                row['new_material_service_checks']['intake_shaft_vertical_lift']['new_material_overlap_mm3'] = float('nan') if mode=='nan' else .001
            if mode == 'fake_release': row['service_removal_qualified'] = True
            with self.subTest(mode=mode), self.assertRaises(ValueError): c.service_gate(row)

    def test_plug_gate_preserves_obstructed_baseline_and_rejects_bad_reservations(self):
        actual = json.loads(c.CAD.read_text())['variants'][0]
        c.plug_gate(actual)
        mutations = (
            ('missing_check',lambda r:r['plug_removal_checks'].pop('2')),
            ('missing_definition',lambda r:r['plug_removal_definitions'].pop('2')),
            ('new_overlap',lambda r:r['plug_removal_checks']['1'].update(new_material_overlap_mm3=.001)),
            ('negative_new',lambda r:r['plug_removal_checks']['1'].update(new_material_overlap_mm3=-1)),
            ('nan_new',lambda r:r['plug_removal_checks']['1'].update(new_material_overlap_mm3=float('nan'))),
            ('negative_baseline',lambda r:r['plug_removal_checks']['1'].update(baseline_overlap_mm3=-1)),
            ('infinite_baseline',lambda r:r['plug_removal_checks']['1'].update(baseline_overlap_mm3=float('inf'))),
            ('wrong_radius',lambda r:r['plug_removal_definitions']['1'].update(radius_mm=10.)),
            ('short_vector',lambda r:r['plug_removal_definitions']['1'].update(start_mm=[0,1])),
            ('infinite_vector',lambda r:r['plug_removal_definitions']['1'].update(end_mm=[0,1,float('inf')])),
            ('bool_vector',lambda r:r['plug_removal_definitions']['1'].update(start_mm=[0,1,True])),
        )
        for mode,mutate in mutations:
            row = copy.deepcopy(actual); mutate(row)
            with self.subTest(mode=mode), self.assertRaises(ValueError): c.plug_gate(row)

    def test_explicit_no_peer_never_counts_process_group_zero(self):
        self.assertEqual(c.PEER_PGID,0)
        with patch.object(c.subprocess,'run',return_value=SimpleNamespace(stdout='0 999999\n987654 123\n')), patch.object(c.shutil,'disk_usage',return_value=SimpleNamespace(free=20*c.GIB)):
            sample = c.resources(987654,c.HERE)
        self.assertEqual(sample['own_RSS_bytes'],123*1024)
        self.assertEqual(sample['peer_RSS_bytes'],0)
        self.assertEqual(sample['combined_RSS_bytes'],123*1024)
        self.assertTrue(sample['own_group_observed'])

    def test_missing_reference_prevents_output_or_process(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(reference=Path(directory)/'missing.json',output=Path(directory)/'never-created')
            with patch.object(c.subprocess,'Popen') as spawn:
                with self.assertRaises(FileNotFoundError): c.run(args)
                spawn.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_only_positive_candidate_and_unchanged_numerical_worker(self):
        with self.assertRaises(ValueError): c.inputs(c.ALL_IDS[1])
        self.assertEqual(inspect.getsource(c.worker),inspect.getsource(c.prior.worker))
        self.assertEqual(inspect.getsource(c.worker),inspect.getsource(c.inner_entry.worker))
        self.assertIs(c.audit,c.prior.audit)
        self.assertEqual(inspect.getsource(c.audit),inspect.getsource(c.inner_entry.audit))
        self.assertEqual(c.THREAD_ENV,c.prior.THREAD_ENV)
        self.assertEqual(c.IDS,(c.IDENT,))

    def test_unconfigured_peer_prevents_output_or_process(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(reference=Path(directory)/'reference.json',output=Path(directory)/'never-created')
            with patch.object(c,'PEER_PGID',None), patch.object(c.native,'native_gate',return_value={}), patch.object(c.subprocess,'Popen') as spawn:
                with self.assertRaisesRegex(ValueError,'unconfigured peer'): c.run(args)
                spawn.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_resource_limits_and_cleanup_only_outer_group(self):
        ordinary = dict(own_RSS_bytes=1*c.GIB,peer_RSS_bytes=14*c.GIB,
                        combined_RSS_bytes=15*c.GIB,free_bytes=20*c.GIB,own_group_observed=True)
        for change,reason in (({'own_RSS_bytes':13*c.GIB},'outer process group RSS'),
                              ({'combined_RSS_bytes':33*c.GIB},'outer plus approved peer RSS'),
                              ({'free_bytes':11*c.GIB},'free disk space')):
            sample = dict(ordinary,**change)
            process = Mock(pid=987654,returncode=None)
            process.poll.return_value = None
            process.wait.side_effect = lambda: setattr(process,'returncode',-9)
            with self.subTest(reason=reason), patch.object(c,'resources',return_value=sample), patch.object(c.os,'killpg') as kill:
                code,status,error,stats = c.monitor(process,c.HERE,c.time.monotonic()+30)
                self.assertEqual((code,status),(-9,'resource_limit'))
                self.assertIn(reason,error)
                self.assertEqual(stats['samples'],1)
                kill.assert_called_once_with(process.pid,c.signal.SIGKILL)
                self.assertNotEqual(process.pid,c.PEER_PGID)
                process.wait.assert_called_once_with()

    def test_unavailable_monitor_or_timeout_still_reaps_outer(self):
        ordinary = dict(own_RSS_bytes=c.GIB,peer_RSS_bytes=0,combined_RSS_bytes=c.GIB,
                        free_bytes=20*c.GIB,own_group_observed=True)
        for mode in ('ps_failed','missing_group','timeout'):
            process = Mock(pid=987654,returncode=None); process.poll.return_value = None
            process.wait.side_effect = lambda: setattr(process,'returncode',-9)
            sample = dict(ordinary,own_group_observed=mode!='missing_group')
            with self.subTest(mode=mode), patch.object(c,'resources',return_value=sample,
                    side_effect=ValueError('RSS unavailable') if mode=='ps_failed' else None), patch.object(c.os,'killpg') as kill:
                _,status,error,_ = c.monitor(process,c.HERE,c.time.monotonic()-1 if mode=='timeout' else c.time.monotonic()+30)
                self.assertEqual(status,'timeout' if mode=='timeout' else 'failed')
                self.assertTrue(error)
                kill.assert_called_once_with(process.pid,c.signal.SIGKILL)
                process.wait.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
