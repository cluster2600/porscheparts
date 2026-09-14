#!/usr/bin/env python3
"""Private native split inventory and limited surface-incidence conservation audit.

No CAD or mesh is modified. Surface chains are not a proof of Gmsh 1D entity
classification, continuous chord fidelity, volume quality, CFD or fabrication.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import math
from pathlib import Path
import resource
import time

DOMAIN = '7fc114c1a8229665047c734fd22129783df420deb5e01e809995c6b3efdc5de8'
REVIEW = '7cb1fecc8b4f710e74824e9cfdac4bf2fb8e845288fb4ec07973fbab3d665e00'
UNIFIED_DOMAIN = 'fab1338a3e3cf36469977716a9cb54b3118382f592c7c41d7c789bdb5fb3aeba'
UNIFIED_MANIFEST = '58b8be5aa0faeac678e6801cad29cfc5520cbf1590076276dbf5ad5157776aa1'
UNIFIED_REVIEW = '7bd9c92d5ac4bafc0146cb77e55f8e95c45d041972ad235f2dce0ab84a21b897'
PREVIOUS_UNIFIED_AUDIT = 'ec44d805d748ff75d45a16121321588ed6706e8782e3aa91bb9ae74bab5d6f6a'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_surface_msh22(text, include_records=False):
    """Keep elementary face tags; accept optional linear 0D/1D/3D elements."""
    sections = {}; lines = iter(text.splitlines())
    for line in lines:
        if not line: continue
        if not line.startswith('$') or line.startswith('$End'):
            raise ValueError('unexpected_MSH_line')
        name = line[1:]; rows = []
        if name in sections: raise ValueError('duplicate_MSH_section')
        for row in lines:
            if row == '$End' + name: break
            rows.append(row)
        else: raise ValueError('unterminated_MSH_section')
        sections[name] = rows
    if sections.get('MeshFormat') != ['2.2 0 8']:
        raise ValueError('MSH22_ASCII_required')
    def counted(name):
        rows = sections[name]
        if int(rows[0]) != len(rows)-1: raise ValueError('MSH_count_mismatch')
        return rows[1:]
    points = {}
    for row in counted('Nodes'):
        values = row.split(); tag = int(values[0]); xyz = tuple(map(float, values[1:]))
        if tag <= 0 or tag in points or len(xyz) != 3 or not all(map(math.isfinite, xyz)):
            raise ValueError('invalid_MSH_node')
        points[tag] = xyz
    faces = defaultdict(list); counts = Counter(); ids = set(); records = []; tetrahedra = []
    for row in counted('Elements'):
        values = list(map(int, row.split())); tag, kind, n = values[:3]
        nodes = tuple(values[3+n:])
        if tag <= 0 or tag in ids or n < 2 or len(values) < 3+n:
            raise ValueError('invalid_MSH_element')
        ids.add(tag)
        if kind not in {1:2, 2:3, 4:4, 15:1} or len(nodes) != {1:2, 2:3, 4:4, 15:1}[kind]:
            raise ValueError('only_linear_MSH_elements_supported')
        if len(set(nodes)) != len(nodes) or any(x not in points for x in nodes):
            raise ValueError('invalid_element_nodes')
        counts[kind] += 1
        if kind == 2:
            if values[4] <= 0: raise ValueError('positive_elementary_face_tag_required')
            faces[values[4]].append(nodes)
            records.append((tag, values[3], values[4], nodes))
        elif kind == 4: tetrahedra.append(nodes)
    if not faces: raise ValueError('surface_triangles_required')
    if include_records: return points, dict(faces), dict(counts), records, tetrahedra
    return points, dict(faces), dict(counts)


def oriented_triangle(nodes):
    return min(nodes[i:]+nodes[:i] for i in range(3))


def compare_volume_boundary(surface_text, volume_text):
    """Exact node/label/orientation comparison, allowing only element-ID changes.

    Also compare the surface records to the actual tetrahedral boundary; this
    is not a test of geometric self-intersections or OpenFOAM cell quality.
    """
    sp,_,_,sr,st=parse_surface_msh22(surface_text,True)
    vp,_,_,vr,vt=parse_surface_msh22(volume_text,True)
    if st or not vt: raise ValueError('surface_then_tetrahedral_volume_required')
    sn={n for row in sr for n in row[3]}; vn={n for row in vr for n in row[3]}
    node_equal=sn==vn and all(sp[n]==vp[n] for n in sn)
    signature=lambda rows:Counter((p,f,oriented_triangle(nodes)) for _,p,f,nodes in rows)
    records_equal=signature(sr)==signature(vr)
    incidence=Counter(); orientation=Counter(); positive=True
    for a,b,c,d in vt:
        u=tuple(vp[b][i]-vp[a][i] for i in range(3)); v=tuple(vp[c][i]-vp[a][i] for i in range(3)); w=tuple(vp[d][i]-vp[a][i] for i in range(3))
        determinant=sum(u[i]*(v[(i+1)%3]*w[(i+2)%3]-v[(i+2)%3]*w[(i+1)%3]) for i in range(3))
        positive=positive and determinant>0 and math.isfinite(determinant)
        for tri in ((a,c,b),(a,b,d),(a,d,c),(b,c,d)):
            key=tuple(sorted(tri)); incidence[key]+=1
            orientation[key]+=1 if oriented_triangle(tri)==key else -1
    outer={k for k,v in incidence.items() if v==1}
    volume_surface=Counter(tuple(sorted(row[3])) for row in vr)
    surface_orientation={tuple(sorted(row[3])):1 if oriented_triangle(row[3])==tuple(sorted(row[3])) else -1 for row in vr}
    incidence_ok=all(v in (1,2) for v in incidence.values()) and all(orientation[k]==0 for k,v in incidence.items() if v==2)
    outer_equal=outer==set(volume_surface) and all(v==1 for v in volume_surface.values())
    outer_orientation=outer_equal and all(surface_orientation[k]==orientation[k] for k in outer)
    before_ids={row[0]:row[1:] for row in sr}
    same_ids=sum(before_ids.get(row[0])==row[1:] for row in vr)
    return {'surface_nodes':len(sn),'surface_triangles':len(sr),'volume_tetrahedra':len(vt),
        'boundary_node_ids_and_coordinates_exact':node_equal,
        'oriented_triangles_and_physical_elementary_groups_exact':records_equal,
        'surface_element_ids_unchanged':same_ids,'surface_element_ids_reassigned':len(vr)-same_ids,
        'tetrahedra_positive_signed_determinant':positive,
        'tetrahedral_face_incidence_and_internal_orientation':incidence_ok,
        'surface_records_equal_actual_tetrahedral_boundary':outer_equal,
        'surface_orientation_matches_outward_tetrahedral_boundary':outer_orientation,
        'passes':node_equal and records_equal and positive and incidence_ok and outer_equal and outer_orientation,
        'self_intersections_and_CFD_quality_proven':False}


def common_face_edges(first, second):
    def edges(triangles):
        result = Counter(); orientation = Counter()
        for tri in triangles:
            for a, b in zip(tri, (*tri[1:], tri[0])):
                result[tuple(sorted((a, b)))] += 1
                orientation[tuple(sorted((a,b)))] += 1 if a < b else -1
        return result, orientation
    (a,oa), (b,ob) = edges(first), edges(second)
    shared = set(a) & set(b)
    if any(a[e] != 1 or b[e] != 1 for e in shared):
        raise ValueError('shared_edge_not_single_incidence_per_face')
    if any(oa[e]+ob[e] != 0 for e in shared):
        raise ValueError('shared_edge_orientations_not_opposite')
    return shared


def match_anchors(points, boundary_nodes, vertices):
    rows = []
    for vertex in vertices:
        distances = sorted((math.dist(vertex['point_private'], points[n]), n) for n in boundary_nodes)
        nearby = [(d,n) for d,n in distances if d <= vertex['tolerance']]
        rows.append({'native_vertex_id':vertex['id'], 'candidate_count':len(nearby),
            'node':nearby[0][1] if len(nearby)==1 else None,
            'distance':distances[0][0] if distances else None,
            'tolerance':vertex['tolerance']})
    tags = [r['node'] for r in rows]
    return rows, all(x is not None for x in tags) and len(set(tags))==len(tags)


def monotone_segment_chain(edges, projected, start, end, other_anchors):
    """Find one strictly parameter-monotone incidence path, not proximity alone.

    projected maps admissible surface node tags to native curve parameters.
    All other native anchors are barriers. Two paths are an ambiguity, not PASS.
    """
    if start not in projected or end not in projected or projected[start] >= projected[end]:
        return {'passes':False, 'reason':'endpoints_not_admissible_or_ordered'}
    low, high = projected[start], projected[end]; allowed = {}
    for node, parameter in projected.items():
        if node not in other_anchors and low <= parameter <= high: allowed[node] = parameter
    graph = defaultdict(list); selected=set()
    for a,b in edges:
        if a not in allowed or b not in allowed: continue
        if allowed[a]==allowed[b]:
            return {'passes':False,'reason':'zero_parameter_interval_edge'}
        selected.add(tuple(sorted((a,b))))
        if allowed[a] > allowed[b]: a,b = b,a
        graph[a].append(b)
    counts = {start:1}; predecessor = {}
    for a in sorted(allowed, key=allowed.get):
        for b in graph[a]:
            if counts.get(a,0):
                counts[b] = min(2, counts.get(b,0)+counts[a]); predecessor[b] = a
    if counts.get(end,0) != 1:
        return {'passes':False, 'reason':'missing_or_ambiguous_monotone_chain',
                'path_count_capped_at_two':counts.get(end,0)}
    path = [end]
    while path[-1] != start: path.append(predecessor[path[-1]])
    path.reverse()
    if {tuple(sorted(e)) for e in zip(path,path[1:])} != selected:
        return {'passes':False,'reason':'uncovered_or_branched_admissible_interface_edges'}
    return {'passes':True, 'nodes_private':path, 'line_segments':len(path)-1,
            'strict_native_parameter_order':True}


def exact_chain_partition(shared_edges, chains):
    counts=Counter(tuple(sorted(edge)) for row in chains if row.get('passes')
        for edge in zip(row['nodes_private'],row['nodes_private'][1:]))
    return {'shared_edges':len(shared_edges),'covered_edges':len(counts),
        'missing_edges':len(set(shared_edges)-counts.keys()),
        'extra_edges':len(counts.keys()-set(shared_edges)),
        'multiply_counted_edges':sum(v>1 for v in counts.values()),
        'passes':len(chains)==4 and all(r.get('passes') for r in chains)
            and set(counts)==set(shared_edges) and all(v==1 for v in counts.values())}


def exact_native_chain_partition(shared_edges, chains, native_edge_ids):
    """Partition de toute l'interface par chaque courbe native, exactement une fois."""
    counts=Counter(tuple(sorted(edge)) for row in chains if row.get('passes')
        for edge in zip(row['nodes_private'],row['nodes_private'][1:]))
    identities=Counter(row['native_edge_id'] for row in chains)
    complete_ids=bool(native_edge_ids) and len(set(native_edge_ids))==len(native_edge_ids)
    complete_ids=complete_ids and identities==Counter(native_edge_ids)
    return {'native_curves':len(native_edge_ids),'native_curve_identity_bijection':complete_ids,
        'shared_edges':len(shared_edges),'covered_edges':len(counts),
        'missing_edges':len(set(shared_edges)-counts.keys()),
        'extra_edges':len(counts.keys()-set(shared_edges)),
        'multiply_counted_edges':sum(v>1 for v in counts.values()),
        'passes':complete_ids and all(r.get('passes') for r in chains)
            and set(counts)==set(shared_edges) and all(v==1 for v in counts.values())}


