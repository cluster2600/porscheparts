"""Unfold actual vertical envelope sheets and reuse native PySLM truss/teeth."""
from collections import deque
import hashlib
import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import Polygon, box
import trimesh
from pyslm.support import GridBlockSupport
from pyslm.support.support import _triangulate_exact_projected_domain


def polygon_parts(geometry):
    if isinstance(geometry, Polygon):
        return [geometry] if not geometry.is_empty else []
    return [part for item in getattr(geometry, 'geoms', []) for part in polygon_parts(item)]


def vertical_components(mesh,planar_only=False):
    xy = mesh.triangles[:, :, :2]
    edges = np.roll(xy, -1, axis=1) - xy
    length = np.linalg.norm(edges, axis=2)
    longest = np.argmax(length, axis=1)
    row = np.arange(len(xy))
    origin, direction = xy[row, longest], edges[row, longest]
    width = length[row, longest]
    distance = np.max(abs(np.cross(xy - origin[:, None], direction[:, None])) /
                      np.maximum(width[:, None], np.finfo(float).tiny), axis=1)
    coordinate_roundoff = 128 * np.spacing(max(1., float(abs(mesh.vertices).max())))
    # Reuse the native supportBoundary orientation gate as well as the strict
    # XY planarity check. A cap sliver can have tiny XY width and a nonzero Z
    # roundoff span while its actual normal is horizontal; it must not join two
    # distinct vertical charts.
    from pyslm.support.utils import getFaceZProjectionWeight
    native_vertical=getFaceZProjectionWeight(mesh)>(1.-1e-4)
    # A very thin horizontal triangle is still horizontal. Conversely retain
    # every positive-width vertical sheet, even below the roundoff bound; later
    # unfolding/infill admission must handle or explicitly reject it.
    mask = (native_vertical & (distance <= coordinate_roundoff) & (width > 0) &
            (np.ptp(mesh.triangles[:,:,2],axis=1)>0) & (mesh.area_faces > 0))
    adjacency = mesh.face_adjacency
    adjacency = adjacency[np.all(mask[adjacency], axis=1)]
    # A closed free volume may contain branched vertical walls at different Z
    # intervals. One periodic abscissa is invalid across a branch. First form
    # planar vertical facets, then cut only the adjacency at real junctions;
    # each remaining chart follows a simple chain or cycle in XY.
    if len(adjacency):
        a,b=adjacency.T
        delta=xy[b]-origin[a,None,:]
        separation=np.max(abs(np.cross(delta,direction[a,None,:])) /
                          np.maximum(width[a,None],np.finfo(float).tiny),axis=1)
        planar=adjacency[separation<=coordinate_roundoff]
    else:planar=np.empty((0,2),dtype=int)
    patches=trimesh.graph.connected_components(planar,nodes=np.flatnonzero(mask),min_len=1)
    if planar_only:return patches,coordinate_roundoff
    owner=np.full(len(mesh.faces),-1,dtype=int)
    for i,patch in enumerate(patches):owner[patch]=i
    connections=np.unique(np.sort(owner[adjacency],axis=1),axis=0)
    connections=connections[connections[:,0]!=connections[:,1]]
    degree=np.bincount(connections.ravel(),minlength=len(patches))
    simple=connections[np.all(degree[connections]<=2,axis=1)]
    charts=trimesh.graph.connected_components(simple,nodes=np.arange(len(patches)),min_len=1)
    components=[np.concatenate([patches[i] for i in chart]) for chart in charts]
    return components, coordinate_roundoff


def _simplify_mapping(points, tolerance):
    """Discard only samples lying within the measured numerical consistency bound."""
    keep = {0, len(points)-1}
    pending = [(0, len(points)-1)]
    while pending:
        first, last = pending.pop()
        if last <= first+1:
            continue
        f = (points[first+1:last, 0]-points[first, 0])/(points[last, 0]-points[first, 0])
        expected = points[first, 1:] + f[:, None]*(points[last, 1:]-points[first, 1:])
        error = np.linalg.norm(points[first+1:last, 1:]-expected, axis=1)
        index = int(np.argmax(error))+first+1
        if error[index-first-1] > tolerance:
            keep.add(index)
            pending.extend([(first,index),(index,last)])
    return points[sorted(keep)]


