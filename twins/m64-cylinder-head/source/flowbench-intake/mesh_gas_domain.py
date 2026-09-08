#!/usr/bin/env python3
"""Native intake-gas pilot mesh, with named boundaries and MSH2.2 checks.

No source scaling, healing, defeaturing or implicit closure is performed.
An accepted geometric candidate is not a converged CFD or manufacturing release.
"""
import argparse
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path
import resource
import sys
import time

SOURCE = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('native_mesh_checks', SOURCE/'mesh_native_ported_head.py')
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)
_PROFILE_SPEC=importlib.util.spec_from_file_location('mesh_native_profiles',Path(__file__).with_name('native_gas_profiles.py'))
profiles=importlib.util.module_from_spec(_PROFILE_SPEC);_PROFILE_SPEC.loader.exec_module(profiles)
PATCH_IDS = {'inlet': 1, 'receiver_outlet': 2, 'walls': 3}
VOLUME_ID = 100
REQUIRED_DOMAIN_GATES = ('single_solid','brep_valid','bop_no_faults',
                         'step_roundtrip_valid','boundary_assignment_complete',
                         'positive_intake_curtain','guide_extensions_communicate')
WALL_ROLES = {'walls_port','walls_chamber','walls_seat','walls_valve','walls_guide',
              'walls_receiver','fixture_stem_seals'}
C0_DIAGNOSTIC_GATES = {'bop_no_faults','positive_intake_curtain'}
GAS05_NATIVE_SHA = '3f20f4c56a3f4bfd5c7f580302dfa08e160ebb13abc3c5217a98312cc48653f3'
GAS05_FACE38_SHA = '9f7dcd51e4548a3222e961c16c0c5586f1725d84be52ee350b37090668753b5b'
GAS05_GUIDE_STEM_FACES = {
    55: ('walls_guide','f4b546496c1b4a040c561ea46685469ec7e9feb4ab3c5dbe9efbeba58b81d465'),
    56: ('walls_guide','d3bfc62403f1bbf60bb1e71dbdda09a48e0fbf4aed8dcbbeb62a480e63b074e0'),
    57: ('walls_guide','c8dc168593fdc85c1cf52b425861ea1505d5a000dfad054f7ab8d8b7959845df'),
    58: ('walls_guide','6312431d0d6bc19ac6a13b9197de9a2c2ff01741c0b065062f3c355afdcf1e82'),
    61: ('walls_valve','3a4754f6312c4ca4b78fe14ba4127cbdb18bb8d6254d8e07a8e8dd0b16e2ba97'),
    62: ('walls_valve','fe1820f9e706df3db439445746ede2b9c5888f61dd019c2bb489ff01129c9ffc'),
    63: ('walls_valve','5134bae58c7ae348813da1ea39c02e2e639b9f266828067d616fd40569b4c646'),
    64: ('walls_valve','fc19b8b3258fb45cf7122f4d839a427b46c93c35e2be1b6de46c4570858ec159'),
}
GAS05_GUIDE_STEM_SOURCES = {
    55:'intake_1_guide_face_4',57:'intake_1_guide_face_4',
    56:'intake_2_guide_face_4',58:'intake_2_guide_face_4',
    61:'intake_1_valve_face_6',63:'intake_1_valve_face_6',
    62:'intake_2_valve_face_6',64:'intake_2_valve_face_6',
}
GUIDE_FRAME_RECEIPT_SHA = '5935ab8da21709637143388cf4932d1f5a09def72b7c550d778a4114dbe11b51'
GUIDE_CHORD_SOURCE_SHA = '32626cc8def4a6e32693395815788af11a554bb8d768295671c45c2800eece14'
# The producer pin above remains historical. Runtime and new receipt pins are distinct.
GUIDE_CHORD_RUNTIME_SOURCE_SHA = 'f91780b69b59964c167558a41d1c3cbb2d0addaf282f711f13c4499719ec5db8'
SEGMENTED_GUIDE_FRAME_RECEIPT_SHA = 'c4ec27ae21efb5f575aa7d6dd9730ad3b27ae2789fc30698d5e8c0d2b5177900'


class SurfaceOnlyComplete(Exception):
    """Internal stop after persistence, while still running final provenance checks."""


def volume_algorithm_options(algorithm, build_options):
    """One explicit volume-only comparison; no change to boundary sizing or acceptance."""
    if type(algorithm) is not int or algorithm not in (1,10):
        raise ValueError('volume_comparison_allows_only_Delaunay1_or_HXT10')
    if algorithm==10 and 'hxt' not in build_options.lower().split():
        raise ValueError('HXT_not_available_in_this_Gmsh_build')
    return {'Mesh.Algorithm3D':algorithm}


def face38_algorithm_assignment(manifest, binding, algorithm):
    """The local experiment is valid only on this exact native face, never a reused tag."""
    if algorithm is None:return None
    if algorithm not in (1,5):raise ValueError('face38_experiment_allows_only_MeshAdapt1_or_Delaunay5')
    faces=[face for face in manifest['boundary_faces'] if face['id']==38]
    domain_sha=manifest['exports']['domain_brep']['sha256']
    expected_sha=(profiles.segmented_face_sha(manifest,38)
                  if domain_sha==profiles.SEGMENTED_DOMAIN_SHA else GAS05_FACE38_SHA)
    if (domain_sha not in (GAS05_NATIVE_SHA,profiles.SEGMENTED_DOMAIN_SHA) or len(faces)!=1 or
            faces[0]['sha256']!=expected_sha or faces[0]['role']!='walls_port' or
            binding.get('descriptor_bijection_verified') is not True):
        raise ValueError('exact_native_gas05_face38_and_bijection_required')
    matches=[row for row in binding['matches_private'] if row['source_face_index']==38]
    if len(matches)!=1:raise ValueError('unique_native_face38_binding_required')
    return {'source_face_id':38,'native_BRep_sha256':domain_sha,'native_face_sha256':expected_sha,
            'gmsh_face_tag':matches[0]['gmsh_face_tag'],'surface_algorithm':algorithm,
            'other_surfaces_default_algorithm':6,'boundary_geometry_modified':False}


def face38_size_assignment(manifest, binding, size):
    """One resolution experiment, not a dimensional or CAD tolerance change."""
    if size is None:return None
    if isinstance(size,bool) or not math.isfinite(size) or not .005<=size<=.2:
        raise ValueError('local_size_must_be_finite_within_unchanged_minimum_and_0p2')
    # Reuse only the exact face binding, without applying its algorithm value.
    target=face38_algorithm_assignment(manifest,binding,1)
    return {key:target[key] for key in ('source_face_id','native_BRep_sha256','native_face_sha256','gmsh_face_tag')} | {
        'local_maximum_size_scan_units':size,'include_boundary':True,
        'CAD_geometry_modified':False,'global_minimum_size_unchanged':.005,
        'authority':'numerical_chord_resolution_experiment_not_physical_scan_precision',
        'neighboring_shared_edge_meshes_may_change':True}


