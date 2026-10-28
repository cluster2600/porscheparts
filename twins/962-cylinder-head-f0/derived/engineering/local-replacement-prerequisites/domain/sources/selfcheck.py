"""UNRUN stdlib selected-AST check; no saved candidate/native/scientific imports."""
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from types import SimpleNamespace
import ast,hashlib,math
SOURCE_SHA='0fe593d385e5a0ab4944528fa1b869ddf2c41c28d050576afe9be18213462296'
source=Path(__file__).with_name('certify_domain.py');assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA
tree=ast.parse(source.read_text());top={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
helper=source.parents[1]/'fixed-shell-coupled-embedding-prep-001/check_embedding.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='1b489cc8149f4b5db8f90c594e32fe4c09b5db00151df6b1cfc88362d1018134'
ht=ast.parse(helper.read_text());names=['rational','subtract','dot','cross','exact_quality','halfspaces','plane_vertex','in_shared_hull','pair_check']
selected=[n for n in ht.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'Fraction':Fraction,'combinations':combinations,'math':math}
exec(compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),'<frozen-pure-helper-AST>','exec'),ns)
faces=next(n for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='FACES')
exec(compile(ast.fix_missing_locations(ast.Module(body=[faces,top['cycle'],top['complex_rows']],type_ignores=[])),'<new-chain-AST>','exec'),ns)
api=SimpleNamespace(exact_quality=ns['exact_quality'],rational=ns['rational'])
points={1:(Fraction(0),Fraction(0),Fraction(0)),2:(Fraction(1),Fraction(0),Fraction(0)),3:(Fraction(0),Fraction(1),Fraction(0)),4:(Fraction(0),Fraction(0),Fraction(1))}
row=[1,2,3,4];shell=[[row[i] for i in f] for f in ns['FACES']]
a,va=ns['complex_rows'](api,points,{101:row},shell)
refined={**points,5:(Fraction(1,4),Fraction(1,4),Fraction(1,4))}
cells={201+i:[5]+face for i,face in enumerate(shell)}
c,vb=ns['complex_rows'](api,refined,cells,shell)
assert va==vb==Fraction(1,6) and a['oriented_boundary']==c['oriented_boundary']
assert a['internal_face_pairs']==0 and c['internal_face_pairs']==6
assert all(ns['pair_check'](refined,cells[x],cells[y])['intersection_equals_tagged_shared_simplex'] for x,y in combinations(cells,2))

def refuses(fn,*args):
 try:fn(*args)
 except ValueError:return
 raise AssertionError('Expected exact refusal')

bad=[list(f) for f in shell];bad[0]=list(reversed(bad[0]))
refuses(ns['complex_rows'],api,points,{101:row},bad)
refuses(ns['complex_rows'],api,points,{101:[1,3,2,4]},shell)
thin={**points,4:(Fraction(0),Fraction(0),Fraction(1,1024))}
poor,v=ns['complex_rows'](api,thin,{101:row},shell)
assert poor['all_exact_positive'] and poor['quality_rows'][0]['exact_point1_gate_passed'] is False
assert ns['cycle']([1,2,3])==ns['cycle']([2,3,1]) and ns['cycle']([1,2,3])!=ns['cycle']([1,3,2])
# Only original-pair geometry is invoked by the planned main; immutable candidate741 is metadata-bound.
queries=[n for n in ast.walk(top['main']) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='pair_check']
assert len(queries)==1 and ast.unparse(queries[0].args[0])=='old_points'
assert not any(isinstance(n,ast.Import) and any(a.name.split('.')[0] in ['numpy','scipy','gmsh'] for a in n.names) for n in ast.walk(tree))
print('PASS: common-oriented-shell subdivision, opposite incidences, old-positive-poor allowed, reversal refused; no native/saved-candidate query')
