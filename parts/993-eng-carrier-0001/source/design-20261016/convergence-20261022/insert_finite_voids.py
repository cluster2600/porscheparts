"""Insert eight closed void chambers while preserving the exact R2 outer surface.

This is a computational baseline. Transition geometry, powder escape and full
mechanics remain pending; no printing or manufacturing release is produced.
"""
import argparse,gzip,hashlib,io,json,signal,time
from pathlib import Path
import numpy as np


def main():
    import manifold3d as mf
    from reconstruct_core_envelopes import canonical_surface
    p=argparse.ArgumentParser(__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--networks',type=Path,nargs=4,required=True);p.add_argument('--envelope-directory',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output;assert not out.exists();out.mkdir();signal.alarm(180);start=time.monotonic();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source_sha=sha(Path(__file__))
    reference=a.reference;raw=gzip.decompress(reference.read_bytes());assert hashlib.sha256(raw).hexdigest()=='396161993b35f708fdd1e527f875aff60daf8c79031dc9a39c42891a9c1ae1a0'
    inputs={str(reference):sha(reference)};tools=[];expected=0.;envelopes=None
    if a.envelope_directory:
     metadata=a.envelope_directory/'assessment.json';archive=a.envelope_directory/'envelopes.npz';envelopes=json.loads(metadata.read_text());assert sha(archive)==envelopes['output_sha256']['envelopes.npz'];envelope_data=np.load(archive);inputs.update({str(p):sha(p)for p in [metadata,archive]})
    for rank in range(4):
     directory=a.networks[rank];r=json.loads((directory/'assessment.json').read_text());assert r['status']in ['dominant_void_network_per_analytic_sign_retained','native_G1_smoothed_voids_transfer_and_containment_checked','internal_void_repair_candidate_generated'] and r['rank']==rank and r['size_mm']==.125 and not r['manufacturing_authorized'];inputs[str(directory/'assessment.json')]=sha(directory/'assessment.json')
     for selected in r['selected']:
      path=directory/selected['file'];assert sha(path)==selected['sha256'];z=np.load(path);tool=mf.Manifold(mf.Mesh64(np.array(z['vertices']),np.array(z['triangles'],dtype=np.uint64)));assert tool.status()==mf.Error.NoError;tools.append(tool);expected+=selected['volume_mm3'];inputs[str(path)]=sha(path)
      if r['status']=='internal_void_repair_candidate_generated':
       assert envelopes is not None,'Reconstructed voids require their original conservative envelopes'
       c=envelopes['components'][rank];vs=sum(x['vertices']for x in envelopes['components'][:rank]);fs=sum(x['triangles']for x in envelopes['components'][:rank]);core=mf.Manifold(mf.Mesh64(np.array(envelope_data['vertices'][vs:vs+c['vertices']]),np.array(envelope_data['triangles'][fs:fs+c['triangles']]-vs,dtype=np.uint64)));assert core.status()==mf.Error.NoError
       outside=tool-core;materialized=tool.to_mesh64();transfer=all(np.array_equal(x,y)for x,y in zip(canonical_surface(z['vertices'],z['triangles']),canonical_surface(np.array(materialized.vert_properties)[:,:3],np.array(materialized.tri_verts,dtype=np.uint64))));parts=tool.decompose()
       observation=dict(rank=rank,branch=selected['branch'],outside_is_empty=outside.is_empty(),outside_volume_mm3=outside.volume(),native_input_oriented_triangles_exact=transfer,positive_void_components=sum(x.volume()>0 for x in parts),negative_cavity_components=sum(x.volume()<0 for x in parts),relative_volume_change=abs(tool.volume()-selected['volume_mm3'])/selected['volume_mm3']);(out/f"region-{rank}-branch-{selected['branch']}-containment.json").write_text(json.dumps(observation,indent=2)+'\n')
       assert outside.is_empty()and transfer and len(parts)==1 and parts[0].volume()>0 and observation['relative_volume_change']<=1e-10
    contract=dict(scope='Closed eight-chamber computational variant; transition blending, powder escape and mechanics are pending',maximum_seconds=180,maximum_mass_kg=1.30,volume_relative_limit=1e-10,original_external_oriented_triangles_must_be_exact=True,final_oriented_triangle_roundtrip_must_be_exact=True,required_positive_shells=1,required_negative_shells=8,input_sha256=inputs,source_sha256=source_sha,manufacturing_authorized=False);(out/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    with io.StringIO(raw.decode())as s:nv,nf=map(int,s.readline().split());v=np.loadtxt(s,max_rows=nv);f=np.loadtxt(s,dtype=np.uint64)
    body=mf.Manifold(mf.Mesh64(np.array(v),np.array(f)));assert body.status()==mf.Error.NoError
    void=mf.Manifold.batch_boolean(tools,mf.OpType.Add);assert void.status()==mf.Error.NoError and abs(void.volume()-expected)/expected<=1e-10
    outside=void-body;(out/'containment.json').write_text(json.dumps(dict(outside_status=str(outside.status()),outside_is_empty=outside.is_empty(),outside_volume_mm3=outside.volume()),indent=2)+'\n');assert outside.is_empty()
    candidate=body-void;assert candidate.status()==mf.Error.NoError;assert abs(candidate.volume()-(body.volume()-expected))/body.volume()<=1e-10 and candidate.volume()*4.42e-6<=1.30
    shells=candidate.decompose();positive=[s for s in shells if s.volume()>0];negative=[s for s in shells if s.volume()<0];assert len(positive)==1 and len(negative)==8
    outer=positive[0].to_mesh64();external_same=all(np.array_equal(x,y)for x,y in zip(canonical_surface(v,f),canonical_surface(np.array(outer.vert_properties)[:,:3],np.array(outer.tri_verts,dtype=np.uint64))));assert external_same
    mesh=candidate.to_mesh64();cv=np.array(mesh.vert_properties)[:,:3];cf=np.array(mesh.tri_verts,dtype=np.uint64);back=mf.Manifold(mf.Mesh64(cv,cf));assert back.status()==mf.Error.NoError;b=back.to_mesh64();same=all(np.array_equal(x,y)for x,y in zip(canonical_surface(cv,cf),canonical_surface(np.array(b.vert_properties)[:,:3],np.array(b.tri_verts,dtype=np.uint64))));assert same
    np.savez_compressed(out/'candidate.npz',vertices=cv,triangles=cf);report=dict(status='complete_closed_chamber_variant_geometry_checked',nominal_reference_mass_kg=body.volume()*4.42e-6,nominal_candidate_mass_kg=candidate.volume()*4.42e-6,removed_volume_mm3=void.volume(),candidate_volume_mm3=candidate.volume(),positive_material_shells=len(positive),negative_void_shells=len(negative),original_external_oriented_triangles_exact=external_same,final_oriented_triangle_roundtrip_exact=same,vertices=len(cv),triangles=len(cf),output_sha256=sha(out/'candidate.npz'),source_sha256=source_sha,elapsed_seconds=time.monotonic()-start,baseline_geometry_changed=False,candidate_geometry_generated=True,smooth_transitions_generated=False,void_boundaries_G1_derived=all(json.loads((d/'assessment.json').read_text())['status']=='native_G1_smoothed_voids_transfer_and_containment_checked'for d in a.networks),powder_escape_demonstrated=False,complete_carrier_mechanics_converged=False,manufacturing_authorized=False);(out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps(report))


if __name__=='__main__':main()
