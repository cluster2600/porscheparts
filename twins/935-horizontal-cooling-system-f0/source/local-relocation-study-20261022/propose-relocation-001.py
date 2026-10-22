"""Propose bounded tangential analysis-vertex moves; do not admit the resulting surface."""
import json
import signal
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from run_reconstruction import ROOT, sha

signal.alarm(180)


def qualities(t):
    normal = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    return 2 * np.sqrt(3) * np.linalg.norm(normal, axis=1) / np.sum((t[:, [1, 2, 0]] - t) ** 2, axis=(1, 2)), normal


def proposal(points, faces, vertex, radius):
    assert 0 < radius <= .05 and len(faces)
    old = points[faces]; old_q, old_n = qualities(old)
    n = old_n.sum(axis=0); length = np.linalg.norm(n)
    if length <= 1e-14: return None
    n /= length; axis = np.eye(3)[np.argmin(np.abs(n))]
    u = np.cross(n, axis); u /= np.linalg.norm(u); basis = np.column_stack([u, np.cross(n, u)])
    local = faces == vertex; floor = np.minimum(old_q, .0501)

    def evaluate(x):
        t = old.copy(); t[local] = points[vertex] + radius * (basis @ x[:2])
        q, normals = qualities(t)
        alignment = np.einsum('ij,ij->i', normals, old_n) / (np.linalg.norm(normals, axis=1) * np.linalg.norm(old_n, axis=1))
        return q, alignment

    def constraints(x):
        q, alignment = evaluate(x)
        return np.r_[q-floor, q-x[2], alignment-.25, 1-np.dot(x[:2], x[:2])]

    result = minimize(lambda x: -x[2], [0., 0., float(old_q.min())], method='SLSQP', bounds=[(-1,1),(-1,1),(0,1)], constraints={'type':'ineq','fun':constraints}, options={'maxiter':60,'ftol':1e-10})
    point = (points[vertex] + radius * (basis @ result.x[:2])).astype(np.float32).astype(float)
    t = old.copy(); t[local] = point; q, normals = qualities(t)
    alignment = np.einsum('ij,ij->i', normals, old_n)
    if not result.success or not np.isfinite(point).all() or np.linalg.norm(point-points[vertex]) > radius+1e-5*radius or np.any(q<floor-1e-10) or np.any(alignment<=0) or q.min()<=old_q.min()+1e-6: return None
    return point


control = np.array([[0.,0,0],[1,0,0],[0,.001,0]])
point = proposal(control, np.array([[0,1,2]]), 2, .05)
assert point is not None and np.linalg.norm(point-control[2]) <= .05+1e-6 and qualities(np.array([[control[0],control[1],point]]))[0][0] > .05
phase = ROOT/'work/935-local-relocation-20261022'; source = ROOT/'work/935-surface-facet-repair-20261022/accepted-005/candidate.npz'
assert sha(source) == '6332340e17dc6e49880d932395605cd4563f16fa4473dab39fd8c4c5d74bc474'
with np.load(source) as z: original, faces = z['vertices'].astype(float), z['faces'].astype(np.int64)
points = original.copy(); old_q, _ = qualities(points[faces]); assert int((old_q<.05).sum()) == 46
eligible = np.unique(faces[old_q<.05]); selected = [int(i) for i in eligible]; moves=[]
for pass_index in range(2):
    for vertex in selected:
        incident = np.flatnonzero(np.any(faces==vertex,axis=1)); local_faces=faces[incident]
        if qualities(points[local_faces])[0].min() >= .05: continue
        point = proposal(points, local_faces, vertex, .01)
        if point is not None:
            moves.append({'pass':pass_index,'vertex':vertex,'before':points[vertex].tolist(),'after':point.tolist()}); points[vertex]=point
q,_ = qualities(points[faces]); fixed=np.ones(len(points),dtype=bool);fixed[eligible]=False
assert np.array_equal(points[fixed],original[fixed]) and np.isfinite(q).all() and np.all(q>0) and np.all(q>=np.minimum(old_q,.05)-1e-10)
volume=float(np.einsum('ij,ij->i',points[faces[:,0]],np.cross(points[faces[:,1]],points[faces[:,2]])).sum()/6);assert volume>0
out=phase/'candidate-001';out.mkdir(mode=0o700)
np.savez_compressed(out/'candidate.npz',vertices=points.astype(np.float32),faces=faces)
with (out/'candidate.off').open('x') as stream:
    stream.write('OFF\n%d %d 0\n'%(len(points),len(faces)));np.savetxt(stream,points,fmt='%.17g');np.savetxt(stream,np.column_stack([np.full(len(faces),3),faces]),fmt='%d')
record={'status':'tangential_vertex_proposal_pending_complete_topology_intersection_and_two_surface_bound_checks','source_sha256':sha(__file__),'input_sha256':sha(source),'triangles':len(faces),'poor_triangles_before':46,'poor_triangles_after':int((q<.05).sum()),'minimum_quality_after':float(q.min()),'maximum_total_vertex_displacement_source_units':float(np.linalg.norm(points-original,axis=1).max()),'per_move_radius_source_units':.01,'eligible_vertices':len(eligible),'moves':moves,'all_faces_and_fixed_vertices_unchanged':True,'analytic_skinny_triangle_control_passed':True,'volume_source_units_cubed':volume,'output_sha256':{name:sha(out/name) for name in ['candidate.npz','candidate.off']},'complete_surface_bound_established':False,'scale_verified':False,'CFD_accepted':False,'manufacturing_authorized':False}
with (out/'proposal.json').open('x') as stream:json.dump(record,stream,indent=2)
print(json.dumps({k:v for k,v in record.items() if k!='moves'}),flush=True)
