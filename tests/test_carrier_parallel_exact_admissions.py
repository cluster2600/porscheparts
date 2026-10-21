"""Small exact replay witnesses; retained real units are read, never recomputed."""
import copy
from concurrent.futures import Future
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

if importlib.util.find_spec('pyslm') is None:
    raise unittest.SkipTest('Optional pinned coverage runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support, '_triangulate_exact_projected_domain'):
    raise unittest.SkipTest('Pinned coverage runtime required')
import shapely

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0, str(SOURCE))
import parallel_exact_admissions as parallel
from grid_intervals import contacts


def load(name):
    spec = importlib.util.spec_from_file_location('_parallel_test_'+name, SOURCE/(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def witness(new=False):
    free = shapely.box(0., 10., 5., 11.)
    interfaces = dict(upper=[[[0.,10. if new else 11.],[5.,10. if new else 11.]]],
                      lower=[[[0.,11. if new else 10.],[5.,11. if new else 10.]]])
    material, receipt = load('continuous_redundant_interfaces' if new else
                            'continuous_combinatorial_interfaces').repair(shapely.Polygon(), free, interfaces, .2)
    return receipt, contacts(material, free, interfaces)


def support(values, index=0):
    return dict(index=index, peripheral_skin=dict(continuous_fragmented_interfaces=True, components=[]),
        grid_coverage=dict(axes=[dict(planes=[dict(order=i, continuous_interface_reconstruction=r, contacts=c)
            for i,(r,c) in enumerate(values)])]))


class ParallelExactAdmissions(unittest.TestCase):
    def test_area_copy_changes_only_the_one_exact_expression(self):
        old = (SOURCE/'incremental_combinatorial_interfaces_ids.py').read_bytes()
        self.assertEqual(parallel.AREA.read_bytes(), old.replace(
            b'ring_area=sum(_OLD.exact_area(ring) for ring in generated)', b'ring_area=sum(areas)'))
        self.assertEqual(parallel.sha(parallel.AREA), parallel.AREA_SHA256)

    def test_spawn_one_and_four_preserve_both_receipts_and_refusal_order(self):
        values = [witness(), witness(True), ({'combinatorial_construction_source_sha256':'unknown'}, [])]
        original = copy.deepcopy(values); engine = parallel.load_engine(); expected = {}
        for index,(r,c) in enumerate(values):
            try: value = engine.continuous_admission(r,c,.2)
            except (ValueError,KeyError,TypeError,IndexError) as error:
                value = dict(passed=False,status='rejected',error=str(error))
            expected[f'grid-0-{index}'] = value
        for count in (1,4):
            environment = {k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')}
            with parallel.ParallelExactAdmissions([0], {parallel.AREA:parallel.AREA_SHA256}, workers=count) as pool:
                self.assertEqual(pool(support(values),.2), expected)
            self.assertTrue(pool.receipt()['worker_group_closed'])
            self.assertEqual(pool.receipt()['runtime_before_sha256'],pool.receipt()['runtime_after_sha256'])
            self.assertEqual([r['unit'] for r in pool.rows], list(expected))
            self.assertEqual({k:os.environ.get(k) for k in environment}, environment)
        self.assertEqual(values, original)

    def test_pending_window_and_out_of_order_completion_preserve_order(self):
        class Pool:
            def __init__(self, **kwargs): self.kwargs=kwargs; self.calls=[]; self.closed=False
            def submit(self, function, reconstruction, contacts, penetration):
                future=Future();future.set_result(dict(passed=True,id=reconstruction['id']))
                self.calls.append((future,reconstruction['id']));return future
            def shutdown(self, **kwargs): self.closed=kwargs
        windows=[]
        def finish(pending, **kwargs):
            windows.append(len(pending));return ({list(pending)[-1]},set(pending)-{list(pending)[-1]})
        with patch.object(parallel,'ProcessPoolExecutor',Pool),patch.object(parallel,'wait',finish):
            with parallel.ParallelExactAdmissions([0], {}) as pool:
                actual=pool(support([({'id':i},[]) for i in range(19)]),.2)
        self.assertEqual([r['id'] for r in actual.values()],list(range(19)))
        self.assertEqual(max(windows),8);self.assertEqual(pool.pool.kwargs['max_workers'],4)
        self.assertEqual(pool.pool.closed,dict(wait=True,cancel_futures=True))

    def test_expected_and_unexpected_failures_close_without_a_pass(self):
        with patch.object(parallel,'WORKER_ENGINE') as engine:
            engine.continuous_admission.side_effect=ValueError('witness refusal')
            self.assertEqual(parallel.calculate({},[],.2),dict(passed=False,status='rejected',error='witness refusal'))
            engine.continuous_admission.side_effect=RuntimeError('fatal witness')
            with self.assertRaisesRegex(RuntimeError,'fatal witness'): parallel.calculate({},[],.2)
        with patch.object(parallel,'ProcessPoolExecutor') as factory:
            factory.return_value.submit.side_effect=RuntimeError('submit failed')
            with self.assertRaisesRegex(RuntimeError,'submit failed'):
                with parallel.ParallelExactAdmissions([0],{}) as pool: pool(support([({},[])]),.2)
            self.assertTrue(pool.closed);self.assertFalse(pool.rows)
            factory.return_value.shutdown.assert_called_once_with(wait=True,cancel_futures=True)

    def test_changed_sources_are_refused_before_worker_initialisation_and_after_close(self):
        with patch.object(parallel,'sha',return_value='changed'),patch.object(parallel,'load_engine') as engine:
            with self.assertRaisesRegex(ValueError,'worker source differs'): parallel.initialise({'source':'expected'}, {})
            engine.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source';path.write_text('original')
            with patch.object(parallel,'ProcessPoolExecutor'):
                with self.assertRaisesRegex(ValueError,'changed during replay'):
                    with parallel.ParallelExactAdmissions([0],{path:parallel.sha(path)}):path.write_text('changed')

    def test_worker_and_parent_runtime_mismatch_are_refused(self):
        with patch.object(parallel,'runtime_identity',return_value={'runtime':'different'}),patch.object(parallel,'load_engine') as engine:
            with self.assertRaisesRegex(ValueError,'worker runtime differs'):parallel.initialise({}, {'runtime':'original'})
            engine.assert_not_called()
        with patch.object(parallel,'ProcessPoolExecutor') as factory,patch.object(parallel,'runtime_identity',
                side_effect=[{'runtime':'original'},{'runtime':'changed'}]):
            with self.assertRaisesRegex(ValueError,'parent runtime changed'):
                with parallel.ParallelExactAdmissions([0],{}) as pool:pass
            self.assertTrue(pool.closed)
            factory.return_value.shutdown.assert_called_once_with(wait=True,cancel_futures=True)
        class OldResults:runtime={'runtime':'historical'}
        with patch.object(parallel,'runtime_identity',return_value={'runtime':'new'}),patch.object(parallel,'ProcessPoolExecutor') as factory:
            with self.assertRaisesRegex(ValueError,'reviewed results'):
                with parallel.ParallelExactAdmissions([0],{},OldResults()):pass
            factory.assert_not_called()

    def test_only_four_retained_results_reuse_under_all_bindings_without_submission(self):
        folder=ROOT/'work/carrier-process-20261016/dual-constructor-real-consumption-001'
        if not (folder/'assessment.json').is_file():self.skipTest('Optional retained real local evidence absent')
        report=json.loads((folder/'assessment.json').read_text());engine=parallel.load_engine()
        producers={r['source_index']:r for r in report['producer_identities']}
        proven=parallel.FourProvenResults(folder/'assessment.json',producers,engine)
        for source_index in (3,9):
            raw=ROOT/f'work/carrier-process-20261016/real-support-v5-regions-001/source-{source_index:03d}/geometry-assessment.json'
            metadata=json.loads(raw.read_text())
            values=[('grid-0-0',metadata['grid_coverage']['axes'][0]['planes'][0]['continuous_interface_reconstruction'],metadata['grid_coverage']['axes'][0]['planes'][0]['contacts']),
                    ('skin-0',metadata['peripheral_skin']['components'][0]['infill']['continuous_interface_reconstruction'],metadata['peripheral_skin']['components'][0]['infill']['interface_contacts'])]
            surface=dict(index=0,grid_coverage=dict(axes=[dict(planes=[dict(order=0,continuous_interface_reconstruction=values[0][1],contacts=values[0][2])])]),
                peripheral_skin=dict(continuous_fragmented_interfaces=True,components=[dict(index=0,infill=dict(continuous_interface_reconstruction=values[1][1],interface_contacts=values[1][2]))]))
            with patch.object(parallel,'ProcessPoolExecutor') as factory:
                with parallel.ParallelExactAdmissions([source_index],{},proven) as pool: actual=pool(surface,.2)
                factory.return_value.submit.assert_not_called()
            for name,r,c in values:
                self.assertTrue(actual[name]['passed']);bad=copy.deepcopy(r);bad['selected_intervals']=-1
                with self.assertRaisesRegex(ValueError,'payload'):proven.get(source_index,name,bad,c,.2)
                with self.assertRaisesRegex(ValueError,'penetration'):proven.get(source_index,name,r,c,.3)
        bad=copy.deepcopy(producers);bad[3]['surface_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'producer'):parallel.FourProvenResults(folder/'assessment.json',bad,engine)