def native_interface_graph(edges):
    """Classer les composantes par incidence native, sans fermer une chaîne ouverte."""
    graph=defaultdict(list); identities=[row['id'] for row in edges]
    if len(set(identities))!=len(identities): raise ValueError('duplicate_native_interface_curve')
    for row in edges:
        a,b=row['vertex_ids_private'];graph[a].append((b,row['id']));graph[b].append((a,row['id']))
    pending=set(graph); components=[]
    while pending:
        stack=[min(pending)];nodes=set();curves=set()
        while stack:
            vertex=stack.pop()
            if vertex in nodes:continue
            nodes.add(vertex);pending.discard(vertex)
            for other,eid in graph[vertex]:curves.add(eid);stack.append(other)
        ends=sorted(v for v in nodes if len(graph[v])==1)
        regular=all(len(graph[v]) in (1,2) for v in nodes)
        kind=('closed_cycle' if not ends else 'open_chain' if len(ends)==2 else 'unresolved') if regular else 'branched'
        components.append({'kind':kind,'native_vertex_ids_private':sorted(nodes),
            'native_edge_ids_private':sorted(curves),'endpoint_vertex_ids_private':ends})
    return {'components_private':components,'vertices':len(graph),'curves':len(edges),
        'open_chains':sum(c['kind']=='open_chain' for c in components),
        'closed_cycles':sum(c['kind']=='closed_cycle' for c in components),
        'unbranched':bool(components) and all(c['kind'] in ('open_chain','closed_cycle') for c in components)}


