"""Private parallel seal, historical gates and checkpoint reuse contracts."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

if importlib.util.find_spec('pyslm') is None:
    raise unittest.SkipTest('Optional pinned coverage runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support, '_triangulate_exact_projected_domain'):
    raise unittest.SkipTest('Pinned coverage runtime required')

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
import admissions_v3 as public_admission
import build_cached as public_builder
ORIGINAL=(public_admission._exact_support_units,public_builder.seal,public_builder.PreparedRegions)
spec=importlib.util.spec_from_file_location('_test_cached_v6',SOURCE/'build_cached_v6.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
fixture_spec=importlib.util.spec_from_file_location('_v6_seal_fixtures',Path(__file__).with_name('test_carrier_combinatorial_admissions_v3.py'))
fixture=importlib.util.module_from_spec(fixture_spec);fixture_spec.loader.exec_module(fixture)


class CachedBuildV6(unittest.TestCase):
    def stage(self,directory):
        """Synthetic serialization fixture; no support geometry admission claimed."""
        directory.mkdir()
        supports=[];rows=[];proofs=[]
        for index,source in enumerate([0,1,2,3,8,9,10]):
            reconstruction=dict(vertical_contact_penetration_mm=.2,software_fixture=index)
            supports.append(dict(index=index,grid_coverage=dict(axes=[dict(planes=[dict(order=0,
                continuous_interface_reconstruction=reconstruction,contacts=[])])]),
                peripheral_skin=dict(continuous_fragmented_interfaces=True,components=[])))
            result=dict(passed=True,software_fixture=index)
            rows.append(dict(source_index=source,unit='grid-0-0',origin='exact_function_with_reused_exact_cycle_areas',
                reconstruction_sha256=driver.parallel.identity(reconstruction),contacts_sha256=driver.parallel.identity([]),
                penetration_mm=.2,result_sha256=driver.parallel.identity(result)))
            proofs.append(dict(region=index,unit='grid-0-0',receipt=result))
        execution=dict(schema='bounded-exact-unit-replays-1',status='completed',workers=4,
            maximum_pending_futures=8,worker_group_closed=True,engine_source_sha256=driver.BASE_SHA256,
            replay_assembly_sha256=driver.parallel.AREA_SHA256,source_indices=[0,1,2,3,8,9,10],
            policy_sha256={p.name:h for p,h in driver.POLICY_SHA256.items()},units=rows,
            runtime_before_sha256=driver.parallel.identity(driver.parallel.runtime_identity()),
            runtime_after_sha256=driver.parallel.identity(driver.parallel.runtime_identity()),
            worker_runtime_identity_verified_at_initialisation=True,
            reviewed_proof_files_sha256={})
        driver._write(directory/driver.REPLAY_NAME,execution)
        digest=driver.sha(directory/driver.REPLAY_NAME)
        binding=dict(receipt=driver.REPLAY_NAME,receipt_sha256=digest,files_sha256={driver.REPLAY_NAME:digest})
        checkpoint=dict(input_sha256='software-fixture',manufacturing_preparation_admitted=True,supports=supports,
            admission={},outputs_sha256={driver.REPLAY_NAME:digest},admission_runtime_hooks=driver.RUNTIME_HOOKS,
            exact_unit_replays=binding)
        for key in driver.KEYS:
            receipt=dict(passed=True,status='passed',input_sha256=checkpoint['input_sha256'],admission_schema=driver.SCHEMA,
                admission_source_sha256=driver._v5.ADMISSION_SHA256,admission_runtime_hooks=driver.RUNTIME_HOOKS,
                exact_unit_replays=binding)
            if key in ('skins','grids','contacts','collisions'):receipt['continuous_interval_exact_admissions']=proofs
            name='admission-'+key+'.json';driver._write(directory/name,receipt)
            checkpoint['admission'][key]=dict(status='passed',receipt=name,receipt_sha256=driver.sha(directory/name))
        driver._write(directory/'support-stage.json',checkpoint)
        return checkpoint

    def test_private_sources_and_both_authorities_remain_original(self):
        self.assertEqual(ORIGINAL,(public_admission._exact_support_units,public_builder.seal,public_builder.PreparedRegions))
        self.assertIs(driver._v5._base.seal,driver.seal)
        self.assertEqual(driver._v5.admissions_v3.seal.__code__.co_filename,str(SOURCE/'admissions_v3.py'))
        self.assertEqual(set(driver.RUNTIME_HOOKS['combinatorial_constructor_dispatch']['authorities']),
            {driver._v5.OLD_CONSTRUCTION_SHA256,driver._v5.REDUNDANT_SHA256})
        self.assertEqual(tuple(driver.KEYS),('envelopes','regions','skins','grids','contacts','collisions'))
        for path in (driver.PARALLEL_PATH,driver.parallel.AREA):
            with patch.dict(driver.POLICY_SHA256,{path:'0'*64}),patch.object(driver._v5._base,'build') as base:
                with self.assertRaisesRegex(ValueError,'policy changed'):driver.build('i','o','e','c')
                base.assert_not_called()

    def test_prepared_closure_retains_all_v6_sources(self):
        prepared=SimpleNamespace(files={},verify=lambda:None)
        with patch.object(driver,'ACTIVE',{}),patch.object(driver,'_prepared',return_value=prepared):
            actual=driver._v5.prepared_regions('manifest',[0])
        self.assertIs(actual,prepared);self.assertEqual(actual.files,driver.POLICY_SHA256)

    def test_reuse_requires_all_six_gates_and_exact_replay_results(self):
        for mutation in ('hook','execution','payload','result','missing_gate','path','proof','copy_map','order','runtime'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                directory=Path(tmp)/'stage';checkpoint=self.stage(directory)
                if mutation=='hook':checkpoint['admission_runtime_hooks']={}
                elif mutation=='payload':checkpoint['supports'][0]['grid_coverage']['axes'][0]['planes'][0]['contacts']=[1]
                elif mutation=='missing_gate':checkpoint['admission'].pop('contacts')
                elif mutation=='path':checkpoint['exact_unit_replays']['receipt']='../outside'
                elif mutation=='copy_map':checkpoint['outputs_sha256'].clear()
                elif mutation=='order':checkpoint['supports'][1]['index']=0
                elif mutation=='execution':
                    with (directory/driver.REPLAY_NAME).open('a') as stream:stream.write(' ')
                elif mutation=='proof':checkpoint['exact_unit_replays']['files_sha256']['foreign.json']='0'*64
                elif mutation=='runtime':
                    execution=json.loads((directory/driver.REPLAY_NAME).read_text());execution['runtime_after_sha256']='0'*64
                    driver._write(directory/driver.REPLAY_NAME,execution);digest=driver.sha(directory/driver.REPLAY_NAME)
                    checkpoint['exact_unit_replays']['receipt_sha256']=digest
                    checkpoint['exact_unit_replays']['files_sha256'][driver.REPLAY_NAME]=digest
                    checkpoint['outputs_sha256'][driver.REPLAY_NAME]=digest
                else:
                    item=checkpoint['admission']['grids'];receipt=json.loads((directory/item['receipt']).read_text())
                    receipt['continuous_interval_exact_admissions'][0]['receipt']['software_fixture']=-1
                    driver._write(directory/item['receipt'],receipt);item['receipt_sha256']=driver.sha(directory/item['receipt'])
                driver._write(directory/'support-stage.json',checkpoint)
                with patch.object(driver._v5,'build') as base,self.assertRaises(ValueError):
                    driver.build('i',Path(tmp)/'new','e','c',reuse_support_stage=directory)
                base.assert_not_called();self.assertFalse((Path(tmp)/'new').exists())

    def test_supports_only_and_full_core_reuse_restore_the_exact_execution_binding(self):
        for only in (True,False):
            with self.subTest(supports_only=only),tempfile.TemporaryDirectory() as tmp:
                output=Path(tmp)/'out';source=output if only else Path(tmp)/'out-supports'
                def base(*args):
                    checkpoint=self.stage(source)
                    if only:return copy.deepcopy(checkpoint)
                    output.mkdir()
                    for path in source.iterdir():
                        if path.name!='support-stage.json':(output/path.name).write_bytes(path.read_bytes())
                    stripped=copy.deepcopy(checkpoint);stripped.pop('exact_unit_replays');stripped.pop('admission_runtime_hooks')
                    stripped['outputs_sha256']={}
                    driver._write(output/'support-stage.json',stripped)
                    return dict(outputs_sha256={})
                with patch.object(driver._v5._base,'build',side_effect=base):
                    report=driver.build('i',output,'e','c',supports_only=only)
                driver.verify_v6_stage(output)
                self.assertEqual(report['runner_adapter_source_sha256'],driver.sha(driver.__file__))
                if not only:self.assertEqual(report['outputs_sha256']['support-stage.json'],driver.sha(output/'support-stage.json'))
                self.assertIsNone(driver.ACTIVE)

    def test_reuse_runs_no_constructor_and_preserves_the_closed_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'stage';self.stage(source);output=Path(tmp)/'full'
            def base(*args):
                output.mkdir()
                for path in source.iterdir():(output/path.name).write_bytes(path.read_bytes())
                return dict(outputs_sha256={})
            with patch.object(driver._v5._base,'build',side_effect=base),patch.object(driver.parallel,'ParallelExactAdmissions') as workers:
                driver.build('i',output,'e','c',reuse_support_stage=source)
            workers.assert_not_called();driver.verify_v6_stage(output)

    def test_seal_preserves_nonoverlay_failures_and_closes_before_publication(self):
        fixture.CombinatorialAdmissionsV3.setUpClass()
        fixture_case=fixture.CombinatorialAdmissionsV3()
        # These small synthetic seven-region metadata fixtures isolate parent gates.
        # Only planar replay is mocked; parent admission logic remains unchanged.
        for failed in (False,True):
            with self.subTest(failed=failed),tempfile.TemporaryDirectory() as tmp:
                directory=Path(tmp);checkpoint,store,_=fixture_case.fixture_seal(directory)
                checkpoint['outputs_sha256']={}
                store.report['regions']=[dict(source_index=i)for i in (0,1,2,3,8,9,10)]
                if failed:checkpoint['supports'][0]['peripheral_skin']['expected_vertical_components']=2
                class Pool:
                    closed=False
                    def __init__(self,*args):self.rows=[]
                    def __enter__(self):return self
                    def __call__(self,support,p):return {name:dict(passed=True)for name,_,_ in driver.parallel.units(support)}
                    def __exit__(self,*args):self.closed=True
                    def receipt(self):return dict(worker_group_closed=self.closed,units=self.rows)
                prepared=SimpleNamespace(files={},verify=lambda:None)
                original=driver._v5.admissions_v3._exact_support_units
                with patch.object(driver,'ACTIVE',dict(prepared=prepared,proven=None)),patch.object(driver.parallel,'ParallelExactAdmissions',Pool):
                    result,passed=driver.seal(directory,checkpoint,store)
                self.assertEqual(passed,not failed);self.assertEqual(set(result),set(driver.KEYS))
                self.assertIs(driver._v5.admissions_v3._exact_support_units,original)
                execution=json.loads((directory/driver.REPLAY_NAME).read_text());self.assertTrue(execution['worker_group_closed'])
                for reference in result.values():
                    receipt=json.loads((directory/reference['receipt']).read_text())
                    self.assertEqual(receipt['exact_unit_replays'],checkpoint['exact_unit_replays'])
                self.assertEqual(checkpoint['supports'][0]['peripheral_skin']['components'][0]['infill'][
                    'outside_free_domain_and_contact_band_area_mm2'],4.99e-30)

    def test_fatal_seal_failure_restores_private_function_and_leaves_no_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=driver._v5.admissions_v3._exact_support_units
            active=dict(prepared=SimpleNamespace(files={},verify=lambda:None),proven=None)
            store=SimpleNamespace(report=dict(regions=[dict(source_index=0)]))
            with patch.object(driver,'ACTIVE',active),patch.object(driver,'_seal',side_effect=RuntimeError('witness fatal')):
                with self.assertRaisesRegex(RuntimeError,'witness fatal'):driver.seal(tmp,{},store)
            self.assertIs(driver._v5.admissions_v3._exact_support_units,original)
            receipt=json.loads((Path(tmp)/driver.REPLAY_NAME).read_text())
            self.assertEqual(receipt['status'],'failed');self.assertTrue(receipt['worker_group_closed'])
            self.assertFalse(list(Path(tmp).glob('admission-*.json')))

    def test_real_small_worker_math_reaches_all_six_synthetic_gate_receipts(self):
        fixture.CombinatorialAdmissionsV3.setUpClass()
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            checkpoint,store,_=fixture.CombinatorialAdmissionsV3().fixture_seal(directory)
            checkpoint['outputs_sha256']={}
            store.report['regions']=[dict(source_index=i)for i in (0,1,2,3,8,9,10)]
            active=dict(prepared=SimpleNamespace(files={},verify=lambda:None),proven=None)
            with patch.object(driver,'ACTIVE',active):
                admission,passed=driver.seal(directory,checkpoint,store)
            self.assertTrue(passed);self.assertEqual(len(admission),6)
            actual=driver.verify_v6_stage(directory)
            execution=json.loads((directory/driver.REPLAY_NAME).read_text())
            self.assertEqual(len(execution['units']),21)
            self.assertEqual([r['source_index']for r in execution['units']],
                [i for i in (0,1,2,3,8,9,10)for _ in range(3)])
            self.assertTrue(execution['worker_group_closed'])
            self.assertEqual(actual['supports'],checkpoint['supports'])
