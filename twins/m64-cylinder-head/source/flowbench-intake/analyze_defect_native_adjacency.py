#!/usr/bin/env python3
"""Localize exported OpenFOAM labels by exact incidence, not VTK proximity.

Point coordinates are not identical across 12-significant-digit serialization.
An exhaustive unique coordinate correspondence uses a declared serialization
error budget, then boundary connectivity, orientation, patches and native face
bindings must match. No nearest-face distance, CAD edit, mesh edit or solve.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import resource
import time

import audit_segmented_c0_mesh as mesh_reader

DOMAIN='7fc114c1a8229665047c734fd22129783df420deb5e01e809995c6b3efdc5de8'
MESH='7774e94e8782a7fa4793977330fdbe27788579ea603f732439c9a2d8539dcf9a'
MESH_REPORT='85dab898495152c5ec2e715e393b9ee0500a6603d2bf02f10a8d7994e6a6f9ef'
MANIFEST='92576714217042c0f152c1da7d8a8fa0da8f1757e5ec06c9c6f4eee3c66ccc58'
LOCALIZATION='877216865f1a9858ce981044a793e11a2a499c3f49070e3c850e619107595216'
FAMILIES=('highAspectRatioCells','skewFaces','underdeterminedCells','concaveCells','lowWeightFaces','lowVolRatioFaces')
ANNULAR={55,56,57,58,61,62,63,64}
UNIFIED_DOMAIN='fab1338a3e3cf36469977716a9cb54b3118382f592c7c41d7c789bdb5fb3aeba'
UNIFIED_MESH='c0cbb257619ce378a9c9274da305d6bf34ce55dd4913a55cf122649ec45326ca'
UNIFIED_MESH_REPORT='de7094fdeff7a338c12ffa89febc80e9273c971d70c306f8238d2863ad980b47'
UNIFIED_MANIFEST='58b8be5aa0faeac678e6801cad29cfc5520cbf1590076276dbf5ad5157776aa1'
UNIFIED_LOCALIZATION='4eb33217f5610088af01e7c748c2bfa80bb297713b5e56954a89aad3b75fe0cc'
UNIFIED_ANNULAR={53,54,55,56,59,60,61,62}


def selected_profile(unified=False):
    if type(unified) is not bool:raise ValueError('explicit_boolean_profile_required')
    return {'domain':UNIFIED_DOMAIN if unified else DOMAIN,'msh':UNIFIED_MESH if unified else MESH,
        'mesh_report':UNIFIED_MESH_REPORT if unified else MESH_REPORT,
        'manifest':UNIFIED_MANIFEST if unified else MANIFEST,
        'localization':UNIFIED_LOCALIZATION if unified else LOCALIZATION,
        'annular':UNIFIED_ANNULAR if unified else ANNULAR,
        'thin_face':None if unified else 38,'merged_port_face':37 if unified else None,
        'families':tuple(n for n in FAMILIES if n!='concaveCells') if unified else FAMILIES}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def foam_list(path, kind):
    text=path.read_text()
    if not re.search(r'\bformat\s+ascii\s*;',text):raise ValueError('ASCII_FOAM_required')
    cls=re.search(r'\bclass\s+(\w+)\s*;',text)[1]
    found=re.search(r'^\s*(\d+)\s*\n\s*\(\s*\n',text,re.M)
    if not found:raise ValueError('FOAM_counted_list_required')
    number=int(found[1]);lines=text[found.end():].splitlines()
    if len(lines)<number+1 or lines[number].strip()!=')':raise ValueError('FOAM_list_count_mismatch')
    rows=[]
    for line in lines[:number]:
        line=line.strip()
        if kind=='points':
            if not line.startswith('(') or not line.endswith(')'):raise ValueError('FOAM_point_syntax')
            row=tuple(map(float,line[1:-1].split()))
            if len(row)!=3 or not all(map(math.isfinite,row)):raise ValueError('FOAM_point')
        elif kind=='faces':
            match=re.fullmatch(r'(\d+)\(([^()]*)\)',line)
            if not match:raise ValueError('FOAM_face_syntax')
            row=tuple(map(int,match[2].split()))
            if len(row)!=int(match[1]) or len(set(row))!=len(row):raise ValueError('FOAM_face_count')
        else:row=int(line)
        rows.append(row)
    return rows,cls


def half_print_quantum(x, precision):
    if x==0:return 0.
    # Include a possible decade crossing caused by rounding.
    exponent=max(math.floor(math.log10(abs(x))),math.floor(math.log10(abs(float(format(x,f'.{precision}g'))))))
    return .5*10.**(exponent-precision+1)


def point_bijection(msh_points,foam_points,precision=12,scale=.001):
    """Unique box correspondence; no nearest-neighbour choice or index guess.

    Budget per coordinate: one half-print quantum before scale, one after,
    plus 8 binary64 ULPs for parsing/multiply/serialization roundoff. This is a
    mapping budget, not a manufacturing tolerance or exact coordinate equality.
    """
    scaled={n:tuple(x*scale for x in p) for n,p in msh_points.items()}
    budgets={n:tuple(half_print_quantum(x,precision)*abs(scale)+half_print_quantum(y,precision)
        +8*max(math.ulp(y),math.ulp(x)*abs(scale)) for x,y in zip(msh_points[n],p)) for n,p in scaled.items()}
    width=max(b for p in budgets.values() for b in p)
    if not width>0:raise ValueError('nonzero_coordinate_span_required')
    buckets=defaultdict(list)
    def bucket(p):return tuple(math.floor(x/width) for x in p)
    for n,p in scaled.items():buckets[bucket(p)].append(n)
    mapping={};ambiguous=[];missing=[];max_delta=0.;max_ratio=0.
    offsets=list(itertools.product((-1,0,1),repeat=3))
    for i,p in enumerate(foam_points):
        cell=bucket(p);candidates=[]
        for off in offsets:
            for n in buckets.get(tuple(a+b for a,b in zip(cell,off)),()):
                if all(abs(x-y)<=budget for x,y,budget in zip(p,scaled[n],budgets[n])):candidates.append(n)
        if len(candidates)!=1:
            (missing if not candidates else ambiguous).append(i);continue
        n=candidates[0];mapping[i]=n
        for x,y,budget in zip(p,scaled[n],budgets[n]):
            delta=abs(x-y);max_delta=max(max_delta,delta)
            if budget:max_ratio=max(max_ratio,delta/budget)
    passed=not ambiguous and not missing and len(mapping)==len(msh_points)==len(foam_points) and len(set(mapping.values()))==len(mapping)
    proof={'passes':passed,'point_count':len(foam_points),'missing':len(missing),'ambiguous':len(ambiguous),
        'distinct_MSH_nodes':len(set(mapping.values())),'maximum_coordinate_delta_m':max_delta,
        'maximum_per_axis_mapping_budget_m':width,'maximum_consumed_budget_fraction':max_ratio,
        'precision_significant_digits':precision,'scale':scale,
        'method':'unique_all-point_serialization_budget_boxes_then_exact_topology; not nearest-point',
        'coordinate_identity_claimed':False,'two_print_half_quanta_plus_binary64_8ULP':True}
    return mapping,proof


def canonical(nodes):return min(nodes,nodes[1:]+nodes[:1],nodes[2:]+nodes[:2])


def family_summary(labels,kind,owner,neighbour,cell_boundary,native,*,unified=False):
    profile=selected_profile(unified)
    cells=set()
    if kind=='cellSet':cells.update(labels)
    elif kind=='faceSet':
        for face in labels:
            cells.add(owner[face])
            if face<len(neighbour):cells.add(neighbour[face])
    else:raise ValueError('cellSet_or_faceSet_required')
    internal_degree=Counter(itertools.chain(owner[:len(neighbour)],neighbour))
    degrees=Counter(internal_degree[c] for c in cells)
    histogram={};roles=Counter();combinations=Counter();boundary_triangles=set();interior=0
    for cell in cells:
        adjacent=cell_boundary.get(cell,())
        if not adjacent:interior+=1;continue
        face_ids={native_face for face,native_face in adjacent};cats=set()
        for face,native_face in adjacent:boundary_triangles.add(face)
        for face_id in face_ids:
            row=histogram.setdefault(face_id,{'native_face_id':face_id,'role':native[face_id]['role'],
                'source_match':native[face_id]['source_match'],'adjacent_affected_cells':0,'adjacent_boundary_triangles':0})
            row['adjacent_affected_cells']+=1
            if face_id in profile['annular']:cats.add('annular_guide_or_stem')
            elif face_id==profile['thin_face']:cats.add('thin_face_38')
            elif face_id==profile['merged_port_face']:cats.add('merged_port_face_37')
            elif native[face_id]['role']=='walls_seat':cats.add('seat')
            else:cats.add('other_boundary')
        for role in {native[f]['role'] for f in face_ids}:roles[role]+=1
        combinations['+'.join(sorted(cats))]+=1
    # Count triangles once per affected cell boundary. A boundary face has one owner.
    for cell in cells:
        for face,face_id in cell_boundary.get(cell,()):histogram[face_id]['adjacent_boundary_triangles']+=1
    return {'selected_kind':kind,'selected_entities':len(labels),'distinct_affected_cells':len(cells),
        'uncoupled_mesh_internal_face_degree_histogram':dict(sorted(degrees.items())),
        'affected_cells_with_at_most_two_internal_faces':sum(n for degree,n in degrees.items() if degree<=2),
        'internal_degree_is_topological_diagnostic_not_a_quality_waiver':True,
        'cells_with_no_boundary_face':interior,'cells_with_boundary_face':len(cells)-interior,
        'directly_selected_boundary_faces':sum(f>=len(neighbour) for f in labels) if kind=='faceSet' else None,
        'directly_selected_internal_faces':sum(f<len(neighbour) for f in labels) if kind=='faceSet' else None,
        'adjacent_boundary_triangles':len(boundary_triangles),
        'native_face_histogram':sorted(histogram.values(),key=lambda r:(-r['adjacent_affected_cells'],r['native_face_id'])),
        'role_histogram_unique_cells_per_role':dict(roles),'disjoint_boundary_category_combinations':dict(combinations),
        'counts_across_faces_or_roles_overlap':True,'distances_computed':False,
        'adjacency_does_not_prove_physical_or_numerical_cause':True}


def run(args):
    start=time.monotonic();unified=getattr(args,'unified_native_only',False);profile=selected_profile(unified)
    paths={args.msh:profile['msh'],args.mesh_report:profile['mesh_report'],args.manifest:profile['manifest'],
        args.localization/ 'localization-receipt.json':profile['localization'],Path(__file__):sha(__file__),
        Path(mesh_reader.__file__):sha(mesh_reader.__file__)}
    if any(sha(p)!=h for p,h in paths.items()):raise ValueError('fixed_input_or_source_hash_mismatch')
    local=json.loads((args.localization/'localization-receipt.json').read_text())
    if unified and (local.get('schema')!='m64-private-OpenFOAM-rejected-defect-localization/v2'
            or local.get('source_MSH_sha256')!=profile['msh'] or local.get('native_domain_sha256')!=profile['domain']
            or local.get('same_five_failure_lines_exact') is not True
            or local.get('concavity_check_passed_no_defect_set_exported') is not True):
        raise ValueError('new_unified_native_label_export_receipt_required')
    hashfile=args.localization/'remote-output'/'copy-geometry-before.sha256'
    if sha(hashfile)!=local['geometry_hash_manifest_sha256']:raise ValueError('geometry_hash_manifest_mismatch')
    for line in hashfile.read_text().splitlines():
        h,name=line.split();paths[args.case/'constant/polyMesh'/name]=h
    for p,h in paths.items():
        if sha(p)!=h:raise ValueError('FOAM_geometry_hash_mismatch')
    for name in ('system/controlDict','mesh-diagnostic.json'):paths[args.case/name]=sha(args.case/name)
    control=(args.case/'system/controlDict').read_text()
    precision=int(re.search(r'\bwritePrecision\s+(\d+)\s*;',control)[1])
    conversion=json.loads((args.case/'mesh-diagnostic.json').read_text())
    if conversion['mesh_sha256']!=profile['msh'] or conversion['native_domain_sha256']!=profile['domain'] or conversion['scale_applications']!=1:
        raise ValueError('converted_case_provenance_mismatch')
    points,gmsh_faces,kinds=mesh_reader.parse_surface_msh22(args.msh.read_text())
    foam_points,_=foam_list(args.case/'constant/polyMesh/points','points')
    point_map,point_proof=point_bijection(points,foam_points,precision,conversion['meters_per_scan_unit_unverified_hypothesis'])
    if not point_proof['passes']:raise ValueError('unique_point_correspondence_not_proven')
    faces,_=foam_list(args.case/'constant/polyMesh/faces','faces')
    owner,_=foam_list(args.case/'constant/polyMesh/owner','labels');neighbour,_=foam_list(args.case/'constant/polyMesh/neighbour','labels')
    ncell=kinds[4]
    if len(owner)!=len(faces) or len(neighbour)>=len(faces) or any(len(f)!=3 for f in faces):raise ValueError('triangular_mesh_sizes')
    if any(c<0 or c>=ncell for c in itertools.chain(owner,neighbour)):raise ValueError('cell_label_out_of_range')
    incidences=Counter(itertools.chain(owner,neighbour))
    if len(incidences)!=ncell or any(n!=4 for n in incidences.values()):raise ValueError('four_faces_per_tetra_cell_required')
    mr=json.loads(args.mesh_report.read_text());manifest=json.loads(args.manifest.read_text())
    lookup=mesh_reader.verified_face_lookup(mr['import']['face_binding_private'],profile['domain']);reverse={g:n for n,g in lookup.items()}
    native={r['id']:r for r in manifest['boundary_faces']}
    msh_triangles={}
    for gmsh_face,triangles in gmsh_faces.items():
        for tri in triangles:
            key=tuple(sorted(tri))
            if key in msh_triangles:raise ValueError('duplicate_MSH_boundary_triangle')
            msh_triangles[key]=(reverse[gmsh_face],canonical(tri))
    patches={}
    boundary=(args.case/'constant/polyMesh/boundary').read_text()
    for name,body in re.findall(r'(\w+)\s*\{([^{}]*)\}',boundary):
        count=re.search(r'\bnFaces\s+(\d+)\s*;',body);begin=re.search(r'\bstartFace\s+(\d+)\s*;',body)
        if count and begin:patches[name]=(int(begin[1]),int(count[1]))
    expected_role={'inlet':'inlet','receiver_outlet':'receiver_outlet'}
    if set(patches)!={'inlet','receiver_outlet','walls'}:raise ValueError('expected_three_patches')
    patch_for={i:name for name,(begin,count) in patches.items() for i in range(begin,begin+count)}
    if set(patch_for)!=set(range(len(neighbour),len(faces))):raise ValueError('complete_patch_index_partition')
    cell_boundary=defaultdict(list);seen=set();orientation_mismatches=0
    for i in range(len(neighbour),len(faces)):
        tri=tuple(point_map[n] for n in faces[i]);key=tuple(sorted(tri))
        if key not in msh_triangles or key in seen:raise ValueError('boundary_triangle_correspondence_not_bijective')
        seen.add(key);face_id,winding=msh_triangles[key]
        orientation_mismatches+=canonical(tri)!=winding
        patch=patch_for[i];role=native[face_id]['role']
        if (patch in expected_role and role!=expected_role[patch]) or (patch=='walls' and role in expected_role):raise ValueError('native_role_patch_mismatch')
        cell_boundary[owner[i]].append((i,face_id))
    if seen!=set(msh_triangles) or orientation_mismatches:raise ValueError('complete_oriented_boundary_required')
    family_results={};export_by_name={r['name']:r for r in local['exports']}
    for name in profile['families']:
        path=args.localization/'native-sets'/name;paths[path]=export_by_name[name]['native_set_sha256']
        if sha(path)!=paths[path]:raise ValueError('native_set_hash_mismatch')
        labels,kind=foam_list(path,'labels');maximum=ncell if kind=='cellSet' else len(faces)
        if len(labels)!=len(set(labels)) or any(x<0 or x>=maximum for x in labels):raise ValueError('native_set_labels_invalid')
        family_results[name]=family_summary(labels,kind,owner,neighbour,cell_boundary,native,unified=unified)
    result={'schema':'m64-private-OpenFOAM-native-face-adjacency/v1','status':'exact_boundary_incidence_localized',
        'source_sha256':paths[Path(__file__)],'reader_source_sha256':paths[Path(mesh_reader.__file__)],
        'native_domain_sha256':profile['domain'],'mesh_sha256':profile['msh'],'mesh_report_sha256':profile['mesh_report'],'native_manifest_sha256':profile['manifest'],
        'localization_receipt_sha256':profile['localization'],'point_mapping':point_proof,
        'boundary_triangle_bijection':{'matches':len(seen),'orientation_mismatches':orientation_mismatches,'native_face_count':len(native),'patch_role_partition_verified':True},
        'cell_count':ncell,'families':family_results,
        'annular_guide_and_stem_native_face_ids':sorted(profile['annular']),'thin_native_face_id':profile['thin_face'],
        'merged_port_native_face_id':profile['merged_port_face'],
        'concavity_check_passed_without_exported_defect_set':True if unified else None,
        'histogram_definition':'For faceSets, affected cells are the union of owner/neighbour of selected faces. Each face/role counts unique affected cells incident to that boundary; cells may count in multiple face/role bins.',
        'distances_computed':False,'VTK_used_as_geometry':False,'mesh_or_CAD_modified':False,'CFD_executed':False,
        'manufacturing_authorized':False,'inputs_unchanged':all(sha(p)==h for p,h in paths.items()),
        'elapsed_seconds':time.monotonic()-start}
    if not result['inputs_unchanged']:raise ValueError('inputs_changed')
    if args.output.exists():raise FileExistsError(args.output)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');args.output.chmod(0o600)
    print(json.dumps({'status':result['status'],'report_sha256':sha(args.output),'elapsed_seconds':result['elapsed_seconds']}))
    return 0


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('case','msh','mesh-report','manifest','localization','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--unified-native-only',action='store_true',help='Exact new fab mesh and native-label receipt, not relabeled historical sets')
    resource.setrlimit(resource.RLIMIT_CPU,(120,125))
    raise SystemExit(run(p.parse_args()))
