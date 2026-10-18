"""Synthetic array/consumer doubles only. No NumPy, AM, graph or remap execution."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_certified_consumer_checks',HERE/'certified_support_consumer.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class Array:
    def __init__(self,values,dtype):
        self.values=deepcopy(values);self.dtype=NS(str=dtype,kind='f'if dtype.endswith('f8')else'i')
        self.shape=(len(values),len(values[0]))if values and isinstance(values[0],list)else(len(values),)
    def __len__(self):return len(self.values)
    def tolist(self):return deepcopy(self.values)
    def copy(self):return Array(self.values,self.dtype.str)
    def tobytes(self):
        flat=[x for row in self.values for x in row]if len(self.shape)==2 else self.values
        code='d'if self.dtype.kind=='f'else'q'
        return struct.pack('<'+code*len(flat),*flat)


class Data:
    def __init__(self,path):
        self.arrays={n:Array(d['values'],d['dtype'])for n,d in json.loads(Path(path).read_text()).items()};self.files=list(self.arrays)
    def __enter__(self):return self
    def __exit__(self,*_):pass
    def __getitem__(self,key):return self.arrays[key]


class Surface:
    def __init__(self,arrays):
        self.vertices=arrays['vertices'].copy();self.faces=arrays['faces'].copy()
        self.face_attributes={n:arrays[n].copy()for n in ('order','type')}
    def copy(self):return Surface(dict(vertices=self.vertices,faces=self.faces,**self.face_attributes))


def save_arrays(path,arrays):
    path.write_text(json.dumps({n:dict(dtype=a.dtype.str,values=a.tolist())for n,a in arrays.items()}))


class Fixture:
    def __init__(self,root,attribute_dtype='<i8'):
        self.root=root;self.calls=[];self.graph_calls=0
        self.original=dict(vertices=Array([[0.,0.,0.],[1.,0.,0.],[1.,0.,1.],[0.,0.,1.]],'<f8'),
            faces=Array([[0,1,2],[0,2,3]],'<i8'),order=Array([7,7],attribute_dtype),type=Array([2,2],attribute_dtype))
        self.candidate={n:a.copy()for n,a in self.original.items()};self.candidate['faces']=Array([[0,1,3],[1,2,3]],'<i8')
        self.group=dict(id='grid-0-7',kind='grid',order=7,type=2,face_range=[0,2])
        self.skin=dict(status='generated',support_surface_face_groups=[self.group],components=[dict(historical='unchanged')])
        self.grid=dict(status='passed',historical_2D_payload='unchanged')
        self.runtime=dict(synthetic='not_an_AM_runtime')
        save_arrays(root/'topology-original.npz',self.original);save_arrays(root/'topology-candidate.npz',self.candidate)
        (root/'topology-trace.npz').write_text('synthetic trace fixture, not a real NPZ')
        self.parent=dict(status='region_geometry_completed_no_global_admission',source_index=3,
            files_sha256={'support.npz':m.sha(root/'topology-original.npz'),'geometry-assessment.json':'synthetic-metadata'},
            runtime_unchanged=True,runtime_before=self.runtime,runtime_after=self.runtime)
        m.write(root/'topology-parent.json',self.parent)
        trace=dict(status='original_skin_parameter_trace_verified_no_repair',source_index=3,
            original_surface_sha256=m.sha(root/'topology-original.npz'),base_surface_sha256=m.sha(root/'topology-original.npz'),
            files_sha256_before={'synthetic-base':m.sha(root/'topology-original.npz')},
            metadata_sha256='synthetic-metadata',trace_npz_sha256=m.sha(root/'topology-trace.npz'),
            runtime_before_sha256=m.identity(self.runtime),runtime_after_sha256=m.identity(self.runtime))
        m.write(root/'topology-trace.json',trace)
        before={n:m.sha(root/n)for n in ('topology-original.npz','topology-trace.npz','topology-trace.json')}
        self.receipt=dict(status='certified_local_flip_candidate_no_global_admission',global_admission=False,inputs_unchanged=True,
            inputs_sha256_before=before,inputs_sha256_after=before,runtime_before_sha256=m.identity(self.runtime),runtime_after_sha256=m.identity(self.runtime),
            output_npz_sha256=m.sha(root/'topology-candidate.npz'),original_arrays=m.array_identities(self.original),candidate_arrays=m.array_identities(self.candidate),
            proof=dict(changed_face_ids=[0,1],initial_collapsed_cuts=2,final_collapsed_cuts=0))
        m.write(root/'topology-candidate.json',self.receipt)
        m.write(root/'topology-remap.json',dict(candidate_npz_sha256=m.sha(root/'topology-candidate.npz'),candidate_receipt_sha256=m.sha(root/'topology-candidate.json'),
            trace_base_surface_sha256=m.sha(root/'topology-original.npz')))
        m.write(root/'topology-strict-plan.json',dict(files_sha256={'synthetic-candidate':m.sha(root/'topology-candidate.npz')}))
        m.write(root/'topology-strict.json',dict(status='strict_candidate_sections_completed_no_global_admission',source_index=3,
            declared_layers=1034,completed_layers=1034,first_refusal=None,runtime_unchanged=True,files_unchanged=True,global_admission=False,
            plan_sha256=m.sha(root/'topology-strict-plan.json'),parallel_sections=dict(worker_group_closed=True,sources_and_inputs_sha256={'candidate':m.sha(root/'topology-candidate.npz')})))
        self.row=dict(source_index=3,parent_checkpoint='topology-parent.json',original_npz='topology-original.npz',candidate_npz='topology-candidate.npz',
            candidate_receipt='topology-candidate.json',strict_plan='topology-strict-plan.json',strict_receipt='topology-strict.json',
            trace_npz='topology-trace.npz',trace_receipt='topology-trace.json',remap_bundle='topology-remap.json',
            historical_skin_sha256=m.identity(self.skin),historical_grid_sha256=m.identity(self.grid))
        self.document=dict(schema='certified-support-topology-capsule-1',global_admission=False,runtime_helpers=[],rows=[self.row],files_sha256={})
        self.reseal()

    def reseal(self):
        self.document['files_sha256']={p.name:m.sha(p)for p in self.root.glob('topology-*')if p.name!=m.MANIFEST}
        m.write(self.root/m.MANIFEST,self.document)
        self.capsule=m.Capsule(self.root/m.MANIFEST,m.sha(self.root/m.MANIFEST))

    def mutate(self,name,fn):
        data=json.loads((self.root/name).read_text());fn(data);m.write(self.root/name,data);self.reseal()

    def graph(self,vertices,faces,groups):
        self.calls.append('graph');self.graph_calls+=1
        return dict(status='passed',input_geometry_sha256=__import__('hashlib').sha256(vertices.tobytes()+faces.tobytes()).hexdigest(),
            groups=1,faces=2,components=[dict(group_ids=[self.group['id']],passed=True,upper_contact_group_ids=['upper'],lower_contact_group_ids=['lower'])],
            internal_connectivity=[dict(group_id=self.group['id'],passed=True,remaining_components=1)],seconds=float(self.graph_calls))

    def check_graph(self,graph,skin,vertices,faces):
        expected=__import__('hashlib').sha256(vertices.tobytes()+faces.tobytes()).hexdigest()
        if graph.get('status')!='passed'or graph['input_geometry_sha256']!=expected or graph['internal_connectivity'][0]['remaining_components']!=1:
            raise ValueError('Synthetic graph identity/connectivity rejected')

    def geometry(self):
        block=NS(skinCoverage=deepcopy(self.skin),gridCoverage=deepcopy(self.grid));surface=Surface(self.original)
        result=self.capsule.geometry(self.row,surface,block,NS(load=lambda p,**kw:Data(p)),self.graph,self.check_graph,m.sha(self.root/'topology-parent.json'))
        return block,surface,result


class Checks(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.f=Fixture(self.root)
    def tearDown(self):self.tmp.cleanup()

    def test_derived_copy_preserves_originals_and_historical_payloads(self):
        block,old,new=self.f.geometry()
        self.assertEqual(m.array_identities(dict(vertices=old.vertices,faces=old.faces,**old.face_attributes)),self.f.receipt['original_arrays'])
        self.assertEqual(new.faces.tolist(),self.f.candidate['faces'].tolist());self.assertEqual(self.f.graph_calls,1)
        self.assertEqual(m.historical_skin(block.skinCoverage),self.f.skin);self.assertEqual(block.gridCoverage,self.f.grid)

    def test_real_float64_scan_attribute_storage_preserved(self):
        directory=self.root/'float-attributes';directory.mkdir();fixture=Fixture(directory,attribute_dtype='<f8')
        _,original,candidate=fixture.geometry()
        for name in ('order','type'):
            self.assertEqual(original.face_attributes[name].dtype.str,'<f8')
            self.assertEqual(candidate.face_attributes[name].dtype.str,'<f8')
            self.assertEqual(original.face_attributes[name].tobytes(),candidate.face_attributes[name].tobytes())

    def test_float_scan_identifiers_nonfinite_or_noninteger_refused(self):
        for name in ('order','type'):
            for value in (float('nan'),float('inf'),7.5):
                arrays={n:a.copy()for n,a in self.f.original.items()};arrays[name]=Array([value,value],'<f8')
                with self.subTest(name=name,value=value),self.assertRaises(ValueError):m.validate_arrays(arrays)

    def test_wrong_parent_refused_before_graph(self):
        with self.assertRaisesRegex(ValueError,'parent checkpoint'):
            self.f.capsule.geometry(self.f.row,Surface(self.f.original),NS(),NS(load=lambda p,**k:Data(p)),self.f.graph,self.f.check_graph,'foreign')
        self.assertEqual(self.f.graph_calls,0)

    def test_outside_certificate_face_refused(self):
        self.f.mutate('topology-candidate.json',lambda d:d['proof'].update(changed_face_ids=[0]))
        self.f.mutate('topology-remap.json',lambda d:d.update(candidate_receipt_sha256=m.sha(self.root/'topology-candidate.json')))
        with self.assertRaisesRegex(ValueError,'changed face'):self.f.geometry()

    def test_attr_dtype_or_row_change_refused(self):
        for name in ('order','vertices'):
            with self.subTest(name=name):
                original=self.f.candidate[name];self.f.candidate[name]=Array(original.tolist(),'<i8'if name=='vertices'else'<f8')
                save_arrays(self.root/'topology-candidate.npz',self.f.candidate);self.f.reseal()
                with self.assertRaises(ValueError):self.f.geometry()
                self.f.candidate[name]=original

    def test_strict_calendar_incomplete_or_unrelated_refused(self):
        self.f.mutate('topology-strict.json',lambda d:d.update(completed_layers=1033))
        with self.assertRaisesRegex(ValueError,'strict-calendar'):self.f.geometry()

    def test_trace_and_remap_binding_refuse(self):
        self.f.mutate('topology-remap.json',lambda d:d.update(candidate_receipt_sha256='foreign'))
        with self.assertRaisesRegex(ValueError,'trace or remap'):self.f.geometry()

    def test_trace_base_can_be_distinct_but_bound_to_both_ancestries(self):
        trace=json.loads((self.root/'topology-trace.json').read_text())
        trace['base_surface_sha256']='synthetic-earlier-GRID-only-candidate';trace['files_sha256_before']['base']=trace['base_surface_sha256']
        m.write(self.root/'topology-trace.json',trace)
        self.f.receipt['inputs_sha256_before']['base']=trace['base_surface_sha256']
        self.f.receipt['inputs_sha256_before']['topology-trace.json']=m.sha(self.root/'topology-trace.json')
        self.f.receipt['inputs_sha256_after']=deepcopy(self.f.receipt['inputs_sha256_before'])
        m.write(self.root/'topology-candidate.json',self.f.receipt)
        self.f.mutate('topology-remap.json',lambda d:d.update(trace_base_surface_sha256=trace['base_surface_sha256'],candidate_receipt_sha256=m.sha(self.root/'topology-candidate.json')))
        self.f.geometry()
        self.f.mutate('topology-remap.json',lambda d:d.update(trace_base_surface_sha256='unbound'))
        with self.assertRaisesRegex(ValueError,'trace or remap'):self.f.geometry()

    def test_trace_base_missing_from_own_ancestry_refused(self):
        self.f.mutate('topology-trace.json',lambda d:d.update(files_sha256_before={}))
        with self.assertRaisesRegex(ValueError,'trace or remap'):self.f.geometry()

    def test_group_ranges_and_scan_attributes_refuse(self):
        block=NS(skinCoverage=deepcopy(self.f.skin),gridCoverage=deepcopy(self.f.grid));block.skinCoverage['support_surface_face_groups'][0]['face_range']=[0,1]
        with self.assertRaises(ValueError):
            self.f.capsule.geometry(self.f.row,Surface(self.f.original),block,NS(load=lambda p,**k:Data(p)),self.f.graph,self.f.check_graph,m.sha(self.root/'topology-parent.json'))

    def test_graph_failure_does_not_publish_metadata(self):
        block=NS(skinCoverage=deepcopy(self.f.skin),gridCoverage=deepcopy(self.f.grid));before=deepcopy(block.skinCoverage)
        with self.assertRaises(ValueError):
            self.f.capsule.geometry(self.f.row,Surface(self.f.original),block,NS(load=lambda p,**k:Data(p)),lambda *a:dict(status='rejected'),self.f.check_graph,m.sha(self.root/'topology-parent.json'))
        self.assertEqual(block.skinCoverage,before)

    def test_capsule_relocation_from_other_cwd_and_tamper(self):
        destination=self.root/'moved';destination.mkdir()
        for p in self.f.capsule.files:shutil.copyfile(p,destination/p.name)
        previous=Path.cwd()
        try:
            os.chdir('/');relocated=m.Capsule(destination/m.MANIFEST,self.f.capsule.digest);relocated.verify()
        finally:os.chdir(previous)
        (destination/'topology-trace.npz').write_text('changed')
        with self.assertRaises(ValueError):relocated.verify()

    def test_manifest_absolute_escape_duplicate_sources_and_symlink_refused(self):
        for value in ('/tmp/topology-bad','../topology-bad','support-000.npz','topology-dir/file'):
            with self.subTest(value=value),self.assertRaises(ValueError):m.local_name(value)
        self.f.document['rows'].append(deepcopy(self.f.row))
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.f.reseal()

    def test_mutated_public_capsule_identity_refused(self):
        self.f.capsule.rows[3]['candidate_npz']='topology-original.npz'
        with self.assertRaisesRegex(ValueError,'public capsule'):self.f.capsule.verify()

    def test_stage_reuse_verifies_actual_arrays_without_recomputing_graph(self):
        block,_,surface=self.f.geometry();output=self.root/'stage';output.mkdir()
        checkpoint=dict(outputs_sha256={},supports=[{}for _ in m.INDICES]);index=m.INDICES.index(3)
        checkpoint['supports'][index]=dict(peripheral_skin=block.skinCoverage,grid_coverage=block.gridCoverage)
        name='admission-contacts.json';m.write(output/name,dict(passed=True,actual_material_connection_graphs=[dict(region=index,passed=True,receipt=block.skinCoverage['material_connection_graph'])]))
        checkpoint['admission']=dict(contacts=dict(receipt=name,receipt_sha256=m.sha(output/name)))
        save_arrays(output/f'support-{index:03d}.npz',dict(vertices=surface.vertices,faces=surface.faces,**surface.face_attributes))
        checkpoint['outputs_sha256'][f'support-{index:03d}.npz']=m.sha(output/f'support-{index:03d}.npz')
        self.f.capsule.copy_to(output,checkpoint)
        np=NS(load=lambda p,**k:Data(p));self.f.capsule.verify_stage(output,checkpoint,np,self.f.check_graph)
        self.assertEqual(self.f.graph_calls,1)
        changed=json.loads((output/f'support-{index:03d}.npz').read_text());changed['faces']['values'][0]=[0,1,2]
        (output/f'support-{index:03d}.npz').write_text(json.dumps(changed));checkpoint['outputs_sha256'][f'support-{index:03d}.npz']=m.sha(output/f'support-{index:03d}.npz')
        with self.assertRaisesRegex(ValueError,'Delivered'):self.f.capsule.verify_stage(output,checkpoint,np,self.f.check_graph)

    def test_private_install_keeps_policy_tuple_and_original_geometry_first(self):
        fixture=self.f;policy=self.root/'old-policy.py';policy.write_text('synthetic')
        class Prepared:
            def __init__(self):
                self.rows=[dict(source_index=i,checkpoint_sha256=m.sha(fixture.root/'topology-parent.json'))for i in m.INDICES];self.index=0;self.files={}
            def verify(self):pass
            def geometry(self,block):
                fixture.calls.append('original');self.index+=1;block.skinCoverage=deepcopy(fixture.skin);block.gridCoverage=deepcopy(fixture.grid)
                return Surface(fixture.original)
            def complete(self):
                if self.index!=7:raise ValueError('Original missing region')
        old_verify=lambda p:(_ for _ in()).throw(ValueError('original six-gate refusal'))
        v5=NS(POLICY_FILES=(policy,),POLICY_SHA256={policy:m.sha(policy)},_base=NS(),RUNTIME_HOOKS={})
        consumer=NS(_v5=v5,POLICY_SHA256={policy:m.sha(policy)},RUNTIME_HOOKS={},_prepared=Prepared,
            seal=lambda *a:None,verify_v6_stage=old_verify,_restore_execution=lambda *a:None)
        installed=m.install(consumer,fixture.capsule,NS(load=lambda p,**k:Data(p)),fixture.graph,fixture.check_graph)
        self.assertEqual(v5.POLICY_FILES,(policy,));prepared=installed._prepared()
        returned=[]
        for i in m.INDICES:returned.append(prepared.geometry(NS()))
        prepared.complete();self.assertEqual(fixture.graph_calls,1)
        self.assertEqual(fixture.calls.count('original'),7);self.assertEqual(fixture.calls[fixture.calls.index('graph')-1],'original')
        with self.assertRaisesRegex(ValueError,'original six-gate refusal'):installed.verify_v6_stage(self.root)
        with self.assertRaisesRegex(ValueError,'already configured'):m.install(consumer,fixture.capsule,None,None,None)

    def test_seal_reuse_restore_and_six_original_hook_checks(self):
        fixture=self.f;block,_,surface=fixture.geometry();source=self.root/'source-stage';source.mkdir();index=m.INDICES.index(3)
        support_name=f'support-{index:03d}.npz'
        save_arrays(source/support_name,dict(vertices=surface.vertices,faces=surface.faces,**surface.face_attributes))
        checkpoint=dict(supports=[{}for _ in m.INDICES],outputs_sha256={support_name:m.sha(source/support_name)})
        checkpoint['supports'][index]=dict(peripheral_skin=block.skinCoverage,grid_coverage=block.gridCoverage)
        policy=self.root/'old-policy.py';policy.write_text('synthetic')
        keys=('envelopes','regions','skins','grids','contacts','collisions')
        def old_seal(directory,cp,store):
            fixture.calls.append('original_seal');cp['admission_runtime_hooks']=deepcopy(consumer.RUNTIME_HOOKS);cp['admission']={}
            for key in keys:
                name='admission-'+key+'.json';receipt=dict(passed=True,admission_runtime_hooks=consumer.RUNTIME_HOOKS)
                if key=='contacts':receipt['actual_material_connection_graphs']=[dict(region=index,passed=True,receipt=deepcopy(cp['supports'][index]['peripheral_skin']['material_connection_graph']))]
                m.write(directory/name,receipt)
                cp['admission'][key]=dict(receipt=name,receipt_sha256=m.sha(directory/name))
            m.write(directory/'support-stage.json',cp);return cp['admission'],True
        def old_verify(directory):
            fixture.calls.append('original_six_verify');cp=json.loads((Path(directory)/'support-stage.json').read_text())
            if set(cp['admission'])!=set(keys):raise ValueError('Original six-gate list rejected')
            for item in cp['admission'].values():
                p=Path(directory)/item['receipt'];d=json.loads(p.read_text())
                if m.sha(p)!=item['receipt_sha256']or d.get('passed')is not True or d.get('admission_runtime_hooks')!=consumer.RUNTIME_HOOKS:
                    raise ValueError('Original six-gate hook rejected')
            return cp
        def old_restore(prior,out,result,supports_only):
            fixture.calls.append('original_restore');target=json.loads((Path(prior)/'support-stage.json').read_text());target.pop(m.KEY)
            target['outputs_sha256']={support_name:target['outputs_sha256'][support_name]}
            m.write(Path(out)/'support-stage.json',target);return result
        v5=NS(POLICY_FILES=(policy,),POLICY_SHA256={policy:m.sha(policy)},_base=NS(),RUNTIME_HOOKS={})
        consumer=NS(_v5=v5,POLICY_SHA256={policy:m.sha(policy)},RUNTIME_HOOKS={},_prepared=lambda:None,
            seal=old_seal,verify_v6_stage=old_verify,_restore_execution=old_restore)
        m.install(consumer,fixture.capsule,NS(load=lambda p,**k:Data(p)),fixture.graph,fixture.check_graph)
        self.assertIs(consumer._v5._base.seal,consumer.seal)
        consumer.seal(source,checkpoint,None);consumer.verify_v6_stage(source)
        target=self.root/'full';target.mkdir()
        for name in [support_name,*[i['receipt']for i in checkpoint['admission'].values()]]:shutil.copyfile(source/name,target/name)
        report=dict(outputs_sha256={support_name:m.sha(target/support_name)})
        result=consumer._restore_execution(source,target,report,False)
        self.assertEqual(result['outputs_sha256']['support-stage.json'],m.sha(target/'support-stage.json'))
        self.assertTrue(set(fixture.capsule.binding()['files_sha256'])<=set(result['outputs_sha256']))
        consumer.verify_v6_stage(target);self.assertEqual(fixture.graph_calls,1)
        cp=json.loads((target/'support-stage.json').read_text());skin=cp['supports'][index]['peripheral_skin']
        original_graph=deepcopy(skin['material_connection_graph'])
        skin['material_connection_graph']['seconds']=999.;skin['material_connection_graph']['positive_intersection_witnesses']=[dict(forged=True)]
        skin[m.KEY]['material_graph_sha256']=m.identity(skin['material_connection_graph']);m.write(target/'support-stage.json',cp)
        with self.assertRaisesRegex(ValueError,'complete graph differs'):consumer.verify_v6_stage(target)
        skin['material_connection_graph']=original_graph;skin[m.KEY]['material_graph_sha256']=m.identity(original_graph);m.write(target/'support-stage.json',cp)
        consumer.verify_v6_stage(target)
        cp=json.loads((target/'support-stage.json').read_text());item=cp['admission']['contacts'];p=target/item['receipt']
        receipt=json.loads(p.read_text());receipt['admission_runtime_hooks'].pop(m.KEY);m.write(p,receipt)
        item['receipt_sha256']=m.sha(p);m.write(target/'support-stage.json',cp)
        with self.assertRaisesRegex(ValueError,'Original six-gate hook'):consumer.verify_v6_stage(target)

    def test_python_capsule_files_must_equal_runtime_helpers(self):
        (self.root/'topology-producer.py').write_text('must be .py.txt unless explicitly runtime')
        with self.assertRaisesRegex(ValueError,'Runtime helpers'):self.f.reseal()


if __name__=='__main__':
    before=set(sys.modules);result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    if any(n.split('.')[0]in {'numpy','shapely','trimesh','pyslm'}for n in set(sys.modules)-before):raise AssertionError('AM imported by stdlib tests')
    report=dict(status='synthetic_private_consumer_guards_passed'if result.wasSuccessful()else'failed',tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),source_sha256=m.sha(HERE/'certified_support_consumer.py'),
        selfcheck_sha256=m.sha(__file__),synthetic_arrays_not_real_NPZ=True,AM_imported=False,real_graph_or_remap_executed=False,
        real_capsule_available=False,global_admission=False)
    with (HERE/'selfcheck-assessment.json').open('x')as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps(report));raise SystemExit(0 if result.wasSuccessful()else 1)