def guide_size_assignment(manifest, binding, size, frames=None):
    """Cover every classified cylindrical fragment of both guide/stem clearances."""
    if size is None:return None
    if isinstance(size,bool) or not math.isfinite(size) or not .005<=size<=.2:
        raise ValueError('guide_size_must_be_finite_between_0p005_and_0p2')
    domain_sha=manifest['exports']['domain_brep']['sha256']
    expected_faces=GAS05_GUIDE_STEM_FACES
    if domain_sha==profiles.SEGMENTED_DOMAIN_SHA:
        profiles.registered_segmented_manifest(manifest,for_meshing=False)
        expected_faces={i:(r,profiles.SEGMENTED_FACE_SHAS[i]) for i,(r,_) in GAS05_GUIDE_STEM_FACES.items()}
    if (domain_sha not in (GAS05_NATIVE_SHA,profiles.SEGMENTED_DOMAIN_SHA) or
            binding.get('descriptor_bijection_verified') is not True):
        raise ValueError('exact_native_gas05_and_bijection_required')
    expected_sources=set(GAS05_GUIDE_STEM_SOURCES.values())
    identified=[r['id'] for r in manifest['boundary_faces'] if any(
        s.get('source') in expected_sources for s in r.get('source_match',[]))]
    if frames is None:raise ValueError('reviewed_native_inventory_required_for_guide_sizing')
    inventoried={r['face_id']:r for r in frames['native_inventory']['cylinders_private']
                 if expected_sources.intersection(r['source_names'])}
    if len(identified)!=len(inventoried) or set(identified)!=set(inventoried):
        raise ValueError('complete_source_fragments_including_nonannular_stems_required')
    selected=set(frames['coverage']['selected_face_ids'])
    excluded={r['face_id'] for r in frames['coverage']['excluded_cylinders']}
    if selected!=set(GAS05_GUIDE_STEM_FACES) or set(identified)-selected-excluded:
        raise ValueError('complete_eight_fragment_guide_stem_inventory_required')
    for row in manifest['boundary_faces']:
        if row['id'] in inventoried:
            native=inventoried[row['id']]
            if row['sha256']!=native['face_sha256'] or row['role']!=native['role']:
                raise ValueError('classified_fragment_differs_from_reviewed_native_inventory')
    faces=[]
    for face_id,(role,expected_sha) in expected_faces.items():
        source=[r for r in manifest['boundary_faces'] if r['id']==face_id]
        match=[r for r in binding['matches_private'] if r['source_face_index']==face_id]
        if (len(source)!=1 or source[0]['role']!=role or source[0]['sha256']!=expected_sha or
                source[0].get('surface_type')!='GeomAbs_Cylinder' or len(match)!=1 or
                GAS05_GUIDE_STEM_SOURCES[face_id] not in {r.get('source') for r in source[0].get('source_match',[])}):
            raise ValueError('exact_unique_guide_stem_cylinder_binding_required')
        faces.append({'source_face_id':face_id,'native_face_sha256':expected_sha,
                      'role':role,'source_component_surface':GAS05_GUIDE_STEM_SOURCES[face_id],
                      'gmsh_face_tag':match[0]['gmsh_face_tag']})
    return {'faces':faces,'local_target_size_scan_units':size,'include_boundary':True,
            'complete_classified_eight_fragment_inventory_verified':True,
            'source_fragments_examined':sorted(identified),
            'native_axially_excluded_stem_fragments':sorted(set(identified)-selected),
            'CAD_geometry_modified':False,'global_minimum_size_unchanged':.005,
            'target_size_is_not_a_guaranteed_actual_chord_bound':True,
            'actual_chords_and_facets_must_be_checked_before_3D':True}


def validated_guide_frames(receipt, receipt_sha, manifest=None):
    """Reuse reviewed native frames, never the earlier surface's acceptance result."""
    if manifest and manifest.get('exports',{}).get('domain_brep',{}).get('sha256')==profiles.SEGMENTED_DOMAIN_SHA:
        profiles.registered_segmented_manifest(manifest)
        if (not SEGMENTED_GUIDE_FRAME_RECEIPT_SHA or receipt_sha!=SEGMENTED_GUIDE_FRAME_RECEIPT_SHA or
                receipt.get('schema')!='m64-native-guide-frame-inventory/v1' or
                receipt.get('mode')!='native_inventory_only' or receipt.get('all_inputs_unchanged') is not True or
                receipt.get('inputs_sha256',{}).get('domain')!=profiles.SEGMENTED_DOMAIN_SHA or
                receipt['inputs_sha256'].get('boundary_report')!=profiles.SEGMENTED_MANIFEST_SHA or
                receipt['inputs_sha256'].get('source')!=GUIDE_CHORD_RUNTIME_SOURCE_SHA or
                receipt['inputs_sha256'].get('profile_source')!=checks.sha256(profiles.__file__) or
                receipt.get('CAD_modified') is not False or receipt.get('mesh_accepted') is not False or
                receipt.get('CFD_executed') is not False or receipt.get('manufacturing_authorized') is not False or
                'whole_facet_chord_gate' not in receipt.get('result',{}) or
                receipt.get('result',{}).get('whole_facet_chord_gate') is not None):
            raise ValueError('exact_new_native_inventory_receipt_required_not_historical_mesh_review')
        frames=receipt['result']['frames_private']
        profiles.guide_face_hashes(frames.get('domain_sha256'),frames)
        if (frames.get('schema')!='m64-native-guide-cylinder-frames/v2' or
                frames.get('coverage',{}).get('selected_face_ids')!=sorted(GAS05_GUIDE_STEM_FACES)):
            raise ValueError('complete_segmented_eight_fragment_frames_required')
        return frames
    if (receipt_sha!=GUIDE_FRAME_RECEIPT_SHA or
            receipt.get('schema')!='m64-persisted-guide-chord-diagnostic/v2' or
            receipt.get('mode')!='native_cylinder_diagnostics' or
            receipt.get('all_inputs_unchanged') is not True or
            receipt['inputs_sha256']['domain']!=GAS05_NATIVE_SHA or
            receipt['inputs_sha256']['source']!=GUIDE_CHORD_SOURCE_SHA):
        raise ValueError('exact_reviewed_native_guide_frame_receipt_required')
    frames=receipt['result']['frames_private']
    if (frames.get('schema')!='m64-native-guide-cylinder-frames/v2' or
            frames.get('domain_sha256')!=GAS05_NATIVE_SHA or
            frames.get('coverage',{}).get('selected_face_ids')!=sorted(GAS05_GUIDE_STEM_FACES)):
        raise ValueError('complete_eight_fragment_native_frames_required')
    return frames