def native_endpoint_ball(node, vertex, curve_endpoint):
    """Le sommet et son extrémité de courbe utilisent la boule native du sommet.

    Les points intérieurs restent soumis à la tolérance native de l'arête.
    Aucune tolérance n'est agrandie ou déduite des résultats du maillage.
    """
    node_error=math.dist(node,vertex['point_private'])
    endpoint_error=math.dist(curve_endpoint,vertex['point_private'])
    return {'node_to_native_vertex_distance':node_error,
        'curve_endpoint_to_native_vertex_distance':endpoint_error,
        'node_to_curve_endpoint_distance':math.dist(node,curve_endpoint),
        'native_vertex_tolerance':vertex['tolerance'],
        'passes':all(math.isfinite(x) and x<=vertex['tolerance'] for x in (node_error,endpoint_error))}


def verified_face_lookup(binding, domain=DOMAIN):
    count={DOMAIN:88,UNIFIED_DOMAIN:86}.get(domain)
    if count is None: raise ValueError('unregistered_native_domain')
    matches=binding.get('matches_private',[])
    if (binding.get('descriptor_bijection_verified') is not True
            or binding.get('unmatched_gmsh_faces') or binding.get('ambiguous_gmsh_faces')
            or len(matches)!=count or {r['source_face_index'] for r in matches}!=set(range(1,count+1))
            or len({r['gmsh_face_tag'] for r in matches})!=count):
        raise ValueError('complete_descriptor_bijective_face_binding_required')
    return {r['source_face_index']:r['gmsh_face_tag'] for r in matches}


