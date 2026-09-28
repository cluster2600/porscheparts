#!/usr/bin/env python3
"""Bounded 2-to-3 / 3-to-2 / 4-to-4 flips; fixed nodes and cavity boundaries."""
import argparse
from collections import defaultdict
import itertools
import json
from pathlib import Path
import signal
import time

import numpy as np
from optimize_fixed_skin_sicn import metric, admissible, native, read_gmsh
from trial_meshers_2026 import boundary

MESH_SHA='6c250dc93cfcfc91e90921e4b9a2d21f550275928226589b6df696cad95bb552'


def oriented_skin(cells):
    return {min(tuple(f),tuple(np.roll(f,1)),tuple(np.roll(f,2))) for f in boundary(cells)}


def admit_cavity(points, old, new):
    """Orient NEW cells only; reject a changed cavity, folds or quality regression."""
    new=np.asarray(new,dtype=np.int64).copy()
    if len({tuple(sorted(c)) for c in new})!=len(new) or any(len(set(c))!=4 for c in new):
        return None
    oq,ov=metric(points[old]);nq,nv=metric(points[new])
    if not (ov>0).all(): raise ValueError('positive_input_cells_required')
    reverse=nv<0
    new[reverse]=new[reverse][:,[0,2,1,3]]
    nq,nv=metric(points[new])
    if (not admissible(oq,ov,nq,nv) or (nq<.1).sum()>=(oq<.1).sum()
            or oriented_skin(old)!=oriented_skin(new)
            or abs(nv.sum()/ov.sum()-1)>1e-10): return None
    return new


def candidates(cells, bad):
    # ponytail: rebuild only stars touching bad vertices; bounded to four sweeps.
    vertices=np.unique(cells[bad]);near=np.flatnonzero(np.isin(cells,vertices).any(1))
    faces,edges=defaultdict(list),defaultdict(list)
    for i in near:
        for f in itertools.combinations(sorted(cells[i]),3):faces[f].append(int(i))
        for e in itertools.combinations(sorted(cells[i]),2):edges[e].append(int(i))
    bad=set(map(int,bad))
    for face,ids in faces.items():
        if len(ids)!=2 or not bad.intersection(ids):continue
        a,b=[next(v for v in cells[i] if v not in face) for i in ids]
        if a==b:continue
        yield ids,[[a,b,face[j],face[(j+1)%3]] for j in range(3)]
    for edge,ids in edges.items():
        if len(ids) not in (3,4) or not bad.intersection(ids):continue
        ring=sorted(set(cells[ids].ravel())-set(edge))
        if len(ids)==len(ring)==3:yield ids,[[*ring,v] for v in edge]
        if len(ids)==len(ring)==4:
            rim={tuple(sorted(set(cells[i])-set(edge))) for i in ids}
            for a,b in itertools.combinations(ring,2):
                if (a,b) in rim:continue
                c,d=sorted(set(ring)-{a,b});cycle=[edge[0],c,edge[1],d]
                yield ids,[[a,b,cycle[j],cycle[(j+1)%4]] for j in range(4)]


