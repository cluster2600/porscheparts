"""Stdlib-only AST tests for the single worker.after projection/comparison."""
import ast,copy,hashlib,json
from pathlib import Path
import unittest

PREP=Path(__file__).resolve().parent;SOURCE=PREP/'reader.py';SOURCE_SHA='65fe8215e9d96100bde76a1ec659d253102e5c3db2ec8ab12cca3f98e8629560'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Frozen diagnosis source changed before AST selection')
TREE=ast.parse(SOURCE.read_text());FUNCTIONS={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}
NS={};exec(compile(ast.Module(body=[FUNCTIONS['optimizer_after_proof'],FUNCTIONS['require_after_match']],type_ignores=[]),str(SOURCE),'exec'),NS)

class ProofGuards(unittest.TestCase):
 def context(self):
  stat=dict(count=3,minimum=.01,maximum=.9,p01=.02,p05=.03,p50=.4,p95=.8,p99=.85,nonpositive_count=0)
  quality={name:{**stat,**({'array_sha256':str(i)*64} if i<4 else {})} for i,name in enumerate(['minimum_jacobian','native_volume_mm3','minimum_SICN','independent_signed_volume_mm3'],1)}
  quality['minimum_SICN']['below_point1_count']=1
  proof=dict(tetrahedra=3,total_mesh_nodes=6,tetra_referenced_nodes=6,tetra_referenced_interior_nodes=2,unreferenced_mesh_nodes=0,quality=quality,summed_tetra_volume_mm3=1.,volume_relative_error=0.,array_sha256s={name:'a'*64 for name in ['sorted_node_tags_sha256','sorted_coordinates_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256']})
  worker=dict(optimizer_returned=True,element_cache_refresh_completed=True,saved_mesh_identity_exact=True,mesh_sha256='b'*64,mesh_bytes=123,candidate_sha256='c'*64,after=proof,before={'not_the_after_proof':True})
  receipt=dict(returncode=2,stop_reason=None,bound_inputs_unchanged=True,worker_report=worker,mesh_sha256='b'*64,mesh_bytes=123)
  contract=dict(MSH_sha256='b'*64,MSH_bytes=123,candidate_sha256='c'*64,expected_positive_poor_total=1,diagnostic_maximum_nonpositive_cells=0)
  report=dict(actual_mesh_nodes=6,actual_tetrahedra=3,actual_tetra_referenced_nodes=6,actual_unreferenced_mesh_nodes=0,actual_referenced_interior_nodes=2,direct_native_quality_extrema={name:copy.deepcopy(quality[key]) for name,key in [('SICN','minimum_SICN'),('Jacobian','minimum_jacobian'),('native_volume_mm3','native_volume_mm3')]},independent_signed_volume_mm3={**quality['independent_signed_volume_mm3'],'sum':1.,'relative_error_to_candidate':0.},positive_poor_SICN_cells={'total':1})
  return worker,receipt,contract,proof,report

 def test_valid_single_nested_after_and_complete_direct_match(self):
  w,r,c,p,observed=self.context();self.assertIs(NS['optimizer_after_proof'](w,r,c),w['after'])
  NS['require_after_match'](observed,p,1)

 def test_saved_identity_and_optimized_after_baseline_are_required(self):
  for owner,key,value in [('worker','saved_mesh_identity_exact',False),('worker','optimizer_returned',False),('worker','element_cache_refresh_completed',False),('receipt','stop_reason','deadline'),('receipt','bound_inputs_unchanged',False),('receipt','returncode',0),('worker','mesh_sha256','d'*64)]:
   with self.subTest(key=key):
    w,r,c,p,o=self.context();(w if owner=='worker' else r)[key]=value
    with self.assertRaises(ValueError):NS['optimizer_after_proof'](w,r,c)
  for field,value in [('count',True),('count',2),('nonpositive_count',False)]:
   w,r,c,p,o=self.context();p['quality']['minimum_SICN'][field]=value
   with self.assertRaises(ValueError):NS['optimizer_after_proof'](w,r,c)
  w,r,c,p,o=self.context();p['array_sha256s'].pop('sorted_node_tags_sha256')
  with self.assertRaises(ValueError):NS['optimizer_after_proof'](w,r,c)

 def test_every_native_metric_hash_count_and_distribution_must_match(self):
  for name in ['SICN','Jacobian','native_volume_mm3']:
   for field,value in [('array_sha256','f'*64),('count',4),('minimum',.001),('maximum',1.),('p01',.1),('p05',.1),('p50',.1),('p95',.1),('p99',.1),('nonpositive_count',1)]:
    with self.subTest(metric=name,field=field):
     w,r,c,p,o=self.context();o['direct_native_quality_extrema'][name][field]=value
     with self.assertRaises(ValueError):NS['require_after_match'](o,p,1)
  w,r,c,p,o=self.context();o['direct_native_quality_extrema']['SICN']['below_point1_count']=2
  with self.assertRaises(ValueError):NS['require_after_match'](o,p,1)

 def test_signed_volume_reference_counts_and_partition_cannot_drift(self):
  for field in ['count','minimum','maximum','p01','p05','p50','p95','p99','nonpositive_count','sum','relative_error_to_candidate']:
   with self.subTest(field=field):
    w,r,c,p,o=self.context();o['independent_signed_volume_mm3'][field]+=1
    with self.assertRaises(ValueError):NS['require_after_match'](o,p,1)
  for field in ['actual_mesh_nodes','actual_tetrahedra','actual_tetra_referenced_nodes','actual_unreferenced_mesh_nodes','actual_referenced_interior_nodes']:
   w,r,c,p,o=self.context();o[field]=True
   with self.assertRaises(ValueError):NS['require_after_match'](o,p,1)
  w,r,c,p,o=self.context();o['positive_poor_SICN_cells']['total']=2
  with self.assertRaises(ValueError):NS['require_after_match'](o,p,1)

 def test_exact_reverse_classifier_and_unchanged_runner(self):
  record=json.loads((PREP/'source-delta.json').read_text());text=SOURCE.read_text()
  for row in reversed(record['reader']['replacements']):
   self.assertEqual(text.count(row['new']),1);text=text.replace(row['new'],row['old'],1)
  self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),'c44eed3f69c83d6f774300634e27f3df90c4a4f699d5787519639e4c3b1fe891')
  before=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='classify_positive_poor_chunk')
  self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(FUNCTIONS['classify_positive_poor_chunk'],include_attributes=False))
  self.assertEqual(hashlib.sha256((PREP/'run_readback.py').read_bytes()).hexdigest(),'4fb37080e1f3847b8b1d14d5df467799d8e9f7bf81b0a09170e5850857de3943')

if __name__=='__main__':unittest.main()
