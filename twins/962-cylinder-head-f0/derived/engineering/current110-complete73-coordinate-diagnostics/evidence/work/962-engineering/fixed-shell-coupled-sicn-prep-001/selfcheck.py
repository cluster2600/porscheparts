"""ROOT-ONLY NumPy/synthetic exact guards, prepared unrun; no SciPy/optimizer or saved rows."""
from pathlib import Path
from fractions import Fraction
import ast,hashlib,json,math,struct

here=Path(__file__).resolve().parent
c=json.loads((here/'held-contract.json').read_text())
import numpy as np  # Only root runs this selected-NumPy literal check.
assert np.__version__=='2.2.6' and Path(np.__file__).resolve()==Path(c['numpy_init']).resolve()
assert hashlib.sha256(Path(c['numpy_init']).read_bytes()).hexdigest()==c['runtime_files'][c['numpy_init']]
source=here/'coupled.py';assert hashlib.sha256(source.read_bytes()).hexdigest()==c['reader_sha256']
tree=ast.parse(source.read_text())
names={'signed_sicn_vector','tagged_indices','assemble_points','fixed_bits','exact_rows','result_status',
       'exact_quality','rational','subtract','dot','cross'}
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
assert {n.name for n in functions}==names
ns=dict(Fraction=Fraction,math=math,struct=struct,FREE=[27,28,29])
exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),ns)

def refuses(fn,*args):
    try:fn(*args)
    except ValueError:return
    raise AssertionError('Required refusal did not occur')

# Native-order sign and the independent exact normalization agree on literal cells.
unit=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
reverse=[unit[0],unit[2],unit[1],unit[3]]
q=ns['signed_sicn_vector'](np,[unit,reverse])
assert math.isclose(float(q[0]),math.sqrt(2/3),rel_tol=1e-11,abs_tol=1e-14) and math.isclose(float(q[1]),-float(q[0]),rel_tol=1e-11,abs_tol=1e-14)
rows,volume=ns['exact_rows']({1:unit[0],2:unit[1],3:unit[2],27:unit[3]},
                            {10:[1,2,3,27],11:[1,3,2,27]})
assert rows[0]['exact_point1_gate_passed'] and not rows[1]['exact_point1_gate_passed']
assert not rows[1]['positive_orientation'] and volume==0  # Signed cancellation never accepts inverted cells.
assert ns['exact_quality'](unit)==(Fraction(1),Fraction(2,3))
planar=[unit[0],unit[1],unit[2],[.25,.25,0.]]
refuses(ns['signed_sicn_vector'],np,[planar])
assert ns['exact_quality'](planar)[0]==0
assert ns['exact_quality']([[0.,0.,0.]]*4)==(Fraction(0),None)

# All three tags share one coupled ten-vector; every unselected bit is retained.
tags=list(range(1,17))+[27,28,29]
indices,positions=ns['tagged_indices'](tags,[[1,2,27,28],[3,28,29,4]],[27,28,29])
assert indices==[[0,1,16,17],[2,17,18,3]] and positions==[16,17,18]
original=np.arange(57,dtype='f8').reshape((19,3));original[0,0]=-0.;original.setflags(write=False)
x=np.r_[np.arange(9,dtype='f8')+.25,.05]
final=ns['assemble_points'](np,original,positions,x)
a=dict(zip(tags,original.tolist()));b=dict(zip(tags,final.tolist()))
assert final[:16].tobytes()==original[:16].tobytes() and ns['fixed_bits'](a,b)
b[1][0]=0.;assert not ns['fixed_bits'](a,b)  # +0 versus -0 is a real bit drift.
refuses(ns['assemble_points'],np,original,positions,x[:-1])
refuses(ns['assemble_points'],np,original,positions,np.r_[x[:-1],np.nan])
refuses(ns['tagged_indices'],[1,1,2,3],[[1,2,3,4]],[2])

# Exact feasibility is not redefined by solver success.
assert ns['result_status'](False,True,True)=='feasible_point_solver_not_converged'
assert ns['result_status'](True,False,True)=='rejected_exact_quality_diagnostic_retained'
assert ns['result_status'](True,True,False)=='rejected_procedural_diagnostic_retained'
calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='minimize']
assert len(calls)==1
bounds=next(k.value for k in calls[0].keywords if k.arg=='bounds')
assert ast.dump(bounds)==ast.dump(ast.parse('[(None,None)]*9+[(initial_min,1.)]',mode='eval').body)
assert c['solver']==dict(method='SLSQP',maxiter=100,ftol=1e-10,eps=2.**-26)
assert not c['proposal_execution_authorized'] and c['input_counts']==dict(nodes=19,cells=39,movable_nodes=3,coordinate_variables=9,variables_with_epigraph=10,constraints=39)
assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and any(a.name.split('.')[0] in ['gmsh','scipy'] for a in n.names) for n in tree.body)
runner=ast.parse((here/'run_readback.py').read_text())
declaration=next(k.value for n in ast.walk(runner) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict' for k in n.keywords if k.arg=='declared_operation_counts')
assert ast.literal_eval(declaration)=={'gmsh_generate':0,'gmsh_createGeometry':0,'gmsh_optimize':0,'SLSQP_minimize_invocations':1,'gmsh_write_mesh':0,'solve':0}
print('PASS: vector/exact sign, all-three tag assembly, raw fixed bits, exact feasibility independence and one-call bounds')
