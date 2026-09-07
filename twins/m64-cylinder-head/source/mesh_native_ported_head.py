#!/usr/bin/env python3
"""Hash-bound native BRep import and coarse tetra diagnostic, never CAE release.

The source BRep is read without STEP translation, healing, sewing, boolean
operations, defeaturing or scaling. Face correspondence uses geometric
descriptors, not Gmsh tag order. No physical boundary condition is assigned.
"""
import argparse
from array import array
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import resource
import sys
import time


TRIAL05_NATIVE_SHA256='3e3cc1631612fb9b7c36a34ceb157888ce66fdf3efb95f3ddad8578f74950ec5'
PRESERVED_SKIN_EVIDENCE_SHA256='21650160410a967cf85ee16f54ded5dad25610e07c67022d602fea8c27174a98'


def preserved_skin_meshadapt_assignments(native_sha, evidence, binding):
    """This experiment targets one hash-bound body's faces, never generic IDs."""
    if (native_sha!=TRIAL05_NATIVE_SHA256 or evidence.get('post_cut_native_BRep_sha256')!=native_sha
            or evidence.get('status')!='completed' or evidence.get('geometry_modified') is not False
            or evidence.get('native_tolerances_modified') is not False
            or evidence.get('pre_cut_source_unchanged') is not True
            or evidence.get('post_cut_source_unchanged') is not True
            or binding.get('descriptor_bijection_verified') is not True):
        raise ValueError('preserved_skin_experiment_provenance_failed')
    selected=(2193,2194,2263);rows=evidence.get('face_results',[])
    if (sorted(row.get('post_cut_face_index',-1) for row in rows)!=list(selected)
            or any(row.get('two_way_surface_area_equivalence_verified') is not True
                   or row.get('outside_both_gas_negatives_by_prior_bound_common') is not True for row in rows)):
        raise ValueError('preserved_skin_face_evidence_failed')
    assignments=[]
    for face in selected:
        matches=[row for row in binding['matches_private'] if row['source_face_index']==face]
        if len(matches)!=1:raise ValueError('preserved_skin_face_bijection_failed')
        assignments.append({'source_face_index':face,'gmsh_face_tag':matches[0]['gmsh_face_tag'],'algorithm':1})
    if len({row['gmsh_face_tag'] for row in assignments})!=len(selected):
        raise ValueError('preserved_skin_face_bijection_failed')
    return assignments


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, report):
    temporary = path.with_suffix(path.suffix+'.tmp')
    with temporary.open('x') as handle:
        json.dump(report,handle,indent=2,allow_nan=False); handle.write('\n')
    temporary.chmod(0o600); temporary.replace(path)


def signed_tetra_volume(a,b,c,d):
    x,y,z = ([point[i]-a[i] for i in range(3)] for point in (b,c,d))
    return (x[0]*(y[1]*z[2]-y[2]*z[1])-x[1]*(y[0]*z[2]-y[2]*z[0])
            +x[2]*(y[0]*z[1]-y[1]*z[0]))/6.


def connectivity_metrics(points_by_tag,tetrahedra,triangles):
    """Pure counterpart of audit_solid_mesh: signed volumes and face ownership."""
    parents = array('I',range(len(tetrahedra)))
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]; i = parents[i]
        return i
    faces = {}; volumes = []; repeated = 0
    for i,tetra in enumerate(tetrahedra):
        if len(tetra)!=4 or any(tag not in points_by_tag for tag in tetra):
            raise ValueError('invalid_tetra_node_reference')
        repeated += len(set(tetra))!=4
        volume = signed_tetra_volume(*(points_by_tag[tag] for tag in tetra))
        if not math.isfinite(volume):
            raise ValueError('nonfinite_tetra_volume')
        volumes.append(volume)
        for ids in ((0,1,2),(0,1,3),(0,2,3),(1,2,3)):
            face = tuple(sorted(tetra[j] for j in ids))
            if face in faces:
                first,count = faces[face]; faces[face]=(first,count+1)
                left,right = root(i),root(first)
                if left!=right: parents[left]=right
            else: faces[face]=(i,1)
    stored = Counter(tuple(sorted(triangle)) for triangle in triangles)
    if any(len(face)!=3 or any(tag not in points_by_tag for tag in face) for face in stored):
        raise ValueError('invalid_surface_triangle_node_reference')
    boundary = {face for face,(_,count) in faces.items() if count==1}
    missing = len(boundary-stored.keys()); extra = len(stored.keys()-boundary)
    nonmanifold = sum(count>2 for _,count in faces.values())
    duplicates = sum(count-1 for count in stored.values())
    return {'signed_volume_sum':math.fsum(volumes),'absolute_volume_sum':math.fsum(abs(v) for v in volumes),
            'minimum_signed_tetra_volume':min(volumes,default=None),
            'count_negative':sum(v<0 for v in volumes),'count_zero':sum(v==0 for v in volumes),
            'repeated_node_tetrahedra':repeated,'tetra_connected_components':len({root(i) for i in range(len(tetrahedra))}),
            'boundary_missing_triangles':missing,'stored_triangles_not_on_boundary':extra,
            'duplicate_stored_triangles':duplicates,'nonmanifold_faces':nonmanifold,
            'boundary_triangle_count':len(boundary),'boundary_matches':not(missing or extra or duplicates or nonmanifold)}


