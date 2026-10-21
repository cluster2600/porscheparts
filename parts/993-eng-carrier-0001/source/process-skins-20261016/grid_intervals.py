"""Whole-triangle grid admission against exact free cross-sections and contact bands."""
import numpy as np
import hashlib
import importlib.util
import math
from pathlib import Path
import shapely
from shapely import affinity
from shapely.geometry import Polygon,LineString
import trimesh
from trimesh.path.entities import Line
from pyslm.support.support import _triangulate_exact_projected_domain

_contact_source=Path(__file__).resolve().parent/'exact_contacts.py'
if not _contact_source.is_file():_contact_source=Path(__file__).resolve().parent.parent/'process-scanpath-audit-20261016/exact_contacts.py'
if hashlib.sha256(_contact_source.read_bytes()).hexdigest()!='399db612b1d5fde6b1a0290d4d497d9b01e6afe3a28d7b63a095a2a06e271cca':
    raise ValueError('Exact contact helper differs from its frozen version')
_spec=importlib.util.spec_from_file_location('carrier_exact_contacts',_contact_source)
_exact_contacts=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_exact_contacts)

_both_source=Path(__file__).resolve().parent/'exact_contacts_both.py'
if not _both_source.is_file():_both_source=Path(__file__).resolve().parent.parent/'process-scanpath-audit-20261016/exact_contacts_both.py'
if hashlib.sha256(_both_source.read_bytes()).hexdigest()!='102aaffcf0c1ac2646b2aef8d5e0dfbfebf14a9b2182b59a731434bcd6a7a855':
    raise ValueError('Exact two-domain contact helper differs from its frozen version')
_both_spec=importlib.util.spec_from_file_location('carrier_exact_contacts_both',_both_source)
_both_contacts=importlib.util.module_from_spec(_both_spec);_both_spec.loader.exec_module(_both_contacts)


def parts(geometry):
    if isinstance(geometry,Polygon):return [geometry] if not geometry.is_empty else []
    return [p for item in getattr(geometry,'geoms',[]) for p in parts(item)]


def vertical_contact_band(domain,penetration):
    triangles=shapely.get_parts(shapely.constrained_delaunay_triangles(domain))
    return shapely.union_all([shapely.MultiPoint(np.vstack([
        np.array(triangle.exterior.coords)[:-1]+[0,penetration],
        np.array(triangle.exterior.coords)[:-1]-[0,penetration]])).convex_hull for triangle in triangles])


def contacts(material,domain,interfaces=None,required_only=False):
    """Intersect source interfaces with both closed IEEE domains, before encoding."""
    round_contacts_in_both=_both_contacts.round_contacts_in_both
    def traces(geometry):
        if isinstance(geometry,LineString):return [np.asarray(geometry.coords).tolist()] if geometry.length>0 else []
        return [line for child in getattr(geometry,'geoms',[]) for line in traces(child)]
    polygons=parts(shapely.orient_polygons(domain))
    if interfaces is None:
        interfaces=dict(upper=[],lower=[])
        for polygon in polygons:
            for ring in [polygon.exterior,*polygon.interiors]:
                coords=np.array(ring.coords)
                for a,b in zip(coords[:-1],coords[1:]):
                    # Only declared standalone fixtures use horizontal floor /
                    # roof boundaries. Production always supplies native ancestry.
                    if a[1]!=b[1]:continue
                    if b[0]>a[0]:interfaces['lower'].append([a.tolist(),b.tolist()])
                    elif b[0]<a[0]:interfaces['upper'].append([a.tolist(),b.tolist()])
    lines={name:[LineString(path) for path in interfaces[name]] for name in ['upper','lower']}
    trees={name:shapely.STRtree(lines[name]) for name in lines}
    def candidates(polygon,name):
        return [interfaces[name][i] for i in sorted(trees[name].query(shapely.box(*polygon.bounds)))]
    def length(segments):
        return sum(math.hypot(float(segment[1][0]-segment[0][0]),float(segment[1][1]-segment[0][1])) for segment in segments)
    def proof(component,free,upper,lower):
        top=round_contacts_in_both(component,free,upper);bottom=round_contacts_in_both(component,free,lower)
        return dict(free_domain_geometry_wkb_hex=free.wkb_hex,
            free_domain_geometry_sha256=hashlib.sha256(free.wkb).hexdigest(),
            contact_clip_scope='source_interface_intersect_material_intersect_free_domain_exact_before_single_float64_encoding',
            upper_interface_traces_2d_mm=upper,lower_interface_traces_2d_mm=lower,
            upper_contact_traces_2d_mm=top,lower_contact_traces_2d_mm=bottom,
            upper_contact_trace_mm=length(top),lower_contact_trace_mm=length(bottom),
            contact_length_semantics='sum of retained encoded intervals; positive contact certified with exact rationals',
            diagnostic_geos_upper_contact_traces_2d_mm=traces(component.intersection(shapely.union_all([LineString(p) for p in upper])).intersection(free)),
            diagnostic_geos_lower_contact_traces_2d_mm=traces(component.intersection(shapely.union_all([LineString(p) for p in lower])).intersection(free)))
    rows=[]
    for index,polygon in enumerate(polygons):
        upper=candidates(polygon,'upper');lower=candidates(polygon,'lower')
        required_top=_exact_contacts.clip_contacts(polygon,upper)
        required_bottom=_exact_contacts.clip_contacts(polygon,lower)
        row=proof(material,polygon,upper,lower)
        rows.append(dict(kind='required_free_interval',domain_index=index,
            required_upper_interface_length_mm=length(required_top),required_lower_interface_length_mm=length(required_bottom),
            upper_interface_required=bool(required_top),lower_interface_required=bool(required_bottom),
            passed=bool((row['upper_contact_trace_mm']>0 or not required_top) and
                        (row['lower_contact_trace_mm']>0 or not required_bottom)),**row))
    if required_only:return rows
    for index,component in enumerate(parts(material)):
        upper=candidates(component,'upper');lower=candidates(component,'lower')
        row=proof(component,domain,upper,lower)
        rows.append(dict(kind='generated_material_component',component_index=index,component_area_mm2=component.area,
            component_geometry_sha256=hashlib.sha256(component.wkb).hexdigest(),component_geometry_wkb_hex=component.wkb_hex,
            required_upper_interface_length_mm=length(_exact_contacts.clip_contacts(domain,upper)),
            required_lower_interface_length_mm=length(_exact_contacts.clip_contacts(domain,lower)),
            passed=bool(row['upper_contact_trace_mm']>0 and row['lower_contact_trace_mm']>0),**row))
    return rows


