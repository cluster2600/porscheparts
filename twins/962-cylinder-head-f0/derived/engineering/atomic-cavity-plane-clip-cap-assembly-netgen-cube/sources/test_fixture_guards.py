"""Unrun stdlib/AST tests of the actual Netgen fixture guards; no native imports."""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'reader.py'
SOURCE_SHA='97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Frozen fixture changed')
TREE=ast.parse(SOURCE.read_text())
FUNCTIONS={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}

def helpers():
 names=['snapshot','require_same','geometry_flag_only','optimize_once','quality_gate','require_contract']
 ns={'math':math,'Path':Path}
 exec(compile(ast.Module(body=[FUNCTIONS[n] for n in names],type_ignores=[]),str(SOURCE),'exec'),ns)
 return ns

class Bits:
 def __init__(self,values):
  self.values=values;self.dtype=SimpleNamespace(str='<f8');self.shape=(len(values),)
 def tobytes(self):return b''.join(struct.pack('<d',v) for v in self.values)
 def __getitem__(self,key):return self
 def __len__(self):return len(self.values)

def live():
 report={'node_entity_classifications':[[1,2,1],[9,3,1]],'periodic_entities_checked':[[2,1]]}
 return report,{},tuple(Bits([1.]) for _ in range(5)),tuple(Bits([.2]) for _ in range(4))