def match_faces(reference, imported, centre_tolerance=1e-4, relative_area_tolerance=1e-6):
    grid = defaultdict(list)
    for face in reference:
        grid[tuple(math.floor(x/centre_tolerance) for x in face['centre'])].append(face)
    matches=[]; ambiguous=[]; missing=[]; seen=Counter()
    for face in imported:
        key = tuple(math.floor(x/centre_tolerance) for x in face['centre'])
        options=[]
        for offset in itertools.product((-1,0,1),repeat=3):
            for original in grid.get(tuple(a+b for a,b in zip(key,offset)),[]):
                centre_delta=math.dist(original['centre'],face['centre'])
                area_delta=abs(original['area']-face['area'])
                if centre_delta<=centre_tolerance and area_delta<=max(1e-6,relative_area_tolerance*original['area']):
                    options.append((original,centre_delta,area_delta))
        if len(options)!=1:
            (ambiguous if options else missing).append(face['tag']); continue
        original,centre_delta,area_delta=options[0]; seen[original['tag']]+=1
        matches.append({'source_face_index':original['tag'],'gmsh_face_tag':face['tag'],
                        'centre_delta':centre_delta,'area_delta':area_delta})
    return {'matches_private':matches,'unmatched_gmsh_faces':missing,'ambiguous_gmsh_faces':ambiguous,
            'unmatched_source_faces':[face['tag'] for face in reference if not seen[face['tag']]],
            'multiply_matched_source_faces':[tag for tag,count in seen.items() if count>1],
            'centre_tolerance_scan_units':centre_tolerance,'relative_area_tolerance':relative_area_tolerance,
            'descriptor_bijection_verified':len(matches)==len(reference)==len(imported) and all(count==1 for count in seen.values()),
            'descriptor_match_is_not_full_geometric_equivalence_proof':True}


def quality_distribution(qualities, determinants):
    if len(qualities)!=len(determinants) or not qualities or not all(math.isfinite(v) for v in qualities+determinants):
        raise ValueError('invalid_quality_or_Jacobian_array')
    bad=[i for i,value in enumerate(qualities) if value<.1]
    absolute_volume=math.fsum(abs(value)/6 for value in determinants)
    return {'tetrahedra':len(qualities),'minimum_minSICN':min(qualities),
            'minSICN_below_0p1':len(bad),'minSICN_below_1e_6':sum(value<1e-6 for value in qualities),
            'minimum_Jacobian_determinant':min(determinants),
            'nonpositive_Jacobians':sum(value<=0 for value in determinants),
            'bad_tetrahedron_count_fraction':len(bad)/len(qualities),
            'bad_tetrahedron_absolute_volume_fraction':math.fsum(abs(determinants[i])/6 for i in bad)/absolute_volume if absolute_volume else None}


def reread_quality_gate(qualities, determinants, expected_count):
    """Recompute export acceptance; tiny coordinate drift is not a quality proof."""
    distribution=quality_distribution(qualities,determinants)
    result={'tetrahedron_count_matches':len(qualities)==expected_count and expected_count>0,
            'positive_jacobians':distribution['nonpositive_Jacobians']==0,
            'minSICN_project_limit':distribution['minimum_minSICN']>=.1,
            'quality_distribution':distribution}
    result['passed']=all(result[key] for key in ('tetrahedron_count_matches','positive_jacobians','minSICN_project_limit'))
    return result


