"""Stdlib/AST-only Netgen delta guards; no scientific/prepared module import."""
import ast,bisect,copy,hashlib,json,struct,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
PREP=Path(__file__).resolve().parent;ROOT=PREP.parents[2]
SOURCE=PREP/'mesh_delaunay_netgen_postexport.py'
SOURCE_SHA='0d1dd1f0625275343f16b713dae2d41143dda8da974bef42e59f6bfa3b0e388a'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Frozen source changed')
TEXT=SOURCE.read_text();TREE=ast.parse(TEXT)
FN={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}
def functions(names,ns):
 exec(compile(ast.Module(body=[FN[n] for n in names],type_ignores=[]),str(SOURCE),'exec'),ns)
 return ns
class Vector:
 dtype='uint64'
 def __init__(self,values):self.values=list(values)
 def __len__(self):return len(self.values)
 def __ge__(self,n):return [v>=n for v in self.values]
 def __getitem__(self,i):return Vector(self.values[k] for k in i.values) if isinstance(i,Vector) else self.values[i]
 def tobytes(self):return b''.join(struct.pack('<Q',v) for v in self.values)
class Rows:
 def __init__(self,values):self.values=[list(row) for row in values]
 def __len__(self):return len(self.values)
 def __getitem__(self,i):return Rows(self.values[k] for k in i.values) if isinstance(i,Vector) else self.values[i]
 def tobytes(self):return b''.join(struct.pack('<d',v) for row in self.values for v in row)
class TinyNP:
 any=staticmethod(any)
 @staticmethod
 def arange(start,stop,dtype=None):return Vector(range(start,stop))
 @staticmethod
 def searchsorted(tags,expected):return Vector(bisect.bisect_left(tags.values,v) for v in expected.values)
 @staticmethod
 def array_equal(a,b):return a.values==b.values
 @staticmethod
 def ascontiguousarray(a):return a
