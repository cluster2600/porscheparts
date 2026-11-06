"""Audit new wall-border loops using actual acquired-edge binormals and ancestry."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def cycle_identity(signatures):
    rows = [tuple(map(int, row)) for row in signatures]
    assert len(set(rows)) == len(rows)
    first = min(range(len(rows)), key=lambda i: rows[i])
    return hashlib.sha256(json.dumps(rows[first:]+rows[:first], separators=(',', ':')).encode()).hexdigest()


def pair_ancestry(mesh, owner, raw, keys, pair, kind, edge):
    """An inferred owner retains its two observed supports, never a measured normal."""
    assert mesh['inferred_surface_kind'][owner] == kind and mesh['original_face_ids'][owner] == -1
    left, right = keys; nodes = [int(left[1]), int(left[2]), int(right[1]), int(right[2])]
    points = raw['vertices'][nodes]; assert len({tuple(p) for p in points}) == 4
    allowed = [[[1,0,3],[1,3,2]], [[1,0,2],[0,3,2]]]
    face = mesh['points'][mesh['triangles'][owner]]
    assert any(np.array_equal(face, points[triangle]) for alternative in allowed for triangle in alternative)
    ids = []
    for node in edge:
        matches = [index for index,p in enumerate(points) if np.array_equal(mesh['points'][node],p)]
        assert len(matches) == 1; ids.append(nodes[matches[0]])
    return [kind, int(pair), int(left[0]), int(right[0]), -1, *ids]


def screen(points, acquired_positions, normals, owner_ids, limits, simple):
    reasons = []; centered = points-points.mean(axis=0)
    _, singular, axes = np.linalg.svd(centered, full_matrices=False)
    rank = int(np.count_nonzero(singular > singular.max()*max(points.shape)*np.finfo(float).eps))
    span = float(np.linalg.norm(np.ptp(points, axis=0)))
    residual = float(np.max(np.abs(centered@axes[-1])))
    if not limits['min_edges'] <= len(points) <= limits['max_edges']: reasons.append('edge_count')
    if rank < 2: reasons.append('rank_below_two')
    if span > limits['max_diagonal_nominal_mm']: reasons.append('diagonal')
    if residual > limits['max_plane_residual_nominal_mm']: reasons.append('planarity')
    if len({tuple(p) for p in points}) != len(points): reasons.append('repeated_source_coordinate')
    if not reasons:
        exact = [tuple(Fraction.from_float(float(v)) for v in p) for p in points]
        area = [sum(a[(axis+1)%3]*b[(axis+2)%3]-a[(axis+2)%3]*b[(axis+1)%3] for a,b in zip(exact,exact[1:]+exact[:1])) for axis in range(3)]
        drop = max(range(3), key=lambda axis: abs(area[axis])); keep = [axis for axis in range(3) if axis != drop]
        if not area[drop] or not simple([tuple(p[axis] for axis in keep) for p in exact]): reasons.append('non_simple_or_zero_exact_projection')
    descriptors = dict(rank=rank, diagonal_nominal_mm=span, plane_residual_nominal_mm=residual,
                       actual_acquired_edges=len(acquired_positions), distinct_actual_acquired_owners=len(set(map(int,owner_ids))))
    if len(set(map(int,owner_ids))) < limits['min_distinct_acquired_owners']:
        reasons.append('insufficient_distinct_actual_acquired_owners')
    newell = np.cross(centered,np.roll(centered,-1,axis=0)).sum(axis=0)
    normal = axes[-1].copy()
    if np.dot(normal,newell) > 0: normal *= -1
    tangent = np.roll(points,-1,axis=0)-points
    selected = tangent[acquired_positions]; lengths = np.linalg.norm(selected,axis=1)
    if len(selected) and np.all(lengths > 0):
        binormals = np.cross(selected/lengths[:,None],normals)
        magnitudes = np.linalg.norm(binormals,axis=1)
        if np.all(magnitudes > 0):
            signed = (binormals/magnitudes[:,None])@normal
            minimum, p10 = float(signed.min()), float(np.quantile(signed,.1))
            descriptors.update(minimum_acquired_binormal_signed_dot=minimum, acquired_binormal_signed_p10=p10)
            if minimum <= 0: reasons.append('nonpositive_acquired_edge_binormal')
            if p10 < limits['minimum_acquired_binormal_signed_p10']: reasons.append('acquired_edge_binormal_cone')
        else: reasons.append('zero_acquired_edge_binormal')
    else: reasons.append('missing_or_zero_acquired_edge')
    return reasons, descriptors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(); job=json.loads(args.job.read_text()); started=time.monotonic()
    assert job['schema']=='935-acquired-binormal-end-wall-admission-1' and job['exploratory_outward_winding_assumption']
    for row in job['inputs']: assert sha(row['path'])==row['sha256']
    proof=json.loads(Path(job['parent_proof']).read_text())
    assert proof['mesh_sha256']==sha(job['mesh']) and proof['surface_study_checks_passed']
    mesh,boundary,raw,previous,frontier_mesh,frontier_boundary,frontier,untried,opposed=map(load,
        (job['mesh'],job['boundaries'],job['source_arrays'],job['immediate_parent_mesh'],job['frontier_parent_mesh'],job['frontier_parent_boundaries'],job['frontier_census'],job['untried_census'],job['opposed_census']))
    assert np.array_equal(mesh['points'],previous['points']) and np.array_equal(mesh['triangles'][:len(previous['triangles'])],previous['triangles'])
    identity=module(job['raw_identity_inspector'],'frozen_end_wall_raw_keys'); projection=module(job['projection_helper'],'frozen_end_wall_projection')
    edges=boundary['boundary']; owners=boundary['owners']; nv=len(mesh['points'])
    parent_edges=previous['triangles'][:,[[0,1],[1,2],[2,0]]].reshape(-1,2)
    parent_codes=np.unique(parent_edges.min(axis=1)*nv+parent_edges.max(axis=1)); del parent_edges,previous
    new=edges[boundary['edge_origin_kind']==8]; new_codes=new.min(axis=1)*nv+new.max(axis=1)
    assert not np.any(np.isin(new_codes,parent_codes)); del parent_codes
    signatures=np.full((len(edges),7),-1,dtype=np.int64); normals=np.zeros((len(edges),3)); references=[]; offsets=[0]
    scope_edges=set(); scope=[]
    for curve in range(len(boundary['offsets'])-1):
        a,b=boundary['offsets'][curve:curve+2]; ids=boundary['cycle_edges'][a:b]; origins=set(map(int,boundary['edge_origin_kind'][ids]))
        if 8 in origins and origins <= {1,6,7,8}: scope.append(curve); scope_edges.update(map(int,ids))
    cache={}; recovered=Counter()
    for edge,(nodes,owner,origin) in enumerate(zip(edges,owners,boundary['edge_origin_kind'])):
        refs=[]
        if edge in scope_edges:
            face=mesh['triangles'][owner]; assert tuple(map(int,nodes)) in list(zip(map(int,face),map(int,np.roll(face,-1))))
            if origin==1:
                key,normals[edge]=identity.original_key(mesh,nodes,owner,raw); signatures[edge]=[0,key[0],key[0],-1,-1,key[1],key[2]]; refs=[key]
            else:
                kind,field,census={6:(4,'source_frontier_pair_ids',frontier),7:(6,'source_untried_pair_ids',untried),8:(7,'source_opposed_wall_pair_ids',opposed)}[int(origin)]
                pair=int(mesh[field][owner]); assert pair>=0; label=(kind,pair)
                if label not in cache:
                    pair_edges=census['selected_pair_edge_ids'][pair]
                    if kind==4:
                        keys=[identity.original_key(frontier_mesh,frontier_boundary['boundary_local_nodes'][row],frontier_boundary['boundary_face_rows'][row],raw)[0] for row in pair_edges]
                    else: keys=census['source_edge_keys'][pair_edges]
                    cache[label]=np.asarray(keys,dtype=np.int64)
                refs=cache[label];signatures[edge]=pair_ancestry(mesh,owner,raw,refs,pair,kind,nodes)
            recovered[str(int(origin))]+=1
        references.extend(refs);offsets.append(len(references))
    decisions=[];counts=Counter();source_hashes=[]
    for curve in range(len(boundary['offsets'])-1):
        a,b=boundary['offsets'][curve:curve+2];ids=boundary['cycle_edges'][a:b];reasons=[];descriptors={};digest=None
        if curve not in scope:reasons=['no_new_wall_ancestry_or_other_origin']
        else:
            nodes=edges[ids,0];assert np.array_equal(edges[ids,1],np.roll(nodes,-1)) and len(np.unique(nodes))==len(nodes)
            acquired=np.flatnonzero(boundary['edge_origin_kind'][ids]==1); owner_ids=mesh['original_face_ids'][owners[ids[acquired]]]
            reasons,descriptors=screen(mesh['points'][nodes],acquired,normals[ids[acquired]],owner_ids,job['limits'],projection.simple_projection)
            digest=cycle_identity(signatures[ids]);source_hashes.append(digest)
        counts.update(reasons);decisions.append(dict(curve=curve,edges=len(ids),eligible_scope=curve in scope,admitted=not reasons,reasons=reasons,descriptors=descriptors,directed_source_cycle_sha256=digest,physical_role_accepted=False))
    assert len(source_hashes)==len(set(source_hashes));assert len(decisions)==1463 and len(scope)==216 and len(scope_edges)==6411
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'private-acquired-owner-references.npz',offsets=np.asarray(offsets),raw_owner_edge_keys=np.asarray(references).reshape(-1,3),edge_signatures=signatures,actual_acquired_normals=normals)
    (args.output/'private-all-walk-decisions.json').write_text(json.dumps(decisions,indent=2)+'\n')
    selected=np.array([row['curve'] for row in decisions if row['admitted']],dtype=np.int64);np.save(args.output/'private-admitted-walk-ids.npy',selected)
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),mesh_sha256=sha(job['mesh']),complete_walk_denominator=len(decisions),complete_boundary_edge_denominator=len(edges),new_wall_border_walks=len(scope),new_wall_border_edges=len(scope_edges),scoped_origin_edge_counts=dict(recovered),admitted_trials=len(selected),rejection_reason_counts=dict(counts),new_wall_cross_edges_absent_from_all_parent_faces=len(new),unchanged_previous_complete_walks_not_retried=True,inferred_normals_used_as_acquired_evidence=False,geometry_modified=False,constructor_admission_pending_independent_check=True,physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    main()