def triangle_signatures(points, triangles):
    """Tag/order-independent coordinate signatures; exact hex is not rounded."""
    exact=[]; oriented=[]; rounded=[]
    for triangle in triangles:
        vertices=tuple(tuple(float(value).hex() for value in points[tag]) for tag in triangle)
        if len(vertices)!=3:raise ValueError('only_triangles_supported')
        exact.append(tuple(sorted(vertices)))
        oriented.append(min(vertices[i:]+vertices[:i] for i in range(3)))
        rounded.append(tuple(sorted(tuple(round(value,12) for value in points[tag]) for tag in triangle)))
    def digest(rows):
        return hashlib.sha256(json.dumps(sorted(rows),separators=(',',':')).encode()).hexdigest()
    return {'triangles':len(exact),'exact_unoriented_sha256':digest(exact),
            'exact_oriented_sha256':digest(oriented),'rounded12_unoriented_sha256':digest(rounded)}


def surface_mesh_snapshot(gmsh):
    tags,xyz,_=gmsh.model.mesh.getNodes()
    points={int(tag):tuple(map(float,xyz[3*i:3*i+3])) for i,tag in enumerate(tags)}
    rows=[]
    for _,tag in gmsh.model.getEntities(2):
        types,_,flat=gmsh.model.mesh.getElements(2,tag)
        if list(map(int,types))!=[2]:raise ValueError('only_linear_surface_triangles_supported')
        triangles=[tuple(map(int,flat[0][i:i+3])) for i in range(0,len(flat[0]),3)]
        rows.append({'gmsh_face_tag':tag,**triangle_signatures(points,triangles)})
    return sorted(rows,key=lambda row:row['gmsh_face_tag'])


def quality_locations(gmsh, surfaces, binding, tags, tetrahedra, points, quality, determinants):
    """Private mesh diagnostics, not an inferred anatomical classification."""
    boundary={}; type_by_tag={};surface_quality=[]
    source_by_tag={item['gmsh_face_tag']:item['source_face_index'] for item in binding['matches_private']}
    for _,surface in surfaces:
        types,triangle_tags,nodes=gmsh.model.mesh.getElements(2,surface)
        if list(map(int,types))!=[2]:raise ValueError('nontriangular_surface_in_diagnostic')
        triangle_quality=list(map(float,gmsh.model.mesh.getElementQualities(triangle_tags[0],'minSICN')))
        if not triangle_quality or not all(math.isfinite(q) for q in triangle_quality):raise ValueError('invalid_surface_quality')
        flat=list(map(int,nodes[0]));type_by_tag[surface]=gmsh.model.getType(2,surface)
        areas=[]
        for i in range(0,len(flat),3):
            face=tuple(sorted(flat[i:i+3]))
            if face in boundary:raise ValueError('surface_triangle_multiple_CAD_owners')
            boundary[face]=surface
            a,b,c=(points[node] for node in face);u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
            areas.append(math.sqrt(sum(x*x for x in (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])))/2)
        surface_quality.append({'source_face_index':source_by_tag[surface],'gmsh_face_tag':surface,
                                'triangles':len(triangle_quality),'minimum_minSICN':min(triangle_quality),
                                'minSICN_below_0p1':sum(q<.1 for q in triangle_quality),
                                'minSICN_below_1e_6':sum(q<1e-6 for q in triangle_quality),
                                'nonpositive_minSICN':sum(q<=0 for q in triangle_quality),
                                'triangulated_area':math.fsum(areas),'minimum_triangle_area':min(areas)})
    bad=sorted((i for i,q in enumerate(quality) if q<.1),key=lambda i:quality[i])
    counts=Counter();no_boundary=0;worst=[]
    for rank,i in enumerate(bad):
        tetra=tetrahedra[i]
        owners=[boundary[face] for face in (tuple(sorted(tetra[j] for j in ids)) for ids in ((0,1,2),(0,1,3),(0,2,3),(1,2,3))) if face in boundary]
        counts.update(set(owners));no_boundary+=not owners
        if rank<100:
            vertices=[points[tag] for tag in tetra]
            worst.append({'tetra_tag':tags[i],'minSICN':quality[i],'Jacobian_determinant':determinants[i],
                          'centroid':[math.fsum(p[k] for p in vertices)/4 for k in range(3)],
                          'node_tags':tetra,'coordinates_private':vertices,
                          'boundary_source_face_indices':[source_by_tag[tag] for tag in owners],
                          'boundary_gmsh_face_tags':owners,'boundary_CAD_types':[type_by_tag[tag] for tag in owners]})
    return {'worst_100_tetrahedra_private':worst,'bad_tetrahedra_with_no_boundary_face':no_boundary,
            'surface_quality_by_source_face_private':surface_quality,
            'bad_tetrahedra_touching_boundary_face':len(bad)-no_boundary,
            'surface_incidence_counts_are_not_unique_tetrahedron_counts':True,
            'CAD_surface_incidence_private':[{'gmsh_face_tag':tag,'source_face_index':source_by_tag[tag],
                                            'CAD_type':type_by_tag[tag],'bad_tetrahedra':count} for tag,count in counts.most_common()],
            'anatomical_classification_performed':False}