def current_guide_chord_gate(gmsh, assignment, frames):
    """Inspect the actual in-memory boundary immediately before/after generate(3)."""
    import audit_guide_chords
    if checks.sha256(audit_guide_chords.__file__)!=GUIDE_CHORD_RUNTIME_SOURCE_SHA:
        raise ValueError('reviewed_guide_chord_auditor_source_required')
    tags,xyz,_=gmsh.model.mesh.getNodes()
    points={int(tag):tuple(map(float,xyz[3*i:3*i+3])) for i,tag in enumerate(tags)}
    grouped={}
    for row in assignment['faces']:
        kinds,_,flat=gmsh.model.mesh.getElements(2,row['gmsh_face_tag'])
        if list(map(int,kinds))!=[2]:raise ValueError('linear_guide_boundary_triangles_required')
        grouped[row['source_face_id']]=[tuple(map(int,flat[0][i:i+3])) for i in range(0,len(flat[0]),3)]
    return audit_guide_chords.mesh_chord_gate(points,grouped,frames)


def validated_boundary_contract(manifest, c0_diagnostic=False, segmented_native_only=False):
    """Preserve failed C0 gates; a reviewed exception permits a diagnostic only."""
    if manifest.get('schema') != 'm64-intake-gas-domain/v1':
        raise ValueError('native_intake_gas_domain_schema_required')
    if c0_diagnostic and segmented_native_only:raise ValueError('historical_C0_and_segmented_profiles_are_exclusive')
    if segmented_native_only:profiles.registered_segmented_manifest(manifest)
    required=(set(profiles.NATIVE_ONLY_GATES) if segmented_native_only else
              set(REQUIRED_DOMAIN_GATES)-(C0_DIAGNOSTIC_GATES if c0_diagnostic else set()))
    if any(manifest.get('gates',{}).get(key) is not True for key in required):
        raise ValueError('native_gas_domain_gate_not_accepted')
    rows=manifest.get('boundary_faces',[])
    if not rows:raise ValueError('native_boundary_faces_required')
    groups={name:[] for name in PATCH_IDS};ids=[];descriptors=[]
    for row in rows:
        face_id=row['id'];role=row['role'];center=row['center'];area=row['area']
        if role not in WALL_ROLES | {'inlet','receiver_outlet'}:
            raise ValueError('unknown_or_unaccepted_boundary_role')
        if (not isinstance(face_id,(int,str)) or isinstance(face_id,bool) or
                len(center)!=3 or not all(math.isfinite(x) for x in center) or
                not math.isfinite(area) or area<=0):
            raise ValueError('invalid_native_face_descriptor')
        patch=role if role in PATCH_IDS else 'walls'
        groups[patch].append(face_id);ids.append(face_id)
        descriptors.append({'tag':face_id,'area':area,'centre':center})
    partition=boundary_partition(ids,groups)
    return {'groups':groups,'descriptors':descriptors,'partition':partition,
            'original_roles':{row['id']:row['role'] for row in rows}}


def boundary_partition(face_ids, groups):
    """Every CAD boundary face belongs to exactly one nonempty pilot patch."""
    if set(groups) != set(PATCH_IDS):
        raise ValueError('exactly_inlet_receiver_outlet_walls_required')
    faces=list(face_ids)
    if not faces or len(set(faces)) != len(faces):
        raise ValueError('unique_nonempty_CAD_faces_required')
    owners=Counter(face for members in groups.values() for face in members)
    if any(not members for members in groups.values()):
        raise ValueError('empty_boundary_patch')
    if set(owners) != set(faces) or any(count != 1 for count in owners.values()):
        raise ValueError('boundary_partition_missing_duplicate_or_unknown_face')
    return {'complete': True, 'face_counts': {name: len(groups[name]) for name in PATCH_IDS}}


def boundary_orientation(points, tetrahedra, grouped_triangles):
    """Check each stored boundary triangle against its sole adjacent tetrahedron."""
    owners={}
    for tetra in tetrahedra:
        for opposite in range(4):
            key=tuple(sorted(tetra[j] for j in range(4) if j!=opposite))
            owners.setdefault(key,[]).append(tetra[opposite])
    results={}
    for name,triangles in grouped_triangles.items():
        outward=inward=zero=invalid=0;areas=[];vectors=[[],[],[]]
        for triangle in triangles:
            adjacent=owners.get(tuple(sorted(triangle)),[])
            if len(adjacent)!=1:
                invalid+=1;continue
            a,b,c=(points[tag] for tag in triangle);d=points[adjacent[0]]
            u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
            normal=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            side=math.fsum(normal[k]*(d[k]-a[k]) for k in range(3))
            outward+=side<0;inward+=side>0;zero+=side==0
            areas.append(math.sqrt(math.fsum(x*x for x in normal))/2)
            for k in range(3):vectors[k].append(normal[k]/2)
        results[name]={'triangles':len(triangles),'outward':outward,'inward':inward,
                       'zero_orientation':zero,'invalid_adjacency':invalid,
                       'area_scan_units_squared':math.fsum(areas),
                       'oriented_area_vector_scan_units_squared':[math.fsum(v) for v in vectors]}
    return {'patches':results,'all_outward':all(r['triangles']>0 and not(r['inward'] or r['zero_orientation'] or r['invalid_adjacency']) for r in results.values())}


def parse_msh22(text, surface_only=False):
    """Independent bounded ASCII parser for only linear tetra/triangle pilot files."""
    lines=iter(text.splitlines());sections={}
    for line in lines:
        if not line:continue
        if not line.startswith('$') or line.startswith('$End'):
            raise ValueError('unexpected_MSH_line')
        name=line[1:]
        if name in sections:raise ValueError('duplicate_MSH_section')
        rows=[]
        for item in lines:
            if item=='$End'+name:break
            rows.append(item)
        else:raise ValueError('unterminated_MSH_section')
        sections[name]=rows
    if sections.get('MeshFormat') != ['2.2 0 8']:
        raise ValueError('MSH_2p2_ASCII_double_required')
    def counted(name):
        rows=sections[name]
        if int(rows[0]) != len(rows)-1:raise ValueError('MSH_section_count_mismatch')
        return rows[1:]
    physical={}
    for row in counted('PhysicalNames'):
        dim,tag,name=row.split(maxsplit=2)
        key=(int(dim),int(tag))
        if key in physical:raise ValueError('duplicate_physical_name')
        physical[key]=json.loads(name)
    expected={(2,tag):name for name,tag in PATCH_IDS.items()};with_volume={**expected,(3,VOLUME_ID):'air'}
    if physical not in ([expected,with_volume] if surface_only else [with_volume]):
        raise ValueError('physical_names_not_preserved')
    points={}
    for row in counted('Nodes'):
        values=row.split();tag=int(values[0]);xyz=tuple(map(float,values[1:]))
        if tag<=0 or tag in points or len(xyz)!=3 or not all(math.isfinite(x) for x in xyz):
            raise ValueError('invalid_MSH_node')
        points[tag]=xyz
    tetrahedra=[];groups={name:[] for name in PATCH_IDS};ids=set()
    for row in counted('Elements'):
        values=list(map(int,row.split()));tag,kind,count=values[:3]
        if tag<=0 or tag in ids or count<2 or len(values)<3+count:
            raise ValueError('invalid_MSH_element')
        ids.add(tag);physical_tag=values[3];nodes=tuple(values[3+count:])
        if any(node not in points for node in nodes):raise ValueError('unknown_MSH_node')
        if kind==4 and len(nodes)==4 and physical_tag==VOLUME_ID:
            tetrahedra.append(nodes)
        elif kind==2 and len(nodes)==3 and (2,physical_tag) in physical:
            groups[physical[(2,physical_tag)]].append(nodes)
        else:raise ValueError('unclassified_or_unsupported_MSH_element')
    if (bool(tetrahedra)==surface_only) or any(not rows for rows in groups.values()):
        raise ValueError('empty_MSH_volume_or_patch')
    return {'points':points,'tetrahedra':tetrahedra,'grouped_triangles':groups,
            'physical_names':physical}


