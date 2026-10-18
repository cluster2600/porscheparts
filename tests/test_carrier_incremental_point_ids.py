from fractions import Fraction as Q
import json
import math
from pathlib import Path
import sys
import unittest

try:import shapely
except ImportError:shapely=None
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
AVAILABLE=shapely is not None and hasattr(shapely,'constrained_delaunay_triangles')
if AVAILABLE:
    import indexed_combinatorial_interfaces as original
    import incremental_combinatorial_interfaces_ids as ids


@unittest.skipUnless(AVAILABLE,'Constrained-triangulation runtime required')
class IncrementalPointIds(unittest.TestCase):
    def test_identity_and_order_are_exact_despite_nonlexicographic_insertion(self):
        points=[(Q(4),Q(0)),(Q(2),Q(0)),(Q(-.1),Q(10)),(Q(0),Q(0)),(Q(1e-300),Q(1))]
        registry=ids._Points();identities=[registry.identity(p) for p in points]
        actual=[registry.coordinates[i] for i in sorted(identities,key=lambda i:registry.keys[i])]
        self.assertEqual(actual,sorted(points))
        self.assertEqual(registry.identity(tuple(points[0])),identities[0])

    def test_nondyadic_wrong_shape_and_nonfinite_encoding_are_refused(self):
        registry=ids._Points()
        for point in [(Q(1,3),Q(0)),(Q(0),Q(0),Q(0)),(0.,0.),(Q(2)**1025,Q(0))]:
            with self.subTest(point=str(point)[:60]),self.assertRaises(ValueError):registry.identity(point)
        self.assertEqual(registry.coordinates,[])

    def test_zero_normalization_and_neighboring_ieee_values_keep_exact_identity(self):
        registry=ids._Points()
        self.assertEqual(registry.identity((Q(-0.),Q(0))),registry.identity((Q(0.),Q(0))))
        a=registry.identity((Q(1.),Q(0)))
        b=registry.identity((Q(math.nextafter(1.,2.)),Q(0)))
        self.assertNotEqual(a,b)
        self.assertLess(registry.keys[a],registry.keys[b])

    def test_cancelled_endpoints_and_nonlexicographic_ids_preserve_subdivision(self):
        registry=ids._Points();line=ids._Line(0,registry)
        p=[(Q(i),Q(0)) for i in [0,2,4,10]]
        line.add(p[1],p[2]);line.add(p[2],p[1]);line.materialize()
        self.assertEqual(line.atoms,{})
        line.add(p[0],p[3]);line.materialize()
        actual={(registry.coordinates[a],registry.coordinates[b]):n for (a,b),n in line.atoms.items()}
        self.assertEqual(actual,{(a,b):1 for a,b in zip(p[:-1],p[1:])})

    def test_two_cycles_keep_the_original_lexicographic_start_and_order(self):
        registry=ids._Points()
        rings=[[(Q(10),Q(0)),(Q(11),Q(0)),(Q(10),Q(1))],
               [(Q(0),Q(0)),(Q(1),Q(0)),(Q(0),Q(1))]]
        encoded=[[registry.identity(p) for p in ring] for ring in rings]
        boundary=ids._chain(encoded,registry)
        cycles=ids._cycles(boundary,registry)
        actual=[[registry.coordinates[i] for i in ring] for ring in cycles]
        expected=original._BASE._cycles(original._BASE._BAND._chain(rings))
        self.assertEqual(actual,expected)

    def test_all_five_complete_surfaces_and_full_receipts_are_identical(self):
        fixture=json.loads((SOURCE/'combinatorial-evidence/fixtures.json').read_text())
        self.assertEqual([r['name'] for r in fixture['cases']],['box','hole','separated_lower','left','right'])
        for case in fixture['cases']:
            with self.subTest(name=case['name']):
                domain=shapely.from_wkb(case['source_domain_geometry_wkb_hex'])
                a,ar=original.construct(domain,case['attested_source_interfaces'],.2)
                b,br,stats=ids.construct_with_statistics(domain,case['attested_source_interfaces'],.2)
                self.assertEqual(a.wkb,b.wkb);self.assertEqual(ar,br)
                self.assertEqual(stats['full_recompute_fallbacks'],0)

    def test_private_assembly_restored_after_reentrant_refusal(self):
        construct=ids._OLD._INDEX.construct
        ids._OLD._INDEX.construct=lambda d,i,p:ids.construct(d,i,p)
        try:
            with self.assertRaisesRegex(ValueError,'reentrant'):
                ids.construct(shapely.box(0,0,10,10),dict(upper=[],lower=[]),.2)
            self.assertIs(ids._OLD._BASE._assemble,ids._OLD._ORIGINAL_ASSEMBLE)
        finally:ids._OLD._INDEX.construct=construct

    def test_rejected_new_ids_never_change_the_next_accepted_surface(self):
        p0,p1,p2,p3,m=[tuple(Q(c) for c in p) for p in [(0,0),(2,0),(2,2),(0,2),(1,1)]]
        source=[[p0,p1,m],[p1,p2,m],[p2,p3,m],[p3,p0,m]]
        state=ids._Assembly(source);prefix=list(source)
        trials=[[[p0,(Q(1),Q(-1)),p1]],[[p1,(Q(3),Q(1)),p2]],
                [[m,(Q(3,2),Q(1)),(Q(1),Q(3,2))]],[[p2,(Q(1),Q(3)),p3]],[]]
        def outcome(function,triangles):
            try:
                polygon,area=function(triangles)
                return ('accepted',polygon.wkb,area)
            except ValueError as error:return ('rejected',str(error),getattr(error,'receipt',None))
        for addition in trials:
            candidate=prefix+addition
            expected=outcome(ids._OLD._ORIGINAL_ASSEMBLE,candidate)
            self.assertEqual(outcome(state,candidate),expected)
            if expected[0]=='accepted':prefix=candidate
        self.assertEqual(state.statistics['rejected_trials'],2)


if __name__=='__main__':unittest.main()