def baseline(args):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopoDS import TopoDS_Shape
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_SOLID,TopAbs_SHELL,TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
    from OCP.TopTools import TopTools_IndexedMapOfShape
    shape=TopoDS_Shape()
    if not BRepTools.Read_s(shape,str(args.input),BRep_Builder()): raise ValueError('native_read_failed')
    checker=BRepCheck_Analyzer(shape,True); checker.SetExactMethod(True)
    if not checker.IsValid(): raise ValueError('native_source_invalid')
    counts={}; faces=None
    for label,kind in [('solids',TopAbs_SOLID),('shells',TopAbs_SHELL),('faces',TopAbs_FACE),('edges',TopAbs_EDGE),('vertices',TopAbs_VERTEX)]:
        index=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(shape,kind,index);counts[label]=index.Extent()
        if label=='faces':faces=index
    properties=GProp_GProps();BRepGProp.VolumeProperties_s(shape,properties)
    if counts['solids']!=1 or properties.Mass()<=0: raise ValueError('one_positive_native_solid_required')
    descriptors=[]
    for i in range(1,faces.Extent()+1):
        props=GProp_GProps();BRepGProp.SurfaceProperties_s(faces.FindKey(i),props)
        centre=props.CentreOfMass()
        descriptors.append({'tag':i,'area':props.Mass(),'centre':[centre.X(),centre.Y(),centre.Z()]})
    report={'schema':'m64-private-native-mesh-source-baseline/v1','native_BRep_sha256':args.sha256,
            'source_sha256':sha256(Path(__file__)),'OCP_version':OCP.__version__,'counts':counts,
            'volume':properties.Mass(),'area':math.fsum(face['area'] for face in descriptors),
            'face_descriptors_private':descriptors,'native_BRep_valid':True,
            'source_unchanged':sha256(args.input)==args.sha256,'manufacturing_authorized':False}
    save(args.output/'native-baseline.json',report)
    print(json.dumps({key:report[key] for key in ('counts','volume','area','source_unchanged')}),flush=True)