def mesh_bounds(points):
    if not points:raise ValueError('nonempty_mesh_required')
    return [min(p[k] for p in points.values()) for k in range(3)]+[max(p[k] for p in points.values()) for k in range(3)]


def surface_topology(triangles):
    edges=Counter();directions=Counter()
    for triangle in triangles:
        if len(set(triangle))!=3:raise ValueError('three_distinct_surface_nodes_required')
        for a,b in zip(triangle,(*triangle[1:],triangle[0])):
            edge=tuple(sorted((a,b)));edges[edge]+=1;directions[edge]+=1 if a<b else -1
    duplicates=sum(count-1 for count in Counter(tuple(sorted(t)) for t in triangles).values())
    return {'triangles':len(triangles),'unique_edges':len(edges),'edges_with_one_incident_triangle':sum(v==1 for v in edges.values()),
            'edges_with_more_than_two_triangles':sum(v>2 for v in edges.values()),
            'incoherent_two_triangle_edge_orientations':sum(edges[e]==2 and v!=0 for e,v in directions.items()),
            'duplicate_triangles':duplicates,'closed_two_manifold_edge_incidence':bool(edges) and all(v==2 for v in edges.values()) and duplicates==0,
            'self_intersection_and_CAD_conformity_not_proven':True}


def persist_surface(gmsh, output, groups, binding):
    """Persist every surface triangle before any attempted volume generation."""
    tags,xyz,_=gmsh.model.mesh.getNodes()
    points={int(tag):tuple(map(float,xyz[3*i:3*i+3])) for i,tag in enumerate(tags)}
    source_for={row['gmsh_face_tag']:row['source_face_index'] for row in binding['matches_private']}
    faces=[];grouped={name:[] for name in groups}
    for name,face_tags in groups.items():
        for face in face_tags:
            kinds,element_tags,flat=gmsh.model.mesh.getElements(2,face)
            if list(map(int,kinds))!=[2]:raise ValueError('persisted_surface_requires_linear_triangles_on_every_face')
            triangles=[tuple(map(int,flat[0][i:i+3])) for i in range(0,len(flat[0]),3)]
            grouped[name].extend(triangles)
            faces.append({'source_face_id':source_for[face],'gmsh_face_tag':face,'patch':name,
                          'triangle_tags':list(map(int,element_tags[0])),'triangles':triangles})
    snapshot=output/'surface-connectivity-private.json'
    checks.save(snapshot,{'scope':'surface_only_before_any_3D_generation','nodes_private':points,'faces_private':faces})
    msh=output/'intake-gas-surface-only.msh';gmsh.write(str(msh));msh.chmod(0o600)
    parsed=parse_msh22(msh.read_text(),surface_only=True)
    same_nodes=parsed['points'].keys()==points.keys()
    delta=max((math.dist(p,parsed['points'][tag]) for tag,p in points.items()),default=0.) if same_nodes else None
    same_triangles=all(sorted(parsed['grouped_triangles'][name])==sorted(grouped[name]) for name in groups)
    result={'MSH_file':msh.name,'MSH_sha256':checks.sha256(msh),'connectivity_file':snapshot.name,
            'connectivity_sha256':checks.sha256(snapshot),'nodes':len(points),'CAD_faces':len(faces),
            'surface_topology':surface_topology(sum(grouped.values(),[])),'tetrahedra_in_saved_MSH':len(parsed['tetrahedra']),
            'node_tags_preserved':same_nodes,'oriented_triangles_and_patch_labels_preserved':same_triangles,
            'maximum_coordinate_delta_scan_units':delta,'volume_mesh_generated':False}
    if not same_nodes or not same_triangles or delta is None or delta>1e-10:
        raise ValueError('surface_MSH_export_roundtrip_changed_connectivity_or_coordinates')
    return result


def validated_c0_advisory(manifest, manifest_sha, receipt):
    """Bind the one-shot diagnostic advisory without converting it to BOP success."""
    if (receipt.get('schema')!='m64-native-gas-domain-advisories/v1' or
            receipt.get('allow_diagnostic_meshing') is not True or
            receipt.get('inputs_sha256',{}).get('domain')!=manifest['exports']['domain_brep']['sha256'] or
            receipt.get('inputs_sha256',{}).get('classified_report')!=manifest_sha):
        raise ValueError('exact_native_C0_diagnostic_advisory_required')
    if (receipt.get('geometry_modified') is not False or receipt.get('tolerance_modified') is not False or
            receipt.get('all_inputs_unchanged') is not True or
            receipt.get('classified_boundary_assignment_complete') is not True or
            receipt.get('native_check',{}).get('BRep_valid_exact_method') is not True):
        raise ValueError('independent_native_geometry_and_provenance_checks_required')
    faces={face['id']:face for face in manifest['boundary_faces']}
    ownership=receipt.get('ambiguous_face_ownership',[])
    if len(ownership)!=4 or len({row.get('face_id') for row in ownership})!=4:
        raise ValueError('four_independent_seat_ownership_checks_required')
    for row in ownership:
        face=faces.get(row.get('face_id'),{})
        if (row.get('ownership_evidence_pass') is not True or
                face.get('sha256')!=row.get('source_face_sha256') or
                face.get('role')!='walls_seat' or row.get('recommended_physical_role')!='walls_seat'):
            raise ValueError('independent_seat_ownership_or_face_hash_mismatch')
    if {key for key,value in manifest['gates'].items() if value is not True}!=C0_DIAGNOSTIC_GATES:
        raise ValueError('only_declared_C0_diagnostic_gates_may_be_false')
    for key in ('native_BOP','native_roundtrip_BOP'):
        bop=manifest[key]
        if (bop.get('has_errors') is not False or bop.get('has_warnings') is not False or
                bop.get('has_faulty') is not True or bop.get('faults')!=['BOPAlgo_GeomAbs_C0']):
            raise ValueError('native_C0_must_be_the_only_BOP_advisory')
    necks=manifest.get('local_intake_necks',[])
    if len(necks)!=2 or len({row.get('name') for row in necks})!=2:
        raise ValueError('two_distinct_intake_neck_geometry_records_required')
    for neck in necks:
        if (neck.get('BRep_valid') is not True or neck.get('solid_count')!=1 or
                neck.get('trunk_excluded_by_axial_bound') is not True or neck.get('other_seat_overlap_volume')!=0 or
                not all(math.isfinite(neck.get(key,float('nan'))) and neck[key]>0 for key in ('throat_side_area','chamber_side_area')) or
                neck.get('BOP',{}).get('has_errors') is not False or neck['BOP'].get('has_warnings') is not False or
                any(fault!='BOPAlgo_GeomAbs_C0' for fault in neck['BOP'].get('faults',[]))):
            raise ValueError('positive_local_neck_geometry_with_no_nonC0_BOP_fault_required')
    knots=[]
    for entity in receipt.get('C0_entities',[]):
        for knot in entity.get('curve',{}).get('C0_internal_knots',[]):
            position=knot.get('position_private',[])
            if (len(position)!=3 or not all(math.isfinite(x) for x in position) or
                    knot.get('position_jump_native_numeric')!=0 or
                    not math.isfinite(knot.get('parameter',float('nan'))) or
                    not math.isfinite(knot.get('tangent_angle_degrees',float('nan')))):
                raise ValueError('finite_position_continuous_C0_checkpoint_required')
            knots.append({'edge_id':entity['edge_id'],'parameter':knot['parameter'],
                          'position_private':position,'tangent_angle_degrees':knot['tangent_angle_degrees']})
    if len(knots)!=3 or len({(knot['edge_id'],knot['parameter']) for knot in knots})!=3:
        raise ValueError('exactly_three_distinct_reviewed_C0_checkpoints_required')
    return {'scope':'one_native_meshing_attempt_diagnostic_only','source_gates_preserved':manifest['gates'],
            'C0_entities_private':receipt['C0_entities'],
            'failed_source_gates_not_promoted':sorted(C0_DIAGNOSTIC_GATES),'C0_checkpoints_private':knots}


