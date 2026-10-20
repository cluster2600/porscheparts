"""UNRUN focused synthetic fixtures for held fixed-word interior2<->3 screen.

Importing the held module and all arithmetic below are deferred to a separately
reviewed synthetic-only invocation. No real census file is loaded by this source.
"""
import copy
from fractions import Fraction
import importlib.util
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/"work/962-engineering/head-star-current24-interior-flip-prep-001/propose_saved_cavity_flips.py"
spec=importlib.util.spec_from_file_location("held_cavity_flip_worker",SOURCE)
worker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

# Rational bipyramid. The triangle has area2 and both apex heights1, so volume4/3.
# Signed zero is deliberate: unchanged geometry does not excuse changing its word.
POINTS={1:(-1.0,-1.0,0.0),2:(1.0,-1.0,0.0),3:(0.0,1.0,-0.0),
        4:(0.0,0.0,1.0),5:(0.0,0.0,-1.0)}
TWO={101:(1,2,3,4),102:(1,3,2,5)}
THREE={201:(4,5,2,1),202:(4,5,1,3),203:(4,5,3,2)}
BOUNDARY={frozenset(t) for t in [(4,1,2),(4,2,3),(4,3,1),
                                (5,1,2),(5,2,3),(5,3,1)]}


def context(cells,points=None,seeds=(1,4),poor=None):
    p=copy.deepcopy(POINTS if points is None else points)
    return dict(points=p,words={t:tuple(float(x).hex() for x in xyz) for t,xyz in p.items()},
        cells=copy.deepcopy(cells),poor={min(cells)} if poor is None else set(poor),
        seeds=set(seeds),protected_cells=set(),protected_nodes=set())


def association(ctx,kind,simplex):
    matches=[a for a in worker.enumerate_associations(ctx)
             if a["kind"]==kind and a["removed_simplex"]==list(simplex)]
    if len(matches)!=1:raise AssertionError("Expected one synthetic feature association")
    return matches[0]


def exact_points(points,conn):
    return [[Fraction.from_float(float(x)) for x in points[t]] for t in conn]


def independent_det(points,conn):
    p=exact_points(points,conn)
    a,b,c=[[row[i]-p[0][i] for i in range(3)] for row in p[1:]]
    return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])


def independent_quality_squared(points,conn):
    """Cartesian edge lengths and face Gram determinants, not worker J columns."""
    p=exact_points(points,conn)
    S=sum((sum((p[i][k]-p[j][k])**2 for k in range(3))
           for i,j in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]),Fraction())
    T=Fraction()
    for i,j,k in [(0,1,2),(0,1,3),(0,2,3),(1,2,3)]:
        u=[p[j][d]-p[i][d] for d in range(3)]
        v=[p[k][d]-p[i][d] for d in range(3)]
        uu=sum(x*x for x in u);vv=sum(x*x for x in v);uv=sum(x*y for x,y in zip(u,v))
        T+=uu*vv-uv*uv
    D=independent_det(points,conn)
    return None if S*T==0 else 36*D*D/(S*T)


def fraction_row(row):
    return Fraction(int(row["numerator"]),int(row["denominator"]))


def bit_snapshot(ctx):
    return {t:struct.pack("<3d",*xyz) for t,xyz in ctx["points"].items()}