class FixtureGuards(unittest.TestCase):
 def test_exact_noop_geometry_flag_and_cache_order(self):
  ns=helpers();calls=[];counts={'createGeometry_dim3':0,'optimize_Netgen':0,'rebuildElementCache':0}
  mesh=SimpleNamespace(createGeometry=lambda x:calls.append(('geometry',x)),
   optimize=lambda **x:calls.append(('optimize',x)),rebuildElementCache=lambda x:calls.append(('cache',x)))
  gmsh=SimpleNamespace(model=SimpleNamespace(mesh=mesh,getEntities=lambda d:[(3,1)],getBoundary=lambda *a,**k:[(2,1)]))
  a=live();ns['geometry_flag_only'](gmsh,a,lambda:copy.deepcopy(a),counts);ns['optimize_once'](gmsh,counts)
  self.assertEqual(calls,[('geometry',[(3,1)]),('optimize',{'method':'Netgen','force':True}),('cache',False)])
  self.assertEqual(counts,{'createGeometry_dim3':1,'optimize_Netgen':1,'rebuildElementCache':1})
  for mutate in ['coordinate','quality','classification']:
   changed=copy.deepcopy(a)
   if mutate=='coordinate':changed[2][1].values[0]=2.
   elif mutate=='quality':changed[3][0].values[0]=.3
   else:changed[0]['node_entity_classifications'][0][1]=3
   with self.assertRaisesRegex(ValueError,'volume-only'):ns['geometry_flag_only'](gmsh,a,lambda:changed,counts)
   self.assertEqual(sum(c[0]=='optimize' for c in calls),1)

 def test_wrong_volume_or_empty_shell_refuses_before_geometry(self):
  ns=helpers();calls=[];counts={'createGeometry_dim3':0}
  for regions,shell in [([(3,2)],[(2,1)]), ([(3,1),(3,2)],[(2,1)]), ([(3,1)],[])]:
   gmsh=SimpleNamespace(model=SimpleNamespace(mesh=SimpleNamespace(createGeometry=lambda x:calls.append(x)),getEntities=lambda d:regions,getBoundary=lambda *a,**k:shell))
   with self.assertRaisesRegex(ValueError,'one region'):ns['geometry_flag_only'](gmsh,live(),lambda:live(),counts)
  self.assertEqual(calls,[]);self.assertEqual(counts['createGeometry_dim3'],0)

 def test_actual_boundary_bits_and_orphan_predicates(self):
  asserts=[n for n in ast.walk(FUNCTIONS['inspect_live']) if isinstance(n,ast.Assert)]
  boundary=next(n for n in asserts if 'coords[ix].tobytes()' in ast.unparse(n))
  orphan=next(n for n in asserts if ast.unparse(n.test)=='np.array_equal(referenced, tags)')
  np=SimpleNamespace(array_equal=lambda a,b:a==b)
  for value,passed in [(0.,True),(-0.,False),(2.**-1074,False)]:
   ns={'np':np,'tags':{0:[1]},'ix':0,'boundary':[1],'coords':Bits([value]),'P':Bits([0.])}
   code=compile(ast.Module(body=[boundary],type_ignores=[]),str(SOURCE),'exec')
   if passed:exec(code,ns)
   else:
    with self.assertRaises(AssertionError):exec(code,ns)
  code=compile(ast.Module(body=[orphan],type_ignores=[]),str(SOURCE),'exec')
  for tags in [[1,2,900],list(range(1,50))]:exec(code,{'np':np,'tags':tags,'referenced':tags[:]})
  with self.assertRaises(AssertionError):exec(code,{'np':np,'tags':[1,2,3],'referenced':[1,2]})
  self.assertNotIn(42,[n.value for n in ast.walk(FUNCTIONS['inspect_live']) if isinstance(n,ast.Constant)])

 def test_saved_reopen_requires_all_array_bits_and_classifications(self):
  ns=helpers();a=live();ns['require_same'](a,copy.deepcopy(a),'saved reopen')
  for index in range(4):
   changed=copy.deepcopy(a);changed[2][index].values[0]=2.
   with self.assertRaisesRegex(ValueError,'saved reopen'):ns['require_same'](a,changed,'saved reopen')
  a[2][1].values[0]=0.;b=copy.deepcopy(a);b[2][1].values[0]=-0.
  with self.assertRaises(ValueError):ns['require_same'](a,b,'saved reopen')
  b=copy.deepcopy(a);b[0]['periodic_entities_checked']=[]
  with self.assertRaises(ValueError):ns['require_same'](a,b,'saved reopen')

 def test_actual_metric_count_and_point_one_gate(self):
  ns=helpers();report={'tetrahedra':2,'quality':{'SICN':{'count':2,'minimum':.1,'below_point1_count':0}}}
  self.assertTrue(ns['quality_gate'](report))
  for key,value in [('count',1),('minimum',.099),('minimum',float('nan')),('minimum',float('inf')),('below_point1_count',1)]:
   bad=copy.deepcopy(report);bad['quality']['SICN'][key]=value;self.assertFalse(ns['quality_gate'](bad))
  predicate=next(n for n in ast.walk(FUNCTIONS['inspect_live']) if isinstance(n,ast.Assert) and ast.unparse(n.test).startswith('len(q) == len(et)'))
  np=SimpleNamespace(isfinite=lambda q:SimpleNamespace(all=lambda:all(math.isfinite(v) for v in q)))
  code=compile(ast.Module(body=[predicate],type_ignores=[]),str(SOURCE),'exec')
  exec(code,{'q':[1.,2.],'et':[10,20],'np':np})
  for values in [[1.],[1.,float('nan')]]:
   with self.assertRaises(AssertionError):exec(code,{'q':values,'et':[10,20],'np':np})

 def test_actual_contract_options_and_cube_only_authority(self):
  ns=helpers();constants={n.targets[0].id:ast.literal_eval(n.value) for n in TREE.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['INPUT','INPUT_SHA','OPTIONS','RUNTIME']}
  ns.update(constants,ROOT=Path('/frozen'),OUTPUT=Path('/frozen/cube'),OUT=Path('/frozen/cube'),sha=lambda p:'a'*64)
  c={'output_directory':'cube','native_execution_authorized':True,'head_execution_authorized':False,'input_mesh':constants['INPUT'],'input_mesh_sha256':constants['INPUT_SHA'],'options':constants['OPTIONS'],'expected_runtime':constants['RUNTIME'],'optimization':{'method':'Netgen','force':True},'geometry_creation_dim_tags':[[3,1]],'input_hashes':{},'external_runtime_hashes':{},'reader_sha256':'a'*64,'runner_sha256':'a'*64}
  ns['sha']=lambda p:constants['INPUT_SHA'] if p==ns['ROOT']/constants['INPUT'] else 'a'*64
  ns['require_contract'](c)
  for field,value in [('native_execution_authorized',False),('head_execution_authorized',True),('geometry_creation_dim_tags',[[2,1]]),('output_directory','stale')]:
   bad=copy.deepcopy(c);bad[field]=value
   with self.assertRaises(ValueError):ns['require_contract'](bad)
  bad=copy.deepcopy(c);bad['options']['Mesh.OptimizeThreshold']=.2
  with self.assertRaises(ValueError):ns['require_contract'](bad)

 def test_source_reuse_reversals_and_single_API_scope(self):
  root=HERE.parents[2];base=Path(root/'work/962-engineering/saved-cube-default-readback-001/reader.py').read_text();base_tree=ast.parse(base)
  original=ast.get_source_segment(base,next(n for n in base_tree.body if isinstance(n,ast.FunctionDef) and n.name=='inspect'))
  transformed=ast.get_source_segment(SOURCE.read_text(),FUNCTIONS['inspect_live'])
  record=json.loads((HERE/'inspect-transform.json').read_text())
  for old,new in reversed(record['ordered_exact_replacements']):self.assertEqual(transformed.count(new),1);transformed=transformed.replace(new,old)
  self.assertEqual(transformed,original)
  for name in ['canonical','distribution']:
   self.assertEqual(ast.dump(FUNCTIONS[name]),ast.dump(next(n for n in base_tree.body if isinstance(n,ast.FunctionDef) and n.name==name)))
  calls=[n for n in ast.walk(TREE) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
  self.assertEqual(sum(n.func.attr=='createGeometry' for n in calls),1);self.assertEqual(sum(n.func.attr=='optimize' for n in calls),1)
  self.assertEqual(sum(n.func.attr=='rebuildElementCache' for n in calls),1);self.assertFalse(any(n.func.attr=='generate' for n in calls))
  main=FUNCTIONS['main']
  self.assertTrue(any(isinstance(n,ast.Global) and 'gmsh' in n.names for n in main.body))
  self.assertTrue(any(isinstance(n,ast.Import) and any(alias.name=='gmsh' and alias.asname is None for alias in n.names) for n in main.body))
  self.assertTrue(any(isinstance(n,ast.Name) and n.id=='gmsh' and isinstance(n.ctx,ast.Load) for n in ast.walk(FUNCTIONS['inspect_live'])))
  runner=HERE/'run_readback.py';text=runner.read_text();record=json.loads((HERE/'runner-transform.json').read_text())
  for old,new in reversed(record['ordered_exact_replacements']):text=text.replace(new,old)
  self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),record['base_sha256'])
  self.assertIn('rss>=1024**3',runner.read_text());self.assertIn('max(0.,30-',runner.read_text());self.assertIn('sampled_output_stop_bytes=16*1024**2',runner.read_text())

if __name__=='__main__':unittest.main()