def unfold(mesh, face_ids):
    """Integrate horizontal tangents on the actual face-adjacency graph."""
    face_ids = np.asarray(face_ids)
    face_set = set(face_ids.tolist())
    graph = {int(face): [] for face in face_ids}
    adjacency=mesh.face_adjacency
    retained=adjacency[np.all(np.isin(adjacency,face_ids),axis=1)]
    for a,b in retained:
        graph[a].append(int(b)); graph[b].append(int(a))
    normals = mesh.face_normals[face_ids]
    xy = mesh.triangles[face_ids,:,:2]
    edges = np.roll(xy,-1,axis=1)-xy
    lengths = np.linalg.norm(edges,axis=2)
    tangent = edges[np.arange(len(face_ids)),np.argmax(lengths,axis=1)]
    tangent /= np.linalg.norm(tangent,axis=1)[:,None]
    normal_tangent = np.column_stack([-normals[:,1],normals[:,0]])
    tangent[np.einsum('ij,ij->i',tangent,normal_tangent)<0] *= -1
    # The normal of a skinny ear is ill conditioned. On a genuinely planar
    # vertical facet, one measured XY tangent serves every triangle, including
    # that ear; it must not become a separate sub-quantum support contour.
    reference=int(np.argmax(mesh.area_faces[face_ids]));reference_tangent=tangent[reference].copy()
    reference_origin=xy[reference,0]
    plane_distance=np.max(abs(np.cross(xy-reference_origin,reference_tangent)))
    if plane_distance<=128*np.spacing(max(1.,float(abs(mesh.vertices).max()))):
        tangent[:]=reference_tangent
    directions = dict(zip(face_ids.tolist(), tangent))
    root = int(face_ids[0])
    root_xy = mesh.vertices[mesh.faces[root], :2]
    charts = {root: (root_xy-root_xy[0]) @ directions[root]}
    queue = deque([root])
    scale = max(1.,float(abs(mesh.vertices).max()))
    theoretical_tolerance = 128*np.spacing(scale)*max(1,len(face_ids))
    while queue:
        parent = queue.popleft()
        for child in graph[parent]:
            if child in charts:
                continue
            shared = np.intersect1d(mesh.faces[parent],mesh.faces[child])
            if len(shared)!=2:
                raise ValueError('Vertical sheets must share actual mesh edges')
            reference = int(shared[0])
            reference_t = charts[parent][np.flatnonzero(mesh.faces[parent]==reference)[0]]
            xy = mesh.vertices[mesh.faces[child],:2]
            charts[child] = reference_t + (xy-mesh.vertices[reference,:2]) @ directions[child]
            queue.append(child)
    periods, zero_errors = [], []
    for a in face_ids:
        for b in graph[a]:
            if a>=b: continue
            shared = np.intersect1d(mesh.faces[a],mesh.faces[b])
            delta = np.array([charts[a][np.flatnonzero(mesh.faces[a]==v)[0]] -
                              charts[b][np.flatnonzero(mesh.faces[b]==v)[0]] for v in shared])
            if np.ptp(delta)>theoretical_tolerance:
                raise ValueError('Vertical sheet cannot be unfolded isometrically')
            value = float(abs(delta.mean()))
            if value>theoretical_tolerance: periods.append(value)
            else: zero_errors.append(value)
    period = float(np.median(periods)) if periods else None
    if period is not None and max(abs(np.asarray(periods)-period))>theoretical_tolerance:
        raise ValueError('Vertical sheet has incompatible winding periods')
    numerical_tolerance = max(128*np.spacing(scale),4*max(zero_errors,default=0),
                              4*max(abs(np.asarray(periods)-period),default=0) if periods else 0)
    # One intrinsic coordinate per actual source vertex removes accumulated
    # floating-point disagreement across shared edges, without moving XYZ.
    canonical = {}
    maximum_canonical_adjustment = 0.
    for face in face_ids:
        for corner,vertex in enumerate(mesh.faces[face]):
            value=charts[face][corner]
            if int(vertex) not in canonical:
                canonical[int(vertex)]=value
            reference=canonical[int(vertex)]
            if period is not None:
                reference += np.round((value-reference)/period)*period
            maximum_canonical_adjustment=max(maximum_canonical_adjustment,abs(value-reference))
            charts[face][corner]=reference
    if maximum_canonical_adjustment>theoretical_tolerance:
        raise ValueError('Shared intrinsic coordinates disagree beyond roundoff')
    triangles = []
    samples = []
    zmin,zmax = mesh.bounds[:,2]
    for face in face_ids:
        points = mesh.vertices[mesh.faces[face]]
        chart = np.column_stack([charts[face],points[:,2]])
        polygon = Polygon(chart)
        # Keep the actual unwrapped chart, with an open seam at the traversal
        # cut. This preserves original edge identities for true part contacts.
        triangles.append(polygon);times=chart[:,0]
        samples.extend(np.column_stack([times,points[:,:2]]).tolist())
    domain = shapely.union_all(triangles)
    source_area = float(mesh.area_faces[face_ids].sum())
    area_tolerance = 128*np.finfo(float).eps*max(1.,source_area)*len(face_ids)
    unfolded_sum = sum(p.area for p in triangles)
    if abs(domain.area-source_area)>area_tolerance or abs(unfolded_sum-source_area)>area_tolerance:
        raise ValueError('Unfolding lost or overlapped a vertical source area')
    points=np.asarray(samples);points=points[np.argsort(points[:,0])]
    selected=[]
    for point in points:
        if selected and point[0]-selected[-1][0]<=numerical_tolerance:
            if np.linalg.norm(point[1:]-selected[-1][1:])>4*numerical_tolerance:
                raise ValueError('Unfolded abscissa maps to incompatible XY coordinates')
        else: selected.append(point)
    points=np.array(selected)
    mapping=_simplify_mapping(points,numerical_tolerance)
    metric_error=abs(np.linalg.norm(np.diff(mapping[:,1:],axis=0),axis=1)-np.diff(mapping[:,0]))
    if np.any(metric_error>8*numerical_tolerance):
        raise ValueError('Vertical chart has multiple XY branches at the same intrinsic abscissa')
    source_xy=np.asarray(samples)
    recovered=np.column_stack([np.interp(source_xy[:,0],mapping[:,0],mapping[:,axis]) for axis in [1,2]])
    remap_error=float(np.linalg.norm(recovered-source_xy[:,1:],axis=1).max())
    if remap_error>4*numerical_tolerance:
        raise ValueError('Unfolded mapping changed source coordinates beyond roundoff')
    source_interfaces=None
    if 'interface_kind' in mesh.face_attributes:
        source_interfaces={'upper':[],'lower':[]}
        adjacency=mesh.face_adjacency;edges=mesh.face_adjacency_edges
        selected=np.isin(adjacency,face_ids)
        for pair,edge,inside in zip(adjacency[np.sum(selected,axis=1)==1],edges[np.sum(selected,axis=1)==1],selected[np.sum(selected,axis=1)==1]):
            inner=int(pair[np.flatnonzero(inside)[0]]);outer=int(pair[np.flatnonzero(~inside)[0]])
            kind=int(mesh.face_attributes['interface_kind'][outer])
            if kind:
                line=[[float(charts[inner][np.flatnonzero(mesh.faces[inner]==vertex)[0]]),float(mesh.vertices[vertex,2])] for vertex in edge]
                if line[0]!=line[1]:source_interfaces['upper' if kind>0 else 'lower'].append(line)
    receipt=dict(source_vertical_faces=len(face_ids),source_vertical_area_mm2=source_area,
        unfolded_domain_area_mm2=domain.area,unfolded_triangle_area_sum_mm2=unfolded_sum,
        numerical_area_tolerance_mm2=area_tolerance,period_mm=period,
        mapping_breakpoints=len(mapping),source_coordinate_roundtrip_max_mm=remap_error,
        canonical_intrinsic_coordinate_adjustment_mm=maximum_canonical_adjustment,
        numerical_coordinate_tolerance_mm=numerical_tolerance,source_interface_traces_2d_mm=source_interfaces)
    return domain,mapping,receipt


