#!/usr/bin/env python3
"""Bounded circular C1 trunk, without a global approximation loft.

Design interpolation, not recovery of measured internal Porsche surfaces.
Each Y-normal circle is retained. PCHIP candidate slopes are limited jointly
so the Bernstein controls of cx +/- r, cz +/- r, cx, cz and r remain between
adjacent stations. Exact rational arithmetic proves those polynomial bounds.
Four rational quadratic quarter-circle surfaces share a cubic C1 B-spline in
the monotone axial coordinate. Hermite-to-B-spline conversion is an exact
linear solve, not sampling/refitting or tolerance-based knot removal.

References: scipy.org PchipInterpolator (Fritsch-Butland interior slopes);
OCCT Geom_BSplineSurface rational tensor-product representation.
CLI inputs and every generated CAD/coordinate receipt must remain private.
"""
import argparse
import bisect
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import resource
import time


FEATURES = ((1,0,0), (0,1,0), (0,0,1), (1,0,-1), (1,0,1), (0,1,-1), (0,1,1))
QUARTERS = (((1,0),(1,1),(0,1)), ((0,1),(-1,1),(-1,0)),
            ((-1,0),(-1,-1),(0,-1)), ((0,-1),(1,-1),(1,0)))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def pchip_slopes(x, values):
    """Exact rational arithmetic on the supplied finite binary floats."""
    x, values = list(map(F,x)), list(map(F,values))
    h = [b-a for a,b in zip(x,x[1:])]
    if len(x)<2 or len(x)!=len(values) or min(h)<=0:
        raise ValueError('two or more strictly increasing stations required')
    d = [(b-a)/step for a,b,step in zip(values,values[1:],h)]
    if len(x)==2:
        return [d[0],d[0]]
    slopes = [F(0)]*len(x)
    for i in range(1,len(x)-1):
        if d[i-1]*d[i]>0:
            w1,w2 = 2*h[i]+h[i-1], h[i]+2*h[i-1]
            slopes[i] = (w1+w2)/(w1/d[i-1]+w2/d[i])
    for target,a,b,ha,hb in [(0,d[0],d[1],h[0],h[1]),(-1,d[-1],d[-2],h[-1],h[-2])]:
        slope = ((2*ha+hb)*a-ha*b)/(ha+hb)
        if slope*a<=0:
            slope = F(0)
        elif a*b<0 and abs(slope)>3*abs(a):
            slope = 3*a
        slopes[target] = slope
    return slopes


def build_model(stations):
    if len(stations)<2:
        raise ValueError('at least two circular stations required')
    sign = stations[0]['normal'][1]
    if sign not in (-1,1):
        raise ValueError('only +/-Y-normal circles are supported')
    rows=[]
    for row in stations:
        if row['normal']!=[0,sign,0] or len(row['center'])!=3:
            raise ValueError('all circles must share the same +/-Y normal')
        vals = [*row['center'],row['radius']]
        if not all(math.isfinite(v) for v in vals) or row['radius']<=0:
            raise ValueError('finite centres and positive radii required')
        rows.append(tuple(map(F,(row['center'][0],row['center'][2],row['radius']))))
    axial = [F(sign)*F(row['center'][1]) for row in stations]
    h = [b-a for a,b in zip(axial,axial[1:])]
    if min(h)<=0:
        raise ValueError('station order must be strictly outward; no sorting or refit')
    columns = [pchip_slopes(axial,[row[k] for row in rows]) for k in range(3)]
    slopes = [tuple(column[i] for column in columns) for i in range(len(rows))]
    factors = [F(1)]*len(rows)
    for i,step in enumerate(h):
        for feature in FEATURES:
            a,b = dot(rows[i],feature), dot(rows[i+1],feature)
            lo,hi = min(a,b),max(a,b)
            for node,base,direction in [(i,a,1),(i+1,b,-1)]:
                delta = direction*step*dot(slopes[node],feature)/3
                if delta>0:
                    factors[node] = min(factors[node],(hi-base)/delta)
                elif delta<0:
                    factors[node] = min(factors[node],(lo-base)/delta)
    if any(not 0<=factor<=1 for factor in factors):
        raise ArithmeticError('invalid bound limiter')
    slopes = [tuple(factor*d for d in slope) for factor,slope in zip(factors,slopes)]
    segments=[]
    for i,step in enumerate(h):
        controls = [rows[i],tuple(a+step*d/3 for a,d in zip(rows[i],slopes[i])),
                    tuple(b-step*d/3 for b,d in zip(rows[i+1],slopes[i+1])),rows[i+1]]
        for feature in FEATURES:
            endpoints = [dot(controls[j],feature) for j in (0,3)]
            if any(not min(endpoints)<=dot(point,feature)<=max(endpoints) for point in controls):
                raise ArithmeticError('Bernstein convex-hull certificate failed')
        segments.append(controls)
    radius_square_integral=F(0)
    for step,controls in zip(h,segments):
        radii = [p[2] for p in controls]
        squared = [sum(F(math.comb(3,i)*math.comb(3,k-i),math.comb(6,k))*radii[i]*radii[k-i]
                       for i in range(4) if 0<=k-i<4) for k in range(7)]
        radius_square_integral += step*sum(squared)/7
    return {'sign':int(sign),'axial':axial,'rows':rows,'slopes':slopes,'factors':factors,
            'segments':segments,'radius_square_integral':radius_square_integral}


