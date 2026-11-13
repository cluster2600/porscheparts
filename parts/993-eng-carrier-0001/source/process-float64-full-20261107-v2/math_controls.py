"""Unchanged exact-rational arithmetic/geometry cases with explicit public bindings."""
from fractions import Fraction as Q
import hashlib,math,platform,time
from pathlib import Path
import common
HERE=Path(__file__).resolve().parent
module=common.module
sha=common.sha

def contains(enclosure, exact):
    if not Q(float(enclosure[0])) <= exact <= Q(float(enclosure[1])):
        raise AssertionError('Exact rational value is outside the outward interval')


def exact_mesh(vertices, faces):
    points = [[Q(float(x)) for x in row] for row in vertices]
    volume, projected = Q(0), Q(0)
    for ids in faces:
        a, b, c = [points[int(i)] for i in ids]
        determinant = (a[0] * (b[1]*c[2]-b[2]*c[1])
                       - a[1] * (b[0]*c[2]-b[2]*c[0])
                       + a[2] * (b[0]*c[1]-b[1]*c[0]))
        volume += determinant / 6
        projected += abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])) / 2
    return volume, projected


def exact_section(vertices, result):
    references = {}
    ring_areas = []
    for edges in result['ring_source_edges']:
        for pair in edges:
            key = tuple(map(int, pair))
            if key in references:
                continue
            a, b = [[Q(float(x)) for x in vertices[i]] for i in key]
            t = (Q(result['z_mm'])-a[2]) / (b[2]-a[2])
            references[key] = [a[j]+t*(b[j]-a[j]) for j in (0, 1)]
        points = [references[tuple(map(int, pair))] for pair in edges]
        ring_areas.append(sum((a[0]*b[1]-b[0]*a[1] for a,b in zip(points[:-1], points[1:])), Q(0))/2)
    return references, ring_areas, sum(ring_areas, Q(0))


def cylinder(np):
    n = 64
    theta = np.arange(n, dtype=np.float64) * (2*np.pi/n)
    vertices = np.array([[5*np.cos(a), 5*np.sin(a), z] for z in (-2., 2.) for a in theta]
                        + [[0.,0.,-2.],[0.,0.,2.]], dtype=np.float64)
    faces = []
    for i in range(n):
        j = (i+1)%n
        faces.extend([[i,j,j+n],[i,j+n,i+n],[2*n,j,i],[2*n+1,i+n,j+n]])
    return vertices, np.array(faces,dtype=np.int64)


