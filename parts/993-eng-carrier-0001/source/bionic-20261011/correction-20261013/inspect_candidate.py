"""Inspect exported geometry against the frozen F0 comparator, not CAD claims."""
import json
from pathlib import Path
import sys

import numpy as np

from corrected_cad import contract, ROOT, SOURCE, sha, precise_volume


class SurfaceGateError(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__('Surface gate failed: '+json.dumps(report))


def intersection_volume(a,b):
    result=a&b
    return 0.0 if result is None else result.volume


def normalized_mesh(path):
    import trimesh
    raw = trimesh.load_mesh(path, process=False)
    if not np.isfinite(raw.vertices).all():
        raise ValueError('Nonfinite mesh')
    vertices, inverse = np.unique(raw.vertices, axis=0, return_inverse=True)
    welded = trimesh.Trimesh(vertices, inverse[raw.faces], process=False)
    keep = welded.area_faces > 0
    clean = trimesh.Trimesh(vertices, welded.faces[keep], process=False)
    clean.remove_unreferenced_vertices()
    check = {'raw_triangles': len(raw.faces), 'exact_zero_faces_removed': int((~keep).sum()),
             'removed_positive_area_faces': 0, 'minimum_retained_face_area_mm2': float(clean.area_faces.min()),
             'watertight': bool(clean.is_watertight), 'consistent_orientation': bool(clean.is_winding_consistent),
             'components': len(clean.split(only_watertight=False)),
             'volume_mm3': float(clean.volume), 'raw_signed_volume_mm3': float(welded.volume)}
    if not (check['watertight'] and check['consistent_orientation'] and check['components']==1
            and check['volume_mm3']>0):
        raise SurfaceGateError(check)
    return clean, check


def inspect(folder):
    import trimesh
    from build123d import Axis, Vector, Cylinder, Pos, GeomType, import_step
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    folder = Path(folder)
    c = contract()
    body = import_step(folder/'carrier.step')
    assert body.is_valid and len(body.solids())==1
    volume,_=precise_volume(body)
    flat_dir=ROOT/'parts/993-eng-carrier-0001'
    flat=json.loads((flat_dir/'source/bionic-20261011/flat-results.json').read_text())
    baseline_path=flat_dir/'derived/bionic-flat-20261012/carrier-flat.step'
    assert sha(baseline_path)==flat['geometry']['flat_STEP_sha256']
    baseline=import_step(baseline_path).solids()[0].translate(Vector(*map(float,-np.array(flat['orientation']['translation_mm']))))
    baseline=baseline.rotate(Axis.Z,-45)
    end_regions={}
    for x in c['study_end_centres_x_mm']:
        bore=Pos(x,0,0)*Cylinder(7,46,rotation=(90,0,0))
        end_regions[f'bore_{x}']=bore
        for y in c['study_end_seat_y_mm']:
            end_regions[f'seat_{x}_{y}']=Pos(x,float(y-np.sign(y)*.1),0)*Cylinder(15.999,.2,rotation=(90,0,0))
    preserved={}
    for label,region in end_regions.items():
        before=baseline&region;after=body&region
        assert before is not None and after is not None and before.volume>0 and after.volume>0
        a=before-after;b=after-before
        preserved[label]=(0 if a is None else a.volume)+(0 if b is None else b.volume)
    carrier, surface = normalized_mesh(folder/'carrier.stl')
    bracket_path = ROOT/'twins/993-engine-mount-system-f0/derived/993-ENG-BRACKET-0001.stl'
    bracket, bracket_surface = normalized_mesh(bracket_path)
    section = bracket.section(plane_origin=[0,0,4], plane_normal=[0,0,1])
    circles = []
    for loop in section.discrete:
        xy = loop[:-1,:2]
        if not (9 < np.ptp(xy,axis=0).min() and np.ptp(xy,axis=0).max() < 12):
            continue
        x,y,d = np.linalg.lstsq(np.c_[2*xy,np.ones(len(xy))], (xy*xy).sum(1),rcond=None)[0]
        r = np.sqrt(d+x*x+y*y)
        circles.append([float(x),float(y),float(r)])
    circles = np.asarray(sorted(circles,key=lambda p:(round(p[0]),round(p[1]))))
    expected = np.asarray(c['study_central_centres_xy_mm'])
    assert circles.shape==(4,3) and np.allclose(circles[:,:2],expected,atol=.05)
    holes=[]
    for face in body.faces():
        if face.geom_type != GeomType.CYLINDER:
            continue
        cylinder=BRepAdaptor_Surface(face.wrapped).Cylinder()
        x,y,z=cylinder.Location().Coord()
        if (abs(x)<70 and abs(y)<35 and abs(cylinder.Radius()-c['study_carrier_bore_radius_mm'])<1e-7
                and abs(abs(cylinder.Axis().Direction().Z())-1)<1e-7):
            box=face.bounding_box()
            holes.append([x,y,cylinder.Radius(),box.min.Z,box.max.Z])
    holes=np.unique(np.round(holes,6),axis=0)
    assert holes.shape==(4,5)
    assert np.allclose(holes[:,:2],expected,atol=1e-7)
    assert np.allclose(holes[:,2:],[5.5,-4,4],atol=1e-7)
    tools=[]
    for x,y in expected:
        x,y=float(x),float(y)
        cutter=Pos(x,y,4+50/2)*Cylinder(c['study_tool_radius_mm'],50)
        tools.append({'xy_mm':[float(x),float(y)],'intersection_mm3':intersection_volume(body,cutter)})
    secondary=[]
    for x,y in ((-160,-26),(-180,-23)):
        secondary.append({'xy_mm':[x,y], 'gauge_radius_mm':1,'gauge_length_mm':12,
                          'intersection_mm3':intersection_volume(body,Pos(x,y,0)*Cylinder(1,12))})
    # Explicitly retain raw export; normalisation removes only zero-area triangles.
    carrier.export(folder/'carrier-normalized.stl')
    pose=np.diag([1.,-1.,-1.,1.]);pose[2,3]=-4
    bracket.apply_transform(pose)
    overlap=trimesh.boolean.intersection([carrier,bracket],engine='manifold',check_volume=True)
    collision_volume=float(abs(overlap.volume)) if len(overlap.faces) else 0.0
    if len(overlap.faces): overlap.export(folder/'bracket-intersection.stl')
    shanks=[]
    angles=np.arange(64)*2*np.pi/64
    for x,y in expected:
        x,y=float(x),float(y)
        # Whole nominal shank, plus Boolean volume checks independent of sampling.
        probes=np.asarray([[x+r*np.cos(a),y+r*np.sin(a),z]
                           for z in np.linspace(-15.9,3.9,17) for r in (0,2.5,5) for a in angles])
        bolt=trimesh.creation.cylinder(radius=5,height=20,sections=128)
        bolt.apply_translation([x,y,-6])
        overlap_bolt=trimesh.boolean.intersection([bolt,bracket],engine='manifold',check_volume=True)
        shanks.append({'xy_mm':[float(x),float(y)],'samples':len(probes),
                       'carrier_hits':int(carrier.contains(probes).sum()),
                       'bracket_hits':int(bracket.contains(probes).sum()),
                       'carrier_exact_cylinder_intersection_mm3':intersection_volume(body,Pos(x,y,-6)*Cylinder(5,20)),
                       'bracket_128_sided_shank_intersection_mm3':float(abs(overlap_bolt.volume)) if len(overlap_bolt.faces) else 0.0})
    bounds=body.bounding_box()
    report={
        'scope':'Independent frozen F0 study comparator; neither part has measured OEM interfaces',
        'inputs_sha256':{'carrier.step':sha(folder/'carrier.step'),'carrier.stl':sha(folder/'carrier.stl'),
                         'F0_bracket.stl':sha(bracket_path),'contract':sha(SOURCE/'interface-study.json'),
                         'frozen_V5_flat.step':sha(baseline_path)},
        'carrier_bore_faces_xy_radius_zmin_zmax_mm':holes.tolist(),
        'independent_bracket_circles_xy_radius_mm':circles.tolist(),
        'maximum_axis_error_vs_fitted_bracket_mm':float(np.linalg.norm(holes[:,:2]-circles[:,:2],axis=1).max()),
        'surface':surface,'bracket_surface':bracket_surface,
        'STEP_volume_mm3':volume,'STL_volume_error_fraction':carrier.volume/volume-1,
        'nominal_mass_kg':volume*4.42e-6,'mass_ceiling_pass':volume*4.42e-6<=c['mass_ceiling_kg'],
        'tool_column_checks':tools,'secondary_gauges':secondary,'shank_checks':shanks,
        'end_interface_symmetric_difference_mm3':preserved,
        'whole_pair_mesh_intersection_mm3':collision_volume,
        'intersection_method':'Manifold boolean on independently authored closed STL surfaces; not CAD/OEM fit proof',
        'bounds_mm':[list(bounds.min),list(bounds.max)],
        'flat_part_height_mm':bounds.max.Z-bounds.min.Z,
        'bolt_stack':{'nominal_length_mm':20,'assumed_carrier_pad_mm':8,'assumed_bracket_pad_mm':8,
                      'remaining_for_nut_washers_protrusion_mm':4,'thread_engagement_verified':False},
        'fitment_validated':False,'manufacturing_authorized':False,
    }
    report['study_assembly_screen_pass']=(collision_volume<=1e-5 and max(preserved.values())<=1e-5 and
        all(x['intersection_mm3']<=1e-6 for x in tools+secondary) and
        all(x['carrier_hits']==x['bracket_hits']==0 and x['carrier_exact_cylinder_intersection_mm3']<=1e-6
            and x['bracket_128_sided_shank_intersection_mm3']<=1e-5 for x in shanks))
    (folder/'inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    (folder/'inspection-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k:report[k] for k in ('nominal_mass_kg','maximum_axis_error_vs_fitted_bracket_mm',
                     'whole_pair_mesh_intersection_mm3','study_assembly_screen_pass')},indent=2))
    return report


if __name__=='__main__':
    inspect(sys.argv[1])
