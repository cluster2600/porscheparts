"""Prepared UNRUN exact synthetic tests; no saved candidate query or scientific import."""
from fractions import Fraction
from itertools import combinations
from pathlib import Path
import ast,hashlib

SOURCE=Path(__file__).with_name('check_embedding.py')
SOURCE_SHA='1b489cc8149f4b5db8f90c594e32fe4c09b5db00151df6b1cfc88362d1018134'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Exact reviewed source required')
names={'rational','subtract','dot','cross','halfspaces','plane_vertex','in_shared_hull','pair_check'}
functions=[x for x in ast.parse(SOURCE.read_text()).body if isinstance(x,ast.FunctionDef) and x.name in names]
assert {x.name for x in functions}==names
ns=dict(Fraction=Fraction,combinations=combinations)
exec(compile(ast.Module(body=functions,type_ignores=[]),str(SOURCE),'exec'),ns)
P={1:(0,0,0),2:(1,0,0),3:(0,1,0),4:(0,0,1),5:(0,0,-1),6:(0,-1,0),7:(0,0,-1),
   8:(-1,0,0),9:(0,-1,0),10:(0,0,-1),11:(3,0,0),12:(4,0,0),13:(3,1,0),14:(3,0,1),
   15:(0,0,0),16:(0,1,0),17:(1,0,0),18:(0,0,-1),
   19:(Fraction(1,8),Fraction(1,8),Fraction(1,2)),
   20:(Fraction(1,8),Fraction(1,8),Fraction(1,8)),
   21:(Fraction(5,8),Fraction(1,8),Fraction(1,8)),
   22:(Fraction(1,8),Fraction(5,8),Fraction(1,8)),
   23:(Fraction(1,8),Fraction(1,8),Fraction(5,8))}
P={t:tuple(Fraction(x) for x in p) for t,p in P.items()};unit=[1,2,3,4]
for other,shared,vertices in [([11,12,13,14],[],0),([1,3,2,5],[1,2,3],3),([1,2,6,7],[1,2],2),([1,8,10,9],[1],1)]:
    row=ns['pair_check'](P,unit,other)
    assert row['shared_node_tags']==shared and row['intersection_vertices']==vertices
    assert row['intersection_equals_tagged_shared_simplex'] and row['illegal_intersection_vertices']==0
    reverse=ns['pair_check'](P,other,unit)
    assert reverse['intersection_vertices']==vertices and reverse['intersection_equals_tagged_shared_simplex']
for other,shared in [([20,21,22,23],[]),([15,16,17,18],[]),([1,2,3,19],[1,2,3])]:
    row=ns['pair_check'](P,unit,other)
    assert row['shared_node_tags']==shared and not row['intersection_equals_tagged_shared_simplex']
    assert row['illegal_intersection_vertices']==len(row['all_illegal_rational_witnesses'])>0
    assert all(Fraction(int(v['numerator']),int(v['denominator']))>=0 for w in row['all_illegal_rational_witnesses'] for v in w['all8_inside_slacks'])
assert ns['plane_vertex']([([1,0,0],Fraction(1,2)),([0,1,0],Fraction(1,3)),([0,0,1],Fraction(1,4))])==(Fraction(1,2),Fraction(1,3),Fraction(1,4))
assert ns['plane_vertex']([([1,0,0],0),([1,0,0],1),([0,1,0],0)]) is None
print('PASS: disjoint/proper face-edge-vertex intersections, illegal overlap and unshared touch, exact Cramer rank handling')