def run(args, output):
    expected,replay,_,_,paths,expected_profile,repo=common.bindings(args)
    import sys
    sys.path.insert(0,str(paths['site_packages']))
    import numpy as np
    replay.verify_profile(expected_profile)
    started=time.monotonic()
    bounds=module('qualified_outward_bounds',common.LAYER/'outward_bounds.py')
    oracle=module('qualified_strict_oracle',common.LAYER/'strict_plane_oracle.py')
    fixtures=module('unchanged_analytic_fixtures',HERE/'fixtures.py')
    primitive_rows = []
    pairs = [(0.,1.),(1.,3.),(-7.,3.),(1e16,1.),(1e16,-1e16),
             (1e-300,1e-100),(np.nextafter(0.,1.),1.),(-1e-200,1e-100),
             (np.nextafter(1.,2.),np.nextafter(1.,0.))]
    for a,b in pairs:
        for name, fn, exact in [('add',bounds.add,Q(float(a))+Q(float(b))),
                                ('sub',bounds.sub,Q(float(a))-Q(float(b))),
                                ('mul',bounds.mul,Q(float(a))*Q(float(b))),
                                ('div',bounds.div,Q(float(a))/Q(float(b)))]:
            enclosure = bounds.packed(fn(bounds.point(a),bounds.point(b)))
            contains(enclosure,exact)
            primitive_rows.append(dict(operation=name,a=float(a),b=float(b),interval=enclosure))
    values = np.array([1e16,1.,-1e16,1e-300,-1e-300],dtype=np.float64)
    summed = bounds.packed(bounds.pair_sum(bounds.point(values)))
    contains(summed,sum(map(lambda x:Q(float(x)),values),Q(0)))
    cube_record, bore_record = fixtures.fixtures()
    cv, cf = np.asarray(cube_record[1].vertices),np.asarray(cube_record[1].faces)
    bv, bf = np.asarray(bore_record[1].vertices),np.asarray(bore_record[1].faces)
    pv,pf = cylinder(np)
    translated = pv.copy();translated[:,:2] += np.array([2.**20,-2.**20])
    definitions = [('cube',cv,cf,100.,1000.),('annular_polygon_prism',bv,bf,bore_record[2],bore_record[4]),
                   ('128_endpoint_polygon_prism',pv,pf,64*math.sin(2*math.pi/64)*25/2,64*math.sin(2*math.pi/64)*50),
                   ('128_endpoint_translated_cancellation',translated,pf,None,None)]
    geometry_rows, sections = [], []
    for name,v,f,analytic_area,analytic_volume in definitions:
        exact_volume,exact_sz = exact_mesh(v,f)
        mesh = bounds.mesh_bounds(v,f,chunk_size=7)
        contains(mesh['signed_volume_mm3'],exact_volume)
        contains(mesh['projected_surface_z_mm2'],exact_sz)
        if name=='cube':
            assert exact_volume==1000 and exact_sz==200
        geometry_rows.append(dict(name=name,mesh_bounds=mesh,exact_volume_fraction=str(exact_volume),
                                  exact_projected_surface_fraction=str(exact_sz),analytic_volume_mm3=analytic_volume,
                                  vertices_sha256=hashlib.sha256(v.tobytes()).hexdigest(),faces_sha256=hashlib.sha256(f.tobytes()).hexdigest()))
        for z in (0.37,float(v[:,2].max()-2.**-28)):
            cut=oracle.slice_rings(v,f,z)
            references,exact_rings,exact_area=exact_section(v,cut)
            row=bounds.section_area_bounds(v,cut['ring_source_edges'],z,cut['signed_area_mm2'])
            contains(row['area_mm2'],exact_area)
            for actual,reference in zip(row['ring_signed_areas_mm2'],exact_rings):contains(actual,reference)
            for edges in cut['ring_source_edges']:
                endpoints=bounds.edge_points_bounds(v,edges,z)
                for index,key in enumerate(map(tuple,edges)):
                    for axis in (0,1):contains([endpoints[0][index,axis],endpoints[1][index,axis]],references[key][axis])
            assert sum(a<0 for a in exact_rings)==(1 if name=='annular_polygon_prism' else 0)
            if name=='cube':assert exact_area==100
            if name.startswith('128_endpoint'):assert len(references)==128
            if name=='annular_polygon_prism':assert len(references)==256
            reported_error=abs(Q(cut['signed_area_mm2'])-exact_area)
            contains(row['reported_oracle_roundoff_error_mm2'],reported_error)
            sections.append(dict(name=name,z_mm=z,unique_endpoints=len(references),holes=sum(a<0 for a in exact_rings),
                                 exact_area_fraction=str(exact_area),analytic_polygon_area_mm2=analytic_area,
                                 exact_reported_area_error_fraction=str(reported_error),bounds=row))
    # Two small complete synthetic calendars exercise area/volume quadrature and
    # actual binary64 tag roundoff. This does not read or slice the carrier.
    calendars=[]
    for name,v,f in [('cube',cv,cf),('annular_polygon_prism',bv,bf)]:
        v=v.copy();v[:,2]-=v[:,2].min()
        h=.3;n=math.ceil(float(v[:,2].max())/h)
        mesh=bounds.mesh_bounds(v,f)
        heights=[float((i+.5)*h) for i in range(n)]
        areas=[];reported=[];exact=[]
        for z in heights:
            cut=oracle.slice_rings(v,f,z)
            row=bounds.section_area_bounds(v,cut['ring_source_edges'],z,cut['signed_area_mm2'])
            areas.append(row['area_mm2']);reported.append(cut['signed_area_mm2'])
            exact.append(exact_section(v,cut)[2])
        result=bounds.calendar_bound(h,list(range(n)),heights,mesh,areas,reported,reported)
        assert result['oracle_volume_bound_passed'] and result['native_volume_bound_passed']
        assert Q(result['delta_exact_fraction'])==max(abs(Q(z)-Q(h)*Q(2*i+1,2)) for i,z in enumerate(heights))
        contains(result['exact_section_quadrature_mm3'],Q(h)*sum(exact,Q(0)))
        actual_volume,sz=exact_mesh(v,f)
        exact_error=abs(Q(h)*sum(exact,Q(0))-actual_volume)
        assert exact_error <= (Q(h)/2+Q(result['delta_exact_fraction']))*sz
        altered=[x+10000 for x in reported]
        altered_bounds=[[a+10000,b+10000] for a,b in areas]
        rejected=bounds.calendar_bound(h,list(range(n)),heights,mesh,altered_bounds,altered,altered)
        assert not rejected['oracle_volume_bound_passed']
        calendars.append(dict(name=name,result=result,exact_quadrature_error_fraction=str(exact_error),
                              corrupted_section_volume_refused=True))
    empty=bounds.section_area_bounds(cv,[],50.,0.)
    assert empty['area_mm2']==[0.,0.] and empty['ring_count']==0
    negatives=[]
    def reject(name,fn):
        try:fn()
        except (ValueError,OverflowError,AssertionError):negatives.append(dict(name=name,refused=True))
        else:raise AssertionError('Invalid interval input accepted: '+name)
    reject('division_interval_contains_zero',lambda:bounds.div(bounds.point(1.),bounds.interval(-1e-300,1e-300)))
    reject('nonfinite_input',lambda:bounds.point(float('nan')))
    reject('primitive_overflow',lambda:bounds.mul(bounds.point(np.finfo(np.float64).max),bounds.point(2.)))
    reject('reversed_source_edge',lambda:bounds.edge_points_bounds(cv,np.array([[4,0]]),0.))
    reject('coplanar_endpoint',lambda:bounds.edge_points_bounds(cv,np.array([[0,4]]),5.))
    cut=oracle.slice_rings(cv,cf,.37)
    reject('duplicate_oriented_cycle',lambda:bounds.section_area_bounds(cv,cut['ring_source_edges']*2,.37))
    reject('open_edge_cycle',lambda:bounds.section_area_bounds(cv,[cut['ring_source_edges'][0][:-1]],.37))
    reject('missing_calendar_index',lambda:bounds.calendar_bound(.3,[0,2],[.15,.75],mesh,areas[:2],reported[:2],reported[:2]))
    reject('plane_outside_calendar_cell',lambda:bounds.calendar_bound(.3,list(range(n)),[0.]+heights[1:],mesh,areas,reported,reported))
    badmesh=dict(mesh,z_support_mm=[-1.,mesh['z_support_mm'][1]])
    reject('calendar_does_not_cover_mesh',lambda:bounds.calendar_bound(.3,list(range(n)),heights,badmesh,areas,reported,reported))
    replay.verify_profile(expected_profile)
    common.bindings(args)
    source_hashes={str(path):sha(path) for path in [Path(__file__),HERE/'fixtures.py',common.LAYER/'outward_bounds.py',common.LAYER/'strict_plane_oracle.py']}
    result=dict(status='finite_outward_bounds_match_exact_rational_geometry_and_section_controls',
                primitive_exact_fraction_controls=primitive_rows,pairwise_cancellation_interval=summed,
                geometry_controls=geometry_rows,section_controls=sections,synthetic_calendars=calendars,
                explicit_empty_section=empty,negative_controls=negatives,source_sha256=source_hashes,
                python_sha256=sha(sys.executable),python_version=platform.python_version(),
                runtime_profile_unchanged=True,runtime_profile_sha256=sha(paths['runtime_profile']),
                package_versions=expected_profile['packages'],full_current_mesh_or_calendar_executed=False,
                source_manifest_sha256=args.source_manifest_sha256,
                native_tolerances_or_exposure_coverage_changed=False,elapsed_seconds=time.monotonic()-started)
    common.write(Path(output)/'math-controls.json',result)
    return result
