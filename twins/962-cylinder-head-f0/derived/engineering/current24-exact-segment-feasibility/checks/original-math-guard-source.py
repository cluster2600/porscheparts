"""HELD: one future synthetic-only runtime/API and mathematical guard invocation."""
import ast
from fractions import Fraction
from functools import cmp_to_key
import hashlib
from itertools import product,combinations
import json
import math
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).with_name("classify_segment_feasibility.py")
ROOT_LIBRARY_BASE=ROOT/"work/962-engineering/head-star-current24-segment-runtime-001/venv/lib/python3.12/site-packages"
NAMES=("coordinate_rows","need","rational","subtract","dot","cross","exact_quality",
    "topology_diagnostic","fixed_bits","exact_rows","root_library","qvalue","poly_data",
    "polynomial_cell","refine_isolator","compare_roots","rational_node","root_snapshot",
    "simplest_sample","sign_decomposition","recheck_word_proposal")
namespace=dict(Fraction=Fraction,cmp_to_key=cmp_to_key,hashlib=hashlib,product=product,
    combinations=combinations,json=json,math=math,os=os,Path=Path,struct=struct,sys=sys,
    ROOT=ROOT,ROOT_LIBRARY_BASE=ROOT_LIBRARY_BASE,BOUNDARY=4,FREE=())
tree=ast.parse(SOURCE.read_text())
nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef)and node.name in NAMES]
assert {node.name for node in nodes}==set(NAMES)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE)+"#pure-fixtures","exec"),namespace)

class SegmentGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sp,cls.runtime=namespace["root_library"]()
        cls.t=cls.sp.Symbol("t")
        print("SELECTED_ROOT_RUNTIME "+json.dumps(cls.runtime,sort_keys=True),flush=True)

    def poly(self,expression):return self.sp.Poly(expression,self.t,domain="QQ")
    def classify(self,entries):
        return namespace["sign_decomposition"]([dict(cell_tag=i+1,kind=k,poly=self.poly(p))
            for i,(k,p)in enumerate(entries)],self.sp)

    def test_selected_versions_backend_origins_and_public_API(self):
        self.assertEqual(self.runtime["sympy_version"],"1.14.0")
        self.assertEqual(self.runtime["mpmath_version"],"1.3.0")
        self.assertEqual(self.runtime["ground_types"],"python")
        self.assertEqual(self.runtime["cache"],"no")
        p=self.poly((3*self.t-1)**2*(2*self.t**2-1))
        coefficient,factors=p.factor_list();rebuilt=self.poly(coefficient)
        for factor,multiplicity in factors:rebuilt*=factor**multiplicity
        self.assertEqual(rebuilt,p)
        sf=p.sqf_part()
        self.assertEqual(sum(int(k)for _,k in sf.intervals()),int(sf.count_roots()))
        self.assertTrue(sf.sturm())
        self.assertEqual(self.poly(2*self.t**2-1).gcd(self.poly(1-2*self.t**2)).degree(),2)

    def test_exact_metric_single_and_pair_degree_bounds(self):
        start=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
        single=[row[:]for row in start];single[3]=[.25,.125,1.25]
        pair=[row[:]for row in single];pair[1]=[1.125,.25,.125]
        for final,dbound,pbound in((single,1,4),(pair,2,6)):
            d,s,f,p=namespace["polynomial_cell"](start,final,self.sp)
            self.assertLessEqual(d.degree(),dbound);self.assertLessEqual(p.degree(),pbound)
            self.assertEqual(p,(d*d).mul_ground(3600)-s*f)

    def test_constant_zero_constraints_retained(self):
        full=self.classify([("D",1),("P",0)])
        self.assertEqual(len(full["constraints"]),2)
        self.assertEqual(len(full["connected_feasible_components"]),1)
        self.assertFalse(self.classify([("D",0),("P",1)])["real_path_feasible"])
        self.assertFalse(self.classify([("D",1),("P",-1)])["real_path_feasible"])

    def test_repeated_common_root_strict_orientation(self):
        value=(2*self.t-1)**2
        result=self.classify([("D",value),("P",value)])
        self.assertEqual(len(result["connected_feasible_components"]),2)
        middle=[r for r in result["ordered_boundaries"]if r["exact_rational"]==
            dict(numerator="1",denominator="2")][0]
        self.assertEqual(middle["constraint_multiplicities"],{"0":2,"1":2})

    def test_strict_domain_endpoints(self):
        result=self.classify([("D",self.t*(1-self.t)),("P",0)])
        component=result["connected_feasible_components"][0]
        self.assertFalse(component["left_closed"]);self.assertFalse(component["right_closed"])
        self.assertEqual(component["canonical_exact_sample"]["value"],dict(numerator="1",denominator="2"))

    def test_irrational_singleton_without_word_construction(self):
        result=self.classify([("D",1),("P",2*self.t**2-1),("P",1-2*self.t**2)])
        component=result["connected_feasible_components"][0]
        self.assertEqual(len(result["connected_feasible_components"]),1)
        self.assertEqual(component["canonical_exact_sample"]["kind"],"exact_singleton")
        self.assertIsNone(component["canonical_exact_sample"]["algebraic_point"]["exact_rational"])
        self.assertIsNone(component["correctly_rounded_binary64_proposal"])
        self.assertFalse(result["binary64_word_construction_supported"])

    def test_distinct_irrational_order_and_global_ordinals(self):
        result=self.classify([("D",1),("P",2*self.t**2-1),("P",2-3*self.t**2)])
        component=result["connected_feasible_components"][0]
        self.assertEqual(component["canonical_exact_sample"]["value"],dict(numerator="3",denominator="4"))
        for boundary in result["ordered_boundaries"]:
            for ref in boundary["algebraic_factor_references"]:
                self.assertEqual(ref["real_root_index"],1)

    def test_empty_multi_constraint_intersection(self):
        result=self.classify([("D",1),("P",4*self.t-3),("P",1-4*self.t)])
        self.assertFalse(result["real_path_feasible"])
        self.assertEqual(len(result["constraints"]),3)
        self.assertTrue(all(not atom["feasible"]for atom in result["complete_sign_atoms"]))

    def test_smallest_rational_closed_boundaries(self):
        result=self.classify([("D",1),("P",(3*self.t-1)*(2-3*self.t))])
        component=result["connected_feasible_components"][0]
        self.assertTrue(component["left_closed"]);self.assertTrue(component["right_closed"])
        self.assertEqual(component["canonical_exact_sample"]["value"],dict(numerator="1",denominator="2"))

    def test_negative_orientation_cannot_be_squared_away(self):
        self.assertFalse(self.classify([("D",-1),("P",1)])["real_path_feasible"])

    def test_separate_word_recheck_retains_full_cell_failure(self):
        points={1:[0.,0.,0.],2:[1.,0.,0.],3:[0.,1.,0.],4:[0.,0.,1.],5:[.25,.25,.25]}
        cells={1:[1,2,3,5],2:[1,4,2,5],3:[1,3,4,5],4:[2,4,3,5]}
        scope=dict(movable_node_tags=[5],full_tetrahedron_tags=[1,2,3,4])
        xyz=[2.,2.,2.];rows=[dict(node_tag=5,coordinates_mm=xyz,binary64_hex=[x.hex()for x in xyz])]
        result=namespace["recheck_word_proposal"](points,cells,scope,rows)
        self.assertFalse(result["actual_word_gate_passed"])
        self.assertEqual(len(result["complete_after_rows"]),4)
        self.assertTrue(result["own_volume_equal"])
        self.assertFalse(result["embedding_or_global_acceptance"])

    def test_fixed_words_preserve_signed_zero(self):
        a={1:[0.,0.,0.]};b={1:[-0.,0.,0.]}
        self.assertFalse(namespace["fixed_bits"](a,b))

if __name__=="__main__":
    unittest.main()
