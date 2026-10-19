from fractions import Fraction as Q
import json
from pathlib import Path
import sys
import unittest

try:
    import shapely
except ImportError:
    shapely = None
SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
AVAILABLE = shapely is not None and hasattr(shapely,'constrained_delaunay_triangles')
if AVAILABLE:
    import indexed_combinatorial_interfaces as old
    import incremental_combinatorial_interfaces as new


@unittest.skipUnless(AVAILABLE,'Constrained-triangulation runtime required')
class IncrementalInterfacesTests(unittest.TestCase):
    def test_integer_shoelace_is_the_exact_fraction_sum(self):
        for points in [[(Q(0),Q(0)),(Q(1,3),Q(1,5)),(Q(8,7),Q(6,11))],
                       [(Q(.1),Q(10.2)),(Q(5.4),Q(-.1)),(Q(8),Q(7))]]:
            self.assertEqual(new.exact_area(points),old._BASE._BAND._signed_area(points))
            self.assertEqual(new.exact_area(list(reversed(points))),-new.exact_area(points))

    def test_cancelled_endpoints_remain_available_for_later_subdivision(self):
        points=[(Q(i),Q(0)) for i in [0,2,4,10]]
        line=new._Line(0)
        line.add(points[1],points[2]);line.add(points[2],points[1]);line.materialize()
        self.assertEqual(line.atoms,{})
        line.add(points[0],points[3]);line.materialize()
        self.assertEqual(line.atoms,{(a,b):1 for a,b in zip(points[:-1],points[1:])})

    def test_accept_reject_sequence_matches_full_recomputation_without_leaking_trials(self):
        p0,p1,p2,p3,m=[tuple(Q(c) for c in p) for p in [(0,0),(2,0),(2,2),(0,2),(1,1)]]
        source=[[p0,p1,m],[p1,p2,m],[p2,p3,m],[p3,p0,m]]
        state=new._Assembly(source);prefix=list(source)
        additions=[[[p0,(Q(1),Q(-1)),p1]],[[p1,(Q(3),Q(1)),p2]],
                   [[m,(Q(3,2),Q(1)),(Q(1),Q(3,2))]],[[p2,(Q(1),Q(3)),p3]],[]]
        def outcome(function,triangles):
            try:
                polygon,area=function(triangles)
                return ('accepted',polygon.wkb,area)
            except ValueError as error:
                return ('rejected',str(error),getattr(error,'receipt',None))
        for addition in additions:
            candidate=prefix+addition
            expected=outcome(new._ORIGINAL_ASSEMBLE,candidate)
            self.assertEqual(outcome(state,candidate),expected)
            if expected[0]=='accepted':prefix=candidate
        self.assertEqual(state.statistics['rejected_trials'],2)
        self.assertEqual(state.statistics['full_recompute_fallbacks'],0)

    def test_complete_five_surfaces_and_receipts_match_the_frozen_constructor(self):
        fixture=json.loads((SOURCE/'combinatorial-evidence/fixtures.json').read_text())
        self.assertEqual([r['name'] for r in fixture['cases']],['box','hole','separated_lower','left','right'])
        for case in fixture['cases']:
            with self.subTest(name=case['name']):
                domain=shapely.from_wkb(case['source_domain_geometry_wkb_hex'])
                a,ar=old.construct(domain,case['attested_source_interfaces'],.2)
                b,br,statistics=new.construct_with_statistics(domain,case['attested_source_interfaces'],.2)
                self.assertEqual(a.wkb,b.wkb);self.assertEqual(ar,br)
                self.assertEqual(statistics['full_recompute_fallbacks'],0)
                self.assertIs(new._BASE._assemble,new._ORIGINAL_ASSEMBLE)

    def test_positive_triangle_overlap_is_refused_identically(self):
        triangle=[(Q(0),Q(0)),(Q(2),Q(0)),(Q(0),Q(2))]
        state=new._Assembly([triangle])
        with self.assertRaisesRegex(ValueError,'multiplicity'):
            state([triangle,triangle])
        self.assertEqual(len(state.prefix),1)


if __name__=='__main__':unittest.main()
