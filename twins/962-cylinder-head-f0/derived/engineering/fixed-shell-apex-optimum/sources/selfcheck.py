"""Prepared one stdlib assert check; no actual saved geometry or native imports."""
from pathlib import Path
from fractions import Fraction
import ast,math,struct

source=Path(__file__).with_name('propose.py');tree=ast.parse(source.read_text())
names={'ARRAYS','WORKER','SHELL','INPUTS','TARGETS'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name!='main'
       or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets)]
ns=dict(Fraction=Fraction,math=math,struct=struct)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
quality=ns['exact_quality'];optimum=ns['optimal_apex']

def refuses(fn,*args):
    try:fn(*args)
    except ValueError:return
    raise AssertionError('Required refusal did not occur')

# Exact calibration independent of the optimum construction.
unit=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
assert quality(unit)==(Fraction(1),Fraction(2,3))
assert quality([unit[0],unit[2],unit[1],unit[3]])==(-Fraction(1),Fraction(2,3))
assert quality([[0.,0.,0.]]*4)==(Fraction(0),None)

# Regular face; tolerance checks only the displayed floating construction.
regular=[[0.,0.,0.],[1.,0.,0.],[.5,math.sqrt(3)/2,0.],[.5,math.sqrt(3)/6,.01]]
xyz,_=optimum(regular,3)
assert abs(xyz[0]-.5)<1e-14 and abs(xyz[1]-math.sqrt(3)/6)<1e-14
assert abs(xyz[2]-math.sqrt(2./3.))<1e-14
assert quality(regular[:3]+[xyz])[1]>Fraction(999999,1000000)
corner0=[regular[3],regular[0],regular[2],regular[1]]
corner0_xyz,_=optimum(corner0,0)
assert struct.pack('<3d',*corner0_xyz)==struct.pack('<3d',*xyz)
assert quality([corner0_xyz,*corner0[1:]])[0]>0

# An anisotropic face stays below the strict quality gate at its optimum.
thin=[[0.,0.,0.],[100.,0.,0.],[0.,1./1024.,0.],[0.,0.,1.]]
xyz,_=optimum(thin,3);assert quality(thin[:3]+[xyz])[1]<Fraction(1,100)
reversed_side=[regular[0],regular[2],regular[1],[.5,.2,-.1]]
xyz,_=optimum(reversed_side,3);assert xyz[2]<0 and quality(reversed_side[:3]+[xyz])[0]>0
refuses(optimum,[regular[0],regular[2],regular[1],regular[3]],3)

# Only the declared two tags may change; unselected signed zero survives.
points={1:[-0.,0.,0.],27:[1.,1.,1.],28:[2.,2.,2.],29:[3.,3.,3.]}
updated=ns['replace_selected'](points,{28:[4.,4.,4.],29:[5.,5.,5.]})
assert struct.pack('<3d',*updated[1])==struct.pack('<3d',*points[1]) and updated[27]==points[27]
refuses(ns['replace_selected'],points,{27:[4.,4.,4.],29:[5.,5.,5.]})

# Missing/changed before-state pins refuse before any query or file read.
pins=dict(ns['INPUTS']);ns['require_input_bindings'](pins)
changed=dict(pins);changed[ns['ARRAYS']]='0'*64;refuses(ns['require_input_bindings'],changed)
missing=dict(pins);missing.pop(ns['WORKER']);refuses(ns['require_input_bindings'],missing)
assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and any(a.name.split('.')[0] in ['gmsh','numpy','scipy'] for a in n.names) for n in ast.walk(tree))
print('PASS: exact metric, regular/thin/old-side optimum, changed-tag/bits and before-pin assertions')