def unified_correspondence(review, merge, manifest):
    """Retrouver les tronçons par descripteurs exacts, jamais par décalage d'IDs."""
    if (merge.get('original_sha256')!=DOMAIN or merge.get('candidate_sha256')!=UNIFIED_DOMAIN
            or merge.get('inputs_unchanged') is not True or not merge.get('gates')
            or any(v is not True for v in merge['gates'].values())):
        raise ValueError('accepted_exact_native_merge_review_required')
    transfer=manifest['boundary_role_transfer']
    if (transfer.get('original_domain_sha256')!=DOMAIN
            or transfer.get('independent_geometry_review_sha256')!=UNIFIED_REVIEW):
        raise ValueError('unified_manifest_merge_binding_required')
    data=merge['descriptors_private']; before=data['before_edges']; after=data['after_edges']
    old_ids=[r['edge_id_private'] for r in review['split_curve_reference_comparisons_private']]
    if len(old_ids)!=4 or len(set(old_ids))!=4: raise ValueError('four_reviewed_split_edges_required')
    pairs=[]
    for i in old_ids:
        matches=[int(k) for k,v in after.items() if v==before[str(i)]]
        if len(matches)!=1: raise ValueError('unique_exact_preserved_split_edge_required')
        pairs.append((i,matches[0]))
    if len({j for _,j in pairs})!=4: raise ValueError('split_edge_correspondence_not_bijective')
    old_faces=[int(k) for k,v in data['before_faces'].items()
        if set(old_ids)<={r['edge_id'] for r in v['occurrences']}]
    if len(old_faces)!=2: raise ValueError('two_reviewed_adjacent_faces_required')
    relation=transfer['face_index_relation']
    if not isinstance(relation,list) or any(not isinstance(row,list) or len(row)!=2 for row in relation):
        raise ValueError('explicit_native_face_pair_relation_required')
    face_relation=dict(relation)
    if len(face_relation)!=len(relation): raise ValueError('duplicate_original_face_relation')
    face_pairs=[]
    for i in old_faces:
        j=face_relation[i]
        old=data['before_faces'][str(i)]; new=data['after_faces'][str(j)]
        if any(old[k]!=new[k] for k in ('support_sha256','orientation','tolerance')):
            raise ValueError('preserved_C0_adjacent_face_support_required')
        for a,b in pairs:
            fields=lambda rows,e:[{k:v for k,v in r.items() if k!='edge_id'} for r in rows if r['edge_id']==e]
            if not fields(old['occurrences'],a) or fields(old['occurrences'],a)!=fields(new['occurrences'],b):
                raise ValueError('preserved_C0_pcurve_occurrences_required')
        face_pairs.append((i,j))
    if len({j for _,j in face_pairs})!=2: raise ValueError('distinct_C0_adjacent_faces_required')
    return {'edge_pairs_private':pairs,'face_pairs_private':face_pairs,
        'after_edges':{str(j):after[str(j)] for _,j in pairs},
        'after_faces':{str(j):data['after_faces'][str(j)] for _,j in face_pairs}}


def complete_unified_correspondence(correspondence, merge):
    """Étendre explicitement de quatre C0 à toutes les courbes communes aux faces.

    L'union des faces change le périmètre d'incidence, pas les seuils. Les
    courbes supplémentaires doivent elles aussi être conservées exactement.
    """
    data=merge['descriptors_private']; faces=correspondence['after_faces']
    if len(faces)!=2: raise ValueError('two_adjacent_interface_faces_required')
    sets=[{r['edge_id'] for r in f['occurrences']} for f in faces.values()]
    shared=sets[0]&sets[1]; c0=[j for _,j in correspondence['edge_pairs_private']]
    if len(shared)!=8 or len(c0)!=4 or not set(c0)<shared:
        raise ValueError('reviewed_eight_curve_interface_including_four_C0_required')
    pairs=[];origins={}
    for eid in sorted(shared):
        current=data['after_edges'][str(eid)]
        old=[int(k) for k,row in data['before_edges'].items() if row==current]
        if len(old)!=1: raise ValueError('unique_exact_preserved_interface_curve_required')
        pairs.append((old[0],eid))
        origins[str(eid)]=[int(k) for k,row in data['before_faces'].items()
            if any(r['edge_id']==old[0] for r in row['occurrences'])]
        occurrences=[[r for r in f['occurrences'] if r['edge_id']==eid] for f in faces.values()]
        if any(len(rows)!=1 for rows in occurrences) or sum(rows[0]['orientation'] for rows in occurrences)!=0:
            raise ValueError('single_opposite_native_occurrence_per_interface_face_required')
    return {**correspondence,'edge_pairs_private':pairs,'c0_edge_ids_private':c0,
        'other_edge_ids_private':sorted(shared-set(c0)),'original_adjacent_faces_private':origins,
        'after_edges':{str(j):data['after_edges'][str(j)] for _,j in pairs}}