def nearest_boundary_nodes(checkpoints, points, grouped_triangles):
    """Measure knot representation, with no invented distance acceptance threshold."""
    owners={}
    for patch,triangles in grouped_triangles.items():
        for triangle in triangles:
            for node in triangle:owners.setdefault(node,set()).add(patch)
    if not owners:raise ValueError('boundary_nodes_required_for_C0_diagnostic')
    rows=[]
    for checkpoint in checkpoints:
        target=checkpoint['position_private']
        node=min(owners,key=lambda tag:(math.dist(points[tag],target),tag))
        rows.append({**checkpoint,'nearest_boundary_node':node,'node_position_private':points[node],
                     'distance_scan_units':math.dist(points[node],target),'patches':sorted(owners[node])})
    return {'checkpoints_private':rows,'maximum_distance_scan_units':max(row['distance_scan_units'] for row in rows),
            'distance_is_diagnostic_not_C0_conformity_or_CFD_acceptance':True}


def import_volume_comparison(imported, adaptive_reference, same_integrator_reference=None):
    """Compare like integrators while retaining the separate adaptive estimate."""
    reference=adaptive_reference if same_integrator_reference is None else same_integrator_reference
    if not all(math.isfinite(value) and value>0 for value in (imported,adaptive_reference,reference)):
        raise ValueError('positive_finite_native_volume_estimates_required')
    relative=abs(imported/reference-1)
    return {'imported_volume_scan_units_cubed':imported,
            'comparison_reference_volume_scan_units_cubed':reference,
            'adaptive_volume_scan_units_cubed':adaptive_reference,
            'relative_volume_difference':relative,
            'relative_difference_from_adaptive_volume':abs(imported/adaptive_reference-1),
            'nonadaptive_reference_used':same_integrator_reference is not None,
            'relative_tolerance_unchanged':1e-6,'within_unchanged_tolerance':relative<=1e-6}


def validated_volume_reference(manifest, receipt):
    if (receipt.get('schema')!='m64-native-volume-quadrature-reference/v1' or
            receipt.get('status')!='matched_nonadaptive_reference' or
            receipt.get('domain_sha256')!=manifest['exports']['domain_brep']['sha256'] or
            receipt.get('input_unchanged') is not True or receipt.get('geometry_modified') is not False or
            receipt.get('tolerance_modified') is not False):
        raise ValueError('exact_native_unmodified_volume_quadrature_reference_required')
    adaptive=receipt.get('adaptive_volume',float('nan'))
    nonadaptive=receipt.get('nonadaptive_volume',float('nan'))
    if (not all(math.isfinite(v) and v>0 for v in (adaptive,nonadaptive)) or
            abs(adaptive/manifest['properties']['volume']-1)>1e-12):
        raise ValueError('volume_quadrature_reference_must_reproduce_source_adaptive_estimate')
    return receipt


def validated_input(manifest_path, advisory_path=None, segmented_native_only=False):
    manifest=json.loads(manifest_path.read_text())
    if segmented_native_only:
        if advisory_path:raise ValueError('segmented_native_profile_cannot_reuse_historical_C0_advisory')
        profiles.registered_segmented_manifest(manifest,checks.sha256(manifest_path))
    advisory=validated_c0_advisory(manifest,checks.sha256(manifest_path),json.loads(advisory_path.read_text())) if advisory_path else None
    contract=validated_boundary_contract(manifest,c0_diagnostic=advisory is not None,segmented_native_only=segmented_native_only)
    required=set(manifest['gates'])-({'step_roundtrip_valid'} if segmented_native_only else C0_DIAGNOSTIC_GATES if advisory else set())
    if (manifest.get('inputs_unchanged') is not True or
            manifest.get('gates',{}).get('native_roundtrip_valid') is not True or
            any(manifest['gates'][key] is not True for key in required)):
        raise ValueError('all_native_domain_gates_and_provenance_required')
    export=manifest['exports']['domain_brep']
    paths={manifest_path:checks.sha256(manifest_path)}
    if advisory_path:paths[advisory_path]=checks.sha256(advisory_path)
    root=manifest_path.parent.resolve()
    for entry in [export,*manifest['boundary_faces']]:
        path=(root/entry['file']).resolve()
        if not path.is_relative_to(root) or path.suffix!='.brep':
            raise ValueError('native_inputs_must_stay_in_declared_private_package')
        if checks.sha256(path)!=entry['sha256']:raise ValueError('native_input_hash_mismatch')
        paths[path]=entry['sha256']
    native=(root/export['file']).resolve()
    return manifest,contract,native,paths,advisory