class ConvexCavityFixtures(unittest.TestCase):
    def assert_convex_domain(self,ctx,a,expected_count):
        before=copy.deepcopy(ctx);bits=bit_snapshot(ctx)
        result=worker.screen_local_cavity(ctx,a)
        self.assertEqual(result["local_result"],"passed_exact_local_screen_only")
        self.assertEqual(len(result["replacement_cells"]),expected_count)
        self.assertEqual({frozenset(f) for f in result["oriented_boundary_original"]},BOUNDARY)
        self.assertEqual(result["oriented_boundary_original"],result["oriented_boundary_replacement"])
        self.assertEqual(len(result["strict_support_witnesses"]),6)
        self.assertTrue(all(r["strict_outward_support"] for r in result["strict_support_witnesses"]))
        # Independent geometry: every supporting face has both other vertices strictly inside.
        for face in result["oriented_boundary_original"]:
            for t in sorted(set(POINTS)-set(face)):
                self.assertLess(independent_det(ctx["points"],face+[t]),0)
        for key in ["original_signed_volume_mm3","replacement_signed_volume_mm3"]:
            self.assertEqual(fraction_row(result[key]),Fraction(4,3))
        self.assertTrue(result["exact_volume_equal"])
        self.assertEqual(ctx,before);self.assertEqual(bit_snapshot(ctx),bits)
        self.assertEqual(bits[3][-8:],struct.pack("<d",-0.0))
        self.assertIsNone(result["complete_flip_eligibility"])
        self.assertFalse(result["mesh_application_authorized"])
        self.assertFalse(result["global_embedding_or_nonoverlap_proved"])
        # Parity correction changes ordering only, never any proposed vertex4-set.
        self.assertEqual({frozenset(c) for c in a["replacement_unoriented_cells"]},
                         {frozenset(r["ordered_node_tags"]) for r in result["replacement_cells"]})
        return result

    def test_two_to_three_fixed_convex_domain_volume_and_signed_zero(self):
        ctx=context(TWO)
        self.assert_convex_domain(ctx,association(ctx,"2_to_3",(1,2,3)),3)

    def test_three_to_two_fixed_convex_domain_volume_and_signed_zero(self):
        ctx=context(THREE,poor=(201,))
        self.assert_convex_domain(ctx,association(ctx,"3_to_2",(4,5)),2)

    def test_every_replacement_metric_and_gate_match_independent_face_gram_formula(self):
        for cells,kind,simplex in [(TWO,"2_to_3",(1,2,3)),(THREE,"3_to_2",(4,5))]:
            ctx=context(cells);r=worker.screen_local_cavity(ctx,association(ctx,kind,simplex))
            self.assertEqual(len(r["replacement_cells"]),3 if kind=="2_to_3" else 2)
            for row in r["replacement_cells"]:
                conn=row["ordered_node_tags"];D=independent_det(ctx["points"],conn)
                q2=independent_quality_squared(ctx["points"],conn)
                self.assertEqual(fraction_row(row["determinant_mm3"]),D)
                self.assertEqual(fraction_row(row["SICN_squared"]),q2)
                self.assertEqual(row["positive_and_SICN_point1"],D>0 and q2>=Fraction(1,100))
                self.assertTrue(row["positive_and_SICN_point1"])

    def test_negative_original_orientation_is_refused_not_reordered(self):
        bad=copy.deepcopy(TWO);bad[101]=(1,3,2,4)
        ctx=context(bad);r=worker.screen_local_cavity(ctx,association(ctx,"2_to_3",(1,2,3)))
        self.assertEqual(r["local_result"],"failed_exact_local_screen")
        self.assertIn("nonpositive original cavity cell",r["reasons"])
        self.assertLess(independent_det(ctx["points"],bad[101]),0)
        self.assertEqual(r["original_cells"][0]["ordered_node_tags"],list(bad[101]))

    def test_coplanar_apex_is_refused(self):
        points=copy.deepcopy(POINTS);points[4]=(0.0,0.0,0.0)
        ctx=context(TWO,points);r=worker.screen_local_cavity(ctx,association(ctx,"2_to_3",(1,2,3)))
        self.assertEqual(independent_det(points,TWO[101]),0)
        self.assertEqual(r["local_result"],"failed_exact_local_screen")
        self.assertIn("nonpositive original cavity cell",r["reasons"])
        self.assertTrue(any(not x["strict_outward_support"] for x in r["strict_support_witnesses"]))

    def test_nonconvex_apices_are_refused_even_with_positive_original_cells(self):
        points=copy.deepcopy(POINTS);points[5]=(3.0,0.0,-1.0)
        ctx=context(TWO,points);r=worker.screen_local_cavity(ctx,association(ctx,"2_to_3",(1,2,3)))
        self.assertTrue(all(independent_det(points,c)>0 for c in TWO.values()))
        self.assertEqual(r["local_result"],"failed_exact_local_screen")
        self.assertIn("not a strictly convex five-point cavity",r["reasons"])

    def test_strictly_convex_skinny_cavity_still_fails_replacement_quality(self):
        points=copy.deepcopy(POINTS)
        points[4]=(0.0,0.0,1.0/1024);points[5]=(0.0,0.0,-1.0/1024)
        ctx=context(TWO,points);r=worker.screen_local_cavity(ctx,association(ctx,"2_to_3",(1,2,3)))
        self.assertTrue(all(x["strict_outward_support"] for x in r["strict_support_witnesses"]))
        self.assertTrue(r["exact_volume_equal"])
        self.assertEqual(r["local_result"],"failed_exact_local_screen")
        self.assertIn("replacement quality/orientation failure",r["reasons"])
        independently_bad=[]
        for row in r["replacement_cells"]:
            q2=independent_quality_squared(points,row["ordered_node_tags"])
            independently_bad.append(q2<Fraction(1,100))
            self.assertEqual(fraction_row(row["SICN_squared"]),q2)
        self.assertTrue(any(independently_bad))

    def test_complete_and_unavailable_owner_scopes_are_not_conflated(self):
        ctx=context(TWO,seeds=(1,))
        a=association(ctx,"2_to_3",(1,2,3))
        self.assertTrue(a["complete_removed_simplex_owner_scope"])
        self.assertFalse(a["complete_introduced_simplex_owner_scope"])
        ctx=context(TWO,seeds=(4,))
        a=association(ctx,"2_to_3",(1,2,3))
        self.assertFalse(a["complete_removed_simplex_owner_scope"])
        self.assertTrue(a["complete_introduced_simplex_owner_scope"])
        r=worker.screen_local_cavity(ctx,a)
        self.assertIn("complete outside owners of removed simplex",r["missing_evidence"])
        # Inverse direction has the complementary edge/face ownership restriction.
        ctx=context(THREE,seeds=(4,))
        a=association(ctx,"3_to_2",(4,5))
        self.assertTrue(a["complete_removed_simplex_owner_scope"])
        self.assertFalse(a["complete_introduced_simplex_owner_scope"])

    def test_complete_owners_never_invent_interface_or_global_eligibility(self):
        ctx=context(TWO,seeds=(1,2,3,4,5))
        a=association(ctx,"2_to_3",(1,2,3));r=worker.screen_local_cavity(ctx,a)
        self.assertTrue(a["complete_removed_simplex_owner_scope"])
        self.assertTrue(a["complete_introduced_simplex_owner_scope"])
        self.assertEqual(r["local_result"],"passed_exact_local_screen_only")
        self.assertIsNone(r["complete_flip_eligibility"])
        self.assertIsNone(r["per_cell_region_and_interface_preservation"])
        self.assertIsNone(r["source_exterior_or_BIN_membership"])
        self.assertIn("per-cell geometric entity/physical region labels",r["missing_evidence"])
        self.assertFalse(r["mesh_application_authorized"])

    def test_complete_poor_face_and_edge_associations_are_unique(self):
        ctx=context(TWO);rows=worker.enumerate_associations(ctx)
        expected={("2_to_3",x) for x in [(1,2,3),(1,2,4),(1,3,4),(2,3,4)]}
        expected|={("3_to_2",x) for x in [(1,2),(1,3),(1,4),(2,3),(2,4),(3,4)]}
        self.assertEqual({(a["kind"],tuple(a["removed_simplex"])) for a in rows},expected)
        self.assertEqual(len(rows),10);self.assertEqual(len({a["association_ID"] for a in rows}),10)
        self.assertTrue(all(a["poor_owner_tags"]==[101] for a in rows))
        self.assertTrue(any(not a["observed_bistellar_pattern"] for a in rows))

    def test_degree_four_edge_is_retained_without_any_three_cell_subset(self):
        points=copy.deepcopy(POINTS);points[6]=(1.0,1.0,1.0)
        cells=copy.deepcopy(THREE);cells[204]=(4,5,1,6)
        ctx=context(cells,points,seeds=(4,));a=association(ctx,"3_to_2",(4,5))
        self.assertEqual(a["observed_owner_tags"],[201,202,203,204])
        self.assertFalse(a["observed_bistellar_pattern"])
        self.assertEqual(a["replacement_unoriented_cells"],[])
        r=worker.screen_local_cavity(ctx,a)
        self.assertEqual(r["local_result"],"refused_observed_incidence_not_2_or_3_five_point_pattern")

    def test_protected_removed_cell_is_refused(self):
        ctx=context(TWO);a=association(ctx,"2_to_3",(1,2,3));ctx["protected_cells"]={101}
        with self.assertRaisesRegex(ValueError,"Protected1983 cells cannot be removed"):
            worker.screen_local_cavity(ctx,a)

    def test_observed_duplicate_and_existing_introduced_edge_are_refused(self):
        cells=copy.deepcopy(TWO);cells[103]=(4,5,2,1)
        ctx=context(cells);a=association(ctx,"2_to_3",(1,2,3))
        r=worker.screen_local_cavity(ctx,a)
        self.assertEqual(r["local_result"],"failed_exact_local_screen")
        self.assertIn("replacement duplicates observed unchanged cell",r["reasons"])
        self.assertIn("introduced simplex already present in observed complement",r["reasons"])
        self.assertEqual(r["introduced_simplex_observed_outside_owners"],[103])
        self.assertEqual([x["existing_tetrahedron_tag"] for x in r["observed_duplicate_cells"]],[103])

    def test_duplicate_replacement_slots_are_refused(self):
        ctx=context(TWO);a=association(ctx,"2_to_3",(1,2,3))
        a["replacement_unoriented_cells"][1]=list(a["replacement_unoriented_cells"][0])
        r=worker.screen_local_cavity(ctx,a)
        self.assertEqual(r["local_result"],"failed_exact_local_screen")
        self.assertIn("duplicate replacement cells",r["reasons"])

    def test_distinct_real_associations_report_shared_removed_cell_conflict(self):
        points=copy.deepcopy(POINTS);points[6]=(0.0,-2.0,1.0)
        cells=copy.deepcopy(TWO);cells[103]=(1,2,4,6)
        ctx=context(cells,points)
        a=association(ctx,"2_to_3",(1,2,3));b=association(ctx,"2_to_3",(1,2,4))
        self.assertNotEqual(a["association_ID"],b["association_ID"])
        rows=worker.association_conflicts([a,b])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["shared_removed_cell_tags"],[101])
        self.assertEqual(set(rows[0]["association_IDs"]),{a["association_ID"],b["association_ID"]})

    def test_signed_zero_word_mismatch_is_refused(self):
        ctx=context(TWO);a=association(ctx,"2_to_3",(1,2,3))
        ctx["words"][3]=(0.0.hex(),1.0.hex(),0.0.hex())
        self.assertNotEqual(ctx["words"][3][-1],ctx["points"][3][-1].hex())
        with self.assertRaisesRegex(ValueError,"Full271 input word identity required"):
            worker.screen_local_cavity(ctx,a)


if __name__=="__main__":
    unittest.main(verbosity=2)