def native_inventory(path, review, correspondence=None, complete_interface=False):
    import OCP
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS_Shape, TopoDS
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.GeomTools import GeomTools
    from OCP.BRepAdaptor import BRepAdaptor_Curve2d
    from OCP.TopoDS import TopoDS_Iterator
    from OCP.TopAbs import TopAbs_WIRE
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape,str(path),BRep_Builder()): raise ValueError('native_read_failed')
    def indexed(obj, kind):
        result = TopTools_IndexedMapOfShape(); TopExp.MapShapes_s(obj,kind,result); return result
    edge_map=indexed(shape,TopAbs_EDGE); vertex_map=indexed(shape,TopAbs_VERTEX); face_map=indexed(shape,TopAbs_FACE)
    expected=(191,118,86) if correspondence else (195,120,88)
    if (edge_map.Extent(),vertex_map.Extent(),face_map.Extent()) != expected:
        raise ValueError('reviewed_native_topology_required')
    edge_ids = ([j for _,j in correspondence['edge_pairs_private']] if correspondence else
        [r['edge_id_private'] for r in review['split_curve_reference_comparisons_private']])
    def encoded(geom):
        stream=io.BytesIO(); GeomTools.Write_s(geom,stream)
        return hashlib.sha256(stream.getvalue()).hexdigest()
    def point(vertex):
        p=BRep_Tool.Pnt_s(vertex); return [p.X(),p.Y(),p.Z()]
    edges = []; native_edges = []; vertices = {}; chain = []
    for i in edge_ids:
        edge=TopoDS.Edge_s(edge_map.FindKey(i)); curve=BRepAdaptor_Curve(edge)
        endpoints=[TopExp.FirstVertex_s(edge),TopExp.LastVertex_s(edge)]
        ids=[vertex_map.FindIndex(v) for v in endpoints]
        if not complete_interface:
            if chain and chain[-1] != ids[0]: raise ValueError('split_chain_not_topologically_consecutive')
            chain.extend(ids if not chain else ids[1:])
        for j,v in zip(ids,endpoints):
            p=BRep_Tool.Pnt_s(v)
            vertices[j]={'id':j,'point_private':[p.X(),p.Y(),p.Z()], 'tolerance':BRep_Tool.Tolerance_s(v)}
        adjacent=[j for j in range(1,face_map.Extent()+1)
                  if indexed(face_map.FindKey(j),TopAbs_EDGE).Contains(edge)]
        if correspondence:
            descriptor={'curve_global_sha256':encoded(BRep_Tool.Curve_s(edge,0.,0.)),
                'range':list(BRep_Tool.Range_s(edge)), 'ends_private':[point(v) for v in endpoints],
                'tolerance':BRep_Tool.Tolerance_s(edge),'same_range':BRep_Tool.SameRange_s(edge),
                'same_parameter':BRep_Tool.SameParameter_s(edge),'degenerated':BRep_Tool.Degenerated_s(edge)}
            if descriptor!=correspondence['after_edges'][str(i)]: raise ValueError('native_split_edge_review_descriptor_mismatch')
            if set(adjacent)!={j for _,j in correspondence['face_pairs_private']}: raise ValueError('native_adjacent_faces_review_mismatch')
        props=GProp_GProps(); BRepGProp.LinearProperties_s(edge,props)
        edges.append({'id':i,'vertex_ids_private':ids,'parameter_range_private':[curve.FirstParameter(),curve.LastParameter()],
            'length':props.Mass(),'tolerance':BRep_Tool.Tolerance_s(edge),'adjacent_native_face_ids':adjacent})
        native_edges.append(edge)
    wire_loops=[]
    if correspondence:
        for _,j in correspondence['face_pairs_private']:
            face=TopoDS.Face_s(face_map.FindKey(j)); expected_face=correspondence['after_faces'][str(j)]
            if (encoded(BRep_Tool.Surface_s(face))!=expected_face['support_sha256']
                    or str(face.Orientation())!=expected_face['orientation']
                    or BRep_Tool.Tolerance_s(face)!=expected_face['tolerance']):
                raise ValueError('native_C0_face_support_review_mismatch')
            measured=[]; wires=indexed(face,TopAbs_WIRE)
            for k in range(1,wires.Extent()+1):
                walk=TopoDS_Iterator(wires.FindKey(k))
                stored=[]
                while walk.More():
                    edge=TopoDS.Edge_s(walk.Value()); eid=edge_map.FindIndex(edge)
                    stored.append((eid,str(edge.Orientation())))
                    if eid in edge_ids:
                        measured.append({'edge_id':eid,'native_orientation':str(edge.Orientation()),
                            'pcurve_sha256':encoded(BRepAdaptor_Curve2d(edge,face).Curve()),
                            'range_on_surface':list(BRep_Tool.Range_s(edge,face))})
                    walk.Next()
                if complete_interface:
                    ordered=[]; explorer=BRepTools_WireExplorer(TopoDS.Wire_s(wires.FindKey(k)),face)
                    while explorer.More():
                        edge=explorer.Current()
                        ordered.append({'edge_id':edge_map.FindIndex(edge),'orientation':str(edge.Orientation()),
                            'start_vertex':vertex_map.FindIndex(TopExp.FirstVertex_s(edge,True)),
                            'end_vertex':vertex_map.FindIndex(TopExp.LastVertex_s(edge,True))})
                        explorer.Next()
                    same=Counter(stored)==Counter((r['edge_id'],r['orientation']) for r in ordered)
                    closed=bool(ordered) and all(a['end_vertex']==b['start_vertex'] for a,b in zip(ordered,ordered[1:]+ordered[:1]))
                    wire_loops.append({'face_id':j,'wire_index':k,'ordered_occurrences_private':ordered,
                        'all_stored_occurrences_covered':same,'topologically_closed':closed})
            fields=('edge_id','native_orientation','pcurve_sha256','range_on_surface')
            expected_occ=[{k:r[k] for k in fields} for r in expected_face['occurrences'] if r['edge_id'] in edge_ids]
            key=lambda r:json.dumps(r,sort_keys=True)
            if Counter(map(key,measured))!=Counter(map(key,expected_occ)):
                raise ValueError('native_C0_pcurve_occurrences_review_mismatch')
    if complete_interface:
        selected={r['id']:r for r in edges};c0chain=[]
        for eid in correspondence['c0_edge_ids_private']:
            ids=selected[eid]['vertex_ids_private']
            if c0chain and c0chain[-1]!=ids[0]:raise ValueError('split_chain_not_topologically_consecutive')
            c0chain.extend(ids if not c0chain else ids[1:])
        chain=c0chain
    if len(edges)!=(8 if complete_interface else 4) or len(set(chain))!=5 or len(set(tuple(r['adjacent_native_face_ids']) for r in edges))!=1:
        raise ValueError('four_split_segments_five_vertices_two_adjacent_faces_required')
    if len(edges[0]['adjacent_native_face_ids'])!=2: raise ValueError('two_adjacent_faces_required')
    graph=review['vertex_graph']
    if not (graph['new_interior_split_vertices_are_distinct_and_not_old_vertices']
            and graph['split_endpoints_preserve_old_vertex_identity_mapping']):
        raise ValueError('independent_vertex_identity_proof_required')
    inventory={'OCP_version':OCP.__version__, 'edges_private':edges,
        'vertices_private':[vertices[i] for i in (sorted(vertices) if complete_interface else chain)],
        'new_vertex_ids_private':chain[1:-1], 'new_vertices_distinct_from_old_by_independent_review':True}
    if complete_interface:
        # Exhaustivité native indépendante de la liste issue du reçu.
        pair=[j for _,j in correspondence['face_pairs_private']]
        face_edges=[indexed(face_map.FindKey(j),TopAbs_EDGE) for j in pair]
        actual_shared={i for i in range(1,edge_map.Extent()+1) if all(m.Contains(edge_map.FindKey(i)) for m in face_edges)}
        if actual_shared!=set(edge_ids):raise ValueError('native_shared_interface_inventory_not_exhaustive')
        inventory.update(native_interface_graph_private=native_interface_graph(edges),
            native_face_wire_loops_private=wire_loops,native_shared_curve_inventory_complete=True,
            C0_edge_ids_private=correspondence['c0_edge_ids_private'],
            other_interface_edge_ids_private=correspondence['other_edge_ids_private'])
        if (not inventory['native_interface_graph_private']['unbranched']
                or not all(r['all_stored_occurrences_covered'] and r['topologically_closed'] for r in wire_loops)):
            raise ValueError('native_interface_and_face_wire_incidence_not_proven')
    return inventory, native_edges


