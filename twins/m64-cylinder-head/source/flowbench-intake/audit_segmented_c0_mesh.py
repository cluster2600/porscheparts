#!/usr/bin/env python3
"""Private native split inventory and limited surface-incidence conservation audit.

No CAD or mesh is modified. Surface chains are not a proof of Gmsh 1D entity
classification, continuous chord fidelity, volume quality, CFD or fabrication.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import resource
import time

DOMAIN = '7fc114c1a8229665047c734fd22129783df420deb5e01e809995c6b3efdc5de8'
REVIEW = '7cb1fecc8b4f710e74824e9cfdac4bf2fb8e845288fb4ec07973fbab3d665e00'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_surface_msh22(text):
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
    faces = defaultdict(list); counts = Counter(); ids = set()
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
    if not faces: raise ValueError('surface_triangles_required')
    return points, dict(faces), dict(counts)


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


def verified_face_lookup(binding):
    matches=binding.get('matches_private',[])
    if (binding.get('descriptor_bijection_verified') is not True
            or binding.get('unmatched_gmsh_faces') or binding.get('ambiguous_gmsh_faces')
            or len(matches)!=88 or {r['source_face_index'] for r in matches}!=set(range(1,89))
            or len({r['gmsh_face_tag'] for r in matches})!=88):
        raise ValueError('complete_descriptor_bijective_face_binding_required')
    return {r['source_face_index']:r['gmsh_face_tag'] for r in matches}


def native_inventory(path, review):
    import OCP
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS_Shape, TopoDS
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape,str(path),BRep_Builder()): raise ValueError('native_read_failed')
    def indexed(obj, kind):
        result = TopTools_IndexedMapOfShape(); TopExp.MapShapes_s(obj,kind,result); return result
    edge_map=indexed(shape,TopAbs_EDGE); vertex_map=indexed(shape,TopAbs_VERTEX); face_map=indexed(shape,TopAbs_FACE)
    if (edge_map.Extent(),vertex_map.Extent(),face_map.Extent()) != (195,120,88):
        raise ValueError('reviewed_native_topology_required')
    edge_ids = [r['edge_id_private'] for r in review['split_curve_reference_comparisons_private']]
    edges = []; native_edges = []; vertices = {}; chain = []
    for i in edge_ids:
        edge=TopoDS.Edge_s(edge_map.FindKey(i)); curve=BRepAdaptor_Curve(edge)
        endpoints=[TopExp.FirstVertex_s(edge),TopExp.LastVertex_s(edge)]
        ids=[vertex_map.FindIndex(v) for v in endpoints]
        if chain and chain[-1] != ids[0]: raise ValueError('split_chain_not_topologically_consecutive')
        chain.extend(ids if not chain else ids[1:])
        for j,v in zip(ids,endpoints):
            p=BRep_Tool.Pnt_s(v)
            vertices[j]={'id':j,'point_private':[p.X(),p.Y(),p.Z()], 'tolerance':BRep_Tool.Tolerance_s(v)}
        adjacent=[j for j in range(1,face_map.Extent()+1)
                  if indexed(face_map.FindKey(j),TopAbs_EDGE).Contains(edge)]
        props=GProp_GProps(); BRepGProp.LinearProperties_s(edge,props)
        edges.append({'id':i,'vertex_ids_private':ids,'parameter_range_private':[curve.FirstParameter(),curve.LastParameter()],
            'length':props.Mass(),'tolerance':BRep_Tool.Tolerance_s(edge),'adjacent_native_face_ids':adjacent})
        native_edges.append(edge)
    if len(edges)!=4 or len(set(chain))!=5 or len(set(tuple(r['adjacent_native_face_ids']) for r in edges))!=1:
        raise ValueError('four_split_segments_five_vertices_two_adjacent_faces_required')
    if len(edges[0]['adjacent_native_face_ids'])!=2: raise ValueError('two_adjacent_faces_required')
    graph=review['vertex_graph']
    if not (graph['new_interior_split_vertices_are_distinct_and_not_old_vertices']
            and graph['split_endpoints_preserve_old_vertex_identity_mapping']):
        raise ValueError('independent_vertex_identity_proof_required')
    return {'OCP_version':OCP.__version__, 'edges_private':edges,
        'vertices_private':[vertices[i] for i in chain], 'new_vertex_ids_private':chain[1:-1],
        'new_vertices_distinct_from_old_by_independent_review':True}, native_edges


def run(args):
    started=time.monotonic(); paths={args.domain:DOMAIN,args.review:REVIEW,Path(__file__):sha(__file__)}
    for p,h in paths.items():
        if p.is_symlink() or sha(p)!=h: raise ValueError('exact_native_and_review_required')
    review=json.loads(args.review.read_text()); inventory,native_edges=native_inventory(args.domain,review)
    report={'schema':'m64-segmented-C0-surface-conservation/v1','source_sha256':sha(__file__),
        'domain_sha256':DOMAIN,'independent_review_sha256':REVIEW,**inventory,
        'status':'native_inventory_only_no_mesh', 'mesh_audited':False,
        'native_1D_mesh_classification_proven':False,'continuous_chord_fidelity_proven':False,
        'CFD_qualified':False,'manufacturing_authorized':False,
        'units':'scan_units_under_unverified_1_unit_per_mm_hypothesis'}
    if args.import_report:
        paths[args.import_report]=sha(args.import_report); imp=json.loads(args.import_report.read_text())
        if DOMAIN not in imp['input_sha256'].values(): raise ValueError('import_domain_mismatch')
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
        if mr['native_BRep_sha256']!=DOMAIN or mr['persisted_surface']['MSH_sha256']!=paths[args.mesh]:
            raise ValueError('mesh_report_native_or_surface_hash_mismatch')
        points,faces,counts=parse_surface_msh22(args.mesh.read_text())
        binding=mr['import']['face_binding_private']
        lookup=verified_face_lookup(binding)
        tags=[lookup[i] for i in inventory['edges_private'][0]['adjacent_native_face_ids']]
        shared=common_face_edges(faces[tags[0]],faces[tags[1]])
        boundary_nodes=set(n for e in shared for n in e)
        anchors,anchors_pass=match_anchors(points,boundary_nodes,inventory['vertices_private'])
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
                for row,p in ((anchors[k],lo),(anchors[k+1],hi)):
                    if row['distance']<=edge['tolerance']:
                        projected[row['node']]=p; distances[row['node']]=row['distance']
                barriers={a['node'] for j,a in enumerate(anchors) if j not in (k,k+1)}
                result=monotone_segment_chain(shared,projected,anchors[k]['node'],anchors[k+1]['node'],barriers)
                result['native_edge_id']=edge['id']
                if result['passes']:
                    result['maximum_native_node_projection_distance']=max((distances.get(n,0.) for n in result['nodes_private']),default=0.)
                rows.append(result)
        partition=exact_chain_partition(shared,rows)
        accepted=anchors_pass and partition['passes']
        report.update(mesh_audited=True,mesh_sha256=paths[args.mesh],mesh_report_sha256=paths[args.mesh_report],
            anchors_private=anchors,all_five_anchors_distinct_and_uniquely_matched=anchors_pass,
            shared_face_tags_private=tags,shared_face_incidence_edges=len(shared),mesh_element_type_counts=counts,
            segment_chains_private=rows,complete_shared_interface_partition=partition,
            surface_incidence_segment_representation=accepted,
            status='surface_incidence_conservation_passed_limited_scope' if accepted else 'surface_incidence_conservation_not_proven')
    report['inputs_unchanged']=all(sha(p)==h for p,h in paths.items())
    report['elapsed_seconds']=time.monotonic()-started
    if args.output.exists(): raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');args.output.chmod(0o600)
    print(json.dumps({'status':report['status'],'report_sha256':sha(args.output),'elapsed_seconds':report['elapsed_seconds']}))
    return 0 if report['inputs_unchanged'] and report.get('surface_incidence_segment_representation',True) else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('domain','review','output'): parser.add_argument('--'+key,type=Path,required=True)
    for key in ('mesh','mesh-report','import-report'):parser.add_argument('--'+key,type=Path)
    resource.setrlimit(resource.RLIMIT_CPU,(120,125))
    raise SystemExit(run(parser.parse_args()))
