"""Audit the fixed-face tetrahedron mean-ratio ceiling before changing mesher settings."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("mesh","tags","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(mode=0o700,exist_ok=False)
    assert sha(args.mesh)=="05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594"
    assert sha(args.tags)=="877cf9c6638eb388755a378775428c7a5067409f166b3ea38d03b1837f2fae2f"
    with np.load(args.mesh,allow_pickle=False) as data:v,f=data["vertices"],data["triangles"]
    tags=np.load(args.tags,allow_pickle=False);assert len(tags)==len(f)
    quality=np.empty(len(f))
    for start in range(0,len(f),100000):
        xyz=v[f[start:start+100000]];a,b,c=xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0],xyz[:,2]-xyz[:,1]
        twice_area=np.linalg.norm(np.cross(a,b),axis=1)
        quality[start:start+len(xyz)]=2*np.sqrt(3)*twice_area/(np.sum(a*a+b*b+c*c,axis=1))
    assert np.all(quality>0) and np.max(quality)<=1+1e-12
    ceiling=quality**(2/3)
    # The analytic maximum occurs above the centroid at h^2=2S/9.
    for base in [np.array([[0,0,0],[1,0,0],[0,1,0]],float),np.array([[0,0,0],[3,0,0],[.01,.001,0]],float)]:
        s=sum(np.sum((base[i]-base[j])**2) for i,j in [(0,1),(0,2),(1,2)])
        a2=np.linalg.norm(np.cross(base[1]-base[0],base[2]-base[0]));h=np.sqrt(2*s/9)
        maximum=12*(a2*h/2)**(2/3)/(4*s/3+3*h*h)
        assert abs(maximum-(2*np.sqrt(3)*a2/s)**(2/3))<1e-12
    bins=[]
    for threshold in [.0001,.001,.01,.05,.1]:
        selected=ceiling<threshold
        count=int(selected.sum())
        bins.append({"mean_ratio_threshold":threshold,"fixed_faces_below_ceiling":count,
                     "retained_parent_skin":int((selected&(tags==0)).sum()),
                     "assumed_caps":int((selected&(tags>0)).sum()),
                     "any_tetrahedralization_forces_at_least_this_many_below_threshold_cells":(count+3)//4})
    bad=np.flatnonzero(ceiling<.01)
    np.savez_compressed(args.output/"private-faces.npz",face_ids=bad,shape_quality=quality[bad],mean_ratio_ceiling=ceiling[bad],construction_tags=tags[bad])
    result={"source_sha256":sha(Path(__file__)),"mesh_sha256":sha(args.mesh),"tags_sha256":sha(args.tags),
            "triangles":len(f),"minimum_triangle_shape_quality":float(quality.min()),
            "minimum_incident_tet_mean_ratio_ceiling":float(ceiling.min()),"bins":bins,
            "analytic_optimum_controls_passed":True,
            "bound":"For fixed triangular base quality q_f, any incident tetrahedron has mean ratio at most q_f^(2/3)",
            "verdict":"Interior sizing or node relocation cannot eliminate these bins while these exact boundary triangles remain",
            "bins_are_diagnostics_not_engineering_allowables":True,"physical_acceptance":False,"manufacturing_qualified":False}
    with (args.output/"report.json").open("x") as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=="__main__":main()
