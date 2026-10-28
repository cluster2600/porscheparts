"""Prepared stdlib synthetic metadata/setter guards; no scientific imports or mesh reads."""
from pathlib import Path
from fractions import Fraction
from types import SimpleNamespace
import ast,copy,struct,math

source=Path(__file__).with_name('reader.py');tree=ast.parse(source.read_text())
constants={'ARRAYS','WORKER','ARRAYS_SHA','WORKER_SHA','SHELL','FREE','AUDIT_INPUTS','COUNTS'}
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['candidate_rows','apply_once','require_applied_state','require_authority']
          or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
ns=dict(Path=Path,Fraction=Fraction,struct=struct,math=math,ROOT=source.resolve().parents[3])
exec(compile(ast.Module(body=selected,type_ignores=[]),str(source),'exec'),ns)

def refuses(fn,*args):
 try:fn(*args)
 except ValueError:return
 raise AssertionError('Expected refusal')

# Metadata-only stand-in, not an asserted geometric/quality fixture.
tags=list(range(1,17))+[27,28,29]
a=dict(node_tags=tags,coordinates_mm=[[float(t),-0.,0.] for t in tags],
       tetra_tags=list(range(1,40)),tetra_node_tags=[[1,2,3,27] for _ in range(39)])
coords=[list(row) for row in a['coordinates_mm']];coords[-2][0]+=.25;coords[-1][0]+=.5
qualification=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
                   engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
d=dict(status='exact_feasible_point_solver_converged_native_unapproved',all39_exact_quality_gate=True,
 procedural_checks_passed=True,all16_shell_coordinate_bits_unchanged=True,original_array_bits_unchanged=True,
 free_tags=[27,28,29],full_source_nodes=19,full_cells=39,qualification=qualification,
 input_hashes={str(ns['ROOT']/name):digest for name,digest in [(ns['ARRAYS'],ns['ARRAYS_SHA']),(ns['WORKER'],ns['WORKER_SHA']),(ns['SHELL'],ns['AUDIT_INPUTS'][ns['SHELL']])]},
 complete_proposed_coordinate_rows=[dict(node_tag=t,coordinates_mm=p,binary64_hex=[v.hex() for v in p]) for t,p in zip(tags,coords)],
 all39_signed_quality_rows=[dict(tetrahedron_tag=t,ordered_node_tags=row,positive_orientation=True,exact_point1_gate_passed=True,
  exact_native_ordered_determinant_mm3={'numerator':'1','denominator':'1'},exact_SICN_squared={'numerator':'1','denominator':'1'}) for t,row in zip(a['tetra_tags'],a['tetra_node_tags'])])
expected,changes=ns['candidate_rows'](d,a)
assert expected==coords and changes==[28,29]  # Identity27 is retained, not called a coordinate change.
bad=copy.deepcopy(d);bad['complete_proposed_coordinate_rows'][0]['coordinates_mm'][1]=0.;bad['complete_proposed_coordinate_rows'][0]['binary64_hex'][1]=0..hex()
refuses(ns['candidate_rows'],bad,a)
bad=copy.deepcopy(d);bad['all39_signed_quality_rows'][0]['ordered_node_tags']=[1,3,2,27];refuses(ns['candidate_rows'],bad,a)
bad=copy.deepcopy(d);bad['all39_exact_quality_gate']=False;refuses(ns['candidate_rows'],bad,a)
bad=copy.deepcopy(d);bad['complete_proposed_coordinate_rows'][-1]['binary64_hex'][0]='0x0.0p+0';refuses(ns['candidate_rows'],bad,a)

# Attempts increment before the API, including a throwing first setter.
counts={'setNode':0,'rebuildElementCache':0};calls=[]
class Mesh:
 def setNode(self,tag,xyz,param):calls.append((tag,xyz,param,counts['setNode']))
 def rebuildElementCache(self,value):assert value is False;calls.append(('cache',counts['rebuildElementCache']))
ns['apply_once'](SimpleNamespace(model=SimpleNamespace(mesh=Mesh())),coords,counts)
assert [v[0] for v in calls]==[27,28,29,'cache'] and counts=={'setNode':3,'rebuildElementCache':1}
counts={'setNode':0,'rebuildElementCache':0}
class Throwing:
 def setNode(self,*args):assert counts['setNode']==1;raise RuntimeError('synthetic setter failure')
try:ns['apply_once'](SimpleNamespace(model=SimpleNamespace(mesh=Throwing())),coords,counts)
except RuntimeError:pass
else:raise AssertionError('Throwing setter must propagate')
assert counts=={'setNode':1,'rebuildElementCache':0}

# Full candidate coordinate bits, connectivity and all classification metadata are bound.
report={'node_classifications':[[t,2 if t<=16 else 3] for t in tags],
 'node_entity_classifications':[[t,2 if t<=16 else 3,1] for t in tags],
 'node_counts_by_classification_dimension':{'2':16,'3':3},'no_curve_or_surface_periodic_mapping':True,'periodic_entities_checked':[[2,1]]}
post=copy.deepcopy(a);post['coordinates_mm']=copy.deepcopy(coords)
ns['require_applied_state']((report,a),(report,post),coords)
bad=copy.deepcopy(post);bad['coordinates_mm'][0][1]=0.;refuses(ns['require_applied_state'],(report,a),(report,bad),coords)
bad=copy.deepcopy(post);bad['tetra_node_tags'][0]=[1,3,2,27];refuses(ns['require_applied_state'],(report,a),(report,bad),coords)
classes=copy.deepcopy(report);classes['node_entity_classifications'][-1][-1]=2;refuses(ns['require_applied_state'],(report,a),(classes,post),coords)
refuses(ns['require_authority'],{})  # before any helper/native import or geometry read
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ['generate','optimize','createGeometry'] for n in ast.walk(tree))
runner=ast.parse(source.with_name('run_readback.py').read_text())
declaration=next(k.value for n in ast.walk(runner) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict' for k in n.keywords if k.arg=='declared_operation_counts')
assert ast.literal_eval(declaration)==ns['COUNTS']
print('PASS: candidate/tag/hex/fixed-bit guards, attempted setters, cache and full-state associations')