def evaluate(model, axial):
    s=F(axial); knots=model['axial']
    if not knots[0]<=s<=knots[-1]:
        raise ValueError('no extrapolation permitted')
    i=min(len(knots)-2,bisect.bisect_right(knots,s)-1)
    t=(s-knots[i])/(knots[i+1]-knots[i]); c=model['segments'][i]
    weights=((1-t)**3,3*t*(1-t)**2,3*t*t*(1-t),t**3)
    value=tuple(sum(w*p[k] for w,p in zip(weights,c)) for k in range(3))
    derivative=tuple(3*sum(w*(c[j+1][k]-c[j][k]) for j,w in enumerate(((1-t)**2,2*t*(1-t),t*t)))
                     /(knots[i+1]-knots[i]) for k in range(3))
    return value,derivative


def basis(knots,i,degree,x):
    if degree==0:
        return F(int(knots[i]<=x<knots[i+1] or (x==knots[-1] and knots[i]<x==knots[i+1])))
    a=F(0) if knots[i+degree]==knots[i] else (x-knots[i])/(knots[i+degree]-knots[i])*basis(knots,i,degree-1,x)
    b=F(0) if knots[i+degree+1]==knots[i+1] else (knots[i+degree+1]-x)/(knots[i+degree+1]-knots[i+1])*basis(knots,i+1,degree-1,x)
    return a+b


def basis_d1(knots,i,degree,x):
    a=F(0) if knots[i+degree]==knots[i] else F(degree)/(knots[i+degree]-knots[i])*basis(knots,i,degree-1,x)
    b=F(0) if knots[i+degree+1]==knots[i+1] else F(degree)/(knots[i+degree+1]-knots[i+1])*basis(knots,i+1,degree-1,x)
    return a-b


def solve_exact(matrix,rhs):
    """Small exact Hermite interpolation solve; no fitted sample cloud."""
    n=len(matrix); cols=len(rhs[0]); a=[list(row)+list(values) for row,values in zip(matrix,rhs)]
    for i in range(n):
        pivot=next((j for j in range(i,n) if a[j][i]),None)
        if pivot is None: raise ArithmeticError('singular Hermite basis')
        a[i],a[pivot]=a[pivot],a[i]
        divisor=a[i][i]; a[i]=[v/divisor for v in a[i]]
        for j in range(n):
            if j!=i and a[j][i]:
                scale=a[j][i]; a[j]=[x-scale*y for x,y in zip(a[j],a[i])]
    return [row[n:n+cols] for row in a]


def bspline_coefficients(model):
    axial=model['axial']; repeated=[axial[0]]*4
    for knot in axial[1:-1]: repeated.extend([knot]*2)
    repeated.extend([axial[-1]]*4)
    n=len(repeated)-4; matrix=[]; rhs=[]
    for x,values,slopes in zip(axial,model['rows'],model['slopes']):
        matrix.append([basis(repeated,i,3,x) for i in range(n)]); rhs.append(values)
        matrix.append([basis_d1(repeated,i,3,x) for i in range(n)]); rhs.append(slopes)
    coefficients=solve_exact(matrix,rhs)
    for row,expected in zip(matrix,rhs):
        if tuple(sum(w*c[k] for w,c in zip(row,coefficients)) for k in range(3))!=tuple(expected):
            raise ArithmeticError('exact B-spline conversion failed')
    return repeated,coefficients