def free_section(volume,axis,value,with_interfaces=False):
    horizontal=1-axis
    # Compute every intersection of one original mesh edge only once.  mesh_plane
    # independently evaluates adjacent faces and can leave 1-ulp gaps; closing
    # those gaps by rounding would change the domain being audited.
    xyz=np.asarray(volume.vertices);distances=xyz[:,axis]-value
    points=[];lookup={};segments=[];source_interfaces={'upper':[],'lower':[]}
    if with_interfaces and 'interface_kind' not in volume.face_attributes:raise ValueError('True interface face ancestry is required')
    def point(key):
        if key not in lookup:
            if len(key)==1:p=xyz[key[0]]
            else:
                a,b=key;fraction=(value-xyz[a,axis])/(xyz[b,axis]-xyz[a,axis])
                p=xyz[a]+fraction*(xyz[b]-xyz[a])
            lookup[key]=len(points);points.append(p[[horizontal,2]])
        return lookup[key]
    signed_faces=distances[volume.faces]
    selected=(signed_faces.min(axis=1)<=0)&(signed_faces.max(axis=1)>=0)&~np.all(signed_faces==0,axis=1)
    # Strict same-side faces contribute no intersections. Preserve the original
    # order and all operations on retained faces, including exact vertex keys.
    for face_index in np.flatnonzero(selected):
        face=volume.faces[face_index]
        d=distances[face]
        if np.all(d==0):continue
        keys=[(int(i),) for i in face[d==0]]
        for a,b in zip(face,np.roll(face,-1)):
            if (distances[a]<0<distances[b]) or (distances[b]<0<distances[a]):
                keys.append(tuple(sorted((int(a),int(b)))))
        keys=list(dict.fromkeys(keys))
        if len(keys)==2:
            line=[point(keys[0]),point(keys[1])];segments.append(line)
            if with_interfaces:
                kind=int(volume.face_attributes['interface_kind'][face_index])
                if kind:source_interfaces['upper' if kind>0 else 'lower'].append([points[i].tolist() for i in line])
        elif len(keys)>2:raise ValueError('Non-coplanar face has more than two plane intersections')
    if not segments:raise ValueError('Generated grid plane has no free-volume section')
    edges=np.unique(np.sort(np.asarray(segments),axis=1),axis=0)
    path=trimesh.path.Path2D(entities=[Line(edge) for edge in edges],vertices=np.asarray(points),process=False)
    if not path.is_closed:raise ValueError('Free section is open; no gap filling is allowed')
    polygons=path.polygons_full
    if not len(polygons) or any(not p.is_valid for p in polygons):raise ValueError('Invalid free cross-section')
    domain=shapely.union_all(polygons)
    return (domain,source_interfaces) if with_interfaces else domain


