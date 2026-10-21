"""Prepared stdlib/AST guards only; no worker/scientific module import."""
from pathlib import Path
from fractions import Fraction
import ast,copy,json,math,struct,unittest
from unittest.mock import Mock

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'reader.py'
TREE=ast.parse(SOURCE.read_text())
SHELL=ROOT/'work/962-engineering/direct-sicn-apex1613031-cavity-study-001/local-shell-input-001.json'
VOLUME=Fraction(104308130846515511471660941377843352992235,1045347431181122959759486794030391945592832)

def function(name,**values):
 node=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name==name)
 namespace=dict(Fraction=Fraction,VOLUME=VOLUME,math=math,struct=struct,**values)
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),namespace)
 return namespace[name]

def shell():
 return json.loads(SHELL.read_text())

class ShellGuards(unittest.TestCase):
 def test_exact_mapping_bits_original_classes_and_volume(self):
  validate=function('validate_shell');rows=function('shell_rows',validate_shell=validate)
  points,faces,result=rows(shell())
  self.assertEqual((len(points),len(faces),result['edges']),(9,14,21))
  self.assertEqual(result['exact_volume_mm3'],dict(numerator=str(VOLUME.numerator),denominator=str(VOLUME.denominator)))

 def test_missing_and_reversed_faces_refuse_before_mesher(self):
  validate=function('validate_shell');rows=function('shell_rows',validate_shell=validate)
  construct=function('construct_shell',shell_rows=rows)
  for operation in ['missing','reversed']:
   data=shell()
   if operation=='missing':data['oriented_triangle_rows'].pop()
   else:data['oriented_triangle_rows'][0]['local_node_tags'].reverse()
   gmsh=Mock();helper=Mock()
   with self.assertRaises(ValueError):construct(gmsh,helper,data)
   self.assertEqual(gmsh.mock_calls,[]);self.assertEqual(helper.mock_calls,[])

 def test_coordinate_hex_inverse_and_original_classification_drift_refuse(self):
  rows=function('shell_rows',validate_shell=function('validate_shell'))
  changes=[lambda d:d['vertex_rows'][0]['binary64_hex'].__setitem__(0,'0x0.0p+0'),
           lambda d:d['global_to_local_node_tags'].__setitem__(str(d['local_to_global_node_tags'][0]),2),
           lambda d:d['vertex_rows'][5].__setitem__('original_source_boundary_node',True),
           lambda d:d['vertex_rows'][5].__setitem__('original_source_classification','below_dim3'),
           lambda d:d['original_source_classifications']['other_interior_local_node_tags'].pop()]
  for change in changes:
   data=shell();change(data)
   with self.assertRaises(ValueError):rows(data)

 def test_every_boundary_bit_face_and_classification_is_fixed(self):
  check=function('require_boundary_same')
  before=dict(coordinate_bytes=struct.pack('<d',0.),tagged_oriented_triangles=[(1,(1,2,3))],classifications=[(1,(2,1))])
  check(before,copy.deepcopy(before))
  for key,value in [('coordinate_bytes',struct.pack('<d',-0.)),('classifications',[(1,(3,1))]),('tagged_oriented_triangles',[(1,(1,3,2))])]:
   after=dict(before);after[key]=value
   with self.assertRaises(ValueError):check(before,after)

 def test_complete_metric_cardinality_finiteness_and_positive_volumes(self):
  check=function('check_metric_rows')
  check([.2,.3],2,'SICN');check([1.,2.],2,'native_volume_mm3')
  for values,count,name in [([.2],2,'SICN'),([],0,'SICN'),([float('nan')],1,'SICN'),([float('inf')],1,'Jacobian'),([0.],1,'native_volume_mm3'),([-1.],1,'independent_signed_volume_mm3')]:
   with self.assertRaises(ValueError):check(values,count,name)

 def test_held_authority_and_single_generation_source_scope(self):
  with self.assertRaises(ValueError):function('require_authority')(dict(native_execution_authorized=False))
  calls=[n for n in ast.walk(TREE) if isinstance(n,ast.Call)]
  self.assertEqual(sum(isinstance(n.func,ast.Attribute) and n.func.attr=='generate' for n in calls),1)
  self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr in ['optimize','createGeometry','setNode'] for n in calls))
  source=SOURCE.read_text()
  for token in ['helper.volume_arrays(gmsh)','helper.tetra_boundary(cells,source_indices)','helper.internal_face_orientation(cells)','helper.tetra_volumes(coords,cells)','helper.require_same(live[\'after_generation\'],live[\'saved_reopen\']']:
   self.assertIn(token,source)
  self.assertNotIn('helper.worker(',source);self.assertNotIn('helper.main(',source)

 def test_complete_positive_tight_screen_required_before_mesher(self):
  rows=function('shell_rows',validate_shell=function('validate_shell'))
  construct=function('construct_shell',shell_rows=rows)
  changes=[lambda d:d.__setitem__('status','DATA_ONLY_REJECTED_FIXED_SHELL_FACE_QUALITY'),
           lambda d:d.__setitem__('necessary_face_quality_passed',False),
           lambda d:d.__setitem__('generation_input_rejected_by_necessary_face_quality',True),
           lambda d:d.__setitem__('apex_not_in_shell_input',False),
           lambda d:d.__setitem__('declared_controller_command_conformant',True),
           lambda d:d.__setitem__('upstream_census_launch_deviation_sha256','0'*64)]
  for change in changes:
   data=shell();change(data);gmsh=Mock();helper=Mock()
   with self.assertRaises(ValueError):construct(gmsh,helper,data)
   self.assertEqual(gmsh.mock_calls,[]);self.assertEqual(helper.mock_calls,[])


if __name__=='__main__':unittest.main()