def analytic_report(model):
    rows=model['rows']
    return {'station_count':len(rows),'segment_count':len(model['segments']),
            'method':'jointly_bounded_PCHIP_Hermite; exact_rational_Bernstein_certificate',
            'design_Bernstein_bounds_violation_exact':'0',
            'C1_axial_derivatives_shared_exactly':True,'C2_claimed':False,
            'circular_sections_exact_in_mathematical_definition':True,
            'positive_radius_lower_bound':float(min(p[2] for seg in model['segments'] for p in seg)),
            'global_X_bounds_private':[float(min(p[0]-p[2] for p in rows)),float(max(p[0]+p[2] for p in rows))],
            'global_Z_bounds_private':[float(min(p[1]-p[2] for p in rows)),float(max(p[1]+p[2] for p in rows))],
            'slope_limiter_factors_private':[float(f) for f in model['factors']],
            'volume_by_exact_polynomial_integration_times_pi':math.pi*float(model['radius_square_integral']),
            'all_sections_and_order_retained':True,'radius_inflation':False,
            'self_intersection_excluded_for_mathematical_surface':
                'strictly_monotone_Y_and_one_positive_radius_circle_per_Y',
            'not_a_scan_uncertainty_certificate':True}


def certify_float_poles(model,pole_rows):
    """Exact coefficient bound on float-stored rows; no sampling of extrema.

    U weights are positive and independent of V, so the row bounds also bound
    the full rational tensor-product surface. Fractions interpret the actual
    stored binary floats exactly. Rounding allowance is reported separately
    and never changes B-Rep tolerances or the exact design certificate.
    """
    axial=model['axial']; repeated=[axial[0]]*4
    for knot in axial[1:-1]: repeated.extend([knot]*2)
    repeated.extend([axial[-1]]*4)
    n=len(repeated)-4
    basis_values=[[basis(repeated,i,3,s) for i in range(n)] for s in axial]
    basis_derivatives=[[basis_d1(repeated,i,3,s) for i in range(n)] for s in axial]
    bounds=[(min(p[0]-p[2] for p in model['rows']),max(p[0]+p[2] for p in model['rows'])),
            (min(F(model['sign'])*s for s in axial),max(F(model['sign'])*s for s in axial)),
            (min(p[1]-p[2] for p in model['rows']),max(p[1]+p[2] for p in model['rows']))]
    violation=F(0); minimum_signed_dY=None
    for row in pole_rows:
        vectors=[tuple(map(F,p)) for p in row]
        values=[tuple(sum(b*v[k] for b,v in zip(basis_row,vectors)) for k in range(3)) for basis_row in basis_values]
        slopes=[tuple(sum(b*v[k] for b,v in zip(basis_row,vectors)) for k in range(3)) for basis_row in basis_derivatives]
        for j in range(len(axial)-1):
            h=axial[j+1]-axial[j]
            controls=[values[j],tuple(a+h*d/3 for a,d in zip(values[j],slopes[j])),
                      tuple(a-h*d/3 for a,d in zip(values[j+1],slopes[j+1])),values[j+1]]
            for control in controls:
                for value,(lo,hi) in zip(control,bounds): violation=max(violation,lo-value,value-hi)
            derivatives=[F(model['sign'])*3*(b[1]-a[1])/h for a,b in zip(controls,controls[1:])]
            minimum_signed_dY=min(derivatives) if minimum_signed_dY is None else min(minimum_signed_dY,*derivatives)
    if violation>F(1e-10) or minimum_signed_dY<=0:
        raise ValueError('float-stored native surface violates certified bound or monotone Y')
    return {'arithmetic':'exact_rational_on_stored_binary_poles_and_knots',
            'global_bound_rounding_allowance':float(violation),
            'global_bound_rounding_allowance_exact':str(violation),
            'rounding_gate_scan_units':1e-10,'native_signed_dY_lower_bound':float(minimum_signed_dY),
            'native_signed_dY_lower_bound_exact':str(minimum_signed_dY),
            'rational_U_weights_positive_and_independent_of_V':True,
            'bound_not_grid_sampled':True}


