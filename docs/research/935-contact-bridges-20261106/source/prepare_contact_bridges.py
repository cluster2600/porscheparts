"""Enumerate source-coordinate contact bridges; never split indices to hide contact."""
import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {k:data[k] for k in data.files}


def contact_fans(faces,vertex):
    """Local face-link traversal, separate from the frozen whole-mesh inspector."""
    assert np.all(np.sum(faces==vertex,axis=1)==1)
    incident = defaultdict(list)
    for row,face in enumerate(faces):
        for other in face[face!=vertex]:incident[int(other)].append(row)
    adjacency = [set() for _ in faces]
    for rows in incident.values():
        assert len(rows)<=2
        for a in rows:adjacency[a].update(rows)
    unseen = set(range(len(faces)));groups = []
    while unseen:
        stack = [min(unseen)];group = set()
        while stack:
            a = stack.pop()
            if a in group:continue
            group.add(a);stack.extend(adjacency[a]-group)
        unseen-=group;groups.append(sorted(group))
    result = []
    for group in groups:
        uses = Counter((int(a),int(b)) for face in faces[group] for a,b in zip(face,np.roll(face,-1)))
        outgoing = [b for a,b in uses if a==vertex and uses[(b,a)]==0]
        incoming = [a for a,b in uses if b==vertex and uses[(b,a)]==0]
        assert (len(outgoing),len(incoming)) in ((0,0),(1,1))
        result.append(dict(local_face_rows=group,outgoing=outgoing,incoming=incoming))
    return result


def proposals(fans,vertex):
    if any(not fan['outgoing'] for fan in fans):return []
    return [np.array([[vertex,fans[a]['incoming'][0],fans[b]['outgoing'][0]]
                      for a,b in zip(order,order[1:])],dtype=np.int64)
            for order in itertools.permutations(range(len(fans)))]


def diagnostics(points,faces,patch):
    uses = {(int(a),int(b)):row for row,f in enumerate(faces) for a,b in zip(f,np.roll(f,-1))}
    normals = np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
    norms = np.linalg.norm(normals,axis=1);assert np.all(norms>0)
    dots = [];area = 0.;diagonal = 0.
    for v,b,a in patch:
        tri = points[[v,b,a]];normal = np.cross(tri[1]-tri[0],tri[2]-tri[0]);length = np.linalg.norm(normal)
        assert length>0,'zero_area_bridge'
        adjacent = [uses[(int(b),int(v))],uses[(int(v),int(a))]]
        dots.extend(float(normal@normals[row]/(length*norms[row])) for row in adjacent)
        area+=length/2;diagonal=max(diagonal,float(np.linalg.norm(np.ptp(tri,axis=0))))
    return dict(area_nominal_mm2=area,maximum_diagonal_nominal_mm=diagonal,minimum_signed_adjacent_normal_dot=min(dots))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args();job = json.loads(args.job.read_text());started=time.monotonic()
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    mesh=load(job['mesh']);counts=load(job['fan_witness'])['candidate_face_fans'];f=mesh['triangles'];v=mesh['points']
    targets=np.flatnonzero(counts>1);assert len(targets)==48
    rows=np.flatnonzero(np.any(np.isin(f,targets),axis=1))
    args.output.mkdir(mode=0o700,exist_ok=False);records=[]
    for target in targets:
        incident=rows[np.any(f[rows]==target,axis=1)];fans=contact_fans(f[incident],int(target))
        assert len(fans)==counts[target]
        trials=[]
        for ordinal,patch in enumerate(proposals(fans,int(target))):
            row=dict(proposal=ordinal)
            try:
                metrics=diagnostics(v,f[incident],patch);row.update(metrics)
                assert metrics['maximum_diagonal_nominal_mm']<=job['experimental_limits']['maximum_diagonal_nominal_mm'],'experimental_size_screen'
                assert metrics['minimum_signed_adjacent_normal_dot']>=job['experimental_limits']['minimum_signed_adjacent_normal_dot'],'experimental_normal_screen'
                row.update(screen_passed=True,reason='bounded_contact_bridge_hypothesis')
            except AssertionError as error:row.update(screen_passed=False,reason=str(error))
            path=args.output/('private-contact-'+str(int(target))+'-proposal-'+str(ordinal)+'.npz')
            np.savez_compressed(path,new_faces=patch,contact_vertex=np.array(target),incident_source_face_rows=incident)
            row['proposal_sha256']=sha(path);trials.append(row)
        records.append(dict(contact_vertex=int(target),source_fans=len(fans),closed_fans=sum(not x['outgoing'] for x in fans),
                            reason='closed_source_fan_cannot_be_joined_by_boundary_addition' if not trials else 'all_orders_retained',trials=trials))
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    result=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),contacts=len(targets),
                contacts_with_closed_fans=sum(x['closed_fans']>0 for x in records),proposals=sum(len(x['trials']) for x in records),
                screen_passed=sum(t['screen_passed'] for x in records for t in x['trials']),private_contacts=records,
                source_coordinates_or_triangles_changed=False,physical_classifications_accepted=0,
                limits_are_experimental_not_physical_tolerances=True,full_bare_head_created=False,manufacturing_authorized=False,
                seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not isinstance(v,(dict,list))}),flush=True)


if __name__=='__main__':main()