class _NativeDomain(GridBlockSupport):
    """Only adapt the hatch bounding rectangle to the unfolded coordinate system."""
    def __init__(self, source, domain):
        super().__init__(supportVolume=source.supportVolume)
        for name in ['gridSpacing','supportWallThickness','supportBorderDistance','trussWidth',
                     'generateTrussGrid',
                     'trussAngle','supportTeethHeight','supportTeethTopLength','supportTeethBottomLength',
                     'supportTeethBaseInterval','supportTeethUpperPenetration',
                     'useLowerSupportTeeth','useUpperSupportTeeth','useSupportBorder']:
            setattr(self,name,getattr(source,name))
        self.domain=domain
    def generateSliceBoundingBoxPolygon(self, section):
        return self.domain.envelope


def _tree_polygons(tree):
    polygons=[]
    if len(tree.polygon) and not tree.isHole:
        polygons.append(Polygon(tree.polygon,[child.polygon for child in tree.children if child.isHole]))
    for child in tree.children:
        polygons.extend(_tree_polygons(child))
    return polygons


def native_infill(block, domain, defer_component_contacts=False,diagnostic_contacts=False,interfaces=None):
    # Native grid coordinates are (Z, abscissa); restore (abscissa,Z) afterwards.
    planar=shapely.transform(domain,lambda p:p[:,::-1])
    segments=[]
    for polygon in polygon_parts(planar):
        for ring in [polygon.exterior,*polygon.interiors]:
            points=np.array(ring.coords)
            segments.extend(np.stack([points[:-1],points[1:]],axis=1))
    generator=_NativeDomain(block,planar)
    tree=generator.generateSliceGeometry((np.asarray(segments),np.eye(4),np.zeros(len(segments),dtype=int)))
    from solid_sheets import as_tree
    tree=as_tree(tree)
    if tree is None:
        raise ValueError('Native infill omitted a required vertical domain')
    skin=shapely.union_all(_tree_polygons(tree))
    skin=shapely.transform(skin,lambda p:p[:,::-1])
    from quantized_contacts import restore_short_horizontal_interfaces
    skin,restoration=restore_short_horizontal_interfaces(skin,domain,float(block.toothProfile()[-1,0]),interfaces)
    # Restrict the numerical Clipper offset at open seams to the original abscissa span.
    tmin,zmin,tmax,zmax=domain.bounds
    penetration=block.supportTeethUpperPenetration
    allowed_parts=[]
    for polygon in polygon_parts(domain):
        for triangle in shapely.get_parts(shapely.constrained_delaunay_triangles(polygon)):
            points=np.array(triangle.exterior.coords)[:-1]
            allowed_parts.append(shapely.MultiPoint(np.vstack([points+[0,penetration],points-[0,penetration]])).convex_hull)
    allowed=shapely.union_all(allowed_parts)
    skin=skin.intersection(allowed).intersection(box(tmin,zmin-penetration,tmax,zmax+penetration))
    continuous=None
    if getattr(block,'continuousFragmentedInterfaces',False):
        from continuous_interfaces import repair
        skin,continuous=repair(skin,domain,interfaces,penetration)
    exact_short_contour=None
    if skin.is_empty and block.useSupportBorder:
        # The native border-fill fallback is the original closed section. Its
        # final default Clipper can collapse a sheet narrower than one lattice
        # step. Restore that source contour exactly instead of omitting it.
        import pyclipr
        step=1./float(pyclipr.Clipper().scaleFactor)
        fallback=generator.gridCoverage['sections_without_truss_interior']
        if tmax-tmin<step and fallback and all(r['treatment']=='configured_boundary_fills_section' for r in fallback):
            skin=domain
            exact_short_contour=dict(reason='native_configured_boundary_fill_collapsed_below_Clipper_step',
                native_quantization_step_mm=step,source_abscissa_span_mm=tmax-tmin,
                exact_source_contour_retained=True,boundary_vertex_displacement_mm=0.,
                source_area_mm2=domain.area,generated_area_mm2=skin.area,
                teeth='native_short_contour_boundary_fill_without_resolvable_truss_or_tooth')
    if skin.is_empty or not skin.is_valid:
        error=ValueError('Native infill did not produce a finite valid skin')
        error.receipt=dict(status='rejected',kind='skin',domain_bounds_mm=list(domain.bounds),
            domain_area_mm2=domain.area,domain_geometry_wkb_hex=domain.wkb_hex,
            native_material_empty=skin.is_empty,native_material_valid=skin.is_valid,
            native_grid_coverage=generator.gridCoverage)
        raise error
    from grid_intervals import contacts
    interface_contacts=contacts(skin,domain,interfaces)
    required=[row for row in interface_contacts if row['kind']=='required_free_interval']
    if not diagnostic_contacts and not all(row['passed'] for row in (required if defer_component_contacts else interface_contacts)):
        error=ValueError('A generated skin component or required interval lacks upper/lower contact')
        error.receipt=dict(status='rejected',kind='skin',contacts=interface_contacts,
            material_geometry_wkb_hex=skin.wkb_hex,free_domain_geometry_wkb_hex=domain.wkb_hex)
        raise error
    return skin,dict(native_grid_coverage=generator.gridCoverage,
        native_short_interface_restoration=restoration,
        continuous_interface_reconstruction=continuous,
        exact_short_contour_recovery=exact_short_contour,
        generated_planar_skin_area_mm2=skin.area,allowed_contact_penetration_mm=penetration,
        outside_free_domain_and_contact_band_area_mm2=skin.difference(allowed).area,
        required_free_intervals=len(polygon_parts(domain)),generated_material_components=len(polygon_parts(skin)),
        component_contacts_deferred_to_3d_graph=bool(defer_component_contacts),
        diagnostic_contacts_unproven=bool(diagnostic_contacts),
        interface_contacts=interface_contacts)


