"""Exact interpolation witnesses, not Porsche geometry or physical validation."""
import copy
from fractions import Fraction as F
import importlib.util
import math
from pathlib import Path
import random
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source'
sys.path.insert(0,str(SOURCE))
import build_bounded_c1_trunk as trunk


def fixture(sign=1):
    return [{'center':[x,sign*y,z],'radius':r,'normal':[0,sign,0]}
            for x,y,z,r in [(0.,0.,0.,2.),(.7,3.,.1,2.5),(-.2,8.,.4,1.8),(.1,14.,0.,2.1)]]


def generated_fixtures():
    """Eight reproducible synthetic models, unrelated to private scan data."""
    rng=random.Random(607)
    for count in (2,3,4,6):
        for sign in (-1,1):
            axial=-31.25;stations=[]
            for _ in range(count):
                axial+=rng.uniform(.1,8.)
                stations.append({'center':[rng.uniform(-5.,5.),sign*axial,rng.uniform(-3.,3.)],
                                 'radius':rng.uniform(.4,5.),'normal':[0,sign,0]})
            yield stations


class BoundedC1Tests(unittest.TestCase):
    def test_station_exactness_and_preservation(self):
        for sign in (-1,1):
            source=fixture(sign);saved=copy.deepcopy(source);model=trunk.build_model(source)
            self.assertEqual(source,saved)
            for s,point,slope in zip(model['axial'],model['rows'],model['slopes']):
                self.assertEqual(trunk.evaluate(model,s),(point,slope))

    def test_all_bernstein_bounds_exact(self):
        model=trunk.build_model(fixture())
        for segment in model['segments']:
            for feature in trunk.FEATURES:
                lo,hi=sorted((trunk.dot(segment[0],feature),trunk.dot(segment[-1],feature)))
                self.assertTrue(all(lo<=trunk.dot(p,feature)<=hi for p in segment))
        self.assertEqual(trunk.analytic_report(model)['design_Bernstein_bounds_violation_exact'],'0')

    def test_C1_exact_unequal_intervals(self):
        model=trunk.build_model(fixture());segs=model['segments'];xs=model['axial']
        for i in range(1,len(segs)):
            left=tuple(3*(a-b)/(xs[i]-xs[i-1]) for a,b in zip(segs[i-1][3],segs[i-1][2]))
            right=tuple(3*(a-b)/(xs[i+1]-xs[i]) for a,b in zip(segs[i][1],segs[i][0]))
            self.assertEqual(left,right)

    def test_exact_bspline_not_refit(self):
        model=trunk.build_model(fixture());knots,coeff=trunk.bspline_coefficients(model)
        for i in range(81):
            x=model['axial'][0]+(model['axial'][-1]-model['axial'][0])*F(i,80)
            values=tuple(sum(trunk.basis(knots,j,3,x)*c[k] for j,c in enumerate(coeff)) for k in range(3))
            self.assertEqual(values,trunk.evaluate(model,x)[0])

    def test_generated_exact_hermite_and_greville_identity(self):
        model_count=point_count=0
        for stations in generated_fixtures():
            model=trunk.build_model(stations);knots,coeff=trunk.bspline_coefficients(model)
            greville=[sum(knots[i+1:i+4])/3 for i in range(len(coeff))]
            model_count+=1
            for j in range(len(stations)-1):
                for k in range(13):
                    x=model['axial'][j]+(model['axial'][j+1]-model['axial'][j])*F(k,12)
                    values=tuple(sum(trunk.basis(knots,i,3,x)*p[d] for i,p in enumerate(coeff)) for d in range(3))
                    derivatives=tuple(sum(trunk.basis_d1(knots,i,3,x)*p[d] for i,p in enumerate(coeff)) for d in range(3))
                    self.assertEqual((values,derivatives),trunk.evaluate(model,x))
                    self.assertEqual(sum(trunk.basis(knots,i,3,x)*s for i,s in enumerate(greville)),x)
                    self.assertEqual(sum(trunk.basis_d1(knots,i,3,x)*s for i,s in enumerate(greville)),1)
                    point_count+=1
        self.assertEqual((model_count,point_count),(8,286))

    def test_float_pole_certificate_rejects_adversarial_mutations(self):
        rejected_bound=rejected_orientation=0
        for stations in generated_fixtures():
            model=trunk.build_model(stations);knots,coeff=trunk.bspline_coefficients(model)
            greville=[sum(knots[i+1:i+4])/3 for i in range(len(coeff))]
            rows=[]
            for quarter in trunk.QUARTERS:
                for dx,dz in quarter:
                    rows.append([(float(cx+dx*r),float(model['sign']*s),float(cz+dz*r))
                                 for (cx,cz,r),s in zip(coeff,greville)])
            certificate=trunk.certify_float_poles(model,rows)
            self.assertGreater(certificate['native_signed_dY_lower_bound'],0.)
            outside=copy.deepcopy(rows);point=list(outside[0][1]);point[0]+=1000.;outside[0][1]=tuple(point)
            with self.assertRaises(ValueError):
                trunk.certify_float_poles(model,outside)
            rejected_bound+=1
            # Reflection about the interval midpoint preserves the global Y
            # bounds. Rejection must therefore detect reversed axial motion,
            # not merely a point outside the global bounding box.
            ysum=model['sign']*(model['axial'][0]+model['axial'][-1])
            reversed_y=[[(p[0],float(ysum-F(p[1])),p[2]) for p in row] for row in rows]
            lo,hi=sorted(float(model['sign']*s) for s in (model['axial'][0],model['axial'][-1]))
            self.assertTrue(all(lo<=p[1]<=hi for row in reversed_y for p in row))
            with self.assertRaises(ValueError):
                trunk.certify_float_poles(model,reversed_y)
            rejected_orientation+=1
        self.assertEqual((rejected_bound,rejected_orientation),(8,8))

    def test_pchip_linear_and_extrema(self):
        self.assertEqual(trunk.pchip_slopes([0,2,7],[0,4,14]),[F(2)]*3)
        self.assertEqual(trunk.pchip_slopes([0,2,7],[0,4,0])[1],0)
        self.assertEqual(trunk.pchip_slopes([0,2],[1,5]),[F(2)]*2)

    def test_no_extrapolation_or_unsupported_axes(self):
        model=trunk.build_model(fixture())
        with self.assertRaises(ValueError): trunk.evaluate(model,-1)
        for mutation in ('axis','order','radius','nan'):
            source=fixture()
            if mutation=='axis': source[1]['normal']=[.1,1.,0.]
            if mutation=='order': source[1]['center'][1]=0.
            if mutation=='radius': source[1]['radius']=0.
            if mutation=='nan': source[1]['center'][0]=math.nan
            with self.assertRaises(ValueError): trunk.build_model(source)

    def test_volume_cylinder_exact_polynomial(self):
        source=[{'center':[0.,y,0.],'radius':2.,'normal':[0.,1.,0.]} for y in (0.,3.,10.)]
        model=trunk.build_model(source)
        self.assertEqual(model['radius_square_integral'],F(40))

    def test_native_true_c1_solid(self):
        if importlib.util.find_spec('OCP') is None:
            self.skipTest('requires qualified native OCCT runtime')
        import build_scan_seeded_ports as ports
        cad=ports.design.CAD()
        for sign in (-1,1):
            model=trunk.build_model(fixture(sign));solid,quality=trunk.construct_native(model)
            self.assertTrue(quality['native_C1_U_and_V_all_quarters'])
            self.assertTrue(quality['BRepCheck_valid'])
            self.assertEqual(quality['solid_count'],1)
            self.assertEqual(quality['free_edges'],0)
            self.assertFalse(ports.bop_check(solid)['has_faulty'])
            expected=math.pi*float(model['radius_square_integral'])
            self.assertAlmostEqual(quality['signed_volume_adaptive_integration']/expected,1.,delta=1e-7)
            self.assertLessEqual(quality['stored_float_poles_bound_certificate']['global_bound_rounding_allowance'],1e-10)
            self.assertGreater(quality['stored_float_poles_bound_certificate']['native_signed_dY_lower_bound'],0.)
            # The exact stored-pole certificate above bounds the full native
            # surface. BRepBndLib's padded/rounded box is kept diagnostic;
            # it is not substituted for that stronger analytic certificate.
            self.assertTrue(quality['stored_float_poles_bound_certificate']['bound_not_grid_sampled'])

    def test_native_certificate_matches_post_sewing_poles_weights_and_knots(self):
        if importlib.util.find_spec('OCP') is None:
            self.skipTest('requires qualified native OCCT runtime')
        from OCP.BRep import BRep_Tool
        from OCP.Geom import Geom_BSplineSurface,Geom_Plane
        from OCP.TopoDS import TopoDS
        import build_four_valve_distribution as design
        cad=design.CAD()
        for sign in (-1,1):
            model=trunk.build_model(fixture(sign));solid,quality=trunk.construct_native(model)
            faces=cad.indexed(solid,cad.TopAbs_FACE);rows=[];lateral_count=cap_count=0
            for fi in range(1,faces.Extent()+1):
                surface=BRep_Tool.Surface_s(TopoDS.Face_s(faces.FindKey(fi)))
                if isinstance(surface,Geom_Plane):
                    cap_count+=1
                    continue
                self.assertIsInstance(surface,Geom_BSplineSurface)
                lateral_count+=1
                self.assertEqual((surface.UDegree(),surface.VDegree()),(2,3))
                self.assertTrue(surface.IsCNu(1) and surface.IsCNv(1))
                self.assertEqual([surface.UKnot(i) for i in range(1,surface.NbUKnots()+1)],[0.,1.])
                self.assertEqual([surface.UMultiplicity(i) for i in range(1,surface.NbUKnots()+1)],[3,3])
                self.assertEqual([surface.VKnot(i) for i in range(1,surface.NbVKnots()+1)],
                                 [float(v) for v in model['axial']])
                self.assertEqual([surface.VMultiplicity(i) for i in range(1,surface.NbVKnots()+1)],
                                 [4]+[2]*(len(model['axial'])-2)+[4])
                self.assertEqual((surface.NbUPoles(),surface.NbVPoles()),(3,2*len(model['axial'])))
                for i in range(1,surface.NbUPoles()+1):
                    weights=[surface.Weight(i,j) for j in range(1,surface.NbVPoles()+1)]
                    self.assertEqual(len(set(weights)),1)
                    self.assertGreater(weights[0],0.)
                    rows.append([surface.Pole(i,j).Coord() for j in range(1,surface.NbVPoles()+1)])
            self.assertEqual((lateral_count,cap_count),(4,2))
            self.assertEqual(trunk.certify_float_poles(model,rows),
                             quality['stored_float_poles_bound_certificate'])


if __name__=='__main__':
    unittest.main()