class NetgenDeltaGuards(unittest.TestCase):
 def context(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name).resolve()
  prior=ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001'
  diagnosis=ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-optimized-diagnosis-001/readback-report.json'
  worker=json.loads((prior/'worker-report.json').read_text());receipt=json.loads((prior/'receipt.json').read_text());diag=json.loads(diagnosis.read_text())
  for name,value in [('worker.json',worker),('receipt.json',receipt),('diagnosis.json',diag)]:
   (root/name).write_text(json.dumps(value))
  fresh=copy.deepcopy(worker['after']);fresh['classifications'].update(boundary_node_classification_dimensions_sha256='1'*64,boundary_node_classification_entity_tags_sha256='2'*64)
  identity={'source_tags':'frozen','source_bits':'frozen','class':'frozen'};state=('q','nt','et','en')
  ns=dict(ROOT=root,INPUT=root/'input.msh',INPUT_WORKER='worker.json',INPUT_RECEIPT='receipt.json',INPUT_READBACK='diagnosis.json',
   INPUT_HASHES={'input.msh':worker['mesh_sha256'],'worker.json':hashlib.sha256((prior/'worker-report.json').read_bytes()).hexdigest(),'diagnosis.json':hashlib.sha256(diagnosis.read_bytes()).hexdigest()},json=json,
   audit_after=lambda *a:(state,copy.deepcopy(fresh)),boundary_identity=lambda *a:copy.deepcopy(identity))
  functions(['current_after_proof','load_before','require_boundary_continuity','geometry_flag_only','optimize_and_refresh'],ns)
  return SimpleNamespace(root=root,worker=worker,receipt=receipt,diag=diag,fresh=fresh,identity=identity,state=state,ns=ns,core=SimpleNamespace(CANDIDATE_SHA=worker['candidate_sha256']))
 def rewrite(self,c):
  for name,value in [('worker.json',c.worker),('receipt.json',c.receipt),('diagnosis.json',c.diag)]:
   (c.root/name).write_text(json.dumps(value))
 def test_current_after_and_separate_completed_diagnosis_allow_rejected_input_baseline(self):
  c=self.context();state,report=c.ns['load_before'](c.core,object(),[],[])
  self.assertEqual(state,c.state);self.assertEqual(report['single_worker_field'],'after')
  self.assertFalse(report['older_first_pass_reader_alias_used']);self.assertTrue(report['fresh_full_input_incidence_and_metrics_completed'])
  self.assertFalse(report['prior_diagnosis_repeated_incidence']);self.assertFalse(report['input_baseline_SICN_point1_passed'])
  self.assertEqual(report['audit']['quality']['minimum_SICN']['below_point1_count'],3438)
  self.assertLess(report['audit']['quality']['minimum_SICN']['minimum'],.1)
  c.diag['single_optimized_worker_proof']['field']='audit';self.rewrite(c)
  with self.assertRaisesRegex(ValueError,'Single current'):c.ns['load_before'](c.core,object(),[],[])
 def test_fresh_arrays_counts_classification_and_every_metric_must_match_single_after(self):
  paths=[('array_sha256s',key) for key in self.context().fresh['array_sha256s']]
  paths += [('total_mesh_nodes',),('classifications','node_classification_dimensions_sha256')]
  paths += [('quality',name,key) for name,row in self.context().fresh['quality'].items() for key in row]
  for path in paths:
   with self.subTest(path=path):
    c=self.context();target=c.fresh
    for key in path[:-1]:target=target[key]
    old=target[path[-1]];target[path[-1]]='changed' if isinstance(old,str) else old+1
    with self.assertRaisesRegex(ValueError,'Fresh'):c.ns['load_before'](c.core,object(),[],[])
 def test_completed_diagnosis_native_arrays_counts_signed_volume_and_identity_are_bound(self):
  paths=[('status',),('bound_inputs_unchanged',),('actual_mesh_nodes',),('actual_tetrahedra',),('actual_referenced_interior_nodes',),('actual_unreferenced_mesh_nodes',),('single_optimized_worker_proof','worker_report_sha256')]
  paths += [(key,) for key in self.context().worker['after']['array_sha256s']]
  paths += [('direct_native_quality_extrema',name,key) for name,row in self.context().diag['direct_native_quality_extrema'].items() for key in row if row[key] is not None]
  paths += [('independent_signed_volume_mm3',key) for key in self.context().diag['independent_signed_volume_mm3']]
  paths += [('positive_poor_SICN_cells','total')]
  for path in paths:
   with self.subTest(path=path):
    c=self.context();target=c.diag
    for key in path[:-1]:target=target[key]
    old=target[path[-1]];target[path[-1]]=False if old is True else ('changed' if isinstance(old,str) else old+1)
    self.rewrite(c)
    with self.assertRaises(ValueError):c.ns['load_before'](c.core,object(),[],[])
 def test_dim3_only_geometry_flag_requires_noop_and_precedes_one_Netgen_cache_call(self):
  c=self.context();_,before=c.ns['load_before'](c.core,object(),[],[]);calls=[]
  gmsh=SimpleNamespace(model=SimpleNamespace(getEntities=lambda dim:[(3,1)],getBoundary=lambda *a,**k:[(2,1)],mesh=SimpleNamespace(
   createGeometry=lambda tags:calls.append(('create',tags)),optimize=lambda **kw:calls.append(('optimize',kw)),rebuildElementCache=lambda flag:calls.append(('cache',flag)))))
  report={};c.ns['geometry_flag_only'](c.core,gmsh,[],[],before,report,lambda:None)
  c.ns['optimize_and_refresh'](gmsh,report,lambda:None)
  self.assertEqual(calls,[('create',[(3,1)]),('optimize',{'method':'Netgen','force':True}),('cache',False)])
  self.assertTrue(report['geometry_flag_full_tagged_arrays_classifications_and_quality_identity_exact'])
  paths=[('array_sha256s','sorted_coordinates_sha256'),('classifications','node_classification_dimensions_sha256'),('quality','minimum_SICN','array_sha256')]
  for path in paths:
   with self.subTest(path=path):
    case=self.context();_,baseline=case.ns['load_before'](case.core,object(),[],[]);target=case.fresh
    for key in path[:-1]:target=target[key]
    target[path[-1]]='drift'
    with self.assertRaisesRegex(ValueError,'geometry flag changed'):case.ns['geometry_flag_only'](case.core,gmsh,[],[],baseline,{},lambda:None)
  for entities,shell in [([],[(2,1)]),([(3,1),(3,2)],[(2,1)]),([(3,1)],[])]:
   gmsh.model.getEntities=lambda dim:entities;gmsh.model.getBoundary=lambda *a,**k:shell
   with self.assertRaisesRegex(ValueError,'Exactly one volume'):c.ns['geometry_flag_only'](c.core,gmsh,[],[],before,{},lambda:None)
 def test_boundary_bits_and_classifications_fixed_with_dynamic_interiors_allowed(self):
  ns=functions(['boundary_identity','require_boundary_continuity'],{})
  core=SimpleNamespace(np=TinyNP,array_sha=lambda v:hashlib.sha256(v.tobytes()).hexdigest())
  points=Rows([[0.,0.,0.],[1.,0.,0.]])
  classification=dict(boundary_node_classification_dimensions_sha256='a',boundary_node_classification_entity_tags_sha256='b',no_curve_or_surface_periodic_mapping=True,periodic_entities_checked=[[2,1]])
  before=(Rows([[0.,0.,0.],[1.,0.,0.],[.5,.5,.5]]),Vector([1,2,10]),Vector([20]),'oldcells')
  after=(Rows([[0.,0.,0.],[1.,0.,0.],[.4,.4,.4],[.6,.6,.6]]),Vector([1,2,50,60]),Vector([90,91]),'newcells')
  a=ns['boundary_identity'](core,before,points,classification);b=ns['boundary_identity'](core,after,points,classification)
  ns['require_boundary_continuity'](a,b)
  for row in [[-0.,0.,0.],[2**-52,0.,0.]]:
   changed=(Rows([row,[1.,0.,0.],[.5,.5,.5]]),before[1],before[2],before[3])
   with self.assertRaisesRegex(ValueError,'Bitwise'):ns['boundary_identity'](core,changed,points,classification)
  for key in ['classification_dimensions_sha256','classification_entity_tags_sha256','periodic_entities_checked']:
   changed=copy.deepcopy(b);changed[key]='changed'
   with self.assertRaisesRegex(ValueError,'Original boundary'):ns['require_boundary_continuity'](a,changed)
 def test_reverse_reuse_and_changed_callers_keep_gates_and_no_generation(self):
  record=json.loads((PREP/'source-delta.json').read_text());text=TEXT
  for row in reversed(record['replacements']):
   self.assertEqual(text.count(row['new']),1);text=text.replace(row['new'],row['old'],1)
  self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),'ebb1f1ba8e7c0b032a4eb0178bbf8c332c68070816e6626f4a3f4788ed638527')
  old=ast.parse(text);oldfn={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)}
  self.assertEqual(ast.dump(FN['audit_after'],include_attributes=False),ast.dump(oldfn['audit_after'],include_attributes=False))
  calls=[n for n in ast.walk(FN['worker']) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
  order=[next(n.lineno for n in calls if n.func.id==name) for name in ['load_before','geometry_flag_only','optimize_and_refresh']]
  self.assertEqual(order,sorted(order));self.assertEqual(len(set(order)),3)
  self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='generate' for n in ast.walk(TREE)))
  self.assertIn('quality["minimum_SICN"]["minimum"]<.1',TEXT);self.assertIn('["volume_relative_error"]>1e-6',TEXT)
  self.assertNotIn('interior_node_coordinates_changed',TEXT);self.assertNotIn('canonical_volume_topology_changed',TEXT)
  self.assertIn('array_identity(core,(q,nt,et,en))!=report["after"]["array_sha256s"]',TEXT)
if __name__=='__main__':unittest.main()