def trim_and_admit(volume,grid,axis,penetration,defer_component_contacts=False,diagnostic_contacts=False,tooth_cycle_length=None,continuous_fragments=False):
    output=[];rows=[];face_cursor=0
    if not len(grid.faces):raise ValueError('Required native grid is empty')
    order=grid.face_attributes['order'];kind=grid.face_attributes['type'];horizontal=1-axis
    for identity in np.unique(order):
        select=np.flatnonzero(order==identity);triangles=grid.triangles[select]
        value=float(triangles[0,0,axis])
        if np.ptp(triangles[:,:,axis])!=0:raise ValueError('Grid group is not an exact X/Y plane')
        if 'interface_kind' in volume.face_attributes:domain,interfaces=free_section(volume,axis,value,True)
        else:domain=free_section(volume,axis,value);interfaces=None
        allowed=vertical_contact_band(domain,penetration)
        native=shapely.union_all(shapely.polygons(triangles[:,:,[horizontal,2]]))
        restoration=None
        if tooth_cycle_length is not None:
            from quantized_contacts import restore_short_horizontal_interfaces
            native,restoration=restore_short_horizontal_interfaces(native,domain,tooth_cycle_length,interfaces)
        cropped=native.intersection(allowed)
        continuous=None
        if continuous_fragments:
            from continuous_interfaces import repair
            cropped,continuous=repair(cropped,domain,interfaces,penetration)
        if cropped.is_empty or not cropped.is_valid:raise ValueError('A complete native grid group lies outside its free/contact domain')
        meshes=[];face_ranges=[]
        for component_index,polygon in enumerate(parts(cropped)):
            (xy,faces),_= _triangulate_exact_projected_domain(polygon,4.)
            vertices=np.zeros((len(xy),3));vertices[:,axis]=value;vertices[:,horizontal]=xy[:,0];vertices[:,2]=xy[:,1]
            from zero_area_faces import retained_faces
            keep,zero_area=retained_faces(vertices,faces);faces=faces[keep]
            mesh=trimesh.Trimesh(vertices,faces,process=False)
            mesh.face_attributes['order']=np.full(len(faces),identity);mesh.face_attributes['type']=np.full(len(faces),kind[select[0]])
            meshes.append(mesh)
            face_ranges.append(dict(component_index=component_index,face_range=[face_cursor,face_cursor+len(faces)],
                component_geometry_sha256=hashlib.sha256(polygon.wkb).hexdigest(),exact_zero_area_cleanup=zero_area))
            face_cursor+=len(faces)
        plane=trimesh.util.concatenate(meshes)
        output.extend(meshes)
        contact=contacts(cropped,domain,interfaces)
        required=[item for item in contact if item['kind']=='required_free_interval']
        if interfaces is not None and any(not r['upper_interface_required'] or not r['lower_interface_required'] for r in required):
            error=ValueError('A closed free grid interval lacks its true upper/lower interface provenance')
            error.receipt=dict(status='rejected',fixed_axis=axis,plane_coordinate_mm=value,order=int(identity),contacts=required)
            raise error
        if not diagnostic_contacts and not all(item['passed'] for item in (required if defer_component_contacts else contact)):
            error=ValueError('A generated grid material component or required free interval lacks upper/lower contact')
            error.receipt=dict(status='rejected',fixed_axis=axis,plane_coordinate_mm=value,order=int(identity),
                contacts=contact,material_geometry_wkb_hex=cropped.wkb_hex,free_domain_geometry_wkb_hex=domain.wkb_hex,
                native_outside_domain_area_mm2=native.difference(allowed).area,
                explicitly_trimmed_area_mm2=native.difference(cropped).area)
            raise error
        rows.append(dict(order=int(identity),fixed_axis=axis,plane_coordinate_mm=value,
            free_section_area_mm2=domain.area,native_grid_union_area_mm2=native.area,
            native_outside_free_and_contact_domain_area_mm2=native.difference(allowed).area,
            explicitly_trimmed_area_mm2=native.difference(cropped).area,
            generated_area_mm2=plane.area,whole_surface_outside_admitted_domain_area_mm2=cropped.difference(allowed).area,
            required_free_intervals=len(parts(domain)),generated_material_components=len(parts(cropped)),
            material_component_face_ranges=face_ranges,
            component_contacts_deferred_to_3d_graph=bool(defer_component_contacts),
            diagnostic_contacts_unproven=bool(diagnostic_contacts),
            native_short_interface_restoration=restoration,
            continuous_interface_reconstruction=continuous,
            contacts=contact,passed=True))
    # Preserve the native scan attributes through the library's attribute-aware concatenate.
    from pyslm.support import GridBlockSupport
    result=GridBlockSupport().concatenateMeshes(output)
    return result,dict(status='passed',algorithm='native_grid_intersect_actual_free_section_vertical_contact_band',
        vertical_contact_penetration_mm=penetration,expected_planes=len(np.unique(order)),generated_planes=len(rows),planes=rows)