def adaptive_volume(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    mass=GProp_GProps()
    estimate=BRepGProp.VolumeProperties_s(shape,mass,1e-11,True,False)
    return mass.Mass(),estimate


def construct_native(model):
    import build_four_valve_distribution as design
    from OCP.Geom import Geom_BSplineSurface
    from OCP.TColgp import TColgp_Array2OfPnt
    from OCP.TColStd import TColStd_Array1OfReal,TColStd_Array1OfInteger,TColStd_Array2OfReal
    from OCP.gp import gp_Pnt,gp_Vec,gp_Pln,gp_Dir
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace,BRepBuilderAPI_MakeEdge,BRepBuilderAPI_MakeWire,BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid
    from OCP.TopoDS import TopoDS
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.BRepLib import BRepLib
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    repeated,coefficients=bspline_coefficients(model); axial=model['axial']; sign=model['sign']
    n=len(coefficients); knots=[float(k) for k in axial]
    def array(values,integer=False):
        result=(TColStd_Array1OfInteger if integer else TColStd_Array1OfReal)(1,len(values))
        for i,value in enumerate(values,1): result.SetValue(i,value)
        return result
    surfaces=[]; stored_pole_rows=[]; sewing=BRepBuilderAPI_Sewing(1e-7,True,True,True,False)
    sample_error=0.; derivative_error=0.; minimum_cross=math.inf
    # Each quarter is smooth in U; keeping it a separate face avoids a formal
    # C0 knot at rational quarter-circle boundaries. Adjacent quarters have
    # identical points and tangents; the single V basis is structurally C1.
    for directions in QUARTERS:
        poles=TColgp_Array2OfPnt(1,3,1,n); weights=TColStd_Array2OfReal(1,3,1,n)
        for i,((dx,dz),weight) in enumerate(zip(directions,(1.,math.sqrt(.5),1.)),1):
            stored_row=[]
            for j,(cx,cz,radius) in enumerate(coefficients,1):
                y=F(sign)*sum(repeated[j:j+3])/3
                point=(float(cx+dx*radius),float(y),float(cz+dz*radius))
                poles.SetValue(i,j,gp_Pnt(*point));stored_row.append(point)
                weights.SetValue(i,j,weight)
            stored_pole_rows.append(stored_row)
        surface=Geom_BSplineSurface(poles,weights,array([0.,1.]),array(knots),array([3,3],True),
                                   array([4]+[2]*(len(knots)-2)+[4],True),2,3,False,False)
        if not surface.IsCNu(1) or not surface.IsCNv(1):
            raise ValueError('native surface is not structurally C1')
        for s,row,slope in zip(axial,model['rows'],model['slopes']):
            for k in range(17):
                u=k/16; b=((1-u)**2,2*u*(1-u)*math.sqrt(.5),u*u); denom=sum(b)
                dx=sum(w*d[0] for w,d in zip(b,directions))/denom
                dz=sum(w*d[1] for w,d in zip(b,directions))/denom
                point,du,dv=gp_Pnt(),gp_Vec(),gp_Vec();surface.D1(u,float(s),point,du,dv)
                target=(float(row[0])+float(row[2])*dx,sign*float(s),float(row[1])+float(row[2])*dz)
                derivative=(float(slope[0])+float(slope[2])*dx,sign,float(slope[1])+float(slope[2])*dz)
                sample_error=max(sample_error,math.dist(point.Coord(),target))
                derivative_error=max(derivative_error,math.dist(dv.Coord(),derivative))
                minimum_cross=min(minimum_cross,du.Crossed(dv).Magnitude())
        face=BRepBuilderAPI_MakeFace(surface,1e-7).Face()
        if sign>0: face.Reverse()
        sewing.Add(face);surfaces.append(surface)
    rounding_certificate=certify_float_poles(model,stored_pole_rows)
    if sample_error>1e-9 or derivative_error>1e-9 or minimum_cross<=0:
        raise ValueError('native circle or derivative construction witness failed')
    for i in (0,-1):
        wire=BRepBuilderAPI_MakeWire()
        for surface in surfaces: wire.Add(BRepBuilderAPI_MakeEdge(surface.VIso(float(axial[i]))).Edge())
        cx,cz,_=model['rows'][i]
        plane=gp_Pln(gp_Pnt(float(cx),sign*float(axial[i]),float(cz)),gp_Dir(0,-1,0))
        cap=BRepBuilderAPI_MakeFace(plane,wire.Wire(),True).Face()
        if (i==0 and sign<0) or (i==-1 and sign>0): cap.Reverse()
        sewing.Add(cap)
    sewing.Perform();sewed=sewing.SewedShape();cad=design.CAD()
    shells=cad.indexed(sewed,TopAbs_SHELL)
    if shells.Extent()!=1 or sewing.NbFreeEdges()!=0 or sewing.NbMultipleEdges()!=0:
        raise ValueError('one sewn closed shell required')
    solid=BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(shells.FindKey(1))).Solid()
    if not BRepLib.OrientClosedSolid_s(solid):
        raise ValueError('closed-solid orientation failed')
    mass=GProp_GProps();BRepGProp.VolumeProperties_s(solid,mass)
    if not cad.valid(solid) or mass.Mass()<=0:
        raise ValueError('invalid or nonpositive oriented solid')
    adaptive,estimate=adaptive_volume(solid)
    return solid,{'native_quarter_surface_count':4,'native_C1_U_and_V_all_quarters':True,
                  'stored_float_poles_bound_certificate':rounding_certificate,
                  'station_circle_point_error_sampled_max':sample_error,
                  'station_axial_derivative_error_sampled_max':derivative_error,
                  'sampled_surface_cross_product_norm_min':minimum_cross,
                  'station_samples_per_quarter':17,'sewing_tolerance':1e-7,
                  'free_edges':sewing.NbFreeEdges(),'multiple_edges':sewing.NbMultipleEdges(),
                  'signed_volume_default_integration':mass.Mass(),
                  'signed_volume_adaptive_integration':adaptive,
                  'adaptive_integration_Eps':1e-11,'adaptive_relative_error_estimate':estimate,
                  'solid_count':cad.indexed(solid,cad.TopAbs_SOLID).Extent(),
                  'BRepCheck_valid':cad.valid(solid),'native_3d_bounds_not_yet_a_physical_wall_check':True}