def remap(skin,mapping):
    """Split at every actual XY turn before remapping; never shortcut a corner."""
    vertices,faces=[],[];vertex_encoding_bounds=[];mapping_area_deviation_bound=0.
    area2d=0.;component_ranges=[];face_cursor=0
    zmin,zmax=skin.bounds[1],skin.bounds[3]
    for component_index,component in enumerate(polygon_parts(skin)):
        begin=face_cursor
        for i in range(len(mapping)-1):
            left,right=mapping[i,0],mapping[i+1,0]
            clipped=component.intersection(box(left,zmin-1,right,zmax+1))
            for polygon in polygon_parts(clipped):
                (points,triangles),_= _triangulate_exact_projected_domain(polygon,4.)
                fraction=(points[:,0]-left)/(right-left)
                xy=mapping[i,1:]+fraction[:,None]*(mapping[i+1,1:]-mapping[i,1:])
                first=points[:,0]==left;last=points[:,0]==right
                xy[first]=mapping[i,1:];xy[last]=mapping[i+1,1:]
                # Forward error of the eight scalar subtract/divide/multiply/add
                # operations, with exact IEEE inputs and no underflow here.
                u=np.finfo(float).eps/2;gamma8=8*u/(1-8*u)
                error=gamma8*np.linalg.norm(abs(mapping[i,1:])+abs(fraction[:,None])*(abs(mapping[i,1:])+abs(mapping[i+1,1:])),axis=1)
                error[first|last]=0.;vertex_encoding_bounds.append(error)
                stretch=np.linalg.norm(mapping[i+1,1:]-mapping[i,1:])/(right-left)
                mapping_area_deviation_bound+=polygon.area*abs(stretch-1.)
                world=np.column_stack([xy,points[:,1]])
                faces.append(triangles+sum(len(v) for v in vertices));vertices.append(world)
                area2d+=polygon.area;face_cursor+=len(triangles)
        component_ranges.append(dict(component_index=component_index,face_range=[begin,face_cursor],
            component_geometry_sha256=hashlib.sha256(component.wkb).hexdigest()))
    if not vertices:
        raise ValueError('Skin remapping produced no surface')
    mesh=trimesh.Trimesh(np.vstack(vertices),np.vstack(faces),process=False)
    tolerance=128*np.finfo(float).eps*max(1.,skin.area)*max(1,len(mesh.faces))
    errors=np.concatenate(vertex_encoding_bounds)[mesh.faces]
    edge1=mesh.triangles[:,1]-mesh.triangles[:,0];edge2=mesh.triangles[:,2]-mesh.triangles[:,0]
    delta1=errors[:,1]+errors[:,0];delta2=errors[:,2]+errors[:,0]
    encoding_area_bound=float(.5*np.sum(np.linalg.norm(edge1,axis=1)*delta2+np.linalg.norm(edge2,axis=1)*delta1+delta1*delta2))
    total_area_bound=tolerance+mapping_area_deviation_bound+encoding_area_bound
    if abs(area2d-skin.area)>tolerance or abs(mesh.area-skin.area)>total_area_bound:
        error=ValueError('Remapping changed the perforated skin area')
        error.receipt=dict(status='rejected',source_planar_area_mm2=skin.area,split_planar_area_mm2=area2d,
            remapped_area_mm2=mesh.area,numerical_area_tolerance_mm2=total_area_bound,
            mapping_t_xy_mm=mapping.tolist(),material_geometry_wkb_hex=skin.wkb_hex,
            triangles=len(mesh.faces))
        raise error
    from zero_area_faces import retained_faces
    keep,zero_area=retained_faces(mesh.vertices,mesh.faces,[tuple(r['face_range']) for r in component_ranges])
    prefix=np.r_[0,np.cumsum(keep)]
    for item in component_ranges:
        a,b=item['face_range'];item['face_range']=[int(prefix[a]),int(prefix[b])]
        if prefix[a]==prefix[b]:raise ValueError('A remapped material component has no positive-area encoded triangle')
    mesh=trimesh.Trimesh(mesh.vertices,mesh.faces[keep],process=False)
    return mesh,dict(split_planar_area_mm2=area2d,remapped_area_mm2=mesh.area,
                     numerical_area_tolerance_mm2=total_area_bound,
                     summation_area_bound_mm2=tolerance,intrinsic_mapping_area_deviation_bound_mm2=mapping_area_deviation_bound,
                     IEEE_vertex_encoding_area_bound_mm2=encoding_area_bound,
                     endpoint_mapping_identity_exact=True,triangles=len(mesh.faces),
                     exact_zero_area_cleanup=zero_area,
                     mapping_t_xy_mm=mapping.tolist(),material_component_face_ranges=component_ranges)