def run(args):
    started=time.monotonic(); unified=args.unified_native_only
    complete=args.complete_unified_interface
    if complete and (not unified or not args.previous_audit):
        raise ValueError('complete_interface_requires_unified_mode_and_historical_audit')
    if args.previous_audit and not complete: raise ValueError('historical_audit_requires_explicit_scope_evolution')
    domain=UNIFIED_DOMAIN if unified else DOMAIN
    paths={args.domain:domain,args.review:REVIEW,Path(__file__):sha(__file__)}
    if unified:
        if not args.manifest or not args.merge_review: raise ValueError('unified_manifest_and_merge_review_required')
        paths.update({args.manifest:UNIFIED_MANIFEST,args.merge_review:UNIFIED_REVIEW})
    elif args.manifest or args.merge_review:
        raise ValueError('explicit_unified_native_mode_required')
    if complete: paths[args.previous_audit]=PREVIOUS_UNIFIED_AUDIT
    for p,h in paths.items():
        if p.is_symlink() or sha(p)!=h: raise ValueError('exact_native_and_review_required')
    review=json.loads(args.review.read_text()); correspondence=None
    if unified:
        correspondence=unified_correspondence(review,json.loads(args.merge_review.read_text()),json.loads(args.manifest.read_text()))
        if complete:correspondence=complete_unified_correspondence(correspondence,json.loads(args.merge_review.read_text()))
    inventory,native_edges=native_inventory(args.domain,review,correspondence,complete)
    report={'schema':'m64-segmented-C0-surface-conservation/v1','source_sha256':sha(__file__),
        'domain_sha256':domain,'independent_review_sha256':REVIEW,**inventory,
        'status':'native_inventory_only_no_mesh', 'mesh_audited':False,
        'native_1D_mesh_classification_proven':False,'continuous_chord_fidelity_proven':False,
        'CFD_qualified':False,'manufacturing_authorized':False,
        'units':'scan_units_under_unverified_1_unit_per_mm_hypothesis'}
    if unified:
        report['unified_native_provenance']={'manifest_sha256':UNIFIED_MANIFEST,
            'merge_review_sha256':UNIFIED_REVIEW,'original_segmented_domain_sha256':DOMAIN,
            'edge_pairs_private':correspondence['edge_pairs_private'],
            'adjacent_face_pairs_private':correspondence['face_pairs_private'],
            'current_native_curves_supports_and_C0_pcurve_occurrences_match_review':True,
            'vertex_distinction_inherited_from_split_review_with_exact_retained_endpoints':True,
            'comparison_basis':'reviewed_serialization_control_not_raw_original_descriptor_identity',
            'previous_mesh_results_transferred':False}
    if complete:
        report['schema']='m64-complete-native-interface-conservation/v2'
        report['scope_evolution']={'previous_audit_sha256':PREVIOUS_UNIFIED_AUDIT,
            'previous_result_preserved':'four_C0_chains_do_not_partition_the_enlarged_interface',
            'new_requirement':'all_eight_native_shared_curves_exactly_partition_all_shared_mesh_edges',
            'native_edge_and_vertex_tolerances_unchanged':True,
            'endpoint_rule':'native_vertex_ball_for_topological_endpoints; native_edge_tolerance_for_interior_projection',
            'original_adjacent_faces_private':correspondence['original_adjacent_faces_private']}
    if args.import_report:
        paths[args.import_report]=sha(args.import_report); imp=json.loads(args.import_report.read_text())
        if domain not in imp['input_sha256'].values(): raise ValueError('import_domain_mismatch')
        candidates=[]
        for edge in inventory['edges_private']:
            matches=[r for r in imp['curves_private'] if abs(r['length']-edge['length'])<=max(1e-10,edge['length']*1e-10)]
            candidates.append({'native_edge_id':edge['id'],'length_matched_curve_candidates_private':matches})
        report['Gmsh_import_comparison']={'report_sha256':paths[args.import_report],
            'candidate_matches_private':candidates,'point_coordinates_available':False,
            'geometric_entity_bijection_proven':False,
            'scope':'length_and_endpoint_graph_only_not_point_coordinate_correspondence'}
    if args.mesh:
        if not args.mesh_report: raise ValueError('mesh_report_required_for_native_face_binding')
        paths[args.mesh]=sha(args.mesh);paths[args.mesh_report]=sha(args.mesh_report)
        mr=json.loads(args.mesh_report.read_text())
        if mr['native_BRep_sha256']!=domain or mr['persisted_surface']['MSH_sha256']!=paths[args.mesh]:
            raise ValueError('mesh_report_native_or_surface_hash_mismatch')
        if unified and mr.get('gas_domain_report_sha256')!=UNIFIED_MANIFEST:
            raise ValueError('mesh_report_unified_manifest_mismatch')
        points,faces,counts=parse_surface_msh22(args.mesh.read_text())
        binding=mr['import']['face_binding_private']
        lookup=verified_face_lookup(binding,domain)
        tags=[lookup[i] for i in inventory['edges_private'][0]['adjacent_native_face_ids']]
        shared=common_face_edges(faces[tags[0]],faces[tags[1]])
        boundary_nodes=set(n for e in shared for n in e)
        anchors,anchors_pass=match_anchors(points,boundary_nodes,inventory['vertices_private'])
        anchors_by_id={r['native_vertex_id']:r for r in anchors}
        vertices_by_id={r['id']:r for r in inventory['vertices_private']}
        rows=[]
        if anchors_pass:
            from OCP.BRep import BRep_Tool
            from OCP.GeomAPI import GeomAPI_ProjectPointOnCurve
            from OCP.gp import gp_Pnt
            for k,(edge,native) in enumerate(zip(inventory['edges_private'],native_edges)):
                curve=BRep_Tool.Curve_s(native,0.,0.); lo,hi=edge['parameter_range_private']; projected={}; distances={}
                for n in boundary_nodes:
                    job=GeomAPI_ProjectPointOnCurve(gp_Pnt(*points[n]),curve,lo,hi)
                    if job.NbPoints()>0 and job.LowerDistance()<=edge['tolerance']:
                        projected[n]=job.LowerDistanceParameter(); distances[n]=job.LowerDistance()
                # The exact shared CAD vertex is the interval endpoint; clamp
                # only its parameter after independently checking spatial error.
                endpoint_rows=[anchors_by_id[v] for v in edge['vertex_ids_private']]
                endpoint_checks=[]
                for row,p,vid in zip(endpoint_rows,(lo,hi),edge['vertex_ids_private']):
                    if complete:
                        endpoint=curve.Value(p)
                        check=native_endpoint_ball(points[row['node']],vertices_by_id[vid],(endpoint.X(),endpoint.Y(),endpoint.Z()))
                        endpoint_checks.append(check)
                        if not check['passes']:continue
                    if row['distance']<=edge['tolerance']:
                        projected[row['node']]=p; distances[row['node']]=row['distance']
                barriers={a['node'] for a in anchors if a['native_vertex_id'] not in edge['vertex_ids_private']}
                result=monotone_segment_chain(shared,projected,endpoint_rows[0]['node'],endpoint_rows[1]['node'],barriers)
                result['native_edge_id']=edge['id']
                if complete:
                    result['native_endpoint_ball_checks']=endpoint_checks
                    result['kind']='C0_split' if edge['id'] in inventory['C0_edge_ids_private'] else 'other_native_interface_curve'
                    if not all(r['passes'] for r in endpoint_checks):
                        result.update(passes=False,reason='native_curve_endpoint_outside_native_vertex_tolerance_ball')
                if result['passes']:
                    if complete:
                        interior=[n for n in result['nodes_private'] if n not in {r['node'] for r in endpoint_rows}]
                        result['interior_surface_nodes_projected']=len(interior)
                        result['maximum_interior_native_curve_projection_distance']=max((distances[n] for n in interior),default=None)
                    else:
                        result['maximum_native_node_projection_distance']=max((distances.get(n,0.) for n in result['nodes_private']),default=0.)
                rows.append(result)
        partition=(exact_native_chain_partition(shared,rows,[r['id'] for r in inventory['edges_private']])
            if complete else exact_chain_partition(shared,rows))
        accepted=anchors_pass and partition['passes']
        report.update(mesh_audited=True,mesh_sha256=paths[args.mesh],mesh_report_sha256=paths[args.mesh_report],
            anchors_private=anchors,all_five_anchors_distinct_and_uniquely_matched=anchors_pass,
            shared_face_tags_private=tags,shared_face_incidence_edges=len(shared),mesh_element_type_counts=counts,
            segment_chains_private=rows,complete_shared_interface_partition=partition,
            surface_incidence_segment_representation=accepted,
            status='surface_incidence_conservation_passed_limited_scope' if accepted else 'surface_incidence_conservation_not_proven')
        if complete:
            report.pop('all_five_anchors_distinct_and_uniquely_matched')
            report.update(all_native_interface_anchors_distinct_and_uniquely_matched=anchors_pass,
                historical_C0_only_partition_recomputed=exact_chain_partition(shared,[r for r in rows if r['kind']=='C0_split']),
                status='complete_native_interface_conservation_passed_limited_scope' if accepted else 'complete_native_interface_conservation_not_proven')
    if args.volume_mesh:
        if not args.mesh: raise ValueError('surface_mesh_and_report_required_before_volume_boundary_comparison')
        paths[args.volume_mesh]=sha(args.volume_mesh)
        if mr.get('mesh_sha256')!=paths[args.volume_mesh]: raise ValueError('volume_mesh_report_hash_mismatch')
        boundary=compare_volume_boundary(args.mesh.read_text(),args.volume_mesh.read_text())
        report.update(volume_mesh_sha256=paths[args.volume_mesh],volume_boundary_conservation=boundary)
        if not boundary['passes']: report['status']='volume_boundary_conservation_not_proven'
    report['inputs_unchanged']=all(sha(p)==h for p,h in paths.items())
    report['elapsed_seconds']=time.monotonic()-started
    if args.output.exists(): raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');args.output.chmod(0o600)
    print(json.dumps({'status':report['status'],'report_sha256':sha(args.output),'elapsed_seconds':report['elapsed_seconds']}))
    return 0 if (report['inputs_unchanged'] and report.get('surface_incidence_segment_representation',True)
        and report.get('volume_boundary_conservation',{}).get('passes',True)) else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('domain','review','output'): parser.add_argument('--'+key,type=Path,required=True)
    for key in ('mesh','mesh-report','import-report','manifest','merge-review','volume-mesh','previous-audit'):parser.add_argument('--'+key,type=Path)
    parser.add_argument('--unified-native-only',action='store_true',
        help='Audit the separately pinned native fab domain; no STEP or prior mesh result is inherited')
    parser.add_argument('--complete-unified-interface',action='store_true',
        help='Separately audit all eight shared native curves; preserve the historical four-C0 partition result')
    resource.setrlimit(resource.RLIMIT_CPU,(120,125))
    raise SystemExit(run(parser.parse_args()))