def run(args):
    import gmsh
    if args.output.exists() or args.mesh.is_symlink() or native.sha256(args.mesh)!=MESH_SHA or gmsh.__version__!='4.15.2':
        raise ValueError('fresh_output_and_bound_input_runtime_required')
    args.output.mkdir(mode=0o700);start=time.monotonic();source_sha=native.sha256(__file__)
    report=dict(schema='m64-fixed-skin-flips/v1',input_sha256=MESH_SHA,source_sha256=source_sha,
        runtime=dict(numpy=np.__version__,gmsh=gmsh.__version__),
        helper_sha256={Path(p).name:native.sha256(p) for p in (native.__file__,Path(__file__).with_name('optimize_fixed_skin_sicn.py'),Path(__file__).with_name('trial_meshers_2026.py'))},
        status='incomplete',moves=[],node_motion_allowed=False,boundary_changed=False,
        CAE_authorized=False,manufacturing_authorized=False)
    target=args.output/'report.json';native.save(target,report);signal.alarm(600)
    gmsh.initialize(['cavity-flips','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0)
    try:
        points,cells,triangles,et=read_gmsh(args.mesh)
        nt=np.sort(gmsh.model.mesh.getNodes()[0]);volumes=gmsh.model.getEntities(3)
        if len(volumes)!=1:raise ValueError('one_material_volume_required')
        q,v=metric(points[cells]);nativeq=gmsh.model.mesh.getElementQualities(et,'minSICN')
        if len(cells)!=1341461 or (q<.1).sum()!=37 or not np.allclose(q,nativeq,rtol=1e-10,atol=1e-12):
            raise ValueError('bound_mesh_and_independent_metric_required')
        report['before']=native.quality_distribution(q.tolist(),(6*v).tolist())
        for sweep in range(4):
            used=set();added=[]
            for ids,new in candidates(cells,np.flatnonzero(q<.1)):
                if used.intersection(ids):continue
                admitted=admit_cavity(points,cells[ids],new)
                if admitted is not None:
                    used.update(ids);added.extend(admitted)
                    oq,ov=metric(points[cells[ids]]);nq,nv=metric(points[admitted])
                    report['moves'].append(dict(sweep=sweep+1,old_cells=len(ids),new_cells=len(new),
                        old_bad=int((oq<.1).sum()),new_bad=int((nq<.1).sum()),
                        old_minimum=float(oq.min()),new_minimum=float(nq.min()),
                        cavity_relative_volume_difference=float(abs(nv.sum()/ov.sum()-1))))
            if not used:break
            cells=np.concatenate([cells[[i not in used for i in range(len(cells))]],np.array(added)])
            q,v=metric(points[cells]);native.save(target,report)
            print(json.dumps(dict(sweep=sweep+1,moves=len(report['moves']),bad=int((q<.1).sum()))),flush=True)
        gmsh.model.mesh.removeElements(3,volumes[0][1])
        gmsh.model.mesh.addElementsByType(volumes[0][1],4,[],nt[cells].ravel())
        gmsh.option.setNumber('Mesh.Binary',1);gmsh.option.setNumber('Mesh.SaveAll',1)
        output=args.output/'flipped-private.msh';gmsh.write(str(output));output.chmod(0o600)
        rp,rc,rf,ret=read_gmsh(output)
        exact=bool(np.array_equal(rp,points) and np.array_equal(rc,cells) and np.array_equal(rf,triangles))
        qr=gmsh.model.mesh.getElementQualities(ret,'minSICN');dv=gmsh.model.mesh.getElementQualities(ret,'minDetJac')
        if not np.allclose(q,qr,rtol=1e-10,atol=1e-12):raise ValueError('native_quality_disagreement')
        conn=native.connectivity_metrics(dict(enumerate(tuple(map(float,p)) for p in rp)),rc.tolist(),rf.tolist())
        invariant=bool(exact and conn['boundary_matches'] and conn['tetra_connected_components']==1
                       and conn['count_negative']==conn['count_zero']==0)
        report.update(status='completed',after=native.quality_distribution(list(map(float,qr)),list(map(float,dv))),
            exact_roundtrip_and_fixed_nodes=exact,connectivity=conn,invariants_passed=invariant,
            mesh_sha256=native.sha256(output),project_quality_passed=bool(invariant and np.min(qr)>=.1))
    except Exception as exc:report.update(status='failed',error=type(exc).__name__+': '+str(exc))
    finally:
        signal.alarm(0);gmsh.finalize()
        report.update(seconds=time.monotonic()-start,inputs_unchanged=native.sha256(args.mesh)==MESH_SHA and native.sha256(__file__)==source_sha)
        native.save(target,report)
    return 0 if report.get('project_quality_passed') and report['inputs_unchanged'] else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('mesh','output'):p.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(run(p.parse_args()))
