"""SOURCE ONLY: synthetic apex/orientation/quality/volume guards; no real head coordinates."""
import ast
from fractions import Fraction
import math
from pathlib import Path
import struct
import unittest

SOURCE=Path(__file__).with_name("propose_analytic_apex.py")
NAMES={"need","rational","subtract","dot","cross","exact_quality","exact_rows","topology_diagnostic","fixed_bits","optimal_apex"}

def pure_functions():
    tree=ast.parse(SOURCE.read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in NAMES]
    if {n.name for n in nodes}!=NAMES:raise ValueError("Exact synthetic helper set required")
    namespace={"Fraction":Fraction,"math":math,"struct":struct,"FREE":()}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),"exec"),namespace)
    return namespace

def face(conn):
    return dict(tetrahedron_tag=1,fixed_face_node_tags=[t for t in conn if t!=4],
        interior_seed_node_tag=4,original_ordered_tetrahedron_node_tags=list(conn))

class SyntheticApexGuards(unittest.TestCase):
    def setUp(self):
        self.f=pure_functions()
        self.points={1:[0.,0.,0.],2:[1.,0.,0.],3:[0.,1.,0.],4:[0.,0.,1.]}

    def test_right_face_apex_improves_original_tetra_quality(self):
        result=self.f["optimal_apex"](face((1,2,3,4)),self.points)
        final=dict(self.points);final[4]=result["coordinates_mm"]
        before=self.f["exact_quality"]([self.points[t] for t in (1,2,3,4)])
        after=self.f["exact_quality"]([final[t] for t in (1,2,3,4)])
        self.assertGreater(after[0],0);self.assertGreater(after[1],before[1])
        self.assertGreaterEqual(after[1],Fraction(1,100))

    def test_positive_native_corner_permutations_preserve_proposal(self):
        baseline=self.f["optimal_apex"](face((1,2,3,4)),self.points)["binary64_hex"]
        for conn in [(2,3,1,4),(4,1,3,2),(1,4,2,3)]:
            result=self.f["optimal_apex"](face(conn),self.points)
            self.assertEqual(result["binary64_hex"],baseline)

    def test_power_of_two_scale_covariance(self):
        baseline=self.f["optimal_apex"](face((1,2,3,4)),self.points)["coordinates_mm"]
        scaled={t:[2*v for v in p] for t,p in self.points.items()}
        result=self.f["optimal_apex"](face((1,2,3,4)),scaled)
        self.assertEqual(result["binary64_hex"],[(2*v).hex() for v in baseline])

    def test_coplanar_original_refuses(self):
        points=dict(self.points);points[4]=[.25,.25,0.]
        with self.assertRaises(ValueError):self.f["optimal_apex"](face((1,2,3,4)),points)

    def test_underflowed_binary64_normal_refuses_without_fallback(self):
        points={1:[0.,0.,0.],2:[1e-300,0.,0.],3:[0.,1e-300,0.],4:[0.,0.,1.]}
        with self.assertRaises(ValueError):self.f["optimal_apex"](face((1,2,3,4)),points)

    def test_negative_tetrahedron_is_retained_as_quality_failure(self):
        points=dict(self.points);points[4]=[0.,0.,-1.]
        rows,volume=self.f["exact_rows"](points,{1:[1,2,3,4]})
        self.assertEqual(len(rows),1);self.assertFalse(rows[0]["positive_orientation"])
        self.assertFalse(rows[0]["exact_point1_gate_passed"]);self.assertLess(volume,0)

    def test_fixed_word_guard_preserves_signed_zero(self):
        final=dict(self.points);final[1]=[-0.,0.,0.]
        self.f["FREE"]=(4,)
        self.assertFalse(self.f["fixed_bits"](self.points,final))

    def test_closed_star_own_exact_volume_and_boundary_are_fixed(self):
        points={0:[0.,0.,0.],1:[1.,0.,0.],2:[0.,1.,0.],3:[0.,0.,1.],4:[.25,.25,.25]}
        cells={1:[0,1,2,4],2:[0,3,1,4],3:[1,3,2,4],4:[2,3,0,4]}
        before_rows,before=self.f["exact_rows"](points,cells)
        topo=self.f["topology_diagnostic"](cells,None)
        self.assertNotIn(4,{t for row in topo["oriented_boundary_faces"] for t in row})
        final=dict(points);final[4]=[.125,.25,.25]
        after_rows,after=self.f["exact_rows"](final,cells)
        self.assertEqual(after,before)
        self.assertTrue(all(row["positive_orientation"] for row in before_rows+after_rows))
        self.assertTrue(self.f["topology_diagnostic"](cells,topo["oriented_boundary_faces"])["exact_frozen_oriented_boundary"])

if __name__=="__main__":unittest.main()
