"""UNRUN selected-AST interface guards and tiny selected-NumPy integer-key check; no Gmsh."""
from pathlib import Path
import ast, copy, hashlib, json
SOURCE_SHA='c59e0c14dd3e6ee9747168ac80f4284374ef62025fe4ec59e171f128ada2122a'
source=Path(__file__).with_name('reader.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA
tree=ast.parse(source.read_text());functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
ns={};names=['canonical','validate_interface','face_hits']
exec(compile(ast.fix_missing_locations(ast.Module(body=[functions[n] for n in names],type_ignores=[])),'<selected-interface-only>','exec'),ns)
expected={(1,2,3):[1,2,3],(4,5,6):[4,5,6]}
owners={(1,2,3):[{'removed_star_owner':True,'oriented_face':[2,3,1]},
                    {'removed_star_owner':False,'oriented_face':[1,3,2]}],
        (4,5,6):[{'removed_star_owner':True,'oriented_face':[4,5,6]}]}
triangles={(1,2,3):[],(4,5,6):[{'node_tags':[5,6,4]}]}
answer=ns['validate_interface'](expected,owners,triangles)
assert [r['interface_kind'] for r in answer]==['internal_with_outside_owner','parent_exterior']
def refuses(o,t):
 try:ns['validate_interface'](expected,o,t)
 except ValueError:return
 raise AssertionError('Expected complete interface refusal')
bad=copy.deepcopy(owners);bad[(1,2,3)][1]['oriented_face']=[1,2,3];refuses(bad,triangles)
bad=copy.deepcopy(owners);bad[(1,2,3)].append(copy.deepcopy(bad[(1,2,3)][1]));refuses(bad,triangles)
bad=copy.deepcopy(triangles);bad[(1,2,3)]=[{'node_tags':[1,2,3]}];refuses(owners,bad)
bad=copy.deepcopy(triangles);bad[(4,5,6)]=[];refuses(owners,bad)
bad=copy.deepcopy(owners);bad[(4,5,6)]=[];refuses(bad,triangles)
assert ns['canonical']([1,2,3])==ns['canonical']([3,1,2])!=ns['canonical']([1,3,2])
for node in ast.walk(tree):
 if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
  assert node.func.attr not in ['getElementQualities','generate','optimize','setNode','addNodes','addElementsByType','removeElements','createGeometry','reclassifyNodes']
  assert ast.unparse(node.func)!='gmsh.write'
# Root-only literal check of the actual NumPy integer face matcher, not a head query.
import numpy as np
assert np.__version__=='2.0.2'
assert Path(np.__file__).resolve()==Path('{SELECTED_CAD_NUMPY_ENV}/lib/python3.10/site-packages/numpy/__init__.py')
high=2**53+1;keys={(1,2,3),(7,8,9),(high,high+1,high+2)}
rows=np.asarray([[9,7,8],[1,2,3],[4,5,6],[3,2,1],[high+2,high,high+1]],dtype='<u8')
assert ns['face_hits'](np,rows,keys).tolist()==[0,1,3,4]
assert ns['face_hits'](np,np.empty((0,3),dtype='<u8'),keys).tolist()==[]
print(json.dumps({'status':'pass','scope':'Selected interface join refusals and literal uint64 face matching only; no Gmsh/head query/native mutation.'}))
