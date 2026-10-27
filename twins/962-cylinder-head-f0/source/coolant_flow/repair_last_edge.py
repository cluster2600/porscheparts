"""Try endpoint collapses only where the local flip cannot remove a deficient face."""
import argparse
import json
from pathlib import Path

from prepare_surface import sha
from repair_slivers import Q_MIN, triangle_q


def collapse(points, faces):
    import numpy as np
    import trimesh
    q = triangle_q(points, faces)
    choices = []
    for fi in np.flatnonzero(q < Q_MIN):
        for i in range(3):
            for u, v in (faces[fi][[i,(i+1)%3]], faces[fi][[(i+1)%3,i]]):
                labels = [next((s for s in (-76,76) if abs(points[k,0]-s)<1e-5), None) for k in (u,v)]
                if labels[0] != labels[1]: continue
                incident = np.any(np.isin(faces,[u,v]),axis=1)
                old = faces[incident]
                replacement = np.where(old==v,u,old)
                keep = np.array([len(set(f))==3 for f in replacement])
                if np.count_nonzero(~keep)!=2: continue
                replacement = replacement[keep]
                new_q = triangle_q(points,replacement)
                if not len(new_q) or min(new_q)<Q_MIN: continue
                trial = np.concatenate((faces[~incident],replacement))
                m = trimesh.Trimesh(vertices=points,faces=trial,process=False)
                m.remove_unreferenced_vertices()
                original = trimesh.Trimesh(vertices=points,faces=faces,process=False)
                if not m.is_watertight or not m.is_winding_consistent or m.euler_number!=original.euler_number: continue
                if len(np.unique(np.sort(trial,axis=1),axis=0))!=len(trial): continue
                if np.count_nonzero(triangle_q(points,trial)<Q_MIN)>=np.count_nonzero(q<Q_MIN): continue
                choices.append((float(np.linalg.norm(points[u]-points[v])),trial,int(u),int(v)))
    if not choices: return faces,None
    distance,trial,u,v=min(choices,key=lambda c:c[0])
    return trial,dict(kept_vertex=u,removed_vertex=v,edge_length_mm=distance)


if __name__ == "__main__":
    import numpy as np
    import trimesh
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();p=args.parent;o=args.output
    record=json.loads((p/'native-report.json').read_text())
    if sha(p/'coolant.stl')!=record['candidate_sha256']:raise ValueError('Parent changed')
    if o.exists():raise ValueError('Output must be new')
    m=trimesh.load_mesh(p/'coolant.stl',process=True)
    f,change=collapse(np.asarray(m.vertices),np.asarray(m.faces))
    if change is None:raise ValueError('No admissible endpoint collapse')
    o.mkdir(parents=True);trimesh.Trimesh(vertices=m.vertices,faces=f,process=False).export(o/'coolant.stl')
    report=dict(status='endpoint_repair_awaiting_independent_checks',source_sha256=record['source_sha256'],
                parent_receipt_sha256=sha(p/'native-report.json'),original_faces=record['original_faces'],
                faces=len(f),collapse=change,below_surface_q_gate=int(np.count_nonzero(triangle_q(m.vertices,f)<Q_MIN)),
                candidate_sha256=sha(o/'coolant.stl'),script_sha256=sha(Path(__file__)),
                geometry_admitted=False,manufacturing_authorized=False)
    (o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
