"""Bounded G13 selection, qualified runtime, checkpoints and no engine release."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/fourvalve'))
try:
    import g13_campaign as g13
except ImportError:
    g13 = None


def result(motion=.03, qualified=True):
    return dict(complete=True, cases=[dict(direction=name, numerical_crosscheck_passed=qualified,
        mechanics=dict(equilibrium_passed=qualified, von_Mises_p95_MPa=10.,
                       journal_weighted_displacement_mm={s: [motion, 0., 0.] for s in g13.g11.SIDES}))
        for name in ('x', 'minus_z')])


@unittest.skipIf(g13 is None, 'optional numerical runtime unavailable')
class G13CampaignChecks(unittest.TestCase):
    def test_mirror_binds_original_step_sidecar_and_all_nonempty_finite_masks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            zero = {'added_volume_mm3': 0., 'removed_volume_mm3': 0.}
            files = {}
            for side in ('p', 'm'):
                path = root/(side+'.step'); path.write_text('fixture '+side)
                files[side] = dict(step=path.name, step_sha256=g13.g8.sha256(path), BRep_valid=True, solid_count=1)
            proof = dict(id=g13.OUTER, symmetry_accepted=True,
                transformation_matrix=[[1, 0, 0], [0, -1, 0], [0, 0, 1]],
                vector_cases={'+x': [1, 0, 0], '-z': [0, 0, -1]}, source_prior_step_sha256='original',
                motion_samples_checked=144, negative_static_interferences=[], sampled_motion_interferences=[],
                native_difference_mm3=zero, files=files,
                foot_mask_comparison_mm3={n: zero for n in ('mirrored_fixed_land', 'positive_land_vs_G7', 'negative_land_vs_G7')},
                journal_mask_comparison_mm3={s: zero for s in ('intake', 'exhaust')})
            equivalence = dict(files={name: {'sha256': digest} for name, digest in (
                ('g11_original', 'original'), ('g13_rebuilt', files['p']['step_sha256']), ('g13_mirror', files['m']['step_sha256']))},
                rebuilt_vs_original_mm3={'added': 0., 'removed': 0.},
                negative_vs_original_mirrored_mm3={'added': 0., 'removed': 0.})
            sidecar = root/'outer-original-step-equivalence.json'; g13.g11.publish(sidecar, equivalence)
            outer = {'step_sha256': 'original'}
            result = g13.mirror_gate({'outer_mirror_audit': proof}, root, outer)
            self.assertEqual(result['original_step_equivalence_sha256'], g13.g8.sha256(sidecar))
            for field in ('foot_mask_comparison_mm3', 'journal_mask_comparison_mm3'):
                bad = copy.deepcopy(proof); bad[field] = {}
                with self.assertRaisesRegex(ValueError, 'complete outer mirror'):
                    g13.mirror_gate({'outer_mirror_audit': bad}, root, outer)
            bad = copy.deepcopy(proof); bad['native_difference_mm3']['added_volume_mm3'] = float('nan')
            with self.assertRaises(ValueError):
                g13.mirror_gate({'outer_mirror_audit': bad}, root, outer)
            self.assertFalse(g13.zero_difference({}))
            equivalence['files']['g11_original']['sha256'] = 'changed'
            sidecar.write_text(json.dumps(equivalence))
            with self.assertRaisesRegex(ValueError, 'equivalence fingerprint'):
                g13.mirror_gate({'outer_mirror_audit': proof}, root, outer)

    def test_select_smallest_volume_margin_then_best_near_threshold_never_above(self):
        variants = {i: {'volume_mm3': n+1.} for n, i in enumerate(g13.IDS)}
        rows = {(i, 2.): result(.034-n*.001) for n, i in enumerate(g13.IDS)}
        selected, reason = g13.choose(rows, variants)
        self.assertEqual(selected['central_diaphragm'], g13.CENTRALS[0])
        self.assertIn('smallest_volume', reason)
        rows = {(i, 2.): result(.041) for i in g13.IDS}
        rows[g13.CENTRALS[1], 2.] = result(.039)
        rows[g13.CENTRALS[2], 2.] = result(.038)
        selected, reason = g13.choose(rows, variants)
        self.assertEqual(selected['central_diaphragm'], g13.CENTRALS[2])
        self.assertIsNone(selected['carrier_base_p'])
        self.assertIn('near_threshold', reason)
        rows[g13.CENTRALS[2], 2.] = result(.001, qualified=False)
        self.assertEqual(g13.choose(rows, variants)[0]['central_diaphragm'], g13.CENTRALS[1])

    def test_reference_requires_all_serial_rows_and_exact_retained_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); binary = root/'binary'; binary.write_text('native runtime')
            rows = []
            for ident, direction, threads in g13.reference.PLAN:
                case = root/ident; case.mkdir(); (case/'x.log').write_text('retained log')
                row = dict(id=ident, direction=direction, threads=threads, compared=True,
                           passed=threads == 1, hashes={'x.log': g13.g8.sha256(case/'x.log')})
                g13.g11.publish(case/'case.json', row); rows.append(row)
            identity = dict(recipe=g13.reference.RECIPE, source_sha256=g13.g8.sha256(Path(g13.reference.__file__)),
                reused_sources_sha256=g13.reference.SOURCES, original_sha256=g13.reference.INPUTS,
                real_ccx_binary_sha256=g13.g8.sha256(binary))
            g13.g11.publish(root/'identity.json', identity)
            summary = dict(recipe=g13.reference.RECIPE, rows=rows, error=None, **g13.reference.assess(rows))
            path = root/'summary-0001.json'; g13.g11.publish(path, summary)
            with patch.object(g13.reference, 'inputs'):
                self.assertTrue(g13.reference_gate(path, binary)['serial_reference_passed'])
                (root/rows[0]['id']/'x.log').write_text('changed')
                with self.assertRaisesRegex(ValueError, 'artifact changed'):
                    g13.reference_gate(path, binary)
                (root/rows[0]['id']/'x.log').write_text('retained log')
                rows[2]['passed'] = False
                path.write_text(json.dumps(dict(summary, rows=rows, **g13.reference.assess(rows))))
                with self.assertRaisesRegex(ValueError, 'every serial'):
                    g13.reference_gate(path, binary)

    def test_serial_logs_require_all_reported_counts_and_clean_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'x.log'
            path.write_text('CalculiX Version 2.21\nUsing up to 1 cpu(s)\nUsing 1 cpu(s)\nJob finished\n')
            self.assertEqual(g13.serial_log(path)['observed_cpu_counts'], [1])
            path.write_text(path.read_text()+'Using up to 4 cpu(s)\n')
            with self.assertRaisesRegex(ValueError, 'serial CalculiX'):
                g13.serial_log(path)
            with self.assertRaises(ValueError):
                g13.confined(Path(folder), '../escape')

    def test_convergence_uses_vectors_not_equal_norms_and_keeps_p95_gate(self):
        medium, fine = result(), result()
        self.assertTrue(g13.g11.assessment(medium, fine)['accepted'])
        medium['cases'][0]['mechanics']['journal_weighted_displacement_mm']['intake'] = [0., .03, 0.]
        self.assertFalse(g13.g11.assessment(medium, fine)['accepted'])
        medium = result(); medium['cases'][0]['mechanics']['von_Mises_p95_MPa'] = 11.
        self.assertFalse(g13.g11.assessment(medium, fine)['accepted'])

    def test_campaign_snapshots_deadline_failure_and_interrupt_are_fail_closed(self):
        for mode in ('complete', 'above', 'failed', 'deadline', 'interrupt'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); snapshots = root/'results'; snapshots.mkdir()
                (snapshots/'summary-0001.json').write_text('{"reference":true}\n')
                args = SimpleNamespace(cad=root/'cad.json', outer_cad=root/'outer.json', reference=root/'ref.json',
                    ccx_wrapper=root/'ccx', ccx_binary=root/'binary', output=snapshots/'g13-campaign', snapshots=snapshots,
                    backend='cpu', deadline=time.time()+(0 if mode == 'deadline' else 1000), case_timeout=10, reserve_seconds=1)
                for name in ('cad', 'outer_cad'):
                    getattr(args, name).write_text('{}')
                variants = {i: {'volume_mm3': n+1.} for n, i in enumerate(g13.IDS)}
                def started(command, **kwargs):
                    case = Path(command[command.index('--output')+1]); case.mkdir()
                    (case/'case.json').write_text('{}')
                    process = Mock(pid=987654, **{'wait.return_value': 1 if mode == 'failed' else 0})
                    if mode == 'interrupt':
                        process.wait.side_effect = [KeyboardInterrupt(), -9]
                    return process
                with patch.object(g13, 'inputs', return_value=({'baseline_support_land': {}}, {}, variants)), \
                        patch.object(g13, 'runtime', return_value={'serial_reference_passed': True}), \
                        patch.object(g13, 'mirror_gate', return_value={'accepted': True}), \
                        patch.object(g13, 'recover', side_effect=lambda *args: result(.05 if mode == 'above' else .03)), \
                        patch.object(g13.subprocess, 'Popen', side_effect=started) as launch, \
                        patch.object(g13.os, 'killpg') as kill:
                    if mode == 'interrupt':
                        with self.assertRaises(KeyboardInterrupt):
                            g13.run(args)
                        kill.assert_called_once_with(987654, g13.signal.SIGKILL)
                        self.assertFalse(list(args.output.glob('checkpoint-*.json')))
                        continue
                    self.assertEqual(g13.run(args), 0)
                    expected = 8 if mode == 'complete' else 0 if mode == 'deadline' else 4
                    self.assertEqual(launch.call_count, expected)
                    self.assertEqual(kill.call_count, expected)
                    summary = json.loads((args.output/'summary-0001.json').read_text())
                    self.assertEqual(summary, json.loads((snapshots/'summary-0002.json').read_text()))
                    self.assertEqual(summary['complete'], mode == 'complete')
                    self.assertEqual(summary['all_supports_qualified'], mode == 'complete')
                    self.assertFalse(summary['manufacturing_authorized'])
                    self.assertFalse(summary['engine_start_authorized'])
                    self.assertFalse(summary['assembled_stiffness_qualified'])
                    self.assertEqual(len(list(snapshots.glob('checkpoint-*.json'))), expected)
                    self.assertEqual(len(summary['records'])+len(summary['not_run']), 12)
                    if mode in ('failed', 'above'):
                        self.assertTrue(all(r['size_mm'] == 2. for r in summary['records']))
                    self.assertFalse(list(args.output.rglob('result.json')))


if __name__ == '__main__':
    unittest.main()
