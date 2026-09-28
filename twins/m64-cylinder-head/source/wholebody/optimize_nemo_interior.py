#!/usr/bin/env python3
"""One bounded PhysicsNeMo-autograd experiment, with every boundary node fixed.

Optimises mesh nodes, never CAD. Reuses the admitted bridge's exact input and
the frozen native topology/quality checks; a better mesh is not CAE admission.
"""
import argparse
import json
from pathlib import Path
import signal
import sys
import time

from audit_nemo_picogk_bridge import MESH_SHA, tetra_reference
from audit_surface_gpu import sha

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mesh_native_ported_head as native


def improves(old, new):
    return (new['nonpositive_Jacobians']==0 and new['minSICN_below_0p1']<old['minSICN_below_0p1']
            and new['minimum_minSICN']>=old['minimum_minSICN']-1e-12
            and new['bad_tetrahedron_absolute_volume_fraction']<=old['bad_tetrahedron_absolute_volume_fraction'])


def run(args):
    import gmsh
    import importlib.metadata as metadata
    import numpy as np
    import torch
    from physicsnemo.mesh import Mesh
    if (args.output.exists() or args.mesh.is_symlink() or sha(args.mesh)!=MESH_SHA
            or sha(native.__file__)!='7171d7b1da250d63086b7fac1e5e1617190ec26f45f2928e729d60582a1d1c04'):
        raise ValueError('fresh_output_exact_mesh_and_auditor_required')
    versions={n:metadata.version(n) for n in ('torch','numpy','nvidia-physicsnemo','gmsh')}
    if versions!={'torch':'2.10.0','numpy':'2.2.6','nvidia-physicsnemo':'2.2.0','gmsh':'4.15.2'}:
        raise ValueError('exact_CPU_runtime_required')
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    start=time.monotonic(); source_hash=sha(__file__); torch.set_num_threads(4)
    gmsh.initialize(['nemo-interior','-nopopup'],readConfigFiles=False,run=False)
    receipt={'schema':'m64-nemo-interior-optimization/v1','status':'incomplete','source_sha256':source_hash,
             'input_sha256':MESH_SHA,'versions':versions,'execution':'actual_PhysicsNeMo_CPU_autograd',
             'native_CAD_modified':False,'boundary_motion_allowed':False,'manufacturing_authorized':False,
             'CAE_authorized':False,'CUDA_run':False,'iterations':120,'check_every':10,
             'per_axis_displacement_limit_fraction_of_initial_min_incident_edge':.25,'history':[]}
    try:
        gmsh.option.setNumber('General.Terminal',0); gmsh.open(str(args.mesh))
        tags,xyz,_=gmsh.model.mesh.getNodes(); order=np.argsort(tags); tags=tags[order]
        points=np.asarray(xyz,dtype=np.float64).reshape(-1,3)[order]
        types,et,en=gmsh.model.mesh.getElements(3); stypes,_,sn=gmsh.model.mesh.getElements(2)
        if list(types)!=[4] or list(stypes)!=[2] or len(et[0])!=241299: raise ValueError('exact_linear_mesh_required')
        cells=np.searchsorted(tags,en[0]).reshape(-1,4).astype(np.int64)
        triangles=np.searchsorted(tags,sn[0]).reshape(-1,3).astype(np.int64)
        tetra_reference(points,cells)
        quality=np.asarray(gmsh.model.mesh.getElementQualities(et[0],'minSICN'))
        boundary=np.unique(triangles); free=np.setdiff1d(np.unique(cells[quality<.1]),boundary)
        affected=np.isin(cells,free).any(1); patch=cells[affected]
        if len(free)!=74 or len(patch)!=1463 or int((quality<.1).sum())!=160: raise ValueError('bound_patch_changed')
        def distribution():
            return native.quality_distribution(list(map(float,gmsh.model.mesh.getElementQualities(et[0],'minSICN'))),
                list(map(float,gmsh.model.mesh.getElementQualities(et[0],'minDetJac'))))
        initial=best=distribution(); best_points=points.copy(); current=points.copy()
        trust=[]
        for index in free:
            neighbours=np.setdiff1d(np.unique(patch[(patch==index).any(1)]),[index])
            trust.append(.25*np.linalg.norm(points[neighbours]-points[index],axis=1).min())
        base=torch.from_numpy(points.copy()); pc=torch.from_numpy(patch); fi=torch.from_numpy(free)
        scales=torch.tensor(trust,dtype=torch.float64)[:,None]
        offset=torch.zeros((len(free),3),dtype=torch.float64,requires_grad=True)
        optimizer=torch.optim.Adam([offset],lr=.03)
        vref=torch.from_numpy(tetra_reference(points,patch)['volumes'])
        def trial_points():
            return base.index_copy(0,fi,base[fi]+scales*torch.tanh(offset))
        for iteration in range(1,121):
            optimizer.zero_grad(); trial=trial_points(); local=Mesh(points=trial,cells=pc)
            aspect=local.quality_metrics['aspect_ratio']
            p=trial[pc]; signed=torch.linalg.det(p[:,1:]-p[:,[0]])/6
            loss=torch.log(aspect).square().mean()+1000*torch.relu(.2-signed/vref).square().mean()
            if not torch.isfinite(loss): raise ValueError('nonfinite_objective')
            loss.backward()
            if offset.grad is None or not torch.isfinite(offset.grad).all(): raise ValueError('nonfinite_gradient')
            optimizer.step()
            if iteration%10: continue
            current=trial_points().detach().numpy()
            for index in free: gmsh.model.mesh.setNode(int(tags[index]),current[index].tolist(),[])
            measured=distribution(); accepted=improves(best,measured)
            receipt['history'].append({'iteration':iteration,'objective_before_step':float(loss.detach()),
                'candidate':measured,'selected_as_best':accepted})
            if accepted: best=measured; best_points=current.copy()
        for index in free: gmsh.model.mesh.setNode(int(tags[index]),best_points[index].tolist(),[])
        final=distribution(); path=args.output/'interior-optimized-private.msh'; gmsh.write(str(path))
        mesh_hash=sha(path); gmsh.clear(); gmsh.open(str(path))
        rt,rxyz,_=gmsh.model.mesh.getNodes(); ro=np.argsort(rt)
        reread=np.asarray(rxyz,dtype=np.float64).reshape(-1,3)[ro]
        rtypes,ret,ren=gmsh.model.mesh.getElements(3); rst,_,rsn=gmsh.model.mesh.getElements(2)
        same_indices=(np.array_equal(rt[ro],tags) and list(rtypes)==[4] and list(rst)==[2]
                      and np.array_equal(ret[0],et[0]) and np.array_equal(ren[0],en[0]) and np.array_equal(rsn[0],sn[0]))
        if not same_indices: raise ValueError('reread_connectivity_or_order_changed')
        readquality=distribution()
        conn=native.connectivity_metrics(dict(enumerate(tuple(map(float,row)) for row in reread)),cells.tolist(),triangles.tolist())
        exact_boundary=np.array_equal(reread[boundary],points[boundary])
        # Require equal boundary coordinates, positive tets, one region and full boundary.
        invariants=(exact_boundary and conn['boundary_matches'] and conn['tetra_connected_components']==1
                    and conn['count_negative']==conn['count_zero']==conn['repeated_node_tetrahedra']==0
                    and np.max(np.abs(reread-best_points))<=1e-10)
        receipt.update(status='completed',movable_nodes=len(free),affected_tetrahedra=len(patch),
            initial=initial,selected=final,reread=readquality,connectivity=conn,
            boundary_coordinates_bitwise_unchanged=exact_boundary,connectivity_bitwise_unchanged=same_indices,
            exported_mesh_sha256=mesh_hash,invariants_passed=bool(invariants),
            maximum_node_displacement=float(np.linalg.norm(reread-points,axis=1).max()),
            quality_improved=bool(invariants and improves(initial,readquality)),
            project_mesh_quality_passed=bool(invariants and readquality['minimum_minSICN']>=.1))
    except Exception as exc:
        receipt.update(status='failed',error_type=type(exc).__name__,error=str(exc)[:180])
    finally:
        gmsh.finalize(); receipt['input_and_source_unchanged']=sha(args.mesh)==MESH_SHA and sha(__file__)==source_hash
        receipt['elapsed_seconds']=time.monotonic()-start
        with (args.output/'report.json').open('x') as stream: json.dump(receipt,stream,indent=2,allow_nan=False)
    print(json.dumps({k:receipt.get(k) for k in ('status','quality_improved','project_mesh_quality_passed')}))
    return 0 if receipt.get('quality_improved') and receipt['input_and_source_unchanged'] else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('mesh','output'): parser.add_argument('--'+name,type=Path,required=True)
    signal.alarm(240)
    raise SystemExit(run(parser.parse_args()))
