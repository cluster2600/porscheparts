"""Independently inspect complete contact denominators and all bounded bridge proposals."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {k:data[k] for k in data.files}


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def inspect(points,faces,vertex,patch,fan_count,detect,limits):
    assert patch.ndim==2 and patch.shape[1]==3 and len(patch)>0
    before,_=fan_count(faces,len(points));assert len(patch)==before[vertex]-1
    assert np.all(patch[:,0]==vertex),'bridge_not_anchored_at_contact'
    uses=Counter((int(a),int(b)) for face in faces for a,b in zip(face,np.roll(face,-1)))
    normals=np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
    lengths=np.linalg.norm(normals,axis=1);assert np.all(lengths>0)
    owner={(int(a),int(b)):i for i,face in enumerate(faces) for a,b in zip(face,np.roll(face,-1))}
    total_area=0.
    for v,b,a in patch:
        assert len({int(v),int(b),int(a)})==3
        assert uses[(int(b),int(v))]==uses[(int(v),int(a))]==1
        assert uses[(int(v),int(b))]==uses[(int(a),int(v))]==0,'bridge_not_reversing_two_source_boundary_edges'
        triangle=points[[v,b,a]];normal=np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0]);length=np.linalg.norm(normal)
        assert length>0,'zero_area_bridge'
        assert np.linalg.norm(np.ptp(triangle,axis=0))<=limits['maximum_diagonal_nominal_mm'],'experimental_size_screen'
        for edge in ((int(b),int(v)),(int(v),int(a))):
            row=owner[edge];assert normal@normals[row]/(length*lengths[row])>=limits['minimum_signed_adjacent_normal_dot'],'experimental_normal_screen'
        total_area+=float(length/2)
    after,_=fan_count(np.r_[faces,patch],len(points))
    assert after[vertex]==1,'contact_fans_not_joined_completely'
    assert np.all(after<=before),'new_disconnected_used_vertex_fan'
    pairs,_,excluded=detect(points,np.r_[faces,patch])
    assert not len(pairs) and not len(excluded),'local_bridge_intersection_or_degeneracy'
    return total_area


def controls(fan_count,detect,limits):
    points=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[-1.,0.,0.],[0.,-1.,0.]])
    faces=np.array([[0,1,2],[0,3,4]]);patch=np.array([[0,2,3]])
    inspect(points,faces,0,patch,fan_count,detect,limits)
    pairs,_,_=detect(np.r_[points,points[:1]],np.array([[0,1,2],[5,3,4]]));assert len(pairs)==1
    crossing=np.array([[0.,0.,0.],[2.,0.,0.],[0.,2.,0.],[1.,1.,-1.],[1.,1.,1.]])
    pairs,_,_=detect(crossing,faces);assert len(pairs)==1
    try:inspect(points,faces,0,patch[:,::-1],fan_count,detect,limits)
    except AssertionError:pass
    else:raise AssertionError('reversed control bridge admitted')
    return dict(one_bridge_joins_two_open_source_fans=True,duplicate_index_contact_detected=True,
                shared_vertex_crossing_beyond_contact_detected=True,reversed_bridge_refused=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','prepared','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    fan_count=module(job['fan_source'],'frozen_whole_vertex_inspector').vertex_fans
    detect=module(job['predicate_source'],'frozen_intersection_predicates').detect
    control=controls(fan_count,detect,job['experimental_limits'])
    prepared=json.loads((args.prepared/'report.json').read_text());assert prepared['job_sha256']==sha(args.job)
    base=load(job['mesh']);v,f=base['points'],base['triangles'];counts=load(job['fan_witness'])['candidate_face_fans']
    expected=set(map(int,np.flatnonzero(counts>1)));assert {x['contact_vertex'] for x in prepared['private_contacts']}==expected
    args.output.mkdir(mode=0o700,exist_ok=False);records=[];selected=[]
    for contact in prepared['private_contacts']:
        target=contact['contact_vertex'];incident=np.flatnonzero(np.any(f==target,axis=1));used,inverse=np.unique(f[incident],return_inverse=True)
        index=int(np.searchsorted(used,target));prior,boundary=fan_count(inverse.reshape(-1,3),len(used))
        assert prior[index]==contact['source_fans']==counts[target]
        open_fans=int(np.count_nonzero(np.any(boundary==index,axis=1)))//2
        assert int(prior[index])-open_fans==contact['closed_fans']
        assert bool(contact['trials'])==(not bool(contact['closed_fans']))
        rows=[];passing=[]
        for trial in contact['trials']:
            ordinal=trial['proposal'];path=args.prepared/('private-contact-'+str(target)+'-proposal-'+str(ordinal)+'.npz')
            assert sha(path)==trial['proposal_sha256'];data=load(path);patch=data['new_faces']
            assert int(data['contact_vertex'])==target and np.array_equal(data['incident_source_face_rows'],incident)
            halo=np.flatnonzero(np.any(np.isin(f,np.unique(patch)),axis=1));global_faces=np.r_[f[halo],patch]
            used,inverse=np.unique(global_faces,return_inverse=True);local=inverse.reshape(-1,3);vertex=int(np.searchsorted(used,target))
            row=dict(contact_vertex=target,proposal=ordinal,prepared_screen_passed=trial['screen_passed'])
            try:
                area=inspect(v[used],local[:-len(patch)],vertex,local[-len(patch):],fan_count,detect,job['experimental_limits'])
                assert trial['screen_passed'],'preparation_and_independent_screen_disagree'
                row.update(accepted=True,reason='source_preserving_local_bridge_hypothesis',added_area_nominal_mm2=area)
                passing.append((area,tuple(map(int,patch.ravel())),ordinal,patch))
            except AssertionError as error:row.update(accepted=False,reason=str(error))
            rows.append(row)
        if passing:
            area,_,ordinal,patch=min(passing,key=lambda x:x[:2]);selected.append(dict(contact_vertex=target,proposal=ordinal,added_faces=len(patch)))
            np.savez_compressed(args.output/('private-selected-contact-'+str(target)+'.npz'),new_faces=patch,contact_vertex=np.array(target))
        records.extend(rows)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),prepared_report_sha256=sha(args.prepared/'report.json'),
                controls=control,complete_contacts=len(expected),contacts_with_closed_fans=prepared['contacts_with_closed_fans'],
                complete_proposals=len(records),locally_accepted_proposals=sum(x['accepted'] for x in records),
                selected_contacts=len(selected),selected_bridge_faces=sum(x['added_faces'] for x in selected),
                private_proposal_checks=records,private_selected_contacts=selected,full_candidate_checks_still_required=True,
                geometry_or_physical_roles_accepted=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not isinstance(v,(dict,list))}),flush=True)


if __name__=='__main__':main()
