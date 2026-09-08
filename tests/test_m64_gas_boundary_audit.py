import importlib.util
import copy
import math
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake'
sys.path.insert(0,str(SOURCE))
import audit_gas_boundaries as audit


class GapTests(unittest.TestCase):
    def test_diametral_clearance_is_halved_and_never_zero(self):
        gap=audit.annular_section(6.,.03,35.)
        self.assertAlmostEqual(gap['radial_gap'],.015)
        self.assertAlmostEqual(gap['area'],math.pi*(3.015**2-3**2))
        self.assertGreater(gap['volume'],0.)
        self.assertTrue(gap['zero_leakage_cannot_be_inferred_from_positive_gap'])
        for bad in (0.,-.03,float('nan')):
            with self.assertRaises(ValueError):audit.annular_section(6,bad,35)

    def test_missing_annular_area_or_invalid_fixture_is_rejected(self):
        row={'contact':{'expected_state_area_matches':True,'full_angular_band_native':True},
             'stem_guide':{'native_passage_BRep_valid':True,'native_passage_solids':1,
                'volume_matches_analytic':True,'native_passage_guide_overlap_volume':{'value':0.},
                'lower_area_matches_gap':True,'upper_area_matches_gap':True,
                'lower_annular_face':{'BRep_valid':True},'upper_annular_face':{'BRep_valid':True}}}
        self.assertTrue(audit.boundary_row_pass(row,'exhaust'))
        for label in ('lower','upper'):
            bad=copy.deepcopy(row);bad['stem_guide'][label+'_area_matches_gap']=False
            self.assertFalse(audit.boundary_row_pass(bad,'exhaust'))
            bad=copy.deepcopy(row);bad['stem_guide'][label+'_annular_face']['BRep_valid']=False
            self.assertFalse(audit.boundary_row_pass(bad,'exhaust'))


@unittest.skipUnless(importlib.util.find_spec('OCP'),'native OCP runtime required')
class NativeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.cad=audit.inspection.design.CAD()
        self.p=audit.inspection.design.Parameters().validate()

    def test_fixture_is_only_the_gap_annulus_not_full_guide_bore(self):
        gap=audit.annular_section(6,.03,35)
        shape=audit.annular_face(self.cad,3,3.015,55)
        self.assertTrue(self.cad.valid(shape))
        self.assertAlmostEqual(self.cad.area(shape),gap['area'],places=10)
        self.assertLess(self.cad.area(shape),math.pi*3**2/50)

    def test_native_full_seat_band_disappears_when_valve_is_open(self):
        spec=audit.inspection.design.valve_specs(self.p)[2]
        profiles,_=audit.inspection.design.profiles(self.p,spec)
        valve=self.cad.pose(self.cad.revolve(profiles['valve']),spec)
        seat=self.cad.pose(self.cad.revolve(profiles['seat']),spec)
        closed,_=audit.native_contact(self.cad,valve,seat)
        self.assertAlmostEqual(closed['total_contact_area_scan_units_squared'],audit.contact_area(self.p,spec),places=7)
        self.assertEqual(len(closed['contact_faces']),1)
        self.assertAlmostEqual(closed['contact_faces'][0]['angular_parameter_span_radians'],2*math.pi)
        opened=self.cad.pose(self.cad.revolve(profiles['valve']),spec,6)
        result,_=audit.native_contact(self.cad,opened,seat)
        self.assertEqual(result['total_contact_area_scan_units_squared'],0.)
        self.assertGreater(result['minimum_component_distance'],0.)

    def test_registration_and_lift_are_combined_once(self):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
        from OCP.BRep import BRep_Tool
        from OCP.TopoDS import TopoDS
        spec=audit.inspection.design.valve_specs(self.p)[0]
        vertex=BRepBuilderAPI_MakeVertex(self.cad.gp_Pnt(1,2,3)).Vertex()
        transformed=audit.registered(self.cad,vertex,spec,6)
        point=BRep_Tool.Pnt_s(TopoDS.Vertex_s(transformed))
        angle=math.radians(spec['axis_angle_deg'])
        for actual,expected in zip(point.Coord(),(2,-1+6*math.sin(angle),6-6*math.cos(angle))):
            self.assertAlmostEqual(actual,expected)


if __name__=='__main__':unittest.main()