def run(args):
    import gmsh
    segmented=getattr(args,'segmented_native_only',False)
    manifest,contract,native,paths,advisory=validated_input(args.manifest,args.diagnostic_c0_advisory,segmented_native_only=segmented)
    paths[Path(profiles.__file__)]=checks.sha256(profiles.__file__)
    volume_reference=validated_volume_reference(manifest,json.loads(args.volume_quadrature_reference.read_text())) if args.volume_quadrature_reference else None
    if volume_reference:paths[args.volume_quadrature_reference]=checks.sha256(args.volume_quadrature_reference)
    if args.output.exists() or args.output.is_symlink():raise FileExistsError(args.output)
    args.output.mkdir(parents=True,mode=0o700)
    source_sha=checks.sha256(__file__);dependency_sha=checks.sha256(checks.__file__)
    started=time.monotonic()
    report={'schema':'m64-intake-gas-pilot-mesh/v1','status':'incomplete','stage':'initializing',
            'source_sha256':source_sha,'dependency_sha256':dependency_sha,
            'gas_domain_report_sha256':checks.sha256(args.manifest),
            'native_BRep_sha256':checks.sha256(native),'gmsh_version':gmsh.__version__,
            'native_profile':profiles.registered_segmented_manifest(manifest) if segmented else {'name':'historical_gas05'},
            'native_profile_source_sha256':checks.sha256(profiles.__file__),
            'native_builder_status':manifest.get('status'),
            'native_builder_gates':manifest['gates'],
            'native_BOP':manifest.get('native_BOP'),'STEP_BOP_qualified':manifest.get('STEP_BOP_qualified'),
            'diagnostic_C0_advisory':advisory,
            'diagnostic_C0_advisory_sha256':checks.sha256(args.diagnostic_c0_advisory) if advisory else None,
            'volume_quadrature_reference':volume_reference,
            'volume_quadrature_reference_sha256':checks.sha256(args.volume_quadrature_reference) if volume_reference else None,
            'builder_independent_closure_audit_accepted':manifest.get('independent_closure_audit_accepted'),
            'meshing_does_not_change_builder_review_status':True,
            'coordinate_units':'unchanged_scan_units_under_unverified_mm_hypothesis',
            'coordinate_scale_applied':1.,'CAD_geometry_modified':False,'STEP_used':False,
            'guide_annular_passages_removed_or_capped_implicitly':False,
            'guide_extension_contract':manifest.get('guide_extensions',[]),
            'fixture_stem_seal_authority':manifest.get('fixture_stem_seal_authority'),
            'CFD_executed':False,'CFD_convergence_established':False,'manufacturing_authorized':False,
            'stop_after_surface_requested':args.stop_after_surface,'volume_generation_attempted':False,
            'physical_groups':{'surface':PATCH_IDS,'volume':{'air':VOLUME_ID}},
            'subroles_private':contract['original_roles'],
            'SICN_0p1_is_diagnostic_not_a_CFD_acceptance_threshold':True,
            'OpenFOAM_cell_determinant_is_not_Gmsh_tetra_Jacobian':True}
    def checkpoint(stage):
        report['stage']=stage;report['elapsed_seconds']=time.monotonic()-started
        checks.save(args.output/'mesh-report.json',report)
    checkpoint('initializing')
    gmsh.initialize(['intake-gas-pilot','-nopopup'],readConfigFiles=False,run=False)
    gmsh.logger.start()
    try:
        options={'General.Terminal':0,'General.NumThreads':4,'Mesh.MaxNumThreads1D':4,
                 'Mesh.MaxNumThreads2D':4,'Mesh.MaxNumThreads3D':4,
                 'Geometry.OCCFixDegenerated':0,'Geometry.OCCFixSmallEdges':0,
                 'Geometry.OCCFixSmallFaces':0,'Geometry.OCCSewFaces':0,
                 'Geometry.OCCMakeSolids':0,'Geometry.OCCAutoFix':0,'Geometry.OCCScaling':1,
                 'Mesh.ElementOrder':1,'Mesh.RecombineAll':0,'Mesh.Algorithm':6,'Mesh.Algorithm3D':1,
                 'Mesh.MeshSizeMin':.005,'Mesh.MeshSizeMax':4.,'Mesh.MeshSizeFromCurvature':32,
                 'Mesh.MeshSizeFromPoints':0,'Mesh.Optimize':1,'Mesh.OptimizeNetgen':0,'Mesh.RandomSeed':1,
                 'Mesh.MshFileVersion':2.2,'Mesh.Binary':0,'Mesh.SaveAll':0}
        for key,value in options.items():gmsh.option.setNumber(key,value)
        report['explicit_options']=options;report['build_options']=gmsh.option.getString('General.BuildOptions')
        gmsh.model.add('intake_gas_NOT_CFD_VALIDATED')
        gmsh.model.occ.importShapes(str(native),highestDimOnly=False);gmsh.model.occ.synchronize()
        volumes=gmsh.model.getEntities(3);surfaces=gmsh.model.getEntities(2)
        volume=math.fsum(gmsh.model.occ.getMass(3,tag) for _,tag in volumes)
        descriptors=[{'tag':tag,'area':gmsh.model.occ.getMass(2,tag),
                      'centre':list(gmsh.model.occ.getCenterOfMass(2,tag))} for _,tag in surfaces]
        area=math.fsum(face['area'] for face in descriptors)
        binding=checks.match_faces(contract['descriptors'],descriptors)
        original_volume=manifest['properties']['volume'];original_area=manifest['properties']['area']
        volume_comparison=import_volume_comparison(volume,original_volume,volume_reference['nonadaptive_volume'] if volume_reference else None)
        report['import']={'regions':len(volumes),'faces':len(surfaces),'volume_scan_units_cubed':volume,
                          'area_scan_units_squared':area,'bbox_scan_units_private':list(gmsh.model.getBoundingBox(-1,-1)),
                          'relative_volume_difference':volume_comparison['relative_volume_difference'],
                          'volume_quadrature_comparison':volume_comparison,
                          'relative_area_difference':abs(area/original_area-1),'face_binding_private':binding}
        checkpoint('native_import_checked')
        if (len(volumes)!=1 or manifest['properties']['solids']!=1 or not binding['descriptor_bijection_verified'] or
                report['import']['relative_volume_difference']>1e-6 or report['import']['relative_area_difference']>1e-6):
            raise ValueError('native_import_conservation_or_bijection_failed')
        lookup={r['source_face_index']:r['gmsh_face_tag'] for r in binding['matches_private']}
        assignment=face38_algorithm_assignment(manifest,binding,args.face38_algorithm)
        report['local_surface_algorithm_assignment']=assignment
        if assignment:gmsh.model.mesh.setAlgorithm(2,assignment['gmsh_face_tag'],assignment['surface_algorithm'])
        sizing=face38_size_assignment(manifest,binding,args.face38_size)
        report['local_surface_size_assignment']=sizing
        background_fields=[]
        if sizing:
            constant=gmsh.model.mesh.field.add('MathEval')
            gmsh.model.mesh.field.setString(constant,'F',format(args.face38_size,'.17g'))
            restricted=gmsh.model.mesh.field.add('Restrict')
            gmsh.model.mesh.field.setNumber(restricted,'InField',constant)
            gmsh.model.mesh.field.setNumbers(restricted,'SurfacesList',[sizing['gmsh_face_tag']])
            gmsh.model.mesh.field.setNumber(restricted,'IncludeBoundary',1)
            background_fields.append(restricted)
            sizing['field_ids']={'MathEval':constant,'Restrict':restricted}
            sizing['MeshSizeExtendFromBoundary']=gmsh.option.getNumber('Mesh.MeshSizeExtendFromBoundary')
            sizing['boundary_entities_private']=gmsh.model.getBoundary([(2,sizing['gmsh_face_tag'])],oriented=False,recursive=False)
        guide_frames=None
        if args.guide_size is not None:
            if args.guide_chord_reference:
                reference_hash=checks.sha256(args.guide_chord_reference)
                guide_frames=validated_guide_frames(json.loads(args.guide_chord_reference.read_text()),reference_hash,manifest)
                paths[args.guide_chord_reference]=reference_hash
                paths[Path(__file__).with_name('audit_guide_chords.py')]=GUIDE_CHORD_RUNTIME_SOURCE_SHA
                report['guide_frame_reference_sha256']=reference_hash
            else:
                raise ValueError('native_guide_frames_required_for_actual_pre3D_chord_gate')
        guide_sizing=guide_size_assignment(manifest,binding,args.guide_size,guide_frames)
        report['guide_stem_size_assignment']=guide_sizing
        if guide_sizing:
            constant=gmsh.model.mesh.field.add('MathEval')
            gmsh.model.mesh.field.setString(constant,'F',format(args.guide_size,'.17g'))
            restricted=gmsh.model.mesh.field.add('Restrict')
            gmsh.model.mesh.field.setNumber(restricted,'InField',constant)
            gmsh.model.mesh.field.setNumbers(restricted,'SurfacesList',[r['gmsh_face_tag'] for r in guide_sizing['faces']])
            gmsh.model.mesh.field.setNumber(restricted,'IncludeBoundary',1)
            background_fields.append(restricted)
            guide_sizing['field_ids']={'MathEval':constant,'Restrict':restricted}
        if background_fields:
            minimum=gmsh.model.mesh.field.add('Min')
            gmsh.model.mesh.field.setNumbers(minimum,'FieldsList',background_fields)
            gmsh.model.mesh.field.setAsBackgroundMesh(minimum)
            report['background_Min_fields']=background_fields
        groups={name:[lookup[face] for face in ids] for name,ids in contract['groups'].items()}
        boundary_partition([tag for _,tag in surfaces],groups)
        for name,tags in groups.items():
            tag=gmsh.model.addPhysicalGroup(2,tags,PATCH_IDS[name]);gmsh.model.setPhysicalName(2,tag,name)
        tag=gmsh.model.addPhysicalGroup(3,[volumes[0][1]],VOLUME_ID);gmsh.model.setPhysicalName(3,tag,'air')
        report['boundary_entity_groups_private']=groups
        for dimension in (1,2,3):
            if dimension==3:
                volume_options=volume_algorithm_options(getattr(args,'volume_algorithm',1),report['build_options'])
                report['volume_stage_options']={'applied_after_surface_persistence':True,
                    'options':volume_options,'boundary_sizing_options_changed':False,
                    'surface_preservation_requires_independent_comparison':True}
                for key,value in volume_options.items():gmsh.option.setNumber(key,value)
                report['volume_generation_attempted']=True
            checkpoint('meshing_'+str(dimension)+'D');gmsh.model.mesh.generate(dimension)
            if dimension==2:
                count=sum(len(ids) for ids in gmsh.model.mesh.getElements(2)[1])
                report['pre3D_surface_triangles']=count
                if advisory:
                    ntags,xyz,_=gmsh.model.mesh.getNodes()
                    points={int(tag):tuple(map(float,xyz[3*i:3*i+3])) for i,tag in enumerate(ntags)}
                    grouped={name:[] for name in groups}
                    for name,face_tags in groups.items():
                        for face in face_tags:
                            kinds,_,flat=gmsh.model.mesh.getElements(2,face)
                            if list(map(int,kinds))!=[2]:raise ValueError('C0_boundary_diagnostic_requires_linear_triangles')
                            grouped[name].extend(tuple(map(int,flat[0][i:i+3])) for i in range(0,len(flat[0]),3))
                    report['C0_pre3D_boundary_diagnostic']=nearest_boundary_nodes(advisory['C0_checkpoints_private'],points,grouped)
                    checkpoint('surface_meshed_C0_checkpoints_measured')
                if count>250000:raise ValueError('pilot_surface_resource_bound_exceeded_before_3D')
                report['persisted_surface']=persist_surface(gmsh,args.output,groups,binding)
                checkpoint('surface_persisted_before_any_3D_generation')
                if guide_frames:
                    report['guide_chord_gate_before_3D']=current_guide_chord_gate(gmsh,guide_sizing,guide_frames)
                    checkpoint('actual_surface_guide_chord_gate_measured_before_3D')
                    if not report['guide_chord_gate_before_3D']['local_radial_envelopes_accepted']:
                        raise ValueError('actual_guide_surface_radial_envelopes_rejected_before_3D')
                if args.stop_after_surface:
                    report['status']='surface_only_not_volume_mesh'
                    raise SurfaceOnlyComplete()
        if guide_frames:
            report['guide_chord_gate_after_3D']=current_guide_chord_gate(gmsh,guide_sizing,guide_frames)
            checkpoint('actual_surface_guide_chord_gate_measured_after_3D')
            if not report['guide_chord_gate_after_3D']['local_radial_envelopes_accepted']:
                raise ValueError('actual_guide_surface_radial_envelopes_rejected_after_3D')
        types,tags,nodes=gmsh.model.mesh.getElements(3)
        if list(map(int,types))!=[4] or not 0<len(tags[0])<=1000000:
            raise ValueError('linear_tetrahedra_within_pilot_resource_bound_required')
        q=list(map(float,gmsh.model.mesh.getElementQualities(tags[0],'minSICN')))
        jac=list(map(float,gmsh.model.mesh.getElementQualities(tags[0],'minDetJac')))
        report['pre_export_quality']=checks.quality_distribution(q,jac)
        original_tetra=sorted(tuple(map(int,nodes[0][i:i+4])) for i in range(0,len(nodes[0]),4))
        node_tags,xyz,_=gmsh.model.mesh.getNodes()
        original_points={int(tag):tuple(map(float,xyz[3*i:3*i+3])) for i,tag in enumerate(node_tags)}
        original_triangles={}
        for name,face_tags in groups.items():
            triangles=[]
            for face in face_tags:
                kinds,_,flat=gmsh.model.mesh.getElements(2,face)
                if list(map(int,kinds))!=[2]:raise ValueError('all_boundary_faces_must_have_linear_triangles')
                triangles.extend(tuple(map(int,flat[0][i:i+3])) for i in range(0,len(flat[0]),3))
            original_triangles[name]=sorted(triangles)
        post_descriptors=[{'tag':tag,'area':gmsh.model.occ.getMass(2,tag),
                          'centre':list(gmsh.model.occ.getCenterOfMass(2,tag))} for _,tag in gmsh.model.getEntities(2)]
        report['native_CAD_descriptors_unchanged_after_meshing']=(post_descriptors==descriptors and gmsh.model.getEntities(3)==volumes and gmsh.model.occ.getMass(3,volumes[0][1])==volume)
        checkpoint('export_MSH22_with_complete_physical_groups')
        mesh_path=args.output/'intake-gas-pilot.msh';gmsh.write(str(mesh_path));mesh_path.chmod(0o600)
        mesh_hash=checks.sha256(mesh_path);parsed=parse_msh22(mesh_path.read_text())
        report['mesh_sha256']=mesh_hash
        triangles=sum(parsed['grouped_triangles'].values(),[])
        topology=checks.connectivity_metrics(parsed['points'],parsed['tetrahedra'],triangles)
        orientation=boundary_orientation(parsed['points'],parsed['tetrahedra'],parsed['grouped_triangles'])
        if advisory:report['C0_saved_MSH_boundary_diagnostic']=nearest_boundary_nodes(advisory['C0_checkpoints_private'],parsed['points'],parsed['grouped_triangles'])
        report['topology']=topology;report['boundary_orientation']=orientation
        report['mesh_bounds_scan_units_private']=mesh_bounds(parsed['points'])
        report['mesh_volume_scan_units_cubed']=topology['signed_volume_sum']
        report['mesh_volume_relative_error']=abs(topology['signed_volume_sum']/original_volume-1)
        same_nodes=parsed['points'].keys()==original_points.keys()
        roundtrip={'node_tags_unchanged':same_nodes,'tetra_connectivity_unchanged':sorted(parsed['tetrahedra'])==original_tetra,
                   'boundary_connectivity_and_labels_unchanged':all(sorted(parsed['grouped_triangles'][name])==original_triangles[name] for name in PATCH_IDS),
                   'maximum_coordinate_delta_scan_units':max((math.dist(p,parsed['points'][tag]) for tag,p in original_points.items()),default=0.) if same_nodes else None}
        report['MSH22_roundtrip']=roundtrip
        gmsh.clear();gmsh.open(str(mesh_path));kinds,reread_tags,_=gmsh.model.mesh.getElements(3)
        if list(map(int,kinds))!=[4]:raise ValueError('reread_tetra_type_changed')
        reread_quality=checks.quality_distribution(list(map(float,gmsh.model.mesh.getElementQualities(reread_tags[0],'minSICN'))),
                                                 list(map(float,gmsh.model.mesh.getElementQualities(reread_tags[0],'minDetJac'))))
        report['MSH_reread_quality']=reread_quality
        report['gates']={'positive_Gmsh_tetra_Jacobians':reread_quality['nonpositive_Jacobians']==0,
                         'positive_direct_tetra_volumes':not(topology['count_negative'] or topology['count_zero'] or topology['repeated_node_tetrahedra']),
                         'one_connected_tetra_region':topology['tetra_connected_components']==1,
                         'complete_nondegenerate_boundary':topology['boundary_matches'],
                         'outward_boundary_orientation':orientation['all_outward'],
                         'native_CAD_descriptors_unchanged':report['native_CAD_descriptors_unchanged_after_meshing'],
                         'same_number_tetrahedra_after_reread':reread_quality['tetrahedra']==len(original_tetra),
                         'MSH22_connectivity_and_groups_preserved':all(roundtrip[k] for k in ('node_tags_unchanged','tetra_connectivity_unchanged','boundary_connectivity_and_labels_unchanged')),
                         'MSH22_coordinate_error_within_1e_10':roundtrip['maximum_coordinate_delta_scan_units'] is not None and roundtrip['maximum_coordinate_delta_scan_units']<=1e-10,
                         'coarse_volume_error_within_1percent':report['mesh_volume_relative_error']<=.01,
                         'MSH_file_unchanged':checks.sha256(mesh_path)==mesh_hash}
        report['status']='pilot_mesh_integrity_passed_pending_OpenFOAM_checkMesh' if all(report['gates'].values()) else 'pilot_mesh_rejected_by_integrity_gate'
        if advisory and all(report['gates'].values()):
            report['status']='diagnostic_C0_mesh_integrity_passed_source_C0_unresolved_no_CFD_release'
    except SurfaceOnlyComplete:
        pass
    except Exception as error:
        report['status']='failed_or_incomplete';report['error_private']=type(error).__name__+': '+str(error)
    finally:
        logs=gmsh.logger.get();gmsh.logger.stop();gmsh.finalize()
        checks.save(args.output/'gmsh-log-private.json',{'lines':logs})
        report['source_unchanged']=checks.sha256(__file__)==source_sha and checks.sha256(checks.__file__)==dependency_sha
        report['all_native_inputs_unchanged']=all(checks.sha256(path)==expected for path,expected in paths.items())
        if not report['source_unchanged'] or not report['all_native_inputs_unchanged']:report['status']='rejected_provenance_changed'
        checkpoint('complete')
    print(json.dumps({'status':report['status'],'elapsed_seconds':report['elapsed_seconds'],'output':str(args.output)}))
    return 0 if report['status'] in ('pilot_mesh_integrity_passed_pending_OpenFOAM_checkMesh','surface_only_not_volume_mesh') else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--diagnostic-c0-advisory',type=Path,help='Exact reviewed C0 advisory; diagnostic attempt only, not a BOP or CFD waiver')
    parser.add_argument('--segmented-native-only',action='store_true',help='Exact separately reviewed C0-segmented package; native checks only, no inherited STEP result')
    parser.add_argument('--volume-quadrature-reference',type=Path,help='Hash-bound OCCT nonadaptive volume reference; import tolerance remains 1e-6')
    parser.add_argument('--stop-after-surface',action='store_true',help='Save all boundary triangles and stop before generate(3); not a volume mesh')
    parser.add_argument('--volume-algorithm',type=int,choices=(1,10),default=1,help='Volume-only comparison after surface persistence: Delaunay1 (default) or HXT10; no quality-gate change')
    parser.add_argument('--face38-algorithm',type=int,choices=(1,5),help='Native gas05 face38 only: MeshAdapt1 or Delaunay5; all other settings unchanged')
    parser.add_argument('--face38-size',type=float,help='Restrict maximum element size on exact face38 and its boundary; CAD and global minimum unchanged')
    parser.add_argument('--guide-size',type=float,help='Exact gas05 guide/stem cylinders only: local target size; surface-only until actual chord review')
    parser.add_argument('--guide-chord-reference',type=Path,help='Exact reviewed native cylinder frames; recompute whole-facet radial bounds before and after 3D')
    resource.setrlimit(resource.RLIMIT_CPU,(285,290))
    raise SystemExit(run(parser.parse_args()))


if __name__=='__main__':
    main()