def mesh(args):
    import gmsh
    baseline_hash=sha256(args.baseline); source=json.loads(args.baseline.read_text())
    if source['native_BRep_sha256']!=args.sha256 or not source['source_unchanged']:
        raise ValueError('native_baseline_binding_failed')
    started=time.monotonic()
    report={'schema':'m64-private-native-ported-head-mesh/v1','status':'incomplete',
            'native_BRep_sha256':args.sha256,'baseline_sha256':baseline_hash,'source_sha256':sha256(Path(__file__)),
            'gmsh_version':gmsh.__version__,'length_units':'unverified_scan_units_no_scaling',
            'geometry_mutated':False,'STEP_used':False,'defeaturing_or_decimation_used':False,
            'manufacturing_authorized':False,'physical_boundary_conditions_assigned':False,
            'ready_for_CHT_or_structure':False,'stage':'initializing',
            'mesh_size_min':args.minimum,'mesh_size_max':args.maximum,
            'volume_relative_error_limit':.01,'import_relative_mass_limit':1e-6,
            'minSICN_project_limit':.1,'maximum_tetrahedra_audited':args.maximum_tetrahedra}
    report['tetrahedral_optimizer']=args.optimizer
    report['volume_algorithm']=args.volume_algorithm
    local_evidence_hash=sha256(args.preserved_skin_meshadapt_evidence) if args.preserved_skin_meshadapt_evidence else None
    if local_evidence_hash and local_evidence_hash!=PRESERVED_SKIN_EVIDENCE_SHA256:
        raise ValueError('preserved_skin_evidence_hash_mismatch')
    report_path=args.output/'mesh-report.json';save(report_path,report)
    gmsh.initialize(['native-ported-head','-nopopup'],readConfigFiles=False,run=False)
    gmsh.logger.start()
    try:
        options={'General.Terminal':0,'General.NumThreads':2,
                 'Mesh.MaxNumThreads1D':2,'Mesh.MaxNumThreads2D':2,'Mesh.MaxNumThreads3D':2,
                 'Geometry.OCCFixDegenerated':0,'Geometry.OCCFixSmallEdges':0,'Geometry.OCCFixSmallFaces':0,
                 'Geometry.OCCSewFaces':0,'Geometry.OCCMakeSolids':0,'Geometry.OCCAutoFix':0,'Geometry.OCCScaling':1,
                 'Mesh.ElementOrder':1,'Mesh.RecombineAll':0,'Mesh.Algorithm':6,'Mesh.Algorithm3D':args.volume_algorithm,
                 'Mesh.MeshSizeMin':args.minimum,'Mesh.MeshSizeMax':args.maximum,
                 'Mesh.MeshSizeFromCurvature':12,'Mesh.MeshSizeFromPoints':0,
                 'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,'Mesh.RandomSeed':1}
        for name,value in options.items():gmsh.option.setNumber(name,value)
        report['explicit_options']=options;report['build_options']=gmsh.option.getString('General.BuildOptions')
        report['stage']='native_import';save(report_path,report)
        gmsh.model.add('native_ported_head_NOT_CAE_READY')
        gmsh.model.occ.importShapes(str(args.input),highestDimOnly=False);gmsh.model.occ.synchronize()
        volumes=gmsh.model.getEntities(3); surfaces=gmsh.model.getEntities(2)
        imported_volume=math.fsum(gmsh.model.occ.getMass(3,tag) for _,tag in volumes)
        descriptors=[{'tag':tag,'area':gmsh.model.occ.getMass(2,tag),
                      'centre':list(gmsh.model.occ.getCenterOfMass(2,tag))} for _,tag in surfaces]
        imported_area=math.fsum(face['area'] for face in descriptors)
        binding=match_faces(source['face_descriptors_private'],descriptors)
        report['import']={'volume_regions':len(volumes),'surface_entities':len(surfaces),
                          'volume':imported_volume,'area':imported_area,
                          'volume_relative_difference':abs(imported_volume/source['volume']-1),
                          'area_relative_difference':abs(imported_area/source['area']-1),
                          'source_face_count_difference':len(surfaces)-source['counts']['faces'],
                          'face_correspondence':binding}
        report['stage']='native_import_checked';save(report_path,report)
        if (len(volumes)!=1 or not binding['descriptor_bijection_verified']
                or report['import']['volume_relative_difference']>1e-6
                or report['import']['area_relative_difference']>1e-6):
            raise ValueError('native_import_geometry_invariants_failed')
        if local_evidence_hash:
            evidence=json.loads(args.preserved_skin_meshadapt_evidence.read_text())
            assignments=preserved_skin_meshadapt_assignments(args.sha256,evidence,binding)
            for item in assignments:
                gmsh.model.mesh.setAlgorithm(2,item['gmsh_face_tag'],item['algorithm'])
            report['local_surface_algorithm_override']={'native_BRep_sha256':args.sha256,
                'preserved_source_evidence_sha256':local_evidence_hash,'assignments':assignments,
                'only_local_surface_meshing_parameter_change':'MeshAdapt_1_instead_of_Frontal_Delaunay_6_on_three_preserved_faces',
                'primary_documentation':'https://gmsh.info/doc/texinfo/#Choosing-the-right-unstructured-algorithm'}
            save(report_path,report)
        for dimension in (1,2,3):
            report['stage']='meshing_'+str(dimension)+'D';save(report_path,report)
            gmsh.model.mesh.generate(dimension)
            if args.volume_algorithm==10 and dimension in (2,3):
                snapshot=surface_mesh_snapshot(gmsh)
                snapshot_path=args.output/('surface-before-3D-private.json' if dimension==2 else 'surface-after-3D-private.json')
                save(snapshot_path,{'schema':'m64-private-surface-triangulation-snapshot/v1',
                    'native_BRep_sha256':args.sha256,'source_sha256':report['source_sha256'],
                    'gmsh_version':gmsh.__version__,'surface_rows_private':snapshot,
                    'exact_signature_scope':'Coordinates serialized as float.hex, triangles unordered; oriented signature retains winding modulo cyclic permutation.',
                    'rounded_signature_scope':'Unoriented triangles with coordinates rounded to 12 decimals; not exact equivalence.'})
                if dimension==2:
                    before_surfaces=snapshot
                    report['surface_before_3D_sha256']=sha256(snapshot_path)
                else:
                    report['surface_after_3D_sha256']=sha256(snapshot_path)
                    report['surface_triangulations_unchanged_during_3D']=snapshot==before_surfaces
                save(report_path,report)
        if args.optimizer=='netgen':
            report['stage']='optimizing_tetrahedra_netgen';save(report_path,report)
            before_types,before_tags,before_nodes=gmsh.model.mesh.getElements(3)
            if list(map(int,before_types))!=[4]:raise ValueError('only_first_order_tetrahedra_supported')
            before_quality=list(map(float,gmsh.model.mesh.getElementQualities(before_tags[0],'minSICN')))
            before_determinants=list(map(float,gmsh.model.mesh.getElementQualities(before_tags[0],'minDetJac')))
            report['before_optimization']=quality_distribution(before_quality,before_determinants)
            before_flat=list(map(int,before_nodes[0]))
            before_tetra=[before_flat[i:i+4] for i in range(0,len(before_flat),4)]
            before_node_tags,before_xyz,_=gmsh.model.mesh.getNodes()
            before_points={int(tag):tuple(map(float,before_xyz[3*i:3*i+3])) for i,tag in enumerate(before_node_tags)}
            save(args.output/'before-optimization-quality-locations-private.json',quality_locations(
                gmsh,surfaces,binding,list(map(int,before_tags[0])),before_tetra,before_points,before_quality,before_determinants))
            save(report_path,report)
            del before_flat,before_tetra,before_points,before_quality,before_determinants
            gmsh.model.mesh.optimize('Netgen',force=False,niter=1)
        report['stage']='auditing_generated_tetrahedra';save(report_path,report)
        types,element_tags,element_nodes=gmsh.model.mesh.getElements(3)
        if list(map(int,types))!=[4]:raise ValueError('only_first_order_tetrahedra_supported')
        tags=list(map(int,element_tags[0]));flat=list(map(int,element_nodes[0]))
        if not tags or len(tags)>args.maximum_tetrahedra:raise ValueError('tetra_count_outside_bounded_audit_limit')
        tetrahedra=[flat[i:i+4] for i in range(0,len(flat),4)]
        surface_types,_,surface_nodes=gmsh.model.mesh.getElements(2)
        if list(map(int,surface_types))!=[2]:raise ValueError('only_linear_surface_triangles_supported')
        flat=list(map(int,surface_nodes[0]));triangles=[flat[i:i+3] for i in range(0,len(flat),3)]
        node_tags,coordinates,_=gmsh.model.mesh.getNodes()
        points={int(tag):tuple(map(float,coordinates[3*i:3*i+3])) for i,tag in enumerate(node_tags)}
        if len(points)!=len(node_tags):raise ValueError('duplicate_node_tags')
        report['mesh']={'nodes':len(points),'tetrahedra':len(tetrahedra),'surface_triangles':len(triangles),
                        'connectivity':connectivity_metrics(points,tetrahedra,triangles)}
        quality=list(map(float,gmsh.model.mesh.getElementQualities(tags,'minSICN')))
        determinants=list(map(float,gmsh.model.mesh.getElementQualities(tags,'minDetJac')))
        if len(quality)!=len(tags) or len(determinants)!=len(tags) or not all(math.isfinite(v) for v in quality+determinants):
            raise ValueError('invalid_quality_or_Jacobian_array')
        report['mesh'].update({'minimum_minSICN':min(quality),'minSICN_below_0p1':sum(v<.1 for v in quality),
            'minimum_Jacobian_determinant':min(determinants),'nonpositive_Jacobians':sum(v<=0 for v in determinants),
            'CAD_faces_without_surface_elements':[tag for _,tag in surfaces if not any(len(group) for group in gmsh.model.mesh.getElements(2,tag)[1])]})
        report['mesh']['quality_distribution']=quality_distribution(quality,determinants)
        save(args.output/'quality-locations-private.json',quality_locations(gmsh,surfaces,binding,tags,tetrahedra,points,quality,determinants))
        post_volume=math.fsum(gmsh.model.occ.getMass(3,tag) for _,tag in gmsh.model.getEntities(3))
        post_faces=[{'tag':tag,'area':gmsh.model.occ.getMass(2,tag),'centre':list(gmsh.model.occ.getCenterOfMass(2,tag))} for _,tag in gmsh.model.getEntities(2)]
        report['native_CAD_model_unchanged_after_meshing']=(gmsh.model.getEntities(3)==volumes and post_volume==imported_volume and post_faces==descriptors)
        conn=report['mesh']['connectivity']
        report['mesh']['volume_relative_difference_from_native']=abs(conn['signed_volume_sum']/source['volume']-1)
        path=args.output/'coarse-native-head.msh';gmsh.option.setNumber('Mesh.SaveAll',1);gmsh.write(str(path));path.chmod(0o600)
        mesh_hash=sha256(path);report['mesh']['sha256']=mesh_hash
        original_tags=sorted(tags); original_tetra=sorted(tuple(t) for t in tetrahedra)
        original_triangles=sorted(tuple(t) for t in triangles);original_points=points
        gmsh.clear();gmsh.open(str(path))
        reread_types,reread_tags,reread_flat=gmsh.model.mesh.getElements(3)
        reread_surface_types,_,reread_surface_flat=gmsh.model.mesh.getElements(2)
        reread_node_tags,reread_xyz,_=gmsh.model.mesh.getNodes()
        reread_points={int(tag):tuple(map(float,reread_xyz[3*i:3*i+3])) for i,tag in enumerate(reread_node_tags)}
        reread_tetra=[tuple(map(int,reread_flat[0][i:i+4])) for i in range(0,len(reread_flat[0]),4)]
        reread_triangles=[tuple(map(int,reread_surface_flat[0][i:i+3])) for i in range(0,len(reread_surface_flat[0]),3)]
        report['mesh']['roundtrip']={'types_unchanged':list(map(int,reread_types))==[4] and list(map(int,reread_surface_types))==[2],
            'tetra_connectivity_unchanged':sorted(reread_tetra)==original_tetra,
            'surface_connectivity_unchanged':sorted(reread_triangles)==original_triangles,
            'tetra_tags_unchanged':sorted(map(int,reread_tags[0]))==original_tags,
            'node_tags_unchanged':reread_points.keys()==original_points.keys(),
            'maximum_coordinate_roundtrip_difference':max((math.dist(point,reread_points.get(tag,(math.inf,)*3)) for tag,point in original_points.items()),default=0.),
            'file_sha256_unchanged':sha256(path)==mesh_hash}
        reread=report['mesh']['roundtrip']
        report['mesh']['reread_quality']=reread_quality_gate(
            list(map(float,gmsh.model.mesh.getElementQualities(reread_tags[0],'minSICN'))),
            list(map(float,gmsh.model.mesh.getElementQualities(reread_tags[0],'minDetJac'))),len(tags))
        reread_quality=report['mesh']['reread_quality']
        export_ok=all(value is True for key,value in reread.items() if key!='maximum_coordinate_roundtrip_difference') and reread['maximum_coordinate_roundtrip_difference']<=1e-10
        export_ok=export_ok and reread_quality['passed']
        gates={'positive_jacobians':report['mesh']['nonpositive_Jacobians']==0,
               'native_CAD_model_unchanged_after_meshing':report['native_CAD_model_unchanged_after_meshing'],
               'positive_signed_tetra_volumes':not(conn['count_negative'] or conn['count_zero'] or conn['repeated_node_tetrahedra']),
               'one_connected_tetra_region':conn['tetra_connected_components']==1,
               'complete_tetra_boundary':conn['boundary_matches'],
               'all_CAD_faces_meshed':not report['mesh']['CAD_faces_without_surface_elements'],
               'minSICN_project_limit':min(quality)>=.1,
               'reread_positive_jacobians':reread_quality['positive_jacobians'],
               'reread_minSICN_project_limit':reread_quality['minSICN_project_limit'],
               'coarse_volume_error_limit':report['mesh']['volume_relative_difference_from_native']<=.01,
               'mesh_export_roundtrip':export_ok}
        if args.volume_algorithm==10:
            gates['surface_triangulations_unchanged_during_3D']=report['surface_triangulations_unchanged_during_3D']
        report['gates']=gates
        report['status']='coarse_mesh_checks_passed_NOT_CAE_VALIDATED' if all(gates.values()) else 'mesh_generated_but_rejected_by_quality_or_integrity_gate'
    except Exception as error:
        report['status']='failed';report['failure']={'type':type(error).__name__,'message_private':str(error)}
    finally:
        logs=gmsh.logger.get();gmsh.logger.stop();gmsh.finalize()
        save(args.output/'gmsh-log-private.json',{'lines':logs})
        report['elapsed_seconds']=time.monotonic()-started
        report['native_input_unchanged']=sha256(args.input)==args.sha256
        report['baseline_unchanged']=sha256(args.baseline)==baseline_hash
        report['source_unchanged']=sha256(Path(__file__))==report['source_sha256']
        report['preserved_skin_evidence_unchanged']=(sha256(args.preserved_skin_meshadapt_evidence)==local_evidence_hash) if local_evidence_hash else None
        if not all(report[key] for key in ('native_input_unchanged','baseline_unchanged','source_unchanged')):report['status']='failed_source_changed'
        if local_evidence_hash and not report['preserved_skin_evidence_unchanged']:report['status']='failed_source_changed'
        save(report_path,report)
    print(json.dumps({'status':report['status'],'stage':report['stage'],'elapsed_seconds':report['elapsed_seconds']}),flush=True)
    return 0 if report['status']=='coarse_mesh_checks_passed_NOT_CAE_VALIDATED' else 2


def argument_parser():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('baseline','mesh'),required=True)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--sha256',required=True)
    parser.add_argument('--baseline',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--minimum',type=float,default=1.);parser.add_argument('--maximum',type=float,default=6.)
    parser.add_argument('--maximum-tetrahedra',type=int,default=1500000)
    parser.add_argument('--optimizer',choices=('none','netgen'),default='none')
    parser.add_argument('--volume-algorithm',type=int,choices=(1,10),default=1,
                        help='1: historical Delaunay; 10: opt-in HXT volume counter-experiment')
    parser.add_argument('--preserved-skin-meshadapt-evidence',type=Path,
                        help='Exact private trial05 preserved-face evidence; never valid on another body')
    return parser


def main():
    parser=argument_parser();args=parser.parse_args()
    if not (math.isfinite(args.minimum) and math.isfinite(args.maximum) and 0<args.minimum<=args.maximum):parser.error('positive_mesh_size_interval_required')
    if args.mode=='mesh' and args.baseline is None:parser.error('baseline_required')
    if args.preserved_skin_meshadapt_evidence and (args.mode!='mesh' or args.optimizer!='none'
            or args.minimum!=1. or args.maximum!=6. or args.sha256!=TRIAL05_NATIVE_SHA256):
        parser.error('isolated_trial05_MeshAdapt_experiment_requires_original_sizes_and_no_optimizer')
    if args.output.exists():raise FileExistsError(args.output)
    if sha256(args.input)!=args.sha256:raise ValueError('native_BRep_hash_mismatch')
    args.output.mkdir(parents=True,mode=0o700)
    resource.setrlimit(resource.RLIMIT_CPU,(270,275))
    if args.mode=='baseline':baseline(args);return 0
    return mesh(args)


if __name__=='__main__':
    sys.exit(main())
