"""Independent numerical controls for the hypothetical curved-shell method."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT/'twins/964-chassis/sculpted-cell-f2-20261106'


def module(name):
    spec = importlib.util.spec_from_file_location('f2_test_'+name, STUDY/(name+'.py'))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


solver = module('solve')
with patch.dict(sys.modules, {'solve': solver}):
    controls = module('benchmark')


class SculptedShellTests(unittest.TestCase):
    def setUp(self):
        self.assumptions = json.loads((STUDY/'analysis-assumptions.json').read_text())

    def test_quadratic_shapes_interpolate_nodes_and_partition_unity(self):
        for kind, nodes, inside in [('S6', [(0,0),(1,0),(0,1),(.5,0),(.5,.5),(0,.5)], (.23,.19)),
                                   ('S8R', [(-1,-1),(1,-1),(1,1),(-1,1),(0,-1),(1,0),(0,1),(-1,0)], (.23,-.19))]:
            for i, (r,s) in enumerate(nodes):
                N, _, _ = solver.shape(kind,r,s)
                for j,v in enumerate(N):
                    self.assertAlmostEqual(v, float(i==j))
            r,s=inside;N,dr,ds=solver.shape(kind,r,s)
            self.assertAlmostEqual(sum(N),1);self.assertAlmostEqual(sum(dr),0);self.assertAlmostEqual(sum(ds),0)
            eps=1e-6
            for index in range(len(N)):
                numeric=(solver.shape(kind,r+eps,s)[0][index]-solver.shape(kind,r-eps,s)[0][index])/(2*eps)
                self.assertAlmostEqual(numeric,dr[index],places=8)

    def test_duffy_integration_matches_independent_triangle_moments(self):
        q=solver.quadrature('S6')
        self.assertAlmostEqual(sum(w for _,_,w in q),.5)
        self.assertAlmostEqual(sum(w*r for r,_,w in q),1/6)
        self.assertAlmostEqual(sum(w*r*s for r,s,w in q),1/24)
        self.assertAlmostEqual(sum(w*r*r for r,_,w in q),1/12)

    def test_flat_floor_pressure_preserves_force_and_affine_virtual_work(self):
        raw=controls.coupon();nodes,elements=solver.canonical_mesh(raw)
        loads,_=solver.make_loads(raw,nodes,elements,'bending',self.assumptions)
        self.assertAlmostEqual(sum(f[2] for f in loads.values()),-10000,places=7)
        work=sum(f[2]*(nodes[n][0]+2*nodes[n][1]) for n,f in loads.items())
        self.assertAlmostEqual(work,-10000*(50+2*5),places=5)

    def test_oblique_canonical_fiber_field_is_used_instead_of_global_X(self):
        raw=controls.coupon(True);nodes,elements=solver.canonical_mesh(raw)
        expected=controls.rotated([1,0,0],True)
        a,b,n,fallback=solver.orientation(nodes,elements[0])
        self.assertAlmostEqual(solver.dot(a,expected),1,places=10)
        self.assertAlmostEqual(solver.dot(a,n),0,places=10)
        self.assertAlmostEqual(solver.dot(b,n),0,places=10)
        without=deepcopy(elements[0]);without.pop('fiber_reference')
        default=solver.orientation(nodes,without)[0]
        self.assertLess(abs(solver.dot(default,expected)),.99)
        self.assertFalse(fallback)

    def test_reversed_surface_normal_is_rejected_against_canonical_hint(self):
        raw=controls.coupon();e=raw['elements'][0]
        e['nodes']=[e['nodes'][i] for i in [0,2,1,5,4,3]]
        with self.assertRaisesRegex(ValueError,'normal hint'):
            solver.audit(raw,self.assumptions,False)

    def test_coincident_unmerged_interface_nodes_fail_before_solver(self):
        raw=controls.coupon();n=max(raw['nodes'])+1;old=raw['elements'][0]['nodes'][5]
        raw['nodes'][n]=raw['nodes'][old][:];raw['elements'][0]['nodes'][5]=n
        with self.assertRaisesRegex(ValueError,'Coincident unmerged'):
            solver.audit(raw,self.assumptions,False)

    def test_missing_mechanical_upper_connection_is_not_full_cell_admission(self):
        raw=controls.coupon()
        with self.assertRaisesRegex(ValueError,'upper structure'):
            solver.audit(raw,self.assumptions,True)


if __name__=='__main__':
    unittest.main()
