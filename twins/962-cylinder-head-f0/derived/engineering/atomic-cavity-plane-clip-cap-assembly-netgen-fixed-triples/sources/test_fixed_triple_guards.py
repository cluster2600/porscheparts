"""Tiny stdlib/AST guards only; never import the reader, NumPy or Gmsh."""
import ast,hashlib,json,math,struct,unittest
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).with_name('reader.py')
SOURCE_SHA='aa62597659177cd40fa7f8e5aca840d9fed46856f09bd93c957200c98cbfbc82'
NAMES={'rational','certificate','tight_fixed_face_ceiling','fixed_triple_record','require_complete_fixed_triples'}


def functions():
 raw=SOURCE.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise ValueError('Exact new reader bytes required')
 tree=ast.parse(raw);selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in NAMES]
 if {n.name for n in selected}!=NAMES:raise ValueError('Only exact declared pure functions required')
 scope={'Fraction':Fraction,'math':math,'hashlib':hashlib,'struct':struct}
 exec(compile(ast.Module(body=selected,type_ignores=[]),'<fixed-triple-stdlib-functions>','exec'),scope)
 return scope


class Guards(unittest.TestCase):
 def test_regular_and_dyadic_sliver(self):
  f=functions();c=f['certificate'];ceiling=f['tight_fixed_face_ceiling']
  regular=ceiling(c([[0.,0,0],[1.,0,0],[0.,1.,0]]))
  self.assertFalse(regular['exact_isolated_apex_maximum_below_SICN_point1'])
  self.assertEqual(regular['exact_triangle_SICN_squared'],{'numerator':'3','denominator':'4'})
  poor=ceiling(c([[0.,0,0],[1.,0,0],[0.,2.**-20,0]]))
  self.assertTrue(poor['exact_isolated_apex_maximum_below_SICN_point1'])
  self.assertTrue(poor['decimal_values_are_not_interval_or_native_metric_certificates'])

 def test_tight_certificate_stricter_than_preserved_loose_one(self):
  f=functions();proof=f['certificate']([[0.,0,0],[1.,0,0],[0.,81/2048,0]])
  self.assertFalse(proof['no_positive_linear_tetrahedron_with_this_fixed_face_can_reach_SICN_point1'])
  self.assertTrue(f['tight_fixed_face_ceiling'](proof)['exact_isolated_apex_maximum_below_SICN_point1'])

 def test_exact_threshold_equality_and_invalid_quality(self):
  c=functions()['tight_fixed_face_ceiling']
  row=lambda q:{'exact_triangle_SICN_squared':{'numerator':str(q.numerator),'denominator':str(q.denominator)}}
  threshold=Fraction(4,841)
  equal=c(row(threshold));self.assertTrue(equal['exact_isolated_apex_maximum_equals_SICN_point1']);self.assertFalse(equal['exact_isolated_apex_maximum_below_SICN_point1'])
  self.assertTrue(c(row(threshold-Fraction(1,10**9)))['exact_isolated_apex_maximum_below_SICN_point1'])
  self.assertFalse(c(row(threshold+Fraction(1,10**9)))['exact_isolated_apex_maximum_below_SICN_point1'])
  for invalid in [Fraction(0),Fraction(-1),Fraction(2)]:
   with self.assertRaises(ValueError):c(row(invalid))

 def test_record_preserves_source_order_and_signed_zero_bits(self):
  f=functions()['fixed_triple_record'];xyz=[[-0.,0.,0.],[.2,.2,1.],[1.,0.,0.],[0.,1.,0.]]
  row=f(9,1000,.05,[1,100,2,3],xyz,3)
  self.assertEqual(row['fixed_node_local_positions'],[0,2,3]);self.assertEqual(row['fixed_triple_node_tags'],[1,2,3])
  self.assertEqual(row['interior_apex_local_position'],1);self.assertEqual(row['interior_apex_node_tag'],100)
  self.assertEqual(row['fixed_triple_binary64_hex'][0][0],'-0x0.0p+0')
  expected=hashlib.sha256(struct.pack('<9d',-0.,0.,0.,1.,0.,0.,0.,1.,0.)).hexdigest()
  self.assertEqual(row['fixed_triple_coordinate_bits_sha256'],expected)
  self.assertIsNone(row['exterior_surface_face_membership']);self.assertFalse(row['exterior_surface_membership_computed'])
  for tags,boundary,q in [([1,2,3,4],4,.05),([1,1,2,100],3,.05),([1,100,2,3],3,.1),([1,100,2,3],3,True)]:
   with self.assertRaises(ValueError):f(9,1000,q,tags,xyz,boundary)
  bad=[row[:] for row in xyz];bad[0][0]=float('nan')
  with self.assertRaises(ValueError):f(9,1000,.05,[1,100,2,3],bad,3)

 def test_full_partition_requires_all195_sorted_unique_rows(self):
  f=functions()['require_complete_fixed_triples'];counts={'0':0,'1':0,'2':15,'3':195,'4':0}
  prior={'status':'direct_saved_file_readback_completed','bound_inputs_unchanged':True,'positive_poor_SICN_cells':{'total':210,'by_original_boundary_node_count':counts.copy()}}
  rows=[{'tetrahedron_tag':i+1} for i in range(195)]
  f(rows,counts,prior,195)
  for wrong in [rows[:-1],list(reversed(rows)),rows[:-1]+[rows[0]]]:
   with self.assertRaises(ValueError):f(wrong,counts,prior,195)
  wrong=counts.copy();wrong['3']=194
  with self.assertRaises(ValueError):f(rows,wrong,prior,195)
  prior['bound_inputs_unchanged']=False
  with self.assertRaises(ValueError):f(rows,counts,prior,195)

 def test_full_inherited_guards_and_runner_are_unchanged(self):
  old=ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-optimized-diagnosis-prep-001/reader.py'
  self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(),'65fe8215e9d96100bde76a1ec659d253102e5c3db2ec8ab12cca3f98e8629560')
  maps=[]
  for p in (old,SOURCE):maps.append({n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_bytes()).body if isinstance(n,ast.FunctionDef)})
  for name in ['classify_positive_poor_chunk','optimizer_after_proof','require_after_match']:self.assertEqual(maps[0][name],maps[1][name])
  helper=ROOT/'twins/962-cylinder-head-f0/source/certify_fixed_face.py'
  original={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(helper.read_bytes()).body if isinstance(n,ast.FunctionDef)}
  for name in ['rational','certificate']:self.assertEqual(original[name],maps[1][name])
  self.assertEqual(hashlib.sha256(SOURCE.with_name('run_readback.py').read_bytes()).hexdigest(),'4fb37080e1f3847b8b1d14d5df467799d8e9f7bf81b0a09170e5850857de3943')


if __name__=='__main__':unittest.main()
