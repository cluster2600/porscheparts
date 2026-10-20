"""UNRUN analytic/semantic fixtures only; no saved-head input is opened.

The fixture module loads only the held first-party Python source. Its execution
requires a separate root review/admission. There is one direct TestCase class.
"""
from fractions import Fraction
import copy
import importlib.util
import math
from pathlib import Path
import unittest

SOURCE=Path(__file__).with_name("propose_saved_edge_removal.py")
spec=importlib.util.spec_from_file_location("held_edge_removal_synthetic_target",SOURCE)
worker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def octahedron(height=1.0):
    # Pole edge length2h; the four equatorial edges have length sqrt2.
    points={1:(1.0,-0.0,0.0),2:(0.0,1.0,0.0),3:(-1.0,0.0,0.0),
            4:(0.0,-1.0,0.0),5:(0.0,0.0,height),6:(0.0,0.0,-height)}
    cells={101+i:(5,6,(i+1)%4+1,i+1) for i in range(4)}
    context=dict(points=points,words={t:tuple(float(v).hex() for v in p) for t,p in points.items()},
        cells=cells,poor=set(cells),seeds={5},protected_cells=set(),protected_nodes=set(),
        intake={"synthetic_only":True},classification_rows=[dict(node_tag=t) for t in sorted(points)])
    case=dict(case_ID="synthetic:5,6",central_edge=[5,6],removed_cell_tags=sorted(cells),
        removed_poor_cell_tags=sorted(cells),owner_scope_complete=True,observed_degree=4)
    return context,case


def first_candidate(context,case):
    cavity=worker.convex_edge_cavity(context,case)
    return cavity,worker.screen_edge_candidate(context,cavity,((1,2,3),(1,3,4)),1)


