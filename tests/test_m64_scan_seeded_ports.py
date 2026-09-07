"""Routing mathematics and native witnesses, not physical head validation."""
import importlib.util
import copy
import math
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source'
sys.path.insert(0,str(SOURCE))
import build_scan_seeded_ports as ports


class RoutingTests(unittest.TestCase):
    def registered_fixture(self):
        p=ports.design.Parameters()
        rows=[]
        for spec in ports.design.valve_specs(p):
            x,y,z=spec['center']; angle=math.radians(spec['axis_angle_deg'])
            rows.append({'name':spec['name'],'axis_origin':[y,-x,z+3.],
                         'axis_direction':[0.,-math.sin(angle),math.cos(angle)],
                         'seat_OD':spec['diameter_mm']+3.,'guide_OD':11.,
                         'seat_axial_interval':[.5,6.],'guide_axial_interval':[20.,55.]})
        return p,rows

    def test_exact_registered_axes(self):
        p,rows=self.registered_fixture()
        ports.check_registered_axes(p,rows)
        ports.check_registered_axes(p,list(reversed(rows)))

    def test_reject_mixed_axis_or_module(self):
        p,rows=self.registered_fixture()
        altered=copy.deepcopy(rows); altered[0]['axis_origin'][0]+=.1
        with self.assertRaises(ValueError): ports.check_registered_axes(p,altered)
        altered=copy.deepcopy(rows); altered[0]['axis_direction'][1]*=2.
        with self.assertRaises(ValueError): ports.check_registered_axes(p,altered)
        altered=copy.deepcopy(rows); altered[1]['name']=altered[0]['name']
        with self.assertRaises(ValueError): ports.check_registered_axes(p,altered)
        altered=copy.deepcopy(rows); altered[0]['seat_OD']+=1.
        with self.assertRaises(ValueError): ports.check_registered_axes(p,altered)

    def test_seed_coordinates_already_in_ABC(self):
        data={'combustion_interface':{'chamber_step':{'center':[10.,20.],'plane_C':30.}},
              'frame_rows_A_B_C':[[0,1,0],[0,0,1],[1,0,0]],
              'port_sections':{'high_B':[
                  {'center':[12.,31.],'plane_B':40.,'diameter_obj_units':8.,'fit_p95_obj_units':.3,'inliers':20},
                  {'center':[13.,32.],'plane_B':35.,'diameter_obj_units':6.,'fit_p95_obj_units':.2,'inliers':15}]}}
        result=ports.seed_sections(data,'high_B')
        self.assertEqual(result[0]['center'],[3.,15.,-2.])
        self.assertEqual(result[1]['center'],[2.,20.,-1.])
        self.assertEqual(result[0]['radius'],3.)
        self.assertEqual(result[0]['fit_p95_scan_units'],.2)

    def test_low_side_orders_towards_outside(self):
        data={'combustion_interface':{'chamber_step':{'center':[0.,0.],'plane_C':0.}},
              'port_sections':{'low_B':[{'center':[0.,-5.],'plane_B':b,'diameter_obj_units':8.,
                                        'fit_p95_obj_units':.1,'inliers':20} for b in (-30.,-10.,-20.)]}}
        result=ports.seed_sections(data,'low_B')
        self.assertEqual([r['center'][1] for r in result],[-10.,-20.,-30.])
        self.assertEqual(result[0]['normal'],[0.,-1.,0.])

    def test_branch_endpoint_constraints(self):
        seed={'center':[0.,40.,20.],'radius':8.,'normal':[0.,1.,0.]}
        stations,controls=ports.branch_stations([10.,0.,0.],[0.,0.,1.],5.,seed,12.,10.)
        self.assertEqual(stations[0]['center'],[10.,0.,0.])
        self.assertEqual(stations[-1]['center'],seed['center'])
        self.assertEqual(stations[0]['normal'],[0.,0.,1.])
        self.assertEqual(stations[-1]['normal'],[0.,1.,0.])
        self.assertEqual(stations[0]['radius'],5.)
        self.assertEqual(stations[-1]['radius'],8.)
        self.assertTrue(all(5.<=s['radius']<=8. for s in stations))

    def test_invalid_inputs_fail(self):
        for direction in ([0.,0.,0.],[math.nan,0.,1.]):
            with self.assertRaises(ValueError): ports.unit(direction)
        with self.assertRaises(ValueError): ports.bezier([[0.,0.,0.]]*4,1.1)

    def test_native_loft_and_nondestructive_boolean(self):
        if importlib.util.find_spec('OCP') is None:
            self.skipTest('OCP native witness requires qualified CAD runtime')
        cad=ports.design.CAD(); api=ports.native()
        cylinder=ports.loft(cad,api,[{'center':[0.,0.,z],'normal':[0.,0.,1.],'radius':2.} for z in (0.,5.,10.)])
        # ThruSections approximates the circular loft at 1e-6 length tolerance;
        # this is a numerical witness, not an exact symbolic cylinder.
        self.assertTrue(math.isclose(cad.volume(cylinder),40*math.pi,rel_tol=1e-7))
        half=cad.BRepPrimAPI_MakeCylinder(2.,5.).Shape()
        result=ports.operation(cad,api['BRepAlgoAPI_Cut'],cylinder,half)
        self.assertTrue(math.isclose(cad.volume(result),20*math.pi,rel_tol=1e-7))
        self.assertTrue(math.isclose(cad.volume(cylinder),40*math.pi,rel_tol=1e-7))
        self.assertEqual(cad.indexed(result,cad.TopAbs_SOLID).Extent(),1)


if __name__=='__main__': unittest.main()
