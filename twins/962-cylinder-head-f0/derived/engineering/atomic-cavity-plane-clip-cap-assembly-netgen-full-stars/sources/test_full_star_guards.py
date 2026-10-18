"""UNRUN stdlib/AST guards; never import the reader, NumPy, Gmsh or geometry."""
import ast
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).with_name('reader.py')
SOURCE_SHA='d978448ac685730c8ab1cf652dec23a00227eb5369869b89d6068017e678c5d5'
NAMES={'movable_from_poor_rows','incident_positions'}

def functions():
 raw=SOURCE.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise ValueError('Exact selected full-star reader required')
 selected=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in NAMES]
 if {n.name for n in selected}!=NAMES:raise ValueError('Both actual pure selection functions required')
 scope={}
 exec(compile(ast.Module(body=selected,type_ignores=[]),'<actual-full-star-selection>','exec'),scope)
 return scope

class Guards(unittest.TestCase):
 def test_complete_union_includes_initially_good_and_shared_rows(self):
  f=functions();poor=[[1,2,3,4],[1,2,4,5]]
  rows=poor+[[2,4,6,7],[1,4,5,7],[1,2,6,7]]
  movable=f['movable_from_poor_rows'](poor,[4,5,6,7],3)
  self.assertEqual(movable,[4,5])
  observed=f['incident_positions'](rows,movable)
  oracle=[i for i,row in enumerate(rows) if sum(int(a==b) for a in row for b in movable)>0]
  self.assertEqual(observed,oracle);self.assertEqual(observed,[0,1,2,3])
  self.assertEqual(len(set(observed)),4)
  self.assertEqual([i for i in observed if i>=len(poor)],[2,3])

 def test_input_row_order_does_not_change_movable_membership(self):
  f=functions();poor=[[5,2,4,1],[4,3,2,1]]
  self.assertEqual(f['movable_from_poor_rows'](poor,[4,5,6,7],3),[4,5])
  rows=[[1,2,6,7],[1,4,5,7],[2,4,6,7],*poor]
  self.assertEqual(f['incident_positions'](rows,[4,5]),[1,2,3,4])

 def test_empty_and_all_boundary_seed_cases(self):
  f=functions();self.assertEqual(f['movable_from_poor_rows']([],[],3),[])
  self.assertEqual(f['incident_positions']([],[]),[])
  self.assertEqual(f['movable_from_poor_rows']([[1,2,3,4]],[5],4),[])
  self.assertEqual(f['incident_positions']([[1,2,3,4]],[]),[])
  # The real main separately refuses any current poor cell not covered by a seed star.

 def test_invalid_boundary_classification_and_connectivity_refuse(self):
  f=functions();m=f['movable_from_poor_rows'];s=f['incident_positions']
  for boundary in [0,-1,True,3.0]:
   with self.assertRaises(ValueError):m([[1,2,3,4]],[4],boundary)
  for interior in [[3,4],[5,4],[4,4],[True],[4.0]]:
   with self.assertRaises(ValueError):m([[1,2,3,4]],interior,3)
  with self.assertRaises(ValueError):m([[1,2,3,5]],[4],3)
  for row in [[1,2,3],[1,2,3,0],[1,2,3,True],[1,2,2,4],[1,2,3,4.0]]:
   with self.assertRaises(ValueError):m([row],[4],3)
   with self.assertRaises(ValueError):s([row],[4])
  for movable in [[4,4],[5,4],[True],[0],[4.0]]:
   with self.assertRaises(ValueError):s([[1,2,3,4]],movable)

 def test_exact_reuse_reverse_and_read_only_call_scope(self):
  raw=SOURCE.read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),SOURCE_SHA)
  delta=json.loads(SOURCE.with_name('source-delta.json').read_bytes())
  old=(ROOT/delta['preserved_reader']).read_bytes()
  restored=raw.decode()
  for row in reversed(delta['exact_replacements']):
   self.assertEqual(restored.count(row['new']),1);restored=restored.replace(row['new'],row['old'])
  self.assertEqual(restored.encode(),old)
  newtree=ast.parse(raw);new={n.name:ast.dump(n,include_attributes=False) for n in newtree.body if isinstance(n,ast.FunctionDef)}
  oldmap={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)}
  for name,body in oldmap.items():self.assertEqual(new[name],body)
  captured=(ROOT/delta['classification_helper']['path']).read_bytes()
  self.assertEqual(hashlib.sha256(captured).hexdigest(),delta['classification_helper']['source_sha256'])
  helper=next(n for n in ast.parse(captured).body if isinstance(n,ast.FunctionDef) and n.name=='classifications')
  self.assertEqual(new['classifications'],ast.dump(helper,include_attributes=False))
  self.assertEqual(hashlib.sha256(SOURCE.with_name('run_readback.py').read_bytes()).hexdigest(),'4fb37080e1f3847b8b1d14d5df467799d8e9f7bf81b0a09170e5850857de3943')
  calls=[n.func.attr for n in ast.walk(newtree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
  for forbidden in ['generate','optimize','createGeometry','rebuildElementCache']:
   self.assertNotIn(forbidden,calls)
  native_calls=[ast.unparse(n.func) for n in ast.walk(newtree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
  self.assertNotIn('gmsh.write',native_calls)
  self.assertIn('complete_seed_star_census',raw.decode())

if __name__=='__main__':unittest.main()
