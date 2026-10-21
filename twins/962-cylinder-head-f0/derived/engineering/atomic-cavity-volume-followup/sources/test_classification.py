"""Root-only synthetic NumPy tests of the actual reader function; no Gmsh import."""
import ast
from pathlib import Path
import unittest
import numpy as np
from poorcell_reference import classify as scalar_reference

SOURCE=Path(__file__).with_name('reader.py')
TREE=ast.parse(SOURCE.read_text())
FUNCTION=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='classify_positive_poor_chunk')
NAMESPACE={'np':np}
exec(compile(ast.Module(body=[FUNCTION],type_ignores=[]),str(SOURCE),'exec'),NAMESPACE)
CLASSIFY=NAMESPACE['classify_positive_poor_chunk']


class ActualClassification(unittest.TestCase):
 def check_reference(self,values,tags,rows,chunk=2):
  expected_counts,expected_indices=scalar_reference(values,tags,rows,4)
  counts={str(k):0 for k in range(5)};reps={}
  q=np.asarray(values,dtype=np.float64);et=np.asarray(tags,dtype=np.uint64)
  en=np.asarray(rows,dtype=np.uint64).reshape((-1,4))
  for offset in range(0,len(q),chunk):
   CLASSIFY(q[offset:offset+chunk],et[offset:offset+chunk],en[offset:offset+chunk],offset,4,counts,reps)
  if not len(q):CLASSIFY(q,et,en,0,4,counts,reps)
  self.assertEqual(counts,expected_counts)
  self.assertEqual({k:v['native_array_index'] for k,v in reps.items()},expected_indices)
  self.assertTrue(all(type(v) is int for v in counts.values()))
  for k,v in reps.items():
   i=expected_indices[k]
   self.assertEqual((v['SICN'],v['tetrahedron_tag']),(values[i],tags[i]))
   self.assertEqual(v['original_boundary_node_count'],int(k))
   self.assertEqual(v['interior_node_count'],4-int(k))

 def test_complete_all_boundary_mixed_and_interior_bins(self):
  rows=[(5,6,7,8),(1,5,6,7),(1,2,5,6),(1,2,3,5),(1,2,3,4)]
  self.check_reference([.05]*5,[10,11,12,13,14],rows)

 def test_minimum_then_tag_ties_across_chunks(self):
  self.check_reference([.04,.03,.03,.05],[5,9,2,1],[(1,2,3,4)]*4)

 def test_empty(self):self.check_reference([],[],[])

 def test_strict_thresholds(self):
  self.check_reference([0,.1,-.1,.05],[1,2,3,4],[(1,2,3,4)]*4)

 def test_nonfinite_values_refused_without_counter_changes(self):
  for value in [float('nan'),float('inf'),float('-inf')]:
   counts={str(k):0 for k in range(5)}
   with self.assertRaises(ValueError):CLASSIFY(np.array([value]),np.array([1]),np.array([[1,2,3,4]]),0,4,counts,{})
   self.assertEqual(counts,{str(k):0 for k in range(5)})

 def test_boundary_and_counters_require_exact_integers(self):
  for boundary in [True,4.,0]:
   with self.assertRaises(ValueError):CLASSIFY(np.array([.05]),np.array([1]),np.array([[1,2,3,4]]),0,boundary,{str(k):0 for k in range(5)},{})
  for invalid in [True,1.,-1]:
   counts={str(k):0 for k in range(5)};counts['4']=invalid
   with self.assertRaises(ValueError):CLASSIFY(np.array([.05]),np.array([1]),np.array([[1,2,3,4]]),0,4,counts,{})

 def test_misaligned_or_noninteger_node_rows_refused(self):
  for rows in [np.array([[1,2,3]]),np.array([[1.,2.,3.,4.]])]:
   with self.assertRaises(ValueError):CLASSIFY(np.array([.05]),np.array([1]),rows,0,4,{str(k):0 for k in range(5)},{})
  with self.assertRaises(ValueError):CLASSIFY(np.array([True]),np.array([1]),np.array([[1,2,3,4]]),0,4,{str(k):0 for k in range(5)},{})


if __name__=='__main__':unittest.main()
