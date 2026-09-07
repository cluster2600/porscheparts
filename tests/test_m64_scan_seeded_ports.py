"""Routing mathematics and native witnesses, not physical head validation."""
import importlib.util
import copy
import contextlib
import io
import math
from pathlib import Path
import sys
import unittest
from unittest import mock

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

    def test_trunk_interpolation_cli_default_and_explicit(self):
        arguments=['ports']
        for key in ('body','body-build','repair-report','interfaces','module-build','output'):
            arguments.extend(['--'+key,'unused-private-fixture'])
        for key in ('body-sha256','interfaces-sha256'):
            arguments.extend(['--'+key,'0'*64])
        for extra,expected in [([], 'smooth'),(['--trunk-interpolation','smooth'], 'smooth'),
                               (['--trunk-interpolation','ruled'], 'ruled'),
                               (['--trunk-interpolation','bounded-c1'], 'bounded-c1')]:
            with mock.patch.object(sys,'argv',arguments+extra), \
                 mock.patch.object(ports.resource,'setrlimit'), \
                 mock.patch.object(ports,'run',return_value=0) as execute:
                self.assertEqual(ports.main(),0)
                self.assertEqual(execute.call_args.args[0].trunk_interpolation,expected)
        with mock.patch.object(sys,'argv',arguments+['--trunk-interpolation','unknown']), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            ports.main()
        self.assertEqual(caught.exception.code,2)

    def test_ruled_flag_is_explicit_boolean(self):
        with self.assertRaisesRegex(ValueError,'Boolean'):
            ports.loft(None,{},[],ruled='smooth')

    def test_trunk_selector_preserves_explicit_method_and_rejects_unknown(self):
        for mode in ('smooth', 'ruled'):
            with mock.patch.object(ports, 'loft', return_value='witness') as loft:
                shape, quality = ports.make_trunk(None, {}, ['station'], mode)
                self.assertEqual(shape, 'witness')
                self.assertEqual(quality['method'], mode)
                self.assertFalse(quality['C1_claimed'])
                loft.assert_called_once_with(None, {}, ['station'], ruled=mode == 'ruled')
        with self.assertRaisesRegex(ValueError, 'unknown trunk'):
            ports.make_trunk(None, {}, [], 'implicit')

    def test_native_bounded_c1_trunk_selector(self):
        if importlib.util.find_spec('OCP') is None:
            self.skipTest('OCP native witness requires qualified CAD runtime')
        cad=ports.design.CAD(); api=ports.native()
        stations=[{'center':[0., y, 0.], 'normal':[0., 1., 0.], 'radius':2.}
                  for y in (0., 3., 10.)]
        with mock.patch.object(ports, 'loft', side_effect=AssertionError('global loft forbidden')):
            shape, quality = ports.make_trunk(cad, api, stations, 'bounded-c1')
        self.assertTrue(cad.valid(shape))
        self.assertEqual(cad.indexed(shape, cad.TopAbs_SOLID).Extent(), 1)
        self.assertLessEqual(quality['volume_relative_error'], 1e-7)
        self.assertTrue(quality['native_quality']['native_C1_U_and_V_all_quarters'])
        self.assertFalse(quality['branch_trunk_boolean_junction_C1_claimed'])

    def test_bounded_selector_rejects_wrong_or_nonfinite_volume(self):
        import build_bounded_c1_trunk as bounded
        stations=[{'center':[0., y, 0.], 'normal':[0., 1., 0.], 'radius':2.}
                  for y in (0., 3., 10.)]
        for volume in (0., 41*math.pi, math.nan, math.inf):
            with mock.patch.object(bounded, 'construct_native', return_value=(
                    'witness', {'signed_volume_adaptive_integration':volume})):
                with self.assertRaisesRegex(ValueError, 'analytic volume'):
                    ports.make_trunk(None, {}, stations, 'bounded-c1')

    def test_native_ruled_trunk_preserves_station_envelope(self):
        if importlib.util.find_spec('OCP') is None:
            self.skipTest('OCP native witness requires qualified CAD runtime')
        cad=ports.design.CAD(); api=ports.native()
        stations=[{'center':[x,0.,z],'normal':[0.,0.,1.],'radius':r}
                  for x,z,r in [(0.,0.,2.),(1.,3.,3.),(-1.,7.,1.5),(0.,12.,2.5)]]
        original=copy.deepcopy(stations)
        factory=mock.Mock(wraps=api['BRepOffsetAPI_ThruSections'])
        with mock.patch.dict(api,{'BRepOffsetAPI_ThruSections':factory}):
            ruled=ports.loft(cad,api,stations,ruled=True)
            self.assertEqual(factory.call_args.args,(True,True,1e-6))
            smooth=ports.loft(cad,api,stations)
            self.assertEqual(factory.call_args.args,(True,False,1e-6))
        self.assertEqual(stations,original)
        for shape in (ruled,smooth):
            self.assertTrue(cad.valid(shape))
            self.assertEqual(cad.indexed(shape,cad.TopAbs_SOLID).Extent(),1)
            self.assertGreater(cad.volume(shape),0.)
        bounds=ports.bbox(api,ruled)
        expected=[min(s['center'][0]-s['radius'] for s in stations),
                  -max(s['radius'] for s in stations),0.,
                  max(s['center'][0]+s['radius'] for s in stations),
                  max(s['radius'] for s in stations),12.]
        # A synthetic envelope witness only; the private head still requires
        # its own BOP, skin-opening and wall-thickness checks after cutting.
        for actual,limit in zip(bounds,expected):
            self.assertAlmostEqual(actual,limit,delta=1e-5)

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