def run(args):
    import OCP
    import build_scan_seeded_ports as ports
    started=time.monotonic(); expected=sha(args.checkpoint)
    if expected!=args.checkpoint_sha256:
        raise ValueError('checkpoint hash mismatch')
    row=json.loads(args.checkpoint.read_text())
    stations=row['seed_sections_private']+[row['extension_private']]
    model=build_model(stations);cad=ports.design.CAD();api=ports.native()
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    report={'schema':'private-bounded-C1-circular-trunk/v1','input_checkpoint_sha256':expected,
            'source_sha256':sha(__file__),'existing_port_builder_sha256':sha(ports.__file__),
            'OCP_version':OCP.__version__,'kind':row['kind'],'stations_private':stations,
            'mathematical_model':analytic_report(model),'length_unit':'unverified_scan_unit',
            'scan_scale_hypothesis_units_per_mm':1.,'head_master_modified':False,
            'branches_fused_or_head_cut':False,'manufacturing_authorized':False,
            'flow_or_thermal_validation':False,'M64_fitment_validated':False}
    try:
        shape,quality=construct_native(model);report['native_quality']=quality
        exported=ports.write_native_and_step(cad,args.output,'bounded-c1-trunk',shape)
        report['exports']=exported;report['native_bbox_private']=ports.bbox(api,shape)
        expected_volume=report['mathematical_model']['volume_by_exact_polynomial_integration_times_pi']
        report['volume_relative_error']=abs(quality['signed_volume_adaptive_integration']-expected_volume)/expected_volume
        report['default_integration_volume_relative_error']=abs(cad.volume(shape)-expected_volume)/expected_volume
        if report['volume_relative_error']>1e-7:
            raise ValueError('native volume disagrees with analytic integral')
        ruled=ports.loft(cad,api,stations,ruled=True)
        report['ruled_reference']={'volume':cad.volume(ruled),'bbox_private':ports.bbox(api,ruled)}
        report['status']='native_C1_trunk_built_not_integrated_not_qualified'
        if exported['native_BOP']['has_faulty']:
            report['status']='rejected_native_C1_trunk_BOP'
    except Exception as error:
        report['status']='rejected_C1_trunk_construction'
        report['error']={'class':type(error).__name__,'reason':str(error)}
        raise
    finally:
        report['input_unchanged']=sha(args.checkpoint)==expected
        report['wall_seconds']=time.monotonic()-started
        ports.save(args.output/'bounded-c1-report.json',report)
    print(json.dumps({k:report[k] for k in ('status','native_quality','volume_relative_error','exports')}))
    return 0 if not exported['native_BOP']['has_faulty'] and exported['STEP_qualified_for_further_CAD'] else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--checkpoint-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU,(300,305))
    return run(args)


if __name__=='__main__':
    raise SystemExit(main())