def generate(block,defer_component_contacts=False,diagnostic_contacts=False):
    if 'interface_kind' not in block.supportVolume.face_attributes:
        if block.supportObject is not None:raise ValueError('Production support contacts require native face ancestry')
        from interface_sources import fixture
        block.interfaceSourceReceipt=fixture(block.supportVolume)
    components,tolerance=vertical_components(block.supportVolume)
    charts=[];refinements=[];patches=None
    # Check all maps before expensive infill/contact construction. If a chart
    # still has several XY branches, its actual planar facet partition is a
    # conservative exact subdivision; no wall or closure is introduced.
    for chart_index,component in enumerate(components):
        try:
            unfolded=unfold(block.supportVolume,component)
            charts.append((component,*unfolded))
        except ValueError as error:
            if patches is None:patches=vertical_components(block.supportVolume,planar_only=True)[0]
            pieces=[p for p in patches if np.any(np.isin(p,component))]
            ids=np.concatenate(pieces)
            if not np.array_equal(np.sort(ids),np.sort(component)) or len(pieces)<=1:
                raise ValueError('No exact planar subdivision can repair the vertical chart') from error
            for piece in pieces:charts.append((piece,*unfold(block.supportVolume,piece)))
            refinements.append(dict(original_chart_index=chart_index,reason=str(error),
                source_faces=len(component),planar_charts=len(pieces),same_source_faces_exactly=True,
                source_coordinates_unchanged=True))
    meshes,rows=[],[];excluded=[]
    for original_index,(component,domain,mapping,receipt) in enumerate(charts):
        if hasattr(block,'exposureCalendar'):
            from layer_schedule import no_exposure
            proof=no_exposure(block.supportVolume,component,block.exposureCalendar)
            if proof is not None:
                excluded.append(dict(proof,source_chart_index=original_index));continue
        index=len(meshes)
        try:
            skin,native_receipt=native_infill(block,domain,defer_component_contacts,diagnostic_contacts,receipt['source_interface_traces_2d_mm'])
            mesh,remap_receipt=remap(skin,mapping)
        except ValueError as error:
            error.receipt=dict(getattr(error,'receipt',{}),vertical_chart_index=index,
                source_face_indices=component.tolist(),mapping_t_xy_mm=mapping.tolist(),unfolding=receipt)
            raise
        meshes.append(mesh);rows.append(dict(index=index,source_chart_index=original_index,unfolding=receipt,infill=native_receipt,remapping=remap_receipt))
    exposure_calendar=None
    if hasattr(block,'exposureCalendar'):
        planes=np.asarray(block.exposureCalendar,dtype=np.float64)
        exposure_calendar=dict(sha256=hashlib.sha256(planes.tobytes()).hexdigest(),planes=len(planes),
            first_z_mm=float(planes[0]),last_z_mm=float(planes[-1]),formula='z_i=(i+0.5)*layer_height_mm, evaluated as IEEE float64')
    return meshes,dict(status='generated_from_actual_vertical_sheets',exposure_calendar=exposure_calendar,
        expected_vertical_components=len(charts),generated_vertical_components=len(meshes),
        explicitly_unexposed_vertical_components=len(excluded),unexposed_vertical_charts=excluded,
        original_vertical_charts=len(components),exact_planar_chart_refinements=refinements,
        vertical_classification_roundoff_mm=tolerance,components=rows)


