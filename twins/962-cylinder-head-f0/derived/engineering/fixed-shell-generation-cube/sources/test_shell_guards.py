"""Prepared stdlib/AST guards only; no NumPy, Gmsh or worker import."""
from pathlib import Path
from fractions import Fraction
import ast,math,struct,unittest
from types import SimpleNamespace
from unittest.mock import Mock

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'reader.py'
HELPER=ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py'
TREE=ast.parse(SOURCE.read_text())
def function(name,**values):
 node=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name==name)
 namespace=dict(Fraction=Fraction,math=math,**values)
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),namespace)
 return namespace[name]
def literal():
 tree=ast.parse(HELPER.read_text());assign={n.targets[0].id:n.value for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)}
 points=ast.literal_eval(assign['P'].args[0]);faces=[[x+1 for x in row] for row in ast.literal_eval(assign['F'].left.args[0])]
 return points,faces

class ShellGuards(unittest.TestCase):
 def test_known_bound_literal_closed_volume(self):
  points,faces=literal();result=function('validate_shell')(points,faces)
  self.assertEqual(result,dict(vertices=8,faces=12,edges=18,signed_volume_mm3=343))

 def test_missing_and_reversed_faces_refuse_before_native_construction(self):
  points,faces=literal();validate=function('validate_shell');construct=function('construct_shell',validate_shell=validate)
  for bad in [faces[:-1],[faces[0][::-1],*faces[1:]]]:
   gmsh=Mock();helper=SimpleNamespace(P=SimpleNamespace(tolist=lambda:points),F=SimpleNamespace(tolist=lambda:bad))
   with self.assertRaises(ValueError):construct(gmsh,helper)
   self.assertEqual(gmsh.mock_calls,[])

 def test_boundary_bit_classification_and_face_drift_refuse(self):
  check=function('require_boundary_same');before=dict(coordinate_bytes=struct.pack('<d',0.),tagged_oriented_triangles=[(1,(1,2,3))],classifications=[(1,(2,1))])
  check(before,dict(before))
  for key,value in [('coordinate_bytes',struct.pack('<d',-0.)),('classifications',[(1,(3,1))]),('tagged_oriented_triangles',[(1,(1,3,2))])]:
   after=dict(before);after[key]=value
   with self.assertRaises(ValueError):check(before,after)

 def test_held_authority_refuses_before_paths_or_imports(self):
  check=function('require_authority')
  with self.assertRaises(ValueError):check(dict(native_execution_authorized=False))

 def test_one_generation_no_optimizer_and_unchanged_helper_calls(self):
  names={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}
  calls=[n for n in ast.walk(TREE) if isinstance(n,ast.Call)]
  self.assertEqual(sum(isinstance(n.func,ast.Attribute) and n.func.attr=='generate' for n in calls),1)
  self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr in ['optimize','createGeometry'] for n in calls))
  for name in ['inspect_live','require_same','quality_gate']:
   self.assertTrue(any(isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='helper' and n.func.attr==name for n in calls))
  loader=ast.get_source_segment(SOURCE.read_text(),names['load_audit_helper'])
  self.assertIn('helper.gmsh=gmsh',loader)
  self.assertNotIn('helper.main(',SOURCE.read_text());self.assertNotIn('helper.require_contract(',SOURCE.read_text())

if __name__=='__main__':unittest.main()
