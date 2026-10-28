"""Prepared compact stdlib selfcheck; synthetic rows only, not executed by author."""
from pathlib import Path
from fractions import Fraction
from math import isqrt
import ast,math,struct

source=Path(__file__).with_name('screen.py');tree=ast.parse(source.read_text())
names={'FREE','FIXED','BITS'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name!='main'
       or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets)]
ns=dict(Fraction=Fraction,isqrt=isqrt,math=math,struct=struct)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)

def refuses(fn,*args):
    try:fn(*args)
    except ValueError:return
    raise AssertionError('Required refusal did not occur')

# Good and poor status cannot filter this complete integer-only support selector.
cells={10:[27,1,2,3],11:[1,28,4,5],12:[4,27,5,6],
       13:[27,28,1,2],14:[27,28,29,1],15:[1,2,3,4]}
groups,excluded=ns['fixed_support'](cells)
assert groups=={27:[10,12],28:[11],29:[]}
assert [r['tetrahedron_tag'] for r in excluded]==[13,14,15]
assert [r['reason'] for r in excluded]==['multiple_free_nodes_not_fixed_triple']*2+['no_free_apex']
assert ns['fixed_support']({})==({27:[],28:[],29:[]},[])
refuses(ns['fixed_support'],{1:[27,1,1,2]})
refuses(ns['fixed_support'],{1:[30,1,2,3]})

# Exact touching remains inconclusive; arbitrarily small strict separation certifies.
zero=[Fraction(0)]*3;one=Fraction(1)
compare=ns['compare_balls']
assert compare((zero,one),([Fraction(2),Fraction(0),Fraction(0)],one))['decision']=='inconclusive'
assert compare((zero,one),([Fraction(2)+Fraction(1,1<<80),Fraction(0),Fraction(0)],one))['strictly_disjoint_necessary_outer_balls']
refuses(ns['disjoint'],Fraction(-1),one,one)
refuses(ns['outer_radius_squared'],Fraction(100),Fraction(1))

# Existing positive native-corner enclosure, exact root bounds and translation invariance.
unit=[[Fraction(v) for v in row] for row in [[0,0,0],[1,0,0],[0,1,0],[0,0,1]]]
ball=ns['enclosing_ball'](unit,3)
assert ball['native_ordered_determinant_mm3']==1 and ball['native_free_corner']==3
root=ns['sqrt_interval'](Fraction(2))
assert root['lo']**2<=2<=root['hi']**2
translated=[[p[0]+(1<<20),p[1],p[2]] for p in unit]
other=ns['enclosing_ball'](translated,3)
assert ball['squared_radius_upper_mm2']==other['squared_radius_upper_mm2']
assert compare((ball['rational_ball_centre_mm'],ball['squared_radius_upper_mm2']),
               (other['rational_ball_centre_mm'],other['squared_radius_upper_mm2']))['decision']=='strict_disjointness_certificate'
refuses(ns['enclosing_ball'],[unit[0],unit[2],unit[1],unit[3]],3)
assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and any(a.name.split('.')[0] in ['gmsh','numpy','scipy'] for a in n.names) for n in ast.walk(tree))
print('PASS: complete fixed-triple selection, multi-free exclusion, exact strict balls and inherited enclosure assertions')
