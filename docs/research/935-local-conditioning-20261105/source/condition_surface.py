"""One preservation-bounded conditioning composition on the actual local head."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def save(path,value):
    with path.open("x") as stream:
        stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def qualities(vertices,faces):
    value=np.empty(len(faces));normals=np.empty((len(faces),3))
    for start in range(0,len(faces),100000):
        xyz=vertices[faces[start:start+100000]]
        a,b=xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]
        cross=np.cross(a,b);length=np.linalg.norm(cross,axis=1)
        assert np.all(length>0),"Degenerate input refused"
        count=len(xyz)
        value[start:start+count]=2*np.sqrt(3)*length/np.sum(a*a+b*b+(a-b)**2,axis=1)
        normals[start:start+count]=cross/length[:,None]
    return value,normals


def summary(quality):
    return {"minimum":float(quality.min()),"below_0p01":int((quality<.01).sum()),
            "incident_tet_ceiling_below_0p01":int((quality**(2/3)<.01).sum())}


def volume(vertices,faces):
    origin=vertices.mean(axis=0);result=0.
    for start in range(0,len(faces),100000):
        xyz=vertices[faces[start:start+100000]]-origin
        result+=float(np.einsum('ij,ij->',xyz[:,0],np.cross(xyz[:,1],xyz[:,2]))/6)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("mesh","tags","geometry-report","upstream-audit","repository","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(mode=0o700,exist_ok=False)
    assert sha(a.mesh)=="05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594"
    assert sha(a.tags)=="877cf9c6638eb388755a378775428c7a5067409f166b3ea38d03b1837f2fae2f"
    admission=json.loads(a.geometry_report.read_text());upstream=json.loads(a.upstream_audit.read_text())
    assert admission["input_sha256"]==sha(a.mesh) and admission["geometry_export_gate_passed"] and admission["intersection_pairs"]==0
    assert upstream["mesh_sha256"]==sha(a.mesh) and upstream["analytic_optimum_controls_passed"]
    previous=a.repository/"docs/research/935-mesh-admission-20261104/source"
    paths={"quads":previous/"trial_bounded_quad_flips.py","relocation":previous/"trial_bounded_relocation.py"}
    modules={name:module(path,"retained_"+name) for name,path in paths.items()}
    quads,relocation=modules["quads"],modules["relocation"]
    plan={"scope":"Separate numerical surface, not replacement print master or functional head acceptance",
          "mesh_sha256":sha(a.mesh),"tags_sha256":sha(a.tags),"geometry_report_sha256":sha(a.geometry_report),
          "upstream_audit_sha256":sha(a.upstream_audit),"source_sha256":sha(Path(__file__)),
          "retained_helper_hashes":{name:sha(path) for name,path in paths.items()},
          "upstream_verdict":"Closed manifold hypothesis surface; fixed-face ceilings require surface conditioning before interior-size sweeps. Inferred closures and physical interfaces remain unaccepted.",
          "passes":1,"quad_patch_bound_limit_mm":.0049,"vertex_displacement_limit_mm":.0049,
          "composed_surface_correspondence_limit_mm":.01,"relative_volume_change_limit":.0001,
          "bad_face_threshold":.01,"bad_face_reduction_min_fraction":.5,
          "protection":"Every cap face and every face incident to an original dihedral angle over 30 degrees stays fixed, including its vertices. No measured-interface acceptance inferred.",
          "physical_acceptance":False,"manufacturing_qualified":False,"parameter_sweep":False}
    save(a.output/"plan.json",plan)
    save(a.output/"quad-controls.json",quads.controls())
    save(a.output/"relocation-controls.json",relocation.controls())
    with np.load(a.mesh,allow_pickle=False) as data:v,f=data["vertices"],data["triangles"]
    tags=np.load(a.tags,allow_pickle=False);assert len(tags)==len(f)
    start=time.monotonic();q,normals=qualities(v,f)
    before=summary(q)
    directed=np.concatenate((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]))
    keys=directed.min(axis=1)*len(v)+directed.max(axis=1)
    order=np.argsort(keys,kind='stable');ordered=keys[order]
    assert len(ordered)%2==0 and np.array_equal(ordered[::2],ordered[1::2])
    assert not np.any(ordered[1:-1:2]==ordered[2::2])
    assert not np.any(np.sign(directed[:,1]-directed[:,0])[order].reshape(-1,2).sum(axis=1))
    pairs=(order.reshape(-1,2)%len(f))
    crease=np.einsum('ij,ij->i',normals[pairs[:,0]],normals[pairs[:,1]])<np.cos(np.deg2rad(30))
    protected=tags>0;protected[np.unique(pairs[crease])]=True
    protected_ids=np.flatnonzero(protected)
    locked=np.zeros(len(v),bool);locked[np.unique(f[protected])]=True
    np.save(a.output/"private-protected-face-ids.npy",protected_ids)
    np.save(a.output/"private-locked-vertices.npy",locked)
    eligible=np.flatnonzero((q[pairs]<.01).any(axis=1)&~protected[pairs].any(axis=1))
    unique_keys=ordered[::2];candidates=[]
    for number,position in enumerate(eligible):
        ra,rb=map(int,pairs[position]);aa,bb=map(int,directed[order[2*position]])
        first,second=f[ra],f[rb]
        i=int(np.flatnonzero(first==aa)[0])
        if first[(i+1)%3]!=bb:aa,bb=bb,aa
        j=int(np.flatnonzero(second==bb)[0]);assert second[(j+1)%3]==aa
        cc=int(first[(first!=aa)&(first!=bb)][0]);dd=int(second[(second!=aa)&(second!=bb)][0])
        key=min(cc,dd)*len(v)+max(cc,dd);where=np.searchsorted(unique_keys,key)
        if cc==dd or (where<len(unique_keys) and unique_keys[where]==key):continue
        certificate=quads.certificate(v[[aa,bb,cc,dd]])
        if certificate is None or certificate[0]>.0049:continue
        replacement=np.array([[cc,aa,dd],[dd,bb,cc]])
        proposed=quads.qvalues(v,replacement);old=q[[ra,rb]]
        improvement=int((old<.01).sum())-int((proposed<.01).sum())
        if improvement<1 or proposed.min()<=old.min()*(1+1e-6):continue
        candidates.append((improvement,float(proposed.min()-old.min()),ra,rb,aa,bb,cc,dd,*certificate,key))
        if number%5000==0:print("Enumerated",number,"of",len(eligible),flush=True)
    candidates.sort(key=lambda row:(-row[0],-row[1],row[2],row[3]))
    candidate=f.copy();touched=np.zeros(len(f),bool);new_edges=set();accepted=[]
    for row in candidates:
        _,_,ra,rb,aa,bb,cc,dd,bound,t,s,key=row
        if touched[ra] or touched[rb] or key in new_edges:continue
        candidate[ra],candidate[rb]=[cc,aa,dd],[dd,bb,cc]
        touched[[ra,rb]]=True;new_edges.add(key)
        accepted.append([ra,rb,aa,bb,cc,dd,bound,t,s])
    provenance=np.asarray(accepted,float).reshape(-1,9)
    np.savez_compressed(a.output/"private-quad-provenance.npz",records=provenance)
    np.savez_compressed(a.output/"flipped.npz",vertices=v,triangles=candidate)
    phase_q,_=qualities(v,candidate)
    save(a.output/"quad-stage.json",{"eligible_edges":len(eligible),"qualified_candidates":len(candidates),
         "flips":len(accepted),"maximum_patch_bound_mm":max((x[6] for x in accepted),default=0),
         "before":before,"after":summary(phase_q),"protected_faces":len(protected_ids),
         "protected_rows_identical":bool(np.array_equal(candidate[protected],f[protected]))})
    del directed,keys,order,ordered,pairs,unique_keys,normals,phase_q,candidates
    # Preserve both original protected vertices and newly detected sharp features.
    new_locks,_,_=relocation.locked_vertices(v,candidate,protected_ids)
    locks=locked|new_locks
    conditioned,moved,visited=relocation.relocate(v,candidate,locks,.0049)
    delta=np.linalg.norm(conditioned-v,axis=1)
    assert delta.max()<=.0049+1e-12 and np.array_equal(conditioned[locked],v[locked])
    assert np.array_equal(candidate[protected],f[protected])
    np.savez_compressed(a.output/"candidate.npz",vertices=conditioned,triangles=candidate)
    np.save(a.output/"private-moved-vertex-ids.npy",moved)
    final_q,_=qualities(conditioned,candidate)
    after=summary(final_q);reduction=1-after["below_0p01"]/before["below_0p01"]
    initial_volume,final_volume=volume(v,f),volume(conditioned,candidate)
    max_patch=max((x[6] for x in accepted),default=0)
    result={"before":before,"after":after,"flips":len(accepted),"vertices_moved":len(moved),
            "vertices_considered_for_relocation":visited,"maximum_vertex_displacement_mm":float(delta.max()),
            "producer_composed_correspondence_bound_mm":max_patch+float(delta.max()),
            "signed_volume_before_mm3":initial_volume,"signed_volume_after_mm3":final_volume,
            "relative_volume_change":abs(final_volume/initial_volume-1),"bad_face_reduction_fraction":reduction,
            "quality_reduction_gate":reduction>=.5,"independent_geometry_and_preservation_pending":True,
            "accepted_for_meshing":False,"physical_acceptance":False,"manufacturing_qualified":False,
            "processing_seconds":time.monotonic()-start}
    save(a.output/"producer.json",result);print(json.dumps(result),flush=True)


if __name__=="__main__":main()
