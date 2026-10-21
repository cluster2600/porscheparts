"""Prepared stdlib-only AST/math/mock guards; no scientific imports or subprocesses."""
import ast
import hashlib
import math
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

SOURCE=Path(__file__).with_name('direct_sicn_cube.py')
SOURCE_SHA='0ddc9c6c96fa17302416c21c8f6a8873d1306dab1056acf7fb2a552c2a7c1d9b'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:
    raise ValueError('Exact witness source required before AST-only guard extraction')
TREE=ast.parse(SOURCE.read_text())
NAMES={'OUTPUT_NAME','LIMITS','SOLVER','OPTIONS','GATE','NODE_TAGS','TET_TAGS','TRI_TAGS',
       'BOUNDARY','TRIANGLES','TETS','INITIAL','CENTRE','QUALIFICATION'}
FUNCTIONS={'sub','dot','cross','signed_sicn','cube_qualities','same_numpy','require_contract_fields'}
SELECTED=[n for n in TREE.body if (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in NAMES for t in n.targets))
          or (isinstance(n,ast.FunctionDef) and n.name in FUNCTIONS)]
PURE=dict(math=math,Path=Path,re=re)
exec(compile(ast.Module(body=SELECTED,type_ignores=[]),str(SOURCE),'exec'),PURE)


class WitnessGuards(unittest.TestCase):
    def test_literal_all_twelve_cells_have_poor_start_and_feasible_centre(self):
        self.assertEqual(len(PURE['TETS']),12);self.assertEqual(len(set(PURE['TETS'])),12)
        self.assertTrue(all(t[0]==201 for t in PURE['TETS']))
        start=PURE['cube_qualities'](PURE['INITIAL']);centre=PURE['cube_qualities'](PURE['CENTRE'])
        self.assertTrue(0<min(start)<.1);self.assertGreater(min(centre),.1)
        points=dict(zip(PURE['NODE_TAGS'],PURE['BOUNDARY']+(PURE['CENTRE'],)))
        volumes=[]
        for tags in PURE['TETS']:
            a,b,c,d=(points[t] for t in tags)
            volumes.append(PURE['dot'](PURE['sub'](b,a),PURE['cross'](PURE['sub'](c,a),PURE['sub'](d,a)))/6)
        self.assertTrue(all(v>0 for v in volumes));self.assertEqual(math.fsum(volumes),8.)

    def test_signed_formula_regular_sliver_orientation_and_degenerate_refusal(self):
        q=PURE['signed_sicn'];r=((0.,0.,0.),(1.,0.,0.),(.5,math.sqrt(3)/2,0.),(.5,math.sqrt(3)/6,math.sqrt(2/3)))
        self.assertAlmostEqual(q(r),1.,places=14)
        sliver=tuple((x,y,z*.001) for x,y,z in r)
        self.assertTrue(math.isclose(q(sliver),3/math.sqrt((2+.001**2)*(2+1/.001**2)),rel_tol=1e-14))
        self.assertAlmostEqual(q((r[1],r[0],r[2],r[3])),-1.,places=14)
        planar=tuple((x,y,0.) for x,y,z in r)
        self.assertEqual(q(planar,allow_planar=True),0.)
        for invalid in [planar,((0.,0.,0.),)*4,((math.nan,0.,0.),)+r[1:]]:
            with self.assertRaises(ValueError):q(invalid)

    def contract(self):
        return dict(schema='962-direct-sicn-cube/v1',scope='tiny_cube_software_only',
            native_execution_authorized=True,root_and_peer_review_complete=True,selected_runtime_review_complete=True,
            qualification=PURE['QUALIFICATION'].copy(),limits=PURE['LIMITS'].copy(),solver=PURE['SOLVER'].copy(),
            options=PURE['OPTIONS'].copy(),sicn_gate=.1,input_hashes={'/source':'a'*64},
            runtime_files={'/runtime':'b'*64},numpy_init='/numpy/__init__.py',scipy_directory='/scipy')

    def test_held_null_authority_and_modified_gate_are_refused(self):
        check=PURE['require_contract_fields'];check(self.contract())
        for key,value in [('native_execution_authorized',False),('root_and_peer_review_complete',False),
                          ('selected_runtime_review_complete',False),('sicn_gate',.099)]:
            c=self.contract();c[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check(c)
        c=self.contract();c['runtime_files']['/unknown']=None
        with self.assertRaises(ValueError):check(c)
        c=self.contract();c['qualification']['head_optimization_authorized']=True
        with self.assertRaises(ValueError):check(c)

    def test_numpy_module_origin_and_version_must_not_be_replaced(self):
        original=SimpleNamespace(__version__='2.0.2',__file__='/selected/numpy/__init__.py')
        check=PURE['same_numpy'];check(original,original,original.__file__)
        for module,path in [(SimpleNamespace(**vars(original)),original.__file__),
                            (original,'/other/numpy/__init__.py')]:
            with self.assertRaises(ValueError):check(module,original,path)
        original.__version__='2.2.6'
        with self.assertRaises(ValueError):check(original,original,original.__file__)

    def test_one_high_level_optimizer_call_and_all_cell_constraints_only(self):
        worker=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='worker')
        calls=[n for n in ast.walk(worker) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
               and n.func.attr=='minimize']
        self.assertEqual(len(calls),1)
        self.assertEqual(next(k.value.value for k in calls[0].keywords if k.arg=='method'),'SLSQP')
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in
                             {'generate','optimize','createGeometry'} for n in ast.walk(TREE)))
        constraints=next(k.value for k in calls[0].keywords if k.arg=='constraints')
        function=next(n for n in ast.walk(constraints) if isinstance(n,ast.Lambda))
        class Array(list):
            def __sub__(self,x):return [v-x for v in self]
        fn=eval(compile(ast.Expression(function),str(SOURCE),'eval'),
                dict(PURE,np=SimpleNamespace(asarray=lambda x:Array(x))))
        rows=fn([*PURE['CENTRE'],.1]);self.assertEqual(len(rows),12);self.assertTrue(all(x>0 for x in rows))

    def test_named_scipy_package_exposure_does_not_add_user_site(self):
        fn=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='scientific_modules')
        calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call)]
        specs=[n for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='spec_from_file_location']
        self.assertEqual(len(specs),1)
        self.assertEqual(specs[0].args[0].value,'scipy')
        self.assertTrue(any(k.arg=='submodule_search_locations' for k in specs[0].keywords))
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr in {'insert','append','extend'}
                             for n in calls))
        self.assertTrue(any(isinstance(n.func,ast.Name) and n.func.id=='same_numpy' for n in calls))


if __name__=='__main__':unittest.main()
