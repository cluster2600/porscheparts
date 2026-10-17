"""Prepared stdlib/AST guards; no scientific or prepared worker import."""
from pathlib import Path
import ast,copy,struct,unittest
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
SOURCE=HERE/'reader.py';TREE=ast.parse(SOURCE.read_text())
CUBE=ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py'

def extracted(tree,names,namespace):
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'<selected-stdlib-guard>','exec'),namespace)
 return namespace

def literal(name,tree=TREE):
 return ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)))

class SourceGuards(unittest.TestCase):
 def test_full_before_array_bits_classification_periodic_and_report_match(self):
  old=ast.parse(CUBE.read_text());ns=extracted(old,['snapshot','require_same'],{})
  helper=SimpleNamespace(require_same=ns['require_same'])
  check=extracted(TREE,['require_before'],{})['require_before']
  def live(value=0.):
   array=SimpleNamespace(dtype=SimpleNamespace(str='<f8'),shape=(1,),tobytes=lambda:struct.pack('<d',value))
   return ({'node_entity_classifications':[[1,2,1]],'periodic_entities_checked':[[2,1]],'extra_report_field':7},{},(array,)*5,(array,)*4)
  expected=live();check(helper,live(),expected)
  changed=[live(-0.)]
  for key,value in [('node_entity_classifications',[[1,3,1]]),('periodic_entities_checked',[]),('extra_report_field',8)]:
   item=live();item[0][key]=value;changed.append(item)
  for item in changed:
   with self.assertRaises(ValueError):check(helper,item,expected)

 def test_single_saved_rejected_baseline_is_required(self):
  check=extracted(TREE,['require_saved_baseline'],dict(INPUT_SHA=literal('INPUT_SHA'),ARRAYS_SHA=literal('ARRAYS_SHA')))['require_saved_baseline']
  baseline=dict(status='completed_specific_cavity_generation_only',fixture_procedural_checks_passed=True,
   actual_SICN_gate_passed=False,saved_mesh_identity_exact=True,bound_inputs_unchanged=True,
   mesh_sha256=literal('INPUT_SHA'),mesh_bytes=5646,full_tiny_arrays_sha256=literal('ARRAYS_SHA'),
   saved_reopen=dict(nodes=32,tetrahedra=57,referenced_interior_nodes=0,unreferenced_nodes=0,
    quality={'SICN':dict(count=57,below_point1_count=11,nonpositive_count=0,minimum=.009188807754622056)}))
  check(baseline)
  for key,value in [('actual_SICN_gate_passed',True),('mesh_sha256','0'*64),('bound_inputs_unchanged',False)]:
   changed=copy.deepcopy(baseline);changed[key]=value
   with self.assertRaises(ValueError):check(changed)
  changed=copy.deepcopy(baseline);changed['saved_reopen']['tetrahedra']=56
  with self.assertRaises(ValueError):check(changed)

 def test_held_authority_refuses_before_runtime_or_paths(self):
  check=extracted(TREE,['require_authority'],{})['require_authority']
  with self.assertRaises(ValueError):check({'native_execution_authorized':False})

 def test_exact_old_Netgen_policy_and_no_generation_or_old_main(self):
  self.assertEqual(literal('OPTIONS'),literal('OPTIONS',ast.parse(CUBE.read_text())))
  calls=[n for n in ast.walk(TREE) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
  self.assertEqual(sum(n.func.attr=='geometry_flag_only' for n in calls),1)
  self.assertEqual(sum(n.func.attr=='optimize_once' for n in calls),1)
  self.assertFalse(any(n.func.attr in ['generate','construct_shell','setNode','optimize','createGeometry'] for n in calls))
  self.assertFalse(any(isinstance(n.func.value,ast.Name) and n.func.value.id=='cavity' and n.func.attr in ['main','require_authority','require_contract'] for n in calls))
  self.assertIn('helper.require_same(live[\'after\'],live[\'saved_reopen\']',SOURCE.read_text())

if __name__=='__main__':unittest.main()