def geometry(block,diagnostic_contacts=False):
    """Combine native interior grids with admitted, remapped peripheral sheets."""
    from pyslm.support.gridBlockSupport import GridMeshType
    from grid_intervals import trim_and_admit
    if not block.generateTrussGrid:
        from solid_sheets import enable
        enable(block)
    continuous=getattr(block,'continuousFragmentedInterfaces',False)
    if continuous and block.generateTrussGrid:raise ValueError('Continuous fragmented interfaces require the explicit full-sheet strategy')
    if 'interface_kind' not in block.supportVolume.face_attributes:
        if block.supportObject is not None:raise ValueError('Production support contacts require native face ancestry')
        from interface_sources import fixture
        block.interfaceSourceReceipt=fixture(block.supportVolume)
    xgrid,ygrid=block.generateSupportSlices()
    # Local absence of a contact remains explicit. Only the separate geometric
    # connection graph may admit it; admissions.seal rejects unproven components.
    cycle=float(block.toothProfile()[-1,0])
    xgrid,x_admission=trim_and_admit(block.supportVolume,xgrid,0,block.supportTeethUpperPenetration,True,diagnostic_contacts,cycle,continuous)
    ygrid,y_admission=trim_and_admit(block.supportVolume,ygrid,1,block.supportTeethUpperPenetration,True,diagnostic_contacts,cycle,continuous)
    skins,receipt=generate(block,True,diagnostic_contacts)
    maximum=max([float(np.max(grid.face_attributes['order'])) for grid in [xgrid,ygrid] if len(grid.faces)],default=-1)
    for i,skin in enumerate(skins):
        skin.face_attributes['order']=np.full(len(skin.faces),maximum+1+i)
        skin.face_attributes['type']=np.full(len(skin.faces),GridMeshType.BOUNDARY)
    groups=[];base=0
    def component_contact(rows,index):
        matches=[(j,row) for j,row in enumerate(rows) if row['kind']=='generated_material_component' and row['component_index']==index]
        if len(matches)!=1:raise ValueError('A surface component has no unique contact identity')
        return matches[0]
    fields=['component_geometry_sha256','component_geometry_wkb_hex','upper_contact_trace_mm','lower_contact_trace_mm',
            'upper_contact_traces_2d_mm','lower_contact_traces_2d_mm',
            'upper_interface_traces_2d_mm','lower_interface_traces_2d_mm',
            'free_domain_geometry_wkb_hex','free_domain_geometry_sha256','contact_clip_scope']
    for axis,(mesh,audit) in enumerate([(xgrid,x_admission),(ygrid,y_admission)]):
        for plane_index,plane in enumerate(audit['planes']):
            for component in plane['material_component_face_ranges']:
                contact_index,contact=component_contact(plane['contacts'],component['component_index'])
                if contact['component_geometry_sha256']!=component['component_geometry_sha256']:
                    raise ValueError('Grid faces and contact component differ')
                begin,end=component['face_range']
                groups.append(dict(id=f"grid-{axis}-{plane['order']}-{component['component_index']}",kind='grid',
                    order=plane['order'],type=int(mesh.face_attributes['type'][begin]),face_range=[base+begin,base+end],
                    fixed_axis=axis,plane_coordinate_mm=plane['plane_coordinate_mm'],
                    contact_reference=f'/grid_coverage/axes/{axis}/planes/{plane_index}/contacts/{contact_index}',
                    **{field:contact[field] for field in fields}))
        base+=len(mesh.faces)
    for index,(mesh,component) in enumerate(zip(skins,receipt['components'])):
        for material in component['remapping']['material_component_face_ranges']:
            contact_index,contact=component_contact(component['infill']['interface_contacts'],material['component_index'])
            if contact['component_geometry_sha256']!=material['component_geometry_sha256']:
                raise ValueError('Skin faces and contact component differ')
            begin,end=material['face_range']
            groups.append(dict(id=f"skin-{index}-{material['component_index']}",kind='skin',
                order=int(mesh.face_attributes['order'][begin]),type=int(GridMeshType.BOUNDARY),face_range=[base+begin,base+end],
                mapping_t_xy_mm=component['remapping']['mapping_t_xy_mm'],
                contact_reference=f'/peripheral_skin/components/{index}/infill/interface_contacts/{contact_index}',
                **{field:contact[field] for field in fields}))
        base+=len(mesh.faces)
    if sum(group['face_range'][1]-group['face_range'][0] for group in groups)!=base:
        raise ValueError('Generated material groups omit or duplicate support faces')
    block.skinCoverage=dict(receipt,status='generated',algorithm='intrinsic_actual_vertical_sheet_unfold_native_infill_remap',
        support_surface_face_groups=groups,interface_source_provenance=block.interfaceSourceReceipt,
        continuous_fragmented_interfaces=bool(continuous),
        support_strategy='continuous_fragmented_interfaces_with_native_full_sheets' if continuous else 'native_perforated_truss' if block.generateTrussGrid else 'native_full_sheet_no_truss_perforation')
    block.gridCoverage=dict(status='passed',axes=[x_admission,y_admission])
    surface=block.concatenateMeshes([xgrid,ygrid,*skins])
    if not diagnostic_contacts:
        from material_connections import connected_material
        graph=connected_material(surface.vertices,surface.faces,groups)
        block.skinCoverage['material_connection_graph']=graph
        if graph['status']!='passed':
            error=ValueError('Actual support material has an unanchored or internally disconnected component')
            error.receipt=dict(status='rejected',material_connection_graph=graph,
                grid_coverage=block.gridCoverage,peripheral_skin=block.skinCoverage)
            raise error
    return surface