class EdgeRemovalSynthetic(unittest.TestCase):
    def test_regular_octahedron_both_four_to_four_fillings(self):
        context,case=octahedron();cavity=worker.convex_edge_cavity(context,case)
        expected=(((1,2,3),(1,3,4)),((1,2,4),(2,3,4)))
        self.assertEqual(worker.link_triangulations((1,2,3,4)),expected)
        self.assertEqual(cavity["old_signed_volume"],worker.rational(Fraction(4,3)))
        self.assertEqual(len(cavity["strict_support_rows"]),24)
        self.assertTrue(cavity["old_embedded_convex_filling_certified"])
        for i,tri in enumerate(expected,1):
            result=worker.screen_edge_candidate(context,cavity,tri,i)
            self.assertEqual(len(result["replacement_cells"]),4)
            # Independently: six edge-squares sum14, four face-cross squares sum14,
            # D=2, so Q^2=36*4/(14*14)=36/49; each volume is1/3.
            self.assertTrue(all(r["D"]==worker.rational(Fraction(2))
                and r["Q_squared"]==worker.rational(Fraction(36,49))
                for r in result["replacement_exact_rows"]))
            self.assertTrue(result["local_finite_predicates_passed"])
            self.assertTrue(result["local_embedded_convex_filling_certified"])

    def test_catalan_completeness_for_all_five_degrees(self):
        for n in range(4,9):
            rows=worker.link_triangulations(tuple(range(1,n+1)))
            self.assertEqual(len(rows),math.comb(2*n-4,n-2)//(n-1))
            self.assertEqual(len(set(rows)),len(rows))
            self.assertTrue(all(len(r)==n-2 and set(v for t in r for v in t)==set(range(1,n+1)) for r in rows))

    def test_duplicate_link_edge_is_not_a_cycle(self):
        context,case=octahedron();context["cells"][104]=context["cells"][101]
        result=worker.link_cycle(context,case)
        self.assertFalse(result["valid"]);self.assertIn("duplicate link edge",result["reasons"])

    def test_disconnected_degree_two_link_is_refused(self):
        context,case=octahedron()
        context["cells"].update({201:(5,6,8,7),202:(5,6,9,8),203:(5,6,10,9),204:(5,6,7,10)})
        case["removed_cell_tags"]=sorted(context["cells"])
        result=worker.link_cycle(context,case)
        self.assertFalse(result["valid"])
        self.assertIn("link disconnected or fails single-cycle closure",result["reasons"])

    def test_reversed_original_orientation_is_not_repaired(self):
        context,case=octahedron();context["cells"][101]=(6,5,2,1)
        result=worker.convex_edge_cavity(context,case)
        self.assertFalse(result["all_old_tetrahedra_positive"])
        self.assertFalse(result["old_embedded_convex_filling_certified"])

    def test_coincident_vertices_refuse_non_degeneracy(self):
        context,case=octahedron();context["points"][4]=context["points"][3]
        result=worker.convex_edge_cavity(context,case)
        self.assertFalse(result["all_old_tetrahedra_positive"])
        self.assertFalse(result["strict_convex_boundary_bijection_certified"])

    def test_nonplanar_ring_can_keep_positive_cells_without_convex_certificate(self):
        context,case=octahedron();context["points"][3]=(-1.0,0.0,3.0)
        result=worker.convex_edge_cavity(context,case)
        # The central-edge determinants depend only on equatorial x,y here.
        # Pole5 lies inside the new hull, so its cone facets cannot all strictly support.
        self.assertTrue(result["all_old_tetrahedra_positive"])
        self.assertFalse(result["strict_convex_boundary_bijection_certified"])
        self.assertIn("strict convex supporting-facet certificate unresolved",result["reasons"])

    def test_skinny_convex_case_refuses_unchanged_quality(self):
        context,case=octahedron(1/1024)
        cavity,result=first_candidate(context,case)
        self.assertTrue(cavity["old_embedded_convex_filling_certified"])
        self.assertTrue(result["local_embedded_convex_filling_certified"])
        self.assertFalse(result["all_replacement_exact_quality_gates_passed"])
        self.assertIn("replacement quality/orientation failure",result["reasons"])
        # For a pole and three ring vertices, D^2=4h^2, S>=8, T>=4;
        # hence Q^2<=4.5h^2<1/100. Strict embedding does not imply quality.

    def test_incomplete_disk_refuses_full_boundary_and_exact_volume(self):
        context,case=octahedron();cavity=worker.convex_edge_cavity(context,case)
        result=worker.screen_edge_candidate(context,cavity,((1,2,3),),1)
        self.assertFalse(result["abstract_suspension_of_triangulated_disk_ball"])
        self.assertFalse(result["oriented_boundary_equal"])
        self.assertEqual(result["signed_volume"],worker.rational(Fraction(2,3)))
        self.assertFalse(result["exact_signed_volume_equal"])
        self.assertFalse(result["local_embedded_convex_filling_certified"])

    def test_repeated_triangle_cannot_be_a_multiplicity_two_filling(self):
        context,case=octahedron();cavity=worker.convex_edge_cavity(context,case)
        result=worker.screen_edge_candidate(context,cavity,((1,2,3),(1,3,4),(1,2,3)),1)
        self.assertTrue(result["all_replacement_exact_quality_gates_passed"])
        self.assertTrue(result["duplicate_replacement_four_sets"])
        self.assertFalse(result["abstract_suspension_of_triangulated_disk_ball"])
        self.assertFalse(result["oriented_boundary_equal"])
        self.assertFalse(result["local_embedded_convex_filling_certified"])

    def test_protected_history_refuses_otherwise_valid_replacement(self):
        context,case=octahedron();context["protected_cells"]={101}
        cavity,result=first_candidate(context,case)
        self.assertTrue(result["local_embedded_convex_filling_certified"])
        self.assertFalse(cavity["protected_prior_cells_disjoint"])
        self.assertFalse(result["local_finite_predicates_passed"])

    def test_existing_complement_cell_and_feature_are_not_silently_reused(self):
        context,case=octahedron();context["cells"][999]=(5,1,2,3)
        _,result=first_candidate(context,case)
        self.assertEqual(result["observed_unchanged_cell_duplicates"],
                         [dict(node_tags=[1,2,3,5],existing_tetrahedron_tag=999)])
        self.assertIn("introduced feature already present in observed complement",result["reasons"])
        self.assertFalse(result["local_finite_predicates_passed"])

    def test_missing_owner_evidence_is_unavailable_even_for_analytic_octahedron(self):
        context,case=octahedron();case["owner_scope_complete"]=False
        result=worker.convex_edge_cavity(context,case)
        self.assertFalse(result["link"]["valid"])
        self.assertFalse(result["old_embedded_convex_filling_certified"])
        self.assertIn("complete central-seed owner coverage unavailable",result["reasons"])

    def test_duplicate_proposals_with_disjoint_removals_are_a_distinct_conflict(self):
        # Association-level records only, not an embedded-cavity assertion.
        cases=[dict(case=dict(case_ID="A",removed_cell_tags=[10])),
               dict(case=dict(case_ID="B",removed_cell_tags=[20]))]
        candidates=[dict(candidate_ID="A:1",case_ID="A",replacement_cells=[[1,2,3,4]]),
                    dict(candidate_ID="B:1",case_ID="B",replacement_cells=[[4,3,2,1]])]
        result=worker.complete_conflict_relations(cases,candidates)
        self.assertEqual(result["cross_case_removed_cell_conflict_products"],[])
        self.assertEqual(result["duplicate_proposed_cell_cliques"],
                         [dict(unordered_four_set=[1,2,3,4],candidate_IDs=["A:1","B:1"])])
        self.assertEqual(result["distinct_conflicting_candidate_pair_count"],1)

    def test_factorized_relations_preserve_exact_pair_union(self):
        cases=[dict(case=dict(case_ID="A",removed_cell_tags=[10])),
               dict(case=dict(case_ID="B",removed_cell_tags=[10,20]))]
        candidates=[dict(candidate_ID=c+":"+str(i),case_ID=c,replacement_cells=[[1,2,3,4]])
                    for c in ("A","B") for i in (2,10)]
        result=worker.complete_conflict_relations(cases,candidates)
        self.assertEqual(result["distinct_conflicting_candidate_pair_count"],6)
        self.assertEqual(len(result["within_case_conflict_cliques"]),2)
        self.assertEqual(len(result["cross_case_removed_cell_conflict_products"]),1)

    def test_all_words_fixed_and_local_pass_does_not_close_global_evidence(self):
        context,case=octahedron();before=worker.canonical_bytes(worker.context_snapshot(context))
        _,result=first_candidate(context,case)
        self.assertEqual(before,worker.canonical_bytes(worker.context_snapshot(context)))
        self.assertEqual(context["words"][1][1],"-0x0.0p+0")
        self.assertTrue(result["local_finite_predicates_passed"])
        self.assertIsNone(result["complete_application_eligibility"])
        self.assertFalse(result["mesh_application_authorized"])
        self.assertFalse(result["global_embedding_and_nonoverlap_accepted"])
        self.assertTrue(any(r["global_missing_owner_absence"] is None
                            for r in result["introduced_feature_owner_rows"]))


if __name__=="__main__":
    unittest.main(verbosity=2)
